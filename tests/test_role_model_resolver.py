"""Unit tests for role_model_resolver — task-aware role/model picking."""
from __future__ import annotations

from unittest.mock import patch

from core.services.role_model_resolver import resolve_role_model


def _stub_config(role: str, **kwargs):
    return [{"role": role, **kwargs}]


def test_no_config_returns_empty():
    with patch(
        "core.services.agent_runtime._load_council_model_config",
        return_value=[],
    ):
        result = resolve_role_model(role="critic", goal="hej")
    assert result["provider"] == ""
    assert result["model"] == ""
    assert result["source"] == "no-config"


def test_legacy_flat_config_used_when_no_tiers():
    with patch(
        "core.services.agent_runtime._load_council_model_config",
        return_value=_stub_config("critic", provider="ollamafreeapi", model="mistral:latest"),
    ):
        result = resolve_role_model(role="critic", goal="hej")
    assert result["provider"] == "ollamafreeapi"
    assert result["model"] == "mistral:latest"
    assert result["source"] == "role-default"


def test_fast_tier_picks_light_model():
    cfg = _stub_config(
        "critic",
        provider="ollamafreeapi", model="mistral:latest",
        tiers={
            "fast": {"provider": "ollamafreeapi", "model": "llama3.2:3b"},
            "reasoning": {"provider": "ollamafreeapi", "model": "mistral:latest"},
            "deep": {"provider": "cloudflare", "model": "scout"},
        },
    )
    with patch(
        "core.services.agent_runtime._load_council_model_config",
        return_value=cfg,
    ), patch(
        "core.services.role_model_resolver._classify_goal_tier",
        return_value="fast",
    ):
        result = resolve_role_model(role="critic", goal="hej")
    assert result["provider"] == "ollamafreeapi"
    assert result["model"] == "llama3.2:3b"
    assert result["source"] == "tier-match"
    assert result["tier"] == "fast"


def test_deep_tier_picks_heavy_model():
    cfg = _stub_config(
        "critic",
        provider="ollamafreeapi", model="mistral:latest",
        tiers={
            "fast": {"provider": "ollamafreeapi", "model": "llama3.2:3b"},
            "deep": {"provider": "cloudflare", "model": "scout"},
        },
    )
    with patch(
        "core.services.agent_runtime._load_council_model_config",
        return_value=cfg,
    ), patch(
        "core.services.role_model_resolver._classify_goal_tier",
        return_value="deep",
    ):
        result = resolve_role_model(role="critic", goal="kør migration på prod")
    assert result["provider"] == "cloudflare"
    assert result["model"] == "scout"
    assert result["source"] == "tier-match"


def test_missing_tier_falls_back_to_role_default():
    cfg = _stub_config(
        "critic",
        provider="ollamafreeapi", model="mistral:latest",
        tiers={"deep": {"provider": "cloudflare", "model": "scout"}},
    )
    # tier=fast, but tiers only defines deep -> fall back to role default
    with patch(
        "core.services.agent_runtime._load_council_model_config",
        return_value=cfg,
    ), patch(
        "core.services.role_model_resolver._classify_goal_tier",
        return_value="fast",
    ):
        result = resolve_role_model(role="critic", goal="hej")
    assert result["provider"] == "ollamafreeapi"
    assert result["model"] == "mistral:latest"
    assert result["source"] == "role-default"


def test_unknown_role_returns_empty():
    cfg = _stub_config("critic", provider="x", model="y")
    with patch(
        "core.services.agent_runtime._load_council_model_config",
        return_value=cfg,
    ):
        result = resolve_role_model(role="researcher", goal="hej")
    assert result["source"] == "no-config"


def test_classify_goal_tier_handles_empty_goal():
    from core.services.role_model_resolver import _classify_goal_tier
    assert _classify_goal_tier("") == "fast"
    assert _classify_goal_tier("   ") == "fast"
