"""Vagten skal kunne SE opgaven — ogsaa naar spoergsmaalene er ren nummerering (26/10-2026).

MAALT 26/10-2026 paa `asg-a413aa7ac3704131` (run-3ff74d5e954946f6), et rigtigt Task-kald
sendt fra Jarvis selv:

  Opgaven skrev spoergsmaalene som   "1)"  "2)"  "3)"
  Den gamle `_QUESTION_RE` kraevede ordet "spoergsmaal" foran tallet.
  => den fandt NUL spoergsmaal, returnerede 0 ubesvarede
  => `incomplete` blev aldrig sat
  => agenten, der svarede paa 1 af 3 og stoppede midt i saetningen, blev meldt `completed`
     med `error_code: ""`, `error_phase: ""`, `has_partial: false`

Det er ikke en manglende gate. Det er en gate hvis TAVSHED betoed "jeg kunne ikke se
opgaven", ikke "alt er besvaret" — samme fejlklasse som en groen vagt der matcher alt.

Disse tests laaser FORMEN, ikke implementeringen: spoergsmaalene skal findes uanset om de
skrives med ord foran eller som ren nummerering, og en enkeltspoergsmaal-opgave skal
stadig vaere helt tavs (ellers er vagten stoj).
"""
from __future__ import annotations

import pytest

from core.services.agent_loop_core import _question_numbers, _unanswered_questions

# Den faktiske opgaveform der gjorde vagten blind: ren nummerering.
OPGAVE_PAREN = """Besvar disse tre spoergsmaal om kodebasen i /media/projects/jarvis-v2.

1) Hvor mange felter har skemaet for vaerktoejet Task?
2) Hvad hedder tabellen der gemmer agent-mandater?
3) Hvor mange steder sammenlignes der med semikolon?
"""

# Samme opgave med ordet foran — den form der ALLEREDE virkede.
OPGAVE_ORD = """Besvar disse tre spoergsmaal.

SPØRGSMÅL 1: Hvor mange felter har Task?
SPØRGSMÅL 2: Hvad hedder tabellen?
SPØRGSMÅL 3: Hvor mange steder?
"""

OPGAVE_PUNKT = "1. Hvor mange felter?\n2. Hvad hedder tabellen?\n3. Hvor mange steder?\n"

OPGAVE_STJERNE = "- 1) Hvor mange felter?\n- 2) Hvad hedder tabellen?\n- 3) Hvor mange steder?\n"

OPGAVE_ENKELT = "Maal i kodebasen: hvor mange steder kalder koden dispatch_agent("

SVAR_1_AF_3 = "1. Fem felter (agent_contract_tools.py:59-67).\n"


# ── Kernen: alle skrivemaader skal give de SAMME numre ──────────────────────────────
@pytest.mark.parametrize(
    "opgave",
    [OPGAVE_PAREN, OPGAVE_ORD, OPGAVE_PUNKT, OPGAVE_STJERNE],
    ids=["1)-form", "SPØRGSMÅL-form", "1.-form", "- 1)-form"],
)
def test_alle_skrivemaader_giver_samme_spoergsmaalsnumre(opgave):
    """Fem former, ét svar. Ellers afhaenger markeringen af hvordan opgaven blev skrevet —
    og det var praecis fejlen: samme indhold, to vidt forskellige udfald."""
    assert _question_numbers(opgave) == {1, 2, 3}


# ── Den maalte koersel: 1)-formen maa ikke laengere give nul ───────────────────────
def test_paren_formen_fandt_foer_nul_spoergsmaal():
    """Den gamle regex returnerede `set()` her. Det var hele aarsagen til den falske
    `completed` — ikke at agenten snød, men at vagten var blind."""
    assert _question_numbers(OPGAVE_PAREN) == {1, 2, 3}
    assert _unanswered_questions(OPGAVE_PAREN, SVAR_1_AF_3) == 2


def test_paren_formen_paa_det_faktiske_svar_markerer_huller():
    """Agenten skrev 'Nu spoergsmaal 2' i prosa — ikke nummereret. Det taelles som hul,
    og det er konservativt med vilje: hellere overrapportere end melde 'faerdig'."""
    svar = (
        "Confirmed: Task har 5 properties: description, model, prompt, run_in_background, "
        "subagent_type.\n\nNu spoergsmaal 2 — database-tabel for agent-assignment-mandater."
    )
    assert _unanswered_questions(OPGAVE_PAREN, svar) == 3


def test_paren_formen_fuldt_besvaret_giver_nul():
    """Vagten skal ogsaa kunne sige 'alt er der' i den nye form — ellers er den bare stoj."""
    svar = "1. Fem felter.\n2. agent_assignment_mandates.\n3. Tre steder.\n"
    assert _unanswered_questions(OPGAVE_PAREN, svar) == 0


# ── Tavsheden skal bevares: en enkeltspoergsmaal-opgave maa ALDRIG rammes ───────────
def test_enkeltspoergsmaal_er_stadig_tavs():
    """Maalt: 1 af 60 historiske agent-opgaver har flere nummererede spoergsmaal. For de
    59 andre skal vagten vaere helt tavs — en vagt der fanger alt er lige saa ubrugelig."""
    assert _unanswered_questions(OPGAVE_ENKELT, "22 rene kald.") == 0
    assert _unanswered_questions("", "") == 0


def test_et_enkelt_nummer_i_opgaven_taeller_ikke_som_flere():
    """Graensen er to fundne spoergsmaal. Ét nummer kan vaere en liste, en fodnote eller
    en henvisning — ikke en flerhed der skal besvares."""
    assert _question_numbers("1) Hvor mange felter har Task?") == {1}
    assert _unanswered_questions("1) Hvor mange felter har Task?", "Svar her.") == 0


def test_henvisning_midt_i_prosa_er_ikke_et_nummereret_spoergsmaal():
    """Nummereringen skal staa ved linjestart. 'Se punkt 1) nedenfor' er en henvisning,
    ikke et spoergsmaal — ellers ville hver parentes i en tekst blive talt som et hul."""
    assert _question_numbers("Se punkt 1) nedenfor.") == set()
    assert _unanswered_questions("Se punkt 1) nedenfor.", "Svar her.") == 0
