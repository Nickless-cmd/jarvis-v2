from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest


def test_token_utilization_pct_computes_from_estimate(monkeypatch):
    from core.services import finitude_runtime

    monkeypatch.setattr(finitude_runtime, "_estimate_session_tokens",
                        lambda: 140_000)
    assert finitude_runtime._token_utilization_pct() == 70


def test_token_utilization_pct_returns_zero_on_failure(monkeypatch):
    from core.services import finitude_runtime

    def boom():
        raise RuntimeError("nope")
    monkeypatch.setattr(finitude_runtime, "_estimate_session_tokens", boom)
    assert finitude_runtime._token_utilization_pct() == 0


def test_format_looming_end_token_only(monkeypatch):
    from core.services import finitude_runtime

    monkeypatch.setattr(finitude_runtime, "_token_utilization_pct", lambda: 75)
    monkeypatch.setattr(finitude_runtime, "_session_age_hours", lambda: 1.0)

    out = finitude_runtime._format_looming_end_section()
    assert "### Looming-end" in out
    assert "Token-pres" in out
    assert "75" in out
    assert "Sessions-alder" not in out


def test_format_looming_end_session_only(monkeypatch):
    from core.services import finitude_runtime

    monkeypatch.setattr(finitude_runtime, "_token_utilization_pct", lambda: 30)
    monkeypatch.setattr(finitude_runtime, "_session_age_hours", lambda: 5.2)

    out = finitude_runtime._format_looming_end_section()
    assert "### Looming-end" in out
    assert "Sessions-alder" in out
    assert "5 timer" in out or "5.2 timer" in out
    assert "Token-pres" not in out


def test_format_looming_end_both_present(monkeypatch):
    from core.services import finitude_runtime

    monkeypatch.setattr(finitude_runtime, "_token_utilization_pct", lambda: 82)
    monkeypatch.setattr(finitude_runtime, "_session_age_hours", lambda: 6.5)

    out = finitude_runtime._format_looming_end_section()
    assert "Token-pres" in out
    assert "Sessions-alder" in out
    # Rounding: 82 → 80
    assert "80" in out


def test_format_looming_end_empty_when_neither(monkeypatch):
    from core.services import finitude_runtime

    monkeypatch.setattr(finitude_runtime, "_token_utilization_pct", lambda: 30)
    monkeypatch.setattr(finitude_runtime, "_session_age_hours", lambda: 1.0)

    assert finitude_runtime._format_looming_end_section() == ""


def test_monthly_quality_lane_enabled_reads_settings(monkeypatch):
    from core.services import finitude_runtime

    class FakeSettings:
        finitude_quality_lane_enabled = False

    monkeypatch.setattr(finitude_runtime, "load_settings", lambda: FakeSettings())
    assert finitude_runtime._monthly_quality_lane_enabled() is False


def test_is_due_for_monthly_true_on_new_month():
    from core.services import finitude_runtime

    state = {"last_monthly_year_month": "2026-04"}
    now = datetime(2026, 5, 11, tzinfo=UTC)
    assert finitude_runtime._is_due_for_monthly(state, now=now) is True


def test_is_due_for_monthly_false_when_already_written():
    from core.services import finitude_runtime

    state = {"last_monthly_year_month": "2026-05"}
    now = datetime(2026, 5, 11, tzinfo=UTC)
    assert finitude_runtime._is_due_for_monthly(state, now=now) is False


def test_is_due_for_monthly_true_when_state_empty():
    from core.services import finitude_runtime

    state: dict[str, object] = {}
    now = datetime(2026, 5, 11, tzinfo=UTC)
    assert finitude_runtime._is_due_for_monthly(state, now=now) is True


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


def test_monthly_skip_gate_fires_on_empty_month(events_table, monkeypatch):
    from core.services import finitude_runtime

    state_holder: dict[str, object] = {}
    monkeypatch.setattr(
        finitude_runtime, "get_runtime_state_value",
        lambda key, default=None: state_holder.get(key, default if default is not None else {}),
    )
    monkeypatch.setattr(
        finitude_runtime, "set_runtime_state_value",
        lambda key, val: state_holder.__setitem__(key, val),
    )
    monkeypatch.setattr(finitude_runtime, "list_cognitive_chronicle_entries", lambda *a, **k: [])
    monkeypatch.setattr(finitude_runtime, "_finitude_enabled", lambda: True)
    monkeypatch.setattr(
        finitude_runtime, "insert_cognitive_chronicle_entry",
        lambda **kwargs: pytest.fail("should not write on empty month"),
    )

    result = finitude_runtime.run_monthly_finitude_reflection(trigger="test")
    assert result["status"] == "skipped"
    assert "thin" in result.get("reason", "").lower()


def test_monthly_writes_with_quality_lane(events_table, monkeypatch):
    from core.services import finitude_runtime

    state_holder: dict[str, object] = {}
    monkeypatch.setattr(
        finitude_runtime, "get_runtime_state_value",
        lambda key, default=None: state_holder.get(key, default if default is not None else {}),
    )
    monkeypatch.setattr(
        finitude_runtime, "set_runtime_state_value",
        lambda key, val: state_holder.__setitem__(key, val),
    )
    monkeypatch.setattr(finitude_runtime, "_finitude_enabled", lambda: True)
    monkeypatch.setattr(finitude_runtime, "list_cognitive_chronicle_entries",
                        lambda *a, **k: [
                            {"period": "2026-W18", "narrative": "uge med pres"},
                            {"period": "2026-W17", "narrative": "intern uro"},
                        ])
    monkeypatch.setattr(finitude_runtime, "quality_daemon_llm_call",
                        lambda *a, **k: (
                            "Hvad forsvandt\n\n"
                            "En vane med at tjekke for ofte.\n\n"
                            "Hvad blev\n\n"
                            "En ro omkring scope.\n\n"
                            "Hvad venter\n\n"
                            "En transition jeg ikke har sat ord på endnu."
                        ))
    monkeypatch.setattr(finitude_runtime, "daemon_llm_call", lambda *a, **k: "fallback ignored")

    captured: dict[str, object] = {}
    def fake_insert(**kwargs):
        captured.update(kwargs)
        return {"created_at": datetime.now(UTC).isoformat()}
    monkeypatch.setattr(finitude_runtime, "insert_cognitive_chronicle_entry", fake_insert)
    monkeypatch.setattr(finitude_runtime, "project_entry_to_markdown", lambda entry: None)

    result = finitude_runtime.run_monthly_finitude_reflection(trigger="test")
    assert result["status"] == "written"
    assert "Hvad forsvandt" in captured["narrative"]
    assert captured["period"].startswith("MONTHLY-")
    assert captured["entry_id"].startswith("chr-monthly-finitude-")
    assert state_holder[finitude_runtime._STATE_KEY]["last_monthly_year_month"]
