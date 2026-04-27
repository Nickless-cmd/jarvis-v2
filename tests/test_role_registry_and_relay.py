"""Unit tests for role_registry and agent_relay."""
from __future__ import annotations

from unittest.mock import patch

from core.services.role_registry import (
    list_all_roles,
    get_role,
    register_custom_role,
)
from core.services.agent_relay import relay_message, relay_to_role


def test_list_all_roles_includes_builtin():
    with patch("core.services.role_registry._load_custom_roles", return_value=[]):
        roles = list_all_roles()
    assert "researcher" in roles
    assert "critic" in roles


def test_custom_roles_merge_on_top():
    custom = [{
        "role": "security_auditor",
        "title": "Security Auditor",
        "system_prompt": "You audit code for security issues.",
        "default_tool_policy": "read-only",
    }]
    with patch("core.services.role_registry._load_custom_roles", return_value=custom):
        roles = list_all_roles()
    assert "security_auditor" in roles
    assert roles["security_auditor"]["title"] == "Security Auditor"


def test_custom_role_can_shadow_builtin():
    custom = [{
        "role": "critic",
        "title": "Custom Critic",
        "system_prompt": "Different prompt.",
        "default_tool_policy": "read-only",
    }]
    with patch("core.services.role_registry._load_custom_roles", return_value=custom):
        roles = list_all_roles()
    assert roles["critic"]["title"] == "Custom Critic"


def test_extends_inherits_from_base():
    custom = [{
        "role": "kind_critic",
        "title": "Kind Critic",
        "extends": "critic",
        "system_prompt": "Be gentle but firm.",
    }]
    with patch("core.services.role_registry._load_custom_roles", return_value=custom):
        roles = list_all_roles()
    # Should have inherited default_tool_policy from critic
    assert "default_tool_policy" in roles["kind_critic"]


def test_get_role_returns_none_for_unknown():
    with patch("core.services.role_registry._load_custom_roles", return_value=[]):
        assert get_role("nonexistent_role") is None


def test_relay_message_validates_inputs():
    result = relay_message(from_agent_id="", to_agent_id="b", content="hi")
    assert result["status"] == "error"
    result = relay_message(from_agent_id="a", to_agent_id="", content="hi")
    assert result["status"] == "error"
    result = relay_message(from_agent_id="a", to_agent_id="b", content="")
    assert result["status"] == "error"


def test_relay_message_unknown_receiver():
    with patch("core.runtime.db.get_agent_registry_entry", return_value=None), \
         patch("core.runtime.db.create_agent_message"):
        result = relay_message(from_agent_id="a", to_agent_id="b", content="hi")
    assert result["status"] == "error"
    assert "not found" in result["error"]


def test_relay_message_success():
    fake_agent = {"agent_id": "b", "role": "researcher"}
    with patch("core.runtime.db.get_agent_registry_entry", return_value=fake_agent), \
         patch("core.runtime.db.create_agent_message") as fake_create:
        result = relay_message(from_agent_id="a", to_agent_id="b", content="findings here")
    assert result["status"] == "ok"
    assert result["delivered"] is True
    assert result["to_role"] == "researcher"
    fake_create.assert_called_once()
    args = fake_create.call_args.kwargs
    assert args["direction"] == "agent->agent"
    assert "findings here" in args["content"]


def test_relay_to_role_finds_member():
    fake_members = [
        {"agent_id": "a1", "role": "researcher"},
        {"agent_id": "a2", "role": "planner"},
    ]
    fake_agent = {"agent_id": "a2", "role": "planner"}
    with patch("core.runtime.db.list_council_members", return_value=fake_members), \
         patch("core.runtime.db.get_agent_registry_entry", return_value=fake_agent), \
         patch("core.runtime.db.create_agent_message"):
        result = relay_to_role(
            from_agent_id="a1", council_id="c1",
            role="planner", content="hi planner",
        )
    assert result["status"] == "ok"
    assert result["to_agent_id"] == "a2"


def test_relay_to_role_unknown_role():
    with patch("core.runtime.db.list_council_members", return_value=[]):
        result = relay_to_role(
            from_agent_id="a", council_id="c", role="ghost", content="hi",
        )
    assert result["status"] == "error"
