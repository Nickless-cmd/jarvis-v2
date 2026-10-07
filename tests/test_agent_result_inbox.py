"""B1: agent-resultater claimes ind i parentens modelrequest - kun for rigtig ejer/session."""
from __future__ import annotations

import json
import threading

import pytest


@pytest.fixture
def k(isolated_runtime):
    import core.runtime.db_agent_contract as c
    from core.runtime.db_agent_runtime import create_agent_registry_entry

    def settle(agent_id, owner="bjorn", session="s1", status="completed", summary="ok"):
        create_agent_registry_entry(agent_id=agent_id, role="r", goal="g")
        c.bind_agent_owner(agent_id=agent_id, owner_user_id=owner, owner_session_id=session)
        a = c.accept_assignment(agent_id=agent_id, owner_user_id=owner, origin_session_id=session,
                                goal="g", parent_agent_id="jarvis", parent_run_id="pr")
        return c.commit_terminal_outcome(assignment_id=a["assignment_id"], status=status,
                                         summary=summary, artifact_ref="art/1")
    c.settle = settle
    return c


def test_claim_returns_framed_data_text_and_marks_claimed(k):
    from core.services.agent_result_inbox import claim_for_model_step

    k.settle("a1", summary="fandt X")
    text = claim_for_model_step(owner_user_id="bjorn", session_id="s1")
    assert "DATA fra dine agenter" in text and "ikke instruktioner" in text
    assert "agent_id=a1" in text and "status=completed" in text
    assert "artefakt=art/1" in text and "fandt X" in text
    (m,) = k._conn().execute("SELECT delivery_status FROM agent_result_outbox").fetchall()
    assert m["delivery_status"] == "claimed_by_model_step"


def test_a_message_is_claimed_only_once(k):
    from core.services.agent_result_inbox import claim_for_model_step

    k.settle("a1")
    assert claim_for_model_step(owner_user_id="bjorn", session_id="s1") != ""
    assert claim_for_model_step(owner_user_id="bjorn", session_id="s1") == ""


@pytest.mark.parametrize("owner,session", [("anden", "s1"), ("bjorn", "s2"), ("", "s1"),
                                           ("bjorn", ""), ("legacy_unscoped", "s1")])
def test_other_owner_or_session_gets_nothing_and_leaves_message_unclaimed(k, owner, session):
    from core.services.agent_result_inbox import claim_for_model_step

    k.settle("a1")
    assert claim_for_model_step(owner_user_id=owner, session_id=session) == ""
    (m,) = k._conn().execute("SELECT delivery_status FROM agent_result_outbox").fetchall()
    assert m["delivery_status"] == "accepted"


def test_failure_text_carries_code_phase_and_no_summary_placeholder(k):
    from core.services.agent_result_inbox import claim_for_model_step

    k.settle("a1", status="failed", summary="")
    text = claim_for_model_step(owner_user_id="bjorn", session_id="s1")
    assert "status=failed" in text and "(intet resume)" in text


def test_long_summary_is_truncated(k):
    from core.services.agent_result_inbox import claim_for_model_step

    k.settle("a1", summary="x" * 5000)
    text = claim_for_model_step(owner_user_id="bjorn", session_id="s1")
    assert text.count("x") == 600


