from __future__ import annotations

from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static

from sayai.orchestrator import Orchestrator


class SayAiApp(App):
    CSS = """
    #output {
        height: 1fr;
        border: solid $boost;
        background: $surface;
    }
    #prompt {
        dock: bottom;
    }
    #hint {
        height: auto;
        color: $text-muted;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
    ]

    def __init__(self, *, cwd: Path | None = None, use_dag: bool | None = None):
        super().__init__()
        self._cwd = cwd or Path.cwd()
        self._use_dag = use_dag

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical():
            yield Static(
                "SayAi — task or /help, /quit | sayai admin | sayai hunt",
                id="hint",
            )
            yield RichLog(id="output", highlight=True, markup=True, wrap=True)
        yield Input(placeholder="Task or /command …", id="prompt")
        yield Footer()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip()
        inp = self.query_one("#prompt", Input)
        inp.value = ""
        if not raw:
            return
        if raw.startswith("/"):
            await self._handle_slash(raw)
            return
        self.run_task(raw)

    @work(exclusive=True)
    async def run_task(self, task: str) -> None:
        log = self.query_one("#output", RichLog)
        log.write(f"[bold]You:[/bold] {task}")
        orch = Orchestrator(cwd=self._cwd, use_dag=self._use_dag)
        try:
            async for chunk in orch.stream(task):
                log.write(chunk)
        except Exception as e:
            log.write(f"[red]Error:[/red] {e!s}")

    async def _handle_slash(self, line: str) -> None:
        log = self.query_one("#output", RichLog)
        parts = line.split(maxsplit=1)
        cmd = parts[0].lower()
        if cmd in ("/quit", "/exit"):
            self.exit()
        elif cmd == "/help":
            log.write(
                "[bold]Commands[/bold]\n"
                "/help — this message\n"
                "/quit — exit\n"
                "/cwd — show working directory\n"
                "Anything else is sent to the CoderAgent (needs API keys; see .env.example).\n"
            )
        elif cmd == "/cwd":
            log.write(f"cwd: {self._cwd}")
        else:
            log.write(f"Unknown command: {cmd}. Try /help.")

    async def action_quit(self) -> None:
        self.exit()


def run_tui(*, cwd: Path | None = None, use_dag: bool | None = None) -> None:
    app = SayAiApp(cwd=cwd, use_dag=use_dag)
    app.run()
