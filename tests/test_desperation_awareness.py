"""Desperation-awareness publisher gyldigt inner_voice.signal-event (bug fikset 1. jul)."""
import inspect
import core.services.desperation_awareness as da


def test_no_dict_as_kind():
    src = inspect.getsource(da)
    assert 'event_bus.publish({' not in src           # ingen dict-som-første-arg
    assert 'event_bus.publish("inner_voice.signal", payload)' in src


def test_rolig_baseline_er_en_MAALING_ikke_en_doed_daemon():
    """`active` stod som `state["level"] != "calm"`.

    `cognitive_architecture_surface` læser nøglen som liv, så en SUND
    tilstand fik systemet til at melde sig dødt i mind-rapporten. Presset
    står i `level` og `score`, hvor det hører hjemme.
    """
    import core.services.desperation_awareness as D

    flade = D.build_desperation_awareness_surface()
    assert flade["active"] is True
    assert "level" in flade and "score" in flade
