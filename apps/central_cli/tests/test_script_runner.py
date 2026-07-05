from __future__ import annotations
import argparse
from central_cli.script_runner import execute


class _FakeClient:
    def __init__(self): self.calls = []
    def get_json(self, path, params=None): self.calls.append(("GET", path)); return {"status": "yellow", "incidents": []}
    def post_json(self, path, body): self.calls.append(("POST", path, body)); return {"ok": True}


def test_execute_status_json_returns_raw():
    c = _FakeClient()
    out, code = execute(c, verb="status", args=[], as_json=True)
    assert code == 0
    assert '"status"' in out and "yellow" in out
    assert c.calls == [("GET", "/central/realtime")]


def test_execute_write_hits_post():
    c = _FakeClient()
    out, code = execute(c, verb="toggle", args=["network/health", "off"], as_json=True)
    assert code == 0
    assert c.calls[0][0] == "POST"
    assert c.calls[0][1] == "/central/nerve/network/health/toggle"
