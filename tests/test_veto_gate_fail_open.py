"""Fail-open synlighed for veto_gate.check_veto (audit 2026-07-04).

Kaster pushback-beregningen tillader veto-gaten handlingen (allow) — men det MÅ
ikke være tavst. Testene bekræfter at incidenten flagges FØR return, at fail-open-
adfærden (True, None) er uændret, og at det hele er self-safe.
"""
from __future__ import annotations


def test_check_veto_pushback_raise_records_incident(monkeypatch):
    from core.services import veto_gate as vg

    # Nå frem til step 3 (pushback): ikke always-allowed, token-signal siger nej.
    monkeypatch.setattr(vg, "_ensure_veto_events_table", lambda: None)
    monkeypatch.setattr(vg, "_check_token_signal_gate", lambda msg, tool: False)
    monkeypatch.setattr(
        "core.services.pushback.affective_pushback_section",
        lambda msg: (_ for _ in ()).throw(RuntimeError("pushback nede")))

    flagged: list[dict] = []
    monkeypatch.setattr(
        "core.runtime.db_central_incidents.record_central_incident",
        lambda **k: flagged.append(k))

    allowed, reason = vg.check_veto("operator_write_file", "gør det", "s1")

    assert allowed is True and reason is None  # fail-open adfærd uændret
    assert len(flagged) == 1
    assert flagged[0]["cluster"] == "review"
    assert flagged[0]["nerve"] == "veto_gate"
    assert flagged[0]["kind"] == "fail_open"


def test_check_veto_incident_failure_is_self_safe(monkeypatch):
    from core.services import veto_gate as vg

    monkeypatch.setattr(vg, "_ensure_veto_events_table", lambda: None)
    monkeypatch.setattr(vg, "_check_token_signal_gate", lambda msg, tool: False)
    monkeypatch.setattr(
        "core.services.pushback.affective_pushback_section",
        lambda msg: (_ for _ in ()).throw(RuntimeError("pushback nede")))
    monkeypatch.setattr(
        "core.runtime.db_central_incidents.record_central_incident",
        lambda **k: (_ for _ in ()).throw(RuntimeError("incident nede")))

    allowed, reason = vg.check_veto("operator_write_file", "gør det", "s1")
    assert allowed is True and reason is None  # fail-open holder trods incident-fejl
