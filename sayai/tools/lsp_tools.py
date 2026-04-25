from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def run_lsp_diagnostics(path: Path, *, cwd: Path, pyright_cmd: str) -> str:
    """Best-effort diagnostics via pyright/basedpyright JSON or ruff JSON."""
    if not path.is_file():
        return "Error: path is not a file"
    suf = path.suffix.lower()
    if suf == ".py":
        exe = shutil.which(pyright_cmd.split()[0]) if pyright_cmd else None
        if exe or shutil.which("pyright"):
            cmd = pyright_cmd.split() if exe else ["pyright"]
            cmd = [*cmd, "--outputjson", str(path)]
            try:
                r = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=cwd,
                )
                raw = (r.stdout or r.stderr or "").strip()
                if raw.startswith("{"):
                    data = json.loads(raw)
                    return _format_pyright_json(data)
                return raw[:8000] or f"(pyright exit {r.returncode})"
            except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
                return f"pyright failed: {e}; trying ruff…\n" + _ruff_json(path, cwd)
        return _ruff_json(path, cwd)
    if suf in (".ts", ".tsx", ".js", ".jsx"):
        eslint = shutil.which("npx")
        if eslint:
            r = subprocess.run(
                ["npx", "--yes", "eslint", str(path), "-f", "json"],
                capture_output=True,
                text=True,
                timeout=180,
                cwd=cwd,
            )
            if r.stdout:
                try:
                    data = json.loads(r.stdout)
                    return json.dumps(data, indent=2)[:12_000]
                except json.JSONDecodeError:
                    return r.stdout[:12_000]
        return "No eslint in PATH / npx; install devDependencies or use IDE LSP."
    return f"No built-in LSP runner for {suf}; use lint() on project roots."


def _ruff_json(path: Path, cwd: Path) -> str:
    ru = shutil.which("ruff")
    if not ru:
        return "Neither pyright nor ruff found on PATH."
    r = subprocess.run(
        ["ruff", "check", str(path), "--output-format", "json"],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=cwd,
    )
    return (r.stdout or r.stderr or "(no ruff output)")[:12_000]


def _format_pyright_json(data: dict) -> str:
    lines: list[str] = []
    general = data.get("generalDiagnostics") or data.get("diagnostics") or []
    for d in general[:80]:
        msg = d.get("message", d)
        sev = d.get("severity", "")
        rng = d.get("range") or {}
        lines.append(f"{sev}: {msg} @ {rng}")
    return "\n".join(lines) if lines else json.dumps(data, indent=2)[:12_000]
