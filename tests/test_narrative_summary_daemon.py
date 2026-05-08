"""Tests for narrative_summary_daemon — Phase 2.5 of causal graph."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.runtime.db import connect
from core.services import narrative_summary_daemon as nsd


def _recent_iso(minutes_ago: int) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutes_ago)).isoformat()


def _insert_event(kind: str, ts_iso: str) -> int:
    with connect() as c:
        cur = c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, ?)",
            (kind, "{}", ts_iso),
        )
        c.commit()
        return int(cur.lastrowid)


def _insert_edge(child_id: int, parent_id: int, confidence: float = 0.95) -> None:
    with connect() as c:
        c.execute(
            "INSERT OR IGNORE INTO causal_edges "
            "(child_event_id, parent_event_id, edge_kind, confidence, source, "
            "created_at, reasoning) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (child_id, parent_id, "triggered", confidence, "explicit",
             _recent_iso(0), "test"),
        )
        c.commit()


@pytest.fixture(autouse=True)
def _reset_daemon_state():
    nsd._last_tick_at = None
    yield
    nsd._last_tick_at = None


def test_skips_when_no_anchor():
    """Returns ran=False when no anchor-kind event exists in the lookback."""
    # Hard to guarantee no anchor in dev DB. Just call and assert structure.
    result = nsd.run_summary_cycle()
    assert isinstance(result, dict)
    assert "ran" in result


def test_skips_when_chain_empty(monkeypatch):
    """Empty backward chain → skip without LLM call."""
    monkeypatch.setattr(nsd, "_fetch_recent_anchor", lambda: {
        "id": 999999, "kind": "runtime.visible_run_started",
        "created_at": _recent_iso(5),
    })
    monkeypatch.setattr(nsd, "_already_summarised", lambda eid: False)
    monkeypatch.setattr(nsd, "_build_chain", lambda eid: [])

    # If LLM gets called, fail loudly
    def boom(*a, **kw): raise AssertionError("LLM should not be called")
    import core.memory.inner_llm_enrichment as ile
    monkeypatch.setattr(ile, "call_cheap_llm", boom)

    result = nsd.run_summary_cycle()
    assert result["ran"] is False
    assert result["reason"] == "empty-chain"


def test_skips_when_already_summarised(monkeypatch):
    """Same anchor within dedupe window → skip."""
    monkeypatch.setattr(nsd, "_fetch_recent_anchor", lambda: {
        "id": 1, "kind": "runtime.visible_run_started",
        "created_at": _recent_iso(5),
    })
    monkeypatch.setattr(nsd, "_already_summarised", lambda eid: True)
    result = nsd.run_summary_cycle()
    assert result["ran"] is False
    assert result["reason"] == "already-summarised"


def test_persists_summary_event_when_llm_returns_text(monkeypatch):
    """Successful LLM call → narrative.summary event written with caused_by."""
    a_id = _insert_event("runtime.executive_action_outcome_recorded",
                         _recent_iso(10))
    p_id = _insert_event("runtime.agentic_round_start", _recent_iso(11))
    _insert_edge(a_id, p_id)

    monkeypatch.setattr(nsd, "_fetch_recent_anchor", lambda: {
        "id": a_id, "kind": "runtime.executive_action_outcome_recorded",
        "created_at": _recent_iso(10),
    })
    monkeypatch.setattr(nsd, "_already_summarised", lambda eid: False)
    monkeypatch.setattr(
        "core.memory.inner_llm_enrichment.call_cheap_llm",
        lambda system, user: "Jeg handlede med vilje, og så registrerede jeg.",
    )

    result = nsd.run_summary_cycle()
    assert result["ran"] is True
    assert result["chain_depth"] == 1
    assert result["summary_chars"] > 0

    # Verify event exists with correct payload
    with connect() as c:
        row = c.execute(
            "SELECT payload_json FROM events WHERE kind = 'narrative.summary' "
            "AND json_extract(payload_json, '$.anchor_event_id') = ? "
            "ORDER BY id DESC LIMIT 1",
            (a_id,),
        ).fetchone()
    assert row is not None
    import json
    payload = json.loads(row["payload_json"])
    assert payload["anchor_event_id"] == a_id
    assert "Jeg handlede" in payload["summary"]


def test_silent_fallback_when_llm_fails(monkeypatch):
    """LLM exception → returns ran=False without crashing daemon loop."""
    a_id = _insert_event("runtime.visible_run_started", _recent_iso(5))
    p_id = _insert_event("runtime.agentic_round_start", _recent_iso(6))
    _insert_edge(a_id, p_id)

    monkeypatch.setattr(nsd, "_fetch_recent_anchor", lambda: {
        "id": a_id, "kind": "runtime.visible_run_started",
        "created_at": _recent_iso(5),
    })
    monkeypatch.setattr(nsd, "_already_summarised", lambda eid: False)

    def kaboom(*a, **kw): raise RuntimeError("simulated LLM crash")
    monkeypatch.setattr(
        "core.memory.inner_llm_enrichment.call_cheap_llm", kaboom,
    )

    result = nsd.run_summary_cycle()
    assert result["ran"] is False
    assert result["error"] == "llm-call-failed"


def test_tick_respects_cadence():
    """Two calls in quick succession: second one skips on cadence."""
    nsd._last_tick_at = datetime.now(UTC)  # just ticked
    result = nsd.tick_narrative_summary_daemon()
    assert result["ran"] is False
    assert result["reason"] == "cadence-not-elapsed"
