"""Shared LLM call for daemons — cheap lane first, heartbeat model fallback."""
from __future__ import annotations


def daemon_llm_call(prompt: str, *, max_len: int = 200, fallback: str = "") -> str:
    """Call LLM for daemon output. Tries cheap lane (Groq) first, then heartbeat model.

    Returns stripped text or fallback on failure. Never raises.
    """
    text = ""

    # 1. Try cheap lane (Groq / fast provider)
    try:
        from apps.api.jarvis_api.services.non_visible_lane_execution import (
            execute_cheap_lane,
        )

        result = execute_cheap_lane(message=prompt)
        text = str(result.get("text") or "").strip()
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
        except Exception:
            pass

    # 3. Clean up quotes
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1].strip()

    return text[:max_len] if text else fallback
