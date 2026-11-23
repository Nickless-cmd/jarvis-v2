"""Prompt-sektionen skal pege paa det RIGTIGE vaerktoej pr. posttype.

MAALT 23/11-2026: `initiatives_prompt_section` endte med én instruktion —
«afvis den med `decline_initiative(id, reason=...)`» — uanset hvad posten var.
`get_pending_initiatives()` skelner ikke paa type, saa et livsprojekt
(`long_term_intention`) fik samme instruktion som en almindelig impuls.

Det er ikke et ukendt vaerktoej (den vagt fandtes allerede og var groen), det er
et FORKERT et: `decline_initiative` saetter `declined` — dommen «praemissen var
forkert». `abandon_initiative` saetter `expired` — dommen «jeg baerer den ikke
videre», som er praecis den dom livsprojekt-dommeren selv afgiver. Et livsprojekt
der ikke blev loeftet er ikke det samme som et der ikke duede.
"""

from __future__ import annotations

import re

from core.services import initiative_queue


def _sektion_efter_livsprojekt() -> str:
    initiative_queue.seed_long_term_intention(
        title="En retning der ikke kan koeres faerdigt",
        why="Test: sektionen skal pege paa abandon, ikke decline.",
    )
    section = initiative_queue.initiatives_prompt_section()
    assert section, "prompt-sektionen blev ikke genereret trods et forfaldent livsprojekt"
    return section


def test_livsprojekt_faar_abandon_og_ikke_decline(isolated_runtime) -> None:
    """Kernen i fejlen: den forkerte dom bliver givet til den forkerte posttype."""
    section = _sektion_efter_livsprojekt()

    assert "`abandon_initiative(" in section, (
        "sektionen peger ikke paa abandon_initiative — saa kan posten ikke lukkes "
        "med den rigtige dom"
    )
    assert "`decline_initiative(" not in section, (
        "sektionen peger paa decline_initiative for et livsprojekt: den stempler "
        "posten som forkert, hvilket er en anden dom end 'jeg baerer den ikke videre'"
    )


def test_livsprojektet_er_markeret_i_linjen(isolated_runtime) -> None:
    """Uden markering kan jeg ikke se hvilken post der er en retning og hvilken en opgave."""
    section = _sektion_efter_livsprojekt()
    assert "[livsprojekt" in section, "livsprojektet er ikke markeret i sektionen"


def test_almindelig_impuls_faar_stadig_decline(isolated_runtime) -> None:
    """Regression: den oprindelige instruktion maa ikke forsvinde for impulserne."""
    initiative_queue.push_initiative(
        focus="En almindelig impuls der ikke er et livsprojekt",
        source="jarvis-tool",
        priority="high",
    )
    section = initiative_queue.initiatives_prompt_section()
    assert section, "prompt-sektionen blev ikke genereret trods en pending impuls"

    assert "`decline_initiative(" in section
    assert "`abandon_initiative(" not in section, (
        "abandon-instuktionen fylder i prompten uden at der er et livsprojekt — "
        "sektionen holdes bevidst kort (latens + cache)"
    )


def test_begge_typer_giver_begge_instruktioner(isolated_runtime) -> None:
    """Naar begge er til stede, skal begge veje vaere navngivet."""
    initiative_queue.push_initiative(
        focus="En impuls ved siden af et livsprojekt",
        source="jarvis-tool",
        priority="high",
    )
    section = _sektion_efter_livsprojekt()

    assert "`decline_initiative(" in section
    assert "`abandon_initiative(" in section


def test_alle_naevnte_vaerktoejer_findes_i_fladen(isolated_runtime) -> None:
    """Udvidet udgave af den eksisterende vagt — nu med et livsprojekt til stede.

    Den gamle vagt koerte kun med en almindelig impuls, saa abandon-stien blev
    aldrig gennemloebet af den.
    """
    from core.tools.simple_tools_definitions import TOOL_DEFINITIONS

    section = _sektion_efter_livsprojekt()
    kendte = {
        d["function"]["name"]
        for d in TOOL_DEFINITIONS
        if isinstance(d, dict) and "function" in d
    }
    naevnte = set(re.findall(r"`([a-z_][a-z0-9_]+)\(", section))
    assert naevnte, "sektionen naevner ingen vaerktoejer — saa er vagten blind"
    ukendte = naevnte - kendte
    assert not ukendte, f"prompten naevner vaerktoejer der ikke findes i fladen: {sorted(ukendte)}"
