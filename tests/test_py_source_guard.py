"""Værn mod over-escaped triple-quotes i .py-writes (LLM-artefakt)."""
import ast

from core.tools.py_source_guard import guard_py_escapes


def test_autofixes_broken_escaped_docstring():
    bad = 'def f():\n    \\"\\"\\"doc\\"\\"\\"\n    return 1\n'
    fixed, note = guard_py_escapes(bad, "x.py")
    ast.parse(fixed)                       # må ikke rejse efter fix
    assert note is not None and '"""doc"""' in fixed


def test_leaves_valid_py_untouched():
    good = 'def f():\n    """doc"""\n    return 1\n'
    out, note = guard_py_escapes(good, "x.py")
    assert out == good and note is None


def test_ignores_non_python_files():
    bad = '\\"\\"\\"not python\\"\\"\\"'
    out, note = guard_py_escapes(bad, "notes.txt")
    assert out == bad and note is None


def test_skips_when_fix_does_not_resolve_syntax():
    # syntaksfejl der IKKE er escaped-quotes → skriv original uændret
    bad = "def f(:\n    pass\n"
    out, note = guard_py_escapes(bad, "x.py")
    assert out == bad and note is None


def test_navnet_er_faktisk_bundet_i_simple_tools():
    """Værnet blev tilføjet 15. juli SAMMEN med sine kaldsteder — men importen
    manglede. `write_file`/`edit_file` fejlede derfor med
    «name '_guard_py_escapes' is not defined» hver gang de skrev en .py-fil,
    og det blev først opdaget 4. sep. Et kald uden binding er en fejl der kun
    viser sig når linjen faktisk køres.
    """
    import core.tools.simple_tools as st

    assert hasattr(st, "_guard_py_escapes"), "kaldsteder uden import = NameError i drift"
    assert st._guard_py_escapes("x = 1\n", "/tmp/a.py") == ("x = 1\n", None)


def test_skrivning_af_en_py_fil_gaar_igennem_uden_nameerror(tmp_path):
    """Ende-til-ende på selve stien der var brudt."""
    import core.tools.simple_tools as st

    mål = tmp_path / "ny.py"
    res = st._force_write_file({"path": str(mål), "content": "def f():\n    return 1\n"})
    assert res.get("status") == "ok", res
    assert mål.read_text() == "def f():\n    return 1\n"
