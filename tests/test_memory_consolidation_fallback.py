from __future__ import annotations

from unittest.mock import patch


def _import():
    return __import__(
        "core.services.end_of_run_memory_consolidation",
        fromlist=["_run_local_consolidation_model"],
    )


def test_primary_heartbeat_target_returns_text_directly(isolated_runtime) -> None:
    mc = _import()

    with patch.object(mc, "event_bus"):  # don't publish anything
        with patch(
            "core.services.heartbeat_runtime._execute_heartbeat_model",
            return_value={"text": "primary-response"},
        ):
            with patch(
                "core.services.heartbeat_runtime._load_heartbeat_policy",
                return_value={},
            ):
                with patch(
                    "core.services.heartbeat_runtime._resolve_heartbeat_target",
                    return_value={"lane": "local", "provider": "ollama"},
                ):
                    result = mc._run_local_consolidation_model("prompt")

    assert result == "primary-response"


def test_falls_back_to_ollama_when_primary_empty(isolated_runtime) -> None:
    mc = _import()

    with patch.object(mc, "event_bus") as bus:
        with patch(
            "core.services.heartbeat_runtime._execute_heartbeat_model",
            return_value={"text": ""},
        ):
            with patch(
                "core.services.heartbeat_runtime._load_heartbeat_policy",
                return_value={},
            ):
                with patch(
                    "core.services.heartbeat_runtime._resolve_heartbeat_target",
                    return_value={"lane": "local", "provider": "ollama"},
                ):
                    with patch.object(
                        mc,
                        "_run_ollama_consolidation_fallback",
                        return_value=("fallback-response", ""),
                    ):
                        result = mc._run_local_consolidation_model("prompt")

    assert result == "fallback-response"
    # fallback event must have been published
    bus.publish.assert_called_once()
    call_args = bus.publish.call_args
    assert call_args[0][0] == "memory.consolidation_model_fallback"
    assert call_args[0][1]["fallback_used"] is True


def test_returns_empty_when_both_lanes_fail(isolated_runtime) -> None:
    mc = _import()

    with patch.object(mc, "event_bus") as bus:
        with patch(
            "core.services.heartbeat_runtime._execute_heartbeat_model",
            side_effect=RuntimeError("primary boom"),
        ):
            with patch(
                "core.services.heartbeat_runtime._load_heartbeat_policy",
                return_value={},
            ):
                with patch(
                    "core.services.heartbeat_runtime._resolve_heartbeat_target",
                    return_value={"lane": "local", "provider": "ollama"},
                ):
                    with patch.object(
                        mc,
                        "_run_ollama_consolidation_fallback",
                        return_value=("", "no-ollama-chat-models-installed"),
                    ):
                        result = mc._run_local_consolidation_model("prompt")

    assert result == ""
    bus.publish.assert_called_once()
    payload = bus.publish.call_args[0][1]
    assert payload["fallback_used"] is False
    assert "primary boom" in payload["primary_error"]
    assert payload["fallback_error"] == "no-ollama-chat-models-installed"
