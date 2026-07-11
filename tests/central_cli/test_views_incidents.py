from central_cli.engine.state import HudState
from central_cli.views.incidents import build_incident_rows, incident_detail_text


def test_build_incident_rows_maps_fields_and_key():
    s = HudState()
    s.set_ok("realtime", {"incidents": [
        {"id": 42, "cluster": "tools", "nerve": "outcome",
         "severity": "error", "message": "Tool-fejlrate 60%"},
    ]})
    rows = build_incident_rows(s)
    assert rows[0]["id"] == "42"          # key_field
    assert rows[0]["cluster"] == "tools"
    assert "60%" in rows[0]["besked"]


def test_incident_detail_text_is_untruncated():
    long_msg = "x" * 600
    d = {"id": 1, "cluster": "c", "nerve": "n", "severity": "error", "message": long_msg}
    out = str(incident_detail_text(d))
    assert long_msg in out                # ingen [:N]-klip i detaljen
