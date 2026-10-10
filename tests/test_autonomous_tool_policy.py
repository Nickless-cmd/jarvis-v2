from __future__ import annotations

from core.services.run_autonomy_context import reset_autonomous, set_autonomous


def test_autonomous_catalog_hides_agent_and_dispatch_tools():
    from core.tools.simple_tools import get_tool_definitions

    token = set_autonomous(True)
    try:
        names = {d["function"]["name"] for d in get_tool_definitions(role="owner", scope="")}
    finally:
        reset_autonomous(token)

    assert {"read_file", "search_memory", "remember_this", "goal_create", "todo_add"} <= names
    assert "scout_agent" not in names
    assert "spawn_agent_task" not in names
    assert "dispatch_code_mode_task" not in names
    assert "dispatch_agent" not in names
    assert not any("agent" in name or "dispatch" in name for name in names)
    assert {"bash", "write_file", "operator_bash", "send_ntfy", "mcp", "start_session",
            "web_fetch", "web_search", "schedule_task", "read_archive"}.isdisjoint(names)


def test_autonomous_loaded_tool_cannot_resolve_agent_schema():
    from core.tools.load_more_tools import _tool_load_more_tools

    token = set_autonomous(True)
    try:
        result = _tool_load_more_tools({"names": ["scout_agent"]})
    finally:
        reset_autonomous(token)

    assert result["status"] == "error"
    assert not result.get("tool_definitions")


def test_autonomous_executor_blocks_direct_and_wrapped_agent_calls(monkeypatch):
    from core.services.simple_tool_executor import _prepare_call

    calls = [
        {"function": {"name": "dispatch_agent", "arguments": {}}},
        {"function": {"name": "call_loaded_tool", "arguments": {
            "navn": "scout_agent", "argumenter": {},
        }}},
        {"function": {"name": "bash", "arguments": {"command": "true"}}},
    ]
    token = set_autonomous(True)
    try:
        for call in calls:
            kind, result = _prepare_call(
                call, force=True, run_id="autonomous-test", session_id="auto-test",
                user_message="", controller=None, round_seen=set(), user_present=False,
            )
            assert kind == "result"
            assert result["status"] == "gate_blocked"
            assert result["result"]["gate_type"] == "autonomous_tool_policy"
    finally:
        reset_autonomous(token)


def test_visible_run_keeps_agent_tools():
    from core.tools.simple_tools import get_tool_definitions

    token = set_autonomous(False)
    try:
        names = {d["function"]["name"] for d in get_tool_definitions(role="owner", scope="")}
    finally:
        reset_autonomous(token)

    assert "scout_agent" in names
    assert "dispatch_code_mode_task" in names


def test_owner_permission_check_cannot_bypass_autonomous_policy():
    from core.tools.tool_scoping import is_tool_allowed

    token = set_autonomous(True)
    try:
        assert is_tool_allowed(role="owner", scope="", name="scout_agent") is False
        assert is_tool_allowed(role="owner", scope="", name="remember_this") is True
    finally:
        reset_autonomous(token)


# ── Delegeret tilladelse pr. oprindelse (10/10-2026) ─────────────────────
#
# Bjørn: «uddelegér tools når du sætter autonome runs og recurring op, så
# autonome runs får kun de tools de behøver». Testene låser at tilladelsen
# følger ORIGIN — og at en ukendt oprindelse aldrig arver en udvidelse.

def _as_origin(origin: str):
    """Sæt autonom-flag + origin; returnér token til oprydning."""
    from core.services.run_autonomy_context import set_run_identity

    token = set_autonomous(True)
    set_run_identity("autonomous-test", origin)
    return token


def _clear_origin() -> None:
    from core.services.run_autonomy_context import set_run_identity

    set_run_identity("", "")


def test_recurring_task_may_send_and_read_runtime():
    from core.tools.autonomous_tool_policy import is_allowed

    token = _as_origin("recurring")
    try:
        assert is_allowed("send_ntfy") is True
        assert is_allowed("send_discord_dm") is True
        assert is_allowed("web_search") is True
        assert is_allowed("bash") is True
    finally:
        reset_autonomous(token)
        _clear_origin()


def test_unknown_origin_falls_back_to_bundle_alone():
    from core.tools.autonomous_tool_policy import is_allowed

    token = _as_origin("")
    try:
        assert is_allowed("remember_this") is True
        assert is_allowed("send_ntfy") is False
        assert is_allowed("bash") is False
    finally:
        reset_autonomous(token)
        _clear_origin()


def test_dream_senses_but_does_not_touch_the_world():
    from core.tools.autonomous_tool_policy import is_allowed

    token = _as_origin("dream")
    try:
        assert is_allowed("look_around") is True
        assert is_allowed("mic_listen") is True
        assert is_allowed("bash") is False
        assert is_allowed("send_ntfy") is False
    finally:
        reset_autonomous(token)
        _clear_origin()


def test_wakeup_may_resume_work_but_not_send_mail():
    from core.tools.autonomous_tool_policy import is_allowed

    token = _as_origin("wakeup")
    try:
        assert is_allowed("bash") is True
        assert is_allowed("send_webchat_message") is True
        assert is_allowed("write_file") is False
        assert is_allowed("send_discord_dm") is False
    finally:
        reset_autonomous(token)
        _clear_origin()


def test_visible_run_ignores_origin_grants():
    from core.tools.autonomous_tool_policy import is_allowed

    token = set_autonomous(False)
    try:
        assert is_allowed("bash") is True
        assert is_allowed("send_discord_dm") is True
    finally:
        reset_autonomous(token)
        _clear_origin()
