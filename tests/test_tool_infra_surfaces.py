"""Surfaces for vaerktoejs-infrastrukturen (dark-edges batch 1).

Hver test goer det samme: (1) en tom/manglende kilde giver active=False med en
AERLIG aarsag, (2) data skrives gennem kildens EGEN producent, (3) surface'en
laeses, og tallene er de skrevne, (4) mere data aendrer tallet. En surface der
altid svarer det samme kan ikke bestaa (4).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest


# ── faelles hjaelpere ────────────────────────────────────────────────────────

@pytest.fixture
def db(monkeypatch, tmp_path):
    """Frisk sqlite-DB som ALLE de steder surface'erne henter `connect` fra peger paa."""
    path = tmp_path / "jarvis.db"

    def _connect():
        c = sqlite3.connect(path)
        c.row_factory = sqlite3.Row
        return c

    import core.runtime.db as dbmod
    import core.runtime.db_composites as dbc
    import core.runtime.db_core as dbcore
    import core.runtime.db_runtime_tasks as dbt
    import core.services.causal_inference_daemon as cid
    monkeypatch.setattr(dbmod, "connect", _connect)
    monkeypatch.setattr(dbcore, "connect", _connect)
    monkeypatch.setattr(dbc, "connect", _connect)
    monkeypatch.setattr(dbt, "connect", _connect)
    monkeypatch.setattr(cid, "connect", _connect)
    return _connect


@pytest.fixture
def bus(monkeypatch):
    """In-memory eventbus: publish() skriver, recent_by_family() laeser det samme."""
    from core.eventbus.bus import event_bus
    log: list[dict] = []

    def publish(kind, payload=None, **_):
        log.insert(0, {"kind": kind, "payload": dict(payload or {})})

    def recent_by_family(family, *, limit=50):
        return [e for e in log if e["kind"].startswith(f"{family}.")][:limit]

    monkeypatch.setattr(event_bus, "publish", publish)
    monkeypatch.setattr(event_bus, "recent_by_family", recent_by_family)
    return log


def _ok(s, mode):
    assert s["mode"] == mode
    assert isinstance(s["signals"], dict)
    assert isinstance(s["summary"], str) and s["summary"]
    return s


def _inactive(s, mode, why):
    _ok(s, mode)
    assert s["active"] is False
    assert why in s["reason"], s["reason"]
    return s


# ── 1. tool_calling_evidence ─────────────────────────────────────────────────

def _agent_runs(connect, rows):
    with connect() as c:
        c.execute("CREATE TABLE IF NOT EXISTS agent_runs (run_id TEXT, provider TEXT, model TEXT, "
                  "output_payload_json TEXT)")
        for i, (prov, model, calls) in enumerate(rows):
            c.execute("INSERT INTO agent_runs VALUES (?,?,?,?)",
                      (f"r{i}-{prov}-{model}", prov, model, json.dumps({"tool_calls": calls})))
        c.commit()


def test_tool_calling_evidence_surface(db):
    from core.services.tool_calling_evidence import build_tool_calling_evidence_surface as build
    _inactive(build(), "tool-calling-evidence", "agent_runs kunne ikke laeses")  # ingen tabel
    _agent_runs(db, [])
    _inactive(build(), "tool-calling-evidence", "ingen raekker")
    _agent_runs(db, [("a", "kan", 1)] * 30 + [("b", "mute", 0)] * 30 + [("c", "ny", 0)] * 3)
    s = _ok(build(), "tool-calling-evidence")
    assert s["active"] is True
    assert s["signals"] == {
        "models": 3, "runs": 63, "runs_with_calls": 30,
        "verdicts": {"kan": 1, "kan-ikke": 1, "umaalt": 1},
        "blocked_models": ["b/mute"], "min_runs": 25, "min_share": 0.02,
    }
    _agent_runs(db, [("c", "ny", 0)] * 30)  # c/ny passerer taerskelen med nul kald
    assert build()["signals"]["blocked_models"] == ["b/mute", "c/ny"]


# ── 2. tool_embeddings ───────────────────────────────────────────────────────

