"""Acceptance tests for the cheap-lane pool resilience round.

These are verification-level tests that lock in the SPEC scenarios for the
multi-profile cheap-lane pool, egress routing, autonomous fallback and the
protected-core invariants. Every boundary is stubbed — NO real network, NO
proxies, NO sleeps. They read the real module signatures and assert the
end-to-end invariants the plan promised.

Cross-reference of the unit-level seams these ride on:
  - tests/test_egress_routing.py            (resolve_egress map)
  - tests/test_non_visible_fallback.py      (fallback chain)
  - tests/test_cheap_provider_runtime_selection.py (multiprofile candidates)
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Shared registry stub (mirrors test_cheap_provider_runtime_selection._stub_groq_registry)
# ---------------------------------------------------------------------------
def _stub_groq_registry(monkeypatch, sel):
    """Make groq a valid cheap candidate via the provider-router registry."""
    registry = {
        "providers": [
            {"provider": "groq", "enabled": True, "auth_profile": "default",
             "auth_mode": "api_key", "base_url": "https://groq.example"},
        ],
        "models": [
            {"provider": "groq", "model": "llama-3-8b", "lane": "cheap",
             "enabled": True, "updated_at": "2026-07-16"},
        ],
    }
    monkeypatch.setattr(sel, "load_provider_router_registry", lambda: registry)
    monkeypatch.setattr(sel, "provider_auth_ready", lambda **kw: True)
    monkeypatch.setattr(sel, "provider_runtime_defaults",
                        lambda p: {"base_url": "https://groq.example", "priority": 22})


# ---------------------------------------------------------------------------
# Scenario 5 (protected core): the visible/paid deepseek path is untouched by
# every flag this round introduced. It is never proxied and can never use the
# non-visible free fallback.
# ---------------------------------------------------------------------------
def test_visible_lane_untouched_by_all_flags():
    from core.services.egress_routing import resolve_egress
    from core.services import non_visible_fallback as f

    # Visible deepseek always egresses over the home IP — never a gateway.
    assert resolve_egress("deepseek", "default") == "home"

    # A visible (non-autonomous) run can NEVER enter the free fallback helper:
    # the hard leak-guard assert fires before any provider is touched.
    with pytest.raises(AssertionError):
        f.run_non_visible_with_fallback(
            message="x",
            primary_call=lambda: {"text": "should-not-run"},
            run_is_autonomous=False,
        )


# ---------------------------------------------------------------------------
# Scenario 6: when the free pool serves the autonomous run, no paid cost is
# attributed and the result is not paid-deepseek.
# ---------------------------------------------------------------------------
def test_free_fallback_costs_zero(monkeypatch):
    from core.services import non_visible_fallback as f

    monkeypatch.setattr(f, "_fallback_enabled", lambda: True)
    monkeypatch.setattr(
        f, "execute_cheap_lane_via_pool",
        lambda **k: {"text": "ok", "lane": "cheap", "provider": "groq", "cost_usd": 0.0},
    )

    def boom():
        raise RuntimeError("quota")

    r = f.run_non_visible_with_fallback(
        message="hej", primary_call=boom, run_is_autonomous=True,
    )
    assert r["lane"] == "cheap"
    assert r["provider"] != "deepseek"     # never the paid API
    assert float(r["cost_usd"]) == 0.0     # free provider → zero paid cost


# ---------------------------------------------------------------------------
# WS4: the agent pool shares the SAME multi-profile pool. With the flag ON,
# _configured_cheap_candidates yields account2 candidates — and since the agent
# path routes through this same function, it inherits them (no separate pool).
# ---------------------------------------------------------------------------
def test_agent_pool_shares_multiprofile_pool(monkeypatch):
    from core.services import cheap_provider_runtime_selection as sel

    monkeypatch.setattr(
        "core.services.auth_profile_scan.ready_profiles_for",
        lambda provider: ["default", "account2"] if provider == "groq" else ["default"],
    )
    monkeypatch.setattr(sel, "_flag_multiprofile", lambda: True)
    _stub_groq_registry(monkeypatch, sel)

    candidates = sel._configured_cheap_candidates(include_public_proxy=True)
    profs = {c["auth_profile"] for c in candidates if c["provider"] == "groq"}
    # account2 appears in the SHARED candidate list that both the cheap lane and
    # the agent lane (via execute_cheap_lane_via_pool) consume.
    assert "account2" in profs
    assert profs == {"default", "account2"}


# ---------------------------------------------------------------------------
# Scenario 3: autonomous ollama quota error → the run completes on the free
# pool (not failed). Acceptance-level statement of the fallback chain.
# ---------------------------------------------------------------------------
def test_autonomous_ollama_quota_falls_to_pool(monkeypatch):
    from core.services import non_visible_fallback as f

    monkeypatch.setattr(f, "_fallback_enabled", lambda: True)
    monkeypatch.setattr(
        f, "execute_cheap_lane_via_pool",
        lambda **k: {"text": "pool-answer", "lane": "cheap", "provider": "groq", "cost_usd": 0.0},
    )

    def ollama_quota_error():
        raise RuntimeError("429 quota exhausted")

    r = f.run_non_visible_with_fallback(
        message="autonom tanke", primary_call=ollama_quota_error, run_is_autonomous=True,
    )
    # Run completed free, not failed.
    assert r["lane"] == "cheap"
    assert r["text"] == "pool-answer"


# ---------------------------------------------------------------------------
# Locks in the empirically-proven egress map for the 13 account2 workhorses:
# groq → he6 (IPv6, its VPN IP is Cloudflare-blocked); everything else → vpn.
# ---------------------------------------------------------------------------
def test_egress_map_covers_all_13_account2_providers():
    from core.services.egress_routing import resolve_egress

    account2_providers = [
        "aihubmix", "cerebras", "cohere", "gemini", "groq", "huggingface",
        "mistral", "nvidia-nim", "opencode", "openrouter", "reka",
        "requesty", "sambanova",
    ]
    assert len(account2_providers) == 13

    for p in account2_providers:
        expected = "he6" if p == "groq" else "vpn"
        assert resolve_egress(p, "account2") == expected, (
            f"egress for {p!r} on account2 should be {expected!r}, "
            f"got {resolve_egress(p, 'account2')!r}"
        )
