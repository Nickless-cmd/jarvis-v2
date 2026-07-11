from central_cli.engine.state import HudState
from central_cli.views.overview import render_overview


def test_render_overview_from_state_returns_text():
    s = HudState()
    s.set_ok("realtime", {"status": "green", "incidents": [], "degrading": []})
    out = render_overview(s)
    assert "green" in str(out).lower() or "GREEN" in str(out)


def test_render_overview_handles_empty_state():
    s = HudState()
    out = render_overview(s)   # ingen data endnu — må ikke kaste
    assert out is not None
