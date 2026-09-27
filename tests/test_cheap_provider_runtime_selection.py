"""Tests for core/services/cheap_provider_runtime_selection.py — pool + floor."""
from __future__ import annotations


def test_quota_snapshot_is_scoped_to_auth_profile(monkeypatch):
    import core.services.cheap_provider_runtime_selection as sel
    import core.services.shared_cache as cache

    stored = {}
    monkeypatch.setattr(cache, "get", lambda key: stored.get(key))
    monkeypatch.setattr(cache, "set", lambda key, value, **_kw: stored.__setitem__(key, value))
    monkeypatch.setattr(sel, "get_cheap_provider_runtime_state", lambda **_kw: None)
    monkeypatch.setattr(sel, "count_cheap_provider_invocations",
                        lambda **kw: 2 if kw.get("auth_profile") == "default" else 30)
    base = {"provider": "groq", "model": "shared", "rpm_limit": 10, "daily_limit": 100}

    home = sel._candidate_quota_snapshot({**base, "auth_profile": "default"})
    account2 = sel._candidate_quota_snapshot({**base, "auth_profile": "account2"})

    assert home["blocked"] is False
    assert account2["blocked"] is True


def test_account_cooldown_does_not_block_other_account(monkeypatch):
    import json
    import core.services.cheap_provider_runtime_selection as sel
    import core.services.shared_cache as cache
    from datetime import UTC, datetime, timedelta

    future = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    state = {"cooldown_until": None,
             "metadata_json": json.dumps({"profile_cooldowns": {"account2": future}})}
    monkeypatch.setattr(cache, "get", lambda _key: None)
    monkeypatch.setattr(cache, "set", lambda *_args, **_kw: None)
    monkeypatch.setattr(sel, "get_cheap_provider_runtime_state", lambda **_kw: state)
    monkeypatch.setattr(sel, "count_cheap_provider_invocations", lambda **_kw: 0)
    base = {"provider": "groq", "model": "shared", "rpm_limit": 10, "daily_limit": 100}

    assert sel._candidate_quota_snapshot({**base, "auth_profile": "default"})["blocked"] is False
    assert sel._candidate_quota_snapshot({**base, "auth_profile": "account2"})["blocked"] is True


def test_account_quota_failure_records_only_profile_cooldown(monkeypatch):
    import json
    import core.services.cheap_provider_runtime_selection as sel
    from core.services.cheap_provider_runtime_adapters import CheapProviderError

    saved = {}
    monkeypatch.setattr(sel, "get_cheap_provider_runtime_state", lambda **_kw: {})
    monkeypatch.setattr(sel, "provider_auth_ready", lambda **_kw: True)
    monkeypatch.setattr(sel, "record_cheap_provider_invocation", lambda **_kw: {"invocation_id": "test"})
    monkeypatch.setattr(sel, "upsert_cheap_provider_runtime_state", lambda **kw: saved.update(kw))
    monkeypatch.setattr(sel.event_bus, "publish", lambda *_args, **_kw: None)

    sel._register_provider_failure(
        provider="groq", model="shared", auth_profile="account2",
        error=CheapProviderError(provider="groq", code="credits-exhausted", message="quota"),
    )

    assert saved["cooldown_until"] is None
    assert "account2" in json.loads(saved["metadata_json"])["profile_cooldowns"]


def test_success_clears_only_succeeding_profile_cooldown(monkeypatch):
    import json
    import core.services.cheap_provider_runtime_selection as sel
    from datetime import UTC, datetime, timedelta

    future = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    state = {"metadata_json": json.dumps({"profile_cooldowns": {
        "default": future, "account2": future,
    }})}
    saved = {}
    monkeypatch.setattr(sel, "get_cheap_provider_runtime_state", lambda **_kw: state)
    monkeypatch.setattr(sel, "upsert_cheap_provider_runtime_state", lambda **kw: saved.update(kw))

    sel._record_provider_success(provider="groq", model="shared", auth_profile="default",
                                 latency_ms=100, quality_score=None, smoke_test=False)

    assert json.loads(saved["metadata_json"])["profile_cooldowns"] == {"account2": future}


def test_provider_blocking_failure_pauses_sibling_model_until_success(isolated_runtime, monkeypatch):
    import core.services.cheap_provider_runtime_selection as sel
    import core.services.shared_cache as cache
    from core.services.cheap_provider_runtime_adapters import CheapProviderError

    monkeypatch.setattr(cache, "get", lambda _key: None)
    monkeypatch.setattr(cache, "set", lambda *_args, **_kw: None)
    monkeypatch.setattr(sel.event_bus, "publish", lambda *_args, **_kw: None)
    monkeypatch.setattr(sel, "count_cheap_provider_invocations", lambda **_kw: 0)
    candidate = {"provider": "chatanywhere", "model": "sibling", "auth_profile": "default",
                 "rpm_limit": 10, "daily_limit": 100}

    sel._register_provider_failure(
        provider="chatanywhere", model="first", auth_profile="default",
        error=CheapProviderError(provider="chatanywhere", code="provider-blocked",
                                 message="account blocked"),
    )
    assert sel._candidate_quota_snapshot(candidate)["status"] == "account-cooldown"

    sel._record_provider_success(provider="chatanywhere", model="first",
                                 auth_profile="default", latency_ms=100,
                                 quality_score=None, smoke_test=False)
    assert sel._candidate_quota_snapshot(candidate)["blocked"] is False


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


