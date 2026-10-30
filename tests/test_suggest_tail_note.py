"""Vagt for suggest-noten i turens hale.

MÅLT 30/10-2026 (Bjørn): «hvordan gør vi dig bedre til at huske
suggest_next_task i code mode før du afslutter med slut beskeden?»

Reglen fandtes i PRÆFIKSET (~30.000 tegn fra beslutningen), og vagten der
kunne tvinge den var slået fra fordi den skubber `done` og giver
«teleportering». Noten her er den tredje vej: gratis, i halen, tæt på
beslutningen.

Testene dækker tre ting, og den sidste er den vigtigste:
  1. noten siger hvad den skal, og ikke mere
  2. den kan slås fra (ét kald pr. tur)
  3. den er FAKTISK koblet på løkken — ellers er den ren teater
"""

from __future__ import annotations

from pathlib import Path

from core.services.suggest_tail_note import suggest_tail_note

_VISIBLE_RUNS = Path(__file__).resolve().parents[1] / "core" / "services" / "visible_runs.py"


def test_noten_naevner_vaerktoejet_og_placeringen() -> None:
    """Uden navnet og placeringen er noten en henstilling uden indhold."""
    tekst = suggest_tail_note()
    assert "suggest_next_task" in tekst
    assert "FØR" in tekst
    # Kort nok til at den ikke bliver baggrundsstøj som prompt-linjen blev.
    assert len(tekst) < 600, len(tekst)


def test_noten_tillader_et_nej() -> None:
    """En gate der altid siger «bliv ved» må ikke kunne holde turen i live."""
    tekst = suggest_tail_note()
    assert "spring det over" in tekst


def test_allerede_lagt_giver_tom_streng() -> None:
    """Ét kald pr. tur: anden gang er der intet at lægge i halen."""
    assert suggest_tail_note(already_sent=True) == ""


def test_noten_er_koblet_paa_den_levende_loekke() -> None:
    """Struktur-vagt — samme form som `test_scheduled_vejen_kalder_den_faelles_aktiv_guard`.

    En note der ikke kaldes er præcis den teater-form Bjørn peger på: den ser
    ud som om den virker, men indgangsbetingelsen opfyldes aldrig. Denne test
    fanger regressionen at nogen fjerner kaldet igen.
    """
    kilde = _VISIBLE_RUNS.read_text(encoding="utf-8")
    assert "suggest_tail_note" in kilde, "noten er ikke koblet på løkken"
    # `tilfoej_runde` er formen: RAADGIVNING som standard (koster nul runder) og
    # kan ikke akkumulere. `tilfoej_vedvarende` ville gen-sende noten i HVER
    # runde — den fejl kostede op til 40 gentagelser i én tur, og
    # `test_gaterne_bruger_naeste_ikke_vedvarende` vogter netop den.
    assert "_tur_hale.tilfoej_runde(_suggest_note)" in kilde, (
        "noten lægges ikke i turens hale")
    assert "_tur_hale.tilfoej_vedvarende(_suggest_note" not in kilde, (
        "noten er faldet tilbage til «resten af turen» — den gen-sendes hver runde")
