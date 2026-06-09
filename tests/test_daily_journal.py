"""Tests for daily journal synthesizer."""
from __future__ import annotations

import unittest.mock as mock
from datetime import UTC, date, datetime
from pathlib import Path


def test_journal_exists_returns_false_for_fresh_day(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "core.services.daily_journal.OBSERVATION_DIR", tmp_path / "obs"
    )
    from core.services.daily_journal import journal_exists_for
    assert journal_exists_for(date(2026, 6, 9)) is False


def test_journal_exists_returns_true_when_file_present(tmp_path, monkeypatch) -> None:
    obs = tmp_path / "obs"
    obs.mkdir()
    (obs / "2026-06-09-daily.md").write_text("existing", encoding="utf-8")
    monkeypatch.setattr("core.services.daily_journal.OBSERVATION_DIR", obs)
    from core.services.daily_journal import journal_exists_for
    assert journal_exists_for(date(2026, 6, 9)) is True


def test_synthesize_skips_when_journal_exists(tmp_path, monkeypatch) -> None:
    obs = tmp_path / "obs"
    obs.mkdir()
    (obs / "2026-06-09-daily.md").write_text("existing", encoding="utf-8")
    monkeypatch.setattr("core.services.daily_journal.OBSERVATION_DIR", obs)
    from core.services.daily_journal import synthesize_daily_journal
    result = synthesize_daily_journal(date(2026, 6, 9))
    assert result["status"] == "skipped"


def test_synthesize_returns_no_content_when_empty(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "core.services.daily_journal.OBSERVATION_DIR", tmp_path / "obs"
    )
    monkeypatch.setattr(
        "core.services.daily_journal._fetch_chat_pairs_for_day", lambda d, limit=80: []
    )
    monkeypatch.setattr(
        "core.services.daily_journal._fetch_brain_carries_for_day", lambda d, limit=20: []
    )
    from core.services.daily_journal import synthesize_daily_journal
    result = synthesize_daily_journal(date(2026, 6, 9))
    assert result["status"] == "no-content"


def test_synthesize_writes_journal_with_llm_output(tmp_path, monkeypatch) -> None:
    obs = tmp_path / "obs"
    monkeypatch.setattr("core.services.daily_journal.OBSERVATION_DIR", obs)
    monkeypatch.setattr(
        "core.services.daily_journal._fetch_chat_pairs_for_day",
        lambda d, limit=80: [
            {"role": "user", "content": "Hej Jarvis", "created_at": "2026-06-09T08:00:00Z"},
            {"role": "assistant", "content": "Hej Bjørn, hvad sker der i dag?",
             "created_at": "2026-06-09T08:00:05Z"},
        ],
    )
    monkeypatch.setattr(
        "core.services.daily_journal._fetch_brain_carries_for_day",
        lambda d, limit=20: [],
    )
    fake_synthesis = "# Dagens overskrift\n\nI dag startede vi med at fikse memory-pipen..."
    with mock.patch(
        "core.context.compact_llm.call_compact_llm",
        return_value=fake_synthesis,
    ):
        from core.services.daily_journal import synthesize_daily_journal
        result = synthesize_daily_journal(date(2026, 6, 9))

    assert result["status"] == "written"
    written_path = Path(result["path"])
    assert written_path.exists()
    content = written_path.read_text(encoding="utf-8")
    assert "Daily journal — 2026-06-09" in content
    assert "Dagens overskrift" in content
    assert "memory-pipen" in content


def test_synthesize_handles_llm_failure(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "core.services.daily_journal.OBSERVATION_DIR", tmp_path / "obs"
    )
    monkeypatch.setattr(
        "core.services.daily_journal._fetch_chat_pairs_for_day",
        lambda d, limit=80: [{"role": "user", "content": "x" * 50, "created_at": "x"}],
    )
    monkeypatch.setattr(
        "core.services.daily_journal._fetch_brain_carries_for_day",
        lambda d, limit=20: [],
    )
    with mock.patch(
        "core.context.compact_llm.call_compact_llm",
        side_effect=RuntimeError("provider down"),
    ):
        from core.services.daily_journal import synthesize_daily_journal
        result = synthesize_daily_journal(date(2026, 6, 9))
    assert result["status"] == "error"


def test_synthesize_rejects_empty_llm_output(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "core.services.daily_journal.OBSERVATION_DIR", tmp_path / "obs"
    )
    monkeypatch.setattr(
        "core.services.daily_journal._fetch_chat_pairs_for_day",
        lambda d, limit=80: [{"role": "user", "content": "x" * 50, "created_at": "x"}],
    )
    monkeypatch.setattr(
        "core.services.daily_journal._fetch_brain_carries_for_day",
        lambda d, limit=20: [],
    )
    with mock.patch(
        "core.context.compact_llm.call_compact_llm",
        return_value="",
    ):
        from core.services.daily_journal import synthesize_daily_journal
        result = synthesize_daily_journal(date(2026, 6, 9))
    assert result["status"] == "error"


def test_should_synthesize_now_outside_window(monkeypatch) -> None:
    """Før kl. 22 lokal tid → ikke synthesize."""
    from core.services.daily_journal import _should_synthesize_now
    # Mock journal_exists_for to ensure it's the time-check that gates
    monkeypatch.setattr(
        "core.services.daily_journal.journal_exists_for", lambda d: False
    )
    morning = datetime(2026, 6, 9, 10, 0)
    assert _should_synthesize_now(morning) is False


def test_should_synthesize_now_inside_window(monkeypatch) -> None:
    """Efter kl. 22 lokal tid + ingen journal → synthesize."""
    from core.services.daily_journal import _should_synthesize_now
    monkeypatch.setattr(
        "core.services.daily_journal.journal_exists_for", lambda d: False
    )
    evening = datetime(2026, 6, 9, 23, 0)
    assert _should_synthesize_now(evening) is True


def test_should_synthesize_now_skipped_when_journal_exists(monkeypatch) -> None:
    """Efter kl. 22 men journal findes → no-op."""
    from core.services.daily_journal import _should_synthesize_now
    monkeypatch.setattr(
        "core.services.daily_journal.journal_exists_for", lambda d: True
    )
    evening = datetime(2026, 6, 9, 23, 0)
    assert _should_synthesize_now(evening) is False


def test_start_stop_idempotent() -> None:
    from core.services import daily_journal as mod
    mod.stop_daily_journal_daemon()
    mod._daemon_thread = None

    mod.start_daily_journal_daemon()
    t1 = mod._daemon_thread
    assert t1 is not None

    mod.start_daily_journal_daemon()
    t2 = mod._daemon_thread
    assert t2 is t1

    mod.stop_daily_journal_daemon()
