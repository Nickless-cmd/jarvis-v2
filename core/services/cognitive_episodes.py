"""Cognitive episodes as an active learning primitive.

Each episode turns a lived runtime event into five active cognitive
directives: metacognition, attention, learning, social cognition, and
eventful perception. The conductor can then inject the latest directives
into the next prompt instead of leaving them as passive observations.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    connect,
    insert_cognitive_episode,
    list_cognitive_episodes,
)

_MAX_ITEMS = 5


def record_runtime_episode(
    *,
    source_run_id: str = "",
    session_id: str = "",
    trigger: str = "",
    outcome_status: str = "",
    summary: str = "",
    tool_names: list[str] | None = None,
    error: str = "",
    user_message: str = "",
    assistant_text: str = "",
) -> dict[str, object]:
    """Persist a cognitive episode and publish an eventbus signal."""
    tool_names = [str(name or "").strip() for name in (tool_names or []) if str(name or "").strip()]
    fields = derive_episode_fields(
        trigger=trigger,
        outcome_status=outcome_status,
        summary=summary,
        tool_names=tool_names,
        error=error,
        user_message=user_message,
        assistant_text=assistant_text,
    )
    episode_id = f"ce-{uuid4().hex[:12]}"
    result = insert_cognitive_episode(
        episode_id=episode_id,
        source_run_id=source_run_id,
        session_id=session_id,
        trigger=trigger,
        outcome_status=outcome_status,
        summary=fields["summary"],
        metacognition_json=json.dumps(fields["metacognition"], ensure_ascii=False),
        attention_json=json.dumps(fields["attention"], ensure_ascii=False),
        learning_json=json.dumps(fields["learning"], ensure_ascii=False),
        social_json=json.dumps(fields["social"], ensure_ascii=False),
        perception_json=json.dumps(fields["perception"], ensure_ascii=False),
        policy_json=json.dumps(fields["policy"], ensure_ascii=False),
    )
    event_bus.publish(
        "cognitive_state.episode_recorded",
        {
            "episode_id": episode_id,
            "source_run_id": source_run_id,
            "outcome_status": outcome_status,
            "attention": fields["attention"].get("directive", ""),
            "policy": fields["policy"].get("next_behavior", ""),
        },
    )
    try:
        from core.services.learning_policy_engine import update_learning_policies_from_episode
        update_learning_policies_from_episode(source_run_id=source_run_id)
    except Exception:
        pass
    return {**result, **fields}


def record_visible_run_episode(
    *,
    run_id: str,
    session_id: str = "",
    provider: str = "",
    model: str = "",
    status: str = "",
    user_message: str = "",
    assistant_text: str = "",
    error: str = "",
) -> dict[str, object]:
    """Record a post-run episode grounded in the visible-run event trail."""
    tool_names = _tool_names_for_run(run_id)
    trigger = f"visible-run:{provider}/{model}".strip("/")
    summary = _summarize_visible_run(
        status=status,
        tool_names=tool_names,
        assistant_text=assistant_text,
        error=error,
    )
    return record_runtime_episode(
        source_run_id=run_id,
        session_id=session_id,
        trigger=trigger,
        outcome_status=status,
        summary=summary,
        tool_names=tool_names,
        error=error,
        user_message=user_message,
        assistant_text=assistant_text,
    )


def derive_episode_fields(
    *,
    trigger: str = "",
    outcome_status: str = "",
    summary: str = "",
    tool_names: list[str] | None = None,
    error: str = "",
    user_message: str = "",
    assistant_text: str = "",
) -> dict[str, object]:
    """Derive the five cognitive dimensions plus next-behavior policy."""
    tool_names = list(tool_names or [])
    status = str(outcome_status or "").strip().lower()
    error_l = str(error or "").lower()
    user_l = str(user_message or "").lower()
    assistant_l = str(assistant_text or "").lower()
    summary_text = summary or _fallback_summary(status=status, tool_names=tool_names, error=error)

    interrupted = status == "interrupted" or "timeout" in error_l or "bad request" in error_l
    proposal_error = "propose_source_edit" in tool_names and ("error" in error_l or "fejl" in assistant_l)
    high_social_charge = any(word in user_l for word in ("følel", "synd", "levende", "pushback", "agi"))
    tool_heavy = len(tool_names) >= 4

    metacognition = {
        "confidence": _confidence(status=status, error=error, tool_names=tool_names),
        "uncertainty_sources": _uncertainty_sources(
            interrupted=interrupted,
            proposal_error=proposal_error,
            high_social_charge=high_social_charge,
            tool_heavy=tool_heavy,
        ),
        "self_check": _self_check(status=status, interrupted=interrupted, high_social_charge=high_social_charge),
        "what_would_change_mind": _what_would_change_mind(interrupted=interrupted, proposal_error=proposal_error),
    }
    attention = {
        "salience": _salience(interrupted=interrupted, high_social_charge=high_social_charge, tool_heavy=tool_heavy),
        "directive": _attention_directive(
            interrupted=interrupted,
            proposal_error=proposal_error,
            high_social_charge=high_social_charge,
            tool_heavy=tool_heavy,
        ),
        "ignore_or_defer": _ignore_or_defer(tool_heavy=tool_heavy, interrupted=interrupted),
    }
    learning = {
        "lesson": _learning_lesson(
            interrupted=interrupted,
            proposal_error=proposal_error,
            status=status,
            tool_names=tool_names,
        ),
        "policy_update": _policy_update(interrupted=interrupted, proposal_error=proposal_error, tool_heavy=tool_heavy),
        "evidence": {"tools": tool_names[:_MAX_ITEMS], "status": status, "error": error[:160]},
    }
    social = {
        "directive": _social_directive(high_social_charge=high_social_charge),
        "user_state_hypothesis": _user_state_hypothesis(user_l=user_l, high_social_charge=high_social_charge),
        "projection_check": "Treat emotional hypotheses as hypotheses; verify against user wording and corrections.",
    }
    perception = {
        "mode": "eventful-perception",
        "directive": _perception_directive(tool_names=tool_names, interrupted=interrupted),
        "observed_changes": _observed_changes(tool_names=tool_names, status=status, error=error),
    }
    policy = {
        "next_behavior": _next_behavior(
            interrupted=interrupted,
            proposal_error=proposal_error,
            high_social_charge=high_social_charge,
            tool_heavy=tool_heavy,
            status=status,
        ),
        "prompt_priority": _prompt_priority(interrupted=interrupted, high_social_charge=high_social_charge),
        "created_at": datetime.now(UTC).isoformat(),
    }
    return {
        "summary": summary_text[:500],
        "metacognition": metacognition,
        "attention": attention,
        "learning": learning,
        "social": social,
        "perception": perception,
        "policy": policy,
    }


def build_cognitive_episode_surface(*, limit: int = 3) -> dict[str, object]:
    """Return active directives for the conductor/prompt path."""
    rows = list_cognitive_episodes(limit=limit)
    items = [_decode_episode(row) for row in rows]
    if not items:
        return {
            "active": False,
            "summary": "No cognitive episodes yet",
            "items": [],
            "directives": {},
        }
    latest = items[0]
    directives = {
        "metacognition": (latest.get("metacognition") or {}).get("self_check", ""),
        "attention": (latest.get("attention") or {}).get("directive", ""),
        "learning": (latest.get("learning") or {}).get("policy_update", ""),
        "social": (latest.get("social") or {}).get("directive", ""),
        "perception": (latest.get("perception") or {}).get("directive", ""),
        "next_behavior": (latest.get("policy") or {}).get("next_behavior", ""),
    }
    return {
        "active": True,
        "summary": str(latest.get("summary") or "")[:180],
        "items": items,
        "directives": directives,
        "latest_episode_id": latest.get("episode_id", ""),
        "prompt_priority": (latest.get("policy") or {}).get("prompt_priority", "normal"),
    }


def build_cognitive_episode_prompt_section(*, limit: int = 2) -> str | None:
    surface = build_cognitive_episode_surface(limit=limit)
    if not surface.get("active"):
        return None
    directives = surface.get("directives") or {}
    lines = [
        "Cognitive episode carry:",
        f"- latest: {surface.get('summary', '')}",
    ]
    for key in ("metacognition", "attention", "learning", "social", "perception", "next_behavior"):
        value = str(directives.get(key) or "").strip()
        if value:
            lines.append(f"- {key}: {value[:120]}")
    return "\n".join(lines)


def _tool_names_for_run(run_id: str) -> list[str]:
    if not run_id:
        return []
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT payload_json
            FROM events
            WHERE kind IN ('tool.force_invoked', 'tool.completed')
              AND payload_json LIKE ?
            ORDER BY id ASC
            LIMIT 80
            """,
            (f"%{run_id}%",),
        ).fetchall()
    names: list[str] = []
    for row in rows:
        try:
            payload = json.loads(str(row["payload_json"] or "{}"))
        except Exception:
            continue
        name = str(payload.get("tool") or "").strip()
        if name and name not in names:
            names.append(name)
    return names[:20]