def test_tool_embeddings_surface(monkeypatch, tmp_path):
    import core.services.tool_embeddings as te
    monkeypatch.setattr(te, "_DB_PATH", tmp_path / "tool_embeddings.sqlite")
    monkeypatch.setattr(te, "_compute_embedding", lambda text, **k: [0.1, 0.2, 0.3, 0.4])
    _inactive(te.build_tool_embeddings_surface(), "tool-embeddings", "findes ikke")
    assert not te._DB_PATH.exists(), "surface'en maa ikke oprette databasen"
    te.get_embedding("read_file", "laeser en fil")
    s = _ok(te.build_tool_embeddings_surface(), "tool-embeddings")
    assert s["active"] is True
    assert s["signals"]["embedded_tools"] == 1 and s["signals"]["dimensions"] == 4
    assert s["signals"]["newest_computed_at"].endswith("+00:00")
    te.get_embedding("write_file", "skriver en fil")
    assert te.build_tool_embeddings_surface()["signals"]["embedded_tools"] == 2
    te.invalidate("read_file")
    assert te.build_tool_embeddings_surface()["signals"]["embedded_tools"] == 1


# ── 3. tool_hunt_nudge ───────────────────────────────────────────────────────

def test_tool_hunt_nudge_surface(bus, monkeypatch):
    import core.services.tool_hunt_nudge as n
    monkeypatch.setattr(n, "_taendt", lambda: True)
    s = _inactive(n.build_tool_hunt_nudge_surface(), "tool-hunt-nudge", "ingen tool_discovery.hunt_*")
    assert (s["signals"]["notes"], s["signals"]["hits"], s["signals"]["misses"]) == (0, 0, 0)
    n._log("grep", "run1", 0.8, "soeger efter noget")
    n._log_svar("hit", "run1", {"vaerktoej": "grep", "slags": "soeg", "kald": 2})
    n._log("find", "run2", 0.6, "mere soegning")
    n._log_svar("miss", "run2", {"vaerktoej": "find", "slags": "soeg", "kald": 6})
    s = _ok(n.build_tool_hunt_nudge_surface(), "tool-hunt-nudge")
    assert s["active"] is True
    sig = s["signals"]
    assert (sig["notes"], sig["hits"], sig["misses"], sig["taken_up_share"]) == (2, 1, 1, 0.5)
    assert sig["per_kind"]["soeg"] == {"noter": 0, "ja": 1, "nej": 1}
    n._husk_udestaaende("runX", "grep", "soeg")
    try:
        assert n.build_tool_hunt_nudge_surface()["signals"]["outstanding_in_process"] == 1
    finally:
        n._UDESTAAENDE.pop("runX", None)


def test_tool_hunt_nudge_surface_reports_unreadable_bus(monkeypatch):
    from core.eventbus.bus import event_bus
    import core.services.tool_hunt_nudge as n

    def boom(*a, **k):
        raise RuntimeError("bus nede")

    monkeypatch.setattr(event_bus, "recent_by_family", boom)
    _inactive(n.build_tool_hunt_nudge_surface(), "tool-hunt-nudge", "bus nede")


# ── 5. tool_usage_store ──────────────────────────────────────────────────────

def test_tool_usage_store_surface(db):
    from core.services import tool_usage_store as u
    s = _inactive(u.build_tool_usage_store_surface(), "tool-usage-store", "findes ikke endnu")
    with db() as c:
        assert c.execute("SELECT 1 FROM sqlite_master WHERE name='tool_usage'").fetchone() is None, \
            "surface'en maa ikke oprette tabellen"
    assert s["signals"] == {}
    u.record_use("read_file")
    u.record_use("read_file", ok=False)
    u.record_use("bash")
    s = _ok(u.build_tool_usage_store_surface(), "tool-usage-store")
    sig = s["signals"]
    assert (sig["tracked_tools"], sig["total_calls"], sig["total_errors"], sig["error_rate"]) == (2, 3, 1, 0.3333)
    assert sig["top"][0] == {"tool": "read_file", "count": 2}
    assert sig["buckets"]["rare"] == 2 and sig["last_used_at"]
    u.record_use("bash")
    assert u.build_tool_usage_store_surface()["signals"]["total_calls"] == 4


# ── 7. agentic_tool_cache ────────────────────────────────────────────────────

