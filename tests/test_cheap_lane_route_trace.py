from __future__ import annotations


def _candidate(provider: str, *, ready: bool = True) -> dict[str, object]:
    return {
        "provider": provider,
        "model": f"{provider}-model",
        "auth_profile": "default",
        "credentials_ready": ready,
        "priority": 10 if provider == "groq" else 20,
        "base_url": f"https://{provider}.example",
        "egress": "home",
    }


def test_selection_records_selected_and_rejected_candidates(
    isolated_runtime, monkeypatch
):
    from core.runtime.db_cheap_lane_control import get_route_decision
    from core.services import cheap_provider_runtime_selection as selection

    candidates = [_candidate("missing", ready=False), _candidate("groq")]
    monkeypatch.setattr(
        selection, "_configured_cheap_candidates", lambda **_kwargs: candidates
    )
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime_adapters.provider_cost_class",
        lambda _provider: "free",
    )
    monkeypatch.setattr(
        selection,
        "_candidate_quota_snapshot",
        lambda _candidate: {
            "blocked": False,
            "status": "ready",
            "requests_last_minute": 0,
            "requests_last_day": 0,
            "rpm_limit": 10,
            "daily_limit": 100,
        },
    )
    monkeypatch.setattr(
        selection,
        "_candidate_adaptive_snapshot",
        lambda candidate: {
            "effective_priority": candidate["priority"],
            "adaptive_penalty": 0,
        },
    )
    monkeypatch.setattr(selection, "_maybe_shadow_compare", lambda _target: None)
    monkeypatch.setattr(
        selection,
        "_maybe_central_route_live",
        lambda target, *_args: target,
    )
    monkeypatch.setattr(selection, "_flag_profile_roundrobin", lambda: False)

    target = selection.select_cheap_lane_target(
        task_kind="background", correlation_id="corr-select", daemon="dream"
    )
    trace = get_route_decision(str(target["route_decision_id"]))

    assert target["provider"] == "groq"
    assert trace is not None
    assert trace["correlation_id"] == "corr-select"
    assert trace["selected_slot_id"] == "groq::groq-model::default"
    assert [row["eligibility_reason"] for row in trace["candidates"]] == [
        "auth-not-ready",
        "eligible",
    ]


def test_fallback_keeps_correlation_and_links_attempts(isolated_runtime, monkeypatch):
    from core.runtime.db_cheap_lane_control import list_cheap_lane_invocations
    from core.services import cheap_provider_runtime as facade
    from core.services import cheap_provider_runtime_selection as selection
    from core.services.cheap_provider_runtime_adapters import CheapProviderError

    targets = iter(
        [
            {**_candidate("groq"), "route_decision_id": "route-1"},
            {**_candidate("gemini"), "route_decision_id": "route-2"},
        ]
    )
    monkeypatch.setattr(selection, "select_cheap_lane_target", lambda **_kw: next(targets))
    calls = {"count": 0}

    def execute(**_kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise CheapProviderError(
                provider="groq", code="rate-limited", message="busy"
            )
        return {
            "text": "ok",
            "input_tokens": 2,
            "output_tokens": 3,
            "cache_hit_tokens": 1,
            "cache_miss_tokens": 1,
            "cost_usd": 0.0,
        }

    monkeypatch.setattr(facade, "_execute_provider_chat", execute)
    monkeypatch.setattr(
        selection,
        "_fallback_after_failure",
        lambda **_kw: {"provider": "gemini", "model": "gemini-model"},
    )
    monkeypatch.setattr(selection, "provider_auth_ready", lambda **_kw: True)
    monkeypatch.setattr(selection, "_record_provider_success", lambda **_kw: None)
    monkeypatch.setattr(selection, "record_cost", lambda **_kw: None)
    monkeypatch.setattr(selection.event_bus, "publish", lambda *_args, **_kw: None)

    selection.execute_cheap_lane_via_pool(
        message="hello",
        correlation_id="corr-fallback",
        daemon="dream",
        task_kind="background",
    )
    rows = list_cheap_lane_invocations(
        since="2026-01-01T00:00:00+00:00", correlation_id="corr-fallback"
    )["items"]
    rows = sorted(rows, key=lambda row: int(row["attempt"]))

    assert [row["attempt"] for row in rows] == [1, 2]
    assert [row["status"] for row in rows] == ["failed", "completed"]
    assert rows[1]["fallback_parent_id"] == rows[0]["invocation_id"]
    assert rows[1]["cache_hit_tokens"] == 1
    assert rows[1]["task_kind"] == "background"
    assert rows[1]["daemon"] == "dream"


def test_status_surface_does_not_persist_a_fake_route(isolated_runtime, monkeypatch):
    from core.runtime.db import connect
    from core.runtime.db_cheap_lane_control import get_route_decision
    from core.services import cheap_provider_runtime_selection as selection

    assert get_route_decision("missing") is None
    monkeypatch.setattr(selection, "_configured_cheap_candidates", lambda **_kw: [])
    monkeypatch.setattr(selection, "_flag_profile_roundrobin", lambda: False)
    selection.cheap_lane_status_surface()

    with connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM cheap_lane_route_decisions"
        ).fetchone()
    assert int(row["n"]) == 0
