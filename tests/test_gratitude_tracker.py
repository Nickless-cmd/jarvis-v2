"""gratitude_tracker observer taknemmelighed egress-frit til Centralen (LivingNeuron Fase A)."""
from core.services import gratitude_tracker as gt


def test_track_gratitude_observes(isolated_runtime):
    # Egress-fri: observe_hub skriver til trace-sinken (ikke central().observe).
    from core.services import central_trace
    trig = next(iter(gt._GRATITUDE_TRIGGERS))
    gt.track_gratitude(trigger_event=trig)
    recs = [r for r in central_trace.sink().recent(limit=50) if r.nerve == "gratitude"]
    assert recs


def test_unknown_trigger_no_crash(isolated_runtime):
    assert gt.track_gratitude(trigger_event="__nope__") is None
