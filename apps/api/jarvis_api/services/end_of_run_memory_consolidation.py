"""End-of-run memory consolidation — uses local model to persist
important learnings to workspace MEMORY.md and USER.md.

Runs after session distillation at the end of each visible run.
Uses the heartbeat (cheap/local) model to keep costs zero.

Design constraints:
- Read-then-write: always reads current file before writing
- Append-only semantics: new entries are added, existing preserved
- No spam: only writes when there's genuinely new information
- Bounded output: local model produces a small JSON decision
- No canonical identity mutation
"""
from __future__ import annotations

import json

from core.eventbus.bus import event_bus
from core.identity.workspace_bootstrap import ensure_default_workspace


def consolidate_run_memory(
    *,
    session_id: str = "",
    run_id: str = "",
    user_message: str = "",
    assistant_response: str = "",
) -> dict[str, object]:
    """Consolidate memory at end of visible run using local model.

    Reads MEMORY.md and USER.md, asks local model if anything from the
    conversation should be persisted, and writes updates if needed.
    """
    result: dict[str, object] = {
        "consolidated": False,
        "memory_updated": False,
        "user_updated": False,
        "skipped_reason": None,
    }

    # Skip if conversation is too short to contain useful information
    if len(user_message) < 20 and len(assistant_response) < 50:
        result["skipped_reason"] = "conversation-too-short"
        return result

    workspace_dir = ensure_default_workspace()
    memory_path = workspace_dir / "MEMORY.md"
    user_path = workspace_dir / "USER.md"

    current_memory = ""
    if memory_path.exists():
        current_memory = memory_path.read_text(encoding="utf-8", errors="replace")

    current_user = ""
    if user_path.exists():
        current_user = user_path.read_text(encoding="utf-8", errors="replace")

    # Truncate conversation to avoid blowing up local model context
    user_msg_truncated = user_message[:1500]
    assistant_truncated = assistant_response[:2000]

    prompt = _build_consolidation_prompt(
        user_message=user_msg_truncated,
        assistant_response=assistant_truncated,
        current_memory=current_memory[:2000],
        current_user=current_user[:1500],
    )

    # Use heartbeat model (local/cheap)
    try:
        from apps.api.jarvis_api.services.heartbeat_runtime import (
            _resolve_heartbeat_target,
            _execute_heartbeat_model,
            _load_heartbeat_policy,
        )

        policy = _load_heartbeat_policy()
        target = _resolve_heartbeat_target(policy=policy)

        model_result = _execute_heartbeat_model(
            prompt=prompt,
            target=target,
            policy=policy,
            open_loops=[],
            liveness=None,
        )
    except Exception:
        result["skipped_reason"] = "model-unavailable"
        return result

    raw = str(model_result.get("text") or "").strip()
    if not raw:
        result["skipped_reason"] = "empty-model-response"
        return result

    # Parse JSON decision
    decision = _parse_decision(raw)
    if decision is None:
        result["skipped_reason"] = "unparseable-response"
        return result

    result["consolidated"] = True

    # Apply memory update if model suggests one
    memory_addition = str(decision.get("memory_addition") or "").strip()
    if memory_addition and memory_addition.lower() not in {"none", "null", "n/a", ""}:
        _append_to_file(memory_path, current_memory, memory_addition)
        result["memory_updated"] = True

    # Apply user update if model suggests one
    user_addition = str(decision.get("user_addition") or "").strip()
    if user_addition and user_addition.lower() not in {"none", "null", "n/a", ""}:
        _append_to_file(user_path, current_user, user_addition)
        result["user_updated"] = True

    event_bus.publish(
        "memory.end_of_run_consolidation",
        {
            "session_id": session_id,
            "run_id": run_id,
            "memory_updated": result["memory_updated"],
            "user_updated": result["user_updated"],
        },
    )

    return result


def _build_consolidation_prompt(
    *,
    user_message: str,
    assistant_response: str,
    current_memory: str,
    current_user: str,
) -> str:
    return f"""You are a memory consolidation agent. Your job is to decide if anything
from this conversation exchange should be persisted to long-term memory.

CURRENT MEMORY.md (project facts, decisions, learned context):
{current_memory}

CURRENT USER.md (user preferences, working style):
{current_user}

CONVERSATION EXCHANGE:
User: {user_message}
Assistant: {assistant_response}

RULES:
- Only persist genuinely NEW information not already in the files
- memory_addition: concrete facts, decisions, project context, completed work
- user_addition: user preferences, communication style, expertise areas
- If nothing new worth remembering, set both to "none"
- Keep additions to 1-2 concise lines each
- Do not repeat existing content
- Do not write inner voice noise or reflective observations

Respond with ONLY a JSON object:
{{"memory_addition": "line to add to MEMORY.md or none", "user_addition": "line to add to USER.md or none"}}"""


def _parse_decision(raw: str) -> dict[str, str] | None:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start:end])
            except json.JSONDecodeError:
                return None
    return None


def _append_to_file(path, current_content: str, addition: str) -> None:
    """Append a line to a workspace file, placing it in the right section."""
    lines = current_content.rstrip().split("\n")

    # Find the last non-empty content line to append after
    insert_idx = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip():
            insert_idx = i + 1
            break

    # Add the new line with a bullet prefix if not already formatted
    new_line = addition if addition.startswith("- ") else f"- {addition}"
    lines.insert(insert_idx, new_line)

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
