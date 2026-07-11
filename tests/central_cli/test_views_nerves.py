from central_cli.engine.state import HudState
from central_cli.views.nerves import build_nerve_rows, nerve_detail_text, nerve_detail_surface_key


def test_build_nerve_rows_uses_name_as_key():
    s = HudState()
    s.set_ok("timeseries", {"series": {"agents:council": {"api": {"count": 5}}}})
    rows = build_nerve_rows(s)
    assert rows[0]["nerve"] == "council"
    assert rows[0]["cluster"] == "agents"


def test_nerve_detail_surface_key_is_namespaced():
    assert nerve_detail_surface_key("council") == "nerve_detail:council"


def test_nerve_detail_text_shows_recent_observations_with_reason():
    detail = {"recent": [
        {"decision": "escalate", "reason": "pattern repeated 3x", "payload": {"x": 1}},
    ]}
    out = str(nerve_detail_text("council", detail))
    assert "escalate" in out and "pattern repeated 3x" in out
