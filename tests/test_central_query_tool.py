"""Tests for central_query-tool'et — Bjørns HÅRDE invariant: ALTID status=ok/error."""
from __future__ import annotations

from core.tools.central_query_tool import central_query as q


def _assert_envelope(r):
    assert r["status"] in ("ok", "error")
    assert "action" in r and "data" in r and "error" in r
    assert "meta" in r and "truncated" in r["meta"] and "source" in r["meta"]
    assert "latency_ms" in r["meta"]


def test_all_read_actions_return_envelope():
    for a in ("status", "incidents", "trace", "cluster_health", "autonomy",
              "learning", "drift", "breakers"):
        _assert_envelope(q({"action": a}))


def test_unknown_action_is_error_not_throw():
    r = q({"action": "frobnicate"})
    _assert_envelope(r)
    assert r["status"] == "error" and "ukendt action" in r["error"]


def test_missing_action_is_error():
    r = q({})
    assert r["status"] == "error" and "action" in r["error"]


def test_nerve_detail_requires_nerve():
    assert q({"action": "nerve_detail"})["status"] == "error"


def test_toggle_security_nerve_refused():
    # tool_access er en sikkerheds-nerve → kan ikke slås fra
    r = q({"action": "toggle_nerve", "nerve": "tool_access", "enabled": False})
    assert r["status"] == "error" and "sikkerheds-nerve" in r["error"]


def test_pagination_sets_meta():
    r = q({"action": "incidents", "limit": 1})
    _assert_envelope(r)
    assert isinstance(r["data"]["items"], list)
    if r["meta"].get("total_count", 0) > 1:
        assert r["meta"]["has_more"] is True and r["meta"]["truncated"] is True
        assert "next_offset" in r["meta"]


def test_self_safe_on_crashing_central(monkeypatch):
    import core.services.central_realtime as cr
    monkeypatch.setattr(cr, "realtime_snapshot",
                        lambda **k: (_ for _ in ()).throw(RuntimeError("central nede")))
    r = q({"action": "status"})
    assert r["status"] == "error" and "central nede" in r["error"]
    assert r["data"] is None  # aldrig tom streng/None uden forklaring — error sat


def test_never_truncates_silently():
    # ethvert list-svar med has_more SKAL have truncated=true
    r = q({"action": "trace", "limit": 1})
    if r["meta"].get("has_more"):
        assert r["meta"]["truncated"] is True


# ── §10 skrive-adgang + owner-gating (2026-06-30) ─────────────────────────────

def _set_role(role: str):
    from core.identity import workspace_context as wc
    wc.set_context(user_id=f"{role}-test", role=role, workspace_name="default")


def test_status_includes_recent_and_known_signals():
    r = q({"action": "status"})
    _assert_envelope(r)
    assert r["status"] == "ok"
    anom = r["data"]["anomalies"]
    assert "recent" in anom and "counts" in anom  # §3.7 — ikke kun counts
    assert "known_signals" in r["data"]


def test_known_signals_action_envelope():
    r = q({"action": "known_signals"})
    _assert_envelope(r)
    assert r["status"] == "ok" and isinstance(r["data"]["items"], list)


def test_write_actions_denied_for_member():
    _set_role("member")
    try:
        for act, extra in [("note", {"text": "x"}),
                           ("resolve_and_route", {"signature": "s", "nerve": "n"}),
                           ("depromote", {"signature": "s"}),
                           ("resolve_incident", {"incident_id": 1}),
                           ("nerve_observe", {"nerve": "n"}),
                           ("toggle_cluster", {"cluster": "c", "enabled": False})]:
            r = q({"action": act, **extra})
            _assert_envelope(r)
            assert r["status"] == "error" and "owner-only" in r["error"], act
        # reads forbliver åbne for member
        assert q({"action": "status"})["status"] == "ok"
    finally:
        _set_role("owner")


def test_write_action_validation_for_owner():
    _set_role("owner")
    try:
        # owner må mutere, men manglende påkrævet felt → struktureret error (ikke owner-only)
        r = q({"action": "resolve_and_route", "signature": "s"})  # mangler nerve
        _assert_envelope(r)
        assert r["status"] == "error" and "nerve" in r["error"]
        # note med text → ok
        r2 = q({"action": "note", "text": "owner test note"})
        _assert_envelope(r2)
        assert r2["status"] == "ok" and r2["data"]["noted"] is True
    finally:
        from core.identity import workspace_context as wc
        wc.set_context(user_id="", role="", workspace_name="default")
