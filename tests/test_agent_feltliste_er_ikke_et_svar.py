"""En feltliste er INDHOLDET af et svar — ikke et svar paa et nummereret spoergsmaal.

MAALT 27/10-2026 paa `asg-cb17dfab58834177` (agent-938baa9cc4494d2e859c313cb4d02322,
run-3e88f47bb99847f4):

  * opgaven stillede TRE nummererede spoergsmaal ("1)" "2)" "3)")
  * agenten svarede kun paa spoergsmaal 1, og skrev selv at den kun daekkede det ene
  * svaret paa spoergsmaal 1 var en nummereret liste over otte felter:
        "1. `goal: str`", "2. `scope_files: tuple[str, ...]`", "3. `allowed_tools: ...`"
  * de tre tal blev laest som svar paa spoergsmaal 1, 2 og 3
  * `qs - answered` blev tom → kørslen blev meldt `completed` med tom `error_code`

Det er den FARLIGE retning: en halv leverance meldt faerdig. Denne vagt laaser at
tællingen ikke kan narres af en liste, og — lige saa vigtigt — at den stadig TAELER
et rigtigt svar, ogsaa naar svaret indeholder et kolon ("Fil: x.py:139").
"""
from __future__ import annotations

from core.services.agent_loop_core import (
    _answered_numbers,
    _question_numbers,
    _unanswered_questions,
)

OPGAVE_3 = """Besvar disse tre spoergsmaal om kodebasen.

1) Hvor mange felter har skemaet for vaerktoejet Task?
2) Hvilken tabel gemmer agent-assignment-mandater?
3) Hvilken fil og linje definerer _unanswered_questions?
"""

#: Ordret fra den maalte koersel. Ingen omskrivning — det er formen der bedrog tællingen.
FELTLISTE_SOM_SVAR = """**Svar paa spoergsmaal 1**

1. `goal: str`
2. `scope_files: tuple[str, ...]`
3. `allowed_tools: tuple[str, ...]`
4. `max_rounds: int`

Kun spoergsmaal 1 besvaret, som instrueret.
"""

#: Samme opgave, men besvaret i prosa — dette SKAL taelles som tre svar.
PROSA_SVAR = """1. Task har 5 felter: description, prompt, subagent_type, model, run_in_background.
2. Tabellen heder agent_assignment_mandates og oprettes i db_agent_mandate.py.
3. Fil: core/services/agent_loop_core.py:139 — funktionen _unanswered_questions.
"""


def test_feltliste_taelles_ikke_som_svar():
    """Den maalte fejl: otte feltdeklarationer blev laest som otte besvarede spoergsmaal."""
    assert _question_numbers(OPGAVE_3) == {1, 2, 3}
    assert _answered_numbers(FELTLISTE_SOM_SVAR, {1, 2, 3}) == set(), (
        "en feltdeklaration er ikke et svar paa et nummereret spoergsmaal"
    )
    assert _unanswered_questions(OPGAVE_3, FELTLISTE_SOM_SVAR) == 3, (
        "en halv leverance maa ikke se ud som en fuld"
    )


def test_prosa_svar_taelles_stadig():
    """Vagten skal ikke goere systemet blindt: rigtige svar SKAL taelle."""
    assert _answered_numbers(PROSA_SVAR, {1, 2, 3}) == {1, 2, 3}
    assert _unanswered_questions(OPGAVE_3, PROSA_SVAR) == 0


def test_kolon_i_prosa_er_ikke_en_type_deklaration():
    """Graensen gaar ved PYTHON-TYPEN, ikke ved kolon. Ellers ville et svar med
    "Fil: x.py:139" blive kastet vaek som om det var en feltliste."""
    tekst = "1. Fil: core/services/agent_loop_core.py:139\n2. Tabel: agent_assignment_mandates\n"
    assert _answered_numbers(tekst, {1, 2}) == {1, 2}


def test_enkeltspoergsmaal_er_stadig_tavs():
    """Kravet om mindst to fundne spoergsmaal staar uaendret."""
    assert _unanswered_questions("Hvor mange felter har Task?", FELTLISTE_SOM_SVAR) == 0


def test_agentens_egen_erkendelse_taelles_ikke_som_daekning():
    """Agenten skrev "Kun spoergsmaal 1 besvaret" — den saetning maa ikke redde tallene.
    Tællingen skal maale FORM, ikke indroemmelser."""
    assert _unanswered_questions(OPGAVE_3, FELTLISTE_SOM_SVAR) > 0
