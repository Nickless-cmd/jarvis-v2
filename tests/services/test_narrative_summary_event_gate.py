"""Fase 2 Lag 5 — narrative_summary daemon gated behind the shared event-gate.

Keeps LLM judgment; only fires the narrative-summary generation when the active
narrative thread actually moved (new anchor / changed chain depth). Flag OFF =
legacy behaviour. Flag ON = consult event_gate.should_generative_fire.

Robust patch.object pattern (NOT sys.modules injection, which leaks across
files): patch the REAL event_gate module attributes.
"""

from unittest import mock

from core.memory import inner_llm_enrichment
from core.services import event_gate
from core.services import narrative_summary_daemon as nsd


def _anchor() -> dict:
    return {"id": 7, "kind": "agentic.turn", "created_at": "2026-07-13T10:00:00+00:00"}


def _chain() -> list[dict]:
    return [{"event": {"kind": "tool.call", "created_at": "2026-07-13T09:58:00+00:00"}}]


def _patches():
    """Common daemon-internal patches so run_summary_cycle reaches the LLM."""
    return (
        mock.patch.object(nsd, "_fetch_recent_anchor", return_value=_anchor()),
        mock.patch.object(nsd, "_already_summarised", return_value=False),
        mock.patch.object(nsd, "_build_chain", return_value=_chain()),
        mock.patch.object(nsd, "_persist_summary", return_value=42),
    )


def test_flag_off_fires_llm_as_today(isolated_runtime):
    p1, p2, p3, p4 = _patches()
    with p1, p2, p3, p4, \
         mock.patch.object(inner_llm_enrichment, "call_cheap_llm", return_value="En rolig refleksion.") as llm, \
         mock.patch.object(event_gate, "event_driven_enabled", return_value=False), \
         mock.patch.object(event_gate, "should_generative_fire", return_value=False) as gate:
        res = nsd.run_summary_cycle()
    assert llm.called
    assert res.get("summary_event_id") == 42
    gate.assert_not_called()


def test_flag_on_no_change_skips_llm(isolated_runtime):
    p1, p2, p3, p4 = _patches()
    with p1, p2, p3, p4, \
         mock.patch.object(inner_llm_enrichment, "call_cheap_llm", return_value="En rolig refleksion.") as llm, \
         mock.patch.object(event_gate, "event_driven_enabled", return_value=True), \
         mock.patch.object(event_gate, "should_generative_fire", return_value=False):
        res = nsd.run_summary_cycle()
    assert not llm.called
    assert res == {"skipped": "no_signal_change"}


def test_flag_on_change_fires_llm(isolated_runtime):
    p1, p2, p3, p4 = _patches()
    with p1, p2, p3, p4, \
         mock.patch.object(inner_llm_enrichment, "call_cheap_llm", return_value="En rolig refleksion.") as llm, \
         mock.patch.object(event_gate, "event_driven_enabled", return_value=True), \
         mock.patch.object(event_gate, "should_generative_fire", return_value=True) as gate:
        res = nsd.run_summary_cycle()
    assert llm.called
    assert res.get("summary_event_id") == 42
    gate.assert_called_once()
