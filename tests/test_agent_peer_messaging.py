"""Peer-kanalen: drain-cursor (DB), agent->agent med træ-værn, peer-id'er i prompten."""
from __future__ import annotations

import pytest

O, S, R = "bjorn", "sess-1", "visible-p"


@pytest.fixture
def sv(isolated_runtime, monkeypatch):
    import core.services.agent_contract_service as svc
    from core.services import agent_runtime_spawn as M
    svc.set_capability(True, role="owner")
    monkeypatch.setattr(svc, "_run_in_background", lambda fn: None)

    def d(parent_run_id=R, goal="find X"):
        out = svc.dispatch_agent(owner_user_id=O, origin_session_id=S, goal=goal,
                                 parent_run_id=parent_run_id)
        assert out["status"] == "accepted", out
        return out["agent_id"]

    class H:
        svc_, dispatch = svc, staticmethod(d)
    return H()


def _send(h, frm, to, content="modstrid i api.py"):
    return h.svc_.send_agent_to_agent(owner_user_id=O, origin_session_id=S,
                                      sender_agent_id=frm, agent_id=to, content=content)


def test_siblings_can_write_each_other_as_agent_to_agent(sv):
    a, b = sv.dispatch(goal="del 1"), sv.dispatch(goal="del 2")
    out = _send(sv, a, b)
    assert out["status"] == "accepted" and out["peer_agent_id"] == a
    from core.runtime.db_agent_runtime import list_agent_messages
    row = [m for m in list_agent_messages(agent_id=b) if m["kind"] == "agent-message"][0]
    assert row["direction"] == "agent->agent" and row["peer_agent_id"] == a


def test_an_agent_outside_the_tree_is_refused_and_nothing_is_written(sv):
    a, outsider = sv.dispatch(), sv.dispatch(parent_run_id="visible-other")
    out = _send(sv, a, outsider)
    assert out["status"] == "error" and out["code"] == "POLICY_DENIED"
    from core.runtime.db_agent_runtime import list_agent_messages
    assert not [m for m in list_agent_messages(agent_id=outsider) if m["kind"] == "agent-message"]


def test_self_send_and_unknown_target_are_refused(sv):
    a = sv.dispatch()
    assert _send(sv, a, a)["code"] == "INVALID_SCOPE"
    assert _send(sv, a, "agent-findes-ikke")["code"] == "INVALID_SCOPE"


def test_a_lone_agent_has_no_peers(sv):
    a = sv.dispatch()
    assert sv.svc_.peer_agent_ids(a, O) == []
    b = sv.dispatch()
    assert sv.svc_.peer_agent_ids(a, O) == [b]


def test_inbox_drain_cursor_skips_history_labels_sender_and_never_repeats(sv):
    a, b = sv.dispatch(), sv.dispatch()
    from core.runtime.db_agent_runtime import create_agent_message
    drain = sv.svc_.make_inbox_drain(b)
    assert drain() == []                                  # task-brief fra spawn læses ikke igen
    _send(sv, a, b, "grænsefladen hedder X")
    create_agent_message(message_id="m-j", thread_id=f"agent-thread-{b}", agent_id=b,
                         direction="jarvis->agent", role="user", kind="parent-message",
                         content="[jarvis]\nret kursen")
    first = drain()
    assert f"[fra {a}] grænsefladen hedder X" in first
    assert "[fra jarvis] ret kursen" in first and len(first) == 2
    assert drain() == []                                  # ingen gentagelse
    _send(sv, a, b, "en ny")
    assert drain() == [f"[fra {a}] en ny"]


def test_prompt_lists_peer_ids_and_the_strict_rule(sv):
    a, b = sv.dispatch(), sv.dispatch()
    from core.runtime.db_agent_runtime import get_agent_registry_entry
    from core.services.agent_prompt_layers import build_layered_prompt
    ly = build_layered_prompt(agent=get_agent_registry_entry(a), messages_text="", execution_mode="x")
    assert b in ly["text"] and "KUN naar du har noget" in ly["text"]
    lone = sv.dispatch(parent_run_id="visible-alene")
    ly2 = build_layered_prompt(agent=get_agent_registry_entry(lone), messages_text="", execution_mode="x")
    # 22/11-2026: reglen er UBETINGET — kun navnene er dynamiske. Foer blev hele blokken
    # udeladt for en agent uden peers ved start, og saa kendte hun hverken vaerktoejet
    # eller sin ret til at svare paa en besked hun godt kunne modtage (et team oprettes
    # spredt: op til 708 s mellem foerste og sidste soeskende).
    assert "send_message_to_agent" in ly2["text"], "kanalen skal vaere naevnt ogsaa for en ensom agent"
    assert "alene" in ly2["text"].lower(), ly2["text"]
    assert b not in ly2["text"], "en ensom agent maa ikke faa en fremmed soesters id"
