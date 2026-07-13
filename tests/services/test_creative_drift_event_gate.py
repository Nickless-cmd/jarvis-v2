"""Fase 2 Lag 5 — creative_drift daemon gated behind the shared event-gate.

Keeps LLM judgment; only fires the associative-surprise generation when
idle-time / unused-context signals actually moved. Flag OFF = legacy behaviour
(fires when daily-cap + cadence allow). Flag ON = consult
event_gate.should_generative_fire.
"""

from unittest import mock

from core.services import creative_drift_daemon as cdd
from core.services import event_gate


def _reset() -> None:
    cdd._last_tick_at = None
    cdd._today_count = 0
    cdd._today_date = None


def test_flag_off_fires_llm_as_today(isolated_runtime):
    _reset()
    with mock.patch.object(cdd, "_generate_drift_idea", return_value="en uventet idé") as gen, \
         mock.patch.object(event_gate, "event_driven_enabled", return_value=False), \
         mock.patch.object(event_gate, "should_generative_fire", return_value=False) as gate:
        res = cdd.tick_creative_drift_daemon(["frag1", "frag2"])
    assert gen.called
    assert res.get("generated") is True
    gate.assert_not_called()


def test_flag_on_no_change_skips_llm(isolated_runtime):
    _reset()
    with mock.patch.object(cdd, "_generate_drift_idea", return_value="en uventet idé") as gen, \
         mock.patch.object(event_gate, "event_driven_enabled", return_value=True), \
         mock.patch.object(event_gate, "should_generative_fire", return_value=False):
        res = cdd.tick_creative_drift_daemon(["frag1", "frag2"])
    assert not gen.called
    assert res == {"skipped": "no_signal_change"}


def test_flag_on_change_fires_llm(isolated_runtime):
    _reset()
    with mock.patch.object(cdd, "_generate_drift_idea", return_value="en uventet idé") as gen, \
         mock.patch.object(event_gate, "event_driven_enabled", return_value=True), \
         mock.patch.object(event_gate, "should_generative_fire", return_value=True) as gate:
        res = cdd.tick_creative_drift_daemon(["frag1", "frag2"])
    assert gen.called
    assert res.get("generated") is True
    gate.assert_called_once()
