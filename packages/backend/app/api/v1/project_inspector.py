from __future__ import annotations

from pathlib import Path
import subprocess

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.db.models.user import User

router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parents[5]
BACKEND_ROOT = Path(__file__).resolve().parents[3]
MAX_DEPTH = 3


class TreeEntry(BaseModel):
    path: str
    name: str
    kind: str


class ProjectSnapshotOut(BaseModel):
    root: str
    cwd: str
    tree: list[TreeEntry]
    changed: list[dict[str, str]]


class ProjectFileOut(BaseModel):
    path: str
    size: int
    truncated: bool
    content: str


def _safe_path(rel_path: str) -> Path:
    if rel_path in ("", ".", "/"):
        return PROJECT_ROOT
    candidate = (PROJECT_ROOT / rel_path).resolve()
    if PROJECT_ROOT not in candidate.parents and candidate != PROJECT_ROOT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path must stay inside project root",
        )
    return candidate


def _is_text_file(path: Path) -> bool:
    binary_suffixes = {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".ico",
        ".pdf",
        ".zip",
        ".gz",
        ".tar",
        ".exe",
        ".dll",
        ".so",
        ".woff",
        ".woff2",
        ".ttf",
    }
    return path.suffix.lower() not in binary_suffixes


def _status_label(code: str) -> str:
    if "A" in code:
        return "added"
    if "D" in code:
        return "deleted"
    if "R" in code:
        return "renamed"
    if "M" in code:
        return "modified"
    if "??" in code:
        return "untracked"
    return "changed"


def _git_changed_files() -> list[dict[str, str]]:
    proc = subprocess.run(
        ["git", "-C", str(PROJECT_ROOT), "status", "--porcelain"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return []

    out: list[dict[str, str]] = []
    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        code = line[:2].strip() or "??"
        path_part = line[3:].strip()
        if " -> " in path_part:
            path_part = path_part.split(" -> ", maxsplit=1)[1].strip()
        out.append({"status": _status_label(code), "path": path_part})
    return out


def _list_tree(base: Path, depth: int) -> list[TreeEntry]:
    if depth < 1 or depth > MAX_DEPTH:
        depth = 2

    entries: list[TreeEntry] = []
    queue: list[tuple[Path, int]] = [(base, 0)]
    blocked = {".git", ".venv", "node_modules", "__pycache__", ".next"}

    while queue:
        parent, level = queue.pop(0)
        try:
            children = sorted(parent.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            continue

        for child in children:
            if child.name in blocked:
                continue
            rel = child.relative_to(PROJECT_ROOT).as_posix()
            kind = "dir" if child.is_dir() else "file"
            entries.append(TreeEntry(path=rel, name=child.name, kind=kind))
            if child.is_dir() and level + 1 < depth:
                queue.append((child, level + 1))
    return entries


@router.get("/project/snapshot", response_model=ProjectSnapshotOut)
def project_snapshot(
    path: str = Query(default="", description="Relative path from project root"),
    depth: int = Query(default=2, ge=1, le=MAX_DEPTH),
    _user: User = Depends(get_current_user),
) -> ProjectSnapshotOut:
    base = _safe_path(path)
    if not base.exists() or not base.is_dir():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Directory not found")

    return ProjectSnapshotOut(
        root=PROJECT_ROOT.as_posix(),
        cwd=base.relative_to(PROJECT_ROOT).as_posix() if base != PROJECT_ROOT else ".",
        tree=_list_tree(base, depth),
        changed=_git_changed_files(),
    )


@router.get("/project/file", response_model=ProjectFileOut)
def project_file(
    path: str = Query(..., description="Relative file path from project root"),
    max_chars: int = Query(default=12000, ge=200, le=50000),
    _user: User = Depends(get_current_user),
) -> ProjectFileOut:
    file_path = _safe_path(path)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    if not _is_text_file(file_path):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Binary file preview is not supported")

    text = file_path.read_text(encoding="utf-8", errors="replace")
    truncated = len(text) > max_chars
    if truncated:
        text = text[:max_chars]
    return ProjectFileOut(
        path=file_path.relative_to(PROJECT_ROOT).as_posix(),
        size=file_path.stat().st_size,
        truncated=truncated,
        content=text,
    )

