import pytest


class _FakeClient:
    def get_json(self, path, params=None):
        if path == "/central/realtime":
            return {"status": "green",
                    "incidents": [{"cluster": "c", "nerve": "n", "severity": "error",
                                   "message": f"m{i}"} for i in range(3)],
                    "degrading": [], "open_breakers": []}
        if path == "/central/diagnostics":
            return {"incidents": [{"id": str(i), "cluster": "c", "nerve": "n",
                                   "severity": "error", "message": f"m{i}"} for i in range(5)],
                    "root_causes": [], "anomalies": [], "degrading": []}
        if path == "/central/timeseries":
            return {"series": {f"c{i}:nv{i}": {"api": {"count": 1, "latest": 0.0}} for i in range(5)}}
        if path == "/central/costs-daily":
            return {"today_usd": 0.03}
        if path.startswith("/central/nerve/"):
            return {"recent": [{"decision": "d", "reason": "r", "payload": {}}]}
        return {}


@pytest.fixture
def fake_client():
    return _FakeClient()
