from __future__ import annotations

from datetime import UTC, datetime

import pytest


def _fjern_maetning(monkeypatch) -> None:
    """Gør trangen høj nok til at tick'et faktisk forsøger at sanse."""
    from core.services import active_sensing_daemon as asd

    monkeypatch.setattr(asd, "_enabled", lambda: True)
    monkeypatch.setattr(asd, "_compute_desire", lambda state, now: 0.9)


def test_fejlet_sansning_nulstiller_ikke_maetningen(isolated_runtime, monkeypatch) -> None:
    """Rodårsagen bag 42 → 2 → 25 → 1 pr. dag.

    Før 18/9 satte tick'et `last_sensed_at` uanset udfald, så en fejlet
    sansning kostede hele mætningen: trangen faldt under tærsklen, og der gik
    30-90 min før næste forsøg. En ustabil formiddag blev til en tavs dag.
    """
    from core.services import active_sensing_daemon as asd

    _fjern_maetning(monkeypatch)
    monkeypatch.setattr(asd, "_choose_modality", lambda state, now: "visual")
    monkeypatch.setattr(
        asd, "_perform_sensing",
        lambda modality, state, now: {"ok": False, "reason": "capture_failed"},
    )

    svar = asd.tick_active_sensing_daemon()
    tilstand = asd._load_state()

    assert svar["sensed"] is False
    assert "sensing_failed" in svar["reason"]
    assert not tilstand.get("last_sensed_at"), "en fejl må ikke tælle som en sansning"
    assert tilstand.get("total_sensing_events", 0) == 0
    assert tilstand.get("total_failed_sensings") == 1


def test_fejl_giver_kort_pause_ikke_fuld_maetning(isolated_runtime, monkeypatch) -> None:
    """Et defekt kamera må ikke ramme hvert tick — men heller ikke æde dagen."""
    from core.services import active_sensing_daemon as asd

    _fjern_maetning(monkeypatch)
    monkeypatch.setattr(asd, "_choose_modality", lambda state, now: "visual")
    monkeypatch.setattr(
        asd, "_perform_sensing",
        lambda modality, state, now: {"ok": False, "reason": "capture_failed"},
    )
    asd.tick_active_sensing_daemon()

    # Straks efter: pausen holder igen.
    assert "afventer_efter_fejl" in asd.tick_active_sensing_daemon()["reason"]

    # Efter pausen: der prøves igen — uden at have mistet 30-90 minutter.
    tilstand = asd._load_state()
    tilstand["last_failed_at"] = "2020-01-01T00:00:00+00:00"
    asd._save_state(tilstand)
    assert "afventer_efter_fejl" not in asd.tick_active_sensing_daemon()["reason"]


def test_vellykket_sansning_taeller_som_foer(isolated_runtime, monkeypatch) -> None:
    from core.services import active_sensing_daemon as asd

    _fjern_maetning(monkeypatch)
    monkeypatch.setattr(asd, "_choose_modality", lambda state, now: "audio")
    monkeypatch.setattr(
        asd, "_perform_sensing",
        lambda modality, state, now: {
            "ok": True, "preview": "category=silence", "reason": "audio_silence",
        },
    )

    svar = asd.tick_active_sensing_daemon()
    tilstand = asd._load_state()

    assert svar["sensed"] is True
    assert tilstand["total_sensing_events"] == 1
    assert tilstand["last_sensed_at"]
    assert tilstand["modality_history"][0]["modality"] == "audio"


def test_atmosfaeren_opdigtes_ikke_naar_kameraet_fejler(isolated_runtime, monkeypatch) -> None:
    """«Atmosfæren var svær at fange» blev arkiveret som et ægte indtryk."""
    from core.services import active_sensing_daemon as asd

    skrevet: list[str] = []
    import core.services.sensory_archive as arkiv
    monkeypatch.setattr(
        arkiv, "record_atmosphere",
        lambda content, **kw: skrevet.append(content) or {"id": "x"},
    )
    import core.services.visual_memory as vm
    monkeypatch.setattr(
        vm, "look_around_now",
        lambda **kw: {"status": "vision_failed", "error": "provider 403"},
    )

    svar = asd._sense_atmosphere({}, datetime.now(UTC))

    assert svar["ok"] is False
    assert "403" in svar["reason"]
    assert skrevet == [], "en fejl må ikke arkiveres som en stemning"


def test_mixed_arkiverer_ikke_to_fejlkoder_som_indtryk(isolated_runtime, monkeypatch) -> None:
    """Før i dag blev «Visuelt: capture_error | Lyd: audio_error» gemt som en
    vellykket sansning."""
    from core.services import active_sensing_daemon as asd

    skrevet: list[str] = []
    import core.services.sensory_archive as arkiv
    monkeypatch.setattr(
        arkiv, "record_mixed",
        lambda content, **kw: skrevet.append(content) or {"id": "x"},
    )
    monkeypatch.setattr(
        asd, "_sense_visual",
        lambda state, now: {"ok": False, "preview": "capture_error", "reason": "kamera nede"},
    )
    monkeypatch.setattr(
        asd, "_sense_audio",
        lambda state, now: {"ok": False, "preview": "audio_error", "reason": "ingen enhed"},
    )

    svar = asd._sense_mixed({}, datetime.now(UTC))

    assert svar["ok"] is False
    assert skrevet == []
    assert "kamera nede" in svar["reason"]


def test_fladen_viser_fejlene_ved_siden_af_taellingen(isolated_runtime, monkeypatch) -> None:
    """799 sansninger lyder som 799 indtryk hvis fejlene ikke står ved siden af."""
    from core.services import active_sensing_daemon as asd

    monkeypatch.setattr(asd, "_enabled", lambda: True)
    tilstand = asd._load_state()
    tilstand["total_sensing_events"] = 799
    tilstand["total_failed_sensings"] = 41
    tilstand["last_fail_reason"] = "vision_failed"
    asd._save_state(tilstand)

    flade = asd.build_active_sensing_surface()

    assert flade["total_sensing_events"] == 799
    assert flade["total_failed_sensings"] == 41
    assert flade["last_fail_reason"] == "vision_failed"
