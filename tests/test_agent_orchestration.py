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

        def assignment(self, name, owner="bjorn", session="s1"):
            create_agent_registry_entry(agent_id=name, role="r", goal="g")
            c.bind_agent_owner(agent_id=name, owner_user_id=owner, owner_session_id=session)
            return c.accept_assignment(agent_id=name, owner_user_id=owner,
                                       origin_session_id=session, goal="g")["assignment_id"]

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
    # `wake_if_run_ends` er et PARAMETERnavn, ikke et vaerktoej
    named = set(re.findall(r"`([a-z_]+)`", ao.orchestrator_section())) - {"wake_if_run_ends"}
    advertised = {d["function"]["name"] for d in get_tool_definitions(role="owner", scope="")}
    assert named == {"dispatch_agent", "wait_agents", "send_message_to_agent", "followup_agent",
                     "interrupt_agent", "close_agent", "list_agents"}
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
    assert "a2" not in out and "a3" not in out
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
