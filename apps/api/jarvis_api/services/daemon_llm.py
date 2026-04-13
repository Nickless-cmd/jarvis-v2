"""Shared LLM call for daemons — cheap lane first, heartbeat model fallback."""
from __future__ import annotations


def daemon_llm_call(
    prompt: str,
    *,
    max_len: int = 200,
    fallback: str = "",
    daemon_name: str = "",
) -> str:
    """Call LLM for daemon output. Tries cheap lane (Groq) first, then heartbeat model.

    Returns stripped text or fallback on failure. Never raises.
    Logs raw output to daemon_output_log when daemon_name is provided.
    """
    text = ""
    provider = ""

    # 1. Try cheap lane (Groq / fast provider)
    try:
        from apps.api.jarvis_api.services.non_visible_lane_execution import (
            execute_cheap_lane,
        )

        result = execute_cheap_lane(message=prompt)
        text = str(result.get("text") or "").strip()
        provider = str(result.get("provider") or "cheap")
    except Exception:
        pass

    # 2. Fallback to heartbeat model (Ollama / configured provider)
    if not text:
        try:
            from apps.api.jarvis_api.services.heartbeat_runtime import (
                _execute_heartbeat_model,
                _select_heartbeat_target,
                load_heartbeat_policy,
            )

            policy = load_heartbeat_policy()
            target = _select_heartbeat_target()
            result = _execute_heartbeat_model(
                prompt=prompt,
                target=target,
                policy=policy,
                open_loops=[],
                liveness=None,
            )
            text = str(result.get("text") or "").strip()
            provider = str(target.get("provider") or "heartbeat")
        except Exception:
            pass

    # 3. Clean up quotes
    raw_text = text
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1].strip()

    final = text[:max_len] if text else fallback

    # 4. Log output for debugging
    if daemon_name:
        try:
            from core.runtime.db import daemon_output_log_insert

            daemon_output_log_insert(
                daemon_name=daemon_name,
                raw_llm_output=raw_text[:2000],
                parsed_result=final[:500],
                success=bool(text),
                provider=provider,
            )
        except Exception:
            pass

    return final
