"""Tests for app_dispatch_store (§18.5 Fase 2 — runtime→app instruktions-kø)."""
from __future__ import annotations


def _instr(action="notify", target="bjorn", channel="discord", text="hej"):
    return {
        "action": action, "target_user": target, "channel": channel,
        "payload": {"text": text}, "requester": "jarvis",
    }


def test_enqueue_and_list(isolated_runtime) -> None:
    from core.services.app_dispatch_store import enqueue, list_pending
    rec = enqueue(_instr())
    assert rec["status"] == "pending"
    assert rec["id"]
    pend = list_pending()
    assert len(pend) == 1
    assert pend[0]["action"] == "notify"
    assert pend[0]["payload"]["text"] == "hej"


def test_enqueue_invalid_action_rejected(isolated_runtime) -> None:
    from core.services.app_dispatch_store import enqueue, list_pending
    rec = enqueue(_instr(action="rm_rf"))
    assert rec is None
    assert list_pending() == []


def test_enqueue_missing_target_rejected(isolated_runtime) -> None:
    from core.services.app_dispatch_store import enqueue
    assert enqueue(_instr(target="")) is None


def test_ack_removes_from_pending(isolated_runtime) -> None:
    from core.services.app_dispatch_store import enqueue, ack, list_pending
    rec = enqueue(_instr())
    assert ack(rec["id"]) is True
    assert list_pending() == []


def test_ack_unknown_false(isolated_runtime) -> None:
    from core.services.app_dispatch_store import ack
    assert ack("nope") is False


def test_multiple_pending_preserve_order(isolated_runtime) -> None:
    from core.services.app_dispatch_store import enqueue, list_pending
    a = enqueue(_instr(text="en"))
    b = enqueue(_instr(text="to"))
    ids = [r["id"] for r in list_pending()]
    assert ids == [a["id"], b["id"]]
