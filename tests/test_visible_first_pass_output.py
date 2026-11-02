"""Den første synlige modelstrøm må beholde tid internt, ikke på skærmen."""
from __future__ import annotations

import pathlib

import pytest

from core.services.visible_first_pass_output import FirstPassOutputFilter


def _stream(text: str, chunk: int) -> str:
    output = FirstPassOutputFilter()
    shown = "".join(output.feed(text[i:i + chunk]) for i in range(0, len(text), chunk))
    return shown + output.flush()


@pytest.mark.parametrize("chunk", range(1, 48))
def test_first_pass_skjuler_transskript_tid_for_alle_chunkgraenser(chunk):
    text = (
        "[2026-10-23 21:59] [2026-10-23 21:59] "
        "Det synlige svar."
    )
    assert _stream(text, chunk) == "Det synlige svar."


def test_first_pass_bevarer_capability_filteret():
    text = 'før <capability-call id="tool:read" /> efter'
    shown = _stream(text, 3)
    assert "capability-call" not in shown
    assert "før" in shown and "efter" in shown


def test_first_pass_udstiller_fundne_citationer_til_turens_metadata():
    """Regression: visible_runs må kunne læse fundene uden AttributeError."""
    from core.services.citation_markorer import Kilder

    output = FirstPassOutputFilter(
        Kilder(web={"ref-a": "https://example.dk/a"})
    )
    assert output.feed("Se kilden 【cite|ref-a】.") == "Se kilden ."
    output.flush()

    assert len(output.fundet) == 1
    assert output.fundet[0].refs == ("ref-a",)


def test_filteret_er_koblet_paa_first_pass_i_runtime():
    """Filteret skal være monteret — og det skal have turens kilder med.

    2/11-2026: her stod den ordrette streng `FirstPassOutputFilter()`. Den
    matcher ikke længere, fordi filteret nu får kilder med — og det er hele
    pointen: uden dem er `Kilder()` tom, og så afvises ALLE citationer
    fail-closed. Vagten måler derfor koblingen og argumentet, ikke
    parentesens indhold.
    """
    source = pathlib.Path("core/services/visible_runs.py").read_text()
    assert "markup_buffer = FirstPassOutputFilter(" in source
    assert "safe_text = markup_buffer.feed(item.delta)" in source
    assert "remaining = markup_buffer.flush()" in source
    # Kilderne skal være den SAMME beholder som turen fylder — ellers fyldes
    # en tom instans ved siden af den filteret læser.
    assert "_turn_kilder" in source, "filteret får ikke turens kilder"
    assert "FirstPassOutputFilter(_turn_kilder)" in source, (
        "filteret instantieres uden kilder — så afvises alle citationer"
    )
    assert "TurnAccumulator(kilder=_turn_kilder)" in source, (
        "turen og filteret deler ikke kilder — de to beholdere divergerer"
    )
