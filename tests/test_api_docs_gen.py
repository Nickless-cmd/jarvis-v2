# tests/test_api_docs_gen.py
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "api_docs_gen", Path(__file__).resolve().parents[1] / "scripts" / "api_docs_gen.py")
g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g)


def test_module_entry_function_signature_and_summary():
    src = 'def foo(a, b=1, *args, **kw):\n    """Does a thing.\n\n    More."""\n    pass\n'
    e = g.module_entry(src, "core/x.py")
    m = [x for x in e["members"] if x["name"] == "foo"][0]
    assert m["kind"] == "function"
    assert m["signature"] == "(a, b=…, *args, **kw)"
    assert m["doc_summary"] == "Does a thing."


def test_module_entry_no_docstring_empty_summary():
    e = g.module_entry("def bar():\n    return 1\n", "core/x.py")
    assert [x for x in e["members"] if x["name"] == "bar"][0]["doc_summary"] == ""


def test_module_entry_class_and_methods():
    src = 'class C:\n    """A class."""\n    def m(self, x):\n        """Method."""\n        pass\n'
    e = g.module_entry(src, "core/x.py")
    names = {x["name"]: x for x in e["members"]}
    assert names["C"]["kind"] == "class"
    assert "C.m" in names and names["C.m"]["kind"] == "method" and names["C.m"]["signature"] == "(self, x)"


def test_module_entry_bad_syntax_safe():
    e = g.module_entry("def (:\n", "core/x.py")
    assert e["members"] == [] and e.get("error")


def test_package_of():
    assert g.package_of("core/services/foo.py") == "core.services"
    assert g.package_of("scripts/jarvis.py") == "scripts"


def test_page_id_single_vs_chunked():
    small = ["a", "b", "c"]
    assert g.page_id("core.runtime", "b", small, chunk=40) == "core.runtime"
    big = [f"m{i:03d}" for i in range(90)]
    pid = g.page_id("core.services", "m000", big, chunk=40)
    assert pid.startswith("core.services.") and pid != "core.services"


def test_routine_execution_modules_have_stable_dedicated_page():
    names = [
        "aaa", "agentic_execution", "routine_prompt", "routine_reconciler",
        "routine_runner", "routine_runtime", "routine_trigger_adapters",
        "routine_migration", "zzz",
    ]
    expected = "core.services.routine-execution"
    assert g.page_id("core.services", "agentic_execution", names) == expected
    assert g.page_id("core.services", "routine_prompt", names) == expected
    assert g.page_id("core.services", "routine_reconciler", names) == expected
    assert g.page_id("core.services", "routine_runner", names) == expected
    assert g.page_id("core.services", "routine_runtime", names) == expected
    assert g.page_id("core.services", "routine_trigger_adapters", names) == expected
    assert g.page_id("core.services", "routine_migration", names) == (
        "core.services.routine-migration"
    )
    assert g.page_id("scripts", "migrate_routines", ["aaa", "migrate_routines"]) == (
        "scripts.routine-migration"
    )
    assert g.page_id("apps.api.jarvis_api.routes", "routines", ["aaa", "routines"]) == (
        "apps.api.jarvis_api.routes.routines"
    )
    assert g.page_id("core.services", "zzz", names, chunk=1) == "core.services.02"


def test_coverage_counts_and_public_undocumented():
    entries = [
        {"module": "core/x.py", "members": [
            {"kind": "function", "name": "pub", "doc_summary": "", "lineno": 1, "signature": "()"},
            {"kind": "function", "name": "_priv", "doc_summary": "", "lineno": 2, "signature": "()"},
            {"kind": "function", "name": "documented", "doc_summary": "Yep.", "lineno": 3, "signature": "()"},
        ]},
    ]
    cov = g.coverage(entries)
    pkg = cov["packages"]["core"]
    assert pkg["functions"] == 3 and pkg["documented"] == 1
    names = {u["name"] for u in cov["undocumented_public"]}
    assert "pub" in names and "_priv" not in names and "documented" not in names


def test_render_contains_names_and_srclink():
    entries = [{"module": "core/x.py", "docstring_summary": "Mod.", "members": [
        {"kind": "function", "name": "foo", "signature": "(a)", "doc_summary": "Hi.", "lineno": 7}]}]
    md = g.render_package_md("core", entries)
    assert "foo" in md and "(a)" in md and "#L7" in md and "core/x.py" in md