def test_agentic_tool_cache_surface(monkeypatch):
    import core.services.agentic_tool_cache as a
    store: dict = {}
    monkeypatch.setattr(a, "load_json", lambda name, default: dict(store.get(name, default)))
    monkeypatch.setattr(a, "save_json", lambda name, data: store.__setitem__(name, dict(data)))
    s = _inactive(a.build_agentic_tool_cache_surface(), "agentic-tool-cache", "ingen poster")
    assert s["signals"] == {"records": 0}
    a.store_result(tool_name="todo_list", arguments={}, result_text="abc", status="ok")
    a.store_result(tool_name="find_files", arguments={"q": "x"}, result_text="hello", status="ok")
    a.store_result(tool_name="bash", arguments={}, result_text="ignoreres", status="ok")  # ikke cachebar
    s = _ok(a.build_agentic_tool_cache_surface(), "agentic-tool-cache")
    sig = s["signals"]
    assert (sig["records"], sig["fresh"], sig["stale"], sig["result_chars"]) == (2, 2, 0, 8)
    assert sig["per_tool"] == {"find_files": 1, "todo_list": 1}
    assert "hit_rate" in s and "ikke maalt" in s["hit_rate"]
    old = (datetime.now(UTC) - timedelta(seconds=a._MAX_AGE_SECONDS + 60)).isoformat()
    key = next(iter(store["agentic_tool_result_cache"]))
    store["agentic_tool_result_cache"][key]["stored_at"] = old
    assert a.build_agentic_tool_cache_surface()["signals"]["stale"] == 1


# ── 8. cache_telemetry ───────────────────────────────────────────────────────

def test_cache_telemetry_surface(monkeypatch, tmp_path):
    import core.services.cache_telemetry as ct
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    _inactive(ct.build_cache_telemetry_surface(), "cache-telemetry", "findes ikke")
    # (hit, miss) pr. kald — hit-raten skal vaegtes efter tokens, ikke gennemsnit af procenter
    ct.record_visible_cache(run_id="r", round_index=0, lane="visible", prefix_sha="aaa", cache_hit=0, cache_miss=1000)
    ct.record_visible_cache(run_id="r", round_index=1, lane="visible", prefix_sha="aaa", cache_hit=9000, cache_miss=0)
    s = _ok(ct.build_cache_telemetry_surface(), "cache-telemetry")
    assert s["active"] is True
    sig = s["signals"]
    assert (sig["calls_read"], sig["hit_tokens"], sig["miss_tokens"], sig["hit_pct"]) == (2, 9000, 1000, 90.0)
    assert sig["distinct_prefix_sha"] == 1 and sig["last_pct"] == 100.0 and sig["last_lane"] == "visible"
    ct.record_visible_cache(run_id="r", round_index=2, lane="visible", prefix_sha="bbb", cache_hit=0, cache_miss=1000)
    sig = ct.build_cache_telemetry_surface()["signals"]
    assert (sig["calls_read"], sig["distinct_prefix_sha"], sig["hit_pct"]) == (3, 2, 81.8)
    with (tmp_path / "logs" / "cache_telemetry.jsonl").open("a") as fh:
        fh.write("{afkortet\n")
    assert ct.build_cache_telemetry_surface()["signals"]["unreadable_lines"] == 1


# ── 10. agent_approval_gate ──────────────────────────────────────────────────

def _approval(connect, i, status, risk="write", note="", tool="write_file"):
    from core.runtime.db_agent_approvals import ensure_approval_tables
    with connect() as c:
        ensure_approval_tables(c)
        c.execute(
            "INSERT INTO agent_approvals (approval_id, owner_user_id, origin_session_id, agent_id, "
            "assignment_id, tool_name, args_digest, risk_class, status, created_at, expires_at, decision_note) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (f"ap{i}", "u", "s", "a", "as", tool, f"d{i}", risk, status,
             f"2026-11-0{i + 1}T00:00:00+00:00", "2026-12-01T00:00:00+00:00", note))
        c.commit()


