"""Unit tests for execute_with_role_or_fallback — per-role agent execution."""
from __future__ import annotations

from unittest.mock import patch

from core.services.non_visible_lane_execution import execute_with_role_or_fallback


def test_no_provider_falls_through_to_cheap_lane():
    """When provider/model not given, just delegates to cheap_lane chain."""
    fake_result = {"provider": "nvidia-nim", "model": "x", "text": "hi", "output_tokens": 1, "cost_usd": 0.0}
    with patch(
        "core.services.non_visible_lane_execution.execute_cheap_lane_via_pool",
        return_value=fake_result,
    ) as fake_pool:
        result = execute_with_role_or_fallback(message="ping", provider="", model="")
    assert result["provider"] == "nvidia-nim"
    fake_pool.assert_called_once()


def test_primary_success_short_circuits_fallback():
    """When primary call succeeds, cheap_lane chain is NOT invoked."""
    primary_result = {"text": "primary OK", "output_tokens": 2, "cost_usd": 0.0}
    with patch(
        "core.services.cheap_provider_runtime._execute_provider_chat",
        return_value=primary_result,
    ) as fake_chat, patch(
        "core.services.non_visible_lane_execution.execute_cheap_lane_via_pool",
    ) as fake_pool:
        result = execute_with_role_or_fallback(
            message="ping", provider="ollamafreeapi", model="gpt-oss:20b"
        )
    assert result["provider"] == "ollamafreeapi"
    assert result["model"] == "gpt-oss:20b"
    assert result["execution_mode"] == "role-primary-direct"
    fake_chat.assert_called_once()
    fake_pool.assert_not_called()


def test_primary_failure_falls_through_to_cheap_lane():
    """When primary raises, cheap_lane chain is invoked instead."""
    fallback_result = {"provider": "nvidia-nim", "model": "y", "text": "fallback OK"}
    with patch(
        "core.services.cheap_provider_runtime._execute_provider_chat",
        side_effect=RuntimeError("primary boom"),
    ), patch(
        "core.services.non_visible_lane_execution.execute_cheap_lane_via_pool",
        return_value=fallback_result,
    ) as fake_pool:
        result = execute_with_role_or_fallback(
            message="ping", provider="ollamafreeapi", model="gpt-oss:20b"
        )
    assert result["provider"] == "nvidia-nim"
    assert result["text"] == "fallback OK"
    fake_pool.assert_called_once()


def test_only_provider_no_model_falls_through():
    """Provider without model is incomplete — fall through."""
    with patch(
        "core.services.non_visible_lane_execution.execute_cheap_lane_via_pool",
        return_value={"provider": "x", "model": "y", "text": "ok"},
    ) as fake_pool:
        result = execute_with_role_or_fallback(message="ping", provider="ollamafreeapi", model="")
    assert result["provider"] == "x"
    fake_pool.assert_called_once()
