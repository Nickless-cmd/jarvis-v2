from core.tools.simple_tools_explore import _execution_context


def test_auto_without_desk_workspace_uses_runtime():
    target, context, error = _execution_context({})

    assert target == "runtime"
    assert context == {"execution_target": "runtime"}
    assert error == ""


def test_unknown_target_is_rejected():
    target, context, error = _execution_context({"target": "moon"})

    assert target == ""
    assert context == {}
    assert "auto, runtime, or workstation" in error
