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


# ── Prune 2026-09-13: registret må ikke vokse ubegrænset ───────────────────
# Målt: 181 planer, hvoraf 173 var den samme auto-plan med skiftende score i
# titlen. Titlerne er nu stabile (fix 9e17b4b9), så floden er væk; men
# terminale planer blev aldrig fjernet. Prune holder registret begrænset —
# og må ALDRIG fjerne et dedup-anker, for så ville planen genopstå.


def _fake_store(monkeypatch, initial):
    """Ægte semantik: _save_all erstatter lageret (som save_json gør).

    De eksisterende tests bruger ``state.update(d)``, som ikke sletter noget —
    til prune-tests ville det skjule præcis det vi måler.
    """
    holder = {"d": {k: dict(v) for k, v in initial.items()}}
    monkeypatch.setattr(pp, "_load_all", lambda: holder["d"])
    monkeypatch.setattr(pp, "_save_all", lambda d: holder.__setitem__("d", dict(d)))
    return holder


def _plan(pid, status, *, created_days_ago=0.0, resolved_days_ago=None, title="T"):
    from datetime import UTC, datetime, timedelta

    rec = {
        "plan_id": pid,
        "session_id": "_default",
        "title": title,
        "status": status,
        "created_at": (datetime.now(UTC) - timedelta(days=created_days_ago)).isoformat(),
        "steps": ["a"],
    }
    if resolved_days_ago is not None:
        rec["resolved_at"] = (
            datetime.now(UTC) - timedelta(days=resolved_days_ago)
        ).isoformat()
    return rec


def test_prune_fjerner_gamle_superseded(monkeypatch):
    state = {
        f"plan-old{i}": _plan(f"plan-old{i}", "superseded", created_days_ago=90 + i)
        for i in range(60)
    }
    holder = _fake_store(monkeypatch, state)

    res = pp.propose_plan(session_id="_default", title="Ny plan", why="x", steps=["a"])

    assert res["status"] == "ok"
    assert res["plan_id"] in holder["d"]
    # 50 arkiverede + den nye ventende — ikke 61.
    assert len(holder["d"]) == pp._MAX_ARCHIVED_PLANS + 1


def test_prune_bevarer_de_nyeste_terminale(monkeypatch):
    state = {
        f"plan-{i:03d}": _plan(f"plan-{i:03d}", "superseded", created_days_ago=60 + i)
        for i in range(60)
    }
    holder = _fake_store(monkeypatch, state)

    pp.propose_plan(session_id="_default", title="Ny", why="x", steps=["a"])

    assert "plan-000" in holder["d"]  # nyeste
    assert "plan-049" in holder["d"]
    assert "plan-050" not in holder["d"]  # ældste ryger
    assert "plan-059" not in holder["d"]


def test_prune_beholder_ikke_terminale_planer(monkeypatch):
    # En ventende/godkendt plan må ALDRIG prunes, uanset alder.
    state = {
        "plan-live": _plan("plan-live", "awaiting_approval", created_days_ago=400),
        "plan-approved": _plan("plan-approved", "approved", created_days_ago=400),
        **{
            f"plan-s{i}": _plan(f"plan-s{i}", "superseded", created_days_ago=200 + i)
            for i in range(60)
        },
    }
    holder = _fake_store(monkeypatch, state)

    pp.propose_plan(session_id="_other", title="Noget nyt", why="x", steps=["a"])

    assert "plan-live" in holder["d"]
    assert "plan-approved" in holder["d"]


def test_prune_goer_ikke_dedup_blind(monkeypatch):
    """Den afgørende invariant: et dedup-anker må ikke prunes væk.

    Pruned vi et anker inden for vinduet, ville planen genopstå — præcis
    bugen fixet 2026-08-30 lukkede.
    """
    anchor = _plan(
        "plan-anker",
        "dismissed",
        created_days_ago=29,
        title="Heartbeat tick-kvalitet er degraderende",
    )
    filler = {
        f"plan-f{i}": _plan(f"plan-f{i}", "superseded", created_days_ago=100 + i)
        for i in range(80)
    }
    holder = _fake_store(monkeypatch, {**filler, "plan-anker": anchor})

    res = pp.propose_plan(
        session_id="_default",
        title="Heartbeat tick-kvalitet er degraderende",
        why="igen",
        steps=["a"],
    )

    assert res["status"] == "skipped_duplicate"
    assert "plan-anker" in holder["d"]


def test_prune_beholder_sent_loest_plan(monkeypatch):
    # Gammel plan, men løst for nylig → bevares som historik. Prune er en
    # SIKKER OVERMÆNGDE: den beholder alt dedup kan få brug for, og mere.
    # NB: dedup'en matcher selv på created_at, så denne plan blokerer ikke et
    # nyt forslag — præeksisterende adfærd, ikke prunens sag. Det vigtige er
    # at prune ikke fjerner noget dedup kunne have brug for.
    anchor = _plan(
        "plan-sent",
        "dismissed",
        created_days_ago=200,
        resolved_days_ago=3,
        title="Sent loest",
    )
    filler = {
        f"plan-f{i}": _plan(f"plan-f{i}", "superseded", created_days_ago=100 + i)
        for i in range(80)
    }
    holder = _fake_store(monkeypatch, {**filler, "plan-sent": anchor})

    pp.propose_plan(session_id="_default", title="Noget andet", why="x", steps=["a"])

    assert "plan-sent" in holder["d"]
    assert len(holder["d"]) == pp._MAX_ARCHIVED_PLANS + 2


def test_revise_plan_pruner_ogsaa(monkeypatch):
    # Revision er en anden skrive-vej ind i samme register — den skal også prune.
    base = _plan("plan-base", "approved", created_days_ago=1)
    filler = {
        f"plan-f{i}": _plan(f"plan-f{i}", "superseded", created_days_ago=100 + i)
        for i in range(80)
    }
    holder = _fake_store(monkeypatch, {**filler, "plan-base": base})

    res = pp.revise_plan(
        plan_id="plan-base", session_id="_default", reason="nyt", new_steps=["b"]
    )

    assert res["status"] == "ok"
    # base + ny revision + 50 arkiverede
    assert len(holder["d"]) == pp._MAX_ARCHIVED_PLANS + 2
