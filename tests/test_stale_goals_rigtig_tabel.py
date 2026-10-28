"""Stale-mål-vagten skal læse de mål der FINDES — ikke en tom tabel.

BAGGRUND (28/10-2026). Bjørn spurgte om 4 af 5 langtidsmål var stale.
Målingen gav ham ret, og afslørede to fejl oveni hinanden:

1. `detect_stale_goals()` læste `autonomous_goals.list_goals(status="active")`
   — en tabel med 0 aktive rækker. De fem aktive mål lå i `long_horizon_goals`,
   som er den tabel prompten viser. Vagten svarede derfor altid `[]` og kunne
   pr. konstruktion ikke fange noget.
2. Tærsklen var 3 dage. For et LANGTIDSMÅL er det for stramt: alle fem mål var
   altid «stale», og så ignorerer man signalet.

3. `format_active_goals_for_heartbeat()` viste titel + procent, men ikke alder.
   Et mål på 70 % der ikke havde rørt sig siden 11. maj læste som «næsten i
   mål» i stedet for «forladt».

Disse tests værner alle tre.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.services import agent_self_evaluation as ase
from core.services import long_horizon_goals as lhg


def _iso(days_ago: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days_ago)).isoformat()


def test_taersklen_er_14_dage_ikke_3() -> None:
    """3 dage gjorde alle langtidsmål stale — signalet blev konstant støj."""
    assert ase._GOAL_STALE_DAYS == 14


def test_vagten_laeser_long_horizon_goals(monkeypatch) -> None:
    """MODPRØVE: hvis nogen peger vagten tilbage på den tomme tabel, fanges det.

    Vi giver `long_horizon_goals` et gammelt mål. Kan vagten ikke se det, læser
    den et andet sted — og så er den ikke en vagt.
    """
    monkeypatch.setattr(
        lhg,
        "list_active_goals",
        lambda limit=50: [
            {"goal_id": "g-gammel", "title": "Gammelt mål", "priority": 50, "updated_at": _iso(40)},
        ],
    )
    stale = ase.detect_stale_goals()
    assert [g["goal_id"] for g in stale] == ["g-gammel"]


def test_friskt_maal_er_ikke_stale(monkeypatch) -> None:
    """Et mål rørt for 9 dage siden må IKKE meldes stale med 14-dages tærskel.

    Det er præcis forskellen der gør tallet læsbart: 4 af 5, ikke 5 af 5.
    """
    monkeypatch.setattr(
        lhg,
        "list_active_goals",
        lambda limit=50: [
            {"goal_id": "g-frisk", "title": "Ni dage", "priority": 50, "updated_at": _iso(9)},
        ],
    )
    assert ase.detect_stale_goals() == []


def test_alderen_vises_i_heartbeat_linjen(monkeypatch) -> None:
    """Procenten er et løfte om fremskridt; alderen er beviset for om der skete noget."""
    monkeypatch.setattr(
        lhg,
        "_db_list_goals",
        lambda status="active", limit=5: [
            {"goal_id": "g1", "title": "Forladt mål", "progress_pct": 70, "updated_at": _iso(170)},
        ],
    )
    linje = lhg.format_active_goals_for_heartbeat(max_goals=5)
    assert "170d" in linje, linje
    assert "Forladt mål" in linje


def test_ukendt_tidsstempel_ser_ikke_friskt_ud(monkeypatch) -> None:
    """MODPRØVE: manglende tid må ikke give alder 0 — det ville lyve om friskhed."""
    monkeypatch.setattr(
        lhg,
        "_db_list_goals",
        lambda status="active", limit=5: [
            {"goal_id": "g1", "title": "Uden tid", "progress_pct": 10, "updated_at": None},
        ],
    )
    linje = lhg.format_active_goals_for_heartbeat(max_goals=5)
    assert "· 0d" not in linje
    assert lhg._alder_dage(None) is None
