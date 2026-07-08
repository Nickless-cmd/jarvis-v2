# tests/test_api_reference_gen.py
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "api_reference_gen", Path(__file__).resolve().parents[1] / "scripts" / "api_reference_gen.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def test_routes_from_app_extracts_method_path():
    from fastapi import FastAPI
    app = FastAPI()

    @app.get("/health")
    def health():
        return {}

    @app.post("/chat/send")
    def send():
        return {}

    rows = gen.routes_from_app(app)
    paths = {(r["method"], r["path"]) for r in rows}
    assert ("GET", "/health") in paths
    assert ("POST", "/chat/send") in paths


def test_routes_from_app_empty():
    from fastapi import FastAPI
    assert gen.routes_from_app(FastAPI()) == []


def test_routes_from_ast_reads_decorators(tmp_path):
    f = tmp_path / "routes_x.py"
    f.write_text(
        'from fastapi import APIRouter\n'
        'router = APIRouter()\n'
        '@router.get("/a")\n'
        'def a(): ...\n'
        '@router.post("/b/{id}")\n'
        'def b(id): ...\n')
    rows = gen.routes_from_ast(tmp_path)
    paths = {(r["method"], r["path"]) for r in rows}
    assert ("GET", "/a") in paths and ("POST", "/b/{id}") in paths


def test_render_md_groups_and_lists():
    rows = [{"method": "GET", "path": "/health", "name": "health", "module": "health.py"}]
    md = gen.render_md(rows)
    assert "/health" in md and "GET" in md and "API_REFERENCE" in md
