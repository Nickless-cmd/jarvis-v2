"""De to rolle-lister må ikke kunne divergere (2/10-2026).

Bjørn: «ret de to rolle-lister til én — med test».

Baggrunden, målt: `_TOOL_USING_ROLES` (agent_runtime_base.py) og `_TOOL_ROLES`
(agent_runtime_spawn.py) betød det SAMME — «hvilke roller må kalde værktøjer» —
men var skrevet som to literaler i to filer. De var drevet fra hinanden:
`synthesizer` stod i base men manglede i spawn, så en synthesizer-agent ikke
fik opgraderet en model under capability-gulvet (0,6) i spawn-blokken.

Rettelsen er at spawn ARVER fra base. `_TOOL_ROLES` er en LOKAL variabel inde i
`spawn_agent_task` (ikke et modul-attribut), så testen her måler den ægte vej:
at spawn-blokken læser `_TOOL_USING_ROLES` — og at den fanger synthesizer.
"""

from __future__ import annotations

import inspect


def test_spawn_laeser_rollelisten_fra_base():
    """Kilden skal være `_TOOL_USING_ROLES` — ikke en lokal literal.

    Kildetekst-tjekket er med vilje: en fremtidig literal med samme indhold
    ville bestå et adfærds-tjek og alligevel kunne drive igen. Vi vil have
    ÉN kilde, ikke to der tilfældigvis er enige i dag.
    """
    from core.services import agent_runtime_spawn as S

    kilde = inspect.getsource(S.spawn_agent_task)
    assert "_TOOL_ROLES = _TOOL_USING_ROLES" in kilde, (
        "spawn's rolle-liste er en selvstændig literal igen — den skal arve "
        "fra `_TOOL_USING_ROLES`, ellers kan de to divergere som de gjorde "
        "med `synthesizer`"
    )
    # Og den gamle literal må ikke stå der længere.
    assert '"devils_advocate", "watcher", "synthesizer"}' not in kilde
    assert '{"researcher", "critic", "planner", "executor", "watcher", "devils_advocate"}' not in kilde


def test_synthesizer_er_med_i_kilden():
    """Den konkrete drift der blev rettet: synthesizer manglede i spawn.

    Regressionen er præcis denne rolle — den stod i base, ikke i spawn, og
    konsekvensen var tavs (ingen opgradering af en svag model).
    """
    from core.services.agent_runtime_base import _TOOL_USING_ROLES

    assert "synthesizer" in _TOOL_USING_ROLES


def test_de_syv_tool_roller_plus_reviewer_er_intakte():
    """Rettelsen må ikke have tabt nogen undervejs.

    De syv roller er dem der faktisk kalder værktøjer; filosof/etiker er
    refleksions-roller og hører ikke her.
    """
    from core.services.agent_runtime_base import _TOOL_USING_ROLES

    ventet = {
        "researcher", "critic", "planner", "executor",
        "devils_advocate", "watcher", "synthesizer",
        "reviewer",        # agent-contract-v1 F5: den uafhaengige, skrivebeskyttede reviewer (review_agent_work)
    }
    assert set(_TOOL_USING_ROLES) == ventet
    # Refleksions-rollerne skal IKKE være med — de kalder ikke værktøjer.
    assert "filosof" not in _TOOL_USING_ROLES
    assert "etiker" not in _TOOL_USING_ROLES


def test_begge_veje_til_rollelisten_er_enige():
    """`_role_needs_tools` og spawn-blokken skal svare det SAMME.

    Det var netop uenigheden mellem de to veje der var fejlen: base sagde
    «synthesizer kan kalde værktøjer», spawn sagde «nej». Testen her binder
    dem sammen, så en fremtidig ændring i den ene fanges af den anden.
    """
    from core.services.agent_runtime_base import (
        _TOOL_USING_ROLES,
        _role_needs_tools,
    )

    for rolle in _TOOL_USING_ROLES:
        assert _role_needs_tools(rolle), rolle
    # Og negativt: en refleksions-rolle skal svare nej begge steder.
    assert not _role_needs_tools("filosof")
    assert not _role_needs_tools("etiker")
