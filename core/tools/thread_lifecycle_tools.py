"""Værktøjs-indgange til trådenes livscyklus.

thought_thread: tværsession-tråde (``cross_session_threads``). Trådene oprettes
    af runtime pr. session; det der manglede var at Jarvis selv kunne sætte en
    tråd på pause, tage den op igen eller lukke den.
open_loop_thread: åbne spørgsmål med bevidst navn (``open_loop_signal_tracking``).
    declare/touch/close er det "bevidste valg-punkt" servicen beskriver; intet
    kaldte det.

Værktøjerne delegerer til produktionens funktioner. ``open_loop_thread`` tager
run-id fra kørslens egen identitet (ContextVar), aldrig fra et argument: en
lukning er kun bevis hvis den kommer fra en ANDEN kørsel end den der åbnede
tråden, og det kan modellen ikke selv få lov at påstå.
"""
from __future__ import annotations

from typing import Any

from core.services import cross_session_threads, open_loop_signal_tracking
from core.services.run_autonomy_context import current_run_id

_THREAD_ACTIONS = ("list", "pause", "resume", "close")
_LOOP_ACTIONS = ("list", "declare", "touch", "close")


def _err(message: str) -> dict[str, Any]:
    return {"status": "error", "error": message}


def _exec_thought_thread(args: dict[str, Any]) -> dict[str, Any]:
    action = str(args.get("action") or "").strip().lower()
    if action not in _THREAD_ACTIONS:
        return _err(f"action must be one of {_THREAD_ACTIONS}")

    if action == "list":
        status = str(args.get("status") or "").strip().lower() or None
        threads = cross_session_threads.list_threads(status=status)
        return {"status": "ok", "count": len(threads), "threads": threads}

    thread_id = str(args.get("thread_id") or "").strip()
    if not thread_id:
        return _err(f"thread_id is required for {action}")

    if action == "pause":
        done = cross_session_threads.pause_thread(
            thread_id, note=str(args.get("note") or "")
        )
        needs = "active"
    elif action == "resume":
        synopsis = args.get("new_synopsis")
        done = cross_session_threads.resume_thread(
            thread_id, new_synopsis=None if synopsis is None else str(synopsis)
        )
        needs = "paused or active"
    else:
        done = cross_session_threads.close_thread(
            thread_id, reason=str(args.get("reason") or "")
        )
        needs = "active or paused"

    existing = cross_session_threads.get_thread(thread_id)
    if not done:
        if existing is None:
            return _err(f"thread_id {thread_id!r} not found")
        return _err(
            f"thread {thread_id!r} is {existing.get('status')}; {action} needs "
            f"a thread that is {needs}"
        )
    return {"status": "ok", "thread": existing}


def _exec_open_loop_thread(args: dict[str, Any]) -> dict[str, Any]:
    action = str(args.get("action") or "").strip().lower()
    if action not in _LOOP_ACTIONS:
        return _err(f"action must be one of {_LOOP_ACTIONS}")

    if action == "list":
        from core.runtime.db_runtime_executive_signals import list_runtime_threads

        status = str(args.get("status") or "").strip().lower() or None
        threads = list_runtime_threads(status=status)
        return {"status": "ok", "count": len(threads), "threads": threads}

    run_id = current_run_id()
    if not run_id:
        return _err(
            f"{action} needs the identity of the current run, and none is set; "
            "a thread cannot be tied to a run that is unknown"
        )

    try:
        if action == "declare":
            result = open_loop_signal_tracking.declare_open_loop_thread(
                name=str(args.get("name") or ""),
                declared_by="jarvis",
                run_id=run_id,
                summary=str(args.get("summary") or ""),
            )
        elif action == "touch":
            result = open_loop_signal_tracking.touch_open_loop_thread(
                str(args.get("thread_id") or "").strip(),
                run_id=run_id,
                summary=str(args.get("summary") or ""),
            )
        else:
            result = open_loop_signal_tracking.close_open_loop_thread(
                str(args.get("thread_id") or "").strip(),
                evidence=str(args.get("evidence") or ""),
                answered_in_run_id=run_id,
            )
    except ValueError as exc:  # servicens afvisning (tomt navn, ukendt/lukket tråd, manglende bevis) er svaret
        return _err(str(exc))
    # Aldrig ``**result``: touch returnerer loop-rækken, som selv har et
    # ``status``-felt, og det ville overskrive værktøjets eget "ok".
    if action == "declare":
        return {"status": "ok", "thread": result["thread"], "loop": result["loop"]}
    return {"status": "ok", "loop" if action == "touch" else "thread": result}


THREAD_LIFECYCLE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "thought_thread",
            "description": (
                "Dine tværsession-tråde — det du går og tænker på på tværs af "
                "samtaler. action=list viser trådene med deres id; pause "
                "lægger en aktiv tråd fra dig fordi du ikke kan følge den nu; "
                "resume tager den op igen; close afslutter den."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": list(_THREAD_ACTIONS)},
                    "thread_id": {"type": "string", "description": "Kræves for pause/resume/close (fra list)."},
                    "note": {"type": "string", "description": "pause: hvorfor den lægges væk."},
                    "new_synopsis": {"type": "string", "description": "resume: opdateret resumé."},
                    "reason": {"type": "string", "description": "close: hvorfor den lukkes."},
                    "status": {"type": "string", "description": "Filter for list: active|paused|closed."},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_loop_thread",
            "description": (
                "Åbne spørgsmål du bevidst giver et navn. declare åbner en "
                "tråd med det navn du sætter; touch markerer at denne kørsel "
                "rører den igen; close lukker den, men KUN med bevis for at "
                "spørgsmålet blev besvaret, og kun fra en anden kørsel end den "
                "der åbnede den. list viser trådene med id."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": list(_LOOP_ACTIONS)},
                    "name": {"type": "string", "description": "Kræves for declare."},
                    "thread_id": {"type": "string", "description": "Kræves for touch/close (fra list/declare)."},
                    "summary": {"type": "string", "description": "declare/touch: hvad spørgsmålet er lige nu."},
                    "evidence": {"type": "string", "description": "Kræves for close: pegepind på svaret."},
                    "status": {"type": "string", "description": "Filter for list: open|closed."},
                },
                "required": ["action"],
            },
        },
    },
]

THREAD_LIFECYCLE_TOOL_HANDLERS: dict[str, Any] = {
    "thought_thread": _exec_thought_thread,
    "open_loop_thread": _exec_open_loop_thread,
}
