"""pause_and_ask — structured clarification prompts mid-run.

Today when Jarvis is uncertain, he either guesses or breaks character to
ask in prose. Both are noisy. This tool surfaces a structured question
with optional pre-canned options that JarvisX can render as buttons.

Tool behavior is intentionally simple:
  1. The tool result carries `kind: "pause_and_ask"` — a marker the UI
     watches for.
  2. The runtime emits a `tool.pause_and_ask` event so subscribers can
     react (e.g. mute autonomy daemons during the pause).
  3. Jarvis is expected to END HIS TURN after this tool call. The
     question + options live in the tool result, the UI renders option
     buttons, and Bjørn's pick comes back as the next user message.

The "pause" is by convention, not enforcement — Jarvis can still keep
running tools afterwards. But the question pattern is what enables the
button UX, so he should naturally stop and wait.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _exec_pause_and_ask(args: dict[str, Any]) -> dict[str, Any]:
    question = str(args.get("question") or "").strip()
    if not question:
        return {"status": "error", "error": "question is required"}

    raw_options = args.get("options")
    options: list[str] = []
    if isinstance(raw_options, list):
        for o in raw_options:
            s = str(o).strip()
            if s and len(s) <= 120:
                options.append(s)
            if len(options) >= 6:  # cap on number of buttons
                break

    context_note = str(args.get("context") or "").strip()[:400]
    urgency = str(args.get("urgency") or "normal").strip().lower()
    if urgency not in {"low", "normal", "high"}:
        urgency = "normal"

    # Emit eventbus signal so other subsystems (autonomy, daemons,
    # notification-bridge) can mute themselves while we wait for input.
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "tool.pause_and_ask",
            {"question": question[:200], "options": options, "urgency": urgency},
        )
    except Exception as exc:
        logger.debug("pause_and_ask: eventbus emit failed: %s", exc)

    return {
        "status": "asked",
        "kind": "pause_and_ask",
        "question": question,
        "options": options,
        "context": context_note,
        "urgency": urgency,
        "instructions_to_jarvis": (
            "End your turn after this tool call. Bjørn's response will arrive "
            "as the next user message — either as a free-form reply or as one "
            "of the option strings if he clicked a button. Don't keep working "
            "until you have his answer."
        ),
    }


PAUSE_AND_ASK_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "pause_and_ask",
            "description": (
                "Pause your run and ask Bjørn a structured clarification question "
                "BEFORE continuing. Use when you're genuinely uncertain about a "
                "decision that would be costly to undo: ambiguous file path, "
                "two reasonable architectural directions, edits that touch many "
                "files. JarvisX renders the options as buttons — Bjørn clicks one "
                "and the answer arrives as the next user message.\n\n"
                "DON'T use for: trivial confirmations (just decide), questions you "
                "can answer yourself by reading code (read first), or as a stall "
                "tactic when you don't want to commit. Reserve it for real forks.\n\n"
                "End your turn after calling this — don't keep doing other work."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to put to Bjørn (one sentence)",
                    },
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Optional pre-canned answers (max 6, each ≤120 chars). "
                            "If omitted, Bjørn just types a free-form reply."
                        ),
                    },
                    "context": {
                        "type": "string",
                        "description": "Brief context for why you're asking (≤400 chars)",
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["low", "normal", "high"],
                        "description": "How urgent — affects UI prominence",
                    },
                },
                "required": ["question"],
            },
        },
    },
]


PAUSE_AND_ASK_TOOL_HANDLERS: dict[str, Any] = {
    "pause_and_ask": _exec_pause_and_ask,
}