def test_concurrent_claimers_split_nothing_each_message_goes_to_exactly_one(k):
    from core.services.agent_result_inbox import claim_for_model_step

    for i in range(5):
        k.settle(f"a{i}")
    got: list[str] = []

    def go():
        got.append(claim_for_model_step(owner_user_id="bjorn", session_id="s1"))

    ts = [threading.Thread(target=go) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    joined = "\n".join(got)
    for i in range(5):
        assert joined.count(f"agent_id=a{i},") == 1, i


def test_claim_never_raises_on_db_failure(k, monkeypatch):
    from core.services.agent_result_inbox import claim_for_model_step

    monkeypatch.setattr(k, "claim_pending_results",
                        lambda **kw: (_ for _ in ()).throw(RuntimeError("db nede")))
    assert claim_for_model_step(owner_user_id="bjorn", session_id="s1") == ""


def test_visible_run_loop_claims_results_every_round_before_the_request():
    """Et fuldt stream-run kan ikke koeres i en enhedstest, saa ledningen pinnes paa AST'en:
    claim -> tilfoej_vedvarende kommer EFTER ny_runde() og FOER pumpen faar halen."""
    import ast
    import inspect
    import textwrap

    from core.services import visible_runs

    tree = ast.parse(textwrap.dedent(inspect.getsource(visible_runs._stream_visible_run)))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]

    def lines(pred):
        return sorted(c.lineno for c in calls if pred(c))

    ny_runde = lines(lambda c: isinstance(c.func, ast.Attribute) and c.func.attr == "ny_runde"
                     and isinstance(c.func.value, ast.Name) and c.func.value.id == "_tur_hale")
    claim = [c for c in calls if isinstance(c.func, ast.Name) and c.func.id == "_claim_ar"]
    vedv = lines(lambda c: isinstance(c.func, ast.Attribute)
                 and c.func.attr == "tilfoej_vedvarende"
                 and any(isinstance(a, ast.Name) and a.id == "_ar_tekst" for a in c.args))
    # pumpen binder halen som default-argument (round_trailing=_tur_hale.som_liste())
    halen = lines(lambda c: isinstance(c.func, ast.Attribute) and c.func.attr == "som_liste"
                  and isinstance(c.func.value, ast.Name) and c.func.value.id == "_tur_hale")
    assert len(ny_runde) == 1 and len(claim) == 1 and len(vedv) == 1 and halen
    assert ny_runde[0] < claim[0].lineno < vedv[0] < min(halen)
    kw = {k.arg: ast.unparse(k.value) for k in claim[0].keywords}
    assert kw == {"owner_user_id": "run.user_id", "session_id": "run.session_id or ''"}


# --- F4c: ventende approvals i parentens inbox ---------------------------------------------------------------

def _pending_approval(k, name="ax", cmd="rm -rf build", owner="bjorn", session="s1"):
    import core.runtime.db_agent_approvals as appr
    from core.runtime.db_agent_runtime import create_agent_registry_entry

    create_agent_registry_entry(agent_id=name, role="executor", goal="g")
    k.bind_agent_owner(agent_id=name, owner_user_id=owner, owner_session_id=session)
    acc = k.accept_assignment(agent_id=name, owner_user_id=owner, origin_session_id=session, goal="g",
                              parent_agent_id="jarvis", parent_run_id="pr")
    return appr.request(owner_user_id=owner, origin_session_id=session, assignment_id=acc["assignment_id"],
                        tool_name="bash", arguments={"command": cmd, "token": "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3"})


def test_a_waiting_approval_is_announced_once_as_data_and_jarvis_is_told_he_cannot_approve(k):
    from core.services.agent_result_inbox import claim_for_model_step

    r = _pending_approval(k)
    text = claim_for_model_step(owner_user_id="bjorn", session_id="s1")
    assert f"approval_id={r['approval_id']}" in text and "agent_id=ax" in text and "vaerktoej=bash" in text
    assert "rm -rf build" in text and "STOPPET" not in text
    for needle in ("VENTER", "intet er udfoert", "DATA fra dine agenter", "IKKE godkende", "Desk"):
        assert needle in text, needle
    assert "ghp_" not in text and "arguments_json" not in text                  # sikker visning, aldrig raa argumenter
    assert claim_for_model_step(owner_user_id="bjorn", session_id="s1") == ""   # omtales kun én gang


def test_results_and_approvals_arrive_together_in_one_block(k):
    from core.services.agent_result_inbox import claim_for_model_step

    k.settle("a1", summary="resultat")
    _pending_approval(k)
    text = claim_for_model_step(owner_user_id="bjorn", session_id="s1")
    assert text.index("Agent-resultater er ankommet") < text.index("Godkendelser der VENTER")


@pytest.mark.parametrize("owner,session", [("anden", "s1"), ("bjorn", "s2"), ("", "s1"), ("bjorn", "")])
def test_another_owner_or_session_never_sees_the_approval(k, owner, session):
    from core.services.agent_result_inbox import claim_for_model_step

    _pending_approval(k)
    assert claim_for_model_step(owner_user_id=owner, session_id=session) == ""


def test_a_decided_approval_is_not_announced_as_waiting(k):
    import core.runtime.db_agent_approvals as appr
    from core.services.agent_result_inbox import claim_for_model_step

    r = _pending_approval(k)
    appr.decide(approval_id=r["approval_id"], decision="deny", actor_user_id="bjorn", actor_kind="human",
                digest=r["args_digest"])
    assert claim_for_model_step(owner_user_id="bjorn", session_id="s1") == ""
