"""Fanger korrektions-detektionen den måde Bjørn faktisk retter på?

Målt 7/9-2026 mod hans ordrette beskeder fra dagen og 400 rigtige
chat-beskeder. Svaret var nej — og den fejlede i BEGGE retninger:

    dækning   40 %   (4 af 10 rettelser)
    præcision 25 %   (12 af 16 træf var ikke rettelser)

Efter rettelserne her: 60 % / 60 %.
"""

from __future__ import annotations

import pytest

from core.services.experience_correction_listener import _looks_like_correction as f


# ── de falske positiver der dominerede ──────────────────────────────────

@pytest.mark.parametrize("tekst", [
    "Du stoppede?", "du stoppede?", "Du stopper igen?", "Du stoppet?",
])
def test_du_stoppede_er_ikke_en_rettelse(tekst):
    """Syv af otteogtyve træf var dette.

    Mønsteret var `\\bstop\\s*(det|nu|med)?` — uden afsluttende ordgrænse, så
    det matchede «stoppede». Bjørn SPØRGER hvorfor Jarvis holdt op; det er
    ikke en rettelse, det er en observation.
    """
    assert f(tekst) is False


@pytest.mark.parametrize("tekst", [
    "Nej det er okay, vi har fri nu..  :)",
    "Nej det er okay nu. Har løst det :)",
    "Nej, det er okay for nu. Vi ser om det var enkeltstående.",
    "nej det er fint",
    "Nej det er i orden",
])
def test_nej_det_er_okay_er_en_ACCEPT(tekst):
    """Dansk accepterer med «nej»: «nej tak, det er fint».

    Seks af otteogtyve træf var Bjørn der sagde at det var i orden — det
    modsatte af en rettelse.
    """
    assert f(tekst) is False


# ── det den skal fange ──────────────────────────────────────────────────

@pytest.mark.parametrize("tekst", [
    "nej jeg slog tilgængelighed fra??",
    "Nej det er ikke dig i denne session der ser.. det er stadig en anden model..",
    "Det var ikke det, jeg mente.",
    "jeg må dog rette dig på et punkt.. hvad der ligger i runtime",
    "vigtigt info, det gik lige op for mig han kørte på vision modelen.",
    "stop lige, bash session skal ikke ændres",
])
def test_bjoerns_egne_rettelser_fanges(tekst):
    """Ordrette rettelser fra 7/9.

    «jeg må rette dig» og «vigtigt info» stod ikke i mønstrene — og det er
    netop dem han bruger når han retter eksplicit.
    """
    assert f(tekst) is True


# ── loftet, sagt ærligt ─────────────────────────────────────────────────

@pytest.mark.parametrize("tekst", [
    "det er random.. til tider sker det osse for flash uden syn",
    "alle dem du nævner der bruger jeg ofte",
    "det er en gate, destruktiv commando i /tmp rm -rf",
])
def test_faktuelle_rettelser_fanges_STADIG_ikke(tekst):
    """Bjørns hyppigste måde at rette på: han leverer den manglende kendsgerning.

    Der er ingen markør i sætningen. Den er kun en rettelse i forhold til hvad
    Jarvis lige har sagt — og dét kan et mønster ikke se. Testen står her for
    at loftet er MÅLT og ikke glemt: skal de fanges, kræver det en
    sammenligning med foregående svar, ikke flere nøgleord.
    """
    assert f(tekst) is False


def test_tom_besked_er_ikke_en_rettelse():
    assert f("") is False
    assert f("   ") is False
