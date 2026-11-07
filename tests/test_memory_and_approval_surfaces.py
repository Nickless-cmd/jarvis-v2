"""Surfaces for hukommelses- og godkendelses-laget (dark-edges batch 2).

Samme regel som batch 1: (1) tom/manglende kilde giver active=False med en
AERLIG aarsag, (2) data skrives gennem kildens EGEN skriver, (3) surface'en
laeses og tallene er de skrevne, (4) mere data aendrer tallet. En surface der
altid svarer det samme kan ikke bestaa (4).
"""
from __future__ import annotations

import queue
import sqlite3
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest


# ── faelles hjaelpere ────────────────────────────────────────────────────────

@pytest.fixture
def db(monkeypatch, tmp_path):
    """Frisk, TOM sqlite-DB. Pool'en genforbinder naar DB_PATH skifter."""
    import core.runtime.db_core as dbcore
    monkeypatch.setattr(dbcore, "DB_PATH", tmp_path / "jarvis.db")
    return dbcore.connect


@pytest.fixture
def state_dir(monkeypatch, tmp_path):
    import core.runtime.state_store as ss
    monkeypatch.setattr(ss, "_STATE_DIR", tmp_path / "state")
    (tmp_path / "state").mkdir()
    return tmp_path / "state"


@pytest.fixture
def bus(monkeypatch):
    """In-memory eventbus: publish() skriver, recent_by_family() laeser det samme."""
    from core.eventbus.bus import event_bus
    log: list[dict] = []

    def publish(kind, payload=None, **_):
        log.insert(0, {"kind": kind, "payload": dict(payload or {}),
                       "created_at": f"2026-11-07T10:00:{len(log):02d}+00:00"})

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


# ── 1. memory_graph ──────────────────────────────────────────────────────────

def test_memory_graph_surface(db):
    import core.services.memory_graph as mg
    _inactive(mg.build_memory_graph_surface(), "memory-graph", "findes ikke endnu")
    with db() as c:  # surface'en maa ikke have oprettet tabellerne
        assert c.execute("SELECT name FROM sqlite_master WHERE name LIKE 'memory_%'").fetchall() == []
    mg._ensure_tables()
    _inactive(mg.build_memory_graph_surface(), "memory-graph", "er tom")
    assert mg.record_triple("Bjorn", "bor_i", "Aarhus", src_kind="person", dst_kind="sted")
    s = _ok(mg.build_memory_graph_surface(), "memory-graph")
    assert s["active"] is True
    assert s["signals"]["entities"] == 2 and s["signals"]["edges"] == 1
    assert s["signals"]["kinds"] == {"person": 1, "sted": 1}
    assert s["signals"]["top_relations"] == {"bor_i": 1}
    assert mg.record_triple("Bjorn", "ejer", "Jarvis", src_kind="person", dst_kind="system")
    s = mg.build_memory_graph_surface()
    assert (s["signals"]["entities"], s["signals"]["edges"]) == (3, 2)
    assert s["signals"]["top_entities"][0] == {"name": "Bjorn", "mentions": 2}


# ── 2. memory_hygiene ────────────────────────────────────────────────────────

def test_memory_hygiene_surface(db, monkeypatch, tmp_path):
    import core.services.memory_hygiene as mh
    monkeypatch.setattr(mh, "REPORT_DIR", tmp_path / "reports")
    _inactive(mh.build_memory_hygiene_surface(), "memory-hygiene", "findes endnu")
    md = tmp_path / "MEMORY.md"
    md.write_text("## Alfa 2026-01-01\ntekst\n## Beta status\ntekst\n## Beta status\nmere\n", encoding="utf-8")
    mh.audit_workspace("ws1", path=md, publish_inbox=False)
    s = _ok(mh.build_memory_hygiene_surface(), "memory-hygiene")
    assert s["active"] is True
    assert s["signals"]["snapshots"] == 1 and s["signals"]["workspaces_audited"] == 1
    ws = s["signals"]["latest_by_workspace"]["ws1"]
    assert ws["sections"] == 3 and ws["duplicate_groups"] == 1 and ws["dated"] == 1
    assert s["signals"]["soft_cap_breached"] == []
    assert mh.record_section_selections("ws1", ["Alfa", "Beta"]) == 2
    mh.record_section_selections("ws1", ["Alfa"])
    md.write_text(md.read_text(encoding="utf-8") + "## Gamma\nx\n", encoding="utf-8")
    mh.audit_workspace("ws1", path=md, publish_inbox=False)
    s = mh.build_memory_hygiene_surface()
    assert s["signals"]["snapshots"] == 2  # to snapshots, men kun SENESTE pr. workspace vises
    assert s["signals"]["latest_by_workspace"]["ws1"]["sections"] == 4
    assert s["signals"]["usage"]["tracked_sections"] == 2 and s["signals"]["usage"]["selections"] == 3
    monkeypatch.setattr(mh, "SOFT_CAP_SECTIONS", 4)
    assert mh.build_memory_hygiene_surface()["signals"]["soft_cap_breached"] == ["ws1"]


