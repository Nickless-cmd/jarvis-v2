"""F4a: approval-lageret - regler haandhaevet i DB, ikke i en prompt. Rigtig sqlite og rigtige traade."""
from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

import pytest

NOW = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def ap(isolated_runtime, monkeypatch):
    import core.runtime.db_agent_approvals as A
    import core.runtime.db_agent_contract as c
    from core.runtime.db_agent_runtime import create_agent_registry_entry

    class H:
        A_, c_ = A, c

        def task(self, name="a1", owner="bjorn", session="s1"):
            create_agent_registry_entry(agent_id=name, role="executor", goal="g")
            c.bind_agent_owner(agent_id=name, owner_user_id=owner, owner_session_id=session)
            return c.accept_assignment(agent_id=name, owner_user_id=owner, origin_session_id=session,
                                       goal="g", parent_agent_id="jarvis", parent_run_id="pr")

        _default = None

        def req(self, acc=None, tool="bash", args=None, owner="bjorn", session="s1", **kw):
            if acc is None:
                self._default = self._default or self.task()
                acc = self._default
            return A.request(owner_user_id=owner, origin_session_id=session, assignment_id=acc["assignment_id"],
                             tool_name=tool, arguments=args if args is not None else {"command": "rm -rf build"},
                             run_id=acc["run_id"], now=kw.pop("now", NOW), **kw)

        def human(self, r, decision="approve", who="bjorn", **kw):
            return A.decide(approval_id=r["approval_id"], decision=decision, actor_user_id=who,
                            actor_kind="human", digest=kw.pop("digest", r["args_digest"]),
                            now=kw.pop("now", NOW + timedelta(minutes=1)), **kw)

    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id", lambda: "platform-ejer")
    return H()


def test_a_request_is_durable_bound_and_has_a_safe_view_and_an_expiry(ap):
    r = ap.req(args={"command": "deploy", "_runtime_session_id": "s1", "token": "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3"})
    assert (r["status"], r["kind"], r["owner_user_id"], r["origin_session_id"], r["tool_name"], r["risk_class"]) == (
        "pending", "tool_call", "bjorn", "s1", "bash", "write")
    assert (r["agent_id"], r["parent_agent_id"], r["parent_run_id"], r["target"]) == (
        "a1", "jarvis", "pr", "runtime-container")
    assert r["assignment_id"] and r["run_id"] and r["args_digest"] and r["approval_id"].startswith("appr-")
    assert "_runtime_session_id" not in r["arguments_json"]                  # serverens egne felter er ikke handlingen
    assert "hemmelighed fjernet" in r["safe_view"] and "ghp_" not in r["safe_view"]
    assert datetime.fromisoformat(r["expires_at"].replace("Z", "+00:00")) - NOW == timedelta(hours=48)
    assert [e["event"] for e in ap.A_.audit_trail(approval_id=r["approval_id"])] == ["requested"]


def test_the_digest_covers_tool_arguments_target_and_assignment(ap):
    base = dict(tool_name="bash", arguments={"command": "ls"}, target="runtime-container", assignment_id="asg-1")
    d = ap.A_.invocation_digest(**base)
    assert ap.A_.invocation_digest(**{**base, "arguments": {"command": "ls", "_runtime_x": 1}}) == d
    for change in ({"tool_name": "write_file"}, {"arguments": {"command": "ls -la"}},
                   {"target": "client:laptop"}, {"assignment_id": "asg-2"}):
        assert ap.A_.invocation_digest(**{**base, **change}) != d, change


def test_requesting_the_same_action_twice_returns_the_same_approval(ap):
    acc = ap.task()
    first, again = ap.req(acc), ap.req(acc)
    assert again["approval_id"] == first["approval_id"]
    assert len(ap.A_.list_for_owner(owner_user_id="bjorn")) == 1
    other = ap.req(acc, args={"command": "noget andet"})
    assert other["approval_id"] != first["approval_id"]


