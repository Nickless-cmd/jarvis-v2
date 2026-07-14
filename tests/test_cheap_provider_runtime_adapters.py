"""Tests for core/services/cheap_provider_runtime_adapters.py — provider defaults."""
from __future__ import annotations

from core.services.cheap_provider_runtime_adapters import CHEAP_PROVIDER_DEFAULTS


def test_new_verified_providers_present_and_well_formed():
    """De 4 live-verificerede providers (14. jul) skal være i CHEAP_PROVIDER_DEFAULTS
    med de felter selection/adapters kræver. En provider der IKKE er her kan ikke
    bruges af cheap lane (provider_auth_ready returnerer False)."""
    required = {"label", "priority", "base_url", "auth_kind", "protocol", "static_models"}
    expected_models = {
        "cerebras": "gpt-oss-120b",
        "cline": "deepseek/deepseek-chat",
        "aihubmix": "gpt-5.5-free",
        "requesty": "novita/tencent/hy3",
    }
    for provider, must_have_model in expected_models.items():
        assert provider in CHEAP_PROVIDER_DEFAULTS, f"{provider} mangler i defaults"
        cfg = CHEAP_PROVIDER_DEFAULTS[provider]
        assert required <= set(cfg), f"{provider} mangler felter: {required - set(cfg)}"
        assert cfg["auth_kind"] == "bearer"
        assert cfg["protocol"] == "openai-chat"
        assert cfg["base_url"].startswith("https://")
        assert must_have_model in cfg["static_models"], f"{provider} mangler {must_have_model}"


def test_cline_base_url_is_api_v1_not_clinebot():
    """Regression: Cline's endpoint er api.cline.bot/api/v1 — IKKE api.clinebot.com,
    IKKE /v1. Forkert host gav HTTP 000 i 1. test."""
    base = CHEAP_PROVIDER_DEFAULTS["cline"]["base_url"]
    assert base == "https://api.cline.bot/api/v1"
    assert "clinebot.com" not in base


def test_aihubmix_static_models_are_free_only():
    """AIHubMix 'auto' router til BETALT (403 balance). Kun *-free må stå i pool."""
    models = CHEAP_PROVIDER_DEFAULTS["aihubmix"]["static_models"]
    assert models, "aihubmix skal have free-modeller"
    assert all("free" in m for m in models), f"ikke-gratis model i aihubmix pool: {models}"
    assert "auto" not in models


def test_deepseek_not_routable_but_free_providers_are():
    """Bjørn 14. jul: deepseek (betalt) skal UD af routbar cheap-pool; gratis ind."""
    from core.services.cheap_provider_runtime_adapters import is_routable_provider
    assert is_routable_provider("deepseek") is False
    assert is_routable_provider("openai-codex") is False   # død efter opsigelse
    for free in ("cerebras", "aihubmix", "requesty", "groq", "nvidia-nim"):
        assert is_routable_provider(free) is True, f"{free} skal være routbar"


def test_gemini_cloudflare_openai_compat_for_tools():
    """Research 14. jul: gemini + cloudflare bruger nu deres OpenAI-compat endpoints
    (protocol=openai-chat) → tool_calls virker → i den tool-kapable agent-pool.
    gemini-2.5 udfaset → -latest-aliaser."""
    from core.services.cheap_provider_runtime_adapters import CHEAP_PROVIDER_DEFAULTS
    g = CHEAP_PROVIDER_DEFAULTS["gemini"]
    assert g["protocol"] == "openai-chat"
    assert g["base_url"].endswith("/openai")
    assert "gemini-flash-latest" in g["static_models"]
    assert "gemini-2.5-flash-lite" not in g.get("static_models", [])
    cf = CHEAP_PROVIDER_DEFAULTS["cloudflare"]
    assert cf["protocol"] == "openai-chat"
    assert "/ai/v1" in cf["base_url"]


def test_opencode_free_models_current_not_deprecated():
    """opencode static_models skal være de AKTUELLE gratis Zen-modeller (verificeret
    via `opencode models` 14. jul), ikke de udfasede."""
    from core.services.cheap_provider_runtime_adapters import CHEAP_PROVIDER_DEFAULTS
    m = CHEAP_PROVIDER_DEFAULTS["opencode"]["static_models"]
    assert "nemotron-3-ultra-free" in m and "mimo-v2.5-free" in m
    assert "nemotron-3-super-free" not in m   # udfaset
    assert "minimax-m2.5-free" not in m       # udfaset
    assert len(m) >= 5


def test_github_models_and_ovhcloud_configured():
    """14. jul: GitHub Models (gratis GPT-5/o4-mini/DeepSeek-R1 via Copilot-token) +
    OVHcloud (anon, auth_kind=none) tilføjet til poolen."""
    from core.services.cheap_provider_runtime_adapters import (
        CHEAP_PROVIDER_DEFAULTS, is_routable_provider, provider_auth_ready)
    gh = CHEAP_PROVIDER_DEFAULTS["github-models"]
    assert gh["protocol"] == "openai-chat" and gh["base_url"].startswith("https://models.github.ai")
    assert "openai/gpt-5-mini" in gh["static_models"]
    assert gh["daily_limit"] == 50           # rate-limitet → ikke arbejdshest
    ov = CHEAP_PROVIDER_DEFAULTS["ovhcloud"]
    assert ov["auth_kind"] == "none"
    # auth_kind=none → altid ready uden nøgle
    assert provider_auth_ready(provider="ovhcloud", auth_profile="default") is True
    assert is_routable_provider("github-models") and is_routable_provider("ovhcloud")


def test_copilot_cost_classes():
    from core.services.cheap_provider_runtime_adapters import provider_cost_class, CHEAP_PROVIDER_DEFAULTS
    assert provider_cost_class("copilot-premium") == "paid"
    assert provider_cost_class("copilot-free") == "free"
    assert provider_cost_class("cerebras") == "free"   # default
    assert "claude-opus-4.8" in CHEAP_PROVIDER_DEFAULTS["copilot-premium"]["static_models"]
    assert "gpt-4o" in CHEAP_PROVIDER_DEFAULTS["copilot-free"]["static_models"]