# ── 3. memory_recall_engine ──────────────────────────────────────────────────

def test_memory_recall_engine_surface(bus):
    import core.services.memory_recall_engine as mre
    _inactive(mre.build_memory_recall_engine_surface(), "memory-recall-engine", "ingen memory.recall")
    mre._observe_recall_quality([{"source": "workspace", "multi_signal_score": 0.8},
                                 {"source": "private_brain", "multi_signal_score": 0.4}],
                                ["workspace", "private_brain"])
    s = _ok(mre.build_memory_recall_engine_surface(), "memory-recall-engine")
    assert s["active"] is True
    assert s["signals"]["recalls"] == 1 and s["signals"]["empty_recalls"] == 0
    assert s["signals"]["last_result_count"] == 2 and s["signals"]["last_top_score"] == 0.8
    assert s["signals"]["mean_private_brain_share"] == 0.5
    assert s["signals"]["sources"] == {"private_brain": 1, "workspace": 1}
    mre._observe_recall_quality([], ["workspace"])
    s = mre.build_memory_recall_engine_surface()
    assert s["signals"]["recalls"] == 2 and s["signals"]["empty_recalls"] == 1
    assert s["signals"]["mean_result_count"] == 1.0
    assert s["signals"]["last_result_count"] == 0


# ── 4. memory_resurfacing ────────────────────────────────────────────────────

def test_memory_resurfacing_surface(db):
    import core.services.memory_resurfacing as mr
    _inactive(mr.build_memory_resurfacing_surface(), "memory-resurfacing", "findes ikke endnu")
    mr._ensure_table()
    _inactive(mr.build_memory_resurfacing_surface(), "memory-resurfacing", "er tom")
    mr._log_resurfacing("Gammel beslutning", "heartbeat")
    s = _ok(mr.build_memory_resurfacing_surface(), "memory-resurfacing")
    assert s["active"] is True
    assert s["signals"]["resurfaced_total"] == 1 and s["signals"]["distinct_headings"] == 1
    assert s["signals"]["by_trigger"] == {"heartbeat": 1}
    mr._log_resurfacing("Gammel beslutning", "manual")
    mr._log_resurfacing("Anden ting", "heartbeat")
    s = mr.build_memory_resurfacing_surface()
    assert s["signals"]["resurfaced_total"] == 3 and s["signals"]["distinct_headings"] == 2
    assert s["signals"]["by_trigger"] == {"heartbeat": 2, "manual": 1}
    assert s["signals"]["recent"][0]["heading"] == "Anden ting"


# ── 6. cross_agent_memory ────────────────────────────────────────────────────

def test_cross_agent_memory_surface(state_dir):
    import core.services.cross_agent_memory as cam
    from core.runtime.state_store import save_json
    _inactive(cam.build_cross_agent_memory_surface(), "cross-agent-memory", "findes ikke")
    save_json("agent_observations", [])
    _inactive(cam.build_cross_agent_memory_surface(), "cross-agent-memory", "er tom")
    save_json("agent_observations", {"ikke": "en liste"})
    _inactive(cam.build_cross_agent_memory_surface(), "cross-agent-memory", "uventet type")
    now = datetime.now(UTC)
    old = (now - timedelta(days=40)).isoformat()
    save_json("agent_observations", [
        {"obs_id": "a", "user_id": "u1", "role": "coder", "recorded_at": now.isoformat()},
        {"obs_id": "b", "user_id": "u1", "role": "coder", "recorded_at": old, "stale": True},
    ])
    s = _ok(cam.build_cross_agent_memory_surface(), "cross-agent-memory")
    assert s["active"] is True
    assert s["signals"]["observations"] == 2 and s["signals"]["fresh_in_lookback"] == 1
    assert s["signals"]["marked_stale"] == 1 and s["signals"]["roles"] == {"coder": 2}
    assert "preview" not in str(s) and "compressed_text" not in str(s), "indhold maa ikke laekke"
    save_json("agent_observations", [
        {"obs_id": "a", "user_id": "u1", "role": "coder", "recorded_at": now.isoformat()},
        {"obs_id": "c", "user_id": "u2", "role": "tester", "recorded_at": now.isoformat()},
    ])
    s = cam.build_cross_agent_memory_surface()
    assert s["signals"]["users"] == 2 and s["signals"]["roles"] == {"coder": 1, "tester": 1}
    assert s["signals"]["fresh_in_lookback"] == 2 and s["signals"]["marked_stale"] == 0


