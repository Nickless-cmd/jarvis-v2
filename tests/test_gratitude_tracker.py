"""gratitude_tracker observer taknemmelighed egress-frit til Centralen (LivingNeuron Fase A)."""
from core.services import gratitude_tracker as gt


def test_track_gratitude_observes(isolated_runtime, monkeypatch):
    seen = []
    import core.services.central_core as cc
    monkeypatch.setattr(cc.central(), "observe", lambda ev: seen.append(ev))
    # brug en gyldig trigger fra _GRATITUDE_TRIGGERS
    trig = next(iter(gt._GRATITUDE_TRIGGERS))
    gt.track_gratitude(trigger_event=trig)
    assert any(e.get("nerve") == "gratitude" for e in seen)


def test_unknown_trigger_no_crash(isolated_runtime):
    assert gt.track_gratitude(trigger_event="__nope__") is None
