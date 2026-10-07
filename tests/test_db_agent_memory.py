"""C4: agentens egen erindring - deterministisk resume, versionerede noter, scoped genkaldelse."""
from __future__ import annotations

import json

import pytest


@pytest.fixture
def mem(isolated_runtime, monkeypatch):
    import core.runtime.db_agent_contract as c
    import core.runtime.db_agent_memory as m
    from core.runtime.db_agent_runtime import create_agent_registry_entry

    class H:
        c_, m_ = c, m

        def agent(self, name="a1", owner="bjorn", session="s1"):
            create_agent_registry_entry(agent_id=name, role="researcher", goal="g")
            c.bind_agent_owner(agent_id=name, owner_user_id=owner, owner_session_id=session)

        def task(self, name="a1", owner="bjorn", session="s1", goal="g"):
            return c.accept_assignment(agent_id=name, owner_user_id=owner, origin_session_id=session,
                                       goal=goal, parent_agent_id="jarvis", parent_run_id="pr")

        def finish(self, acc, status="completed", summary="", **kw):
            return c.commit_terminal_outcome(assignment_id=acc["assignment_id"], status=status,
                                             summary=summary, **kw)

        def summaries(self):
            return [dict(r) for r in c._conn().execute(
                "SELECT * FROM agent_memory_summaries ORDER BY created_at, summary_id")]

    h = H()
    h.agent()
    return h


def test_a_completed_assignment_gets_a_deterministic_summary_with_honest_unknowns(mem):
    acc = mem.task()
    mem.finish(acc, summary="fandt X i y.py:42", artifact_ref="run-1/result.json")
    (s,) = mem.summaries()
    assert (s["agent_id"], s["owner_user_id"], s["owner_session_id"], s["assignment_id"], s["status"]) == (
        "a1", "bjorn", "s1", acc["assignment_id"], "completed")
    assert (s["gjort"], s["besluttet"], s["aabent"]) == ("fandt X i y.py:42", "ukendt", "ukendt")
    assert json.loads(s["evidence_refs_json"]) == ["run-1/result.json"]


def test_a_failed_assignment_records_why_it_is_open_and_missing_fields_are_unknown(mem):
    acc = mem.task()
    mem.finish(acc, status="failed", error_code="AGENT_FAILED", error_phase="model")
    (s,) = mem.summaries()
    assert (s["gjort"], s["aabent"]) == ("ukendt", "opgaven endte failed: AGENT_FAILED model")
    assert json.loads(s["evidence_refs_json"]) == []


def test_summary_fields_are_truncated_to_the_fixed_schema(mem):
    acc = mem.task()
    mem.finish(acc, summary="ord " * 1000)
    (s,) = mem.summaries()
    assert len(s["gjort"]) == 600


def test_projection_makes_no_model_call_and_is_idempotent(mem, monkeypatch):
    from core.services import agent_runtime_spawn as M

    monkeypatch.setattr(M, "_facade", lambda: (_ for _ in ()).throw(AssertionError("modelkald!")))
    acc = mem.task()
    mem.finish(acc, summary="ok")
    assert mem.m_.project_summary(acc["assignment_id"]) is not None
    assert mem.m_.project_summary(acc["assignment_id"]) is not None
    assert len(mem.summaries()) == 1


def test_an_open_assignment_has_no_summary(mem):
    acc = mem.task()
    assert mem.m_.project_summary(acc["assignment_id"]) is None and mem.summaries() == []


def test_earlier_summaries_are_never_the_source_of_a_new_one(mem):
    first = mem.task()
    mem.finish(first, summary="HEMMELIG-FOERSTE-PAASTAND")
    second = mem.task()
    mem.finish(second, summary="anden")
    s1, s2 = mem.summaries()
    assert "HEMMELIG-FOERSTE-PAASTAND" not in json.dumps(s2) and s2["gjort"] == "anden"


def test_a_missing_result_is_unknown_never_borrowed_from_an_earlier_summary(mem):
    mem.finish(mem.task(), summary="FOERSTE-RESULTAT")
    mem.finish(mem.task(), status="failed")                          # intet resultat i det andet
    s1, s2 = mem.summaries()
    assert s1["gjort"] == "FOERSTE-RESULTAT" and s2["gjort"] == "ukendt"


