"""tool_result_format: udskilt fra simple_tools, samme adfaerd og samme navne."""
from __future__ import annotations

import pytest

NAMES = ("format_tool_result_for_model", "_verify_hint_for", "_signal_linjer", "_json_safe_default")


@pytest.mark.parametrize("name", NAMES)
def test_every_function_is_reexported_from_simple_tools(name):
    from core.tools import simple_tools, tool_result_format

    assert getattr(simple_tools, name) is getattr(tool_result_format, name)


def test_write_file_ok_gets_a_verify_hint_with_the_path_and_errors_get_none():
    from core.tools.tool_result_format import _verify_hint_for

    hint = _verify_hint_for("write_file", {"status": "ok", "path": "/x/y.py"})
    assert hint and "verify_file_contains(path='/x/y.py'" in hint
    assert _verify_hint_for("write_file", {"status": "error", "path": "/x/y.py"}) is None
    assert _verify_hint_for("bash", {"status": "ok"}) is None


def test_readback_replaces_the_verify_hint_text():
    from core.tools.tool_result_format import _verify_hint_for

    hint = _verify_hint_for("edit_file", {"status": "ok", "path": "/a", "readback": "..."})
    assert "Readback" in hint and "verify_file_contains" not in hint


def test_json_safe_default_never_raises_on_odd_objects():
    import json

    from core.tools.tool_result_format import _json_safe_default

    out = json.dumps({"a": object(), "b": {1, 2}}, default=_json_safe_default)
    assert isinstance(out, str) and out.startswith("{")