def test_agent_approval_gate_surface(db):
    from core.services import agent_approval_gate as g
    s = _inactive(g.build_agent_approval_gate_surface(), "agent-approval-gate", "findes ikke endnu")
    assert s["signals"]["policy"]["always_approve_tools"] == len(g.ALWAYS_APPROVE)
    _approval(db, 0, "pending")
    _approval(db, 1, "denied", note="for risikabelt")
    _approval(db, 2, "denied", note="for risikabelt", tool="bash", risk="destructive")
    _approval(db, 3, "approved")
    s = _ok(g.build_agent_approval_gate_surface(), "agent-approval-gate")
    sig = s["signals"]
    assert s["active"] is True and sig["total"] == 4
    assert sig["by_status"] == {"pending": 1, "denied": 2, "approved": 1}
    assert sig["by_risk_class"] == {"write": 3, "destructive": 1}
    assert sig["denied_reasons"] == [{"reason": "for risikabelt", "count": 2}]
    assert sig["oldest_pending_at"] == "2026-11-01T00:00:00+00:00"
    _approval(db, 4, "denied")
    assert g.build_agent_approval_gate_surface()["signals"]["denied_reasons"][1] == \
        {"reason": "(ingen begrundelse)", "count": 1}


# ── 11. task_worker ──────────────────────────────────────────────────────────

def test_task_worker_surface(db):
    from core.runtime.db_runtime_tasks import ensure_runtime_tasks_tables
    from core.services import task_worker as w

    def add(i, kind, status, reason=""):
        with db() as c:
            ensure_runtime_tasks_tables(c)
            c.execute("INSERT INTO runtime_tasks (task_id, kind, origin, status, goal, blocked_reason, "
                      "created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
                      (f"t{i}", kind, "test", status, "g", reason, f"2026-11-0{i}T00:00:00", f"2026-11-0{i}T01:00:00"))
            c.commit()

    s = _inactive(w.build_task_worker_surface(), "task-worker", "findes ikke endnu")
    assert s["signals"] == {}
    add(1, "generic", "queued")
    add(2, "unknown-kind", "queued")           # ikke claimbar
    add(3, "heartbeat-followup", "blocked", w._FOLLOWUP_BLOCKED)
    add(4, "generic", "running")
    s = _ok(w.build_task_worker_surface(), "task-worker")
    sig = s["signals"]
    assert s["active"] is True and sig["total"] == 4
    assert sig["by_status"] == {"queued": 2, "blocked": 1, "running": 1}
    assert (sig["claimable_queued"], sig["followup_blocked"]) == (1, 1)
    assert sig["blocked_reasons"] == [{"reason": w._FOLLOWUP_BLOCKED[:160], "count": 1}]
    assert sig["oldest_queued_at"] == "2026-11-01T00:00:00"
    assert sig["oldest_running_updated_at"] == "2026-11-04T01:00:00"
    claimed = w.claim_next_task()  # den rigtige indgang flytter en task -> surface'en skal se det
    assert claimed is not None
    assert w.build_task_worker_surface()["signals"]["claimable_queued"] == 0


# ── 12. causal_inference_daemon ──────────────────────────────────────────────

def test_causal_inference_daemon_surface(db):
    from core.runtime.db_schema import _ensure_causal_edges_table
    import core.services.causal_inference_daemon as d
    s = _inactive(d.build_causal_inference_daemon_surface(), "causal-inference-daemon", "findes ikke endnu")
    assert s["signals"]["daemon"]["cadence_seconds"] == d._CADENCE_SECONDS
    with db() as c:
        _ensure_causal_edges_table(c)
        c.commit()
    _inactive(d.build_causal_inference_daemon_surface(), "causal-inference-daemon", "tom")
    assert d._record_edge(child=2, parent=1, edge_kind="triggered", confidence=0.5,
                          source="inferred-kind", reasoning="r") == "created"
    assert d._record_edge(child=3, parent=1, edge_kind="triggered", confidence=0.9,
                          source="explicit", reasoning="r") == "created"
    s = _ok(d.build_causal_inference_daemon_surface(), "causal-inference-daemon")
    sig = s["signals"]
    assert s["active"] is True and sig["edges"] == 2 and sig["avg_confidence"] == 0.7
    assert {x["source"]: x["count"] for x in sig["by_source"]} == {"inferred-kind": 1, "explicit": 1}
    assert sig["by_edge_kind"] == {"triggered": 2}
    assert d._record_edge(child=2, parent=1, edge_kind="triggered", confidence=0.8,
                          source="inferred-id", reasoning="r") == "upgraded"  # opgradering aendrer snit, ikke antal
    sig = d.build_causal_inference_daemon_surface()["signals"]
    assert sig["edges"] == 2 and sig["avg_confidence"] == 0.85
