"""Leverance C, hul 4: retention-sweep for artefakter og hukommelse (spec 12.1) - rigtig sqlite, rigtige filer."""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta

import pytest

O, S = "bjorn", "s1"
T0 = datetime.now(UTC)


def at(days: float) -> datetime:
    return T0 + timedelta(days=days)


class _AutoCommit:
    def __init__(self, conn):
        self._c = conn

    def execute(self, sql, params=()):
        cur = self._c.execute(sql, params)
        if not sql.lstrip().upper().startswith("SELECT"):
            self._c.commit()
        return cur

    def commit(self):
        return None


@pytest.fixture
def rt(isolated_runtime, monkeypatch):
    import core.runtime.db_agent_artifacts as art
    import core.runtime.db_agent_contract as c
    import core.runtime.db_agent_memory as mem
    import core.services.agent_retention as R
    from core.runtime.db_agent_runtime import create_agent_registry_entry
    from core.services import in_flight_runs as ifr

    ifr._mutate(lambda r: r.clear())
    monkeypatch.setattr(R, "_last_run", 0.0)

    class H:
        c_, art_, mem_, R_ = c, art, mem, R

        def conn(self):
            """En forbindelse der committer hver skrivning straks: ``connect()`` ruller en aaben transaktion
            tilbage naar den kaldes igen paa traaden, saa ``conn().execute(..); conn().commit()`` ville
            tabe skrivningen."""
            return _AutoCommit(c._conn())

        def agent(self, name, owner=O, session=S):
            create_agent_registry_entry(agent_id=name, role="researcher", goal="g")
            if owner:
                c.bind_agent_owner(agent_id=name, owner_user_id=owner, owner_session_id=session)

        def case(self, name="a1", *, status="completed", delivery="acknowledged", files=("result.json", "final.txt"),
                 owner=O, terminal=True):
            """Et assignment med artefakter. ``delivery`` = hvor langt terminalbeskeden er kommet."""
            self.agent(name, owner=owner)
            acc = c.accept_assignment(agent_id=name, owner_user_id=owner, origin_session_id=S, goal="g",
                                      parent_agent_id="jarvis", parent_run_id="pr")
            for f in files:
                art.write_artifact(agent_id=name, run_id=acc["run_id"], name=f, data=f"data-{f}",
                                   assignment_id=acc["assignment_id"], owner_user_id=owner)
            if terminal:
                res = c.commit_terminal_outcome(assignment_id=acc["assignment_id"], status=status, summary="s")
                for step in c.DELIVERY_STATES[1:c.DELIVERY_STATES.index(delivery) + 1]:
                    c.advance_delivery(message_id=res["message"]["message_id"], owner_user_id=owner, to_status=step)
            return acc

        def paths(self, acc):
            return [r["path"] for r in self.conn().execute(
                "SELECT path FROM agent_artifacts WHERE run_id=? ORDER BY name", (acc["run_id"],))]

        def status(self, acc):
            return {r["name"]: (r["status"], r["size"]) for r in self.conn().execute(
                "SELECT name, status, size FROM agent_artifacts WHERE run_id=?", (acc["run_id"],))}

        def sweep(self, days):
            return R.sweep_artifacts(now=at(days))

        def insert(self, table, **cols):
            keys = ",".join(cols)
            self.conn().execute(f"INSERT INTO {table} ({keys}) VALUES ({','.join('?' * len(cols))})",
                                tuple(cols.values()))
            self.conn().commit()

    yield H()
    ifr._mutate(lambda r: r.clear())


# --- tidsreglerne ----------------------------------------------------------------------------------------------------------

def test_a_processed_success_is_kept_30_days_then_becomes_a_tombstone(rt):
    acc = rt.case()
    files = rt.paths(acc)
    assert all(os.path.exists(f) for f in files)
    kept = rt.sweep(29.9)
    assert kept == {"expired": [], "protected": {}, "attention": [], "refused": []}
    assert all(os.path.exists(f) for f in files)
    out = rt.sweep(30.5)
    assert sorted(out["expired"]) == sorted([f"{acc['run_id']}/final.txt", f"{acc['run_id']}/result.json"])
    assert out["protected"] == {} and out["attention"] == [] and out["refused"] == []
    assert not any(os.path.exists(f) for f in files)
    assert not os.path.exists(os.path.dirname(files[0]))                     # tomme mapper ryddes
    assert rt.status(acc) == {"final.txt": ("expired", 0), "result.json": ("expired", 0)}
    got = rt.art_.read_artifact(owner_user_id=O, ref=f"{acc['run_id']}/result.json")
    assert got["status"] == "EXPIRED" and "content" not in got