@pytest.mark.parametrize("case", ["anden-ejer", "anden-session", "afsluttet", "ukendt", "tom-ejer"])
def test_a_request_must_match_owner_session_and_an_open_assignment(ap, case):
    acc = ap.task()
    kw = dict(owner_user_id="bjorn", origin_session_id="s1", assignment_id=acc["assignment_id"])
    if case == "anden-ejer":
        kw["owner_user_id"] = "anden"
    elif case == "anden-session":
        kw["origin_session_id"] = "s2"
    elif case == "afsluttet":
        ap.c_.commit_terminal_outcome(assignment_id=acc["assignment_id"], status="completed")
    elif case == "ukendt":
        kw["assignment_id"] = "asg-findes-ikke"
    else:
        kw["owner_user_id"] = ""
    with pytest.raises(ap.c_.ContractError):
        ap.A_.request(tool_name="bash", arguments={}, **kw)
    assert ap.A_.list_for_owner(owner_user_id="bjorn") == []


def test_a_human_owner_can_approve_and_the_decision_is_recorded_and_audited(ap):
    r = ap.req()
    d = ap.human(r, note="ok, men kun denne ene gang")
    assert (d["status"], d["decided_by"], d["decision_note"]) == ("approved", "bjorn", "ok, men kun denne ene gang")
    assert [e["event"] for e in ap.A_.audit_trail(approval_id=r["approval_id"])] == ["requested", "approved"]


def test_the_platform_owner_may_decide_too(ap):
    r = ap.req()
    assert ap.human(r, who="platform-ejer")["status"] == "approved"


@pytest.mark.parametrize("kind", ["agent", "model", "jarvis", "system", "", "HUMAN"])
def test_only_a_human_can_decide_never_jarvis_an_agent_or_a_model(ap, kind):
    r = ap.req()
    with pytest.raises(ap.c_.ContractError) as e:
        ap.A_.decide(approval_id=r["approval_id"], decision="approve", actor_user_id="bjorn", actor_kind=kind,
                     digest=r["args_digest"], now=NOW)
    assert e.value.code == "POLICY_DENIED"
    assert ap.A_.get(approval_id=r["approval_id"])["status"] == "pending"
    assert any(x["event"].startswith("refused: ikke et menneske") for x in ap.A_.audit_trail(approval_id=r["approval_id"]))


@pytest.mark.parametrize("who", ["anden", "", "a1", "jarvis"])
def test_a_human_who_is_neither_owner_nor_platform_owner_is_refused(ap, who):
    r = ap.req()
    with pytest.raises(ap.c_.ContractError) as e:
        ap.human(r, who=who)
    assert e.value.code == "POLICY_DENIED" and ap.A_.get(approval_id=r["approval_id"])["status"] == "pending"


def test_a_stale_digest_means_the_action_changed_and_needs_a_new_approval(ap):
    r = ap.req()
    for bad in ("", "0" * 64, ap.A_.invocation_digest(tool_name="bash", arguments={"command": "andet"},
                                                       target="runtime-container", assignment_id=r["assignment_id"])):
        with pytest.raises(ap.c_.ContractError) as e:
            ap.human(r, digest=bad)
        assert e.value.code == "INVALID_SCOPE"
    assert ap.A_.get(approval_id=r["approval_id"])["status"] == "pending"


def test_a_decision_after_expiry_is_refused_and_marks_the_approval_expired(ap):
    r = ap.req()
    with pytest.raises(ap.c_.ContractError) as e:
        ap.human(r, now=NOW + timedelta(hours=48, seconds=1))
    assert e.value.code == "EXPIRED" and ap.A_.get(approval_id=r["approval_id"])["status"] == "expired"


def test_double_decision_is_refused(ap):
    r = ap.req()
    ap.human(r, "deny")
    with pytest.raises(ap.c_.ContractError) as e:
        ap.human(r, "approve")
    assert e.value.code == "INVALID_TRANSITION" and ap.A_.get(approval_id=r["approval_id"])["status"] == "denied"


def test_concurrent_approve_and_deny_give_exactly_one_winner(ap):
    r = ap.req()
    out = []

    def go(decision):
        try:
            ap.human(r, decision)
            out.append(decision)
        except ap.c_.ContractError as exc:
            out.append(exc.code)

    ts = [threading.Thread(target=go, args=(d,)) for d in ("approve", "deny", "approve", "deny")]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sum(1 for x in out if x in ("approve", "deny")) == 1 and out.count("INVALID_TRANSITION") == 3
    assert ap.A_.get(approval_id=r["approval_id"])["status"] in ("approved", "denied")


