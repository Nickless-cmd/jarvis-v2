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
    for free in ("cerebras", "aihubmix", "requesty", "groq", "nvidia-nim"):
        assert is_routable_provider(free) is True, f"{free} skal være routbar"
