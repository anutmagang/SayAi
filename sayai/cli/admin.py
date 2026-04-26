from __future__ import annotations

import difflib

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static

from sayai.db.skill_store import SkillStore


class AdminApp(App):
    """TUI for reviewing SkillHunter proposals (blueprint §12)."""

    TITLE = "SayAi Admin"
    SUB_TITLE = "Persetujuan skill hasil SkillHunter"

    CSS = """
    #out { height: 1fr; border: solid $boost; }
    #cmd { dock: bottom; }
    #hint { height: auto; color: $text-muted; padding: 0 1; }
    """

    BINDINGS = [("ctrl+c", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical():
            yield Static(
                "[bold]Apa ini?[/bold] Proposal skill dari [cyan]sayai hunt[/cyan] status [yellow]pending[/yellow] "
                "— Anda tinjau lalu setujui atau tolak.\n"
                "[bold]Alur singkat:[/bold] [cyan]list[/cyan] → pilih id → [cyan]show[/cyan] <id> → "
                "[cyan]approve[/cyan] <id> atau [cyan]reject[/cyan] <id> <alasan>\n"
                "[dim]Perintah lain: diff, versions, help, quit[/dim]",
                id="hint",
            )
            yield RichLog(id="out", highlight=True, markup=True, wrap=True)
        yield Input(placeholder="Ketik perintah lalu Enter…", id="cmd")
        yield Footer()

    def on_mount(self) -> None:
        self._store = SkillStore()
        log = self.query_one("#out", RichLog)
        log.write(
            "[bold green]Selamat datang[/bold green] — panel admin skill SayAi.\n"
            "Ketik [bold]list[/bold] untuk melihat antrean [yellow]pending[/yellow]. "
            "Ketik [bold]help[/bold] untuk penjelasan tiap perintah.\n"
        )

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
                    "[bold]Daftar perintah[/bold]\n"
                    "[cyan]list[/cyan] — tampilkan semua proposal [yellow]pending[/yellow] (belum disetujui).\n"
                    "[cyan]show[/cyan] <id> — pratinjau isi SKILL.md untuk id tersebut.\n"
                    "[cyan]diff[/cyan] <id> — diff ringkas (cek struktur).\n"
                    "[cyan]versions[/cyan] <id> — riwayat revisi di database.\n"
                    "[cyan]approve[/cyan] <id> — setujui; skill bisa dipakai agen (sesuai pengaturan load approved).\n"
                    "[cyan]reject[/cyan] <id> <alasan> — tolak proposal (alasan wajib).\n"
                    "[cyan]quit[/cyan] — keluar.\n"
                    "[dim]Tip: salin [bold]id[/bold] persis seperti di kolom pertama hasil list.[/dim]"
                )
            elif cmd == "list":
                rows = await self._store.list_by_status("pending")
                if not rows:
                    log.write(
                        "[yellow]Tidak ada proposal pending.[/yellow]\n"
                        "[dim]Jalankan [bold]sayai hunt[/bold] (dengan SkillHunter aktif di YAML) untuk mengisi antrean.[/dim]"
                    )
                    return
                log.write(f"[bold]Proposal pending: {len(rows)}[/bold] (salin [cyan]id[/cyan] untuk show / approve / reject)\n")
                for r in rows:
                    log.write(
                        f"  [cyan]{r['id']}[/cyan]  skor={r.get('score')}  "
                        f"lisensi={r.get('license')}  [yellow]{r.get('name')}[/yellow]"
                    )
            elif cmd == "show" and len(parts) >= 2:
                row = await self._store.get(parts[1])
                if not row:
                    log.write(f"[red]Tidak ditemukan:[/red] {parts[1]}")
                    return
                body = str(row.get("content") or "")
                log.write(f"[dim]Pratinjau {parts[1]} ({len(body)} karakter)[/dim]\n")
                log.write(body[:25_000] + ("…" if len(body) > 25_000 else ""))
            elif cmd == "diff" and len(parts) >= 2:
                row = await self._store.get(parts[1])
                if not row:
                    log.write(f"[red]Tidak ditemukan:[/red] {parts[1]}")
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
                    log.write("[dim](Belum ada riwayat versi untuk id ini)[/dim]")
                    return
                for v in vers:
                    log.write(
                        f"rev={v.get('revision')} action={v.get('action')} "
                        f"at={v.get('created_at')} len={len(str(v.get('content') or ''))}"
                    )
            elif cmd == "approve" and len(parts) >= 2:
                await self._store.approve(parts[1], approved_by="tui-admin")
                log.write(f"[green]Disetujui[/green] — [cyan]{parts[1]}[/cyan] sekarang [bold]approved[/bold].")
            elif cmd == "reject" and len(parts) >= 3:
                await self._store.reject(parts[1], parts[2], by="tui-admin")
                log.write(f"[yellow]Ditolak[/yellow] — [cyan]{parts[1]}[/cyan] (alasan tercatat).")
            elif cmd == "reject":
                log.write("[red]Format salah.[/red] Contoh: [bold]reject[/bold] [cyan]sai_1[/cyan] [dim]terlalu spesifik untuk proyek kami[/dim]")
            else:
                log.write(f"[red]Perintah tidak dikenal:[/red] {line}\n[dim]Ketik [bold]help[/bold] untuk daftar perintah.[/dim]")
        except Exception as e:
            log.write(f"[red]error[/red] {e!s}")

    async def action_quit(self) -> None:
        self.exit()


def run_admin() -> None:
    AdminApp().run()
