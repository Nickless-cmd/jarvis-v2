"""Coding lane tools — Niveau 1 skeleton dispatcher.

Giver Jarvis mulighed for at requeste et kode-skeleton eller en plan
fra Codex *før* han begynder på en opgave han selv vurderer som svær.

Design (Claude + Jarvis + Bjørn, 2026-05-17):
- Niveau 1: explicit "ask Codex first" — Jarvis kalder selv
- Niveau 2: Lag 1 credit assignment samler data over tid (følger senere)
"""

from __future__ import annotations

from typing import Any

CODING_LANE_TOOL_HANDLERS: dict[str, Any] = {}


def _exec_request_codex_skeleton(args: dict[str, Any]) -> dict[str, Any]:
    """Byg et skeleton/plan for en opgave via coding lane (Codex).

    Kaldes når Jarvis selv vurderer at en opgave er svær eller ukendt:
    multi-file refactor, første brug af et library, komplekst test-setup,
    SQLAlchemy relationships, decorator chains, osv.
    """
    task_description = str(args.get("task_description") or "").strip()
    if not task_description:
        return {
            "status": "error",
            "error": "task_description is required",
        }

    context_files = args.get("context_files") or []
    extra_context = str(args.get("extra_context") or "").strip()

    # Build skeleton prompt for Codex
    lines: list[str] = [
        "Du er en kode-arkitekt og skal levere et struktureret skeleton/plan.",
        "",
        "OPGAVE:",
        task_description,
    ]

    if context_files:
        lines.append(f"\nRELEVANTE FILER:\n" + "\n".join(f"  - {f}" for f in context_files))

    if extra_context:
        lines.append(f"\nEKSTRA KONTEKST:\n{extra_context}")

    lines.append("""
BEDSTE SVARFORMAT (returner ren tekst):

## Architecture / Design
<overordnet tilgang, hvilke filer, hvordan de samarbejder>

## Skeleton
<for hver fil: funktionssignaturer, klasser, imports — kode man kan copy-paste>

## Edge cases / pitfalls
<hvad skal Jarvis passe på>

## Implementation order
<hvilken rækkefølge filerne bør skrives i>

Hold skeleton kort — max 200 linjer i alt. Returnér kun planen, ingen dialog.
""")

    prompt = "\n".join(lines)

    # Publish event for observability
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("coding_lane.skeleton_requested", {
            "task_preview": task_description[:200],
            "context_files": context_files,
        })
    except Exception:
        pass

    # Dispatch to coding lane (same provider as auto-reviewer).
    # Fallback to cheap lane if coding lane isn't executable (e.g. expired OAuth).
    coding_lane_ok = False
    result: dict[str, Any] = {}

    try:
        from core.services.non_visible_lane_execution import execute_coding_lane
        result = execute_coding_lane(message=prompt)
        text = str(result.get("text") or result.get("output") or result.get("response") or "")
        if text:
            coding_lane_ok = True
    except Exception:
        pass

    if not coding_lane_ok:
        # Fallback: use cheap lane (NVIDIA, Groq, Gemini, etc.)
        try:
            from core.services.non_visible_lane_execution import (
                execute_with_role_or_fallback,
            )
            fallback_prompt = prompt.replace(
                "Du er en kode-arkitekt",
                "Du er Claude Code, en ekspert kode-arkitekt",
            )
            result = execute_with_role_or_fallback(message=fallback_prompt)
            text = str(result.get("text") or result.get("output") or result.get("response") or "")
            if not text:
                return {
                    "status": "error",
                    "error": "coding lane + fallback both returned empty skeleton",
                }
            result["lane"] = "coding-fallback"
        except Exception as exc:
            return {
                "status": "error",
                "error": (
                    f"coding lane + fallback both failed: "
                    f"{type(exc).__name__}: {exc}"
                ),
            }

    return {
        "status": "ok",
        "skeleton": text[:4000],  # cap at 4000 chars
        "provider": str(result.get("provider") or result.get("lane") or "unknown"),
        "model": str(result.get("model") or ""),
    }


# ── Tool definitions ──────────────────────────────────────────────────

CODING_LANE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "request_codex_skeleton",
            "description": (
                "Request a code skeleton or implementation plan from Codex "
                "via the coding lane BEFORE starting a complex task. Use this "
                "when you (Jarvis) know an opgave is going to be hard — "
                "multi-file refactors, first-time library use, complex test "
                "fixtures, SQLAlchemy relationships, decorator chains, or "
                "anything where getting the structure right first matters. "
                "Codex returns a skeleton with signatures, classes, and "
                "implementation order."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task_description": {
                        "type": "string",
                        "description": "Clear description of what you need a skeleton/plan for.",
                    },
                    "context_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of file paths relevant to the task.",
                    },
                    "extra_context": {
                        "type": "string",
                        "description": "Optional extra context — existing code patterns, constraints, requirements.",
                    },
                },
                "required": ["task_description"],
            },
        },
    },
]

CODING_LANE_TOOL_HANDLERS = {
    "request_codex_skeleton": _exec_request_codex_skeleton,
}
