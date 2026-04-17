"""End-of-run memory consolidation driven by the local model.

Runs after each visible run and asks the local model for bounded memory
candidates instead of free-form file writes. The runtime then persists
those candidates through the governed candidate workflow.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha1
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.identity.candidate_workflow import (
    auto_apply_safe_memory_md_candidates,
    auto_apply_safe_user_md_candidates,
)
from core.identity.workspace_bootstrap import workspace_memory_paths
from core.runtime.db import upsert_runtime_contract_candidate

_EXCERPT_MEMORY_CHARS = 2400
_EXCERPT_USER_CHARS = 1800
_FULL_MEMORY_CHARS = 12000
_FULL_USER_CHARS = 8000
_MAX_ITEMS = 3
_NONE_MARKERS = {"", "none", "null", "n/a"}


def consolidate_run_memory(
    *,
    session_id: str = "",
    run_id: str = "",
    user_message: str = "",
    assistant_response: str = "",
    internal_context: str = "",
) -> dict[str, object]:
    result: dict[str, object] = {
        "consolidated": False,
        "memory_updated": False,
        "user_updated": False,
        "candidate_count": 0,
        "auto_applied_user_count": 0,
        "auto_applied_memory_count": 0,
        "used_full_context": False,
        "daily_memory_logged": False,
        "skipped_reason": None,
    }

    def _finish() -> dict[str, object]:
        _publish_consolidation_event(
            result,
            session_id=session_id,
            run_id=run_id,
        )
        return result

    if len(user_message) < 12 and len(assistant_response) < 40:
        result["skipped_reason"] = "conversation-too-short"
        return _finish()

    memory_paths = workspace_memory_paths()
    memory_path = memory_paths["curated_memory"]
    user_path = memory_paths["user"]
    current_memory = memory_path.read_text(encoding="utf-8", errors="replace") if memory_path.exists() else ""
    current_user = user_path.read_text(encoding="utf-8", errors="replace") if user_path.exists() else ""

    decision = _run_memory_consolidation_pass(
        user_message=user_message[:1800],
        assistant_response=assistant_response[:2600],
        internal_context=internal_context[:1800],
        current_memory=current_memory,
        current_user=current_user,
        full_context=False,
    )
    if decision is None:
        result["skipped_reason"] = "model-unavailable"
        return _finish()
    if bool(decision.get("needs_full_context")):
        decision = _run_memory_consolidation_pass(
            user_message=user_message[:1800],
            assistant_response=assistant_response[:2600],
            internal_context=internal_context[:1800],
            current_memory=current_memory,
            current_user=current_user,
            full_context=True,
        )
        result["used_full_context"] = True
    if decision is None:
        result["skipped_reason"] = "unparseable-response"
        return _finish()

    items = _normalize_memory_items(decision.get("items"))
    if not items:
        result["consolidated"] = True
        result["skipped_reason"] = "no-new-memory-items"
        return _finish()

    persisted = _persist_memory_candidates(
        items=items,
        session_id=session_id,
        run_id=run_id,
    )
    logged_daily = _append_daily_memory_log(
        daily_memory_path=memory_paths["daily_memory"],
        session_id=session_id,
        run_id=run_id,
        user_message=user_message,
        assistant_response=assistant_response,
        items=items,
    )
    user_apply = auto_apply_safe_user_md_candidates()
    memory_apply = auto_apply_safe_memory_md_candidates()

    result["consolidated"] = True
    result["candidate_count"] = len(persisted)
    result["auto_applied_user_count"] = int(user_apply.get("auto_applied") or 0)
    result["auto_applied_memory_count"] = int(memory_apply.get("auto_applied") or 0)
    result["user_updated"] = result["auto_applied_user_count"] > 0
    result["memory_updated"] = result["auto_applied_memory_count"] > 0
    result["daily_memory_logged"] = logged_daily

    return _finish()


def _publish_consolidation_event(
    result: dict[str, object],
    *,
    session_id: str,
    run_id: str,
) -> None:
    event_bus.publish(
        "memory.end_of_run_consolidation",
        {
            "session_id": session_id,
            "run_id": run_id,
            "consolidated": bool(result.get("consolidated")),
            "candidate_count": int(result.get("candidate_count") or 0),
            "memory_updated": bool(result.get("memory_updated")),
            "user_updated": bool(result.get("user_updated")),
            "daily_memory_logged": bool(result.get("daily_memory_logged")),
            "used_full_context": bool(result.get("used_full_context")),
            "skipped_reason": result.get("skipped_reason"),
            "auto_applied_user_count": int(result.get("auto_applied_user_count") or 0),
            "auto_applied_memory_count": int(result.get("auto_applied_memory_count") or 0),
        },
    )


def _run_memory_consolidation_pass(
    *,
    user_message: str,
    assistant_response: str,
    internal_context: str,
    current_memory: str,
    current_user: str,
    full_context: bool,
) -> dict[str, object] | None:
    memory_slice = current_memory[: (_FULL_MEMORY_CHARS if full_context else _EXCERPT_MEMORY_CHARS)]
    user_slice = current_user[: (_FULL_USER_CHARS if full_context else _EXCERPT_USER_CHARS)]
    prompt = _build_consolidation_prompt(
        user_message=user_message,
        assistant_response=assistant_response,
        internal_context=internal_context,
        current_memory=memory_slice,
        current_user=user_slice,
        full_context=full_context,
    )
    raw = _run_local_consolidation_model(prompt)
    if not raw:
        return None
    return _parse_decision(raw)


def _run_local_consolidation_model(prompt: str) -> str:
    """Run consolidation prompt. Primary: heartbeat target. Fallback: direct Ollama.

    Returns empty string if all lanes fail. Failures are published on the
    eventbus so the reason is visible instead of silent.
    """
    primary_error: str = ""
    try:
        from apps.api.jarvis_api.services.heartbeat_runtime import (
            _execute_heartbeat_model,
            _load_heartbeat_policy,
            _resolve_heartbeat_target,
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
        text = str((model_result or {}).get("text") or "").strip()
        if text:
            return text
        primary_error = "heartbeat-model-empty-response"
    except Exception as exc:  # noqa: BLE001
        primary_error = f"heartbeat-model-error: {type(exc).__name__}: {exc}"[:200]

    # Fallback: direct Ollama call, try each non-embedding model in turn.
    fallback_text, fallback_error = _run_ollama_consolidation_fallback(prompt)
    event_bus.publish(
        "memory.consolidation_model_fallback",
        {
            "primary_error": primary_error,
            "fallback_used": bool(fallback_text),
            "fallback_error": fallback_error,
        },
    )
    return fallback_text


def _run_ollama_consolidation_fallback(prompt: str) -> tuple[str, str]:
    """Direct Ollama generate call, trying available chat-capable models in order.

    Returns (text, error_summary). Empty text means all fallbacks failed.
    """
    try:
        import urllib.error
        import urllib.request
    except Exception as exc:  # noqa: BLE001
        return "", f"stdlib-import-error: {type(exc).__name__}: {exc}"[:200]

    base_url = "http://127.0.0.1:11434"
    # Discover installed models; skip embeddings.
    try:
        with urllib.request.urlopen(f"{base_url}/api/tags", timeout=3) as resp:
            tags = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return "", f"ollama-tags-error: {type(exc).__name__}: {exc}"[:200]

    candidates = [
        str(m.get("name") or "")
        for m in (tags.get("models") or [])
        if m.get("name") and "embed" not in str(m.get("name") or "").lower()
    ]
    if not candidates:
        return "", "no-ollama-chat-models-installed"

    errors: list[str] = []
    for model_name in candidates:
        try:
            req = urllib.request.Request(
                f"{base_url}/api/generate",
                data=json.dumps(
                    {
                        "model": model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.2},
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            text = str((data or {}).get("response") or "").strip()
            if text:
                return text, ""
            errors.append(f"{model_name}: empty")
        except urllib.error.HTTPError as exc:
            errors.append(f"{model_name}: HTTP {exc.code}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{model_name}: {type(exc).__name__}")

    return "", ("all-ollama-fallbacks-failed: " + "; ".join(errors))[:220]


def _build_consolidation_prompt(
    *,
    user_message: str,
    assistant_response: str,
    internal_context: str,
    current_memory: str,
    current_user: str,
    full_context: bool,
) -> str:
    context_label = "FULL FILE CONTEXT" if full_context else "BOUNDED FILE EXCERPTS"
    internal_block = (
        f"\nINTERNAL JARVIS-ONLY TOOL/RUNTIME CONTEXT:\n{internal_context}\n"
        if str(internal_context or "").strip()
        else ""
    )
    return f"""You are a bounded memory consolidation agent for Jarvis.

