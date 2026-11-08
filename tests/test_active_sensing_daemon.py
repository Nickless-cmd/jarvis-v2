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
        lambda state, now, **kw: {"ok": False, "preview": "capture_error", "reason": "kamera nede"},
    )
    monkeypatch.setattr(
        asd, "_sense_audio",
        lambda state, now, **kw: {"ok": False, "preview": "audio_error", "reason": "ingen enhed"},
    )

    svar = asd._sense_mixed({}, datetime.now(UTC))

    assert svar["ok"] is False
    assert skrevet == []
    assert "kamera nede" in svar["reason"]


def test_atmosphere_skriver_EEN_post_ikke_to(isolated_runtime, monkeypatch) -> None:
    """Atmosphere-sansningen ejer sin egen modalitet.

    Målt 6/10-2026: grenen kaldte `look_around_now`, som arkiverede sit eget svar
    som `visual` — og skrev derefter SAMME tekst igen som `atmosphere`. Hver
    atmosphere-sansning blev to rækker i samme sekund.
    """
    from core.services import active_sensing_daemon as asd
    import core.services.sensory_archive as arkiv
    import core.services.visual_memory as vm

    kald: list[dict] = []
    skrevet: list[str] = []

    def falsk_look(**kw):
        kald.append(kw)
        return {"status": "captured", "description": "Rummet føles tungt."}

    monkeypatch.setattr(vm, "look_around_now", falsk_look)
    monkeypatch.setattr(
        arkiv, "record_atmosphere",
        lambda content, **kw: skrevet.append(content) or {"id": "x"},
    )

    svar = asd._sense_atmosphere({}, datetime.now(UTC))

    assert svar["ok"] is True
    assert skrevet == ["Rummet føles tungt."], "atmosphere-posten mangler"
    assert kald and kald[0].get("arkiver") is False, (
        "grenen bad ikke om at eje arkiveringen — så skriver look_around_now "
        "en ekstra visual-række med samme tekst"
    )


def test_mixed_skriver_EEN_post_ikke_tre(isolated_runtime, monkeypatch) -> None:
    """Mixed-posten er den fulde sansning; halvdelene må ikke arkivere selv.

    Målt 6/10-2026: én mixed-sansning skrev TRE rækker — `visual`, `audio` og
    `mixed` — hvoraf de to første var halvdele af den tredje.
    """
    from core.services import active_sensing_daemon as asd
    import core.services.sensory_archive as arkiv

    flag: list[object] = []
    skrevet: list[str] = []

    monkeypatch.setattr(
        asd, "_sense_visual",
        lambda state, now, **kw: (
            flag.append(kw.get("arkiver"))
            or {"ok": True, "description": "En stol.", "preview": "En stol.",
                "reason": "visual_captured"}
        ),
    )
    monkeypatch.setattr(
        asd, "_sense_audio",
        lambda state, now, **kw: (
            flag.append(kw.get("arkiver"))
            or {"ok": True, "preview": "music", "reason": "audio_music"}
        ),
    )
    monkeypatch.setattr(
        arkiv, "record_mixed",
        lambda content, **kw: skrevet.append(content) or {"id": "x"},
    )

    svar = asd._sense_mixed({}, datetime.now(UTC))

    assert svar["ok"] is True
    assert len(skrevet) == 1, "mixed skal give præcis én post"
    assert flag == [False, False], (
        "mixed kaldte en del der arkiverede selv — så skrev den en ekstra række"
    )


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


def test_silence_lyt_taeller_ikke_som_arkiveret(isolated_runtime, monkeypatch) -> None:
    """Et lyt der endte i `silence` er ikke et indtryk.

    Målt 28/9-2026: 24 sådanne poster, nyeste 26/9 — og hanen skrev videre.
    Turen må ikke melde «arkiveret» når arkivet afviste den.
    """
    from datetime import UTC, datetime

    from core.services import active_sensing_daemon as asd
    from core.services import ambient_sound_daemon as amb

    monkeypatch.setattr(
        amb, "_capture_sample",
        lambda save_wav=True: ("silence", 0.0, 0.0, None),
    )

    svar = asd._sense_audio({}, datetime.now(UTC))

    assert svar["ok"] is False, "intet indtryk blev arkiveret"
    assert svar["reason"] == "audio_silence_not_an_impression"


def test_rigtig_lyd_arkiveres_som_foer(isolated_runtime, monkeypatch) -> None:
    """Kun `silence` er en kvittering — musik er en sansning."""
    from datetime import UTC, datetime

    from core.services import active_sensing_daemon as asd
    from core.services import ambient_sound_daemon as amb

    monkeypatch.setattr(
        amb, "_capture_sample",
        lambda save_wav=True: ("music", 0.0312, 0.0081, None),
    )

    svar = asd._sense_audio({}, datetime.now(UTC))

    assert svar["ok"] is True
    assert svar["reason"] == "audio_music"


