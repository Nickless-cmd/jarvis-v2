from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest


@pytest.fixture
def cheap_registry(tmp_path, monkeypatch):
    path = tmp_path / "provider_router.json"
    path.write_text(json.dumps({
        "providers": [{
            "provider": "groq", "enabled": True, "auth_profile": "default",
            "quota_policy": [],
        }],
        "models": [{
            "provider": "groq", "model": "llama", "lane": "cheap", "enabled": True,
        }],
    }), encoding="utf-8")
    import core.runtime.config as cfg
    import core.runtime.provider_router as router
    monkeypatch.setattr(cfg, "PROVIDER_ROUTER_FILE", path, raising=False)
    monkeypatch.setattr(router, "PROVIDER_ROUTER_FILE", path, raising=False)
    monkeypatch.setattr(router, "_credentials_ready", lambda **_kw: True)
    return path


def test_provider_report_beats_config_and_counts_token_usage(
    isolated_runtime, cheap_registry
):
    from core.runtime.db_cheap_provider import record_cheap_provider_invocation
    from core.runtime.db_cheap_lane_control import record_quota_observation
    from core.services.cheap_lane_quotas import capacity_snapshot, set_quota_policy

    set_quota_policy(provider="groq", auth_profile="default", windows=[{
        "period": "month", "unit": "tokens", "limit": 1_000_000,
        "reset_timezone": "UTC", "reset_day": 1,
    }])
    record_cheap_provider_invocation(
        provider="groq", model="llama", status="completed",
        input_tokens=100, output_tokens=50, auth_profile="default",
    )
    # TIDEN SKAL HÆNGE SAMMEN (21/9-2026). Kaldet ovenfor stemples med det
    # RIGTIGE ur, mens snapshottet fik en fast dato. Så længe den faste dato
    # tilfældigvis lå efter «nu», gik det godt — men med uret stillet frem lå
    # kaldet i FREMTIDEN set fra vinduet, blev ikke talt med, og
    # `observed_usage` faldt fra 150 til 0. Målt med faketime: testen knækker
    # 1/11-2026. Nu følger begge ender det samme ur.
    nu = datetime.now(UTC)
    record_quota_observation(
        provider="groq", auth_profile="default", period="month", unit="tokens",
        limit=900_000, remaining=700_000,
        reset_at=(nu + timedelta(days=13)).isoformat(),
        observed_at=(nu - timedelta(hours=1)).isoformat(),
    )
    window = capacity_snapshot(now=nu)["windows"][0]

    assert window["source"] == "provider"
    assert window["limit"] == 900_000
    assert window["used"] == 200_000  # provider remaining is authoritative
    assert window["observed_usage"] == 150


def test_stale_provider_report_falls_back_to_config(isolated_runtime, cheap_registry):
    from core.runtime.db_cheap_lane_control import record_quota_observation
    from core.services.cheap_lane_quotas import capacity_snapshot, set_quota_policy

    set_quota_policy(provider="groq", auth_profile="default", windows=[{
        "period": "week", "unit": "requests", "limit": 500,
    }])
    record_quota_observation(
        provider="groq", auth_profile="default", period="week", unit="requests",
        limit=400, remaining=100, reset_at=None,
        observed_at=(datetime(2026, 9, 10, tzinfo=UTC)).isoformat(),
    )
    window = capacity_snapshot(
        now=datetime(2026, 9, 18, 11, tzinfo=UTC)
    )["windows"][0]
    assert window["source"] == "configured"
    assert window["limit"] == 500
    assert window["used"] == 0


def test_aggregate_keeps_units_separate_and_unknown_is_not_zero(
    isolated_runtime, cheap_registry
):
    from core.services.cheap_lane_quotas import capacity_snapshot, set_quota_policy

    set_quota_policy(provider="groq", auth_profile="default", windows=[
        {"period": "month", "unit": "tokens", "limit": 1_000},
        {"period": "month", "unit": "requests", "limit": 20},
    ])
    snapshot = capacity_snapshot(now=datetime.now(UTC))

    assert snapshot["totals"]["month:tokens"]["limit"] == 1_000
    assert snapshot["totals"]["month:requests"]["limit"] == 20
    assert "month:credits_usd" not in snapshot["totals"]
    assert snapshot["unknown_members"] == []


