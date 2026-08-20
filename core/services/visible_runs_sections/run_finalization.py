"""Hvad der skal ske NÅR et visible run er slut — samlet ét sted.

Boy Scout-udtrækning (2026-08-20): `visible_runs.py` er 7.055 linjer, og
run-afslutningens sideeffekter lå spredt. Denne enhed samler dem, så der
findes ÉT svar på "hvad køres ved run-slut" i stedet for et kald pr. gren.

## Bug'en der gjorde udtrækningen nødvendig

`_advance_tool_lifecycle` blev kaldt PRÆCIS ét sted (visible_runs.py:4574),
inde i den agentiske followup-gren. Men `_persist_session_assistant_message`
kaldes fra otte forskellige steder — den simple ikke-agentiske gren (~5226),
afbrudt-grenen (~5364) og fire fejlstier. Alle ture der afsluttede ad de veje
avancerede **aldrig** cold_floor.

Målt live 20. aug 2026 på Bjørns session: floor stod på 104207 fra kl. 18:05,
mens otte afsluttede runs (18:23-18:31) ikke flyttede den. Manuelt kald gav
straks 104207 → 104311, hvilket flyttede 61 tool-results fra warm til cold og
sparede 3.641 tokens i hver eneste prompt derefter.

Diagnosen kom fra Codex, som forudsagde både det nye floor-tal (104311) og
effekten (92 → 31 warm) korrekt før verifikation.

## Hvorfor finally-blokken

`_post_process`-tråden startes fra en `finally`, som ALLE runs når — completed,
failed, interrupted og cancelled. Det er den eneste sti med den garanti.
`evaluate_and_advance` er idempotent (floor'en beregnes fra beskederne, ikke
inkrementelt), så et ekstra kald fra den gamle gren er harmløst.
"""
from __future__ import annotations


def advance_tool_lifecycle(session_id: str) -> None:
    """Ryk tool-result cold_floor frem (spec 2026-07-16). Self-safe.

    Idempotent: `evaluate_and_advance` udleder floor'en fra sessionens beskeder
    med hysterese, så gentagne kald i samme tilstand er no-ops. Må ALDRIG kaste
    — en fejl her må ikke vælte run-afslutningen.
    """
    if not session_id:
        return
    try:
        from core.context.tool_result_lifecycle import evaluate_and_advance
        evaluate_and_advance(session_id)
    except Exception:
        pass


def finalize_run(session_id: str, *, status: str) -> None:
    """Kaldes fra run-afslutningens finally — uanset hvordan runnet endte.

    Kun `completed` avancerer lifecycle: et afbrudt run kan have efterladt
    halve tool-exchanges, og at fryse dem til cold-stubs ville tabe kontekst
    Jarvis stadig har brug for i den næste tur.
    """
    if status == "completed":
        advance_tool_lifecycle(session_id)
