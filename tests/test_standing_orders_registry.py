"""Tests for standing_orders_registry.py — TDD first pass."""
from __future__ import annotations

from core.services import standing_orders_registry as sor


def test_add_and_list_active(isolated_runtime):
    sor.add_standing_order(text="Verify a number with a tool before stating it", match_key="claim")
    active = sor.list_active_standing_orders()
    assert any(o["match_key"] == "claim" for o in active)


def test_deactivate_hides_order(isolated_runtime):
    oid = sor.add_standing_order(text="Never overwrite USER.md", match_key="user_md")
    sor.set_standing_order_active(oid, active=False)
    assert all(o["id"] != oid for o in sor.list_active_standing_orders())


def test_list_is_self_safe_on_missing_table(monkeypatch):
    monkeypatch.setattr(sor, "connect", lambda: (_ for _ in ()).throw(RuntimeError("db down")))
    assert sor.list_active_standing_orders() == []
