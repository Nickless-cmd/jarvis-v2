"""Bölge 2 (privat-indre → Central): private_relation_state pulser egress-frit."""
from __future__ import annotations

import inspect

import core.memory.private_relation_state as mod


def test_module_imports():
    assert hasattr(mod, "build_private_relation_state")


def test_uses_record_private_egress_free():
    src = inspect.getsource(mod)
    assert "record_private" in src
    assert "central().observe" not in src
    assert "event_bus" not in src
    assert "_emit(" not in src


def test_inactive_and_active_contract():
    empty = mod.build_private_relation_state(
        visible_session_continuity=None,
        visible_continuity=None,
        visible_selected_work_item=None,
        private_retained_memory_projection=None,
    )
    assert empty["active"] is False
    active = mod.build_private_relation_state(
        visible_session_continuity={"latest_run_id": "run-1", "active": True},
        visible_continuity={},
        visible_selected_work_item={"selected_user_message_preview": "hi"},
        private_retained_memory_projection=None,
    )
    assert active["active"] is True
    assert active["current"]["relation_id"].startswith("private-relation-state:")
