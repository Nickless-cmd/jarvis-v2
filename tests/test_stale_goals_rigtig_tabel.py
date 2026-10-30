"""Stale-mål-vagten skal måle FREMSKRIDT — ikke rørelse, og ikke en tom tabel.

BAGGRUND (28/10-2026). Bjørn spurgte om 4 af 5 langtidsmål var stale.
Målingen gav ham ret, og afslørede tre fejl oveni hinanden:

1. `detect_stale_goals()` læste `autonomous_goals.list_goals(status="active")`
   — en tabel med 0 aktive rækker. De fem aktive mål lå i `long_horizon_goals`,
   som er den tabel prompten viser. Vagten svarede derfor altid `[]` og kunne
   pr. konstruktion ikke fange noget.
2. Tærsklen var 3 dage. For et LANGTIDSMÅL er det for stramt: alle fem mål var
   altid «stale», og så ignorerer man signalet.
3. `format_active_goals_for_heartbeat()` viste titel + procent, men ikke alder.
   Et mål på 70 % der ikke havde rørt sig siden 11. maj læste som «næsten i
   mål» i stedet for «forladt».

OG EN FJERDE, som jeg selv lavede bagefter: fixet målte `updated_at`, altså
RØRELSE. Da jeg skrev en statusnote på de forladte mål — en note der SAGDE at
de var forladte — flyttede `updated_at` sig, og vagten svarede pludselig 0.
Vagten kunne gøres blind ved at skrive til den. Nu måles kun opdateringer med
`progress_delta`; et mål uden en enkelt sådan måles fra `created_at`.

Disse tests værner alle fire.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.services import agent_self_evaluation as ase
from core.services import long_horizon_goals as lhg


def _iso(days_ago: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days_ago)).isoformat()


def _maal(goal_id: str, *, title: str = "Mål", created_days_ago: int | None = 60,
          updated_days_ago: int | None = None) -> dict:
    g: dict = {"goal_id": goal_id, "title": title, "priority": 50}
    if created_days_ago is not None:
        g["created_at"] = _iso(created_days_ago)
    if updated_days_ago is not None:
        g["updated_at"] = _iso(updated_days_ago)
    return g


def test_taersklen_er_14_dage_ikke_3() -> None:
    """3 dage gjorde alle langtidsmål stale — signalet blev konstant støj."""
    assert ase._GOAL_STALE_DAYS == 14


def test_vagten_laeser_long_horizon_goals(monkeypatch) -> None:
    """MODPRØVE: hvis nogen peger vagten tilbage på den tomme tabel, fanges det."""
    monkeypatch.setattr(lhg, "list_active_goals", lambda limit=50: [_maal("g-gammel", created_days_ago=40)])
    monkeypatch.setattr(lhg, "last_progress_map", lambda ids: {})
    stale = ase.detect_stale_goals()
    assert [g["goal_id"] for g in stale] == ["g-gammel"]


def test_friskt_maal_er_ikke_stale(monkeypatch) -> None:
    """Et mål med fremskridt for 9 dage siden må IKKE meldes stale (tærskel 14)."""
    monkeypatch.setattr(lhg, "list_active_goals", lambda limit=50: [_maal("g-frisk", created_days_ago=200)])
    monkeypatch.setattr(lhg, "last_progress_map", lambda ids: {"g-frisk": _iso(9)})
    assert ase.detect_stale_goals() == []


def test_note_uden_delta_goer_ikke_maalet_friskt(monkeypatch) -> None:
    """MODPRØVE — kernen i fixet.

    Målet er rørt i dag (`updated_at` = nu), fordi nogen skrev en note. Men
    noten flyttede ingen procent: sidste reelle fremskridt er 170 dage gammelt.
    Måler vagten `updated_at`, svarer den 0 — og så kan den gøres blind ved at
    skrive til den. Den skal stadig melde målet.
    """
    monkeypatch.setattr(
        lhg,
        "list_active_goals",
        lambda limit=50: [_maal("g-note", created_days_ago=170, updated_days_ago=0)],
    )
    monkeypatch.setattr(lhg, "last_progress_map", lambda ids: {"g-note": _iso(170)})
    stale = ase.detect_stale_goals()
    assert [g["goal_id"] for g in stale] == ["g-note"]
    assert stale[0]["basis"] == "progress"
    assert stale[0]["days_stale"] >= 169


def test_maal_uden_fremskridt_maales_fra_oprettelsen(monkeypatch) -> None:
    """Et mål der aldrig har flyttet sig er forladt fra fødslen, ikke friskt."""
    monkeypatch.setattr(lhg, "list_active_goals", lambda limit=50: [_maal("g-nul", created_days_ago=29)])
    monkeypatch.setattr(lhg, "last_progress_map", lambda ids: {})
    stale = ase.detect_stale_goals()
    assert stale and stale[0]["basis"] == "created"
    assert stale[0]["days_stale"] >= 28


def test_ukendt_tidsstempel_skjules_ikke(monkeypatch) -> None:
    """Kan alderen ikke måles, må målet ikke forsvinde ud af vagten."""
    monkeypatch.setattr(lhg, "list_active_goals", lambda limit=50: [_maal("g-uden-tid", created_days_ago=None)])
    monkeypatch.setattr(lhg, "last_progress_map", lambda ids: {})
    stale = ase.detect_stale_goals()
    assert [g["goal_id"] for g in stale] == ["g-uden-tid"]
    assert stale[0]["days_stale"] is None


def test_blandede_tidsformater_er_samme_tid() -> None:
    """MODPRØVE: `Z` og `+00:00` er samme tidspunkt — og kan ikke sammenlignes som strenge.

    Målt i `causal_edges`: 102.419 rækker med `Z`, resten med `+00:00`, i samme
    kolonne. Falder `Z`-håndteringen ud, er sammenligningen lexikografisk og
    dermed tilfældig.
    """
    a = ase._parse_ts("2026-10-14T20:00:00Z")
    b = ase._parse_ts("2026-10-14T20:00:00+00:00")
    assert a == b
    assert a is not None and a.tzinfo is not None
    assert ase._parse_ts("ikke en tid") is None
    assert ase._parse_ts(None) is None


def test_sektionen_viser_grundlaget(monkeypatch) -> None:
    """«uden fremskridt» skal kunne læses som hvad den er — og alderen skal med."""
    monkeypatch.setattr(
        ase,
        "detect_stale_goals",
        lambda **kw: [
            {"goal_id": "a", "title": "Aldrig flyttet", "priority": 70, "days_stale": 29, "basis": "created"},
            {"goal_id": "b", "title": "Stoppet", "priority": 50, "days_stale": 170, "basis": "progress"},
        ],
    )
    s = ase.stale_goals_section()
    assert s is not None
    assert "intet fremskridt siden oprettelse · 29d" in s
    assert "sidste fremskridt · 170d" in s


def test_sektionen_er_tav_naar_alt_er_friskt(monkeypatch) -> None:
    monkeypatch.setattr(ase, "detect_stale_goals", lambda **kw: [])
    assert ase.stale_goals_section() is None


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