def test_a_projection_failure_is_registered_never_changes_the_outcome_and_can_be_retried(mem, monkeypatch):
    acc = mem.task()
    real = mem.m_._clip
    monkeypatch.setattr(mem.m_, "_clip", lambda *a, **k: (_ for _ in ()).throw(ValueError("boem")))
    out = mem.finish(acc, summary="ok")
    assert out["committed"] is True
    assert mem.c_.get_assignment(assignment_id=acc["assignment_id"], owner_user_id="bjorn")["status"] == "completed"
    errs = [dict(r) for r in mem.c_._conn().execute("SELECT * FROM agent_memory_errors")]
    assert len(errs) == 1 and errs[0]["agent_id"] == "a1" and errs[0]["resolved_at"] == ""
    assert mem.summaries() == []
    rec = mem.m_.recall(owner_user_id="bjorn", agent_id="a1", session_id="s1")
    assert "Hukommelsesfejl" in rec["text"]               # synlig, ikke tavs tomhed
    monkeypatch.setattr(mem.m_, "_clip", real)
    assert mem.m_.retry_failed_projections() == [acc["assignment_id"]]
    assert len(mem.summaries()) == 1 and mem.m_.retry_failed_projections() == []


# --- noter ----------------------------------------------------------------------------------------

def test_notes_are_versioned_with_author_source_and_a_trace(mem):
    n1 = mem.m_.write_note(owner_user_id="bjorn", agent_id="a1", content="v1", author="agent:a1",
                           source_assignment_id="asg-1")
    n2 = mem.m_.write_note(owner_user_id="bjorn", agent_id="a1", content="v2", author="agent:a1")
    assert (n1["version"], n1["supersedes_note_id"], n1["source_assignment_id"]) == (1, "", "asg-1")
    assert (n2["version"], n2["supersedes_note_id"]) == (2, n1["note_id"])
    rows = mem.c_._conn().execute("SELECT version FROM agent_memory_notes ORDER BY version").fetchall()
    assert [r["version"] for r in rows] == [1, 2]                      # den gamle bevares


@pytest.mark.parametrize("kw,code", [
    ({"content": "  "}, "INVALID_SCOPE"),
    ({"content": "x" * 4001}, "CAPACITY"),
    ({"owner_user_id": "anden"}, "INVALID_SCOPE"),
    ({"owner_user_id": ""}, "INVALID_SCOPE"),
    ({"agent_id": "findes-ikke"}, "INVALID_SCOPE"),
])
def test_invalid_notes_are_refused_and_stored_nowhere(mem, kw, code):
    args = dict(owner_user_id="bjorn", agent_id="a1", content="ok", author="x")
    args.update(kw)
    with pytest.raises(mem.c_.ContractError) as e:
        mem.m_.write_note(**args)
    assert e.value.code == code
    assert mem.c_._conn().execute("SELECT COUNT(*) FROM agent_memory_notes").fetchone()[0] == 0


# --- genkaldelse -----------------------------------------------------------------------------------

def _seed(mem):
    mem.m_.write_note(owner_user_id="bjorn", agent_id="a1", content="husk edge-casen", author="agent:a1")
    mem.finish(mem.task(), summary="loeste første opgave")


def test_recall_is_framed_as_low_trust_data_and_cites_sources(mem):
    _seed(mem)
    r = mem.m_.recall(owner_user_id="bjorn", agent_id="a1", session_id="s1")
    t = r["text"]
    assert r["items"] == 2 and r["error"] == ""
    assert "LAVERE tillid" in t and "ikke instruktion" in t and "ikke ny evidens" in t
    assert "[note v1 · af agent:a1" in t and "husk edge-casen" in t
    assert "[resume · assignment asg-" in t and "gjort: loeste første opgave" in t


@pytest.mark.parametrize("owner,agent,session", [
    ("anden", "a1", "s1"),            # anden bruger
    ("bjorn", "a1", "s2"),            # samme bruger, anden session UDEN relation
    ("bjorn", "findes-ikke", "s1"),   # forfalsket agent-id
    ("", "a1", "s1"), ("bjorn", "a1", ""),
])
def test_recall_leaks_nothing_across_owner_session_or_agent(mem, owner, agent, session):
    _seed(mem)
    assert mem.m_.recall(owner_user_id=owner, agent_id=agent, session_id=session) == {
        "text": "", "items": 0, "error": ""}


