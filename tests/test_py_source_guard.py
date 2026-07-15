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
