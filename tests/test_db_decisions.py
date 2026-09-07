"""Tests for core.runtime.db_decisions — focus on update_decision.

update_decision semantics (2026-09-07):
- None  → field unchanged
- ""    → field cleared to NULL (rationale/trigger_cue/trigger_name)
- value → field set

Uses a throwaway sqlite DB via monkeypatched connect — never the live DB.
"""
from __future__ import annotations

import sqlite3

import pytest


@pytest.fixture()
def tmp_db(monkeypatch, tmp_path):
    """Point db_decisions.connect at a fresh temp database."""
    from core.runtime import db_decisions as mod

    db_path = tmp_path / "decisions-test.db"
    monkeypatch.setattr(mod, "connect", lambda: _connect_row(str(db_path)))

    # ensure tables once through the module's own code path
    conn = sqlite3.connect(str(db_path))
    mod._ensure_tables(conn)
    conn.close()
    return mod


def _connect_row(db_path):
    """Production connect() sets row_factory=sqlite3.Row — mirror that."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _mk(tmp_db, **over):
    """Create a baseline decision row via the store's create path."""
    params = {
        "directive": "Pause before replying when unsure.",
        "rationale": "Cutting people off costs trust.",
        "trigger_cue": "when a message feels urgent",
        "priority": 60,
    }
    params.update(over)
    return tmp_db.create_decision(**params)


def test_update_directive_and_priority(tmp_db):
    d = _mk(tmp_db)
    did = d["decision_id"]

    u = tmp_db.update_decision(did, directive="New sharper rule.", priority=90)

    assert u["directive"] == "New sharper rule."
    assert u["priority"] == 90
    # untouched fields survive
    assert u["rationale"] == "Cutting people off costs trust."
    assert u["status"] == "active"
    assert u["updated_at"] >= d["updated_at"]


def test_update_clears_optional_fields_with_empty_string(tmp_db):
    d = _mk(tmp_db)
    did = d["decision_id"]

    u = tmp_db.update_decision(did, trigger_cue="", rationale="")

    assert u["trigger_cue"] is None
    assert u["rationale"] is None


def test_update_keeps_field_when_none_passed(tmp_db):
    d = _mk(tmp_db, trigger_cue="when X")
    did = d["decision_id"]

    u = tmp_db.update_decision(did, priority=80)  # trigger_cue not passed

    assert u["trigger_cue"] == "when X"
    assert u["priority"] == 80


def test_update_status(tmp_db):
    d = _mk(tmp_db)
    did = d["decision_id"]

    u = tmp_db.update_decision(did, status="fulfilled")

    assert u["status"] == "fulfilled"


def test_update_rejects_invalid_status(tmp_db):
    d = _mk(tmp_db)
    did = d["decision_id"]

    u = tmp_db.update_decision(did, status="not-a-status")

    assert u is None
    # unchanged in db
    assert tmp_db.get_decision(did)["status"] == "active"


def test_update_unknown_id_returns_none(tmp_db):
    assert tmp_db.update_decision("dec-unknown", directive="x") is None


def test_update_nothing_to_change_returns_row_unchanged(tmp_db):
    d = _mk(tmp_db)
    did = d["decision_id"]

    u = tmp_db.update_decision(did)

    assert u is not None
    assert u["decision_id"] == did
    assert u["directive"] == d["directive"]