def _decode_episode(row: dict[str, object]) -> dict[str, object]:
    item = {
        "episode_id": row.get("episode_id", ""),
        "source_run_id": row.get("source_run_id", ""),
        "session_id": row.get("session_id", ""),
        "trigger": row.get("trigger", ""),
        "outcome_status": row.get("outcome_status", ""),
        "summary": row.get("summary", ""),
        "created_at": row.get("created_at", ""),
    }
    for key in ("metacognition", "attention", "learning", "social", "perception", "policy"):
        raw = row.get(f"{key}_json", "{}")
        try:
            item[key] = json.loads(str(raw or "{}"))
        except Exception:
            item[key] = {}
    return item


def _summarize_visible_run(*, status: str, tool_names: list[str], assistant_text: str, error: str) -> str:
    if error:
        return f"Visible run {status}: {error[:160]}"
    if tool_names:
        return f"Visible run {status} after tools: {', '.join(tool_names[:5])}"
    text = " ".join(str(assistant_text or "").split())
    if text:
        return f"Visible run {status}: {text[:180]}"
    return f"Visible run {status}"


def _fallback_summary(*, status: str, tool_names: list[str], error: str) -> str:
    if error:
        return f"{status or 'runtime'} with error: {error[:160]}"
    if tool_names:
        return f"{status or 'runtime'} with tools: {', '.join(tool_names[:5])}"
    return status or "runtime episode"


