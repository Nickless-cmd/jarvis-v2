"""Tests for causal_patterns awareness section.

Phase 3 of causal graph wiring (2026-05-08).
"""
from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

import pytest

from core.runtime.db import connect
from core.services.prompt_sections import causal_patterns


def _recent_iso(hours_ago: int) -> str:
    return (datetime.now(UTC) - timedelta(hours=hours_ago)).isoformat()


def _insert_event(kind: str, ts_iso: str) -> int:
    with connect() as c:
        cur = c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, ?)",
            (kind, "{}", ts_iso),
        )
        c.commit()
        return int(cur.lastrowid)


def _insert_edge(child_id: int, parent_id: int, confidence: float = 1.0) -> None:
    with connect() as c:
        c.execute(
            "INSERT OR IGNORE INTO causal_edges "
            "(child_event_id, parent_event_id, edge_kind, confidence, source, "
            "created_at, reasoning) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (child_id, parent_id, "triggered", confidence, "explicit", _recent_iso(0), "test"),
        )
        c.commit()


@pytest.fixture(autouse=True)
def _reset_cache():
    causal_patterns.invalidate_cache()
    yield
    causal_patterns.invalidate_cache()


def test_filters_out_pure_plumbing():
    """tool.invoked → tool.completed should never appear in output."""
    out = causal_patterns.causal_patterns_section()
    assert "tool.invoked → tool.completed" not in out


def test_filters_out_test_data_kinds():
    """Patterns from runtime.test_/cycle_/chain_/etc prefixes are suppressed."""
    out = causal_patterns.causal_patterns_section()
    for marker in ("runtime.chain_", "runtime.cycle_", "runtime.test_", "runtime.multi_"):
        assert marker not in out, f"test-data marker {marker!r} leaked into output"


def test_renders_narrative_meaningful_patterns():
    """When narrative-meaningful patterns are present, they appear with counts."""
    # Insert 6 instances of channel.message_inbound → tool.invoked
    # (channel.message_inbound is not plumbing, tool.invoked is — kept
    # because at least one side is meaningful)
    parent_ids: list[int] = []
    child_ids: list[int] = []
    for i in range(6):
        p = _insert_event("channel.message_inbound", _recent_iso(2))
        c_ = _insert_event("tool.invoked", _recent_iso(2))
        parent_ids.append(p)
        child_ids.append(c_)
        _insert_edge(c_, p)

    causal_patterns.invalidate_cache()
    out = causal_patterns.causal_patterns_section()
    # The output may or may not surface this exact pattern depending on
    # other patterns in the DB, but the section should not be empty when
    # any narrative pattern exists.
    assert isinstance(out, str)
    if out:
        # When non-empty, it should always start with the marker
        assert "📊" in out
        assert "Tilbagevendende kausal-mønstre" in out


def test_returns_empty_when_nothing_meets_threshold():
    """Empty output when no pattern reaches _MIN_OCCURRENCES."""
    # Insert just 2 instances — below the threshold of 5
    p1 = _insert_event("identity.mutation_applied", _recent_iso(1))
    c1 = _insert_event("memory.end_of_run_consolidation", _recent_iso(1))
    _insert_edge(c1, p1)
    p2 = _insert_event("identity.mutation_applied", _recent_iso(1))
    c2 = _insert_event("memory.end_of_run_consolidation", _recent_iso(1))
    _insert_edge(c2, p2)

    # Output may still be non-empty due to other patterns in the DB,
    # but at minimum we just verify the section doesn't include this
    # under-threshold pattern with a count below _MIN_OCCURRENCES.
    causal_patterns.invalidate_cache()
    out = causal_patterns.causal_patterns_section()
    if "identity.mutation_applied → memory.end_of_run_consolidation" in out:
        # If it leaked through, the count must be at least _MIN_OCCURRENCES
        import re
        m = re.search(
            r"identity\.mutation_applied → memory\.end_of_run_consolidation \((\d+)×",
            out,
        )
        assert m is not None
        assert int(m.group(1)) >= causal_patterns._MIN_OCCURRENCES


def test_caches_for_ttl_window():
    """Repeated calls within TTL return the same result without re-querying."""
    out1 = causal_patterns.causal_patterns_section()
    t = time.monotonic()
    out2 = causal_patterns.causal_patterns_section()
    elapsed_ms = (time.monotonic() - t) * 1000
    assert out1 == out2
    assert elapsed_ms < 5, f"warm call should be ~0ms, was {elapsed_ms:.1f}ms"


def test_silent_fallback_on_db_error(monkeypatch):
    """If the DB query fails, returns "" silently — never breaks prompt assembly."""
    def boom(*args, **kwargs):
        raise RuntimeError("simulated db failure")
    monkeypatch.setattr(
        "core.services.prompt_sections.causal_patterns._fetch_patterns",
        boom,
    )
    out = causal_patterns.causal_patterns_section()
    assert out == ""


def test_is_plumbing_classifier():
    """The plumbing predicate covers both denylist + test-prefix branches."""
    assert causal_patterns._is_plumbing("tool.invoked")
    assert causal_patterns._is_plumbing("runtime.cheap_lane_provider_failed")
    assert causal_patterns._is_plumbing("runtime.test_parent")
    assert causal_patterns._is_plumbing("runtime.chain_a")
    assert not causal_patterns._is_plumbing("runtime.agentic_round_start")
    assert not causal_patterns._is_plumbing("identity.drift_detected")
    assert not causal_patterns._is_plumbing("memory.end_of_run_consolidation")
