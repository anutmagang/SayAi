from __future__ import annotations

import asyncio
from pathlib import Path

import click


@click.group()
@click.version_option()
def cli() -> None:
    """SayAi — AI agentic coding platform."""


@cli.command("tui")
@click.option("--cwd", type=click.Path(path_type=Path), default=None, help="Working directory for tools")
@click.option("--simple", is_flag=True, help="Single CoderAgent only (no planner/DAG).")
def tui_cmd(cwd: Path | None, simple: bool) -> None:
    """Open the Textual TUI."""
    from sayai.cli.app import run_tui

    run_tui(cwd=cwd or Path.cwd(), use_dag=False if simple else None)


@cli.group()
def db() -> None:
    """Database commands."""


@db.command("init")
def db_init() -> None:
    """Create SQLite tables under the configured data directory."""

    async def _go() -> None:
        from sayai.db import init_db

        await init_db()

    asyncio.run(_go())
    from sayai.db import db_path

    click.echo(f"Database ready at {db_path()}")


@cli.command("hunt")
@click.option(
    "--cwd",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=None,
    help="Project root for stack detection (pyproject.toml, package.json).",
)
def hunt_cmd(cwd: Path | None) -> None:
    """Run SkillHunter crawlers + analyzer + rewriter (writes pending proposals)."""

    async def _go() -> None:
        from sayai.skillhunter import SkillHunter

        stats = await SkillHunter().hunt(cwd=cwd)
        click.echo(f"SkillHunter done: {stats}")

    asyncio.run(_go())


@cli.command("admin")
def admin_cmd() -> None:
    """Open admin TUI to approve/reject skill proposals."""
    from sayai.cli.admin import run_admin

    run_admin()


@cli.command("index")
@click.option("--cwd", type=click.Path(path_type=Path), default=".", help="Root to scan")
@click.option("--max-files", default=400, show_default=True)
def index_codebase(cwd: Path, max_files: int) -> None:
    """Bulk-index text files into Qdrant (requires memory.qdrant_enabled)."""

    async def _go() -> None:
        from pathlib import Path

        from sayai.memory.indexer import index_directory

        root = cwd.resolve()
        n = await index_directory(root, max_files=max_files)
        click.echo(f"Indexed up to {n} files under {root}")

    asyncio.run(_go())


@cli.command("run")
@click.argument("task")
@click.option("--cwd", type=click.Path(path_type=Path), default=None)
@click.option(
    "--simple",
    is_flag=True,
    help="Skip planner/DAG; run a single CoderAgent only.",
)
def run_task(task: str, cwd: Path | None, simple: bool) -> None:
    """Run a single task non-interactively (streams to stdout)."""

    async def _go() -> None:
        from sayai.orchestrator import Orchestrator

        orch = Orchestrator(cwd=cwd or Path.cwd(), use_dag=False if simple else None)
        async for chunk in orch.stream(task):
            click.echo(chunk, nl=False)
        click.echo()

    asyncio.run(_go())


@cli.command("server")
@click.option("--host", default=None, help="Override settings.server.host")
@click.option("--port", default=None, type=int, help="Override settings.server.port")
def server_cmd(host: str | None, port: int | None) -> None:
    """Run a tiny HTTP server with GET /health for probes (VPS / k8s style)."""

    from sayai.config import load_config
    from sayai.server.health import run_health_server

    cfg = load_config()
    h = host or cfg.server.host
    p = port or cfg.server.port
    click.echo(f"[sayai] Health: http://{h}:{p}/health (Ctrl+C to stop)")
    asyncio.run(run_health_server(h, p))


@cli.group()
def session() -> None:
    """Session helpers (export placeholder for future transcript sharing)."""


@session.command("export")
@click.option(
    "--out",
    type=click.Path(path_type=Path, dir_okay=False, writable=True),
    default=None,
    help="Output JSON path (default: under data_dir/sessions/).",
)
def session_export(out: Path | None) -> None:
    """Write a small JSON stub; extend later with TUI transcript or Redis snapshot."""

    import json
    import time
    import uuid

    from sayai.config import load_config

    cfg = load_config()
    dest = out or (cfg.data_dir / "sessions" / f"{uuid.uuid4().hex}.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "exported_at": time.time(),
        "note": "Placeholder: attach TUI transcript or scratchpad keys in a future release.",
    }
    dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    click.echo(str(dest))


@cli.command("plugins")
def plugins_list() -> None:
    """List optional drop-in Python files under data_dir/plugins/*.py."""

    from sayai.config import load_config

    cfg = load_config()
    d = cfg.data_dir / "plugins"
    d.mkdir(parents=True, exist_ok=True)
    files = sorted(d.glob("*.py"))
    if not files:
        click.echo(f"No .py plugins in {d}")
        return
    for f in files:
        click.echo(str(f))


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
