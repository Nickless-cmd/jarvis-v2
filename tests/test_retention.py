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
