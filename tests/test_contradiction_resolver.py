from __future__ import annotations
from core.services.contradiction_resolver import classify_tier, pick_survivor

def _finding(**kw):
    base = {
        "decision_id": "d1", "decision_directive": "Svar altid kort",
        "decision_priority": 3, "review_id": 7,
        "review_text": "Jeg svarer ikke kort nok i lange tr%ade",
        "overlap_tokens": ["svar", "kort", "nok"], "detected_at": "2026-07-10T10:00:00+00:00",
    }
    base.update(kw); return base

def test_pick_survivor_review_wins_by_recency_same_authority():
    # Decision og self-review er begge self-derived → tie → nyere critique vinder.
    s = pick_survivor(_finding())
    assert s["winner"] == "review"
    assert s["loser"] == "decision"
    assert s["confidence"] == "high"      # 3 overlap-tokens
    assert "recency" in s["rule"]

def test_pick_survivor_confidence_medium_two_tokens():
    s = pick_survivor(_finding(overlap_tokens=["svar", "kort"]))
    assert s["confidence"] == "medium"

def test_pick_survivor_confidence_low_one_token():
    s = pick_survivor(_finding(overlap_tokens=["svar"]))
    assert s["confidence"] == "low"

def test_classify_tier_operational_is_auto():
    assert classify_tier(_finding()) == "auto"

def test_classify_tier_identity_keyword_escalates():
    assert classify_tier(_finding(decision_directive="Jeg er nysgerrig af natur")) == "escalate"

def test_classify_tier_high_priority_escalates():
    assert classify_tier(_finding(decision_priority=9)) == "escalate"

def test_classify_tier_low_confidence_escalates():
    # Svag overlap → for usikkert til auto → escalate (konservativt).
    assert classify_tier(_finding(overlap_tokens=["svar"])) == "escalate"

from core.runtime.db import connect
from core.services import contradiction_resolver as cr

def _seed_active_decision(decision_id="d1", directive="Svar altid kort", priority=3):
    # behavioral_decisions oprettes lazily af db_decisions (ikke af init_db) → ensure den her.
    from core.runtime.db_decisions import _ensure_tables
    with connect() as c:
        _ensure_tables(c)
        c.execute(
            "INSERT INTO behavioral_decisions (decision_id, directive, trigger_cue, priority, status, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, 'active', ?, ?)",
            (decision_id, directive, "cue", priority, "2026-07-01T00:00:00+00:00", "2026-07-01T00:00:00+00:00"),
        )
        c.commit()

def _decision_status(decision_id):
    with connect() as c:
        row = c.execute("SELECT status FROM behavioral_decisions WHERE decision_id=?", (decision_id,)).fetchone()
    return row["status"] if row else None

def test_apply_supersede_flips_status_and_is_reversible(isolated_runtime):
    _seed_active_decision("d1")
    assert cr._apply_supersede("d1", review_id=7, rule="r") is True
    assert _decision_status("d1") == "superseded"
    # Reversibel — aldrig slettet.
    assert cr.revert_supersede("d1") is True
    assert _decision_status("d1") == "active"

def test_apply_supersede_missing_decision_is_false(isolated_runtime):
    assert cr._apply_supersede("nope", review_id=1, rule="r") is False

def test_escalate_is_deduped(isolated_runtime, monkeypatch):
    published = []
    monkeypatch.setattr(cr.event_bus, "publish", lambda topic, payload: published.append((topic, payload)))
    f = {"decision_id": "d9", "review_id": 3, "decision_directive": "x", "review_text": "y"}
    assert cr._write_escalation_proposal(f, rule="r", seen=set()) is True
    seen = {("d9", 3)}
    assert cr._write_escalation_proposal(f, rule="r", seen=seen) is False  # allerede foreslaaet
    assert len([p for p in published if p[0] == "contradiction.resolution_proposed"]) == 1

def test_resolve_shadow_records_but_does_not_mutate(isolated_runtime, monkeypatch):
    _seed_active_decision("d1", directive="Svar altid kort", priority=3)
    monkeypatch.setattr(cr, "detect_contradictions", lambda **k: [{
        "decision_id": "d1", "decision_directive": "Svar altid kort", "decision_priority": 3,
        "review_id": 7, "review_text": "svarer ikke kort nok", "overlap_tokens": ["svar","kort","nok"],
        "detected_at": "2026-07-10T10:00:00+00:00"}])
    summary = cr.resolve_contradictions(live=False)
    assert summary["shadow"] is True
    assert summary["would_supersede"] == 1
    assert _decision_status("d1") == "active"      # IKKE muteret i shadow

def test_resolve_live_supersedes(isolated_runtime, monkeypatch):
    _seed_active_decision("d1", directive="Svar altid kort", priority=3)
    monkeypatch.setattr(cr, "detect_contradictions", lambda **k: [{
        "decision_id": "d1", "decision_directive": "Svar altid kort", "decision_priority": 3,
        "review_id": 7, "review_text": "svarer ikke kort nok", "overlap_tokens": ["svar","kort","nok"],
        "detected_at": "2026-07-10T10:00:00+00:00"}])
    summary = cr.resolve_contradictions(live=True)
    assert summary["superseded"] == 1
    assert _decision_status("d1") == "superseded"

def test_resolve_escalate_tier_does_not_mutate(isolated_runtime, monkeypatch):
    _seed_active_decision("d1", directive="Jeg er nysgerrig", priority=3)
    monkeypatch.setattr(cr, "detect_contradictions", lambda **k: [{
        "decision_id": "d1", "decision_directive": "Jeg er nysgerrig", "decision_priority": 3,
        "review_id": 7, "review_text": "nysgerrig passer ikke", "overlap_tokens": ["jeg","er","nysgerrig"],
        "detected_at": "2026-07-10T10:00:00+00:00"}])
    summary = cr.resolve_contradictions(live=True)
    assert summary["escalated"] == 1
    assert summary["superseded"] == 0
    assert _decision_status("d1") == "active"      # identitet → forslag, ingen mutation

def test_resolve_fail_open_on_detection_error(isolated_runtime, monkeypatch):
    def boom(**k): raise RuntimeError("db down")
    monkeypatch.setattr(cr, "detect_contradictions", boom)
    summary = cr.resolve_contradictions(live=True)   # maa ALDRIG kaste
    assert summary["error"] is True
