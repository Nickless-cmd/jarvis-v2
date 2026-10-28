"""Langtidsmålene — den tabel prompten viser, og den alder der gør dem læsbare.

BAGGRUND (28/10-2026). Bjørn spurgte om 4 af 5 langtidsmål var stale. Målingen
gav ham ret og afslørede at heartbeat-linjen viste titel + procent, men IKKE
alder — så et mål på 70 % der ikke havde rørt sig siden 11. maj læste som
«næsten i mål» i stedet for «forladt».

Disse tests værner:
  * at alderen faktisk vises i heartbeat-linjen
  * at et ukendt tidsstempel giver None (ukendt), ikke 0 (friskt)
  * at `update_goal` kan sætte status til `abandoned` — den vej
    konsoliderings-dommeren bruger
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.services import long_horizon_goals as lhg


def _iso(days_ago: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days_ago)).isoformat()


def test_alder_dage_beregner_dage() -> None:
    assert lhg._alder_dage(_iso(170)) == 170
    assert lhg._alder_dage(_iso(0)) == 0


def test_alder_dage_ukendt_giver_none_ikke_nul() -> None:
    """MODPRØVE: et manglende tidsstempel må ikke se friskt ud."""
    assert lhg._alder_dage(None) is None
    assert lhg._alder_dage("") is None
    assert lhg._alder_dage("ikke-en-dato") is None


def test_alder_dage_fremtid_klippes_til_nul() -> None:
    """Et tidsstempel i fremtiden (ur-skævhed) må ikke give negativ alder."""
    frem = (datetime.now(UTC) + timedelta(days=3)).isoformat()
    assert lhg._alder_dage(frem) == 0


def test_heartbeat_linjen_viser_alder(monkeypatch) -> None:
    """Procenten er et løfte om fremskridt; alderen er beviset for om der skete noget."""
    monkeypatch.setattr(
        lhg,
        "_db_list_goals",
        lambda status="active", limit=5: [
            {"goal_id": "g1", "title": "Forladt mål", "progress_pct": 70, "updated_at": _iso(170)},
        ],
    )
    linje = lhg.format_active_goals_for_heartbeat(max_goals=5)
    assert "Forladt mål (70%)" in linje, linje
    assert "170d" in linje, linje


def test_heartbeat_uden_tid_viser_ingen_alder(monkeypatch) -> None:
    """MODPRØVE: hellere ingen alder end en falsk «0d»."""
    monkeypatch.setattr(
        lhg,
        "_db_list_goals",
        lambda status="active", limit=5: [
            {"goal_id": "g1", "title": "Uden tid", "progress_pct": 10, "updated_at": None},
        ],
    )
    linje = lhg.format_active_goals_for_heartbeat(max_goals=5)
    assert "· 0d" not in linje, linje
    assert "Uden tid (10%)" in linje, linje


def test_heartbeat_tom_naar_ingen_maal(monkeypatch) -> None:
    monkeypatch.setattr(lhg, "_db_list_goals", lambda status="active", limit=5: [])
    assert lhg.format_active_goals_for_heartbeat() == ""


def test_update_goal_kan_abandonne(monkeypatch) -> None:
    """Dommerens «abandon» skal kunne ramme denne tabel — ellers er den tavs."""
    kaldt: dict[str, object] = {}

    def _fake_append(**kw):
        kaldt.update(kw)
        return {"goal_id": kw.get("goal_id"), "status": kw.get("new_status")}

    monkeypatch.setattr(lhg, "append_goal_update", _fake_append)
    res = lhg.update_goal(
        goal_id="g1",
        note="forladt af konsoliderings-dommeren: ingen fremdrift",
        new_status="abandoned",
        source="consolidation_judge",
    )
    assert res is not None
    assert kaldt["new_status"] == "abandoned"
    assert kaldt["goal_id"] == "g1"
