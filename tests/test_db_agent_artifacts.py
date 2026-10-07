"""C1: artefaktlager - atomiske skrivninger, ejer-adgang, afstemning, terminale artefakter."""
from __future__ import annotations

import json
import os
import time

import pytest


@pytest.fixture
def art(isolated_runtime):
    import core.runtime.db_agent_artifacts as a
    import core.runtime.db_agent_contract as c
    from core.runtime.db_agent_runtime import create_agent_registry_entry

    class H:
        a_, c_ = a, c

        def agent(self, name="a1", owner="bjorn", session="s1", settle_via_registry=False):
            create_agent_registry_entry(agent_id=name, role="r", goal="g")
            c.bind_agent_owner(agent_id=name, owner_user_id=owner, owner_session_id=session)
            acc = c.accept_assignment(agent_id=name, owner_user_id=owner, origin_session_id=session,
                                      goal="g", parent_agent_id="jarvis", parent_run_id="pr")
            return acc

        def w(self, acc, name="result.json", data="{}", owner="bjorn", **kw):
            return a.write_artifact(agent_id=acc["agent_id"], run_id=acc["run_id"], name=name,
                                    data=data, assignment_id=acc["assignment_id"],
                                    owner_user_id=owner, **kw)

    return H()


def test_write_is_atomic_registered_and_leaves_no_tmp(art):
    acc = art.agent()
    rec = art.w(acc, "final.txt", "hej æøå")
    assert (rec["size"], rec["status"], rec["owner_user_id"]) == (len("hej æøå".encode()), "complete", "bjorn")
    import hashlib
    assert rec["sha256"] == hashlib.sha256("hej æøå".encode()).hexdigest()
    files = sorted(p.name for p in os.scandir(os.path.dirname(rec["path"])))
    assert files == ["final.txt"]


def test_rewriting_a_name_replaces_content_and_record(art):
    acc = art.agent()
    art.w(acc, "final.txt", "første")
    rec = art.w(acc, "final.txt", "anden version")
    assert open(rec["path"], encoding="utf-8").read() == "anden version"
    assert art.a_.run_bytes(acc["run_id"]) == len("anden version")


@pytest.mark.parametrize("name", ["../etc/passwd", "x.txt", "result.json/../x", ""])
def test_unknown_artifact_names_are_refused(art, name):
    acc = art.agent()
    with pytest.raises(art.c_.ContractError) as e:
        art.w(acc, name)
    assert e.value.code == "INVALID_SCOPE"


@pytest.mark.parametrize("agent_id,run_id", [("../x", "r"), ("a", "../r"), ("a/b", "r"), ("", "r"), ("a", "a..b")])
def test_path_traversal_in_ids_is_refused(art, agent_id, run_id):
    with pytest.raises(art.c_.ContractError):
        art.a_.write_artifact(agent_id=agent_id, run_id=run_id, name="final.txt", data="x",
                              assignment_id="asg", owner_user_id="bjorn")


def test_over_the_per_run_limit_writes_nothing_and_registers_nothing(art, monkeypatch):
    acc = art.agent()
    monkeypatch.setattr(art.a_, "MAX_RUN_BYTES", 10)
    art.w(acc, "stdout.log", "12345")
    with pytest.raises(art.a_.ArtifactTooLarge):
        art.w(acc, "stderr.log", "1234567")
    assert art.a_.get_artifact_record(run_id=acc["run_id"], name="stderr.log") is None
    assert art.a_.run_bytes(acc["run_id"]) == 5
    art.w(acc, "stdout.log", "1234567890")        # genskrivning raekker kun sin egen stoerrelse


def test_a_crash_before_the_rename_leaves_no_file_no_tmp_and_no_row(art, monkeypatch):
    acc = art.agent()
    monkeypatch.setattr(os, "replace", lambda *a, **k: (_ for _ in ()).throw(OSError("diskfuld")))
    with pytest.raises(OSError):
        art.w(acc, "final.txt", "x")
    assert art.a_.get_artifact_record(run_id=acc["run_id"], name="final.txt") is None
    d = art.a_._run_dir(acc["agent_id"], acc["run_id"])
    assert [p.name for p in d.iterdir()] == []


def test_read_is_owner_checked_paged_and_flags_partial(art):
    acc = art.agent()
    art.w(acc, "final.txt", "abcdefghij", status="partial")
    ref = f"{acc['run_id']}/final.txt"
    out = art.a_.read_artifact(owner_user_id="bjorn", ref=ref, offset=2, limit=3)
    assert (out["status"], out["content"], out["truncated"], out["partial"], out["size"]) == (
        "ok", "cde", True, True, 10)
    assert art.a_.read_artifact(owner_user_id="bjorn", ref=ref, offset=8)["truncated"] is False
    for who in ("anden", "", None):
        assert art.a_.read_artifact(owner_user_id=who, ref=ref)["status"] == "NOT_FOUND"
    assert art.a_.read_artifact(owner_user_id="bjorn", ref="findes/ikke")["status"] == "NOT_FOUND"


def test_read_reports_missing_corrupt_and_expired_instead_of_empty_text(art):
    acc = art.agent()
    rec = art.w(acc, "final.txt", "intakt")
    ref = f"{acc['run_id']}/final.txt"
    open(rec["path"], "w").write("pillet")
    assert art.a_.read_artifact(owner_user_id="bjorn", ref=ref)["status"] == "CORRUPT"
    os.unlink(rec["path"])
    assert art.a_.read_artifact(owner_user_id="bjorn", ref=ref)["status"] == "MISSING"
    c = art.a_._conn()
    c.execute("UPDATE agent_artifacts SET status='expired'")
    c.commit()
    assert art.a_.read_artifact(owner_user_id="bjorn", ref=ref)["status"] == "EXPIRED"


