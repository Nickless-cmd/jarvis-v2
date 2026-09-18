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
    record_quota_observation(
        provider="groq", auth_profile="default", period="month", unit="tokens",
        limit=900_000, remaining=700_000, reset_at="2026-10-01T00:00:00+00:00",
        observed_at="2026-09-18T10:00:00+00:00",
    )
    window = capacity_snapshot(
        now=datetime(2026, 9, 18, 11, tzinfo=UTC)
    )["windows"][0]

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
        "provider": "mistral", "period": "month", "unit": "tokens",
    }]