def test_small_internal_prompt_requests_latency_sensitive_route(monkeypatch):
    import core.services.cheap_provider_runtime_selection as sel

    seen = []
    monkeypatch.setattr(sel, "select_cheap_lane_target", lambda **kw: (
        seen.append(kw) or {"active": False, "provider": ""}
    ))
    monkeypatch.setattr("core.services.cheap_lane_floor.attempt_floor", lambda **_kw: {
        "status": "degraded", "provider": "floor", "text": "", "is_floor": True,
    })

    sel.execute_cheap_lane_via_pool(message="kort", task_kind="inner_voice_shadow")
    sel.execute_cheap_lane_via_pool(message="x" * 5000, task_kind="default")
    assert seen[0]["latency_sensitive"] is True
    assert seen[1]["latency_sensitive"] is False


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
    # Samme adresse-flytning som i catalogue-testen: gatewayen rykkede fra
    # 10.0.0.45 til 10.0.0.26 den 7/9-2026. Testen pinner porten og formen,
    # ikke det oktet der flytter sig.
    assert captured["proxy"].startswith("http://10.0.0.")
    assert captured["proxy"].endswith(":8888")


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


def test_slukket_udbyder_i_registret_giver_ingen_katalog_kandidater(monkeypatch):
    """17/9-2026: `enabled: false` virkede ikke for katalogets static_models —
    løkken slog op i de TÆNDTE og fik {} for en slukket udbyder."""
    from core.services import cheap_provider_runtime_selection as sel
    monkeypatch.setattr(sel, "load_provider_router_registry", lambda: {"providers": [
        {"provider": "cerebras", "enabled": False, "auth_profile": "default"},
        {"provider": "xkiro", "enabled": True, "auth_profile": "default"},
    ], "models": []})
    monkeypatch.setattr("core.services.auth_profile_scan.ready_profiles_for", lambda provider: ["default"])
    monkeypatch.setattr(sel, "_flag_multiprofile", lambda: True)
    udbydere = {c["provider"] for c in sel._configured_cheap_candidates(include_public_proxy=True)}
    assert "cerebras" not in udbydere
    assert "xkiro" in udbydere


def test_slukket_model_i_registret_kommer_ikke_ind_via_kataloget(monkeypatch):
    """17/9-2026: en model med `enabled: false` blev sprunget over FØR den blev
    markeret som set, så katalogets static_models tilføjede den igen."""
    from core.services import cheap_provider_runtime_selection as sel
    from core.services.cheap_provider_catalogue import CHEAP_PROVIDER_DEFAULTS
    modeller = list(CHEAP_PROVIDER_DEFAULTS["xkiro"]["static_models"])
    assert len(modeller) >= 2
    doed, levende = modeller[0], modeller[1]
    monkeypatch.setattr(sel, "load_provider_router_registry", lambda: {"providers": [
        {"provider": "xkiro", "enabled": True, "auth_profile": "default"},
    ], "models": [
        {"provider": "xkiro", "model": doed, "lane": "cheap", "enabled": False},
    ]})
    monkeypatch.setattr("core.services.auth_profile_scan.ready_profiles_for", lambda provider: ["default"])
    monkeypatch.setattr(sel, "_flag_multiprofile", lambda: True)
    xkiro = {c["model"] for c in sel._configured_cheap_candidates(include_public_proxy=True) if c["provider"] == "xkiro"}
    assert doed not in xkiro
    assert levende in xkiro


# ── Hvad der må ryge gennem en mellemhandler (26/9-2026) ────────────────


def test_de_to_gateways_regnes_som_mellemhandlere():
    """Bjørn: «uanset om det ryger igennem der, så må vi styre hvad der ryger
    der igennem».

    `chinaapi` og `airforce` er hans egne konti med hans egen nøgle, men begge
    er videresalgs-gateways — chinaapi svarer med `x-oneapi-request-id`. Prompten
    passerer deres server uanset hvem der ejer kontoen, og cheap-lanen kører på
    indhold fra `chat_messages`. Medlemskab her er styringen: de droppes for
    «important»-arbejde og for de kaldere der sætter `include_public_proxy=False`.
    """
    from core.services.cheap_provider_runtime_selection import _is_public_proxy

    assert _is_public_proxy("chinaapi")
    assert _is_public_proxy("airforce")


def test_nscale_er_IKKE_en_mellemhandler():
    """Førstepartsudbyder der kører sin egen inferens. At sætte den på listen
    ville gøre ordet meningsløst — og listen er kun værd at have så længe den
    betyder én ting."""
    from core.services.cheap_provider_runtime_selection import _is_public_proxy

    assert not _is_public_proxy("nscale")
