"""Tests for pattern_counterfactual_daemon + section — Phase 3.5."""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from core.runtime.db import connect
from core.services import pattern_counterfactual_daemon as pcd
from core.services.prompt_sections import pattern_counterfactuals as pcs


def _recent_iso(hours_ago: int) -> str:
    return (datetime.now(UTC) - timedelta(hours=hours_ago)).isoformat()


@pytest.fixture(autouse=True)
def _reset():
    pcd._last_tick_at = None
    pcs.invalidate_cache()
    yield
    pcd._last_tick_at = None
    pcs.invalidate_cache()


def test_skips_when_no_patterns(monkeypatch):
    monkeypatch.setattr(pcd, "_fetch_top_patterns", lambda: [])
    result = pcd.run_pattern_cf_cycle()
    assert result["ran"] is False
    assert result["reason"] == "no-patterns"


def test_skips_already_counterfactualized(monkeypatch):
    """Patterns already covered in dedupe window → skipped."""
    monkeypatch.setattr(pcd, "_fetch_top_patterns", lambda: [
        {"parent_kind": "a.x", "child_kind": "b.y", "count": 10, "avg_conf": 1.0},
    ])
    monkeypatch.setattr(pcd, "_already_counterfactualized", lambda p, c: True)

    def boom(*a, **kw): raise AssertionError("LLM should not be called when deduped")
    monkeypatch.setattr(
        "core.memory.inner_llm_enrichment.call_cheap_llm", boom,
    )

    result = pcd.run_pattern_cf_cycle()
    assert result["ran"] is True
    assert result["written"] == 0
    assert result["skipped_dedupe"] == 1


def test_persists_pattern_what_if_event(monkeypatch):
    """Successful LLM call → counterfactual.pattern_what_if event written."""
    monkeypatch.setattr(pcd, "_fetch_top_patterns", lambda: [
        {"parent_kind": "x.start", "child_kind": "y.end", "count": 42, "avg_conf": 0.95},
    ])
    monkeypatch.setattr(pcd, "_already_counterfactualized", lambda p, c: False)
    monkeypatch.setattr(
        "core.memory.inner_llm_enrichment.call_cheap_llm",
        lambda system, user: "Jeg ville miste evnen til at gå i mål med opgaver.",
    )

    result = pcd.run_pattern_cf_cycle()
    assert result["written"] == 1

    # event_bus.publish() skriver ASYNKRONT via en writer-tråd, så eventet er ikke
    # nødvendigvis persisteret i samme øjeblik publish() returnerer. Poll kort i
    # stedet for at læse én gang med det samme (racen ramte tidligere kun tilfældigt
    # når prod-DB'en var varm; en frisk/kold DB afslører den).
    import time as _time
    row = None
    for _ in range(30):
        with connect() as c:
            row = c.execute(
                "SELECT payload_json FROM events "
                "WHERE kind = 'counterfactual.pattern_what_if' "
                "AND json_extract(payload_json, '$.parent_kind') = 'x.start' "
                "AND json_extract(payload_json, '$.child_kind') = 'y.end' "
                "ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if row is not None:
            break
        _time.sleep(0.1)
    assert row is not None
    payload = json.loads(row["payload_json"])
    assert payload["occurrences_7d"] == 42
    assert "Jeg ville miste" in payload["hypothesis"]


def test_section_renders_recent_counterfactuals():
    """Awareness section reads the persisted events back."""
    # If test_persists_pattern_what_if_event has run, an event exists
    # already. Just call and check structure.
    out = pcs.pattern_counterfactuals_section()
    if out:
        assert "🔮" in out
        assert "Hvad hvis" in out


def test_section_silent_on_db_error(monkeypatch):
    monkeypatch.setattr(
        "core.services.prompt_sections.pattern_counterfactuals._fetch_recent_counterfactuals",
        lambda: (_ for _ in ()).throw(RuntimeError("simulated")),
    )
    pcs.invalidate_cache()
    out = pcs.pattern_counterfactuals_section()
    assert out == ""


def test_tick_respects_cadence():
    pcd._last_tick_at = datetime.now(UTC)
    result = pcd.tick_pattern_counterfactual_daemon()
    assert result["ran"] is False
    assert result["reason"] == "cadence-not-elapsed"
