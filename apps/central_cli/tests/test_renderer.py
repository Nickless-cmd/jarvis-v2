from __future__ import annotations
from rich.console import Console
from central_cli.renderer import render_status, render_generic


def _to_text(renderable) -> str:
    con = Console(width=100, no_color=True, record=True)
    con.print(renderable)
    return con.export_text()


def test_render_status_shows_status_and_incidents():
    data = {"status": "yellow", "open_breakers": [],
            "incidents": [{"severity": "error", "cluster": "network", "nerve": "health", "message": "latens høj"}]}
    out = _to_text(render_status(data))
    assert "yellow" in out.lower()
    assert "network" in out and "health" in out
    assert "latens" in out


def test_render_generic_json_fallback():
    out = _to_text(render_generic({"a": 1, "b": ["x", "y"]}))
    assert "a" in out and "1" in out