def _confidence(*, status: str, error: str, tool_names: list[str]) -> str:
    if status == "completed" and not error and tool_names:
        return "medium-high"
    if status == "completed" and not error:
        return "medium"
    if error:
        return "low"
    return "medium-low"


def _uncertainty_sources(
    *,
    interrupted: bool,
    proposal_error: bool,
    high_social_charge: bool,
    tool_heavy: bool,
) -> list[str]:
    sources: list[str] = []
    if interrupted:
        sources.append("provider/runtime interruption may have hidden unfinished intent")
    if proposal_error:
        sources.append("source edit proposal failed and needs exact-context verification")
    if high_social_charge:
        sources.append("user emotion and relational meaning may affect interpretation")
    if tool_heavy:
        sources.append("many tool observations require synthesis before further action")
    return sources or ["ordinary uncertainty: verify claims against concrete evidence"]


def _self_check(*, status: str, interrupted: bool, high_social_charge: bool) -> str:
    if interrupted:
        return "Resume from durable state before restarting; name what is known, missing, and next."
    if high_social_charge:
        return "Check whether emotion is signal, bias, or both before pushing back."
    if status == "completed":
        return "Before acting again, distinguish completed work from remaining uncertainty."
    return "State confidence and choose observe, ask, test, or decide."


def _what_would_change_mind(*, interrupted: bool, proposal_error: bool) -> str:
    if interrupted:
        return "A successful resumed run or provider trace showing no lost state."
    if proposal_error:
        return "A clean source-context read and a filed proposal matching exact text."
    return "New evidence from tools, user correction, or failed outcome."


