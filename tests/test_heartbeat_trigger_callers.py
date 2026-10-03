"""Tests for de tre tidligere trigger-kaldere: aesthetic, self-review og
queue_followup-vaerktoejet.

3/10-2026: alle tre skrev til `HEARTBEAT_TRIGGERS.json`, som er skrive-only —
1.726 poster, intet fjernet i 160 dage. Ingen af dem skriver til koeen mere;
de gaar gennem `notification_bridge`. Filen laaser begge sider af den flytning:
koeen skal staa TOM, og beskeden skal faktisk afsted."""
from __future__ import annotations

from pathlib import Path

import pytest

from core.runtime import heartbeat_triggers


@pytest.fixture
def fake_workspace(tmp_path: Path, monkeypatch) -> Path:
    ws = tmp_path / "workspaces" / "default"
    (ws / "runtime").mkdir(parents=True)
    monkeypatch.setattr(
        "core.identity.workspace_bootstrap.ensure_default_workspace",
        lambda name="default": ws,
    )
    return ws


def test_default_workspace_wrapper_resolves_and_sets(fake_workspace: Path) -> None:
    entry = heartbeat_triggers.set_trigger_for_default_workspace(
        reason="test", source="unit", text="hello"
    )
    assert entry is not None
    assert entry["reason"] == "test"
    assert heartbeat_triggers.peek_trigger(fake_workspace)["reason"] == "test"


def test_aesthetic_insight_koeer_ikke_paa_trigger_koeen(fake_workspace: Path, monkeypatch) -> None:
    """3/10-2026: daemonen skrev til heartbeat-trigger-koeen, som aldrig
    toemmes — 1.721 af 1.726 poster var dens, og ingen laeste dem. Indsigten
    har sin egen kanal (`private_brain_records`), saa koeen skal staa tom."""
    # Stub the DB write and event bus so _store_insight runs cleanly in isolation
    import core.services.aesthetic_taste_daemon as daemon

    gemt: list = []
    monkeypatch.setattr(daemon, "insert_private_brain_record", lambda **kw: gemt.append(kw))
    monkeypatch.setattr(daemon.event_bus, "publish", lambda *a, **kw: None)

    daemon._store_insight("Jeg trækkes mod klarhed og ro.")

    assert heartbeat_triggers.peek_trigger(fake_workspace) is None
    assert gemt, "indsigten skal stadig skrives til private_brain"


@pytest.fixture
def self_review_stubs(monkeypatch) -> list:
    """Stubber DB-laget i self_review_run_tracking, saa
    `_persist_self_review_runs` kan kaldes uden en database.

    Returnerer listen af beskeder der blev sendt — saa testen ser hvad der
    FAKTISK gik ud, ikke bare hvad der ikke blev lagt i koeen.
    """
    import core.services.self_review_run_tracking as sr
    from core.services import notification_bridge

    sendt: list = []
    monkeypatch.setattr(sr.event_bus, "publish", lambda *a, **kw: None)
    monkeypatch.setattr(sr, "list_runtime_self_review_runs", lambda limit=40: [])
    monkeypatch.setattr(
        sr, "supersede_runtime_self_review_runs_for_domain", lambda **kw: 0
    )

    def _upsert(**kw):
        return {
            "run_id": kw.get("run_id"),
            "canonical_key": kw.get("canonical_key"),
            "summary": kw.get("summary"),
            "confidence": kw.get("confidence"),
            "was_created": True,
            "was_updated": False,
        }

    monkeypatch.setattr(sr, "upsert_runtime_self_review_run", _upsert)

    def _send(content, *, source="", push=True, **_kw):
        sendt.append({"source": source, "text": content, "push": push})
        return {"status": "ok"}

    monkeypatch.setattr(notification_bridge, "send_session_notification", _send)
    return sendt


def _self_review_run(*, confidence: str) -> dict:
    return {
        "canonical_key": "self-review-run:drift:tool-execution",
        "domain_key": "tool-execution",
        "run_type": "self-review-run",
        "status": "fresh",
        "title": "Self-review snapshot: Tool execution",
        "summary": "Critical drift detected in tool execution",
        "confidence": confidence,
    }


