"""Test: pending-plans-sektion dropper vane-halen (Jarvis-spec 2026-06-23 #9)."""
from __future__ import annotations

from core.services import plan_proposals as pp


def test_no_list_plans_habit_tail():
    # Kerne-check (#9): uanset om der er ægte plans eller ej, MÅ vane-halen
    # "Brug list_plans for detaljer..." ikke længere optræde i sektionen.
    section = pp.all_pending_plans_section()
    if section is not None:
        assert "list_plans" not in section
        assert "for detaljer" not in section


# ── Regression 2026-08-30: afviste planer må ikke genopstå ved genstart ──
# Problemet: dedup tjekkede kun awaiting_approval, så en dismissed/superseded
# plan med samme titel blev foreslået igen ved hver restart.


def test_dismissed_plan_same_title_blocks_reproposal(tmp_path, monkeypatch):
    from datetime import UTC, datetime, timedelta
    from core.services import plan_proposals as pp

    state = {
        "plan-old": {
            "plan_id": "plan-old",
            "session_id": "_default",
            "title": "1 provider(e) kronisk ikke-tilgængelige",
            "status": "dismissed",
            "created_at": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
            "steps": ["a"],
        }
    }
    monkeypatch.setattr(pp, "_load_all", lambda: state)
    monkeypatch.setattr(pp, "_save_all", lambda d: state.update(d))

    res = pp.propose_plan(
        session_id="_default",
        title="1 provider(e) kronisk ikke-tilgængelige",
        why="samme titel igen",
        steps=["b"],
    )
    assert res.get("status") == "skipped_duplicate"
    assert res.get("existing_status") == "dismissed"


def test_superseded_plan_same_title_blocks_reproposal(tmp_path, monkeypatch):
    from datetime import UTC, datetime, timedelta
    from core.services import plan_proposals as pp

    state = {
        "plan-old": {
            "plan_id": "plan-old",
            "session_id": "_default",
            "title": "Noget helt andet",
            "status": "superseded",
            "created_at": (datetime.now(UTC) - timedelta(days=2)).isoformat(),
            "steps": ["a"],
        }
    }
    monkeypatch.setattr(pp, "_load_all", lambda: state)
    monkeypatch.setattr(pp, "_save_all", lambda d: state.update(d))

    res = pp.propose_plan(
        session_id="_default",
        title="Noget helt andet",
        why="igen",
        steps=["b"],
    )
    assert res.get("status") == "skipped_duplicate"


def test_old_dismissed_plan_beyond_window_allows_reproposal(tmp_path, monkeypatch):
    # Efter 30 dage må samme titel foreslås igen — problemet kan være reelt.
    from datetime import UTC, datetime, timedelta
    from core.services import plan_proposals as pp

    state = {
        "plan-old": {
            "plan_id": "plan-old",
            "session_id": "_default",
            "title": "Gammel plan",
            "status": "dismissed",
            "created_at": (datetime.now(UTC) - timedelta(days=40)).isoformat(),
            "steps": ["a"],
        }
    }
    monkeypatch.setattr(pp, "_load_all", lambda: state)
    monkeypatch.setattr(pp, "_save_all", lambda d: state.update(d))

    res = pp.propose_plan(
        session_id="_default",
        title="Gammel plan",
        why="igen efter lang tid",
        steps=["b"],
    )
    assert res.get("status") == "ok"