def test_reconcile_marks_missing_and_corrupt_finds_orphans_and_cleans_stale_tmp(art):
    acc = art.agent()
    good, gone, bad = art.w(acc, "result.json"), art.w(acc, "final.txt", "a"), art.w(acc, "stdout.log", "b")
    os.unlink(gone["path"])
    open(bad["path"], "w").write("andet")
    d = art.a_.artifact_root() / acc["agent_id"] / acc["run_id"]
    (d / "stderr.log").write_text("forældreløs")                      # fil uden DB-post
    old, fresh = d / "x.tmp", d / "y.tmp"
    old.write_text("."), fresh.write_text(".")
    past = time.time() - 7200
    os.utime(old, (past, past))
    out = art.a_.reconcile()
    ref = lambda n: f"{acc['run_id']}/{n}"
    assert out["missing"] == [ref("final.txt")] and out["corrupt"] == [ref("stdout.log")]
    assert out["orphans"] == [str(d / "stderr.log")] and out["tmp_removed"] == [str(old)]
    assert not old.exists() and fresh.exists()
    assert art.a_.get_artifact_record(run_id=acc["run_id"], name="result.json")["status"] == "complete"
    assert art.a_.get_artifact_record(run_id=acc["run_id"], name="final.txt")["status"] == "missing"
    assert art.a_.reconcile()["missing"] == []                         # idempotent
    assert good["sha256"]


def test_manifest_lists_every_attempt_of_an_assignment_for_its_owner_only(art):
    acc = art.agent()
    art.w(acc, "stdout.log", "forsøg 1")
    c = art.c_._conn()
    c.execute("INSERT INTO agent_runs (run_id, agent_id, status, assignment_id, owner_user_id, "
              "attempt_no, created_at, updated_at) VALUES ('run-2','a1','running',?,?,2,'t','t')",
              (acc["assignment_id"], "bjorn"))
    c.commit()
    art.a_.write_artifact(agent_id="a1", run_id="run-2", name="final.txt", data="forsøg 2",
                          assignment_id=acc["assignment_id"], owner_user_id="bjorn")
    m = art.a_.manifest(owner_user_id="bjorn", assignment_id=acc["assignment_id"])
    assert [(x["attempt_no"], x["name"]) for x in m] == [(1, "stdout.log"), (2, "final.txt")]
    assert art.a_.manifest(owner_user_id="anden", assignment_id=acc["assignment_id"]) == []


# --- terminale artefakter -----------------------------------------------------------------

def _settle(art, acc, text, status="completed", fail_write=False):
    from core.runtime.db_agent_runtime import create_agent_message, update_agent_registry_entry

    if text:
        create_agent_message(message_id="m1", thread_id="t", agent_id=acc["agent_id"],
                             direction="agent->jarvis", role="assistant", kind="result", content=text)
    update_agent_registry_entry(acc["agent_id"], status=status)
    (m,) = art.c_.list_pending_results(owner_user_id="bjorn", origin_session_id="s1")
    return json.loads(m["payload_json"])


def test_terminal_settlement_stores_the_full_reply_not_just_the_summary(art):
    acc = art.agent()
    long = "linje\n" * 400                      # 2400 tegn > 500-tegns resume
    payload = _settle(art, acc, long)
    assert payload["artifact_ref"] == f"{acc['run_id']}/result.json" and payload["artifact_error"] == ""
    assert len(payload["summary"]) == 500
    final = art.a_.read_artifact(owner_user_id="bjorn", ref=f"{acc['run_id']}/final.txt", limit=10_000)
    assert final["content"] == long
    res = json.loads(art.a_.read_artifact(owner_user_id="bjorn", ref=payload["artifact_ref"])["content"])
    assert (res["status"], res["has_final_text"], res["attempt_run_ids"]) == ("completed", True, [acc["run_id"]])


def test_result_file_exists_before_the_terminal_db_commit(art, monkeypatch):
    acc = art.agent()
    seen = {}
    real = art.c_.commit_terminal_outcome

    def spy(**kw):
        seen["on_disk"] = art.a_.get_artifact_record(run_id=acc["run_id"], name="result.json") is not None
        return real(**kw)

    monkeypatch.setattr(art.c_, "commit_terminal_outcome", spy)
    _settle(art, acc, "svar")
    assert seen == {"on_disk": True}


def test_a_failing_artifact_write_is_visible_and_never_changes_the_outcome(art, monkeypatch):
    acc = art.agent()
    monkeypatch.setattr(art.a_, "write_artifact",
                        lambda **kw: (_ for _ in ()).throw(OSError("disk")))
    payload = _settle(art, acc, "svar")
    assert payload["status"] == "completed" and payload["artifact_ref"] == ""
    assert payload["artifact_error"].startswith("OSError")


def test_failed_agent_without_any_reply_still_gets_a_result_file(art):
    acc = art.agent()
    payload = _settle(art, acc, "", status="failed")
    res = json.loads(art.a_.read_artifact(owner_user_id="bjorn", ref=payload["artifact_ref"])["content"])
    assert (res["status"], res["error_code"], res["has_final_text"]) == ("failed", "AGENT_FAILED", False)
    assert art.a_.get_artifact_record(run_id=acc["run_id"], name="final.txt") is None