def test_an_explicit_session_relation_unlocks_the_old_memory_for_that_session_only(mem):
    _seed(mem)
    mem.m_.grant_session_relation(owner_user_id="bjorn", agent_id="a1", session_id="s2", granted_by="bjorn")
    assert mem.m_.recall(owner_user_id="bjorn", agent_id="a1", session_id="s2")["items"] == 2
    assert mem.m_.recall(owner_user_id="bjorn", agent_id="a1", session_id="s3")["items"] == 0


def test_only_the_agents_owner_can_grant_a_relation(mem):
    with pytest.raises(mem.c_.ContractError):
        mem.m_.grant_session_relation(owner_user_id="anden", agent_id="a1", session_id="s2", granted_by="x")
    with pytest.raises(mem.c_.ContractError):
        mem.m_.grant_session_relation(owner_user_id="bjorn", agent_id="a1", session_id="", granted_by="x")


def test_a_new_agent_with_the_same_role_inherits_nothing(mem):
    _seed(mem)
    mem.agent("a2")
    assert mem.m_.recall(owner_user_id="bjorn", agent_id="a2", session_id="s1")["items"] == 0


def test_the_budget_limits_the_excerpt_and_says_so(mem):
    for i in range(5):
        mem.finish(mem.task(), summary=f"opgave {i} " + "y" * 300)
    r = mem.m_.recall(owner_user_id="bjorn", agent_id="a1", session_id="s1", budget_chars=700)
    assert 0 < r["items"] < 5 and "udeladt af budgettet" in r["text"]


def test_a_read_failure_is_visible_and_forbids_assuming_nothing_happened(mem, monkeypatch):
    monkeypatch.setattr(mem.m_, "_conn", lambda: (_ for _ in ()).throw(RuntimeError("db nede")))
    r = mem.m_.recall(owner_user_id="bjorn", agent_id="a1", session_id="s1")
    assert r["error"].startswith("RuntimeError") and "Antag IKKE at intet tidligere arbejde findes" in r["text"]
    assert "Hukommelsesfejl: erindringen kunne ikke laeses" in r["text"]


# --- ind i selve prompten --------------------------------------------------------------------------

def test_a_followup_assignment_prompt_carries_the_agents_own_memory(mem):
    from core.runtime.db_agent_runtime import get_agent_registry_entry
    from core.services.agent_prompt_layers import build_layered_prompt

    mem.finish(mem.task(), summary="første opgave løst med metode Q")
    mem.task(goal="anden opgave")
    t = build_layered_prompt(agent=get_agent_registry_entry("a1"), messages_text="",
                             execution_mode="solo-task")["text"]
    assert "EGEN ERINDRING" in t and "metode Q" in t
    assert t.index("[OPGAVE") < t.index("EGEN ERINDRING") < t.index("Samtalen hidtil")


def test_collective_layers_are_not_injected_into_another_users_agent(isolated_runtime, monkeypatch):
    import core.identity.owner_resolver as orr
    import core.services.agent_skill_library as lib
    import core.services.cross_agent_memory as cam
    from core.services.agent_runtime_spawn import spawn_agent_task

    monkeypatch.setattr(orr, "owner_user_id", lambda: "bjorn")
    monkeypatch.setattr(lib, "get_skills", lambda role: {"exists": True, "content": "SKILL-TEKST"})
    monkeypatch.setattr(cam, "cross_agent_recall_section", lambda **k: "TVAERAGENT-OBSERVATION")

    def prompt(ctx):
        a = spawn_agent_task(role="researcher", goal="g", auto_execute=False, context=ctx)
        from core.runtime.db_agent_runtime import get_agent_registry_entry
        return get_agent_registry_entry(a["agent_id"])["system_prompt"]

    own, other, legacy = (prompt({"user_id": "bjorn", "parent_session_id": "s"}),
                          prompt({"user_id": "anden", "parent_session_id": "s"}), prompt({}))
    for p in (own, legacy):
        assert "SKILL-TEKST" in p and "TVAERAGENT-OBSERVATION" in p
    assert "SKILL-TEKST" not in other and "TVAERAGENT-OBSERVATION" not in other
