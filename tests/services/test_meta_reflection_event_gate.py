"""Fase 2 Lag 5 — meta_reflection daemon gated behind the shared event-gate.

Keeps LLM judgment; only fires cross-signal synthesis when a relevant signal
actually moved. Flag OFF = legacy behaviour (always fires when cadence+signals
allow). Flag ON = consult event_gate.should_generative_fire.
"""

from unittest import mock

from core.services import event_gate
from core.services import meta_reflection_daemon as mrd


def _snapshot() -> dict:
    return {
        "latest_fragment": "en tanke der bevæger sig",
        "last_surprise": "det overraskede mig",
        "last_conflict": "der er en indre strid",
    }


def test_flag_off_fires_llm_as_today(isolated_runtime):
    mrd._last_meta_at = None
    with mock.patch.object(mrd, "daemon_llm_call", return_value="et mønster") as llm, \
         mock.patch.object(event_gate, "event_driven_enabled", return_value=False), \
         mock.patch.object(event_gate, "should_generative_fire", return_value=False) as gate:
        res = mrd.tick_meta_reflection_daemon(_snapshot())
    assert llm.called
    assert res.get("generated") is True
    gate.assert_not_called()


def test_flag_on_no_change_skips_llm(isolated_runtime):
    mrd._last_meta_at = None
    with mock.patch.object(mrd, "daemon_llm_call", return_value="et mønster") as llm, \
         mock.patch.object(event_gate, "event_driven_enabled", return_value=True), \
         mock.patch.object(event_gate, "should_generative_fire", return_value=False):
        res = mrd.tick_meta_reflection_daemon(_snapshot())
    assert not llm.called
    assert res == {"skipped": "no_signal_change"}


def test_flag_on_change_fires_llm(isolated_runtime):
    mrd._last_meta_at = None
    with mock.patch.object(mrd, "daemon_llm_call", return_value="et mønster") as llm, \
         mock.patch.object(event_gate, "event_driven_enabled", return_value=True), \
         mock.patch.object(event_gate, "should_generative_fire", return_value=True) as gate:
        res = mrd.tick_meta_reflection_daemon(_snapshot())
    assert llm.called
    assert res.get("generated") is True
    gate.assert_called_once()
