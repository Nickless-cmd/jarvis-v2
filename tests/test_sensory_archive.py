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
