"""Tests for unified fejl-meddelelses-system (central_error_envelope)."""
from __future__ import annotations

from core.services import central_error_envelope as cee


def test_build_known_code_maps_to_user_message():
    env = cee.build_envelope(code="provider_rate_limited", origin_cluster="stream",
                             run_id="visible-1")
    assert env.severity == "warning" and env.retryable is True
    assert "rate-limited" in env.user_message
    assert env.correlation_id == "visible-1" and env.origin_cluster == "stream"


def test_unknown_code_falls_back_but_keeps_code():
    env = cee.build_envelope(code="some_new_thing", run_id="r")
    assert env.code == "some_new_thing"           # rå kode bevaret til MC
    assert env.severity == "error" and "galt" in env.user_message


def test_client_event_shape_is_consistent():
    env = cee.build_envelope(code="agent_error", run_id="r2")
    ev = env.to_client_event()
    assert ev["type"] == "error" and ev["code"] == "agent_error"
    assert set(ev) == {"type", "code", "severity", "message", "retryable",
                       "fix_hint", "correlation_id"}


def test_for_interruption_bridges_reason():
    env = cee.for_interruption(reason="approval-wait-timeout", run_id="r3")
    assert env.code == "approval-wait-timeout" and env.severity == "info"
    assert env.origin_cluster == "loop"


def test_emit_observes_user_error(monkeypatch):
    seen = {}
    class _C:
        def observe(self, ev): seen.update(ev)
    monkeypatch.setattr("core.services.central_core.central", lambda: _C())
    env = cee.build_envelope(code="provider_error", origin_cluster="stream", run_id="r4")
    ev = cee.emit(env, session_id="s1")
    assert ev["code"] == "provider_error"
    assert seen["cluster"] == "system" and seen["nerve"] == "user_error"
    assert seen["origin_cluster"] == "stream" and seen["correlation_id"] == "r4"


def test_emit_self_safe(monkeypatch):
    monkeypatch.setattr("core.services.central_core.central",
                        lambda: (_ for _ in ()).throw(RuntimeError("nede")))
    env = cee.build_envelope(code="unknown", run_id="r")
    ev = cee.emit(env)  # må ikke kaste
    assert ev["type"] == "error"


def test_user_error_nerve_in_catalog():
    from core.services import central_catalog as cc
    assert cc.validate() == []
    names = [n.name for n in cc.by_cluster("system")]
    assert "user_error" in names


# ── Fejl-notifikationen naaede aldrig frem (maalt 25/9-2026) ────────────────


def test_notifikationen_kaldes_med_routerens_EGNE_parameternavne(monkeypatch):
    """Kaldet stod med `kind="error"`.

    `route_proactive_notification` har ingen parameter der hedder `kind` — den
    hedder `notification_type`. Kaldet kastede altså `TypeError` ved HVERT
    forsøg, og et `except: pass` herunder slugte den. Fejl-notifikationer fra
    fejl-konvolutten er aldrig nået frem til nogen.

    Testen kalder mod den ÆGTE signatur frem for en mock der tager `**kwargs`:
    en mock der sluger alt ville have været grøn hele tiden.
    """
    import inspect

    from core.services import central_error_envelope as CE
    from core.services.notification_router import route_proactive_notification

    set_kald: list[tuple] = []

    def _falsk(user_id, notification_type, payload, importance="normal", **kw):
        set_kald.append((user_id, notification_type, payload))
        return {"delivered": True}

    # Den falske har SAMME positionelle navne som den ægte — ellers måler
    # testen sin egen mock.
    aegte = list(inspect.signature(route_proactive_notification).parameters)[:3]
    assert aegte == ["user_id", "notification_type", "payload"], aegte

    import core.services.notification_router as NR
    monkeypatch.setattr(NR, "route_proactive_notification", _falsk)

    env = CE.build_envelope(code="provider_error")
    CE.emit(env, user_id="u-1", notify=True)

    assert len(set_kald) == 1, "notifikationen blev ikke sendt"
    uid, ntype, payload = set_kald[0]
    assert uid == "u-1"
    assert ntype == "error"
    assert payload.get("title") == "Jarvis-fejl"


def test_en_fejlet_notifikation_logges_frem_for_at_tie(monkeypatch, caplog):
    """`except: pass` var ikke en ekstra sikkerhed — det var det der holdt
    fejlen skjult i månedsvis."""
    import logging

    import core.services.notification_router as NR
    from core.services import central_error_envelope as CE

    def _knaek(*a, **k):
        raise RuntimeError("kanalen er nede")

    monkeypatch.setattr(NR, "route_proactive_notification", _knaek)

    env = CE.build_envelope(code="provider_error")
    with caplog.at_level(logging.WARNING):
        ud = CE.emit(env, user_id="u-1", notify=True)

    assert ud, "en fejlet notifikation maa ikke vaelte kalderen"
    assert any("fejl-notifikation" in r.message for r in caplog.records), \
        "fejlen blev slugt i tavshed"