def test_mixed_post_beholder_lyd_halvdelen(isolated_runtime, monkeypatch) -> None:
    """Mixed-posten skal bære BEGGE sanser — også efter stillads-gaten.

    Målt 8/11-2026: 13 af 40 mixed-poster i 30 dage indeholdt «Jeg så og
    lyttede samtidig» men IKKE «Lyd:». Aarsagen var at `_sense_mixed` byggede
    lyd-delen af `preview` — «category=talk amplitude=0.0215» — og
    `_PROMPT_EKKO_MOENSTRE` klipper ved `amplitude \\d`. Posten blev derfor
    arkiveret som om begge sanser indgik, men bar kun den visuelle halvdel.

    Gaten er det punkt hvor tabet skete, saa det er der vagten maaler.
    """
    from core.services import active_sensing_daemon as asd
    import core.services.sensory_archive as arkiv

    skrevet: list[str] = []
    monkeypatch.setattr(
        arkiv, "record_mixed",
        lambda content, **kw: skrevet.append(content) or {"id": "x"},
    )
    monkeypatch.setattr(
        asd, "_sense_visual",
        lambda state, now, **kw: {
            "ok": True, "description": "Rummet er stille og køligt.",
            "preview": "Rummet er stille og køligt.", "reason": "visual_captured",
        },
    )
    monkeypatch.setattr(
        asd, "_sense_audio",
        lambda state, now, **kw: {
            "ok": True, "preview": "category=talk amplitude=0.0215",
            "reason": "audio_talk", "category": "talk", "amplitude_mean": 0.0215,
        },
    )

    asd._sense_mixed({}, datetime.now(UTC))

    assert len(skrevet) == 1, "mixed skal give praecis én post"
    tekst, _ = arkiv._uden_stillads(skrevet[0])
    assert "Lyd: talk" in tekst, f"lyd-halvdelen blev klippet væk: {tekst!r}"
    assert "Visuelt: Rummet er stille" in tekst, f"den visuelle halvdel forsvandt: {tekst!r}"


def test_lyd_postens_klassifikation_overlever_stillads_gaten(
    isolated_runtime, monkeypatch
) -> None:
    """Et lyt er sin KLASSIFIKATION — amplituden er maalingen bag den.

    Målt 8/11-2026: to lyd-poster i arkivet stod som «Jeg lyttede til rummet.»
    — 23 tegn, over `_MINDSTE_INDTRYK`, og derfor gemt som et indtryk uden
    indhold. Amplituden i `content` blev klippet af samme moenster, og
    klassifikationen forsvandt med den. Den hoerer i metadata.
    """
    from core.services import active_sensing_daemon as asd
    from core.services import ambient_sound_daemon as amb
    import core.services.sensory_archive as arkiv

    monkeypatch.setattr(
        amb, "_capture_sample",
        lambda save_wav=True: ("talk", 0.0215, 0.0100, None),
    )

    svar = asd._sense_audio({}, datetime.now(UTC))

    assert "amplitude" not in svar["description"], (
        f"amplituden staar i indtrykket og bliver klippet væk: {svar['description']!r}"
    )
    tekst, _ = arkiv._uden_stillads(svar["description"])
    assert "talk" in tekst, f"klassifikationen forsvandt gennem gaten: {tekst!r}"


def test_lyd_postens_amplituden_naar_metadata(isolated_runtime, monkeypatch) -> None:
    """Flyttet, ikke slettet: maalingen skal stadig kunne slas op."""
    from core.services import active_sensing_daemon as asd
    from core.services import ambient_sound_daemon as amb

    monkeypatch.setattr(
        amb, "_capture_sample",
        lambda save_wav=True: ("music", 0.0312, 0.0081, None),
    )

    svar = asd._sense_audio({}, datetime.now(UTC))

    assert svar["category"] == "music"
    assert svar["amplitude_mean"] == 0.0312


def test_mixed_paastaar_ikke_at_den_lyttede_naar_lyden_var_stilhed(
    isolated_runtime, monkeypatch
) -> None:
    """Praefikset maa kun paastaa den sansning der faktisk gav et indtryk.

    Maalt 8/11-2026: 160 af 273 mixed-poster i 60 dage sagde «Jeg saa og
    lyttede samtidig», mens `audio_status` var `audio_silence_not_an_impression`
    — lyden var stilhed, blev korrekt udeladt, og teksten paastod alligevel en
    sansning som metadata modsiger.
    """
    from core.services import active_sensing_daemon as asd
    import core.services.sensory_archive as arkiv

    skrevet: list[str] = []
    monkeypatch.setattr(
        arkiv, "record_mixed",
        lambda content, **kw: skrevet.append(content) or {"id": "x"},
    )
    monkeypatch.setattr(
        asd, "_sense_visual",
        lambda state, now, **kw: {
            "ok": True, "description": "Rummet er stille og køligt.",
            "preview": "Rummet er stille og køligt.", "reason": "visual_captured",
        },
    )
    monkeypatch.setattr(
        asd, "_sense_audio",
        lambda state, now, **kw: {
            "ok": False, "preview": "category=silence amplitude=0.0000",
            "reason": "audio_silence_not_an_impression",
        },
    )

    asd._sense_mixed({}, datetime.now(UTC))

    assert len(skrevet) == 1
    tekst = skrevet[0]
    assert "lyttede" not in tekst, f"posten paastaar en sansning der ikke skete: {tekst!r}"
    assert tekst.startswith("Jeg så på rummet."), tekst


def test_mixed_siger_begge_dele_naar_begge_gav_indtryk(
    isolated_runtime, monkeypatch
) -> None:
    """Den anden retning: naar lyden ER et indtryk, skal posten sige det."""
    from core.services import active_sensing_daemon as asd
    import core.services.sensory_archive as arkiv

    skrevet: list[str] = []
    monkeypatch.setattr(
        arkiv, "record_mixed",
        lambda content, **kw: skrevet.append(content) or {"id": "x"},
    )
    monkeypatch.setattr(
        asd, "_sense_visual",
        lambda state, now, **kw: {
            "ok": True, "description": "Rummet er stille og køligt.",
            "preview": "Rummet er stille og køligt.", "reason": "visual_captured",
        },
    )
    monkeypatch.setattr(
        asd, "_sense_audio",
        lambda state, now, **kw: {
            "ok": True, "preview": "category=talk amplitude=0.0215",
            "reason": "audio_talk", "category": "talk", "amplitude_mean": 0.0215,
        },
    )

    asd._sense_mixed({}, datetime.now(UTC))

    assert skrevet[0].startswith("Jeg så og lyttede samtidig."), skrevet[0]