def test_usage_excludes_rows_before_calendar_month(isolated_runtime, cheap_registry):
    from core.runtime.db import connect
    from core.runtime.db_cheap_provider import record_cheap_provider_invocation
    from core.services.cheap_lane_quotas import capacity_snapshot, set_quota_policy

    set_quota_policy(provider="groq", auth_profile="default", windows=[{
        "period": "month", "unit": "tokens", "limit": 1_000,
    }])
    old = record_cheap_provider_invocation(
        provider="groq", status="completed", input_tokens=900,
        auth_profile="default",
    )
    recent = record_cheap_provider_invocation(
        provider="groq", status="completed", input_tokens=100,
        auth_profile="default",
    )
    with connect() as conn:
        conn.execute("UPDATE cheap_provider_invocations SET created_at=? WHERE invocation_id=?",
                     ("2026-08-31T23:59:59+00:00", old["invocation_id"]))
        conn.execute("UPDATE cheap_provider_invocations SET created_at=? WHERE invocation_id=?",
                     ("2026-09-02T00:00:00+00:00", recent["invocation_id"]))
        conn.commit()
    window = capacity_snapshot(now=datetime(2026, 9, 18, tzinfo=UTC))["windows"][0]
    assert window["used"] == 100


def test_unknown_provider_capacity_makes_aggregate_incomplete(
    isolated_runtime, cheap_registry
):
    data = json.loads(cheap_registry.read_text(encoding="utf-8"))
    data["providers"].append({
        "provider": "mistral", "enabled": True, "auth_profile": "default",
    })
    data["models"].append({
        "provider": "mistral", "model": "small", "lane": "cheap", "enabled": True,
    })
    cheap_registry.write_text(json.dumps(data), encoding="utf-8")
    from core.services.cheap_lane_quotas import capacity_snapshot, set_quota_policy

    set_quota_policy(provider="groq", auth_profile="default", windows=[{
        "period": "month", "unit": "tokens", "limit": 1_000,
    }])
    snapshot = capacity_snapshot(now=datetime(2026, 9, 18, tzinfo=UTC))
    total = snapshot["totals"]["month:tokens"]

    assert total["complete"] is False
    assert total["limit"] is None
    assert total["known_limit"] == 1_000
    assert snapshot["unknown_members"] == [{
        "provider": "mistral", "auth_profile": "default",
        "period": "month", "unit": "tokens",
    }]


def test_capacity_usage_counts_both_accounts_without_quota_policy(
    isolated_runtime, cheap_registry
):
    from core.runtime.db_cheap_provider import record_cheap_provider_invocation
    from core.services.cheap_lane_quotas import capacity_snapshot

    for profile, input_tokens, output_tokens in (
        ("default", 100, 40), ("account2", 70, 30),
    ):
        record_cheap_provider_invocation(
            provider="groq", model="llama", status="completed",
            input_tokens=input_tokens, output_tokens=output_tokens,
            auth_profile=profile,
        )
    snapshot = capacity_snapshot(now=datetime.now(UTC))

    assert snapshot["windows"] == []
    day = snapshot["usage"]["day"]
    assert (day["input_tokens"], day["output_tokens"], day["total_tokens"]) == (170, 70, 240)
    assert {(row["provider"], row["auth_profile"]): row["total_tokens"]
            for row in day["profiles"]} == {
        ("groq", "default"): 140, ("groq", "account2"): 100,
    }


def test_capacity_aggregate_keeps_unconfigured_account_unknown(
    isolated_runtime, cheap_registry, monkeypatch
):
    from core.services import auth_profile_scan
    from core.runtime import db_core
    from core.services.cheap_lane_quotas import capacity_snapshot, set_quota_policy

    monkeypatch.setattr(db_core, "get_runtime_state_bool", lambda *_args: True)
    monkeypatch.setattr(auth_profile_scan, "ready_profiles_for",
                        lambda provider: ["default", "account2"] if provider == "groq" else [])
    set_quota_policy(provider="groq", auth_profile="default", windows=[{
        "period": "month", "unit": "tokens", "limit": 1_000,
    }])
    snapshot = capacity_snapshot(now=datetime.now(UTC))

    assert snapshot["totals"]["month:tokens"]["complete"] is False
    assert snapshot["totals"]["month:tokens"]["known_limit"] == 1_000
    assert {m["auth_profile"] for m in snapshot["unknown_members"]} == {"account2"}


