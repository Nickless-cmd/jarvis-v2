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
