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


# --- incident_detail / cost_today -----------------------------------------

class RaisingClient:
    def get_json(self, path, params=None):
        raise RuntimeError("boom")


def _detail_client():
    return FakeClient({
        "/central/realtime": {
            "incidents": [
                {"cluster": "infra", "nerve": "pfsense_security", "kind": "security",
                 "severity": "error", "message": "port_scan detected", "ts": 2},
                {"cluster": "infra", "nerve": "webservice", "kind": "health",
                 "severity": "error", "message": "5xx spike", "ts": 3},
                {"cluster": "network", "nerve": "health", "kind": "latency",
                 "severity": "error", "message": "latens høj", "ts": 1},
            ],
        },
        "/central/diagnostics": {"root_causes": [
            {"cluster": "infra", "nerve": "pfsense_security", "signature": "port_scan norm",
             "count": 3, "severe": True, "first": "2026-07-05T10:00:00+00:00",
             "last": "2026-07-05T15:00:00+00:00", "sample": "port_scan detected"},
            {"cluster": "infra", "nerve": "pfsense_security", "signature": "other lower",
             "count": 1, "severe": False, "first": "x", "last": "y", "sample": "z"},
        ]},
        "/central/healers": {"registry_enabled": True, "healers": [
            {"kind": "security", "mode": "LIVE", "destructive": False, "live_flag_on": True},
        ]},
        "/mc/costs": {"summary": {"total_cost_usd": 25.4057, "cost_rows": 10}, "items": []},
    })


def test_incident_detail_joins_root_cause_and_correlation():
    c = _detail_client()
    inc = {"cluster": "infra", "nerve": "pfsense_security", "kind": "security",
           "severity": "error", "message": "port_scan detected"}
    d = ds.incident_detail(c, inc)
    assert d["cluster"] == "infra" and d["nerve"] == "pfsense_security"
    assert d["title"] == "pfsense_security"
    # highest-count root_cause wins
    assert d["root_cause"] == "port_scan norm"
    assert d["correlation"] is not None
    assert d["correlation"]["count"] == 3
    assert d["correlation"]["first"] == "2026-07-05T10:00:00+00:00"
    assert d["correlation"]["last"] == "2026-07-05T15:00:00+00:00"
    # sig = blake2s digest_size=4 of the signature → 8 hex chars
    import hashlib
    assert d["correlation"]["sig"] == hashlib.blake2s(b"port_scan norm", digest_size=4).hexdigest()
    assert len(d["correlation"]["sig"]) == 8


def test_incident_detail_related_same_cluster_excludes_self():
    c = _detail_client()
    inc = {"cluster": "infra", "nerve": "pfsense_security", "kind": "security",
           "severity": "error", "message": "port_scan detected"}
    d = ds.incident_detail(c, inc)
    # webservice is same cluster (infra) -> included; pfsense_security (self) excluded;
    # network/health is a different cluster -> excluded
    assert d["related"] == ["infra/webservice"]


def test_incident_detail_heal_status_from_signature():
    c = _detail_client()
    inc = {"cluster": "infra", "nerve": "pfsense_security", "kind": "security",
           "severity": "error", "message": "port_scan AUTO-HEALED by rule"}
    d = ds.incident_detail(c, inc)
    assert d["heal_status"] is not None
    assert "AUTO-HEALED" in d["heal_status"]


def test_incident_detail_heal_status_none_when_not_healed():
    # incident whose kind matches no live healer and no HEALED text
    c = FakeClient({
        "/central/realtime": {"incidents": []},
        "/central/diagnostics": {"root_causes": []},
        "/central/healers": {"registry_enabled": True, "healers": []},
        "/mc/costs": {"summary": {"total_cost_usd": 1.0}},
    })
    inc = {"cluster": "infra", "nerve": "x", "kind": "latency",
           "severity": "error", "message": "just slow"}
    d = ds.incident_detail(c, inc)
    assert d["heal_status"] is None


def test_incident_detail_no_root_cause_match():
    c = _detail_client()
    inc = {"cluster": "cognition", "nerve": "agenda", "kind": "drift",
           "severity": "error", "message": "agenda drifted"}
    d = ds.incident_detail(c, inc)
    assert d["root_cause"] is None
    assert d["correlation"] is None
    # still copies core fields
    assert d["severity"] == "error"
    assert d["cluster"] == "cognition"
    assert d["nerve"] == "agenda"
    assert d["message"] == "agenda drifted"
    # no same-cluster others in the realtime set
    assert d["related"] == []


def test_cost_today_returns_float():
    c = _detail_client()
    assert ds.cost_today(c) == 25.4057


def test_cost_today_none_on_empty_or_garbage():
    assert ds.cost_today(FakeClient({"/mc/costs": {}})) is None
    assert ds.cost_today(FakeClient({"/mc/costs": {"summary": {}}})) is None
    assert ds.cost_today(FakeClient({"/mc/costs": "garbage"})) is None
    assert ds.cost_today(FakeClient({"/mc/costs": {"summary": {"total_cost_usd": None}}})) is None


def test_incident_detail_self_safe_on_raising_client():
    d = ds.incident_detail(RaisingClient(), {"cluster": "a", "nerve": "b"})
    assert isinstance(d, dict)
    assert d["root_cause"] is None
    assert d["correlation"] is None
    assert d["related"] == []
    assert d["heal_status"] is None


def test_cost_today_self_safe_on_raising_client():
    assert ds.cost_today(RaisingClient()) is None
