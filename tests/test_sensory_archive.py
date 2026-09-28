from __future__ import annotations

import pytest


def test_raa_raesonnement_gemmes_ikke_som_indtryk(isolated_runtime) -> None:
    """Målt 18/9: to poster i arkivet var hele reasoning-monologer.

    At strippe taggene ville efterlade monologen og få den til at ligne et
    ægte indtryk — værre end et tomt felt, fordi den så bliver læst som noget
    Jarvis har sanset.
    """
    from core.services.sensory_archive import record_audio

    with pytest.raises(ValueError):
        record_audio(
            "<think>\nOkay, so the user wants me to create a Danish sentence "
            "about the acoustic environment being classified as silence.\n"
        )


def test_svaret_efter_tanken_overlever(isolated_runtime) -> None:
    """Er tanken lukket, er teksten bagefter det rigtige indtryk."""
    from core.services.sensory_archive import record_atmosphere

    post = record_atmosphere(
        "<think>Brugeren vil have en dansk sætning om rummet.</think>\n"
        "Rummet ligger stille med en lav summen fra køleskabet."
    )

    assert "<think>" not in post["content"]
    assert "Brugeren vil have" not in post["content"]
    assert post["content"].startswith("Rummet ligger stille")


def test_almindeligt_indtryk_roeres_ikke(isolated_runtime) -> None:
    from core.services.sensory_archive import record_visual

    tekst = "Skarpt eftermiddagslys gennem vinduet, støv der driver i strålen."
    assert record_visual(tekst)["content"] == tekst


def test_pladsholder_er_ikke_et_indtryk(isolated_runtime) -> None:
    """«Intet mærkbart ændret» er et gyldigt udfald, men ikke et indtryk."""
    from core.services.sensory_archive import er_maettet

    assert er_maettet("Rummet føles tungt og stillestående, tiden står stille.")
    assert not er_maettet("Intet mærkbart ændret.")
    assert not er_maettet("intet maerkbart aendret")
    assert not er_maettet("")
    assert not er_maettet(None)


def test_seneste_maettede_springer_pladsholderne_over(isolated_runtime) -> None:
    """Den rige beskrivelse må ikke ligge ulæst bag fire kvitteringer."""
    from core.services.sensory_archive import record_visual, seneste_maettede

    record_visual("Aftenlys, lange skygger over bordet og en åben bog.")
    for _ in range(4):
        record_visual("Intet mærkbart ændret.")

    fundet = seneste_maettede(modality="visual")

    assert fundet is not None
    assert fundet["content"].startswith("Aftenlys")


def test_seneste_maettede_tier_naar_alt_er_pladsholder(isolated_runtime) -> None:
    """Ingen mættet post i vinduet → sig ingenting, grav ikke i forgårs."""
    from core.services.sensory_archive import record_visual, seneste_maettede

    for _ in range(3):
        record_visual("Intet mærkbart ændret.")

    assert seneste_maettede(modality="visual", kig=3) is None


def test_oversigten_viser_maettede_ikke_kvitteringer(isolated_runtime) -> None:
    """Fem kvitteringer i træk fik læsefladen til at se tom ud."""
    from core.runtime.db_sensory import insert_sensory_memory
    from core.services.sensory_archive import summarize_for_context

    # Eksplicitte tidsstempler. Skrives alle syv inden for samme sekund, er
    # rækkefølgen blandt ens timestamps udefineret, og testen ville måle sin
    # egen fixture i stedet for sorteringen.
    def _skriv(minut: int, tekst: str) -> None:
        insert_sensory_memory(
            modality="visual",
            content=tekst,
            timestamp=f"2026-09-18T10:{minut:02d}:00+00:00",
        )

    _skriv(1, "Morgenlys over bordet, en kop damper stadig.")
    _skriv(2, "Skyggerne er vandret hen over gulvet siden sidst.")
    for nr in range(3, 8):
        _skriv(nr, "Intet mærkbart ændret.")

    oversigt = summarize_for_context(limit=3)

    assert oversigt["total"] == 7, "tællingen dækker HELE arkivet"
    assert oversigt["substantive_in_window"] == 2
    assert [r["content"][:12] for r in oversigt["recent"]] == ["Skyggerne er", "Morgenlys ov"]


