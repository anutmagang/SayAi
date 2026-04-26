from __future__ import annotations

from pathlib import Path

from sayai.cli.hunt_summary import format_hunt_summary_lines
from sayai.config.settings import AppSettings, SkillHunterSettings


def test_hunt_summary_disabled() -> None:
    cfg = AppSettings(skillhunter=SkillHunterSettings(enabled=False))
    lines = format_hunt_summary_lines({"items": 0, "proposed": 0}, Path("/tmp/x"), cfg)
    text = "\n".join(lines).lower()
    assert "mati" in text or "nonaktif" in text
    assert "enabled" in text or "skillhunter" in text


def test_hunt_summary_enabled_with_proposals() -> None:
    cfg = AppSettings(skillhunter=SkillHunterSettings(enabled=True))
    lines = format_hunt_summary_lines({"items": 5, "proposed": 2}, Path("/proj"), cfg)
    text = "\n".join(lines)
    assert "5" in text and "2" in text
    assert "sayai admin" in text.lower() or "admin" in text.lower()


def test_hunt_summary_enabled_no_items() -> None:
    cfg = AppSettings(skillhunter=SkillHunterSettings(enabled=True))
    lines = format_hunt_summary_lines({"items": 0, "proposed": 0}, Path("/proj"), cfg)
    text = "\n".join(lines).lower()
    assert "github" in text or "crawler" in text
