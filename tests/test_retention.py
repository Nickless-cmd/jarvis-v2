from datetime import UTC, datetime, timedelta

import core.services.retention as ret


def test_should_run_first_time():
    assert ret._should_run(None, datetime.now(UTC)) is True


def test_should_run_respects_24h_throttle():
    now = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
    recent = (now - timedelta(hours=5)).isoformat()
    old = (now - timedelta(hours=25)).isoformat()
    assert ret._should_run(recent, now) is False
    assert ret._should_run(old, now) is True


def test_should_run_bad_timestamp_defaults_true():
    assert ret._should_run("ikke-en-dato", datetime.now(UTC)) is True


def test_sweep_skips_when_recently_run(monkeypatch):
    now = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(ret, "get_runtime_state_value", lambda k, d: (now - timedelta(hours=2)).isoformat(), raising=False)
    # Patch db-import-stien som run_retention_sweep bruger
    import core.runtime.db as db
    monkeypatch.setattr(db, "get_runtime_state_value", lambda k, d=None: (now - timedelta(hours=2)).isoformat())
    res = ret.run_retention_sweep(now=now)
    assert res["ran"] is False
    assert res["reason"] == "cadence"


def test_sweep_runs_and_aggregates(monkeypatch):
    now = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
    import core.runtime.db as db
    monkeypatch.setattr(db, "get_runtime_state_value", lambda k, d=None: None)
    monkeypatch.setattr(db, "set_runtime_state_value", lambda k, v: None)
    monkeypatch.setattr("core.services.reasoning_store.compact_stale", lambda: 7)
    monkeypatch.setattr(ret, "_prune_unmatched_policies", lambda d, n: 3)
    monkeypatch.setattr(ret, "_prune_telemetry", lambda t, a, n: 5)
    res = ret.run_retention_sweep(now=now, force=True)
    assert res["ran"] is True
    assert res["removed"]["reasoning_conclusions"] == 7
    assert res["removed"]["generalized_policies"] == 3
    assert res["total"] == 7 + 3 + 5 * 2  # 2 telemetri-tabeller


def test_sweep_one_table_failure_does_not_stop_others(monkeypatch):
    now = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
    import core.runtime.db as db
    monkeypatch.setattr(db, "get_runtime_state_value", lambda k, d=None: None)
    monkeypatch.setattr(db, "set_runtime_state_value", lambda k, v: None)
    monkeypatch.setattr("core.services.reasoning_store.compact_stale",
                        lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(ret, "_prune_unmatched_policies", lambda d, n: 2)
    monkeypatch.setattr(ret, "_prune_telemetry", lambda t, a, n: 1)
    res = ret.run_retention_sweep(now=now, force=True)
    assert res["ran"] is True
    assert "reasoning_conclusions" not in res["removed"]  # fejlede, men de andre kørte
    assert res["removed"]["generalized_policies"] == 2


def test_metadata_retention_defaults_to_60_days_and_payload_to_7(
    isolated_runtime, monkeypatch
):
    from core.runtime.db_core import connect
    from core.runtime.db_cheap_provider import record_cheap_provider_invocation
    from core.services.cheap_lane_payloads import capture_invocation_payload

    now = datetime.now(UTC)
    keep = record_cheap_provider_invocation(provider="groq", status="completed")
    remove = record_cheap_provider_invocation(provider="groq", status="completed")
    payload = record_cheap_provider_invocation(provider="groq", status="completed")
    capture_invocation_payload(
        invocation_id=str(payload["invocation_id"]), prompt="hello", response="world"
    )
    with connect() as conn:
        conn.execute(
            "UPDATE cheap_provider_invocations SET created_at=? WHERE invocation_id=?",
            ((now - timedelta(days=59)).isoformat(), keep["invocation_id"]),
        )
        conn.execute(
            "UPDATE cheap_provider_invocations SET created_at=? WHERE invocation_id=?",
            ((now - timedelta(days=61)).isoformat(), remove["invocation_id"]),
        )
        conn.execute(
            "UPDATE cheap_lane_redacted_payloads SET expires_at=? WHERE invocation_id=?",
            ((now - timedelta(days=1)).isoformat(), payload["invocation_id"]),
        )
        conn.commit()

    import core.runtime.db as db
    monkeypatch.setattr(db, "get_runtime_state_value", lambda *_a, **_kw: None)
    monkeypatch.setattr(db, "set_runtime_state_value", lambda *_a, **_kw: None)
    monkeypatch.setattr("core.services.reasoning_store.compact_stale", lambda: 0)
    result = ret.run_retention_sweep(force=True, now=now)

    with connect() as conn:
        ids = {
            row["invocation_id"] for row in conn.execute(
                "SELECT invocation_id FROM cheap_provider_invocations"
            ).fetchall()
        }
        payload_count = conn.execute(
            "SELECT COUNT(*) AS n FROM cheap_lane_redacted_payloads"
        ).fetchone()["n"]
    assert keep["invocation_id"] in ids
    assert remove["invocation_id"] not in ids
    assert payload["invocation_id"] in ids
    assert payload_count == 0
    assert result["removed"]["cheap_lane_redacted_payloads"] == 1