# ── 7. end_of_run_memory_consolidation ───────────────────────────────────────

def test_end_of_run_memory_consolidation_surface(bus):
    import core.services.end_of_run_memory_consolidation as eor
    _inactive(eor.build_end_of_run_memory_consolidation_surface(),
              "end-of-run-memory-consolidation", "ingen konsolidering")
    # Den rigtige indgang: heartbeat-arbejde konsolideres ikke, men melder det.
    eor.consolidate_run_memory(session_id="s1", run_id="r1", human_user_message=False)
    s = _ok(eor.build_end_of_run_memory_consolidation_surface(), "end-of-run-memory-consolidation")
    assert s["active"] is True
    assert s["signals"]["runs"] == 1 and s["signals"]["consolidated"] == 0
    assert s["signals"]["skipped"] == 1 and len(s["signals"]["skipped_reasons"]) == 1
    eor._publish_consolidation_event(
        {"consolidated": True, "candidate_count": 3, "memory_updated": True,
         "auto_applied_memory_count": 2, "rule_proposals": 1},
        session_id="s2", run_id="r2")
    s = eor.build_end_of_run_memory_consolidation_surface()
    assert s["signals"]["runs"] == 2 and s["signals"]["consolidated"] == 1
    assert s["signals"]["candidates_proposed"] == 3 and s["signals"]["auto_applied_memory"] == 2
    assert s["signals"]["memory_updated"] == 1 and s["signals"]["rule_proposals"] == 1
    bus.insert(0, {"kind": "memory.consolidation_model_fallback", "payload": {}, "created_at": "x"})
    assert eor.build_end_of_run_memory_consolidation_surface()["signals"]["model_fallbacks"] == 1


# ── 8. approval_runtime ──────────────────────────────────────────────────────

def test_approval_runtime_surface(state_dir):
    import core.services.approval_runtime as ar
    import core.services.visible_runs as vr
    _inactive(ar.build_approval_runtime_surface(), "approval-runtime", "ingen ventende")
    run = SimpleNamespace(run_id="r1", session_id="s1")
    fresh = ar.build_request(tool_name="bash", arguments={"cmd": "ls"}, result={}, run=run)
    old = {**fresh, "tool_name": "write_file",
           "created_at": (datetime.now(UTC) - timedelta(days=3)).isoformat()}
    vr._save_approvals_state(vr._APPROVALS_STATE_KEY, {"a-1": fresh})
    s = _ok(ar.build_approval_runtime_surface(), "approval-runtime")
    assert s["active"] is True
    assert s["signals"]["pending"] == 1 and s["signals"]["expired_not_swept"] == 0
    assert s["signals"]["by_tool"] == {"bash": 1}
    vr._save_approvals_state(vr._APPROVALS_STATE_KEY, {"a-1": fresh, "a-2": old})
    s = ar.build_approval_runtime_surface()
    assert s["signals"]["pending"] == 2 and s["signals"]["expired_ids"] == ["a-2"]
    assert s["signals"]["by_tool"] == {"bash": 1, "write_file": 1}
    ar.sweep_expired()  # den rigtige fejning fjerner kortet, og surface'en foelger med
    s = ar.build_approval_runtime_surface()
    assert s["signals"]["pending"] == 1 and s["signals"]["expired_not_swept"] == 0


# ── 9. approval_outbox ───────────────────────────────────────────────────────

def test_approval_outbox_surface(db):
    import core.services.approval_outbox as ob
    _inactive(ob.build_approval_outbox_surface(), "approval-outbox", "findes ikke endnu")
    with db() as c:
        ob.ensure_approval_outbox_table(c)
    _inactive(ob.build_approval_outbox_surface(), "approval-outbox", "er tom")
    with db() as c:
        ob.enqueue_approval_notification(c, request_id="r1", user_id="u", envelope={"x": 1})
        ob.enqueue_approval_notification(c, request_id="r2", user_id="u", envelope={"x": 2})
    s = _ok(ob.build_approval_outbox_surface(), "approval-outbox")
    assert s["active"] is True
    assert s["signals"]["by_state"] == {"pending": 2} and s["signals"]["retrying"] == 0
    ob.dispatch_pending_approval_notifications(deliver=lambda uid, env: env["x"] == 1)
    s = ob.build_approval_outbox_surface()
    assert s["signals"]["by_state"] == {"delivered": 1, "pending": 1}
    assert s["signals"]["retrying"] == 1 and s["signals"]["max_attempts_pending"] == 1
    assert s["signals"]["pending_errors"] == [{"error": "delivery returned false", "count": 1}]
    assert s["signals"]["last_delivered_at"]


