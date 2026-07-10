from __future__ import annotations
from core.tools import ui_panel_tools as u


def test_open_confirmed_when_desk_acks(isolated_runtime, monkeypatch):
    # Simulér at desk allerede har ack'et (status 'opened').
    monkeypatch.setattr(u, "get_request_status", lambda rid: "opened")
    r = u._exec_open_ui_panel({"panel": "file_tree", "detail": "core/x.py"})
    assert r["status"] == "ok" and r["confirmed"] is True
    assert r["panel"] == "file_tree"


def test_open_unconfirmed_on_timeout(isolated_runtime, monkeypatch):
    # Ingen ack → efter (kort) timeout: ÆRLIG unconfirmed, ikke blind "ok".
    monkeypatch.setattr(u, "get_request_status", lambda rid: "pending")
    monkeypatch.setattr(u, "_ACK_TIMEOUT_S", 0.15)
    monkeypatch.setattr(u, "_ACK_POLL_S", 0.05)
    r = u._exec_open_ui_panel({"panel": "preview", "detail": "docs/x.md"})
    assert r["status"] == "unconfirmed" and r["confirmed"] is False
    assert "IKKE bekræftet" in r["note"]


def test_close_still_returns_signal(isolated_runtime):
    r = u._exec_open_ui_panel({"panel": "right", "action": "close"})
    assert r["status"] == "ok" and r["action"] == "close"