# ── Kvitterings-gaten: skrivesiden lukket (28/9-2026) ────────────────────────
#
# Læsesiden (`er_maettet`) har filtreret kvitteringer fra siden 18/9 — men
# arkivet blev ved med at fyldes, og filteret skjulte det bagefter. Her er det
# samme spørgsmål flyttet til det ene punkt alle skrivninger går igennem.


def test_pladsholder_arkiveres_ikke(isolated_runtime) -> None:
    """«Intet mærkbart ændret.» er svaret på at der ikke var noget at se.

    Målt 28/9-2026: 45 sådanne poster i arkivet, den nyeste 26/9 — og hanen
    skrev videre, fordi `visual_memory_daemon` arkiverede hvert svar uanset.
    """
    from core.services.sensory_archive import count, record_visual

    foer = count()
    post = record_visual("Intet mærkbart ændret.")

    assert post["skipped"] is True
    assert post["reason"] == "kvittering"
    assert count() == foer, "arkivet vokser ikke af en kvittering"


def test_silence_lyt_arkiveres_ikke(isolated_runtime) -> None:
    """Et lyt der endte i `silence` er ikke et indtryk — der var intet at høre.

    Målt 28/9-2026: 24 sådanne poster, nyeste 26/9.
    """
    from core.services.sensory_archive import count, record_audio

    foer = count()
    post = record_audio(
        "Jeg lyttede til rummet. Klassifikation: silence "
        "(amplitude 0.0000±0.0000)."
    )

    assert post["skipped"] is True
    assert count() == foer


def test_rigtigt_indtryk_arkiveres_uændret(isolated_runtime) -> None:
    """Gaten må ikke fange det den skal beskytte."""
    from core.services.sensory_archive import record_visual

    tekst = "Skarpt eftermiddagslys gennem vinduet, støv der driver i strålen."
    post = record_visual(tekst)

    assert "skipped" not in post
    assert post["content"] == tekst
    assert post["id"]


def test_en_lyd_der_faktisk_var_noget_arkiveres(isolated_runtime) -> None:
    """Kun `silence` er en kvittering — musik er en sansning."""
    from core.services.sensory_archive import record_audio

    post = record_audio(
        "Jeg lyttede til rummet. Klassifikation: music "
        "(amplitude 0.0312±0.0081)."
    )

    assert "skipped" not in post
    assert post["id"]


def test_mode_always_gendanner_den_gamle_adfaerd(isolated_runtime, monkeypatch) -> None:
    """Indstillingen skal kunne skrues tilbage — ellers er den ikke en beslutning."""
    from core.services import sensory_archive

    monkeypatch.setattr(sensory_archive, "_kvittering_mode", lambda: "always")
    post = sensory_archive.record_visual("Intet mærkbart ændret.")

    assert "skipped" not in post
    assert post["id"]


def test_ukendt_mode_falder_til_skip(monkeypatch) -> None:
    """En slåfejl i indstillingen må ikke åbne hanen igen."""
    from core.services import sensory_archive

    class _Falsk:
        sensory_receipt_archive_mode = "altid-agtig-slåfejl"

    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: _Falsk())
    assert sensory_archive._kvittering_mode() == "skip"


def test_er_kvittering_fanger_begge_familier() -> None:
    from core.services.sensory_archive import er_kvittering

    assert er_kvittering("Intet mærkbart ændret.")
    assert er_kvittering("Ingen ændring.")
    assert er_kvittering(
        "Jeg lyttede til rummet. Klassifikation: silence (amplitude 0.0)."
    )
    assert er_kvittering("Lydbillede: silence")
    assert er_kvittering("")
    assert not er_kvittering("Rummet ligger stille med en lav summen fra køleskabet.")
    # Grænsen: en BESKRIVELSE der nævner 'silence' er et indtryk, ikke en
    # kvittering. Reglen skal være snæver nok til at lade den stå — målt
    # 28/9-2026: arkivet har flere af dem, og de beskriver noget.
    assert not er_kvittering(
        "En akustisk snapshot med kategori 'silence' betyder, at der er en "
        "meget lav lydintensitet i rummet lige nu."
    )
