import ast, importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "requirements_gen", Path(__file__).resolve().parents[1] / "scripts" / "requirements_gen.py")
rg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rg)


def test_top_level_imports_extracts_roots():
    tree = ast.parse("import fastapi\nfrom pydantic import BaseModel\nimport os.path\n")
    mods = rg.top_level_imports(tree)
    assert "fastapi" in mods and "pydantic" in mods and "os" in mods


def test_top_level_imports_ignores_relative():
    tree = ast.parse("from . import x\nfrom ..core import y\n")
    assert rg.top_level_imports(tree) == set()


def test_third_party_filters_stdlib_and_first_party():
    mods = {"os", "sys", "json", "core", "apps", "scripts", "fastapi", "torch"}
    tp = rg.third_party(mods)
    assert "fastapi" in tp and "torch" in tp
    assert "os" not in tp and "core" not in tp and "json" not in tp
