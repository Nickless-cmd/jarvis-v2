"""Post-tool-genbygningen skal bygge prompten i SAMME rum som resten af turen.

## Hvorfor testen findes

Målt 22/10-2026 i drift: ét run byggede to prompts. Den første fik «CHAT MODE»
(610 tegn), genbygningen 12 sekunder senere fik «UDEN mode-signal» (240 tegn) —
samme run, samme session, samme tråd, inden for runnets levetid. Det var
genbygningen modellen svarede ud fra, så orienteringen blev kastet væk midt i
turen.

Årsagen er ikke en glemt funktion men en kontekst-grænse: `set_tool_scope`
kaldes inde i pumpe-tråden, mens genbygningen kører i `asyncio.to_thread`, hvis
kontekst kopieres fra event-loopet — hvor scopet aldrig blev sat.

## Hvad testen vogter — tre ting, og hvorfor netop de

1. **Adfærd:** scopet er synligt inde i kaldet og ryddet bagefter. En test der
   kun grep'er efter `set_tool_scope` i kilden er grøn også når kaldet står i
   en `if False:`-gren — det er målt, ikke gættet (22/10, to forgæves forsøg).
2. **Kaldestederne:** AST'en må ikke indeholde `asyncio.to_thread` med den RÅ
   `_build_visible_input`. Det fanger at nogen tilføjer et tredje sted uden om
   hjælperen, hvilket er præcis hvordan fejlen opstod.
3. **Cachenøglen:** samme besked i to rum må ikke give samme assembly. Stod
   scope uden for nøglen, kunne genbygningen serve den anden modes prompt.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

VISIBLE_RUNS = Path(__file__).resolve().parents[1] / "core" / "services" / "visible_runs.py"


def test_hjaelperen_saetter_scope_i_worker_traaden_og_rydder_bagefter(monkeypatch):
    """Scope skal være sat INDE i kaldet — og væk igen efter."""
    from core.tools.tool_scoping import current_tool_scope
    from core.services import visible_runs

    set_under_kaldet: list[str] = []

    def falsk_bygger(*args, **kwargs):
        set_under_kaldet.append(current_tool_scope())
        return {"built": True}

    monkeypatch.setattr(visible_runs, "_build_visible_input", falsk_bygger)

    resultat = visible_runs._build_visible_input_with_scope("chat", "hej")

    assert resultat == {"built": True}
    assert set_under_kaldet == ["chat"], (
        "scopet var ikke sat inde i worker-traaden — så bygges prompten i fejl "
        "rum, og orienteringen siger «UDEN mode-signal»"
    )
    assert current_tool_scope() == "", (
        "scopet lækkede ud af kaldet; executor-traade genbruges, så næste "
        "kørsel ville arve det"
    )


def test_hjaelperen_uden_scope_bygger_uaendret(monkeypatch):
    """En kørsel uden scope (fx en wakeup) må ikke få et påklistret rum."""
    from core.tools.tool_scoping import current_tool_scope
    from core.services import visible_runs

    set_under_kaldet: list[str] = []
    monkeypatch.setattr(
        visible_runs,
        "_build_visible_input",
        lambda *a, **k: set_under_kaldet.append(current_tool_scope()),
    )

    visible_runs._build_visible_input_with_scope("", "hej")

    assert set_under_kaldet == [""]


def test_ingen_to_thread_bygger_prompten_uden_om_hjaelperen():
    """Alle `asyncio.to_thread`-kald der bygger prompten skal gå gennem hjælperen.

    Det er den vagt der fanger et tredje kaldested — fejlen opstod netop ved at
    der fandtes et sted ingen havde set.
    """
    trae = ast.parse(VISIBLE_RUNS.read_text(encoding="utf-8"))

    raa_kald: list[int] = []
    hjaelper_kald: list[int] = []
    for node in ast.walk(trae):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "to_thread"):
            continue
        if not node.args:
            continue
        foerste = node.args[0]
        navn = getattr(foerste, "id", None) or getattr(foerste, "attr", None)
        if navn == "_build_visible_input":
            raa_kald.append(node.lineno)
        elif navn == "_build_visible_input_with_scope":
            hjaelper_kald.append(node.lineno)

    assert not raa_kald, (
        f"prompten bygges i to_thread uden om hjælperen på linje {raa_kald} — "
        "så får den tomt scope og «UDEN mode-signal»"
    )
    assert len(hjaelper_kald) >= 2, (
        f"forventede begge genbygningssteder (approval-vejen og post-tool-"
        f"vejen), fandt {hjaelper_kald}"
    )


def test_cachenoeglen_skelner_rum(monkeypatch):
    """Samme besked i to rum er to forskellige prompts — ikke ét cache-hit."""
    from core.services import prompt_assembly_runtime as runtime
    from core.services import prompt_assembly_turn_cache as cache
    from core.tools.tool_scoping import reset_tool_scope, set_tool_scope

    cache.clear()
    builds: list[str] = []
    udfald: list[str] = []
    monkeypatch.setattr(
        "core.services.prompt_assembly_telemetri.rapporter_cache_lookup",
        lambda **kwargs: udfald.append(kwargs["outcome"]),
    )

    def builder(**kwargs):
        builds.append(kwargs["user_message"])
        return object()

    common = dict(
        builder=builder,
        latest_message_id=7,
        provider="deepseek",
        model="deepseek-flash",
        user_message="hej",
        session_id="s1",
        name="default",
        runtime_self_report_context=None,
    )

    token = set_tool_scope("chat")
    try:
        foerste = runtime.build_with_turn_cache(**common, caller_phase="initial")
        anden = runtime.build_with_turn_cache(**common, caller_phase="post_tool")
    finally:
        reset_tool_scope(token)

    assert foerste is anden, "samme rum skal stadig ramme cachen"
    assert builds == ["hej"]

    token = set_tool_scope("code")
    try:
        tredje = runtime.build_with_turn_cache(**common, caller_phase="initial")
    finally:
        reset_tool_scope(token)

    assert tredje is not foerste, (
        "et andet rum fik det første rums assembly — så bærer prompten den "
        "forkerte modes værktøjsoverblik og orientering"
    )
    assert builds == ["hej", "hej"]
    assert udfald == ["miss", "hit", "miss"]