# ── 10. approval_expiry_daemon ───────────────────────────────────────────────

def test_approval_expiry_daemon_surface(db, bus):
    import core.runtime.db_approval_bridge as bridge
    import core.services.approval_expiry_daemon as ed
    ed._nulstil_for_tests()
    _inactive(ed.build_approval_expiry_daemon_surface(), "approval-expiry-daemon", "ikke tikket")
    t0 = datetime.now(UTC)
    ed.tick_approval_expiry_daemon(now=t0)
    s = _ok(ed.build_approval_expiry_daemon_surface(), "approval-expiry-daemon")
    assert s["active"] is True
    assert s["signals"]["tick"]["ticked_in_this_process"] is True
    assert s["signals"]["tick"]["last_result"]["udloebet"] == 0
    assert s["signals"]["expired_total"] == 0
    bridge.request("ap-1", tool_name="bash", arguments={}, ttl_s=1)
    bridge.request("ap-2", tool_name="bash", arguments={"a": 1}, ttl_s=1)
    ed.tick_approval_expiry_daemon(now=t0 + timedelta(minutes=10))
    s = ed.build_approval_expiry_daemon_surface()
    assert s["signals"]["tick"]["last_result"]["udloebet"] == 2
    assert s["signals"]["expired_events"] == 1 and s["signals"]["expired_total"] == 2
    assert s["signals"]["last_expired_at"]
    ed._nulstil_for_tests()


def test_approval_expiry_daemon_surface_reads_events_without_local_tick(bus):
    import core.services.approval_expiry_daemon as ed
    ed._nulstil_for_tests()
    bus.insert(0, {"kind": "approvals.expired", "payload": {"count": 4}, "created_at": "2026-11-07T09:00:00+00:00"})
    s = _ok(ed.build_approval_expiry_daemon_surface(), "approval-expiry-daemon")
    assert s["active"] is True and s["signals"]["expired_total"] == 4
    assert s["signals"]["tick"]["ticked_in_this_process"] is False


# ── 12. agent_approval_notify ────────────────────────────────────────────────

def test_agent_approval_notify_surface(isolated_runtime):
    import core.runtime.db_agent_approvals as appr
    import core.runtime.db_agent_contract as c
    import core.services.agent_approval_notify as nt
    from core.runtime.db_agent_runtime import create_agent_registry_entry

    def req(name, session, cmd):
        create_agent_registry_entry(agent_id=name, role="executor", goal="g")
        c.bind_agent_owner(agent_id=name, owner_user_id="bjorn", owner_session_id=session)
        acc = c.accept_assignment(agent_id=name, owner_user_id="bjorn", origin_session_id=session,
                                  goal="g", parent_agent_id="jarvis", parent_run_id="p")
        return appr.request(owner_user_id="bjorn", origin_session_id=session,
                            assignment_id=acc["assignment_id"], tool_name="bash",
                            arguments={"command": cmd}, run_id=acc["run_id"],
                            now=datetime.now(UTC) - timedelta(minutes=5))

    _inactive(nt.build_agent_approval_notify_surface(), "agent-approval-notify", "findes ikke endnu")
    a1 = req("a1", "s1", "rm -rf build")
    s = _ok(nt.build_agent_approval_notify_surface(), "agent-approval-notify")
    assert s["active"] is True
    assert s["signals"]["pending"] == 1 and s["signals"]["pending_with_wake_staged"] == 0
    assert s["signals"]["unstaged_overdue"] == 1  # praecis det ensure_wakes ville samle op
    assert nt.stage(a1)  # den rigtige indgang planlaegger vaekningen
    s = nt.build_agent_approval_notify_surface()
    assert s["signals"]["pending_with_wake_staged"] == 1 and s["signals"]["unstaged_overdue"] == 0
    req("a2", "s2", "ls")
    s = nt.build_agent_approval_notify_surface()
    assert s["signals"]["total"] == 2 and s["signals"]["unstaged_overdue"] == 1
    assert s["signals"]["by_status"] == {"pending": 2}
