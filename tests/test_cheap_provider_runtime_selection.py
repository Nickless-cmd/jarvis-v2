"""Tests for core/services/cheap_provider_runtime_selection.py — pool + floor."""
from __future__ import annotations


def test_pool_falls_to_floor_instead_of_raising(monkeypatch):
    """Spec Fund 4: execute_cheap_lane_via_pool må ALDRIG rejse 'no-healthy-provider'
    — den falder til bunden (cheap_lane_floor)."""
    import core.services.cheap_provider_runtime_selection as sel
    monkeypatch.setattr(sel, "select_cheap_lane_target",
                        lambda **kw: {"active": False, "provider": ""})
    called = {}

    def fake_floor(*, message, lane, reason):
        called["reason"] = reason
        return {"status": "degraded", "provider": "floor", "lane": lane,
                "text": "", "is_floor": True}

    monkeypatch.setattr("core.services.cheap_lane_floor.attempt_floor", fake_floor)
    res = sel.execute_cheap_lane_via_pool(message="hej")
    assert res["provider"] == "floor"          # ingen exception
    assert called["reason"] == "no-healthy-provider"


def test_shadow_compare_off_is_noop(monkeypatch):
    """Task 9: default OFF → zero overhead, byte-identisk adfærd."""
    import core.services.cheap_provider_runtime_selection as sel
    monkeypatch.setattr(sel, "_central_route_shadow", lambda: False)
    called = {"n": 0}
    monkeypatch.setattr(sel, "_record_route_divergence",
                        lambda o, n: called.__setitem__("n", called["n"] + 1))
    sel._maybe_shadow_compare({"provider": "groq", "model": "y"})
    assert called["n"] == 0


def test_shadow_compare_on_records_divergence(monkeypatch):
    """Task 9: shadow ON → central_route FORESLÅR, divergens registreres."""
    import core.services.cheap_provider_runtime_selection as sel
    monkeypatch.setattr(sel, "_central_route_shadow", lambda: True)
    monkeypatch.setattr("core.services.central_route.route",
                        lambda **kw: {"provider": "cerebras", "model": "gemma-4-31b"})
    seen = {}
    monkeypatch.setattr(sel, "_record_route_divergence",
                        lambda o, n: seen.update({"old": o, "new": n}))
    sel._maybe_shadow_compare({"provider": "groq", "model": "y"})
    assert seen["new"]["provider"] == "cerebras"
    assert seen["old"]["provider"] == "groq"


def test_cheap_selection_excludes_paid(monkeypatch):
    """15. jul: direkte cheap/daemon-selection er gratis-only — copilot-premium (paid)
    må aldrig vælges her (kun via central_route allow_paid)."""
    import core.services.cheap_provider_runtime_selection as sel
    fake = [
        {"provider": "copilot-premium", "model": "claude-sonnet-5", "credentials_ready": True,
         "priority": 5, "effective_priority": 5},
        {"provider": "cerebras", "model": "gemma-4-31b", "credentials_ready": True,
         "priority": 22, "effective_priority": 22},
    ]
    monkeypatch.setattr(sel, "_configured_cheap_candidates", lambda **kw: list(fake))
    monkeypatch.setattr(sel, "_candidate_quota_snapshot", lambda c: {"blocked": False})
    monkeypatch.setattr(sel, "_candidate_adaptive_snapshot",
                        lambda c: {"effective_priority": c.get("priority", 99), "adaptive_penalty": 0})
    monkeypatch.setattr("core.services.cheap_provider_runtime_adapters.provider_cost_class",
                        lambda p: "paid" if p == "copilot-premium" else "free")
    t = sel.select_cheap_lane_target(task_kind="default")
    assert t.get("provider") != "copilot-premium"   # betalt ekskluderet


def _stub_groq_registry(monkeypatch, sel):
    """Gør groq til en gyldig cheap-kandidat via provider-router-registry."""
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


def test_candidates_multiprofile_when_flag_on(monkeypatch):
    from core.services import cheap_provider_runtime_selection as sel
    monkeypatch.setattr("core.services.auth_profile_scan.ready_profiles_for",
                        lambda provider: ["default", "account2"] if provider == "groq" else ["default"])
    monkeypatch.setattr(sel, "_flag_multiprofile", lambda: True)
    _stub_groq_registry(monkeypatch, sel)
    profs = {c["auth_profile"] for c in sel._configured_cheap_candidates(include_public_proxy=True)
             if c["provider"] == "groq"}
    assert profs == {"default", "account2"}


def test_roundrobin_peek_stable_until_advance():
    # A/2: the builder PEEKS the rotation (stable across the several builder calls
    # per pick); the counter only moves via _advance_profile_rr. This is what keeps
    # the split at 50/50 (advancing per builder-call skewed it well below).
    from core.services import cheap_provider_runtime_selection as sel
    sel._PROFILE_RR.clear()
    p = ["default", "account2"]
    assert sel._roundrobin_profiles("groq", p) == ["default", "account2"]
    assert sel._roundrobin_profiles("groq", p) == ["default", "account2"]  # peek: stable
    sel._advance_profile_rr("groq")
    assert sel._roundrobin_profiles("groq", p) == ["account2", "default"]  # flipped
    sel._advance_profile_rr("groq")
    assert sel._roundrobin_profiles("groq", p) == ["default", "account2"]


