"""Tests for core.tools.decisions_tools — decision_update surface.

The tool layer validates/translates args, then delegates to the
behavioral_decisions service. Service is monkeypatched here; the store
logic itself is covered in test_db_decisions.py.
"""
from __future__ import annotations

from core.tools.decisions_tools import (
    DECISION_TOOL_HANDLERS,
    _exec_decision_update,
)


def _patch_service(monkeypatch, result=None):
    """Point the module's service reference at a fake update fn."""
    import core.tools.decisions_tools as mod
    import core.services.behavioral_decisions as svc

    calls = {}

    def fake_update(decision_id, **fields):
        calls["decision_id"] = decision_id
        calls["fields"] = fields
        if result is None:
            return None
        return {**result, "decision_id": decision_id, **fields}

    monkeypatch.setattr(svc, "update_decision", fake_update)
    # decisions_tools holds a module ref, not a copied function:
    monkeypatch.setattr(mod.behavioral_decisions, "update_decision", fake_update)
    return calls


def test_update_requires_decision_id(monkeypatch):
    res = _exec_decision_update({})
    assert res["status"] == "error"
    assert "decision_id" in res["error"]


def test_update_nothing_to_update(monkeypatch):
    calls = _patch_service(monkeypatch)
    res = _exec_decision_update({"decision_id": "dec-1"})
    assert res["status"] == "error"
    assert "nothing to update" in res["error"]
    assert "decision_id" not in calls  # service never called


def test_update_directive_and_priority(monkeypatch):
    calls = _patch_service(monkeypatch, result={"directive": "old", "priority": 50})
    res = _exec_decision_update(
        {"decision_id": "dec-1", "directive": "New rule.", "priority": 88}
    )
    assert res["status"] == "ok"
    assert calls["decision_id"] == "dec-1"
    assert calls["fields"]["directive"] == "New rule."
    assert calls["fields"]["priority"] == 88


def test_update_clears_rationale_when_none(monkeypatch):
    calls = _patch_service(monkeypatch, result={})
    res = _exec_decision_update({"decision_id": "dec-1", "rationale": None})
    assert res["status"] == "ok"
    assert calls["fields"]["rationale"] == ""  # "" = clear at store layer


def test_update_rejects_empty_directive(monkeypatch):
    res = _exec_decision_update({"decision_id": "dec-1", "directive": "   "})
    assert res["status"] == "error"
    assert "cannot be empty" in res["error"]


def test_update_rejects_bad_priority(monkeypatch):
    res = _exec_decision_update({"decision_id": "dec-1", "priority": "high"})
    assert res["status"] == "error"
    assert "integer" in res["error"]


def test_update_unknown_id_returns_error(monkeypatch):
    _patch_service(monkeypatch, result=None)
    res = _exec_decision_update({"decision_id": "dec-missing", "priority": 70})
    assert res["status"] == "error"
    assert "not found" in res["error"]


def test_handler_registered():
    assert "decision_update" in DECISION_TOOL_HANDLERS
    assert callable(DECISION_TOOL_HANDLERS["decision_update"])
