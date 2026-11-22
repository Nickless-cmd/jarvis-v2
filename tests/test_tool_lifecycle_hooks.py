from __future__ import annotations

from core.services import tool_lifecycle_hooks as hooks


def setup_function() -> None:
    hooks.clear_hooks()
    hooks.set_enabled(False)


def teardown_function() -> None:
    hooks.clear_hooks()
    hooks.set_enabled(False)


def test_hooks_are_disabled_by_default() -> None:
    seen: list[str] = []

    class Hook:
        def before_tool(self, tool_name, arguments):
            seen.append(f"before:{tool_name}")

        def after_tool(self, tool_name, arguments, result):
            seen.append(f"after:{tool_name}")

    hooks.register_hook(Hook())
    result = hooks.execute_with_hooks("demo", {"x": 1}, lambda: {"status": "ok"})

    assert result == {"status": "ok"}
    assert seen == []


def test_hook_observes_before_and_after() -> None:
    seen: list[tuple] = []

    class Hook:
        def before_tool(self, tool_name, arguments):
            seen.append(("before", tool_name, arguments.copy()))

        def after_tool(self, tool_name, arguments, result):
            seen.append(("after", tool_name, arguments.copy(), result.copy()))

    hooks.register_hook(Hook())
    hooks.set_enabled(True)
    result = hooks.execute_with_hooks("demo", {"x": 1}, lambda: {"status": "ok"})

    assert result == {"status": "ok"}
    assert seen == [
        ("before", "demo", {"x": 1}),
        ("after", "demo", {"x": 1}, {"status": "ok"}),
    ]


def test_explicit_before_decision_blocks_execution() -> None:
    executed = False

    class Hook:
        def before_tool(self, tool_name, arguments):
            return hooks.HookDecision.block("policy says no")

    def execute():
        nonlocal executed
        executed = True
        return {"status": "ok"}

    hooks.register_hook(Hook())
    hooks.set_enabled(True)
    result = hooks.execute_with_hooks("danger", {}, execute)

    assert executed is False
    assert result == {
        "status": "error",
        "error": "tool_blocked_by_lifecycle_hook",
        "detail": "policy says no",
        "tool": "danger",
    }


def test_throwing_hook_does_not_kill_tool_call(caplog) -> None:
    class Hook:
        def before_tool(self, tool_name, arguments):
            raise RuntimeError("broken hook")

        def after_tool(self, tool_name, arguments, result):
            raise RuntimeError("broken after hook")

    hooks.register_hook(Hook())
    hooks.set_enabled(True)
    result = hooks.execute_with_hooks("demo", {}, lambda: {"status": "ok"})

    assert result == {"status": "ok"}
    assert "broken hook" in caplog.text
    assert "broken after hook" in caplog.text


def test_simple_tools_executor_runs_registered_hooks(monkeypatch) -> None:
    from core.tools import simple_tools

    seen: list[str] = []

    class Hook:
        def before_tool(self, tool_name, arguments):
            seen.append(f"before:{tool_name}")

        def after_tool(self, tool_name, arguments, result):
            seen.append(f"after:{tool_name}:{result['value']}")

    monkeypatch.setitem(
        simple_tools._TOOL_HANDLERS,
        "lifecycle_test_tool",
        lambda args: {"status": "ok", "value": args["value"]},
    )
    hooks.register_hook(Hook())
    hooks.set_enabled(True)

    result = simple_tools.execute_tool("lifecycle_test_tool", {"value": 3})

    assert result["value"] == 3
    assert seen == ["before:lifecycle_test_tool", "after:lifecycle_test_tool:3"]


def test_force_executor_runs_registered_hooks(monkeypatch) -> None:
    from core.tools import simple_tools

    seen: list[str] = []

    class Hook:
        def before_tool(self, tool_name, arguments):
            seen.append(f"before:{tool_name}")

        def after_tool(self, tool_name, arguments, result):
            seen.append(f"after:{tool_name}")

    monkeypatch.setitem(
        simple_tools._TOOL_HANDLERS,
        "force_lifecycle_test_tool",
        lambda args: {"status": "ok"},
    )
    hooks.register_hook(Hook())
    hooks.set_enabled(True)

    result = simple_tools.execute_tool_force("force_lifecycle_test_tool", {})

    assert result["status"] == "ok"
    assert seen == ["before:force_lifecycle_test_tool", "after:force_lifecycle_test_tool"]


def test_force_executor_keeps_observation_self_safe(monkeypatch) -> None:
    from core.tools import simple_tools

    monkeypatch.setitem(
        simple_tools._TOOL_HANDLERS,
        "force_observation_test_tool",
        lambda args: {"status": "ok"},
    )

    def fail_observation(*args, **kwargs):
        raise RuntimeError("observation unavailable")

    monkeypatch.setattr(
        "core.tools.tool_call_observation.observe_tool_call", fail_observation,
    )

    assert simple_tools.execute_tool_force("force_observation_test_tool", {}) == {
        "status": "ok"
    }
