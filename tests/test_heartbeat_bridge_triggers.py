"""Integration tests: bridge posts to chat only when trigger present."""
from __future__ import annotations

from pathlib import Path

import pytest

from core.runtime import heartbeat_triggers
from core.services import heartbeat_runtime


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspaces" / "default"
    (ws / "runtime").mkdir(parents=True)
    return ws


def _base_policy(workspace: Path, ping_channel: str = "none") -> dict:
    return {
        "workspace": str(workspace),
        "ping_channel": ping_channel,
        "allow_ping": True,
        "kill_switch": "enabled",
    }


def test_propose_silent_when_channel_none_and_no_trigger(workspace: Path) -> None:
    result = heartbeat_runtime._deliver_heartbeat_proposal(
        policy=_base_policy(workspace),
        tick_id="t1",
        summary="summary",
        proposed_action="proposed text",
    )
    assert result["status"] == "recorded"
    assert result["blocked_reason"] == ""


def test_propose_posts_when_trigger_present(workspace: Path, monkeypatch) -> None:
    heartbeat_triggers.set_trigger(
        workspace, reason="project-need", source="test", text="project ping"
    )
    calls: list[dict] = []

    def fake_append(*, session_id, role, content, user_id=None, workspace_name=None):
        # Eksplicitte nøgleord, ikke **kwargs: faken er en kanariefugl for at
        # kaldet aendrer form. 2/10-2026 fangede den netop at vagten begyndte
        # at sende user_id/workspace_name videre.
        calls.append({"session_id": session_id, "role": role, "content": content,
                      "user_id": user_id, "workspace_name": workspace_name})
        return {"id": "msg-1"}

    def fake_list():
        return [{"id": "sess-1"}]

    def fake_get(sid):
        return {"id": sid}

    import core.services.chat_sessions as cs
    import core.services.session_inbox as inbox
    monkeypatch.setattr(cs, "append_chat_message", fake_append)
    monkeypatch.setattr(cs, "list_chat_sessions", fake_list)
    monkeypatch.setattr(cs, "get_chat_session", fake_get)
    # Denne test maaler den DIREKTE vej. Den forudsaetning laa implicit i at
    # testmiljoeets DB var tom; nu staar den som en paastand, saa testen ikke
    # stiltiende skifter til koe-vejen hvis miljoeet aendrer sig.
    monkeypatch.setattr(inbox, "is_session_active", lambda sid, **k: False)

    result = heartbeat_runtime._deliver_heartbeat_proposal(
        policy=_base_policy(workspace),
        tick_id="t2",
        summary="summary",
        proposed_action="real proposal text",
    )
    assert result["status"] == "sent"
    assert len(calls) == 1
    assert calls[0]["content"] == "real proposal text"
    # Trigger was consumed (queue is empty again)
    assert heartbeat_triggers.peek_trigger(workspace) is None


def test_ping_silent_when_channel_none_and_no_trigger(workspace: Path) -> None:
    result = heartbeat_runtime._deliver_heartbeat_ping_directly(
        policy=_base_policy(workspace),
        tick_id="t3",
        ping_text="a real question from Jarvis",
        summary="summary",
    )
    assert result["status"] == "recorded"


def test_ping_posts_when_trigger_present(workspace: Path, monkeypatch) -> None:
    heartbeat_triggers.set_trigger(
        workspace, reason="user-question", source="test"
    )

    def fake_append(*, session_id, role, content):
        return {"id": "msg-2"}

    import core.services.chat_sessions as cs
    monkeypatch.setattr(cs, "append_chat_message", fake_append)
    monkeypatch.setattr(cs, "list_chat_sessions", lambda: [{"id": "sess-1"}])
    monkeypatch.setattr(cs, "get_chat_session", lambda sid: {"id": sid})

    result = heartbeat_runtime._deliver_heartbeat_ping_directly(
        policy=_base_policy(workspace),
        tick_id="t4",
        ping_text="a real, non-templated question",
        summary="summary",
    )
    # Outbound nudge system (2026-05-13) routes heartbeat pings through
    # push_nudge instead of direct webchat send. The result status is
    # now "queued" (nudge added to ledger for Jarvis to surface) rather
    # than "sent" (direct write). Tested intent — "ping was delivered
    # through the canonical channel" — still holds.
    assert result["status"] in {"queued", "sent"}
    assert heartbeat_triggers.peek_trigger(workspace) is None


