"""Tests for #4 adaptiv læring (central_learning) — deterministisk pr. cluster fra incidents."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.services import central_learning as cl


def _inc(cluster, nerve, *, severity="error", kind="", age_hours=1):
    ts = (datetime.now(UTC) - timedelta(hours=age_hours)).isoformat()
    return {"cluster": cluster, "nerve": nerve, "severity": severity, "kind": kind, "ts": ts}


def test_cluster_health_counts_window():
    inc = [_inc("auth", "tool_access", severity="severe", age_hours=1),
           _inc("auth", "tool_access", age_hours=2),
           _inc("loop", "loop_control", age_hours=100)]  # uden for 24t
    h = cl.cluster_health(hours=24, incidents=inc)
    assert h["auth"]["total"] == 2 and h["auth"]["severe"] == 1
    assert "loop" not in h


def test_degrading_detects_recent_spike():
    # 5 incidents i sidste time, ingen ældre baseline → recent-rate >> baseline → degraderende
    inc = [_inc("stream", "provider_call", age_hours=0.2) for _ in range(5)]
    deg = cl.degrading(recent_hours=6, baseline_hours=48, incidents=inc)
    assert any(d["cluster"] == "stream" and d["nerve"] == "provider_call" for d in deg)


def test_no_degrading_when_below_min():
    inc = [_inc("loop", "x", age_hours=0.5)]  # kun 1 < _DEGRADE_MIN_RECENT
    assert cl.degrading(incidents=inc) == []


def test_degrading_excludes_own_learning_meta_nerve():
    # system/learning er Centralens EGEN meta-observation → må ALDRIG flagge sig selv
    # (ellers selv-forstærkende loop). Selv en spike skal ignoreres.
    inc = [_inc("system", "learning", age_hours=0.2) for _ in range(20)]
    assert cl.degrading(incidents=inc) == []


def test_observe_learning_does_not_persist_degrading_incidents(monkeypatch):
    # degradering er en live projektion — observe_learning må IKKE skrive den tilbage som
    # incidents (dual-truth + feedback-loop). Verificér at record_central_incident ikke kaldes.
    calls = []
    monkeypatch.setattr("core.runtime.db_central_incidents.record_central_incident",
                        lambda **k: calls.append(k))
    monkeypatch.setattr(cl, "learning_summary", lambda: {
        "degrading": [{"cluster": "stream", "nerve": "provider_call",
                       "recent_rate_hr": 5.0, "baseline_rate_hr": 0.1}],
        "root_causes": [], "proposals": [],
        "autonomy": {"verdict": "hold"},
    })
    cl.observe_learning()
    assert calls == []  # ingen persistering af afledt signal


def test_autonomous_reliability_from_supervision():
    inc = [_inc("autonomous", "supervision", kind="lied", age_hours=1),
           _inc("autonomous", "supervision", kind="connection_error", age_hours=2),
           _inc("auth", "tool_access", age_hours=1)]  # ikke supervision
    rel = cl.autonomous_reliability(hours=24, incidents=inc)
    assert rel["lied"] == 1 and rel["connection_error"] == 1 and rel["flagged_runs"] == 2


def test_assess_autonomy_lie_disqualifies():
    inc = [_inc("autonomous", "supervision", kind="lied", age_hours=1)]
    a = cl.assess_autonomy(incidents=inc)
    assert a["verdict"] == "ikke_moden" and a["dishonest"] is True


def test_assess_autonomy_clean_is_mature():
    a = cl.assess_autonomy(incidents=[])  # ingen flag → moden
    assert a["verdict"] == "moden"


def test_connection_flakiness_not_disqualifying():
    inc = [_inc("autonomous", "supervision", kind="connection_error", age_hours=1) for _ in range(3)]
    a = cl.assess_autonomy(incidents=inc)
    assert a["dishonest"] is False  # netværks-flakiness ≠ ustabil/uærlig


def test_catalog_has_learning():
    from core.services import central_catalog as cc
    assert cc.validate() == []
    assert "learning" in [n.name for n in cc.by_cluster("system")]


# ── §6: root-cause-klyngning + reviewbare forslag (2026-06-23) ───────────────
def _ts(mins_ago: float) -> str:
    return (datetime.now(UTC) - timedelta(minutes=mins_ago)).isoformat()


def test_signature_strips_ids_numbers():
    s = cl._signature("deepseek HTTP 500 on run visible-d8d4a161e826429fbcc7573372e3f8ae")
    s2 = cl._signature("deepseek HTTP 503 on run visible-aaaabbbbccccddddeeeeffff00001111")
    assert "<id>" in s and "<n>" in s and s == s2


def test_root_causes_groups_recurring():
    inc = [{"cluster": "stream", "nerve": "provider_error", "severity": "error",
            "message": f"deepseek HTTP 500 on run visible-{'a'*32}", "ts": _ts(5 + i)}
           for i in range(3)]
    rc = cl.root_causes(incidents=inc)
    assert len(rc) == 1 and rc[0]["count"] == 3 and rc[0]["nerve"] == "provider_error"


def test_root_causes_respects_min_count():
    inc = [{"cluster": "x", "nerve": "y", "severity": "error",
            "message": f"fejl {'a'*16}", "ts": _ts(5)} for _ in range(2)]
    assert cl.root_causes(incidents=inc) == []


def test_propose_root_cause_severe_is_top_priority():
    inc = [{"cluster": "auth", "nerve": "tool_access", "severity": "severe",
            "kind": "fail_open", "message": f"auth backstop kastede {'a'*12}", "ts": _ts(3 + i)}
           for i in range(3)]
    root = [p for p in cl.propose_adjustments(incidents=inc) if p["kind"] == "fix_root_cause"]
    assert root and root[0]["priority"] == 1 and root[0]["target"] == "auth/tool_access"


def test_propose_autonomy_hold_on_lie():
    inc = [{"cluster": "autonomous", "nerve": "supervision", "kind": "lied",
            "severity": "error", "message": "run løj", "ts": _ts(10)}]
    assert any(p["kind"] == "autonomy_hold" for p in cl.propose_adjustments(incidents=inc))


def test_poll_proposals_self_safe(monkeypatch):
    monkeypatch.setattr(cl, "propose_adjustments",
                        lambda **k: (_ for _ in ()).throw(RuntimeError("nede")))
    assert cl.poll_proposals() == []
