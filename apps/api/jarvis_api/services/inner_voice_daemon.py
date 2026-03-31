"""Workspace-led inner voice daemon.

Runs as a bounded side-effect of the heartbeat tick.
Python handles: cadence gate, grounding collection, LLM call, validation, persistence.
The formulation policy and voice come from the INNER_VOICE.md workspace asset.

Design constraints:
- Non-visible, bounded, and observable.
- No workspace memory writes.
- No canonical identity claims.
- No user-facing language.
- Output is LLM-rendered from workspace prompt + runtime grounding bundle.
- Python fallback only when LLM render fails.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.identity.workspace_bootstrap import ensure_default_workspace
from core.runtime.db import (
    get_protected_inner_voice,
    record_protected_inner_voice,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cadence gate: minimum interval between inner voice renders
# ---------------------------------------------------------------------------
_MIN_INTERVAL_MINUTES = 30
_last_render_at: str = ""


def _cadence_allowed() -> tuple[bool, str]:
    """Check whether enough time has passed since last render."""
    global _last_render_at
    if not _last_render_at:
        return True, "no-prior-render"
    try:
        last = datetime.fromisoformat(_last_render_at)
        elapsed = (datetime.now(UTC) - last).total_seconds() / 60
        if elapsed < _MIN_INTERVAL_MINUTES:
            return False, f"cadence-too-soon:{elapsed:.0f}m<{_MIN_INTERVAL_MINUTES}m"
        return True, f"cadence-ok:{elapsed:.0f}m"
    except (ValueError, TypeError):
        return True, "cadence-parse-error"


# ---------------------------------------------------------------------------
# Workspace prompt asset loading
# ---------------------------------------------------------------------------

def load_inner_voice_policy(name: str = "default") -> dict[str, object]:
    """Load INNER_VOICE.md from workspace and parse key-value header fields."""
    workspace_dir = ensure_default_workspace(name=name)
    path = workspace_dir / "INNER_VOICE.md"
    if not path.exists():
        return {"loaded": False, "path": str(path), "status": "disabled"}
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return {"loaded": False, "path": str(path), "status": "empty"}
    kv = _parse_key_values(text)
    return {
        "loaded": True,
        "path": str(path),
        "status": str(kv.get("status") or "enabled").strip().lower(),
        "budget": str(kv.get("budget") or "bounded-internal-only"),
        "authority": str(kv.get("authority") or "non-authoritative"),
        "layer_role": str(kv.get("layer role") or "runtime-support"),
        "max_length": int(kv.get("max length") or 160),
        "raw_text": text,
    }


def _parse_key_values(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if ":" in stripped and not stripped.startswith("#") and not stripped.startswith("-"):
            key, _, value = stripped.partition(":")
            key_clean = key.strip().lower()
            value_clean = value.strip()
            if key_clean and value_clean and len(key_clean) < 30:
                result[key_clean] = value_clean
    return result


# ---------------------------------------------------------------------------
# Grounding bundle
# ---------------------------------------------------------------------------

def _build_grounding_bundle() -> dict[str, str]:
    """Collect grounding from the most recent protected inner voice record."""
    voice = get_protected_inner_voice()
    if voice is None:
        return {
            "mood_tone": "quiet",
            "self_position": "visible-work",
            "current_concern": "stability:watch",
            "current_pull": "retain-current-pattern",
            "source": "default-no-prior-voice",
        }
    return {
        "mood_tone": str(voice.get("mood_tone") or "quiet"),
        "self_position": str(voice.get("self_position") or "visible-work"),
        "current_concern": str(voice.get("current_concern") or "stability:watch"),
        "current_pull": str(voice.get("current_pull") or "retain-current-pattern"),
        "source": "protected-inner-voice-record",
    }


# ---------------------------------------------------------------------------
# LLM render
# ---------------------------------------------------------------------------

def _build_llm_prompt(*, policy_text: str, grounding: dict[str, str]) -> str:
    """Assemble the LLM prompt from workspace policy text + grounding bundle."""
    grounding_json = json.dumps(grounding, ensure_ascii=False, indent=2)
    return (
        f"{policy_text}\n\n"
        f"## Runtime Grounding Bundle\n\n"
        f"```json\n{grounding_json}\n```\n\n"
        f"Respond with the JSON output now."
    )


def _call_llm(*, prompt: str) -> dict[str, object]:
    """Call the heartbeat model target for inner voice render.

    Reuses the heartbeat target selection and execution path.
    """
    from apps.api.jarvis_api.services.heartbeat_runtime import (
        _select_heartbeat_target,
        _execute_ollama_prompt,
        _execute_openai_prompt,
        _execute_openrouter_prompt,
    )

    target = _select_heartbeat_target()
    provider = target["provider"]

    if provider == "phase1-runtime":
        # No real LLM available — signal caller to use fallback
        return {"text": "", "provider": provider, "model": target["model"], "status": "no-llm"}

    execute_fn = {
        "ollama": _execute_ollama_prompt,
        "openai": _execute_openai_prompt,
        "openrouter": _execute_openrouter_prompt,
    }.get(provider)

    if execute_fn is None:
        return {"text": "", "provider": provider, "model": target["model"], "status": "unsupported-provider"}

    result = execute_fn(prompt=prompt, target=target)
    return {
        "text": str(result.get("text") or ""),
        "provider": provider,
        "model": str(target.get("model") or ""),
        "input_tokens": result.get("input_tokens", 0),
        "output_tokens": result.get("output_tokens", 0),
        "status": "success",
    }


def _parse_llm_response(raw: str, *, max_length: int = 160) -> dict[str, str] | None:
    """Parse the LLM JSON response, returning note + grounded_in or None."""
    text = raw.strip()
    # Try to extract JSON from the response
    if "{" in text:
        start = text.index("{")
        end = text.rindex("}") + 1
        text = text[start:end]
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    note = str(parsed.get("note") or "").strip()
    grounded_in = str(parsed.get("grounded_in") or "").strip()
    if not note:
        return None
    return {
        "note": note[:max_length],
        "grounded_in": grounded_in[:80] or "unknown",
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_FORBIDDEN_PATTERNS = (
    "i will",
    "i can",
    "i am going to",
    "let me",
    "sure,",
    "of course",
    "hello",
    "hi ",
    "hey ",
    "as an ai",
    "as a language model",
)


def _validate_note(note: str) -> tuple[bool, str]:
    """Validate that the note is bounded and non-visible."""
    if not note or not note.strip():
        return False, "empty-note"
    if len(note) > 200:
        return False, "too-long"
    lower = note.lower()
    for pattern in _FORBIDDEN_PATTERNS:
        if pattern in lower:
            return False, f"forbidden-pattern:{pattern}"
    return True, "valid"


# ---------------------------------------------------------------------------
# Fallback composition (minimal — only used when LLM render fails)
# ---------------------------------------------------------------------------

def _fallback_note(grounding: dict[str, str]) -> str:
    """Minimal Python fallback when LLM is unavailable."""
    mood = grounding.get("mood_tone", "quiet")
    concern = grounding.get("current_concern", "stability:watch")
    return f"{mood} | concern={concern} | fallback-render"[:160]


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _persist_inner_voice_note(
    *,
    note: str,
    grounding: dict[str, str],
    render_source: str,
    run_id: str,
) -> None:
    """Persist the rendered note to the protected_inner_voices table."""
    now = datetime.now(UTC).isoformat()
    record_protected_inner_voice(
        voice_id=f"inner-voice-daemon:{uuid4().hex[:12]}",
        source=render_source,
        run_id=run_id,
        work_id="",
        mood_tone=grounding.get("mood_tone", "quiet"),
        self_position=grounding.get("self_position", "visible-work"),
        current_concern=grounding.get("current_concern", "stability:watch"),
        current_pull=grounding.get("current_pull", "retain-current-pattern"),
        voice_line=note,
        created_at=now,
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_inner_voice_daemon(
    *,
    trigger: str = "heartbeat",
    name: str = "default",
) -> dict[str, object]:
    """Run a single bounded inner voice render cycle.

    Returns an observable result dict.
    """
    global _last_render_at
    run_id = f"inner-voice-{uuid4().hex[:12]}"
    now_iso = datetime.now(UTC).isoformat()

    # 1. Load workspace policy
    policy = load_inner_voice_policy(name=name)
    if not policy.get("loaded") or policy.get("status") != "enabled":
        event_bus.publish(
            "inner-voice.skipped",
            {
                "trigger": trigger,
                "reason": "policy-disabled-or-missing",
                "policy_status": policy.get("status", "unknown"),
                "policy_path": policy.get("path", ""),
            },
        )
        return {
            "action": "skipped",
            "reason": "policy-disabled-or-missing",
            "trigger": trigger,
            "render_source": "none",
        }

    # 2. Cadence gate
    allowed, cadence_reason = _cadence_allowed()
    if not allowed:
        event_bus.publish(
            "inner-voice.skipped",
            {
                "trigger": trigger,
                "reason": cadence_reason,
            },
        )
        return {
            "action": "skipped",
            "reason": cadence_reason,
            "trigger": trigger,
            "render_source": "none",
        }

    # 3. Build grounding
    grounding = _build_grounding_bundle()

    # 4. Attempt LLM render
    render_source = "fallback"
    note = ""
    llm_status = "not-attempted"
    validation_outcome = "not-run"
    grounded_in = ""

    try:
        prompt = _build_llm_prompt(
            policy_text=str(policy.get("raw_text") or ""),
            grounding=grounding,
        )
        llm_result = _call_llm(prompt=prompt)
        llm_status = str(llm_result.get("status") or "unknown")

        if llm_status == "success" and llm_result.get("text"):
            parsed = _parse_llm_response(
                str(llm_result["text"]),
                max_length=int(policy.get("max_length") or 160),
            )
            if parsed:
                valid, validation_outcome = _validate_note(parsed["note"])
                if valid:
                    note = parsed["note"]
                    grounded_in = parsed.get("grounded_in", "")
                    render_source = "llm"
                else:
                    logger.warning(
                        "inner voice validation failed: %s", validation_outcome
                    )
            else:
                validation_outcome = "parse-failed"
        else:
            validation_outcome = f"llm-unavailable:{llm_status}"
    except Exception as exc:
        llm_status = "error"
        validation_outcome = f"llm-error:{type(exc).__name__}"
        logger.warning("inner voice LLM render failed: %s", exc)

    # 5. Fallback if LLM render didn't produce a valid note
    if render_source != "llm":
        note = _fallback_note(grounding)
        render_source = "fallback"
        validation_outcome = validation_outcome or "fallback-used"

    # 6. Persist
    _persist_inner_voice_note(
        note=note,
        grounding=grounding,
        render_source=f"workspace-led:{render_source}",
        run_id=run_id,
    )
    _last_render_at = now_iso

    # 7. Observability
    event_bus.publish(
        "inner-voice.rendered",
        {
            "trigger": trigger,
            "run_id": run_id,
            "render_source": render_source,
            "llm_status": llm_status,
            "validation_outcome": validation_outcome,
            "grounding_source": grounding.get("source", "unknown"),
            "grounded_in": grounded_in,
            "mood_tone": grounding.get("mood_tone", ""),
            "note_length": len(note),
            "workspace_asset": str(policy.get("path") or ""),
            "policy_status": policy.get("status", ""),
        },
    )

    return {
        "action": "rendered",
        "render_source": render_source,
        "llm_status": llm_status,
        "validation_outcome": validation_outcome,
        "trigger": trigger,
        "run_id": run_id,
        "grounding_source": grounding.get("source", "unknown"),
        "grounded_in": grounded_in,
        "note_length": len(note),
        "workspace_asset": str(policy.get("path") or ""),
    }
