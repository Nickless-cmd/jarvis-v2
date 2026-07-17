"""Tests for central_incidents — persistent log af det Centralen griber."""
from __future__ import annotations


def test_record_list_resolve_count(isolated_runtime):
    from core.runtime.db_central_incidents import (
        record_central_incident, list_central_incidents,
        resolve_central_incident, count_unresolved,
    )
    rid = record_central_incident(cluster="truth", nerve="claim_scanner", kind="error",
                                  severity="severe", message="boom", run_id="r1")
    assert rid
    record_central_incident(cluster="loop", nerve="x", kind="error", severity="error",
                            message="mild", run_id="r2")
    rows = list_central_incidents(limit=10)
    assert any(r["nerve"] == "claim_scanner" and r["severity"] == "severe" for r in rows)
    # severity-filter
    sev = list_central_incidents(min_severity="severe")
    assert sev and all(r["severity"] == "severe" for r in sev)
    assert count_unresolved(min_severity="severe") >= 1
    # resolve fjerner fra unresolved
    assert resolve_central_incident(rid)
    assert all(r["id"] != rid for r in list_central_incidents(unresolved_only=True))


def test_record_is_self_safe_on_bad_input(isolated_runtime):
    from core.runtime.db_central_incidents import record_central_incident
    # ukendt severity → normaliseres til 'error', kaster ikke
    rid = record_central_incident(cluster="x", nerve="y", kind="error",
                                  severity="nonsense", message="m")
    assert rid


def test_resolve_central_incidents_batch(isolated_runtime):
    from core.runtime.db_central_incidents import (
        record_central_incident, resolve_central_incidents, list_central_incidents,
    )
    for i in range(3):
        record_central_incident(cluster="system", nerve="config_drift", kind="drift",
                                severity="severe", message=f"drift {i}")
    record_central_incident(cluster="other", nerve="x", kind="error", message="keep")
    n = resolve_central_incidents(cluster="system", nerve="config_drift")
    assert n == 3
    unresolved = list_central_incidents(unresolved_only=True)
    # config_drift væk, men 'keep' fra andet cluster står
    assert all(r["nerve"] != "config_drift" for r in unresolved)
    assert any(r["nerve"] == "x" for r in unresolved)


def test_record_dedup_bumps_open_instead_of_duplicate(isolated_runtime):
    from core.runtime.db_central_incidents import (
        record_central_incident, list_central_incidents,
    )
    a = record_central_incident(cluster="netX", nerve="healthX", kind="network_degraded",
                                message="latens 900ms", dedup=True)
    assert a is not None  # første → ægte række
    b = record_central_incident(cluster="netX", nerve="healthX", kind="network_degraded",
                                message="latens 4000ms", dedup=True)
    assert b is None  # bumpede den åbne → ingen ny række
    open_inc = [i for i in list_central_incidents(unresolved_only=True, limit=500)
                if i["cluster"] == "netX" and i["nerve"] == "healthX"]
    assert len(open_inc) == 1
    assert "gentaget ×2" in open_inc[0]["message"]


def test_record_dedup_false_preserves_distinct_rows(isolated_runtime):
    from core.runtime.db_central_incidents import (
        record_central_incident, list_central_incidents,
    )
    a = record_central_incident(cluster="netY", nerve="healthY", kind="k", message="1")
    b = record_central_incident(cluster="netY", nerve="healthY", kind="k", message="2")
    assert a is not None and b is not None and a != b  # default: distinkte rækker bevaret


def test_has_unresolved_message_dedup(isolated_runtime):
    from core.runtime.db_central_incidents import (
        record_central_incident, has_unresolved_message, resolve_central_incidents,
    )
    msg = "config-drift: settings.port=8010 men API svarer på 8080"
    assert has_unresolved_message(cluster="system", nerve="config_drift", message=msg) is False
    record_central_incident(cluster="system", nerve="config_drift", kind="drift",
                            severity="severe", message=msg)
    assert has_unresolved_message(cluster="system", nerve="config_drift", message=msg) is True
    # andre beskeder matcher ikke
    assert has_unresolved_message(cluster="system", nerve="config_drift",
                                  message="anden besked") is False
    # når resolved → ikke længere en dublet-blokering
    resolve_central_incidents(cluster="system", nerve="config_drift")
    assert has_unresolved_message(cluster="system", nerve="config_drift", message=msg) is False
