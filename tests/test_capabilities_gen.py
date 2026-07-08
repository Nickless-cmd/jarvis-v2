import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "capabilities_gen", Path(__file__).resolve().parents[1] / "scripts" / "capabilities_gen.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def test_tools_from_registry_categorizes():
    handlers = {"read_file": lambda a: None, "operator_bash": lambda a: None,
                "write_file": lambda a: None, "search_memory": lambda a: None}
    mutating = {"write_file", "operator_bash"}
    rows = gen.tools_from_registry(handlers, mutating)
    by = {r["name"]: r for r in rows}
    assert by["read_file"]["mutating"] is False and by["read_file"]["kind"] == "native"
    assert by["operator_bash"]["mutating"] is True and by["operator_bash"]["kind"] == "operator"
    assert by["write_file"]["mutating"] is True


def test_tools_from_registry_skips_bad():
    rows = gen.tools_from_registry({"": None, "ok_tool": lambda a: None}, set())
    assert [r["name"] for r in rows] == ["ok_tool"]


def test_render_md_has_counts_and_rows():
    rows = [{"name": "read_file", "kind": "native", "mutating": False}]
    md = gen.render_md(rows)
    assert "read_file" in md and "CAPABILITIES" in md and "1" in md
