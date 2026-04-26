"""Human-readable terminal output for ``sayai hunt``."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from sayai.config import AppSettings


def format_hunt_summary_lines(stats: dict[str, int], root: Path, cfg: AppSettings) -> list[str]:
    """Build plain lines (Rich markup allowed) for the hunt result panel."""
    items = int(stats.get("items", 0))
    proposed = int(stats.get("proposed", 0))
    sh = cfg.skillhunter
    lines: list[str] = []

    if not sh.enabled:
        lines.append("[yellow]SkillHunter mati[/yellow] di konfigurasi ([dim]skillhunter.enabled: false[/dim]).")
        lines.append("")
        lines.append("Aktifkan lalu jalankan ulang, misalnya:")
        lines.append("  • Di [bold]~/.config/sayai/settings.yaml[/bold] → blok [cyan]skillhunter:[/cyan] dengan [cyan]enabled: true[/cyan]")
        lines.append("  • Atau env: [cyan]SAYAI_SKILLHUNTER__ENABLED=true[/cyan]")
        return lines

    lines.append("[bold]Ringkasan[/bold]")
    lines.append(f"  • Kandidat unik setelah crawl: [cyan]{items}[/cyan]")
    lines.append(f"  • Proposal [yellow]pending[/yellow] baru ditulis: [green]{proposed}[/green]")
    lines.append(f"  • Folder deteksi stack: [dim]{root}[/dim]")

    if items == 0:
        lines.append("")
        lines.append("[dim]Crawler tidak mengembalikan item. Yang bisa dicek:[/dim]")
        lines.append("  • Koneksi keluar; untuk GitHub: set [cyan]GITHUB_TOKEN[/cyan] di .env (hindari batas rate / 403).")
        lines.append("  • [cyan]skillhunter.mcp_registry_url[/cyan] kosong → sumber MCP dilewati.")
        lines.append("  • Sumber opsional: [cyan]clawhub_enabled[/cyan], [cyan]awesome_enabled[/cyan], [cyan]autoskills_map_enabled[/cyan] di YAML.")
    elif proposed == 0:
        lines.append("")
        lines.append("[dim]Ada kandidat, tetapi tidak ada proposal baru. Umumnya:[/dim]")
        lines.append("  • URL sudah pernah tercatat, skor di bawah min_score, atau ditolak analyzer (LLM / safety).")
        lines.append(f"  • [dim]min_score={sh.min_score}[/dim] · [dim]max_proposals_per_run={sh.max_proposals_per_run}[/dim]")
        lines.append("  • Pastikan API key di [bold]~/.config/sayai/.env[/bold] valid untuk model analyzer.")
    else:
        lines.append("")
        lines.append("[green]Berikutnya:[/green] buka [bold]sayai admin[/bold], ketik [bold]list[/bold], lalu [bold]show[/bold] / [bold]approve[/bold] / [bold]reject[/bold].")

    return lines


def print_hunt_summary(stats: dict[str, int], root: Path, cfg: AppSettings) -> None:
    """Print a bordered summary to the terminal (Rich)."""
    lines = format_hunt_summary_lines(stats, root, cfg)
    console = Console()
    subtitle = "sayai admin → tinjau proposal"
    console.print(
        Panel(
            "\n".join(lines),
            title="SayAi · SkillHunter",
            subtitle=subtitle,
            border_style="cyan",
            padding=(1, 2),
        )
    )