def test_aktiv_session_DROPPER_forslaget(workspace: Path, monkeypatch) -> None:
    """To aendringer paa to dage, og den anden afloeser den foerste.

    2/10 blev leveringen flyttet gennem daemon-vagten, saa et forslag i en aktiv
    session blev KOEET i stedet for skrevet midt i en saetning. Senere samme dag
    blev de to aktivitets-tjek slaaet sammen: funktionen havde sit EGET
    haandrullede 5-minutters-tjek der DROPPEDE forslaget, og det overlappede
    `is_session_active`. Ét tjek, og handlingen er drop.

    Hvorfor drop og ikke koe netop her: et forslag er periodisk og bliver lavet
    igen ved naeste tik. Et gammelt forslag der lander efter Bjoerns tur er
    stoej han ikke bad om, mens et friskt kommer af sig selv. Drop er strengt
    stillere, og det var hele formaalet.

    Gaelder KUN denne sti. De oevrige kilder koees som foer — det pinnes i
    test_aktiv_session_vagten.py.
    """
    heartbeat_triggers.set_trigger(
        workspace, reason="project-need", source="test", text="project ping"
    )
    direkte: list[dict] = []
    koeet: list[dict] = []

    def fake_append(*, session_id, role, content, user_id=None, workspace_name=None):
        direkte.append({"session_id": session_id, "content": content})
        return {"id": "msg-direkte"}

    def fake_enqueue(*, session_id, content, source, urgent=False,
                     user_id=None, workspace_name=None):
        koeet.append({"session_id": session_id, "source": source})
        return {"status": "queued", "id": 7}

    import core.services.chat_sessions as cs
    import core.services.session_inbox as inbox
    monkeypatch.setattr(cs, "append_chat_message", fake_append)
    monkeypatch.setattr(cs, "list_chat_sessions", lambda: [{"id": "sess-1"}])
    monkeypatch.setattr(cs, "get_chat_session", lambda sid: {"id": sid})
    monkeypatch.setattr(inbox, "is_session_active", lambda sid, **k: True)
    monkeypatch.setattr(inbox, "enqueue", fake_enqueue)

    result = heartbeat_runtime._deliver_heartbeat_proposal(
        policy=_base_policy(workspace),
        tick_id="t-aktiv",
        summary="summary",
        proposed_action="forslag der ikke maa banke paa",
    )

    assert direkte == [], f"skrev direkte i en aktiv session: {direkte}"
    assert koeet == [], f"koeede et forslag der skulle vaere droppet: {koeet}"
    assert result["status"] == "blocked"
    assert result["blocked_reason"] == "recent-session-activity", result


def test_de_to_aktivitets_tjek_er_ÉT_tjek():
    """Vagten mod at de driver fra hinanden igen.

    Det haandrullede tjek laeste sessionens beskeder, kiggede kun paa
    role="user" og havde sit eget haardkodede 5. `is_session_active` laeser
    events-tabellen, taeller enhver besked og har vinduet som konstant. To tjek
    med samme formaal og forskellig maaling er ét der kan drive.
    """
    import ast
    import pathlib as _p

    kilde = _p.Path("core/services/heartbeat_delivery.py").read_text()
    for n in ast.walk(ast.parse(kilde)):
        if isinstance(n, ast.FunctionDef) and n.name == "_deliver_heartbeat_proposal":
            tekst = ast.unparse(n)
            assert "is_session_active" in tekst, "bruger ikke det faelles tjek"
            assert "age_minutes" not in tekst, "det haandrullede tjek er tilbage"
            assert "role" not in tekst or "user_msgs" not in tekst, (
                "laeser igen sessionens beskeder selv"
            )
            return
    raise AssertionError("_deliver_heartbeat_proposal findes ikke laengere")
