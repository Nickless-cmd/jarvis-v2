from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def journal_tmp(tmp_path, monkeypatch):
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    monkeypatch.setattr(
        "core.services.creative_journal_runtime.creative_journal_dir",
        lambda: journal_dir,
    )
    return journal_dir


def test_returns_empty_when_no_entries(journal_tmp):
    from core.services.prompt_contract import format_journal_for_heartbeat

    assert format_journal_for_heartbeat() == ""


def test_includes_latest_entry_body(journal_tmp):
    (journal_tmp / "2026-05-10.md").write_text(
        "# Kreativ journal — 2026-05-10\n\nDet stak mig i siden at høre det.\n",
        encoding="utf-8",
    )
    from core.services.prompt_contract import format_journal_for_heartbeat

    out = format_journal_for_heartbeat()
    assert "Det stak mig i siden at høre det." in out
    assert "2026-05-10" in out


def test_truncates_at_300_words(journal_tmp):
    body = " ".join(["ord"] * 500)
    (journal_tmp / "2026-05-10.md").write_text(
        f"# Kreativ journal — 2026-05-10\n\n{body}\n", encoding="utf-8",
    )
    from core.services.prompt_contract import format_journal_for_heartbeat

    out = format_journal_for_heartbeat()
    # Truncated → roughly 300 words plus headers
    body_section = out.split("\n\n", 2)[-1]
    assert len(body_section.split()) <= 305  # 300 + ellipsis tokens slack
    assert "…" in out
