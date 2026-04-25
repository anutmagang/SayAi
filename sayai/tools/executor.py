from __future__ import annotations

import asyncio
import json
import re
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import httpx

from sayai.config import load_config


class ToolExecutor:
    """Parses `<tool>...</tool><args>...</args>` from LLM output and runs handlers."""

    def __init__(
        self,
        cwd: Path | None = None,
        *,
        session_id: str | None = None,
        shared_scratch: dict[str, Any] | None = None,
    ):
        self.cwd = (cwd or Path.cwd()).resolve()
        self.session_id = session_id or "default"
        self.shared_scratch: dict[str, Any] = shared_scratch if shared_scratch is not None else {}
        self._settings = load_config()
        self._mcp: Any = None

    @property
    def mcp(self) -> Any:
        if self._mcp is None:
            from sayai.tools.mcp_bridge import MCPBridge

            self._mcp = MCPBridge()
        return self._mcp

    def _roots(self) -> list[Path]:
        roots = [self.cwd]
        for raw in self._settings.tools.allowed_dirs:
            p = Path(raw).expanduser()
            if not p.is_absolute():
                p = (self.cwd / p).resolve()
            else:
                p = p.resolve()
            roots.append(p)
        return roots

    def _is_under_root(self, path: Path) -> bool:
        rp = path.resolve()
        for root in self._roots():
            try:
                rp.relative_to(root)
                return True
            except ValueError:
                continue
        return False

    def _resolve_path(self, path: str) -> Path:
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = (self.cwd / p).resolve()
        else:
            p = p.resolve()
        return p

    async def execute(self, llm_response: str) -> str:
        tool_match = re.search(r"<tool>(.*?)</tool>", llm_response, re.DOTALL)
        args_match = re.search(r"<args>(.*?)</args>", llm_response, re.DOTALL)
        if not tool_match:
            return ""

        tool_name = tool_match.group(1).strip()
        args: dict = {}
        if args_match:
            try:
                args = json.loads(args_match.group(1).strip())
            except json.JSONDecodeError as e:
                return f"Error: invalid JSON in <args>: {e}"

        handler_name = f"tool_{tool_name}"
        handler = getattr(self, handler_name, None)
        if not handler:
            return f"Error: tool '{tool_name}' not found"

        return await handler(**args)

    async def tool_bash(self, command: str, timeout: int | None = None) -> str:
        t = timeout if timeout is not None else self._settings.tools.bash_timeout
        max_out = self._settings.tools.bash_max_output

        def _run() -> str:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=t,
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            if len(out) > max_out:
                return out[:max_out] + f"\n... (truncated, max {max_out} chars)"
            return out or "(no output)"

        try:
            return await asyncio.to_thread(_run)
        except subprocess.TimeoutExpired:
            return f"Error: command timed out after {t}s"

    async def tool_read_file(self, path: str) -> str:
        p = self._resolve_path(path)
        if not self._is_under_root(p):
            return "Error: path not allowed"
        try:
            text = p.read_text(encoding="utf-8")
        except OSError as e:
            return f"Error: {e}"
        if self._settings.memory.index_on_read and self._settings.memory.qdrant_enabled:
            from sayai.memory.indexer import schedule_index_file

            schedule_index_file(self.cwd, p, text)
        return text

    async def tool_write_file(self, path: str, content: str) -> str:
        p = self._resolve_path(path)
        if not self._is_under_root(p):
            return "Error: path not allowed"
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        except OSError as e:
            return f"Error: {e}"
        if self._settings.memory.index_on_write and self._settings.memory.qdrant_enabled:
            from sayai.memory.indexer import schedule_index_file

            schedule_index_file(self.cwd, p, content)
        return f"OK: wrote {p}"

    async def tool_list_dir(self, path: str = ".") -> str:
        p = self._resolve_path(path)
        if not self._is_under_root(p):
            return "Error: path not allowed"
        try:
            names = sorted(x.name for x in p.iterdir())
            return "\n".join(names) if names else "(empty)"
        except OSError as e:
            return f"Error: {e}"

    def _rg_search(self, query: str, base: Path, max_count: int = 50) -> str:
        r = subprocess.run(
            ["rg", "-n", "--max-count", str(max_count), query, str(base)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=self.cwd,
        )
        return (r.stdout or r.stderr or "").strip()

    async def tool_search_code(self, query: str, path: str = ".") -> str:
        base = self._resolve_path(path)
        if not self._is_under_root(base):
            return "Error: path not allowed"
        try:

            def _run() -> str:
                return self._rg_search(query, base)

            out = await asyncio.to_thread(_run)
            return out or "(no matches)"
        except FileNotFoundError:
            return "Error: ripgrep (rg) not installed"
        except subprocess.TimeoutExpired:
            return "Error: ripgrep timed out"

    async def tool_web_search(self, query: str) -> str:
        """DuckDuckGo instant answer API (no API key)."""
        url = "https://api.duckduckgo.com/"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                r = await client.get(
                    url,
                    params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
                )
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            return f"Error: web_search failed: {e}"

        parts: list[str] = []
        if data.get("AbstractText"):
            parts.append(str(data["AbstractText"]))
        if data.get("Answer"):
            parts.append(str(data["Answer"]))
        for topic in data.get("RelatedTopics", [])[:8]:
            if isinstance(topic, dict) and topic.get("Text"):
                parts.append(str(topic["Text"]))
        if not parts:
            return f"(no instant results; try https://duckduckgo.com/?q={quote_plus(query)})"
        return "\n".join(parts)

    async def tool_fetch_url(self, url: str) -> str:
        try:
            async with httpx.AsyncClient(
                timeout=25.0,
                follow_redirects=True,
                headers={"User-Agent": "SayAi/0.2 (+https://example.local)"},
            ) as client:
                r = await client.get(url)
                r.raise_for_status()
                raw = r.text[:200_000]
        except Exception as e:
            return f"Error: fetch_url failed: {e}"
        text = re.sub(r"<script[^>]*>.*?</script>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > 14_000:
            text = text[:14_000] + " …(truncated)"
        return text or "(empty body)"

    async def tool_retrieve_codebase(
        self, query: str, path: str = ".", max_files: int = 5
    ) -> str:
        """Basic RAG: ripgrep hits then read tops of unique files."""
        base = self._resolve_path(path)
        if not self._is_under_root(base):
            return "Error: path not allowed"
        try:

            def _rg() -> str:
                return self._rg_search(query, base, max_count=80)

            raw = await asyncio.to_thread(_rg)
        except FileNotFoundError:
            return "Error: ripgrep (rg) not installed"
        except subprocess.TimeoutExpired:
            return "Error: ripgrep timed out"

        paths_ordered: list[str] = []
        for line in raw.splitlines():
            m = re.match(r"^([^:]+?):\d+:", line)
            if not m:
                continue
            rel = m.group(1).strip()
            if rel and rel not in paths_ordered:
                paths_ordered.append(rel)
            if len(paths_ordered) >= max_files:
                break

        chunks: list[str] = []
        for rel in paths_ordered:
            p = self._resolve_path(rel)
            if not self._is_under_root(p):
                continue
            try:
                content = p.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                chunks.append(f"### {rel}\n(read error: {e})\n")
                continue
            head = "\n".join(content.splitlines()[:120])
            if len(head) > 6000:
                head = head[:6000] + "\n…(truncated)"
            chunks.append(f"### {rel}\n```\n{head}\n```\n")

        if not chunks:
            return raw or "(no retrieve_codebase hits)"
        return "\n".join(chunks)

    def _git_repo(self) -> bool:
        return (self.cwd / ".git").exists()

    async def tool_git_diff(self, staged: bool = False, paths: str = "") -> str:
        if not self._git_repo():
            return "Error: not a git repository"
        cmd = ["git", "diff"]
        if staged:
            cmd.append("--staged")
        if paths.strip():
            cmd.extend(shlex.split(paths))

        def _run() -> str:
            r = subprocess.run(
                cmd,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return ((r.stdout or "") + (r.stderr or ""))[: self._settings.tools.bash_max_output]

        return await asyncio.to_thread(_run)

    async def tool_git_status(self, porcelain: bool = True) -> str:
        if not self._git_repo():
            return "Error: not a git repository"
        args = ["git", "status", "--porcelain=v1"] if porcelain else ["git", "status"]

        def _run() -> str:
            r = subprocess.run(
                args,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return ((r.stdout or "") + (r.stderr or ""))[:8000]

        return await asyncio.to_thread(_run)

    async def tool_git_log(self, n: int = 20, oneline: bool = True) -> str:
        if not self._git_repo():
            return "Error: not a git repository"
        cmd = ["git", "log", f"-n{int(n)}"]
        if oneline:
            cmd.append("--oneline")

        def _run() -> str:
            r = subprocess.run(
                cmd,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return ((r.stdout or "") + (r.stderr or ""))[:12_000]

        return await asyncio.to_thread(_run)

    async def tool_git_commit(self, message: str, add_all: bool = False) -> str:
        if not self._git_repo():
            return "Error: not a git repository"
        if not message.strip():
            return "Error: empty commit message"

        def _run() -> str:
            if add_all:
                a = subprocess.run(
                    ["git", "add", "-A", "."],
                    cwd=self.cwd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if a.returncode != 0:
                    return f"git add failed: {a.stderr or a.stdout}"
            c = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return (c.stdout or c.stderr or f"exit {c.returncode}")[:8000]

        return await asyncio.to_thread(_run)

    async def tool_patch_file(self, path: str, diff: str) -> str:
        """Apply a unified diff in the repo (git apply, then patch -p0)."""
        if not self._is_under_root(self._resolve_path(path)):
            return "Error: path not allowed"
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".patch",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp.write(diff)
            tmp_path = tmp.name

        try:

            def _try_git() -> str | None:
                if not self._git_repo():
                    return None
                chk = subprocess.run(
                    ["git", "apply", "--check", tmp_path],
                    cwd=self.cwd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if chk.returncode != 0:
                    return f"git apply --check failed:\n{chk.stderr or chk.stdout}"
                ap = subprocess.run(
                    ["git", "apply", tmp_path],
                    cwd=self.cwd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if ap.returncode != 0:
                    return f"git apply failed:\n{ap.stderr or ap.stdout}"
                return "OK: applied patch via git apply"

            def _try_patch() -> str:
                p = subprocess.run(
                    ["patch", "-p0", "-i", tmp_path],
                    cwd=self.cwd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if p.returncode != 0:
                    return f"patch failed:\n{p.stderr or p.stdout}"
                return "OK: applied patch via patch"

            msg = await asyncio.to_thread(_try_git)
            if msg is not None:
                return msg
            return await asyncio.to_thread(_try_patch)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def tool_run_tests(self, command: str | None = None) -> str:
        cmd = command or self._settings.tool_extra.test_command
        parts = shlex.split(cmd, posix=True)
        if not parts:
            return "Error: empty test command"

        def _run() -> str:
            r = subprocess.run(
                parts,
                cwd=self.cwd,
                shell=False,
                capture_output=True,
                text=True,
                timeout=600,
            )
            out = (r.stdout or "") + (r.stderr or "")
            return out[: self._settings.tools.bash_max_output] or f"(exit {r.returncode})"

        return await asyncio.to_thread(_run)

    async def tool_lint(self, path: str = ".") -> str:
        p = self._resolve_path(path)
        if not self._is_under_root(p):
            return "Error: path not allowed"

        def _run() -> str:
            if p.is_file() and p.suffix.lower() == ".py":
                r = subprocess.run(
                    ["ruff", "check", str(p), "--output-format", "concise"],
                    cwd=self.cwd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                return ((r.stdout or "") + (r.stderr or ""))[:8000] or "(ruff ok / no output)"
            if p.is_dir():
                r = subprocess.run(
                    ["ruff", "check", str(p), "--output-format", "concise"],
                    cwd=self.cwd,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                return ((r.stdout or "") + (r.stderr or ""))[:12_000] or "(ruff ok / no output)"
            if p.suffix.lower() in (".ts", ".tsx", ".js", ".jsx"):
                eslint = self._settings.tool_extra.eslint_path
                r = subprocess.run(
                    [eslint, str(p)],
                    cwd=self.cwd,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                return ((r.stdout or "") + (r.stderr or ""))[:12_000] or "(eslint ok / no output)"
            return "lint: use a .py file/dir or .ts/.tsx/.js path; install ruff/eslint as needed."

        return await asyncio.to_thread(_run)

    async def tool_lsp_diagnostics(self, path: str) -> str:
        p = self._resolve_path(path)
        if not self._is_under_root(p):
            return "Error: path not allowed"
        from sayai.tools.lsp_tools import run_lsp_diagnostics

        return await asyncio.to_thread(
            run_lsp_diagnostics,
            p,
            cwd=self.cwd,
            pyright_cmd=self._settings.tool_extra.pyright_command,
        )

    async def tool_vector_search(self, query: str, top_k: int = 8) -> str:
        from sayai.memory.vector import get_vector_memory

        vm = get_vector_memory()
        hits = await vm.search(query, top_k=int(top_k))
        if not hits:
            return "(no vector hits; enable memory.qdrant_enabled and index files)"
        lines = []
        for h in hits:
            lines.append(
                f"score={h.get('score', 0):.4f} path={h.get('path','')}\n{h.get('content','')[:1500]}"
            )
        return "\n---\n".join(lines)

    async def tool_scratch_get(self, key: str) -> str:
        if key in self.shared_scratch:
            return self.shared_scratch[key]
        if self._settings.memory.redis_url:
            from sayai.memory.scratchpad import RedisScratchpad

            v = await RedisScratchpad(self.session_id).hget(key)
            return v if v is not None else "(missing)"
        return "(missing)"

    async def tool_scratch_set(self, key: str, value: str) -> str:
        val = str(value)[:50_000]
        k = str(key)
        self.shared_scratch[k] = val
        if self._settings.memory.redis_url:
            from sayai.memory.scratchpad import RedisScratchpad

            await RedisScratchpad(self.session_id).hset_one(k, val)
        return f"OK: scratch[{key}] set"

    async def tool_mcp_call(self, server: str, tool: str, arguments: dict | None = None) -> str:
        return await self.mcp.call(server, tool, arguments or {})

    async def tool_browser_open(self, url: str) -> str:
        """Alias for fetch_url (blueprint browser / fetch)."""
        return await self.tool_fetch_url(url)
