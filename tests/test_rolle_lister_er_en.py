"""Rolle-listerne må ikke kunne divergere — og de må ikke lyve (2/10 + 10/11-2026).

Bjørn: «ret de to rolle-lister til én — med test».

Baggrunden, målt 2/10: `_TOOL_USING_ROLES` (agent_runtime_base.py) og
`_TOOL_ROLES` (agent_runtime_spawn.py) betød det SAMME — «hvilke roller må
kalde værktøjer» — men var skrevet som to literaler i to filer, og de var
drevet fra hinanden.

Baggrunden, målt 10/11: rettelsen bandt de to lister sammen, men lod dem
begge være en LITERAL der kunne påstå noget andet end den besluttede.
`synthesizer` og `devils_advocate` stod i listen som værktøjs-brugere med
`default_tool_policy: "none"` — altså nul værktøjer. Konsekvensen var ikke
kosmetisk: `_role_needs_tools` styrer om agenten får en sandboxet
værktøjs-worker eller en ren tekst-tur, så de to roller fik en dyr worker
de ikke kunne bruge.

Rettelsen er at listen UDLEDES af `default_tool_policy` — den beslutning
der allerede findes ét sted. Testen her måler at udledningen er sand, og at
en fremtidig literal ikke kan snige sig ind igen.
"""

from __future__ import annotations

import inspect


def test_spawn_udleder_rollen_i_stedet_for_at_laese_en_literal():
    """Kilden skal kalde `_tool_using_roles()` — ikke en literal.

    Kildetekst-tjekket er med vilje: en literal med samme indhold ville bestå
    et adfærds-tjek og alligevel kunne drive igen. Vi vil have ÉN kilde, ikke
    to der tilfældigvis er enige i dag.
    """
    from core.services import agent_runtime_spawn as S

    kilde = inspect.getsource(S.spawn_agent_task)
    assert "_TOOL_ROLES = _tool_using_roles()" in kilde, (
        "spawn's rolle-liste er ikke længere udledt af `default_tool_policy` — "
        "den skal kalde `_tool_using_roles()`, ellers kan den påstå noget andet "
        "end den besluttede"
    )
    # Den gamle literal må ikke stå der længere.
    assert '"devils_advocate", "watcher", "synthesizer"}' not in kilde
    assert '{"researcher", "critic", "planner", "executor", "watcher", "devils_advocate"}' not in kilde


def test_udledningen_stemmer_med_policyen_for_hver_rolle():
    """Kernen i rettelsen: listen må ikke indeholde en rolle uden værktøjer.

    Det var præcis fejlen — `synthesizer` og `devils_advocate` stod som
    værktøjs-brugere med policy `"none"`. Testen går gennem ALLE templates,
    så en ny rolle med `"none"` ikke kan snige sig ind i listen.
    """
    from core.services.agent_runtime_base import (
        AGENT_ROLE_TEMPLATES,
        _role_needs_tools,
        tools_for_policy,
    )

    for rolle, template in AGENT_ROLE_TEMPLATES.items():
        policy = str(template.get("default_tool_policy") or "")
        antal = len(tools_for_policy(policy))
        assert _role_needs_tools(rolle) == (antal > 0), (
            f"{rolle}: policy {policy!r} giver {antal} værktøjer, men "
            f"_role_needs_tools siger {_role_needs_tools(rolle)} — de to skal "
            f"svare det samme, ellers får agenten en worker den ikke kan bruge"
        )


def test_de_seks_vaerktoejs_roller_er_intakte():
    """Rettelsen må ikke have tabt en rolle undervejs.

    Seks roller har en policy der giver værktøjer. `synthesizer` og
    `devils_advocate` er rene tekstroller (policy `"none"`) og hører ikke
    her — det var netop fejlen at de stod der.
    """
    from core.services.agent_runtime_base import _tool_using_roles

    ventet = {
        "researcher", "critic", "planner", "executor",
        "watcher", "reviewer",   # agent-contract-v1 F5: den uafhaengige reviewer
    }
    assert set(_tool_using_roles()) == ventet
    # Refleksions- og tekstrollerne skal IKKE være med.
    for rolle in ("filosof", "etiker", "synthesizer", "devils_advocate"):
        assert rolle not in _tool_using_roles(), (
            f"{rolle} har policy 'none' og må ikke stå som værktøjs-bruger"
        )


def test_ukendt_rolle_arver_researcher_bunden():
    """Fri tekst er tilladt som rollenavn — og skal følge den template den kører på.

    `spawn_agent_task` falder tilbage til `researcher`-templaten for et ukendt
    navn. Så skal `_role_needs_tools` svare det samme som den template, ellers
    får agenten en anden behandling end dens egen prompt lover.
    """
    from core.services.agent_runtime_base import _role_needs_tools

    assert _role_needs_tools("en-rolle-der-ikke-findes") is True
    assert _role_needs_tools("") is True


def test_begge_veje_til_rollelisten_er_enige():
    """`_role_needs_tools` og den udledte liste skal svare det SAMME."""
    from core.services.agent_runtime_base import _role_needs_tools, _tool_using_roles

    for rolle in _tool_using_roles():
        assert _role_needs_tools(rolle), rolle
    # Og negativt: en refleksions-rolle skal svare nej.
    assert not _role_needs_tools("filosof")
    assert not _role_needs_tools("etiker")
