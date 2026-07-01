"""Tests for cross-proces bro-tilstedeværelse (bridge_presence) — lukker blindzonen hvor
en proces ikke kunne se om/hvor der findes en levende desk-bro."""
from __future__ import annotations

from core.services import bridge_presence as bp


def test_publish_then_read_roundtrip(isolated_runtime, monkeypatch):
    monkeypatch.setenv("JARVIS_ENABLE_RUNTIME_SERVICES", "0")  # vi ER api
    bp.publish({"owner-1": {"client": "jarvis-desk", "platform": "linux", "capabilities": ["operator_bash"]}})
    presence = bp.all_presence()
    assert "owner-1" in presence
    assert presence["owner-1"]["process"] == "api"
    assert presence["owner-1"]["client"] == "jarvis-desk"


def test_process_for_user(isolated_runtime, monkeypatch):
    monkeypatch.setenv("JARVIS_ENABLE_RUNTIME_SERVICES", "0")
    bp.publish({"owner-1": {"client": "desk"}})
    assert bp.process_for_user("owner-1") == "api"
    assert bp.process_for_user("nobody") is None


def test_empty_when_no_presence(isolated_runtime):
    assert bp.all_presence() == {}
    assert bp.process_for_user("anyone") is None
