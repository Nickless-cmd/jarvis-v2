from core.tools import jc_tool_catalog as cat


def test_colliding_tools_are_the_verified_four():
    assert cat.COLLIDING_TOOLS == ("bash", "read_file", "write_file", "edit_file")


def test_default_companions_list():
    assert cat.DEFAULT_COMPANIONS == (
        "search_memory", "read_memory_topic", "write_memory_topic",
        "read_project_notes", "update_project_notes",
        "recall_memories", "search_jarvis_brain",
        "remember_this", "archive_brain_entry", "read_mood", "skill_gate",
    )


def test_skill_gate_in_catalog_locked(monkeypatch):
    def _fake_defs(role):
        return [
            {"type": "function", "function": {"name": "read_mood", "description": "mood"}},
            {"type": "function", "function": {"name": "skill_gate", "description": "gate"}},
        ]
    monkeypatch.setattr(cat, "_all_native_defs", _fake_defs)
    out = cat.build_jc_catalog(role="owner", unlocked=False)
    names = _names(out)
    assert "skill_gate" in names


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


# --- Fase 0: eksplicit execution-lokation -----------------------------------


def test_execution_location_client_for_bare_colliding_and_local():
    for n in ("bash", "read_file", "write_file", "edit_file",
              "multi_edit", "glob", "grep", "web_fetch", "web_scrape",
              "web_search", "bash_output", "todo_write", "task"):
        assert cat.execution_location(n) == "client", n


def test_execution_location_runtime_for_aliased_colliding():
    for n in ("runtime_bash", "runtime_read_file",
              "runtime_write_file", "runtime_edit_file"):
        assert cat.execution_location(n) == "runtime", n


def test_execution_location_server_for_companions_and_rest():
    for n in ("search_memory", "remember_this", "read_mood",
              "load_more_tools", "operator_launch_app", "unrelated_tool"):
        assert cat.execution_location(n) == "server", n


def test_execution_location_strips_whitespace():
    assert cat.execution_location("  runtime_bash  ") == "runtime"
    assert cat.execution_location(" bash ") == "client"


def test_client_tools_is_frozenset_and_contains_colliding():
    assert isinstance(cat.CLIENT_TOOLS, frozenset)
    for n in cat.COLLIDING_TOOLS:
        assert n in cat.CLIENT_TOOLS


def test_execution_map_over_unlocked_catalog(monkeypatch):
    monkeypatch.setattr(cat, "_all_native_defs", lambda role: _fake_defs())
    out = cat.build_jc_catalog(role="owner", unlocked=True)
    m = cat.execution_map(out)
    assert m["runtime_bash"] == "runtime"
    assert m["runtime_edit_file"] == "runtime"
    assert m["remember_this"] == "server"
    assert m["read_mood"] == "server"
    assert m["unrelated"] == "server"
    assert m["load_more_tools"] == "server"
    assert "bash" not in m


def test_execution_map_empty_for_empty():
    assert cat.execution_map([]) == {}


def test_defs_carry_no_execution_key(monkeypatch):
    # Fase 0-kontrakt: vi må IKKE stample en 'execution'-nøgle på de def's der
    # sendes til providers. Lokation er en ren funktion, ikke en def-nøgle.
    monkeypatch.setattr(cat, "_all_native_defs", lambda role: _fake_defs())
    out = cat.build_jc_catalog(role="owner", unlocked=True)
    for d in out:
        assert "execution" not in d
        assert "execution" not in (d.get("function") or {})
