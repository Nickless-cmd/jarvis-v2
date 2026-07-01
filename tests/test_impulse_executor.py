"""impulse_executor observer sult/liveness til Centralen (LivingNeuron Fase A)."""
from core.services import impulse_executor as ie


def test_observe_impulse_tick_self_safe():
    # Fire-and-forget, må aldrig kaste (også hvis central er nede).
    ie._observe_impulse_tick(pending=0, executed=0, starved=True)
    ie._observe_impulse_tick(pending=2, executed=1, starved=False)


def test_starved_tick_observes(isolated_runtime, monkeypatch):
    # Egress-fri: observe_hub skriver til trace-sinken (ikke central().observe).
    from core.services import central_trace
    monkeypatch.setattr("core.services.pressure_threshold_gate.get_pending_impulses", lambda: [])
    out = ie.run_impulse_executor_tick()
    assert out["impulses_executed"] == 0
    recs = [r for r in central_trace.sink().recent(limit=50) if r.nerve == "impulse_executor"]
    assert recs and recs[-1].payload.get("starved") is True
