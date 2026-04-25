from __future__ import annotations

import difflib

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static

from sayai.db.skill_store import SkillStore


class AdminApp(App):
    """TUI for reviewing SkillHunter proposals (blueprint §12)."""

    CSS = """
    #out { height: 1fr; border: solid $boost; }
    #cmd { dock: bottom; }
    #hint { height: auto; color: $text-muted; }
    """

    BINDINGS = [("ctrl+c", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical():
            yield Static(
                "Commands: list | approve <id> | reject <id> <reason> | show <id> | "
                "versions <id> | diff <id> | help | quit",
                id="hint",
            )
            yield RichLog(id="out", highlight=True, markup=True, wrap=True)
        yield Input(placeholder="admin> ", id="cmd")
        yield Footer()

    def on_mount(self) -> None:
        self._store = SkillStore()
        self.query_one("#out", RichLog).write("[bold]SayAi Admin[/bold] — type `list` to load pending skills.")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        line = event.value.strip()
        self.query_one("#cmd", Input).value = ""
        if not line:
            return
        await self._dispatch(line)

    async def _dispatch(self, line: str) -> None:
        log = self.query_one("#out", RichLog)
        parts = line.split(maxsplit=2)
        cmd = parts[0].lower()
        try:
            if cmd in ("quit", "exit", "q"):
                self.exit()
            elif cmd == "help":
                log.write(
                    "[bold]help[/bold]\n"
                    "list — pending proposals\n"
                    "show <id> — SKILL.md body preview\n"
                    "diff <id> — unified diff vs empty (structure check)\n"
                    "versions <id> — version history rows\n"
                    "approve <id> — mark approved (optional: edit content via show + future export)\n"
                    "reject <id> <reason> — reject with reason\n"
                )
            elif cmd == "list":
                rows = await self._store.list_by_status("pending")
                if not rows:
                    log.write("(no pending proposals)")
                    return
                for r in rows:
                    log.write(
                        f"[cyan]{r['id']}[/cyan]  score={r.get('score')}  "
                        f"lic={r.get('license')}  [yellow]{r.get('name')}[/yellow]"
                    )
            elif cmd == "show" and len(parts) >= 2:
                row = await self._store.get(parts[1])
                if not row:
                    log.write("not found")
                    return
                body = str(row.get("content") or "")
                log.write(body[:25_000] + ("…" if len(body) > 25_000 else ""))
            elif cmd == "diff" and len(parts) >= 2:
                row = await self._store.get(parts[1])
                if not row:
                    log.write("not found")
                    return
                body = str(row.get("content") or "")
                lines = body.splitlines()
                diff = "\n".join(
                    difflib.unified_diff(
                        [""],
                        lines,
                        fromfile="empty",
                        tofile="proposal",
                        lineterm="",
                    )
                )
                log.write(diff[:20_000] or "(no diff)")
            elif cmd == "versions" and len(parts) >= 2:
                vers = await self._store.list_versions(parts[1])
                if not vers:
                    log.write("(no versions)")
                    return
                for v in vers:
                    log.write(
                        f"rev={v.get('revision')} action={v.get('action')} "
                        f"at={v.get('created_at')} len={len(str(v.get('content') or ''))}"
                    )
            elif cmd == "approve" and len(parts) >= 2:
                await self._store.approve(parts[1], approved_by="tui-admin")
                log.write(f"approved {parts[1]}")
            elif cmd == "reject" and len(parts) >= 3:
                await self._store.reject(parts[1], parts[2], by="tui-admin")
                log.write(f"rejected {parts[1]}")
            elif cmd == "reject":
                log.write("usage: reject <id> <reason>")
            else:
                log.write(f"unknown command: {line}")
        except Exception as e:
            log.write(f"[red]error[/red] {e!s}")

    async def action_quit(self) -> None:
        self.exit()


def run_admin() -> None:
    AdminApp().run()