def test_roundrobin_builder_stable_within_pick(monkeypatch):
    # Multiple builder calls (as happen within one select) must yield the SAME first
    # profile — otherwise the used pick desyncs from the counter.
    from core.services import cheap_provider_runtime_selection as sel
    monkeypatch.setattr("core.services.auth_profile_scan.ready_profiles_for",
                        lambda provider: ["default", "account2"] if provider == "groq" else ["default"])
    monkeypatch.setattr(sel, "_flag_multiprofile", lambda: True)
    monkeypatch.setattr(sel, "_flag_profile_roundrobin", lambda: True)
    _stub_groq_registry(monkeypatch, sel)
    sel._PROFILE_RR.clear()

    def first_groq_profile():
        for c in sel._configured_cheap_candidates(include_public_proxy=True):
            if c["provider"] == "groq":
                return c["auth_profile"]

    assert first_groq_profile() == first_groq_profile() == first_groq_profile()
    sel._advance_profile_rr("groq")
    assert first_groq_profile() == "account2"


def test_roundrobin_off_keeps_default_first(monkeypatch):
    # roundrobin OFF (default): default always emitted first -> account2 stays failover.
    from core.services import cheap_provider_runtime_selection as sel
    monkeypatch.setattr("core.services.auth_profile_scan.ready_profiles_for",
                        lambda provider: ["default", "account2"] if provider == "groq" else ["default"])
    monkeypatch.setattr(sel, "_flag_multiprofile", lambda: True)
    monkeypatch.setattr(sel, "_flag_profile_roundrobin", lambda: False)
    _stub_groq_registry(monkeypatch, sel)
    for _ in range(3):
        first = next(c["auth_profile"] for c in sel._configured_cheap_candidates(include_public_proxy=True)
                     if c["provider"] == "groq")
        assert first == "default"


def test_candidates_single_profile_when_flag_off(monkeypatch):
    from core.services import cheap_provider_runtime_selection as sel
    monkeypatch.setattr(sel, "_flag_multiprofile", lambda: False)
    _stub_groq_registry(monkeypatch, sel)
    profs = [c["auth_profile"] for c in sel._configured_cheap_candidates(include_public_proxy=True)
             if c["provider"] == "groq"]
    assert len(profs) == 1


# ---------------------------------------------------------------------------
# Task 8b: inject proxy per egress + leak guard
# ---------------------------------------------------------------------------
def test_resolve_proxy_home_is_none():
    from core.services import cheap_provider_runtime_selection as sel
    assert sel._resolve_proxy("home") is None
    assert sel._resolve_proxy("") is None


def test_resolve_proxy_vpn_endpoint():
    from core.services import cheap_provider_runtime_selection as sel
    assert sel._resolve_proxy("vpn", {"vpn": "http://10.0.0.45:8888"}) == "http://10.0.0.45:8888"


def test_resolve_proxy_leak_guard_raises():
    from core.services import cheap_provider_runtime_selection as sel
    import pytest
    with pytest.raises(RuntimeError):
        sel._resolve_proxy("vpn", {})   # non-home egress but no endpoint -> refuse


def _stub_openai_compat_http(monkeypatch):
    """Stub the credential + defaults + HTTP seam on the facade so
    _execute_openai_compatible_chat runs offline and we can capture the proxy
    passed to the lowest-level HTTP call. Returns the captured-kwargs dict."""
    from core.services import cheap_provider_runtime as facade
    captured: dict = {}

    def fake_http_json(url, *, provider, proxy=None, **kw):
        captured["proxy"] = proxy
        captured["url"] = url
        return ({"choices": [{"message": {"content": "ok"}}], "usage": {}}, {})

    monkeypatch.setattr(facade, "_require_credentials",
                        lambda *, profile, provider: {"api_key": "k"})
    monkeypatch.setattr(facade, "provider_runtime_defaults",
                        lambda provider: {"base_url": "https://api.cohere.ai/compatibility/v1"})
    monkeypatch.setattr(facade, "_http_json", fake_http_json)
    return captured


def test_executor_sets_proxy_for_account2(monkeypatch):
    # flag ON + account2 (cohere -> egress vpn) -> proxy == vpn endpoint.
    from core.services import cheap_provider_runtime_selection as sel
    monkeypatch.setattr(sel, "_flag_multiprofile", lambda: True)
    captured = _stub_openai_compat_http(monkeypatch)
    sel._execute_provider_chat(
        provider="cohere", model="command", auth_profile="account2",
        base_url="https://api.cohere.ai/compatibility/v1", message="hi",
    )
    assert captured["proxy"] == "http://10.0.0.45:8888"


def test_executor_no_proxy_for_default(monkeypatch):
    # flag ON but auth_profile=default -> egress home -> no proxy.
    from core.services import cheap_provider_runtime_selection as sel
    monkeypatch.setattr(sel, "_flag_multiprofile", lambda: True)
    captured = _stub_openai_compat_http(monkeypatch)
    sel._execute_provider_chat(
        provider="cohere", model="command", auth_profile="default",
        base_url="https://api.cohere.ai/compatibility/v1", message="hi",
    )
    assert captured["proxy"] is None


def test_executor_no_proxy_when_flag_off(monkeypatch):
    # flag OFF -> proxy path never engages even for account2 (unchanged behavior).
    from core.services import cheap_provider_runtime_selection as sel
    monkeypatch.setattr(sel, "_flag_multiprofile", lambda: False)
    captured = _stub_openai_compat_http(monkeypatch)
    sel._execute_provider_chat(
        provider="cohere", model="command", auth_profile="account2",
        base_url="https://api.cohere.ai/compatibility/v1", message="hi",
    )
    assert captured["proxy"] is None
