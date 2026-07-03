"""Tests for daemon_llm cache-effektivitets-instrumentering (Bølge 0, observe-only)."""
from __future__ import annotations

import pytest

from core.services import central_timeseries
from core.services import daemon_llm as dl


@pytest.fixture(autouse=True)
def _clean():
    with dl._llm_lock:
        dl._llm_stats.clear()
    central_timeseries._reset_for_tests()
    yield
    with dl._llm_lock:
        dl._llm_stats.clear()
    central_timeseries._reset_for_tests()


def test_note_call_tracks_hit_rate():
    dl._note_call("somatic", hit=False)
    dl._note_call("somatic", hit=True)
    dl._note_call("somatic", hit=True)
    snap = dl.daemon_llm_cache_snapshot()
    assert snap["somatic"] == {"calls": 3, "hits": 2, "hit_rate": round(2 / 3, 3)}
    # seneste sample i tidsserien = løbende hit-rate
    last = central_timeseries.recent("daemon_llm", "somatic", limit=1)[-1]
    assert last.value == round(2 / 3, 3)


def test_snapshot_sorted_by_calls():
    for _ in range(5):
        dl._note_call("dream", hit=False)
    dl._note_call("mood", hit=True)
    keys = list(dl.daemon_llm_cache_snapshot().keys())
    assert keys[0] == "dream"  # flest kald først


def test_note_call_self_safe():
    try:
        dl._note_call(None, hit=True)  # type: ignore[arg-type]
    except Exception as e:  # pragma: no cover
        pytest.fail(f"_note_call kastede: {e}")