Your job is to decide whether this turn contains durable information that
should be carried into USER.md or MEMORY.md as short append-only lines.

{context_label}
CURRENT MEMORY.md:
{current_memory}

CURRENT USER.md:
{current_user}

TURN:
User: {user_message}
Assistant: {assistant_response}
{internal_block}

RULES:
- Prefer generic judgment over hardcoded patterns.
- Persist only durable facts, preferences, working context, or stable decisions.
- Tool/runtime context is Jarvis-only context: use it as evidence for durable
  work state or outcomes, but do not quote raw tool dumps into memory.
- Do not store transient observations, inner voice, filler, praise, or paraphrases of temporary tasks.
- USER.md is for durable user preferences or collaboration preferences.
- MEMORY.md is for durable project facts, repo/workspace context, shared anchors, and stable decisions.
- If you are unsure whether the existing file context is sufficient, return needs_full_context=true and no items.
- If the relevant fact may already exist and you cannot tell from the provided context, return needs_full_context=true and no items.
- Each item must be one short line suitable for append-only storage.
- At most {_MAX_ITEMS} items.

Return ONLY JSON in this shape:
{{
  "needs_full_context": false,
  "items": [
    {{
      "target": "USER.md" or "MEMORY.md",
      "kind": "preference|fact|context|decision",
      "confidence": "low|medium|high",
      "source": "explicit-user-statement|explicit-assistant-confirmation|runtime-inference",
      "summary": "short summary",
      "reason": "why this is durable",
      "line": "- concise line for the file"
    }}
  ]
}}
If nothing new is worth keeping, return {{"needs_full_context": false, "items": []}}."""


def _parse_decision(raw: str) -> dict[str, object] | None:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(raw[start:end])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def _normalize_memory_items(raw_items: object) -> list[dict[str, str]]:
    if not isinstance(raw_items, list):
        return []
    items: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for raw in raw_items[:_MAX_ITEMS]:
        if not isinstance(raw, dict):
            continue
        target = str(raw.get("target") or "").strip()
        if target not in {"USER.md", "MEMORY.md"}:
            continue
        line = _normalize_line(raw.get("line") or "")
        if not line:
            continue
        key = (target, line.lower())
        if key in seen:
            continue
        seen.add(key)
        items.append(
            {
                "target": target,
                "kind": str(raw.get("kind") or "fact").strip().lower() or "fact",
                "confidence": _normalize_confidence(raw.get("confidence") or ""),
                "source": str(raw.get("source") or "runtime-inference").strip().lower() or "runtime-inference",
                "summary": _normalize_sentence(raw.get("summary") or ""),
                "reason": _normalize_sentence(raw.get("reason") or ""),
                "line": line,
            }
        )
    return items


def _persist_memory_candidates(
    *,
    items: list[dict[str, str]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for item in items:
        target = item["target"]
        candidate_type = "preference_update" if target == "USER.md" else "memory_promotion"
        canonical_key = _candidate_canonical_key(item)
        confidence = item["confidence"]
        source = item["source"]
        evidence_class = _evidence_class_for_source(source)
        candidate = upsert_runtime_contract_candidate(
            candidate_id=f"candidate-{uuid4().hex}",
            candidate_type=candidate_type,
            target_file=target,
            status="proposed",
            source_kind="user-explicit" if source == "explicit-user-statement" else "runtime-derived-support",
            source_mode="end_of_run_memory_consolidation",
            actor="runtime:end-of-run-memory-consolidation",
            session_id=str(session_id or ""),
            run_id=str(run_id or ""),
            canonical_key=canonical_key,
            summary=item["summary"] or _summary_from_line(item["line"]),
            reason=item["reason"] or "Bounded local-model consolidation judged this worth carrying forward.",
            evidence_summary=_summary_from_line(item["line"]),
            support_summary=f"target={target} | kind={item['kind']} | source={source}",
            confidence=confidence,
            evidence_class=evidence_class,
            support_count=1,
            session_count=1,
            created_at=now,
            updated_at=now,
            status_reason="Candidate proposed by bounded end-of-run local memory consolidation.",
            proposed_value=item["line"],
            write_section="## Durable Preferences" if target == "USER.md" else "## Curated Memory",
        )
        persisted.append(candidate)
    return persisted


def _candidate_canonical_key(item: dict[str, str]) -> str:
    target = item["target"]
    kind = item["kind"]
    digest = sha1(f"{target}|{item['line'].lower()}".encode("utf-8")).hexdigest()[:12]
    if target == "USER.md":
        return f"user-preference:llm:{kind}-{digest}"
    if kind in {"fact", "context", "decision"}:
        return f"workspace-memory:remembered-fact:llm-{kind}-{digest}"
    return f"workspace-memory:stable-context:llm-{kind}-{digest}"


def _append_daily_memory_log(
    *,
    daily_memory_path,
    session_id: str,
    run_id: str,
    user_message: str,
    assistant_response: str,
    items: list[dict[str, str]],
) -> bool:
    if not items:
        return False
    daily_memory_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC).isoformat()
    lines: list[str] = [
        f"## {now}",
        f"- session_id: {str(session_id or '').strip() or 'none'}",
        f"- run_id: {str(run_id or '').strip() or 'none'}",
        f"- user: {_daily_excerpt(user_message, limit=220)}",
        f"- assistant: {_daily_excerpt(assistant_response, limit=220)}",
        "- carried:",
    ]
    for item in items:
        lines.append(
            f"  - [{item['target']}] {item['line'][2:] if item['line'].startswith('- ') else item['line']}"
        )
    lines.append("")
    with daily_memory_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")
    return True


def _evidence_class_for_source(source: str) -> str:
    if source == "explicit-user-statement":
        return "explicit_user_statement"
    if source == "explicit-assistant-confirmation":
        return "single_session_pattern"
    return "runtime_support_only"


def _normalize_line(value: object) -> str:
    normalized = " ".join(str(value or "").split()).strip()
    if normalized.lower() in _NONE_MARKERS:
        return ""
    if not normalized.startswith("- "):
        normalized = f"- {normalized}"
    return normalized[:220]


def _normalize_sentence(value: object) -> str:
    normalized = " ".join(str(value or "").split()).strip()
    if normalized.lower() in _NONE_MARKERS:
        return ""
    return normalized[:220]


def _normalize_confidence(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"high", "medium", "low"}:
        return normalized
    return "medium"


def _summary_from_line(line: str) -> str:
    normalized = " ".join(str(line or "").split()).strip()
    if normalized.startswith("- "):
        normalized = normalized[2:]
    return normalized[:180]


def _daily_excerpt(value: str, *, limit: int) -> str:
    normalized = " ".join(str(value or "").split()).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"
