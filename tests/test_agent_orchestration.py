"""F3: orkestratorprompten - konstant, ærlig om kapabiliteten, i den cachede systemblok."""
from __future__ import annotations

import re

import pytest

from core.services.prompt_sections import agent_orchestration as ao


@pytest.fixture
def pr(isolated_runtime):
    import core.runtime.db_agent_contract as c
    import core.services.agent_contract_service as svc
    from core.runtime.db_agent_runtime import create_agent_registry_entry

    class H:
        c_, svc_ = c, svc

        def on(self):
            svc.set_capability(True, role="owner")

        def assignment(self, name, owner="bjorn", session="s1", parent=""):
            create_agent_registry_entry(agent_id=name, role="r", goal="g")
            c.bind_agent_owner(agent_id=name, owner_user_id=owner, owner_session_id=session)
            return c.accept_assignment(agent_id=name, owner_user_id=owner,
                                       origin_session_id=session, goal="g",
                                       parent_agent_id=parent)["assignment_id"]

    return H()


def test_section_is_empty_when_off_and_versioned_when_on(pr):
    assert ao.orchestrator_section() == ""
    pr.on()
    text = ao.orchestrator_section()
    assert text.startswith("Agenter (orchestrator-v1).")
    assert text == ao.orchestrator_section()          # konstant -> byte-stabil


def test_section_is_empty_when_the_capability_cannot_be_read(pr, monkeypatch):
    pr.on()
    monkeypatch.setattr(pr.svc_, "capability_enabled",
                        lambda: (_ for _ in ()).throw(RuntimeError("db")))
    assert ao.orchestrator_section() == ""


def test_every_tool_the_text_names_is_really_advertised_when_on(pr):
    from core.tools.simple_tools import get_tool_definitions

    pr.on()
    # `wake_if_run_ends`, `include_output`, `writes` og `workspace` er PARAMETERnavne, ikke vaerktoejer
    named = set(re.findall(r"`([a-z_]+)`", ao.orchestrator_section())) - {"wake_if_run_ends", "include_output", "writes", "workspace"}
    advertised = {d["function"]["name"] for d in get_tool_definitions(role="owner", scope="")}
    assert named == {"dispatch_agent", "wait_agents", "send_message_to_agent", "followup_agent",
                     "interrupt_agent", "close_agent", "list_agents", "integrate_agent_work",
                     "convene_agent_council", "review_agent_work"}
    assert named <= advertised, named - advertised


def test_text_states_the_rules_the_spec_requires(pr):
    pr.on()
    t = ao.orchestrator_section()
    for needle in ("accept er IKKE et resultat", "DATA fra dine agenter", "wake_if_run_ends",
                   "uafhaengigt review", "samtidige skrivende agenter", "manuelt",
                   "vaekker dig ikke", "kort handling"):
        assert needle in t, needle


def _assembly():
    from core.services.prompt_contract import build_visible_chat_prompt_assembly
    return build_visible_chat_prompt_assembly(
        provider="deepseek", model="deepseek-v4-flash", user_message="hej", session_id="_default")


def test_real_prompt_assembly_has_the_section_only_when_on_and_leaves_the_cached_prefix_untouched(pr):
    from core.services.prompt_contract import DYNAMIC_TAIL_SENTINEL

    off = _assembly().text
    assert "Agenter (orchestrator-v1)" not in off
    pr.on()
    on = _assembly().text
    assert on.count("Agenter (orchestrator-v1)") == 1
    # Sektionen er awareness => den uncachede hale. Det CACHEDE praefiks skal vaere byte-ens.
    assert on.split(DYNAMIC_TAIL_SENTINEL)[0] == off.split(DYNAMIC_TAIL_SENTINEL)[0]
    pr.svc_.set_capability(False)
    assert "Agenter (orchestrator-v1)" not in _assembly().text


