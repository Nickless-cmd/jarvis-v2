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


def test_expire_gate_enforce_incidents_closes_only_old_cognitive(isolated_runtime):
    """Kognitive governance-hændelser (gate_enforce/info) er ØJEBLIKKE, ikke defekter: gamle
    lukkes, ferske bevares — men en SECURITY-RED (severe) og ægte fejl røres ALDRIG."""
    from datetime import UTC, datetime, timedelta

    from core.runtime.db_central_incidents import (
        expire_gate_enforce_incidents, list_central_incidents, record_central_incident,
    )
    from core.runtime.db_core import connect

    old = record_central_incident(cluster="proactivity", nerve="verification",
                                  kind="gate_enforce", severity="info", message="gammel")
    # historisk række fra FØR severity-fixet 10. sep: severity='error', samme klasse → lukkes også
    old_err = record_central_incident(cluster="proactivity", nerve="verification",
                                      kind="gate_enforce", severity="error", message="gammel error")
    fresh = record_central_incident(cluster="proactivity", nerve="verification",
                                    kind="gate_enforce", severity="info", message="fersk")
    # SECURITY-RED = ægte cross-user-lækage → må ALDRIG forsvinde af sig selv
    sec = record_central_incident(cluster="privacy", nerve="cross_user_share",
                                  kind="gate_enforce", severity="severe", message="lækage")
    # ægte fejl (anden kind) → urørt
    err = record_central_incident(cluster="stream", nerve="provider_error",
                                  kind="error", severity="error", message="ægte fejl")

    old_ts = (datetime.now(UTC) - timedelta(hours=5)).isoformat()
    with connect() as conn:
        conn.execute("UPDATE central_incidents SET ts = ? WHERE id IN (?, ?, ?, ?)",
                     (old_ts, old, old_err, sec, err))

    assert expire_gate_enforce_incidents(older_than_hours=2.0) == 2

    unresolved = {r["id"] for r in list_central_incidents(unresolved_only=True, limit=100)}
    assert old not in unresolved      # gammel kognitiv governance → lukket
    assert old_err not in unresolved  # historisk error-gate_enforce → samme klasse, lukket
    assert fresh in unresolved        # fersk → stadig synlig
    assert sec in unresolved          # SECURITY-RED → ALDRIG auto-lukket
    assert err in unresolved          # ægte fejl → urørt


def test_expire_gate_enforce_incidents_is_self_safe(monkeypatch):
    from core.runtime.db_central_incidents import expire_gate_enforce_incidents
    monkeypatch.setattr("core.runtime.db_central_incidents.connect",
                        lambda: (_ for _ in ()).throw(RuntimeError("db nede")))
    assert expire_gate_enforce_incidents() == 0


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
