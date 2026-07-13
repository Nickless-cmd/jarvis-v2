"""Fase 2 Lag 5 — irony daemon gated behind the shared event-gate.

Keeps LLM judgment; only fires the self-observation generation when the
self-distance signals (user-inactivity / load) actually crossed. Flag OFF =
legacy behaviour. Flag ON = consult event_gate.should_generative_fire.

Robust patch.object pattern (NOT sys.modules injection, which leaks across
files): patch the REAL event_gate module attributes.
"""

from unittest import mock

from core.services import event_gate
from core.services import irony_daemon as ird


def _reset() -> None:
    ird._observations_today = 0
    ird._last_reset_date = ""
    ird._cached_observation = ""


def test_flag_off_fires_llm_as_today(isolated_runtime):
    _reset()
    with mock.patch.object(ird, "_generate_observation", return_value="En tør observation.") as gen, \
         mock.patch.object(ird, "_store_observation"), \
         mock.patch.object(event_gate, "event_driven_enabled", return_value=False), \
         mock.patch.object(event_gate, "should_generative_fire", return_value=False) as gate:
        res = ird.tick_irony_daemon()
    assert gen.called
    assert res.get("generated") is True
    gate.assert_not_called()


def test_flag_on_no_change_skips_llm(isolated_runtime):
    _reset()
    with mock.patch.object(ird, "_generate_observation", return_value="En tør observation.") as gen, \
         mock.patch.object(ird, "_store_observation"), \
         mock.patch.object(event_gate, "event_driven_enabled", return_value=True), \
         mock.patch.object(event_gate, "should_generative_fire", return_value=False):
        res = ird.tick_irony_daemon()
    assert not gen.called
    assert res == {"skipped": "no_signal_change"}


def test_flag_on_change_fires_llm(isolated_runtime):
    _reset()
    with mock.patch.object(ird, "_generate_observation", return_value="En tør observation.") as gen, \
         mock.patch.object(ird, "_store_observation"), \
         mock.patch.object(event_gate, "event_driven_enabled", return_value=True), \
         mock.patch.object(event_gate, "should_generative_fire", return_value=True) as gate:
        res = ird.tick_irony_daemon()
    assert gen.called
    assert res.get("generated") is True
    gate.assert_called_once()
