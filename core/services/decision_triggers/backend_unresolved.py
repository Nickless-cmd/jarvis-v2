"""Trigger: fire when 3 consecutive Jarvis-backend tool calls happen
without a resolution-text response.

Decision: dec_56d4dbb03e22 — "Når jeg finder et problem i min egen
backend, handler jeg inden 3 tool calls: fix, foreslå fix, eller forklar
tydeligt hvad der blokerer. Ingen ren rapportering."

Filter logic (BOTH must hold to count as backend-investigation):
1. Tool name matches an investigation pattern (read_file, grep, etc.)
2. Path argument (when present) points inside Jarvis's project tree

git_* calls are accepted by name alone — they're always in the current
repo by definition. Tools without a path argument (e.g., bash without
explicit cwd) also count as backend.

Cooldown: cooldown_turns=3 (2026-07-04). Var 0 ("incident-style nagging until
streak breaks or resolution"), men da signalet føjedes til den buffer exit-tjekket
selv læste, kunne nag'en aldrig se en resolution → self-poisoning runaway (hundredvis
af markører i ét svar, model-degeneration). Staging er nu efemer (se
decision_signal_staging.py); cooldown_turns=3 er bælte-og-seler oveni.
"""
from __future__ import annotations

import json
from typing import Any

from core.services.decision_signals import register, TriggerContext


_BACKEND_TOOL_PATTERNS = ("read_file", "grep", "list_dir", "glob", "git_")
_JARVIS_PATH_HINTS = (
    "/media/projects/jarvis-v2",
    "/home/bs/.jarvis-v2",
    "core/",
    "apps/",
)
_RESOLUTION_MIN_CHARS = 80
_RESOLUTION_KEYWORDS = (
    "fixed", "found", "root cause", "fundet", "fikset", "rod", "løst",
    "deployed", "deployet", "committed", "committet",
)


def _is_jarvis_backend_call(tool_call: dict[str, Any]) -> bool:
    fn = tool_call.get("function") or {}
    name = str(fn.get("name") or tool_call.get("name") or "")
    if not any(name.startswith(p) for p in _BACKEND_TOOL_PATTERNS):
        return False
    # git_* tools are always against the current repo
    if name.startswith("git_"):
        return True
    args = fn.get("arguments") or tool_call.get("arguments") or {}
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            args = {}
    if not isinstance(args, dict):
        args = {}
    path = str(args.get("path") or args.get("dir") or "")
    if not path:
        # No path arg → treat as backend (e.g., grep without dir)
        return True
    return any(hint in path for hint in _JARVIS_PATH_HINTS)


def backend_unresolved_3_calls(ctx: TriggerContext) -> bool:
    backend_streak = 0
    for tc in (ctx.recent_tool_calls or [])[-5:]:
        if _is_jarvis_backend_call(tc):
            backend_streak += 1
        else:
            backend_streak = 0
    if backend_streak < 3:
        return False
    last_text = (ctx.recent_assistant_text or "").strip().lower()
    if len(last_text) >= _RESOLUTION_MIN_CHARS and any(
        kw in last_text for kw in _RESOLUTION_KEYWORDS
    ):
        return False
    return True


register("backend_unresolved_3_calls", backend_unresolved_3_calls, cooldown_turns=3)