@pytest.mark.parametrize("status", ["failed", "cancelled", "timed_out"])
def test_failed_stopped_and_timed_out_results_are_kept_90_days(rt, status):
    acc = rt.case(status=status)
    assert rt.sweep(89.5)["expired"] == [] and all(os.path.exists(f) for f in rt.paths(acc))
    assert len(rt.sweep(90.5)["expired"]) == 2 and not any(os.path.exists(f) for f in rt.paths(acc))


def test_the_clock_runs_from_the_acknowledgement_not_from_the_terminal_time(rt):
    acc = rt.case(delivery="delivered")
    rt.conn().execute("UPDATE agent_assignments SET terminal_at=? WHERE assignment_id=?",
                      ((T0 - timedelta(days=100)).isoformat().replace("+00:00", "Z"), acc["assignment_id"]))
    rt.conn().commit()
    msg = rt.conn().execute("SELECT message_id FROM agent_result_outbox").fetchone()["message_id"]
    rt.c_.advance_delivery(message_id=msg, owner_user_id=O, to_status="claimed_by_model_step")
    rt.c_.advance_delivery(message_id=msg, owner_user_id=O, to_status="acknowledged")     # kvitteret NU
    assert rt.sweep(10)["expired"] == []                                    # terminal for 110 dage siden, kvitteret for 10
    assert len(rt.sweep(31)["expired"]) == 2


# --- hvad der ALDRIG slettes --------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("delivery", ["accepted", "delivered", "claimed_by_model_step"])
def test_an_unprocessed_terminal_result_is_never_deleted_and_is_reported_after_90_days(rt, delivery):
    acc = rt.case(delivery=delivery, status="failed")
    files = rt.paths(acc)
    early = rt.sweep(60)
    assert early["expired"] == [] and early["protected"] == {"unprocessed": 2} and early["attention"] == []
    late = rt.sweep(5000)
    assert late["expired"] == [] and late["attention"] == [acc["assignment_id"]]
    assert late["protected"] == {"unprocessed": 2}
    assert all(os.path.exists(f) for f in files)
    assert rt.status(acc) == {"final.txt": ("complete", 14), "result.json": ("complete", 16)}


def test_a_terminal_assignment_without_any_receipt_record_is_protected(rt):
    acc = rt.case()
    rt.conn().execute("DELETE FROM agent_result_outbox")
    rt.conn().commit()
    out = rt.sweep(5000)
    assert out["expired"] == [] and out["protected"] == {"no_receipt": 2} and all(os.path.exists(f) for f in rt.paths(acc))


def test_a_non_terminal_assignment_is_protected(rt):
    acc = rt.case(terminal=False)
    out = rt.sweep(5000)
    assert out["expired"] == [] and out["protected"] == {"not_terminal": 2} and all(os.path.exists(f) for f in rt.paths(acc))


@pytest.mark.parametrize("status,expect_protected", [("pending", True), ("approved", True), ("consumed", False),
                                                      ("denied", False), ("expired", False), ("cancelled", False)])
def test_an_open_approval_protects_the_artifacts_and_a_settled_one_does_not(rt, status, expect_protected):
    acc = rt.case()
    rt.insert("agent_approvals", approval_id="ap1", owner_user_id=O, origin_session_id=S, agent_id="a1",
              assignment_id=acc["assignment_id"], tool_name="wt_bash", args_digest="d", status=status,
              created_at="2026-01-01T00:00:00Z", expires_at="2026-01-02T00:00:00Z")
    out = rt.sweep(60)
    if expect_protected:
        assert out["expired"] == [] and out["protected"] == {"open_approval": 2}
    else:
        assert len(out["expired"]) == 2 and out["protected"] == {}


def test_a_parked_checkpoint_protects_and_a_resumed_one_does_not(rt):
    acc = rt.case()
    rt.insert("agent_checkpoints", checkpoint_id="cp1", assignment_id=acc["assignment_id"], agent_id="a1",
              owner_user_id=O, run_id=acc["run_id"], approval_id="ap1", payload_json="{}",
              created_at="2026-01-01T00:00:00Z", status="parked")
    assert rt.sweep(60)["protected"] == {"parked": 2}
    rt.conn().execute("UPDATE agent_checkpoints SET status='resumed'")
    rt.conn().commit()
    assert len(rt.sweep(60)["expired"]) == 2