def test_request_based_estimate_uses_distinct_active_accounts(
    isolated_runtime, cheap_registry, monkeypatch
):
    from core.runtime.db_cheap_provider import record_cheap_provider_invocation
    from core.services import auth_profile_scan
    from core.runtime import db_core
    from core.services.cheap_provider_catalogue import CHEAP_PROVIDER_DEFAULTS
    from core.services.cheap_lane_quotas import capacity_snapshot

    monkeypatch.setattr(db_core, "get_runtime_state_bool", lambda *_args: True)
    monkeypatch.setattr(auth_profile_scan, "ready_profiles_for",
                        lambda provider: ["default", "account2"])
    monkeypatch.setitem(CHEAP_PROVIDER_DEFAULTS["groq"], "daily_limit", 10)
    for profile, tokens in (("default", 100), ("account2", 50)):
        record_cheap_provider_invocation(
            provider="groq", model="llama", status="completed",
            input_tokens=tokens, output_tokens=0, auth_profile=profile,
        )
    snapshot = capacity_snapshot(now=datetime.now(UTC))
    estimate = snapshot["estimated_capacity"]["day"]

    assert estimate["known_estimate_tokens"] == 1350
    assert estimate["complete"] is True
    assert {(p["provider"], p["auth_profile"]) for p in estimate["profiles"]} == {
        ("groq", "default"), ("groq", "account2"),
    }


def test_account2_can_have_its_own_quota_policy(
    isolated_runtime, cheap_registry, monkeypatch
):
    from core.services import auth_profile_scan
    from core.runtime import db_core
    from core.services.cheap_lane_quotas import capacity_snapshot, set_quota_policy

    monkeypatch.setattr(db_core, "get_runtime_state_bool", lambda *_args: True)
    monkeypatch.setattr(auth_profile_scan, "ready_profiles_for",
                        lambda provider: ["default", "account2"])
    first = set_quota_policy(provider="groq", auth_profile="default", windows=[{
        "period": "day", "unit": "tokens", "limit": 1000,
    }])
    second = set_quota_policy(provider="groq", auth_profile="account2", windows=[{
        "period": "day", "unit": "tokens", "limit": 2000,
    }])
    snapshot = capacity_snapshot(now=datetime.now(UTC))

    assert first["status"] == second["status"] == "ok"
    assert snapshot["totals"]["day:tokens"]["limit"] == 3000
    assert snapshot["totals"]["day:tokens"]["complete"] is True


def test_fresh_provider_observation_is_visible_without_manual_policy(
    isolated_runtime, cheap_registry
):
    from core.runtime.db_cheap_lane_control import record_quota_observation
    from core.services.cheap_lane_quotas import capacity_snapshot

    now = datetime.now(UTC)
    record_quota_observation(
        provider="groq", auth_profile="default", period="day", unit="tokens",
        limit=5000, remaining=4200, reset_at=None, observed_at=now.isoformat(),
    )
    snapshot = capacity_snapshot(now=now)

    assert snapshot["totals"]["day:tokens"]["limit"] == 5000
    assert snapshot["windows"][0]["source"] == "provider"
    assert snapshot["windows"][0]["remaining"] == 4200


def test_ready_second_account_is_not_counted_while_multiprofile_is_off(
    isolated_runtime, cheap_registry, monkeypatch
):
    from core.runtime import db_core
    from core.services import auth_profile_scan
    from core.services.cheap_lane_quotas import capacity_snapshot, set_quota_policy

    monkeypatch.setattr(db_core, "get_runtime_state_bool", lambda *_args: False)
    monkeypatch.setattr(auth_profile_scan, "ready_profiles_for",
                        lambda provider: ["default", "account2"])
    set_quota_policy(provider="groq", auth_profile="default", windows=[{
        "period": "day", "unit": "tokens", "limit": 1000,
    }])

    snapshot = capacity_snapshot(now=datetime.now(UTC))
    assert snapshot["totals"]["day:tokens"]["complete"] is True
    assert snapshot["totals"]["day:tokens"]["limit"] == 1000
