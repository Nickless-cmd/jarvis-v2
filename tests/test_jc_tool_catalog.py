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
