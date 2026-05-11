from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest


@pytest.fixture()
def events_table(tmp_path, monkeypatch):
    import sqlite3

    db_path = tmp_path / "events.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE events (id INTEGER PRIMARY KEY, kind TEXT, payload_json TEXT, created_at TEXT)"
    )

    def fake_connect():
        c = sqlite3.connect(str(db_path))
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr("core.runtime.db.connect", fake_connect)
    return conn


def test_fetch_broken_decisions_returns_recent_events(events_table):
    now = datetime.now(UTC)
    events_table.execute(
        "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, ?)",
        ("decision_revoked", json.dumps({"reason": "vi tog det forkerte valg"}), now.isoformat()),
    )
    events_table.execute(
        "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, ?)",
        ("conflict.detected", json.dumps({"description": "uoverensstemmelse om scope"}),
         (now - timedelta(days=2)).isoformat()),
    )
    # Old event → outside 7-day window
    events_table.execute(
        "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, ?)",
        ("decision_revoked", json.dumps({"reason": "gammel sag"}),
         (now - timedelta(days=14)).isoformat()),
    )
    events_table.commit()

    from core.services.creative_journal_runtime import _fetch_broken_decisions

    out = _fetch_broken_decisions()
    assert len(out) == 2
    assert any("forkerte valg" in s for s in out)
    assert all("gammel sag" not in s for s in out)


def test_fetch_affective_klangbraet_present_keys():
    from core.services.creative_journal_runtime import _fetch_affective_klangbraet

    out = _fetch_affective_klangbraet()
    assert isinstance(out, dict)
    assert set(out.keys()) == {"dream_bias", "user_temperature", "current_pull"}


def test_should_skip_week_when_corpus_thin():
    from core.services.creative_journal_runtime import _should_skip_week

    skip, reason = _should_skip_week(
        chronicle_count=1,
        broken_decisions_count=0,
        life_projects_count=0,
    )
    assert skip is True
    assert "thin" in reason.lower() or "skip" in reason.lower()


def test_should_not_skip_when_any_signal_present():
    from core.services.creative_journal_runtime import _should_skip_week

    skip, _ = _should_skip_week(
        chronicle_count=2,
        broken_decisions_count=0,
        life_projects_count=0,
    )
    assert skip is False

    skip2, _ = _should_skip_week(
        chronicle_count=0,
        broken_decisions_count=1,
        life_projects_count=0,
    )
    assert skip2 is False

    skip3, _ = _should_skip_week(
        chronicle_count=0,
        broken_decisions_count=0,
        life_projects_count=1,
    )
    assert skip3 is False


def test_interval_extends_after_three_consecutive_skips():
    from core.services.creative_journal_runtime import _interval_days_for_state

    assert _interval_days_for_state({"consecutive_skips": 0}) == 7
    assert _interval_days_for_state({"consecutive_skips": 2}) == 7
    assert _interval_days_for_state({"consecutive_skips": 3}) == 14
    assert _interval_days_for_state({"consecutive_skips": 5}) == 14


def test_run_cycle_skips_when_corpus_thin(events_table, monkeypatch, tmp_path):
    """Empty week → no journal file, consecutive_skips increments."""
    from core.services import creative_journal_runtime as cjr

    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    monkeypatch.setattr(cjr, "creative_journal_dir", lambda: journal_dir)

    state_holder: dict[str, object] = {}
    monkeypatch.setattr(cjr, "get_runtime_state_value",
                        lambda key, default=None: state_holder.get(key, default if default is not None else {}))
    monkeypatch.setattr(cjr, "set_runtime_state_value",
                        lambda key, val: state_holder.__setitem__(key, val))

    monkeypatch.setattr(cjr, "list_cognitive_chronicle_entries", lambda *, limit: [])
    monkeypatch.setattr(cjr, "list_active_long_term_intentions", lambda *, limit: [])
    monkeypatch.setattr(cjr, "_fetch_broken_decisions", lambda *a, **k: [])
    monkeypatch.setattr(cjr, "refresh_voice_recent", lambda: False)
    monkeypatch.setattr(cjr, "quality_daemon_llm_call",
                        lambda *a, **k: pytest.fail("LLM should not be called when skipping"))
    monkeypatch.setattr(cjr, "daemon_llm_call",
                        lambda *a, **k: pytest.fail("LLM should not be called when skipping"))

    result = cjr.run_creative_journal_cycle(trigger="test")
    assert result["status"] == "skipped"
    assert state_holder[cjr._STATE_KEY]["consecutive_skips"] == 1
    assert not list(journal_dir.iterdir())


def test_run_cycle_writes_with_frontmatter_and_resets_skips(
    events_table, monkeypatch, tmp_path,
):
    """Rich week → entry written with YAML frontmatter, skip counter resets."""
    from core.services import creative_journal_runtime as cjr

    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    monkeypatch.setattr(cjr, "creative_journal_dir", lambda: journal_dir)

    state_holder: dict[str, object] = {cjr._STATE_KEY: {"consecutive_skips": 2}}
    monkeypatch.setattr(cjr, "get_runtime_state_value",
                        lambda key, default=None: state_holder.get(key, default if default is not None else {}))
    monkeypatch.setattr(cjr, "set_runtime_state_value",
                        lambda key, val: state_holder.__setitem__(key, val))

    monkeypatch.setattr(cjr, "list_cognitive_chronicle_entries",
                        lambda *, limit: [
                            {"period": "2026-W18", "narrative": "uge med pres og nogle små åbninger"},
                            {"period": "2026-W17", "narrative": "intern uro omkring scope"},
                        ])
    monkeypatch.setattr(cjr, "list_active_long_term_intentions", lambda *, limit: [])
    monkeypatch.setattr(cjr, "_fetch_broken_decisions", lambda *a, **k: ["vi tog det forkerte valg"])
    monkeypatch.setattr(cjr, "refresh_voice_recent", lambda: False)
    monkeypatch.setattr(cjr, "read_voice_anchor", lambda: "## VOICE.md\n\ntør, lavmælt")
    monkeypatch.setattr(cjr, "quality_daemon_llm_call",
                        lambda *a, **k: "En kort betragtning. Ingen ord der prøver for hårdt.")

    result = cjr.run_creative_journal_cycle(trigger="test")
    assert result["status"] == "written"
    assert state_holder[cjr._STATE_KEY]["consecutive_skips"] == 0

    files = list(journal_dir.glob("*.md"))
    assert len(files) == 1
    body = files[0].read_text(encoding="utf-8")
    assert body.startswith("---\n")  # YAML frontmatter
    assert "chronicle_count: 2" in body
    assert "broken_decisions_count: 1" in body
    assert "En kort betragtning." in body
