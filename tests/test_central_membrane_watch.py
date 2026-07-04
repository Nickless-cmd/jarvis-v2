"""Tests for WARDEN — vogteren over muren (LivingNeuron-roadmap §2).

Kerne-egenskab: FAIL-CLOSED. En SECURITY-tripwire der ikke kan verificere sig selv skal
alarmere (intact=False), ALDRIG fail-silent grønt. Plus dedup: alarmér kun ved NYT brud.
"""
from __future__ import annotations

import core.services.central_membrane_watch as warden


def test_check_intact_when_source_unchanged(monkeypatch):
    monkeypatch.setattr(
        "core.services.central_hypothesis_governance.verify_frozen_core", lambda: True)
    chk = warden.check_membrane()
    assert chk["intact"] is True
    assert chk["egress_sha_ok"] is True
    assert chk["frozen_core_ok"] is True
    assert chk["violations"] == []


def test_fail_closed_when_verify_frozen_core_raises(monkeypatch):
    # KRITISK: verify_frozen_core kaster → intact MÅ være False, IKKE True (aldrig fail-silent)
    def boom():
        raise RuntimeError("frossen kerne utilgængelig")
    monkeypatch.setattr(
        "core.services.central_hypothesis_governance.verify_frozen_core", boom)
    chk = warden.check_membrane()
    assert chk["intact"] is False
    assert chk["frozen_core_ok"] is False
    assert any("frozen_core" in v for v in chk["violations"])


def test_fail_closed_on_frozen_core_false(monkeypatch):
    monkeypatch.setattr(
        "core.services.central_hypothesis_governance.verify_frozen_core", lambda: False)
    chk = warden.check_membrane()
    assert chk["intact"] is False
    assert chk["frozen_core_ok"] is False


def test_sha_mismatch_is_breach(monkeypatch):
    # simulér at en egress-funktion er ændret i runtime (SHA divergerer fra reference)
    monkeypatch.setattr(
        "core.services.central_hypothesis_governance.verify_frozen_core", lambda: True)
    monkeypatch.setattr(warden, "_REFERENCE_SHAS",
                        {"central_core._egress_safe": "0" * 64})
    monkeypatch.setattr(warden, "_egress_targets",
                        lambda: [("central_core._egress_safe", lambda p: p)])
    chk = warden.check_membrane()
    assert chk["intact"] is False
    assert chk["egress_sha_ok"] is False
    assert any("sha-mismatch" in v for v in chk["violations"])


def test_fail_closed_when_no_reference_shas(monkeypatch):
    monkeypatch.setattr(
        "core.services.central_hypothesis_governance.verify_frozen_core", lambda: True)
    monkeypatch.setattr(warden, "_REFERENCE_SHAS", {})
    monkeypatch.setattr(warden, "_egress_targets", lambda: [])
    chk = warden.check_membrane()
    assert chk["intact"] is False
    assert chk["egress_sha_ok"] is False


def test_run_tick_emits_green_nerve_when_intact(monkeypatch):
    monkeypatch.setattr(warden, "check_membrane",
                        lambda: {"intact": True, "egress_sha_ok": True,
                                 "frozen_core_ok": True, "violations": []})
    emitted = []
    monkeypatch.setattr("core.services.central_private_observe.record_private",
                        lambda c, n, **kw: emitted.append((c, n, kw.get("value"))))
    monkeypatch.setattr(warden, "_kv_get_str", lambda k: "")
    out = warden.run_membrane_watch_tick()
    assert out["status"] == "ok" and out["intact"] is True
    assert ("security", "membrane_watch", 1.0) in emitted


def test_run_tick_new_breach_records_incident_and_notifies(monkeypatch):
    monkeypatch.setattr(warden, "check_membrane",
                        lambda: {"intact": False, "egress_sha_ok": False,
                                 "frozen_core_ok": True,
                                 "violations": ["egress:central_core._egress_safe:sha-mismatch"]})
    emitted = []
    monkeypatch.setattr("core.services.central_private_observe.record_private",
                        lambda c, n, **kw: emitted.append((c, n, kw.get("value"))))
    incidents = []
    monkeypatch.setattr("core.runtime.db_central_incidents.record_central_incident",
                        lambda **kw: incidents.append(kw) or 123)
    monkeypatch.setattr(warden, "_notify_owner_breach", lambda msg: True)
    monkeypatch.setattr(warden, "_kv_get_str", lambda k: "")   # ingen tidligere signatur
    saved = {}
    monkeypatch.setattr(warden, "_kv_set_str", lambda k, v: saved.update({k: v}))
    out = warden.run_membrane_watch_tick()
    assert out["status"] == "breach" and out["intact"] is False
    assert ("security", "membrane_watch", 0.0) in emitted
    assert incidents and incidents[0]["cluster"] == "security"
    assert incidents[0]["severity"] == "critical"
    assert out["incident_id"] == 123 and out["notified"] is True
    assert saved[warden._SIG_KEY]  # signatur gemt til dedup


def test_run_tick_repeated_breach_is_deduped(monkeypatch):
    # SAMME brud igen (signaturen matcher forrige) → INGEN ny incident/ntfy (mod alarm-spam)
    sig = "egress:central_core._egress_safe:sha-mismatch"
    monkeypatch.setattr(warden, "check_membrane",
                        lambda: {"intact": False, "egress_sha_ok": False,
                                 "frozen_core_ok": True, "violations": [sig]})
    monkeypatch.setattr("core.services.central_private_observe.record_private",
                        lambda c, n, **kw: None)
    incidents = []
    monkeypatch.setattr("core.runtime.db_central_incidents.record_central_incident",
                        lambda **kw: incidents.append(kw) or 1)
    notified = []
    monkeypatch.setattr(warden, "_notify_owner_breach", lambda msg: notified.append(msg) or True)
    monkeypatch.setattr(warden, "_kv_get_str", lambda k: sig)  # signatur = forrige = uændret
    monkeypatch.setattr(warden, "_kv_set_str", lambda k, v: None)
    out = warden.run_membrane_watch_tick()
    assert out["status"] == "breach" and out["deduped"] is True
    assert incidents == [] and notified == []  # ingen gentagen alarm


def test_reference_shas_computed_at_import():
    # write-once baseline findes og dækker mindst egress_safe (import-tids-beregning kørte)
    assert isinstance(warden._REFERENCE_SHAS, dict)
    assert "central_core._egress_safe" in warden._REFERENCE_SHAS
    assert len(warden._REFERENCE_SHAS["central_core._egress_safe"]) == 64
