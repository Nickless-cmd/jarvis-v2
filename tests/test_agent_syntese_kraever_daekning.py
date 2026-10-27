"""Det AFSLUTTENDE kald skal kraeve DÆKNING-linjen — ikke kun system-prompten (27/10-2026).

MAALT 27/10-2026 paa `asg-8c08c689239f4ff8` (researcher, run-18c079a314b24e14):

* agenten brugte alle 8 vaerktoejs-runder (8 tool_call + 8 tool_result i events)
* syntese-kaldet fyrede korrekt — det er grenen for "rundebudgettet loeb ud"
* men `_AGENT_SYNTHESIS_DIRECTIVE` naevnte IKKE DÆKNING, saa det afsluttende svar
  blev skrevet uden linjen
* `_declared_coverage()` gav `None`, taellingen faldt tilbage paa heuristikken og
  sagde 3 ubesvarede — hvor det sande tal var 2 (agenten svarede faktisk paa
  spoergsmaal 3, i prosa, uden nummer)

Kontrakten stod i system-prompten hele tiden. Den blev ikke fulgt, fordi den
afsluttende ordre er det der vejer tungest naar modellen skal lukke turen.

Vaernet er et PAR: begge afsluttende ordrer skal baere kontrakten, OG den skal
naevne den aerlige form ("ingen") — ellers kan en agent der ikke svarede paa
noget ikke erklaere det uden at lyve.
"""

from __future__ import annotations

import pytest

from core.services.agent_loop_core import _answers_directive
from core.services.agent_runtime_base import _AGENT_SYNTHESIS_DIRECTIVE


def test_syntese_direktivet_kraever_daekning():
    """Grenen for 'rundebudgettet loeb ud' — den der fejlede i drift."""
    assert "DÆKNING" in _AGENT_SYNTHESIS_DIRECTIVE, (
        "syntese-direktivet mangler DÆKNING-linjen; saa skriver agenten sit "
        "afsluttende svar uden kontrakten og taellingen falder tilbage paa heuristikken"
    )


def test_svar_direktivet_kraever_daekning():
    """Grenen for 'spoergsmaal staar ubesvarede foer budgettet er brugt'."""
    assert "DÆKNING" in _answers_directive(2)


@pytest.mark.parametrize("direktiv", [
    pytest.param(_AGENT_SYNTHESIS_DIRECTIVE, id="syntese"),
    pytest.param(_answers_directive(3), id="svar"),
])
def test_begge_direktiver_naevner_den_aerlige_form(direktiv):
    """'DÆKNING: ingen' skal vaere en tilladt erklaering.

    Uden den kan en agent der ikke besvarede NOGET kun skrive en tom liste —
    og en tom liste er let at forveksle med en glemt linje.
    """
    assert "ingen" in direktiv.lower(), (
        "direktivet naevner ikke 'DÆKNING: ingen'; en agent der ikke svarede paa "
        "noget har saa ingen aerlig form at erklaere det i"
    )


def test_direktiverne_siger_at_ikke_verificeret_ikke_er_besvaret():
    """Kernen i kontrakten: et spoergsmaal man ikke kunne verificere ER ikke besvaret.

    Det var praecis den fejl der blev maalt: agenten skrev et nummereret svar paa
    spoergsmaal 3, men svaret var en afvisning — og taellingen tog nummeret som bevis.
    """
    for d in (_AGENT_SYNTHESIS_DIRECTIVE, _answers_directive(2)):
        low = d.lower()
        assert "ikke" in low and ("besvaret" in low or "verificere" in low), (
            f"direktivet praeciserer ikke at en uverificeret besvarelse ikke taeller: {d!r}"
        )
