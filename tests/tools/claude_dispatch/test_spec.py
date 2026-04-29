import pytest
from core.tools.claude_dispatch.spec import TaskSpec, parse_spec, SpecValidationError


def test_parse_spec_minimal_valid():
    spec = parse_spec({
        "goal": "Add a docstring to foo()",
        "scope_files": ["core/foo.py"],
        "allowed_tools": ["Read", "Edit"],
        "max_tokens": 50_000,
        "max_wall_seconds": 600,
    })
    assert isinstance(spec, TaskSpec)
    assert spec.goal == "Add a docstring to foo()"
    assert spec.scope_files == ("core/foo.py",)
    assert spec.allowed_tools == ("Read", "Edit")
    assert spec.max_tokens == 50_000
    assert spec.max_wall_seconds == 600


def test_parse_spec_rejects_missing_goal():
    with pytest.raises(SpecValidationError, match="goal"):
        parse_spec({"scope_files": ["a.py"], "allowed_tools": ["Read"]})


def test_parse_spec_rejects_empty_scope():
    with pytest.raises(SpecValidationError, match="scope_files"):
        parse_spec({"goal": "x", "scope_files": [], "allowed_tools": ["Read"]})


def test_parse_spec_rejects_unknown_tool():
    with pytest.raises(SpecValidationError, match="unknown tool"):
        parse_spec({
            "goal": "x", "scope_files": ["a.py"],
            "allowed_tools": ["Read", "RmRf"],
        })


def test_parse_spec_rejects_absolute_scope_paths():
    with pytest.raises(SpecValidationError, match="absolute"):
        parse_spec({
            "goal": "x", "scope_files": ["/etc/passwd"],
            "allowed_tools": ["Read"],
        })


def test_parse_spec_rejects_parent_traversal():
    with pytest.raises(SpecValidationError, match="traversal"):
        parse_spec({
            "goal": "x", "scope_files": ["../foo.py"],
            "allowed_tools": ["Read"],
        })


def test_taskspec_is_frozen():
    spec = parse_spec({
        "goal": "x", "scope_files": ["a.py"], "allowed_tools": ["Read"],
    })
    with pytest.raises((AttributeError, Exception)):
        spec.goal = "mutated"


def test_parse_spec_applies_default_budget():
    spec = parse_spec({
        "goal": "x", "scope_files": ["a.py"], "allowed_tools": ["Read"],
    })
    assert spec.max_tokens == 100_000
    assert spec.max_wall_seconds == 1800
    assert spec.permission_mode == "default"


def test_parse_spec_caps_max_tokens():
    with pytest.raises(SpecValidationError, match="max_tokens"):
        parse_spec({
            "goal": "x", "scope_files": ["a.py"],
            "allowed_tools": ["Read"], "max_tokens": 10_000_000,
        })
