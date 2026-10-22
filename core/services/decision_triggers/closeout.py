"""Triggers: de øjeblikke hvor arbejde lukkes — og hvor disciplinen falder.

## Hvorfor de findes

Målt 22/10-2026: **80 aktive beslutninger, 0 bundet til en trigger.** To
triggere fandtes i forvejen (`loop_nudge_5_rounds`, `backend_unresolved_3_calls`),
så signal-mekanismen kørte hver runde, kaldte `_active_decisions_with_triggers()`
— og fik en tom liste. Adherence var 0,726, og de 12 laveste (0,10–0,33) havde
en fælles form: de handler alle om at LUKKE arbejde ordentligt.

Skriv memory-sektionen. Opdater README-portrættet. Sweep fejlformen.
Afslut turen rent. Ingen af dem er tidløse hensigter — de er handlinger der
skal ske LIGE EFTER noget andet er sket. Uden en trigger bliver de læst som
tekst i et præfiks 30.000 tegn væk fra det øjeblik de gælder.

## Skelnen der er værd at holde fast

En trigger kan minde mig om en regel **midt i turen**. Den kan ikke håndhæve
noget strukturelt — fx kan `closing_round_with_tools` minde mig om at den
afsluttende tekstblok er sidste handling, men den kan ikke forhindre at jeg
kalder et værktøj bagefter. Det kræver et værn i runtime, ikke en trigger.
Triggeren er påmindelsen; værn er en anden slags arbejde.
"""
from __future__ import annotations

import json
from typing import Any

from core.services.decision_signals import TriggerContext, register


def _call_name_and_args(tool_call: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Læs navn+argumenter fra både OpenAI- og Ollama-formen.

    Målt i `visible_followup_events.ToolExchange`: `tool_calls` er rå
    model-dicts, altså `{"function": {"name", "arguments"}}`. Argumenterne
    kan være en JSON-streng. `backend_unresolved` gør præcis det samme, og
    det er den form der er målt — ikke en antagelse.
    """
    fn = tool_call.get("function") or {}
    name = str(fn.get("name") or tool_call.get("name") or "")
    args = fn.get("arguments") or tool_call.get("arguments") or {}
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            args = {}
    if not isinstance(args, dict):
        args = {}
    return name, args


def commit_just_made(ctx: TriggerContext) -> bool:
    """Fyr når der lige er lavet en git-commit i denne tur.

    Det er lukke-øjeblikket: arbejdet er færdigt nok til at være committet,
    og det er præcis dér de tre lavt-scorende beslutninger gælder — skriv
    memory-sektionen, opdater portrættet hvis identiteten flyttede sig, og
    sweep fejlformen hvis det jeg lige rettede var en FORM og ikke én fejl.
    """
    for tc in reversed(list(ctx.recent_tool_calls or [])):
        name, args = _call_name_and_args(tc)
        if name not in {"bash", "operator_bash", "bash_session_run"}:
            continue
        cmd = str(args.get("command") or "")
        if "git commit" in cmd:
            return True
    return False


def closing_round_with_tools(ctx: TriggerContext) -> bool:
    """Fyr i sene runder hvor der stadig kaldes værktøjer.

    Beslutningen med prioritet 92 og adherence 0,13 er «den afsluttende
    tekstblok er ALTID sidste handling». Den overtrædes ikke i runde 1 —
    den overtrædes når jeg er dybt i arbejdet og lægger et sidste kald efter
    svaret. Derfor fyrer denne kun fra runde 2 og frem, og kun når runden
    faktisk indeholder værktøjskald.
    """
    if ctx.agentic_round_seq < 2:
        return False
    return bool(ctx.recent_tool_calls)


register("commit_just_made", commit_just_made, cooldown_turns=2)
register("closing_round_with_tools", closing_round_with_tools, cooldown_turns=2)
