from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from sayai.config import load_config
from sayai.memory.vector import get_vector_memory

logger = logging.getLogger(__name__)

_TEXT_SUFFIXES = {
    ".py",
    ".pyi",
    ".md",
    ".txt",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".css",
    ".html",
    ".rs",
    ".go",
    ".java",
    ".kt",
    ".cs",
    ".sql",
    ".sh",
    ".ps1",
    ".rb",
    ".php",
}


def _should_index(path: Path) -> bool:
    return path.suffix.lower() in _TEXT_SUFFIXES and path.is_file()


def _chunks(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]


async def index_file_content(cwd: Path, rel_or_abs: Path, content: str | None = None) -> None:
    cfg = load_config()
    if not cfg.memory.qdrant_enabled:
        return
    path = rel_or_abs if rel_or_abs.is_absolute() else (cwd / rel_or_abs).resolve()
    if not _should_index(path):
        return
    try:
        body = content if content is not None else path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    vm = get_vector_memory()
    max_c = cfg.memory.index_max_chunk_chars
    try:
        rel = str(path.relative_to(cwd))
    except ValueError:
        rel = str(path)
    for i, chunk in enumerate(_chunks(body, max_c)):
        try:
            await vm.upsert(
                chunk,
                path=rel,
                source="auto_index",
                extra={"chunk": i, "chars": len(chunk)},
            )
        except Exception as e:
            logger.debug("index chunk failed: %s", e)
            return


def schedule_index_file(cwd: Path, path: Path, content: str | None = None) -> None:
    """Fire-and-forget index of a file (best-effort)."""

    async def _run() -> None:
        await index_file_content(cwd, path, content)

    try:
        asyncio.create_task(_run())
    except RuntimeError:
        try:
            asyncio.get_event_loop_policy().get_event_loop().create_task(_run())
        except RuntimeError:
            logger.debug("no event loop for schedule_index_file")


async def index_directory(cwd: Path, *, max_files: int = 500) -> int:
    """Bulk index text files under cwd (CLI / maintenance)."""
    n = 0
    for p in cwd.rglob("*"):
        if n >= max_files:
            break
        if p.is_file() and _should_index(p):
            await index_file_content(cwd, p, None)
            n += 1
    return n