def test_an_approval_can_be_consumed_exactly_once(ap):
    r = ap.req()
    ap.human(r)
    assert ap.A_.consume(approval_id=r["approval_id"], digest=r["args_digest"], now=NOW + timedelta(minutes=2)) is True
    assert ap.A_.consume(approval_id=r["approval_id"], digest=r["args_digest"], now=NOW + timedelta(minutes=2)) is False
    assert ap.A_.get(approval_id=r["approval_id"])["status"] == "consumed"
    events = [e["event"] for e in ap.A_.audit_trail(approval_id=r["approval_id"])]
    assert events == ["requested", "approved", "consumed", "consume refused"]


def test_concurrent_consumers_get_one_execution(ap):
    r = ap.req()
    ap.human(r)
    wins = []
    ts = [threading.Thread(target=lambda: wins.append(ap.A_.consume(
        approval_id=r["approval_id"], digest=r["args_digest"], now=NOW + timedelta(minutes=2)))) for _ in range(6)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert wins.count(True) == 1


@pytest.mark.parametrize("case", ["pending", "denied", "forkert-digest", "udloebet"])
def test_consume_refuses_anything_but_a_fresh_approved_exact_match(ap, case):
    r = ap.req()
    digest, now = r["args_digest"], NOW + timedelta(minutes=2)
    if case == "denied":
        ap.human(r, "deny")
    elif case == "forkert-digest":
        ap.human(r)
        digest = "f" * 64
    elif case == "udloebet":
        ap.human(r)
        now = NOW + timedelta(hours=49)
    assert ap.A_.consume(approval_id=r["approval_id"], digest=digest, now=now) is False
    assert ap.A_.get(approval_id=r["approval_id"])["status"] != "consumed"


def test_a_denied_action_cannot_be_requested_again_in_the_same_assignment(ap):
    acc = ap.task()
    r = ap.req(acc)
    ap.human(r, "deny")
    with pytest.raises(ap.c_.ContractError) as e:
        ap.req(acc)
    assert e.value.code == "POLICY_DENIED"
    assert any(x["event"] == "re-request refused" for x in ap.A_.audit_trail(approval_id=r["approval_id"]))
    other_task = ap.task("a2")                                                  # et ANDET assignment er ikke bundet af det
    assert ap.req(other_task)["status"] == "pending"
    changed = ap.req(acc, args={"command": "noget andet"})                       # en anden handling kan godt anmodes
    assert changed["status"] == "pending"


def test_expire_due_expires_pending_and_unused_approved_but_not_consumed_or_fresh(ap):
    pend = ap.req(args={"command": "1"})
    appr = ap.req(args={"command": "2"})
    ap.human(appr)
    used = ap.req(args={"command": "3"})
    ap.human(used)
    ap.A_.consume(approval_id=used["approval_id"], digest=used["args_digest"], now=NOW + timedelta(minutes=2))
    fresh = ap.req(args={"command": "4"}, now=NOW + timedelta(hours=47))
    due = ap.A_.expire_due(now=NOW + timedelta(hours=48, minutes=1))
    assert sorted(due) == sorted([pend["approval_id"], appr["approval_id"]])
    st = {x["approval_id"]: x["status"] for x in ap.A_.list_for_owner(owner_user_id="bjorn")}
    assert (st[pend["approval_id"]], st[appr["approval_id"]], st[used["approval_id"]], st[fresh["approval_id"]]) == (
        "expired", "expired", "consumed", "pending")


def test_an_expired_approval_can_be_requested_anew(ap):
    acc = ap.task()
    old = ap.req(acc)
    ap.A_.expire_due(now=NOW + timedelta(days=3))
    new = ap.req(acc, now=NOW + timedelta(days=3))
    assert new["approval_id"] != old["approval_id"] and new["status"] == "pending"


def test_cancel_for_assignment_cancels_open_approvals_only(ap):
    acc = ap.task()
    p, a = ap.req(acc, args={"command": "1"}), ap.req(acc, args={"command": "2"})
    ap.human(a)
    d = ap.req(acc, args={"command": "3"})
    ap.human(d, "deny")
    assert sorted(ap.A_.cancel_for_assignment(assignment_id=acc["assignment_id"], reason="afsluttet")) == sorted(
        [p["approval_id"], a["approval_id"]])
    st = {x["approval_id"]: x["status"] for x in ap.A_.list_for_owner(owner_user_id="bjorn")}
    assert (st[p["approval_id"]], st[a["approval_id"]], st[d["approval_id"]]) == ("cancelled", "cancelled", "denied")


def test_listing_and_lookup_are_owner_scoped(ap):
    mine = ap.req()
    theirs = ap.req(ap.task("a9", owner="anden", session="sx"), owner="anden", session="sx")
    assert [x["approval_id"] for x in ap.A_.list_for_owner(owner_user_id="bjorn")] == [mine["approval_id"]]
    assert ap.A_.get_for_owner(owner_user_id="bjorn", approval_id=theirs["approval_id"]) is None
    assert ap.A_.get_for_owner(owner_user_id="bjorn", approval_id=mine["approval_id"]) is not None
    assert [x["approval_id"] for x in ap.A_.list_for_owner(owner_user_id="bjorn", status="pending",
                                                         origin_session_id="s1")] == [mine["approval_id"]]
    assert ap.A_.list_for_owner(owner_user_id="bjorn", origin_session_id="andet") == []
    with pytest.raises(ap.c_.ContractError):
        ap.A_.list_for_owner(owner_user_id="")


def test_each_pending_approval_is_announced_to_the_parent_exactly_once(ap):
    a, b = ap.req(args={"command": "1"}), ap.req(args={"command": "2"})
    first = ap.A_.claim_announcements(owner_user_id="bjorn", origin_session_id="s1")
    assert {x["approval_id"] for x in first} == {a["approval_id"], b["approval_id"]}
    assert ap.A_.claim_announcements(owner_user_id="bjorn", origin_session_id="s1") == []
    assert ap.A_.claim_announcements(owner_user_id="bjorn", origin_session_id="s2") == []
    assert ap.A_.claim_announcements(owner_user_id="anden", origin_session_id="s1") == []
    c = ap.req(args={"command": "3"})
    assert [x["approval_id"] for x in ap.A_.claim_announcements(owner_user_id="bjorn", origin_session_id="s1")] == [c["approval_id"]]


def test_concurrent_announcement_claims_never_double_announce(ap):
    for i in range(4):
        ap.req(args={"command": str(i)})
    got = []
    ts = [threading.Thread(target=lambda: got.extend(
        ap.A_.claim_announcements(owner_user_id="bjorn", origin_session_id="s1"))) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len(got) == 4 and len({x["approval_id"] for x in got}) == 4


def test_a_restart_rebuilds_the_pending_set_from_the_database_alone(ap):
    r = ap.req()
    ap.A_.claim_announcements(owner_user_id="bjorn", origin_session_id="s1")
    # "genstart": ingen processtilstand - alt laeses fra DB
    pending = ap.A_.list_for_owner(owner_user_id="bjorn", status="pending")
    assert [p["approval_id"] for p in pending] == [r["approval_id"]] and pending[0]["announced_at"]
    assert ap.human(pending[0])["status"] == "approved"                           # kan stadig afgoeres


def test_announcement_claim_is_atomic_even_with_a_forced_window_between_select_and_update(ap, monkeypatch):
    import time

    for i in range(3):
        ap.req(args={"command": str(i)})
    real = ap.A_._now_iso

    def slow():
        time.sleep(0.2)                    # vinduet mellem SELECT og UPDATE
        return real()

    monkeypatch.setattr(ap.A_, "_now_iso", slow)
    got, errors = [], []

    def go():
        try:
            got.extend(ap.A_.claim_announcements(owner_user_id="bjorn", origin_session_id="s1"))
        except Exception as exc:               # uden skrivelaas dør de tabende traade med 'database is locked'
            errors.append(type(exc).__name__)

    ts = [threading.Thread(target=go) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert errors == [] and len(got) == 3 and len({x["approval_id"] for x in got}) == 3
