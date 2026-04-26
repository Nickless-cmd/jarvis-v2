"""Verification gate — advisory check on destructive/mutation actions.

R2 of the reasoning-layer rollout. Pure observational: reads the eventbus,
classifies recent tool.completed events, and reports two kinds of signals:

1. **Unverified mutations** — files written/edited or commands run, with no
   matching verify_* call afterward. Suggests a verify_* the model could
   make next.
2. **Failed verifications** — recent verify_* calls that returned status
   "failed". Hard evidence the model claimed something that wasn't true.

Does NOT block. Does NOT auto-call verify_* (that would surprise the user
and cost tokens). It surfaces awareness only — the model decides what to
do with it.

Reads eventbus on demand. No daemon, no persistence. Cheap to call.

Promotion path: if telemetry shows the model ignores the warnings while
mutations slip through, R2.5 can flip the gate to blocking for tier=deep
actions. That's a separate decision after we have data.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# Tools that *change state* (file/repo/system/config) and should ideally be
# paired with a verify_* call before the model claims success.
_MUTATION_TOOLS_FILE: frozenset[str] = frozenset({
    "write_file", "edit_file", "publish_file",
})
_MUTATION_TOOLS_SHELL: frozenset[str] = frozenset({
    "bash", "bash_session_run",
})
_MUTATION_TOOLS_SERVICE: frozenset[str] = frozenset({
    "control_daemon", "restart_overdue_daemons",
})
_MUTATION_TOOLS_CONFIG: frozenset[str] = frozenset({
    "update_setting", "approve_proposal", "approve_plan",
})

_MUTATION_TOOLS: frozenset[str] = (
    _MUTATION_TOOLS_FILE
    | _MUTATION_TOOLS_SHELL
    | _MUTATION_TOOLS_SERVICE
    | _MUTATION_TOOLS_CONFIG
)

_VERIFY_TOOLS: frozenset[str] = frozenset({
    "verify_file_contains", "verify_service_active", "verify_endpoint_responds",
})

_LOOKBACK_MINUTES = 10
_LOOKBACK_EVENTS = 200
_MAX_WARNINGS_SURFACED = 4


def _suggested_verify(tool: str) -> str | None:
    if tool in _MUTATION_TOOLS_FILE:
        return "verify_file_contains"
    if tool in _MUTATION_TOOLS_SERVICE:
        return "verify_service_active"
    return None  # bash / config: no automatic suggestion


def _recent_events(minutes: int = _LOOKBACK_MINUTES) -> list[dict[str, Any]]:
    try:
        from core.eventbus.bus import event_bus
        events = event_bus.recent(limit=_LOOKBACK_EVENTS)
    except Exception:
        return []
    cutoff = (datetime.now(UTC) - timedelta(minutes=minutes)).isoformat()
    out: list[dict[str, Any]] = []
    for e in events:
        if str(e.get("created_at", "")) >= cutoff:
            out.append(e)
    return out


def _scan(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Classify events into mutations + verifies and pair them."""
    mutations: list[dict[str, Any]] = []
    verifies: list[dict[str, Any]] = []
    failed_verifies: list[dict[str, Any]] = []

    for e in events:
        if str(e.get("kind", "")) != "tool.completed":
            continue
        payload = e.get("payload") or {}
        if not isinstance(payload, dict):
            continue
        tool = str(payload.get("tool", ""))
        status = str(payload.get("status", ""))
        ts = str(e.get("created_at", ""))
        if tool in _VERIFY_TOOLS:
            verifies.append({"tool": tool, "status": status, "ts": ts, "payload": payload})
            if status == "failed":
                failed_verifies.append({"tool": tool, "status": status, "ts": ts, "payload": payload})
        elif tool in _MUTATION_TOOLS and status == "ok":
            mutations.append({"tool": tool, "status": status, "ts": ts, "payload": payload})

    # Crude pairing: count mutations that have NO subsequent verify in the window.
    # We don't try to match by path/target — that's brittle and the goal is just
    # to surface "you mutated N things and verified M". The model can decide if
    # M < N is a problem.
    return {
        "mutations": mutations,
        "verifies": verifies,
        "failed_verifies": failed_verifies,
    }


def evaluate_verification_gate(*, minutes: int = _LOOKBACK_MINUTES) -> dict[str, Any]:
    """Return verification-gate signals for the recent window."""
    events = _recent_events(minutes=minutes)
    scan = _scan(events)
    mutations = scan["mutations"]
    verifies = scan["verifies"]
    failed = scan["failed_verifies"]

    by_tool: dict[str, int] = {}
    for m in mutations:
        by_tool[m["tool"]] = by_tool.get(m["tool"], 0) + 1

    unverified_count = max(0, len(mutations) - len(verifies))
    suggestions: list[str] = []
    for tool, count in sorted(by_tool.items(), key=lambda kv: -kv[1]):
        verify = _suggested_verify(tool)
        if verify and count > 0:
            suggestions.append(f"{count}× {tool} → overvej {verify}")

    return {
        "status": "ok",
        "window_minutes": minutes,
        "mutation_count": len(mutations),
        "verify_count": len(verifies),
        "failed_verify_count": len(failed),
        "unverified_count": unverified_count,
        "by_tool": by_tool,
        "suggestions": suggestions,
        "failed_verifies": [
            {
                "tool": f["tool"],
                "reason": str((f.get("payload") or {}).get("result", {}).get("reason"))
                if isinstance((f.get("payload") or {}).get("result"), dict)
                else "",
                "ts": f["ts"],
            }
            for f in failed[:_MAX_WARNINGS_SURFACED]
        ],
    }


def verification_gate_section() -> str | None:
    """Format gate signals as a prompt-awareness section, or None."""
    result = evaluate_verification_gate()
    failed = result.get("failed_verifies") or []
    unverified = int(result.get("unverified_count") or 0)
    suggestions = result.get("suggestions") or []

    if not failed and unverified <= 0:
        return None

    lines: list[str] = []
    if failed:
        lines.append(
            f"❌ {len(failed)} verify_* fejlede i sidste {result['window_minutes']} min "
            f"— hård evidens for at du har påstået noget der ikke holder:"
        )
        for f in failed:
            reason = f.get("reason") or "se eventbus for detaljer"
            lines.append(f"  - {f['tool']}: {reason}")
    if unverified > 0 and suggestions:
        lines.append(
            f"⚠ {result['mutation_count']} mutations / {result['verify_count']} verifies "
            f"i sidste {result['window_minutes']} min — overvej at verificere før du "
            f"rapporterer noget som gjort:"
        )
        for s in suggestions[:_MAX_WARNINGS_SURFACED]:
            lines.append(f"  - {s}")

    return "Verification gate:\n" + "\n".join(lines)


def _exec_verification_status(args: dict[str, Any]) -> dict[str, Any]:
    minutes = int(args.get("minutes") or _LOOKBACK_MINUTES)
    minutes = max(1, min(120, minutes))
    return evaluate_verification_gate(minutes=minutes)


VERIFICATION_GATE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "verification_status",
            "description": (
                "Read the verification gate: how many mutations vs verifies "
                "in the recent window, plus any failed verify_* calls. "
                "Returns suggestions for which verify_* to run next. "
                "Advisory only — does not block or auto-call anything."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "minutes": {
                        "type": "integer",
                        "description": "Lookback window (default 10, max 120).",
                    },
                },
                "required": [],
            },
        },
    },
]
