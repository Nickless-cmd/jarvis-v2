"""Tests for real-time Central-surface (owner-vindue)."""
from __future__ import annotations

from core.services import central_realtime as cr


def test_snapshot_shape_self_safe():
    s = cr.realtime_snapshot()
    for k in ("status", "coverage", "diagnose", "feed", "incidents",
              "open_breakers", "learning"):
        assert k in s
    assert s["status"] in ("green", "yellow", "red")
    assert isinstance(s["feed"], list)


def test_status_red_on_open_breaker():
    st = cr._status_from({"degraded": False}, [], ["auth/tool_access"], {}, [])
    assert st == "red"


def test_status_red_on_severe_incident():
    st = cr._status_from({"degraded": False}, [{"severity": "severe"}], [], {}, [])
    assert st == "red"


def test_status_red_on_fail_open():
    st = cr._status_from({"degraded": False}, [{"kind": "fail_open", "severity": "error"}], [], {}, [])
    assert st == "red"


def test_status_yellow_on_degrading():
    st = cr._status_from({"degraded": False}, [], [], {}, [{"cluster": "x", "nerve": "y"}])
    assert st == "yellow"


def test_status_green_when_clean():
    st = cr._status_from({"degraded": False}, [], [], {}, [])
    assert st == "green"


def test_status_red_on_foreign_process_breaker():
    # en åben breaker i RUNTIME-processen (ikke api) skal hæve status til rød
    procs = [{"process": "runtime", "open_breakers": ["loop/runaway"], "degraded": True}]
    st = cr._status_from({"degraded": False}, [], [], {}, [], None, procs)
    assert st == "red"


def test_status_yellow_on_foreign_process_degraded():
    procs = [{"process": "runtime", "open_breakers": [], "degraded": True}]
    st = cr._status_from({"degraded": False}, [], [], {}, [], None, procs)
    assert st == "yellow"


def test_snapshot_has_processes_key():
    s = cr.realtime_snapshot()
    assert "processes" in s and isinstance(s["processes"], list)


def test_balanced_feed_does_not_starve_low_volume_process():
    # api fyrer 100 records (nyeste ts), runtime kun 3 (ældre) — runtime må IKKE sultes ud
    recs = [{"process": "api", "nerve": f"a{i}", "ts": 1000.0 + i} for i in range(100)]
    recs += [{"process": "runtime", "nerve": f"r{i}", "ts": 10.0 + i} for i in range(3)]
    out = cr._balanced_feed(recs, 24)
    procs = {f["process"] for f in out}
    assert "runtime" in procs and "api" in procs
    # alle 3 runtime-records overlever (færre end kvoten)
    assert sum(1 for f in out if f["process"] == "runtime") == 3
    assert len(out) == 24


def test_balanced_feed_single_process_unaffected():
    recs = [{"process": "api", "nerve": f"a{i}", "ts": float(i)} for i in range(10)]
    out = cr._balanced_feed(recs, 5)
    assert len(out) == 5 and all(f["process"] == "api" for f in out)
    # nyeste først
    assert out[0]["ts"] >= out[-1]["ts"]


# ── Sande incident-tal (målt 4/10-2026) ──────────────────────────────────────
#
# Kalderen henter incidents med `limit=40`, og visnings-listen klippes yderligere
# til 12. Blev farven og tallene regnet på DEN liste, kunne Centralen stå grøn med
# en uløst error i DB'en — og «12» stod der, uanset om der var 12 eller 240 åbne.

def test_status_ser_fejl_uden_for_de_nyeste_40(isolated_runtime):
    """Farven må ikke afhænge af hvilke rækker der er INDEN FOR vinduet.

    Ligger den eneste ægte fejl uden for de nyeste 40, ser listen ren ud. Den gamle
    beregning svarede derfor GRØN — mens DB'en havde en uløst error."""
    from core.runtime.db_central_incidents import (
        record_central_incident, count_open_incidents,
    )
    # fejlen skrives FØRST → lavest id → falder uden for de nyeste 40
    record_central_incident(cluster="runtime", nerve="silent_cutoff",
                            kind="turn_without_reply", severity="error", message="cut")
    for i in range(45):
        record_central_incident(cluster="proactivity", nerve="verification",
                                kind="gate_enforce", severity="info", message=f"g{i}")
    vindue = [{"severity": "info"} for _ in range(40)]  # hvad kalderen FAKTISK ser
    # modprøve: uden de sande tal er fejlen usynlig → grøn
    assert cr._status_from({"degraded": False}, vindue, [], {}, []) == "green"
    # med DB-tallene er den synlig → gul
    c = count_open_incidents()
    assert c["errors"] == 1 and c["unresolved"] == 46
    assert cr._status_from({"degraded": False}, vindue, [], {}, [],
                           incident_counts=c) == "yellow"


def test_snapshot_baerer_sande_incident_tal(isolated_runtime):
    """Snapshottet skal eksponere DB-tallene — ikke `len()` af visnings-listen."""
    from core.runtime.db_central_incidents import record_central_incident
    for i in range(20):
        record_central_incident(cluster="proactivity", nerve="verification",
                                kind="gate_enforce", severity="info", message=f"g{i}")
    s = cr.realtime_snapshot(trace_limit=1)
    c = s.get("incident_counts") or {}
    assert c.get("unresolved") == 20
    assert c.get("governance") == 20
    # visnings-listen er stadig klippet — det er meningen ...
    assert len(s["incidents"]) <= 12
    # ... men tallet lyver ikke længere
    assert c["unresolved"] != len(s["incidents"])