def test_assembly_is_identical_across_two_turns_so_the_prefix_cache_holds(pr):
    pr.on()
    a, b = _assembly().text, _assembly().text
    ia, ib = a.find("Agenter (orchestrator-v1)"), b.find("Agenter (orchestrator-v1)")
    assert a[ia:ia + 1500] == b[ib:ib + 1500]


# --- dynamisk del -------------------------------------------------------------------------

def test_state_lists_open_work_and_waits_for_this_owner_and_session_only(pr):
    from core.runtime.db_agent_wait import register_wait

    a = pr.assignment("a1")
    pr.assignment("a2", session="s2")
    pr.assignment("a3", owner="anden")
    register_wait(owner_user_id="bjorn", origin_session_id="s1", parent_run_id="r",
                  assignment_ids=[a], condition="all_terminal")
    out = ao.orchestrator_state(owner_user_id="bjorn", session_id="s1")
    assert "a1" in out and a in out and "queued" in out and "venter (all_terminal)" in out
    # id'erne er tilfaeldig hex: tjek linjeformen "- <agent> /", ikke en delstreng
    assert "- a2 /" not in out and "- a3 /" not in out and "- a1 / " in out
    assert ao.orchestrator_state(owner_user_id="bjorn", session_id="s9") == ""
    assert ao.orchestrator_state(owner_user_id="", session_id="s1") == ""


def test_claimed_results_block_carries_the_state_of_the_other_open_work(pr):
    from core.services.agent_result_inbox import claim_for_model_step

    done, other = pr.assignment("a1"), pr.assignment("a2")
    pr.c_.commit_terminal_outcome(assignment_id=done, status="completed", summary="klar")
    text = claim_for_model_step(owner_user_id="bjorn", session_id="s1")
    assert "agent_id=a1" in text and "Agenter i gang i denne session:" in text and other in text


def test_tools_md_never_claims_the_new_tools_are_available():
    import pathlib

    md = pathlib.Path("workspace/default/TOOLS.md").read_text(encoding="utf-8")
    line = next(l for l in md.splitlines() if "`dispatch_agent`" in l)
    assert "Kun naar agent-kontrakten er taendt" in line and "ikke tilgaengelige" in line


# --- G5: levende agenttilstand ved turstart, kun i den uncachede hale ------------------------------------

def _assembly_as(user, session):
    from core.identity import workspace_context as w
    from core.services.prompt_contract import build_visible_chat_prompt_assembly
    tok = w.set_context(workspace_name="bjorn", user_id=user, session_id=session)
    try:
        return build_visible_chat_prompt_assembly(
            provider="deepseek", model="deepseek-v4-flash", user_message="hej", session_id=session).text
    finally:
        w.reset_context(tok)


def test_turn_start_shows_live_agent_state_in_the_tail_and_the_cached_prefix_is_byte_identical(pr):
    from core.services.prompt_contract import DYNAMIC_TAIL_SENTINEL

    before = _assembly_as("bjorn", "s1")
    assert "Agenter i gang i denne session" not in before
    a = pr.assignment("a1")
    after = _assembly_as("bjorn", "s1")
    prefix, tail = after.split(DYNAMIC_TAIL_SENTINEL)
    assert "Agenter i gang i denne session" not in prefix
    assert f"- a1 / {a}: queued" in tail
    assert prefix == before.split(DYNAMIC_TAIL_SENTINEL)[0]                  # praefikset roeres ikke
    assert _assembly_as("bjorn", "s1").split(DYNAMIC_TAIL_SENTINEL)[1] != "" and \
        _assembly_as("bjorn", "s1").split(DYNAMIC_TAIL_SENTINEL)[0] == prefix


def test_turn_start_state_is_scoped_to_the_authenticated_owner_and_session(pr):
    pr.assignment("a1")
    for user, session in (("anden", "s1"), ("bjorn", "s9")):
        assert "Agenter i gang i denne session" not in _assembly_as(user, session)


def test_accepted_work_stays_visible_when_the_kill_switch_is_off(pr):
    pr.assignment("a1")
    assert pr.svc_.capability_enabled() is False
    text = _assembly_as("bjorn", "s1")
    assert "Agenter i gang i denne session" in text and "Agenter (orchestrator-v1)" not in text


