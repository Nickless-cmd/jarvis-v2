"""Agentens EGEN dæknings-erklæring vinder over teksttællingen (27/10-2026).

Krav (Bjørn 26/10): "Jarvis skal altid vide, hvad den nåede, hvad den ikke nåede, og
hvorfor arbejdet stoppede."

MAALT 27/10-2026 på `asg-57f9d4917a884776` (researcher, run-92841eba58574974) — den
kørsel der gjorde kontrakten nødvendig. Agenten svarede korrekt på spørgsmål 1 og 2, og
skrev på spørgsmål 3:

    "3) Jeg kunne ikke verificere fil og linjenummer for funktionen _unanswered_questions"

Det er en AFVISNING, ikke et svar. Alligevel gav `_unanswered_questions` **0**, kørslen
blev meldt `completed` med tom `error_code`, og et af tre spørgsmål forsvandt ud af
status. Samme fejlklasse var målt to gange tidligere samme døgn: en feltliste
("1. goal: str") blev læst som svar på spørgsmål 1-3, og "1) 2) 3)"-nummereringen var
usynlig for en regex der krævede ordet "spørgsmål".

Tre lap på en tekstheuristik, tre nye huller. Denne vagt går en anden vej: den læser
agentens egen erklæring i stedet for at gætte ud fra dens formatering.

GRÆNSEN, som ikke skal skjules: en agent der IKKE skriver linjen er stadig underlagt
teksttællingen, og den kan stadig tage fejl. Kontrakten gør erklæringen eksplicit og
efterprøvbar — den gør ikke agenten ufejlbarlig.
"""
from __future__ import annotations

import pytest

from core.services.agent_loop_core import (
    _declared_coverage,
    _unanswered_questions,
)

D = "D\u00c6KNING"

OPGAVE = """Besvar disse tre spørgsmål om kodebasen.

1) Hvor mange felter har skemaet for værktøjet Task?
2) Hvilken tabel holder agent-assignment-mandater?
3) Hvor ligger funktionen _unanswered_questions?"""

# Den målte leverance, ordret i sin form: 1 og 2 besvaret, 3 afvist.
SVAR_1_OG_2 = """**Findings**
1) Task-værktøjets skema har 5 properties.
2) Tabellen hedder agent_assignment_mandates (linje 29).
3) Jeg kunne ikke verificere fil og linjenummer for funktionen _unanswered_questions."""


def test_den_maalte_koersel_bliver_en_hul_naar_agenten_erklaerer_det():
    """Kernen i kontrakten: agenten siger 1,2 — så er 3 et hul, ikke et svar."""
    tekst = SVAR_1_OG_2 + f"\n\n{D}: 1,2"
    assert _unanswered_questions(OPGAVE, tekst) == 1


@pytest.mark.parametrize("form", [
    f"{D}: 1,2",
    f"**{D}:** 1,2",          # markdown-fed — agenter skriver sådan
    f"- {D}: 1,2",            # punktopslag
    f"{D}: 1,2 AF 3",         # med total angivet bagefter
    f"{D}: 1, 2",             # med mellemrum efter komma
])
def test_formatering_maa_ikke_goere_kontrakten_blind(form):
    """En kontrakt der fejler på **fed** eller en tankestreg er lige så blind som regex'en."""
    assert _unanswered_questions(OPGAVE, SVAR_1_OG_2 + "\n\n" + form) == 1


def test_ingen_besvaret_er_en_erklaering_ikke_en_mangel():
    """"DÆKNING: ingen" skal give 3 huller — ikke falde tilbage på tællingen.

    MÅLT FØR RETTELSEN: regex'en krævede et TAL, så "ingen" gav ``None`` = "ingen
    erklæring", hvorefter tællingen svarede 0. En agent der erklærede at den intet
    havde besvaret blev altså meldt færdig.
    """
    tekst = SVAR_1_OG_2 + f"\n\n{D}: ingen"
    assert _declared_coverage(tekst) == set()
    assert _unanswered_questions(OPGAVE, tekst) == 3


def test_alle_besvaret_giver_nul():
    tekst = SVAR_1_OG_2 + f"\n\n{D}: 1,2,3"
    assert _unanswered_questions(OPGAVE, tekst) == 0


def test_uden_linje_er_adfaerden_uaendret():
    """Fallback'et skal bestå: en agent der ikke skriver linjen må ikke straffes.

    Kontrakten kan kun gøre målingen bedre. Efterlader den en tidligere korrekt kørsel
    som fejl, er den en regression forklædt som en forbedring.
    """
    assert _declared_coverage(SVAR_1_OG_2) is None
    # Uændret teksttælling — inkl. dens kendte fejl (afvisningen tælles som svar).
    assert _unanswered_questions(OPGAVE, SVAR_1_OG_2) == 0


def test_en_feltliste_kan_ikke_naere_kontrakten():
    """Den oprindelige fejl: en liste over 8 felter blev læst som 8 svar."""
    feltliste = "1. goal: str\n2. scope_files: tuple[str, ...]\n3. allowed_tools: tuple[str, ...]"
    assert _unanswered_questions(OPGAVE, feltliste) == 3
    # Og med en ærlig erklæring oveni: kun det agenten faktisk dækkede forsvinder.
    assert _unanswered_questions(OPGAVE, feltliste + f"\n\n{D}: 1") == 2


def test_enkelthoersmaal_opgave_er_stadig_tavs():
    """Vagten fyrer kun når opgaven FAKTISK stiller flere spørgsmål."""
    enkelt = "1) Hvad hedder tabellen?"
    assert _unanswered_questions(enkelt, "Ingen anelse.") == 0
    assert _unanswered_questions(enkelt, f"Ingen anelse.\n\n{D}: ingen") == 0
