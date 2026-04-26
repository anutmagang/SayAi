from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


def _read_text(path: Path, limit: int = 120_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def _tokens_from_requirements(text: str) -> set[str]:
    out: set[str] = set()
    for line in text.splitlines():
        line = line.strip().split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        # name==1.0 or name>=1
        m = re.match(r"^([a-zA-Z0-9_\-\.]+)", line)
        if m:
            out.add(m.group(1).lower())
    return out


def _tokens_from_pyproject(text: str) -> set[str]:
    out: set[str] = set()
    try:
        import tomllib

        data = tomllib.loads(text)
    except Exception:
        # fallback: crude [project] deps line scan
        for m in re.finditer(r'^\s*["\']?([a-zA-Z0-9_\-\.]+)["\']?\s*=', text, re.MULTILINE):
            out.add(m.group(1).lower())
        return out

    proj = data.get("project") or {}
    for key in ("dependencies", "optional-dependencies"):
        block = proj.get(key)
        if isinstance(block, list):
            for dep in block:
                if isinstance(dep, str):
                    m = re.match(r"^([a-zA-Z0-9_\-\.]+)", dep.strip())
                    if m:
                        out.add(m.group(1).lower())
        elif isinstance(block, dict):
            for _group, deps in block.items():
                if isinstance(deps, list):
                    for dep in deps:
                        if isinstance(dep, str):
                            m = re.match(r"^([a-zA-Z0-9_\-\.]+)", dep.strip())
                            if m:
                                out.add(m.group(1).lower())
    tool = data.get("tool") or {}
    uv = tool.get("uv") if isinstance(tool, dict) else None
    if isinstance(uv, dict):
        dev = uv.get("dev-dependencies")
        if isinstance(dev, list):
            for dep in dev:
                if isinstance(dep, str):
                    m = re.match(r"^([a-zA-Z0-9_\-\.]+)", dep.strip())
                    if m:
                        out.add(m.group(1).lower())
    return out


def _tokens_from_package_json(text: str) -> set[str]:
    out: set[str] = set()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return out
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        block = data.get(key)
        if isinstance(block, dict):
            for name in block:
                out.add(str(name).lower())
    return out


@dataclass
class StackProfile:
    """Lightweight signals from repo root for SkillHunter ranking."""

    tokens: frozenset[str] = field(default_factory=frozenset)
    summary: str = ""

    @classmethod
    def detect(cls, root: Path) -> StackProfile:
        root = root.resolve()
        tokens: set[str] = set()

        pp = root / "pyproject.toml"
        if pp.is_file():
            try:
                raw = pp.read_text(encoding="utf-8", errors="replace")[:400_000]
            except OSError:
                raw = ""
            tokens |= _tokens_from_pyproject(raw)

        req = root / "requirements.txt"
        if req.is_file():
            tokens |= _tokens_from_requirements(_read_text(req))

        pkg = root / "package.json"
        if pkg.is_file():
            tokens |= _tokens_from_package_json(_read_text(pkg))

        # normalise noise
        noise = {"", "true", "false", "null", "name", "version", "description"}
        tokens = {t for t in tokens if t and t not in noise and len(t) > 1}

        parts: list[str] = []
        if (root / "pyproject.toml").is_file() or (root / "requirements.txt").is_file():
            py_toks = sorted(t for t in tokens if t in tokens and not t.startswith("@"))[:12]
            if py_toks:
                parts.append("Python-ish: " + ", ".join(py_toks))
        if (root / "package.json").is_file():
            js_toks = sorted(tokens)[:12]
            if js_toks:
                parts.append("Node/JS deps: " + ", ".join(js_toks))
        summary = " | ".join(parts) if parts else "No strong stack signal (missing pyproject/package.json)."
        return cls(tokens=frozenset(tokens), summary=summary)


def stack_relevance_boost(item_name: str, description: str, url: str, profile: StackProfile) -> float:
    """Small additive boost when crawl item text overlaps repo stack tokens."""
    if not profile.tokens:
        return 0.0
    hay = f"{item_name} {description} {url}".lower()
    gain = 0.0
    for tok in profile.tokens:
        if len(tok) < 3:
            continue
        if tok in hay:
            gain += 0.06
    return min(0.24, gain)
