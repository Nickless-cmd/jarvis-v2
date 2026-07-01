"""impulse_executor observer sult/liveness til Centralen (LivingNeuron Fase A)."""
from core.services import impulse_executor as ie


def test_observe_impulse_tick_self_safe():
    # Fire-and-forget, må aldrig kaste (også hvis central er nede).
    ie._observe_impulse_tick(pending=0, executed=0, starved=True)
    ie._observe_impulse_tick(pending=2, executed=1, starved=False)


def test_starved_tick_observes(isolated_runtime, monkeypatch):
    seen = []
    import core.services.central_core as cc
    monkeypatch.setattr(cc.central(), "observe", lambda ev: seen.append(ev))
    monkeypatch.setattr("core.services.pressure_threshold_gate.get_pending_impulses", lambda: [])
    out = ie.run_impulse_executor_tick()
    assert out["impulses_executed"] == 0
    assert any(e.get("nerve") == "impulse_executor" and e.get("starved") for e in seen)