def test_self_review_hoej_confidence_gaar_til_notification_bridge(
    fake_workspace: Path, self_review_stubs: list
) -> None:
    """3/10-2026: samme fejlklasse som aesthetic-daemonen og vagtposterne.

    Ved `confidence == "high"` skrev tracking til heartbeat-trigger-koeen, som
    aldrig toemmes — de fire `self-review-incident`-poster der laa i koeen var
    fra maj og naaede aldrig frem. Udgangen er nu `notification_bridge`.
    """
    import core.services.self_review_run_tracking as sr

    sr._persist_self_review_runs(
        runs=[_self_review_run(confidence="high")],
        session_id="s-1",
        run_id="run-1",
    )

    assert heartbeat_triggers.peek_trigger(fake_workspace) is None, (
        "tracking maa ikke laegge i trigger-koeen — den toemmes aldrig"
    )
    assert len(self_review_stubs) == 1
    assert self_review_stubs[0]["source"] == "self-review-run-tracking"
    assert "drift" in self_review_stubs[0]["text"]
    assert self_review_stubs[0]["push"] is False


def test_self_review_lav_confidence_sender_intet(
    fake_workspace: Path, self_review_stubs: list
) -> None:
    """Kun high-confidence skal ud. Med den nye udgang betyder det: ingen
    besked overhovedet — ikke bare «ikke i koeen»."""
    import core.services.self_review_run_tracking as sr

    sr._persist_self_review_runs(
        runs=[_self_review_run(confidence="low")],
        session_id="s-1",
        run_id="run-1",
    )

    assert self_review_stubs == []
    assert heartbeat_triggers.peek_trigger(fake_workspace) is None


def test_queue_followup_gaar_gennem_notification_bridge(
    fake_workspace: Path, monkeypatch
) -> None:
    """3/10-2026: vaerktoejet skrev til trigger-koeen, som aldrig toemmes — det
    lovede «kom tilbage ved naeste tick» og leverede ingenting. Maalt samme
    dag stod en besked lagt her nummer 1.725 af 1.726 poster.

    Det gaar nu gennem `notification_bridge`, den vej der faktisk leverer (og
    som har daemon-vagt: koeer ved aktiv session, flusher efter turen).
    """
    from core.services import notification_bridge
    from core.tools import simple_tools

    sendt: list = []

    def _send(content, *, source="", push=True, **_kw):
        sendt.append({"source": source, "text": content})
        return {"status": "ok", "message": {"id": "msg-test"}}

    monkeypatch.setattr(notification_bridge, "send_session_notification", _send)

    result = simple_tools._exec_queue_followup({
        "reason": "follow-up",
        "text": "Jeg kommer tilbage om dit spørgsmål om X i morgen.",
    })
    assert result["status"] == "queued"
    assert result["reason"] == "follow-up"
    assert len(sendt) == 1
    assert sendt[0]["source"] == "jarvis-self-followup"
    assert "X i morgen" in sendt[0]["text"]

    assert heartbeat_triggers.peek_trigger(fake_workspace) is None, (
        "vaerktoejet maa ikke laegge i trigger-koeen — den toemmes aldrig"
    )


def test_queue_followup_tool_rejects_empty(fake_workspace: Path) -> None:
    from core.tools import simple_tools

    assert simple_tools._exec_queue_followup({"reason": "", "text": "a"})["status"] == "error"
    assert simple_tools._exec_queue_followup({"reason": "x", "text": ""})["status"] == "error"


def test_queue_followup_tool_rejects_oversize(fake_workspace: Path) -> None:
    from core.tools import simple_tools

    result = simple_tools._exec_queue_followup({
        "reason": "follow-up",
        "text": "x" * 2001,
    })
    assert result["status"] == "error"
    assert "2000" in result["error"]


def test_queue_followup_registered_in_handler_registry() -> None:
    from core.tools import simple_tools

    assert "queue_followup" in simple_tools._TOOL_HANDLERS
    names = {
        t["function"]["name"] for t in simple_tools.TOOL_DEFINITIONS
        if t.get("type") == "function"
    }
    assert "queue_followup" in names