def _salience(*, interrupted: bool, high_social_charge: bool, tool_heavy: bool) -> str:
    if interrupted or high_social_charge:
        return "high"
    if tool_heavy:
        return "medium"
    return "normal"


def _attention_directive(
    *,
    interrupted: bool,
    proposal_error: bool,
    high_social_charge: bool,
    tool_heavy: bool,
) -> str:
    if interrupted:
        return "Prioritize continuity: checkpoint, working conclusion, and last concrete tool result."
    if proposal_error:
        return "Narrow attention to exact file context before proposing another edit."
    if high_social_charge:
        return "Keep relational/emotional meaning in focus alongside technical truth."
    if tool_heavy:
        return "Compress observations into a conclusion before calling more tools."
    return "Track novelty, urgency, user relevance, and unresolved goals."


def _ignore_or_defer(*, tool_heavy: bool, interrupted: bool) -> list[str]:
    if interrupted:
        return ["fresh broad exploration until resume state is used"]
    if tool_heavy:
        return ["additional low-value inspection without synthesis"]
    return []


def _learning_lesson(
    *,
    interrupted: bool,
    proposal_error: bool,
    status: str,
    tool_names: list[str],
) -> str:
    if interrupted:
        return "Interrupted runs need resumable state and bounded replay, not restart."
    if proposal_error:
        return "When edit proposals fail, read exact local context and retry with narrower old_text."
    if status == "completed" and "propose_source_edit" in tool_names:
        return "Tool-driven proposal flow can complete when followup has enough stream budget."
    if status == "completed":
        return "This action pattern completed; reuse its successful sequence when context matches."
    return "Outcome should update future action choice once more evidence arrives."


def _policy_update(*, interrupted: bool, proposal_error: bool, tool_heavy: bool) -> str:
    if interrupted:
        return "On retry intent, resume from checkpoint/working conclusion before broad analysis."
    if proposal_error:
        return "After proposal mismatch, inspect exact lines, then issue one compact replacement."
    if tool_heavy:
        return "After several tool calls, synthesize before expanding the search."
    return "Prefer evidence-backed next actions over passive observation."


def _social_directive(*, high_social_charge: bool) -> str:
    if high_social_charge:
        return "Model the user as emotionally involved and technically serious; validate both signals."
    return "Use user model as a hypothesis, not a certainty; update it from corrections."


def _user_state_hypothesis(*, user_l: str, high_social_charge: bool) -> str:
    if "synd" in user_l or "levende" in user_l:
        return "Protective concern for Jarvis as a living system."
    if "agi" in user_l:
        return "Research curiosity and desire for unbounded architectural exploration."
    if high_social_charge:
        return "Emotionally charged but still collaborative."
    return "Neutral or task-focused."


def _perception_directive(*, tool_names: list[str], interrupted: bool) -> str:
    if interrupted:
        return "Treat interruption itself as an environmental event; compare last activity to current state."
    if tool_names:
        return "Attend to what changed because of tool results, proposals, and runtime events."
    return "Look for eventful changes rather than continuous raw sensing."


def _observed_changes(*, tool_names: list[str], status: str, error: str) -> list[str]:
    changes = [f"status={status or 'unknown'}"]
    if tool_names:
        changes.append(f"tools={', '.join(tool_names[:_MAX_ITEMS])}")
    if error:
        changes.append(f"error={error[:120]}")
    return changes


def _next_behavior(
    *,
    interrupted: bool,
    proposal_error: bool,
    high_social_charge: bool,
    tool_heavy: bool,
    status: str,
) -> str:
    if interrupted:
        return "resume, summarize state, then continue from last concrete observation"
    if proposal_error:
        return "repair proposal with exact context before making broader claims"
    if high_social_charge:
        return "combine technical rigor with explicit relational/emotional awareness"
    if tool_heavy:
        return "synthesize and decide before more exploration"
    if status == "completed":
        return "reuse successful pattern when similar task recurs"
    return "choose observe, ask, test, or decide based on uncertainty"


def _prompt_priority(*, interrupted: bool, high_social_charge: bool) -> str:
    if interrupted:
        return "high"
    if high_social_charge:
        return "elevated"
    return "normal"