def test_an_outcome_unknown_run_or_an_open_tool_call_protects(rt):
    acc = rt.case()
    rt.conn().execute("UPDATE agent_runs SET status='outcome_unknown' WHERE run_id=?", (acc["run_id"],))
    rt.conn().commit()
    out = rt.sweep(500)
    assert out["expired"] == [] and out["protected"] == {"outcome_unknown": 2}
    rt.conn().execute("UPDATE agent_runs SET status='completed' WHERE run_id=?", (acc["run_id"],))
    rt.insert("agent_tool_calls", tool_call_id="tc1", run_id=acc["run_id"], agent_id="a1", tool_name="wt_bash",
              started_at="2026-01-01T00:00:00Z", finished_at="", created_at="2026-01-01T00:00:00Z")
    assert rt.sweep(500)["protected"] == {"outcome_unknown": 2}
    rt.conn().execute("UPDATE agent_tool_calls SET finished_at='2026-01-01T00:00:01Z'")
    rt.conn().commit()
    assert len(rt.sweep(500)["expired"]) == 2


def test_an_active_wait_contract_on_the_assignment_protects_until_it_is_settled(rt):
    acc = rt.case()
    rt.insert("agent_wait_contracts", contract_id="w1", owner_user_id=O, origin_session_id=S, condition="all_terminal",
              assignment_ids_json=json.dumps([acc["assignment_id"]]), status="registered",
              created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z")
    assert rt.sweep(60)["protected"] == {"wait_contract": 2}
    rt.conn().execute("UPDATE agent_wait_contracts SET status='fired'")
    rt.conn().commit()
    assert len(rt.sweep(60)["expired"]) == 2


@pytest.mark.parametrize("owner_value", ["legacy_unscoped", ""])
def test_legacy_unscoped_or_ownerless_artifacts_are_never_touched(rt, owner_value):
    acc = rt.case()
    rt.conn().execute("UPDATE agent_artifacts SET owner_user_id=?", (owner_value,))
    rt.conn().commit()
    out = rt.sweep(5000)
    assert out["expired"] == [] and out["protected"] == {"legacy_or_unowned": 2} and all(os.path.exists(f) for f in rt.paths(acc))


def test_artifacts_of_an_unknown_assignment_are_left_alone(rt):
    acc = rt.case()
    rt.conn().execute("UPDATE agent_artifacts SET assignment_id='findes-ikke'")
    rt.conn().commit()
    out = rt.sweep(5000)
    assert out["expired"] == [] and out["protected"] == {"no_assignment": 2} and all(os.path.exists(f) for f in rt.paths(acc))


# --- worktree-artefakter foelger worktree'et ------------------------------------------------------------------------------------

def _worktree(rt, acc, status, closed_at=""):
    rt.insert("agent_worktrees", worktree_id="wt1", assignment_id=acc["assignment_id"], agent_id="a1", owner_user_id=O,
              repo_path="/r", base_commit="b", branch="agent/x", path="/p", status=status, closed_at=closed_at,
              created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z")


@pytest.mark.parametrize("wstatus", ["reserved", "creating", "active", "retained", "decided", "unknown"])
def test_diff_changes_and_bundle_are_kept_while_the_worktree_is_held_but_other_artifacts_expire(rt, wstatus):
    acc = rt.case(files=("result.json", "diff.patch", "changes.json", "worktree.bundle"))
    _worktree(rt, acc, wstatus)
    out = rt.sweep(100)
    assert out["expired"] == [f"{acc['run_id']}/result.json"] and out["protected"] == {"worktree_held": 3}
    assert rt.status(acc) == {"result.json": ("expired", 0), "diff.patch": ("complete", 15),
                              "changes.json": ("complete", 17), "worktree.bundle": ("complete", 20)}


def test_after_the_worktree_is_archived_its_artifacts_follow_90_days_from_the_archive(rt):
    acc = rt.case(files=("diff.patch", "worktree.bundle"))
    _worktree(rt, acc, "archived", closed_at=_iso(at(40)))
    assert rt.sweep(129)["expired"] == []                                   # 89 dage efter arkivering
    assert len(rt.sweep(131)["expired"]) == 2


def test_an_archived_worktree_without_a_close_time_keeps_its_artifacts(rt):
    acc = rt.case(files=("diff.patch",))
    _worktree(rt, acc, "archived", closed_at="")
    assert rt.sweep(5000)["protected"] == {"worktree_held": 1}


@pytest.mark.parametrize("wstatus", ["removed", "failed"])
def test_a_removed_or_failed_worktree_releases_its_artifacts_to_the_normal_clock(rt, wstatus):
    acc = rt.case(files=("diff.patch",))
    _worktree(rt, acc, wstatus)
    assert len(rt.sweep(31)["expired"]) == 1


def _iso(dt):
    return dt.isoformat().replace("+00:00", "Z")


# --- robusthed ------------------------------------------------------------------------------------------------------------------

def test_a_db_path_outside_the_artifact_root_is_refused_and_the_file_is_untouched(rt, tmp_path):
    acc = rt.case(files=("result.json",))
    victim = tmp_path / "vigtig.txt"
    victim.write_text("maa ikke slettes")
    rt.conn().execute("UPDATE agent_artifacts SET path=?", (str(victim),))
    rt.conn().commit()
    out = rt.sweep(100)
    assert out["expired"] == [] and out["refused"] == [f"{acc['run_id']}/result.json"] and victim.read_text() == "maa ikke slettes"
    assert rt.status(acc) == {"result.json": ("complete", 16)}


def test_a_crash_between_file_removal_and_the_db_update_is_healed_by_the_next_round(rt):
    acc = rt.case(files=("result.json",))
    os.unlink(rt.paths(acc)[0])                                             # filen er vaek, posten staar stadig 'complete'
    assert rt.sweep(31)["expired"] == [f"{acc['run_id']}/result.json"]
    assert rt.status(acc) == {"result.json": ("expired", 0)}
    rt.conn().execute("UPDATE agent_artifacts SET status='missing'")        # reconcile naaede at kalde den 'missing'
    rt.conn().commit()
    assert rt.sweep(31)["expired"] == [f"{acc['run_id']}/result.json"]


def test_a_tombstone_whose_file_is_still_on_disk_is_cleaned_up(rt):
    acc = rt.case(files=("result.json",))
    path = rt.paths(acc)[0]
    rt.sweep(31)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write("efterladt")
    rt.sweep(32)
    assert not os.path.exists(path)


def test_the_sweep_is_idempotent_and_leaves_other_runs_alone(rt):
    a = rt.case("a1")
    b = rt.case("a2", delivery="delivered")
    first = rt.sweep(31)
    assert len(first["expired"]) == 2 and first["protected"] == {"unprocessed": 2}
    assert rt.sweep(31) == {"expired": [], "protected": {"unprocessed": 2}, "attention": [], "refused": []}
    assert rt.status(b) == {"final.txt": ("complete", 14), "result.json": ("complete", 16)}
    assert rt.status(a) == {"final.txt": ("expired", 0), "result.json": ("expired", 0)}


def test_an_expired_artifact_no_longer_counts_against_the_run_quota(rt):
    acc = rt.case()
    assert rt.art_.run_bytes(acc["run_id"]) == 30
    rt.sweep(31)
    assert rt.art_.run_bytes(acc["run_id"]) == 0


def test_reconcile_does_not_resurrect_a_tombstone_as_missing(rt):
    acc = rt.case()
    rt.sweep(31)
    out = rt.art_.reconcile()
    assert out["missing"] == [] and out["corrupt"] == [] and rt.status(acc)["result.json"][0] == "expired"


# --- tombstone i hukommelsen ------------------------------------------------------------------------------------------------------

def test_an_expired_evidence_reference_is_shown_as_a_tombstone_in_the_agents_recall(rt):
    acc = rt.case("a1", status="completed")
    rt.mem_.project_summary(acc["assignment_id"])
    rt.conn().execute("UPDATE agent_memory_summaries SET evidence_refs_json=?",
                      (json.dumps([f"{acc['run_id']}/result.json", f"{acc['run_id']}/final.txt"]),))
    rt.conn().commit()
    before = rt.mem_.recall(owner_user_id=O, agent_id="a1", session_id=S)["text"]
    assert "[udloebet]" not in before
    rt.conn().execute("UPDATE agent_artifacts SET status='expired' WHERE name='result.json'")
    rt.conn().commit()
    after = rt.mem_.recall(owner_user_id=O, agent_id="a1", session_id=S)["text"]
    assert f"evidens: {acc['run_id']}/result.json [udloebet], {acc['run_id']}/final.txt" in after
    assert f"{acc['run_id']}/final.txt [udloebet]" not in after


# --- hukommelse ---------------------------------------------------------------------------------------------------------------------

def _memory(rt, name, owner=O):
    rt.mem_.write_note(owner_user_id=owner, agent_id=name, content=f"note {name}", author=f"agent:{name}")
    rt.conn().execute("INSERT INTO agent_memory_errors (error_id, agent_id, assignment_id, error, created_at) "
                      "VALUES (?,?,?,?,?)", (f"e-{name}", name, "x", "fejl", "2026-01-01T00:00:00Z"))
    rt.conn().execute("INSERT INTO agent_session_relations (agent_id, session_id, owner_user_id, granted_by, created_at) "
                      "VALUES (?,?,?,?,?)", (name, "s2", owner, "t", "2026-01-01T00:00:00Z"))
    rt.conn().commit()


def _rows(rt, name):
    return {t: rt.conn().execute(f"SELECT COUNT(*) FROM {t} WHERE agent_id=?", (name,)).fetchone()[0]
            for t in ("agent_memory_summaries", "agent_memory_notes", "agent_memory_errors", "agent_session_relations")}


def _close(rt, name, closed_at):
    rt.conn().execute("UPDATE agent_registry SET lifecycle_status='closed', closed_at=? WHERE agent_id=?", (closed_at, name))
    rt.conn().commit()


def test_a_closed_agents_memory_is_kept_90_days_then_deleted_and_only_its_own(rt):
    a = rt.case("a1")
    rt.mem_.project_summary(a["assignment_id"])
    rt.case("a2")
    _memory(rt, "a1")
    _memory(rt, "a2")
    _close(rt, "a1", _iso(at(0)))
    assert _rows(rt, "a1") == {"agent_memory_summaries": 1, "agent_memory_notes": 1, "agent_memory_errors": 1,
                               "agent_session_relations": 1}
    assert rt.R_.sweep_memory(now=at(89.9)) == {"deleted": [], "stamped": [], "protected": {}}
    out = rt.R_.sweep_memory(now=at(90.1))
    assert out == {"deleted": [{"agent_id": "a1", "rows": 4}], "stamped": [], "protected": {}}
    assert _rows(rt, "a1") == dict.fromkeys(_rows(rt, "a1"), 0)
    assert _rows(rt, "a2") == {"agent_memory_summaries": 1, "agent_memory_notes": 1, "agent_memory_errors": 1,
                               "agent_session_relations": 1}


@pytest.mark.parametrize("lifecycle", ["available", "active", "suspended", "closing"])
def test_an_agent_that_is_not_closed_never_loses_memory_however_old(rt, lifecycle):
    rt.case("a1")
    _memory(rt, "a1")
    rt.conn().execute("UPDATE agent_registry SET lifecycle_status=?, closed_at=? WHERE agent_id='a1'",
                      (lifecycle, _iso(at(-1000))))
    rt.conn().commit()
    assert rt.R_.sweep_memory(now=at(5000)) == {"deleted": [], "stamped": [], "protected": {}}
    assert _rows(rt, "a1")["agent_memory_notes"] == 1


def test_a_closed_agent_without_a_close_time_gets_the_clock_started_now_not_deleted(rt):
    rt.case("a1")
    _memory(rt, "a1")
    _close(rt, "a1", "")
    out = rt.R_.sweep_memory(now=at(500))
    assert out == {"deleted": [], "stamped": ["a1"], "protected": {}}
    assert rt.conn().execute("SELECT closed_at FROM agent_registry WHERE agent_id='a1'").fetchone()[0] == _iso(at(500))
    assert rt.R_.sweep_memory(now=at(500 + 89))["deleted"] == []
    assert rt.R_.sweep_memory(now=at(500 + 91))["deleted"] == [{"agent_id": "a1", "rows": 4}]


@pytest.mark.parametrize("delivery", ["accepted", "delivered", "claimed_by_model_step"])
def test_memory_is_kept_while_any_result_of_the_agent_is_unprocessed(rt, delivery):
    rt.case("a1", delivery=delivery)
    _memory(rt, "a1")
    _close(rt, "a1", _iso(at(0)))
    assert rt.R_.sweep_memory(now=at(1000)) == {"deleted": [], "stamped": [], "protected": {"unprocessed_or_open": 1}}
    assert _rows(rt, "a1")["agent_memory_notes"] == 1


def test_memory_is_kept_while_an_assignment_is_still_open_or_has_no_receipt(rt):
    rt.case("a1", terminal=False)
    _memory(rt, "a1")
    _close(rt, "a1", _iso(at(0)))
    assert rt.R_.sweep_memory(now=at(1000))["protected"] == {"unprocessed_or_open": 1}
    rt.case("a2")
    rt.conn().execute("DELETE FROM agent_result_outbox")
    rt.conn().commit()
    _memory(rt, "a2")
    _close(rt, "a2", _iso(at(0)))
    assert rt.R_.sweep_memory(now=at(1000))["protected"] == {"unprocessed_or_open": 2}


def test_legacy_unscoped_agents_memory_is_never_touched(rt):
    rt.agent("old", owner=None)
    rt.conn().execute("INSERT INTO agent_memory_notes (note_id, agent_id, owner_user_id, owner_session_id, version, "
                      "content, author, created_at) VALUES ('n1','old','legacy_unscoped','',1,'x','a','2026-01-01T00:00:00Z')")
    rt.conn().commit()
    _close(rt, "old", _iso(at(-1000)))
    assert rt.R_.sweep_memory(now=at(5000)) == {"deleted": [], "stamped": [], "protected": {"legacy_or_unowned": 1}}
    assert _rows(rt, "old")["agent_memory_notes"] == 1


def test_closing_an_agent_records_when(rt):
    rt.case("a1")
    rt.c_.set_lifecycle(agent_id="a1", owner_user_id=O, lifecycle_status="closing")
    assert rt.conn().execute("SELECT closed_at FROM agent_registry WHERE agent_id='a1'").fetchone()[0] == ""
    rt.c_.set_lifecycle(agent_id="a1", owner_user_id=O, lifecycle_status="closed")
    stamped = rt.conn().execute("SELECT closed_at FROM agent_registry WHERE agent_id='a1'").fetchone()[0]
    assert stamped.endswith("Z") and datetime.fromisoformat(stamped.replace("Z", "+00:00")) <= datetime.now(UTC)
    rt.c_.set_lifecycle(agent_id="a1", owner_user_id=O, lifecycle_status="closed")          # aldrig genaabnet/omstemplet
    assert rt.conn().execute("SELECT closed_at FROM agent_registry WHERE agent_id='a1'").fetchone()[0] == stamped


# --- supervisoren -------------------------------------------------------------------------------------------------------------------

def test_run_runs_worktree_artifact_and_memory_sweeps_and_one_failing_part_does_not_stop_the_rest(rt, monkeypatch):
    acc = rt.case()

    def boom(**_):
        raise RuntimeError("worktree-sweep faldt")

    from core.services import agent_worktrees as W
    monkeypatch.setattr(W, "sweep", boom)
    out = rt.R_.run(now=at(31))
    assert out["errors"] == ["worktrees: RuntimeError: worktree-sweep faldt"] and "worktrees" not in out
    assert len(out["artifacts"]["expired"]) == 2 and out["memory"] == {"deleted": [], "stamped": [], "protected": {}}
    assert not any(os.path.exists(p) for p in rt.paths(acc))


def test_run_calls_the_existing_worktree_sweep_with_the_same_clock(rt, monkeypatch):
    from core.services import agent_worktrees as W
    seen = []
    monkeypatch.setattr(W, "sweep", lambda now=None: seen.append(now) or {"removed": []})
    out = rt.R_.run(now=at(3))
    assert seen == [at(3)] and out["worktrees"] == {"removed": []}


def test_supervise_runs_retention_at_most_once_an_hour(rt, monkeypatch):
    import core.services.agent_contract_service as svc
    calls = []
    monkeypatch.setattr(rt.R_, "run", lambda: calls.append(1) or {"errors": []})
    svc.supervise()
    svc.supervise()
    assert calls == [1]
    monkeypatch.setattr(rt.R_, "_last_run", rt.R_.time.monotonic() - rt.R_.RUN_EVERY_S - 1)
    svc.supervise()
    assert calls == [1, 1]


def test_a_failing_retention_round_never_breaks_the_supervisor(rt, monkeypatch):
    import core.services.agent_contract_service as svc

    def boom():
        raise RuntimeError("retention faldt")

    monkeypatch.setattr(rt.R_, "run", boom)
    assert svc.supervise() == []


def test_a_legacy_unscoped_assignment_protects_even_artifacts_that_name_an_owner(rt):
    acc = rt.case()
    rt.conn().execute("UPDATE agent_assignments SET owner_user_id='legacy_unscoped'")
    out = rt.sweep(5000)
    assert out["expired"] == [] and out["protected"] == {"legacy_or_unowned": 2} and all(os.path.exists(f) for f in rt.paths(acc))
