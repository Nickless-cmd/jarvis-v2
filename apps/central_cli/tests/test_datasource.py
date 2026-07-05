from __future__ import annotations
from central_cli import datasource as ds


class FakeClient:
    def __init__(self, data): self._d = data
    def get_json(self, path, params=None): return self._d[path]


def _client():
    return FakeClient({
        "/central/realtime": {
            "status": "yellow",
            "coverage": {"nerves": 122, "clusters": 21},
            "open_breakers": [],
            "incidents": [{"cluster": "network", "nerve": "health", "severity": "error", "message": "latens høj", "ts": 1},
                          {"cluster": "infra", "nerve": "pfsense_security", "severity": "error", "message": "port_scan", "ts": 2}],
            "feed": [{"cluster": "infra", "nerve": "pfsense_security", "decision": "error", "reason": "scan"},
                     {"cluster": "infra", "nerve": "pfsense_security", "decision": "error", "reason": "scan"},
                     {"cluster": "cognition", "nerve": "agenda", "decision": "observe", "reason": ""}],
        },
        "/central/timeseries": {"series": {
            "network:health": {"api": {"count": 970, "latest": 1.0, "meta": {"state": "degraded"}, "ts": "2026-07-05T14:57:42+00:00", "recent": [1.0, 2.0, 3.0]}},
            "cognition:agenda": {"api": {"count": 43, "latest": 1.0, "meta": {"state": "steady"}, "ts": "2026-07-05T14:59:00+00:00", "recent": [1.0, 1.0, 1.0]}},
            "system:semantic_indexer": {"api": {"count": 0, "latest": 0.0, "meta": {}, "ts": "", "recent": []}},
        }},
        "/central/diagnostics": {"incidents": [1, 2], "anomalies": [], "root_causes": ["rc"], "degrading": []},
        "/central/governance": {"flags": [{"key": "lag4_live", "label": "lag4", "kind": "bool", "dangerous": True, "value": True, "options": None}]},
        "/central/healers": {"registry_enabled": True, "healers": [{"kind": "central.circuit_open", "mode": "LIVE", "destructive": False, "live_flag_on": None}]},
    })


def test_overview():
    o = ds.overview(_client())
    assert o["status"] == "yellow"
    assert o["nerves"] == 122 and o["clusters"] == 21
    assert o["incidents"] == 2 and o["breakers"] == 0
    assert len(o["top_incidents"]) == 2


def test_nerves_shape_and_state():
    rows = ds.nerves(_client())
    by = {r["nerve"]: r for r in rows}
    # network/health er i incidents m. error → degraded
    assert by["health"]["state"] == "degraded"
    assert by["health"]["count"] == 970
    assert by["health"]["spark"]  # sparkline-streng ikke tom
    # semantic_indexer count 0 / ingen data → død
    assert by["semantic_indexer"]["state"] == "død"
    # agenda: aktivitet, ikke i incidents → aktiv
    assert by["agenda"]["state"] == "aktiv"


def test_incidents():
    rows = ds.incidents(_client())
    assert len(rows) == 2
    assert rows[0]["cluster"] == "network"


def test_feed_deduped():
    f = ds.feed(_client())
    # to identiske pfsense-linjer → dedupe til én m. count 2
    pf = [x for x in f if x["nerve"] == "pfsense_security"]
    assert len(pf) == 1 and pf[0]["count"] == 2


def test_governance_and_healers_passthrough():
    assert ds.governance(_client())[0]["key"] == "lag4_live"
    assert ds.healers(_client())["registry_enabled"] is True


def test_diagnostics():
    d = ds.diagnostics(_client())
    assert d["root_causes"] == ["rc"]
