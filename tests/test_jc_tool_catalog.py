from core.tools import jc_tool_catalog as cat


def test_colliding_tools_are_the_verified_four():
    assert cat.COLLIDING_TOOLS == ("bash", "read_file", "write_file", "edit_file")


def test_default_companions_list():
    assert cat.DEFAULT_COMPANIONS == (
        "search_memory", "read_memory_topic", "write_memory_topic",
        "read_project_notes", "update_project_notes",
        "recall_memories", "search_jarvis_brain",
        "remember_this", "archive_brain_entry", "read_mood",
    )


def test_alias_roundtrip():
    assert cat.alias_for("bash") == "runtime_bash"
    assert cat.unalias("runtime_bash") == "bash"
    assert cat.unalias("remember_this") == "remember_this"


def test_is_runtime_alias():
    assert cat.is_runtime_alias("runtime_bash") is True
    assert cat.is_runtime_alias("runtime_read_file") is True
    assert cat.is_runtime_alias("runtime_notacolliding") is False
    assert cat.is_runtime_alias("bash") is False


def _fake_defs():
    return [
        {"type": "function", "function": {"name": "bash", "description": "run"}},
        {"type": "function", "function": {"name": "read_file", "description": "r"}},
        {"type": "function", "function": {"name": "write_file", "description": "w"}},
        {"type": "function", "function": {"name": "edit_file", "description": "e"}},
        {"type": "function", "function": {"name": "remember_this", "description": "m"}},
        {"type": "function", "function": {"name": "read_mood", "description": "mood"}},
        {"type": "function", "function": {"name": "unrelated", "description": "x"}},
    ]


def _names(defs):
    return {(d.get("function") or d).get("name") for d in defs}


def test_locked_catalog_has_companions_plus_load_more(monkeypatch):
    monkeypatch.setattr(cat, "_all_native_defs", lambda role: _fake_defs())
    out = cat.build_jc_catalog(role="owner", unlocked=False)
    names = _names(out)
    assert "remember_this" in names and "read_mood" in names
    assert "load_more_tools" in names
    assert "runtime_bash" not in names
    assert "bash" not in names


def test_unlocked_catalog_adds_runtime_aliases(monkeypatch):
    monkeypatch.setattr(cat, "_all_native_defs", lambda role: _fake_defs())
    out = cat.build_jc_catalog(role="owner", unlocked=True)
    names = _names(out)
    assert "runtime_bash" in names and "runtime_edit_file" in names
    assert "bash" not in names
    assert "unrelated" in names


def test_load_more_tool_def_shape():
    d = cat.LOAD_MORE_TOOL_DEF
    assert d["function"]["name"] == "load_more_tools"