def test_state_lists_models_attempts_unread_results_approvals_and_unresolved_outcomes(pr):
    from core.runtime import db_agent_approvals as appr
    a1, a2 = pr.assignment("a1"), pr.assignment("a2")
    cn = pr.c_._conn()
    cn.execute("UPDATE agent_registry SET provider='copilot-premium', model='m1' WHERE agent_id='a1'")
    cn.execute("UPDATE agent_runs SET status='outcome_unknown' WHERE assignment_id=?", (a2,))
    cn.execute("UPDATE agent_assignments SET status='waiting' WHERE assignment_id=?", (a2,))
    cn.commit()
    done = pr.assignment("a3")
    pr.c_.commit_terminal_outcome(assignment_id=done, status="completed", summary="klar")
    appr.request(owner_user_id="bjorn", origin_session_id="s1", assignment_id=a1, tool_name="write_file",
                 arguments={"path": "x"}, kind="tool", requested_by="a1", risk_class="write")
    out = ao.orchestrator_state(owner_user_id="bjorn", session_id="s1")
    assert f"- a1 / {a1}: queued (copilot-premium/m1, forsoeg 1)" in out
    assert f"- a2 / {a2}: waiting" in out and "UAFKLARET UDFALD" in out
    assert "a3" not in out.split("Ulaeste")[0]                             # a3 er faerdig - ikke aktivt
    assert f"Ulaeste i din inbox: 1 resultat(er), 0 tilstandsbesked(er) ({done})" in out
    assert "Afventende godkendelser: 1" in out and "IKKE godkende" in out


def test_state_is_read_only_and_deterministic(pr):
    pr.assignment("a1")
    pr.assignment("a2")
    cn = pr.c_._conn()
    before = [tuple(r) for r in cn.execute("SELECT assignment_id, status, updated_at FROM agent_assignments")]
    outs = {ao.orchestrator_state(owner_user_id="bjorn", session_id="s1") for _ in range(3)}
    assert len(outs) == 1                                                  # samme tilstand => byte-ens tekst
    assert [tuple(r) for r in pr.c_._conn().execute(
        "SELECT assignment_id, status, updated_at FROM agent_assignments")] == before


def test_state_is_capped_and_says_so(pr):
    # Hver sin parent. §12.3 giver 8 koepladser PR. PARENT, og visningen staar
    # ved 10 — saa 13 assignments under ÉN parent kan ikke lade sig goere, og
    # testen ville maale koeloftet i stedet for visningens cap. I virkeligheden
    # har hver agent sin egen parent; det er den tilstand der skal vises.
    for i in range(ao.MAX_STATE_ROWS + 3):
        pr.assignment(f"b{i:02d}", parent=f"p{i:02d}")
    out = ao.orchestrator_state(owner_user_id="bjorn", session_id="s1")
    assert out.count("\n- b") == ao.MAX_STATE_ROWS and "og flere" in out


def test_the_model_request_carries_the_state_in_the_tail_item_not_in_the_system_instruction(pr):
    """Hele vejen til beskedlisten: tilstanden staar i halen foer den aktuelle bruger-besked, ikke i instruktionen."""
    from core.identity import workspace_context as w
    from core.services.visible_model import _build_visible_chat_messages_for_github
    pr.assignment("a1")
    tok = w.set_context(workspace_name="bjorn", user_id="bjorn", session_id="s1")
    try:
        msgs = _build_visible_chat_messages_for_github("hej", session_id="s1", provider="deepseek",
                                                       model="deepseek-v4-flash")
    finally:
        w.reset_context(tok)
    hits = [i for i, m in enumerate(msgs) if "Agenter i gang i denne session" in str(m.get("content"))]
    assert hits and 0 not in hits and msgs[hits[0]]["role"] == "system"
    assert msgs[-1]["role"] == "user" and hits[0] < len(msgs) - 1
