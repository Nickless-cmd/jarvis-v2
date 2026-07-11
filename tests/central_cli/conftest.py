import pytest


class _FakeClient:
    def get_json(self, path, params=None):
        if path == "/central/realtime":
            return {"status": "green",
                    "incidents": [{"id": str(i), "cluster": "c", "nerve": "n",
                                   "severity": "error", "message": f"m{i}"} for i in range(5)],
                    "nerves": [{"nerve": f"nv{i}", "cluster": "c", "state": "aktiv"}
                               for i in range(5)], "degrading": [], "open_breakers": []}
        if path == "/central/costs-daily":
            return {"today_usd": 0.03}
        if path == "/central/diagnostics":
            return {"incidents": [], "root_causes": []}
        if path.startswith("/central/nerve/"):
            return {"recent": [{"decision": "d", "reason": "r", "payload": {}}]}
        return {}


@pytest.fixture
def fake_client():
    return _FakeClient()
