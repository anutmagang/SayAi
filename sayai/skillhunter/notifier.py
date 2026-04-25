from __future__ import annotations

import json
from pathlib import Path

import httpx

from sayai.config import load_config


class HuntNotifier:
    """Blueprint §12: TUI flag file + optional webhooks from admin.notify."""

    def __init__(self) -> None:
        self._cfg = load_config()

    def _tui_flag_path(self) -> Path:
        p = self._cfg.data_dir / "hunt_notify.txt"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def _log_path(self) -> Path:
        p = self._cfg.data_dir / "hunt_notifications.log"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    async def notify_new_proposal(
        self,
        *,
        name: str,
        skill_id: str,
        score: float,
        source_url: str,
    ) -> None:
        line = f"[proposal] {name} id={skill_id} score={score:.2f} url={source_url}\n"
        self._log_path().open("a", encoding="utf-8").write(line)
        if self._cfg.admin.notify_tui:
            self._tui_flag_path().write_text(line.strip(), encoding="utf-8")

        for entry in self._cfg.admin.notify:
            if not isinstance(entry, dict):
                continue
            if entry.get("type") == "email":
                self._log_path().open("a", encoding="utf-8").write(
                    f"[email-notify-skip] to={entry.get('to', '')}\n"
                )
                continue
            if entry.get("type") != "webhook":
                continue
            url = str(entry.get("url", "")).strip()
            if not url:
                continue
            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    await client.post(
                        url,
                        json={
                            "text": line.strip(),
                            "skill": name,
                            "skill_id": skill_id,
                            "score": score,
                            "source_url": source_url,
                        },
                    )
            except Exception:
                self._log_path().open("a", encoding="utf-8").write(
                    f"[webhook-fail] {url}\n"
                )
