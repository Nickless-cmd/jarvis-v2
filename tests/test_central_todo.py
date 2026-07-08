"""Tests for Central TODO (central_todo) — prioriteret pollbar huskeliste på tværs af clusters."""
from __future__ import annotations

import pytest

from core.services import central_todo as ct


@pytest.fixture
def mocked_sources(monkeypatch):
    # list_central_incidents now takes unresolved_only — accept **kwargs so the
    # mock stays compatible with the current call signature.
    monkeypatch.setattr("core.runtime.db_central_incidents.list_central_incidents",
                        lambda limit=30, min_severity=None, **kwargs: [
                            {"id": 1, "cluster": "auth", "nerve": "tool_access", "message": "uautoriseret"}])
    monkeypatch.setattr("core.services.central_correlate.recent_broken_runs",
                        lambda window=500: [{"run_id": "r1", "cluster": "truth", "nerve": "truth",
                                             "reason": "konfabulation", "file": "x.py"}])
    monkeypatch.setattr("core.services.config_drift.check_port_drift",
                        lambda: {"drift": True, "declared_port": 8010, "actual_port": 8080})
    monkeypatch.setattr("core.services.daemon_health.daemon_health_summary",
                        lambda window=1000: {"failing_daemons": {"process_watcher": 3}})
    monkeypatch.setattr("core.services.db_sentinel.dead_table_candidates",
                        lambda: ["empty_a", "empty_b"])
    monkeypatch.setattr("core.services.endpoint_usage_store.dead_endpoints",
                        lambda: ["GET /unused"])
    # New §6 learning-suggestion source — mock to empty so the fixed set of
    # sources under test stays deterministic.
    monkeypatch.setattr("core.services.central_learning.propose_adjustments",
                        lambda *a, **k: [])


def test_build_todo_aggregates_and_prioritizes(mocked_sources):
    todo = ct.build_todo()
    sources = {it["source"] for it in todo}
    assert {"incident", "broken_run", "config_drift", "daemon", "db", "endpoint"} <= sources
    # severe incident (priority 1) skal komme før oprydning (priority 5)
    assert todo[0]["priority"] == 1 and todo[0]["source"] == "incident"
    assert todo[-1]["priority"] == 5


def test_poll_counts_by_priority(mocked_sources):
    p = ct.poll(limit=10)
    assert p["critical"] >= 1 and p["high"] >= 2  # incident + (broken_run + config_drift)
    assert p["cleanup"] >= 2  # db + endpoint
    assert len(p["top"]) <= 10


def test_self_safe_when_sources_fail(monkeypatch):
    # alle kilder kaster → tom liste, ingen exception
    for path in ("core.runtime.db_central_incidents.list_central_incidents",
                 "core.services.central_correlate.recent_broken_runs",
                 "core.services.config_drift.check_port_drift",
                 "core.services.daemon_health.daemon_health_summary",
                 "core.services.db_sentinel.dead_table_candidates",
                 "core.services.endpoint_usage_store.dead_endpoints",
                 "core.services.central_learning.propose_adjustments"):
        monkeypatch.setattr(path, lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    assert ct.build_todo() == []


def test_no_config_drift_no_item(monkeypatch, mocked_sources):
    monkeypatch.setattr("core.services.config_drift.check_port_drift", lambda: {"drift": False})
    todo = ct.build_todo()
    assert not any(it["source"] == "config_drift" for it in todo)


def test_incident_is_fresh_helper():
    from datetime import UTC, datetime, timedelta
    now = datetime.now(UTC)
    assert ct._incident_is_fresh({"ts": now.isoformat()}) is True
    old = (now - timedelta(hours=ct._INCIDENT_TODO_MAX_AGE_H + 5)).isoformat()
    assert ct._incident_is_fresh({"ts": old}) is False
    assert ct._incident_is_fresh({}) is True            # ingen ts → fail-open (vis)
    assert ct._incident_is_fresh({"ts": "ikke-en-dato"}) is True  # uparsbar → fail-open


def test_stale_severe_incident_not_elected_as_todo(monkeypatch):
    """En severe incident ældre end tærsklen bliver IKKE en agenda-todo (fastlåser ikke
    next_intention) — men en frisk gør. Andre kilder stubbes fejlende (self-safe)."""
    from datetime import UTC, datetime, timedelta
    now = datetime.now(UTC)
    old_ts = (now - timedelta(hours=ct._INCIDENT_TODO_MAX_AGE_H + 5)).isoformat()
    monkeypatch.setattr(
        "core.runtime.db_central_incidents.list_central_incidents",
        lambda limit=30, min_severity=None, **kwargs: [
            {"id": 1, "cluster": "connections", "nerve": "unauthorized",
             "message": "gammel rolle-deny operator_bash", "ts": old_ts},
            {"id": 2, "cluster": "truth", "nerve": "fact_gate",
             "message": "frisk incident", "ts": now.isoformat()}])
    for path in ("core.services.central_correlate.recent_broken_runs",
                 "core.services.config_drift.check_port_drift",
                 "core.services.daemon_health.daemon_health_summary",
                 "core.services.db_sentinel.dead_table_candidates",
                 "core.services.endpoint_usage_store.dead_endpoints",
                 "core.services.central_learning.propose_adjustments"):
        monkeypatch.setattr(path, lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    incident_msgs = [i["what"] for i in ct.build_todo() if i.get("source") == "incident"]
    assert any("frisk" in m for m in incident_msgs)
    assert not any("gammel" in m for m in incident_msgs)
