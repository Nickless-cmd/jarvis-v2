"""Hjerteslagets sansning skal se aktive mål — uanset hvilken butik de bor i.

MÅLT 29/10-2026 (Bjørn: «heartbeat står på productive_idle i 90+ minutter»):

    heartbeat_runtime_ticks: 17:42, 17:57, 18:12, 18:27, 18:42 → alle
    `ok` / `productive_idle`, med `blocked_reason` = NULL. Sidste faktiske
    beslutning var 17:13. Imens stod 5 initiativer i køen.

Årsagen var ikke en tom kø, ikke en blokeret gate og ikke en model der valgte
idle. `act_phase` er ren heuristik: er `reflection["priorities"]` tom, går den
til `productive_idle`. Og `advance_goals`-grenen i `_identify_priorities`
kiggede på `signals["active_goals"]`, som `sense_phase` fyldte fra
`autonomous_goals` — en JSON-butik med **3.691 mål, alle i `pending`, nul i
`active`**, og ingen kode promoverer dem. Den butik der faktisk havde et aktivt
mål (`long_horizon_goals`, DB-tabellen) blev aldrig læst.

Grenen kunne altså aldrig fyre. Det er samme fejlform som guard-emitteren: en
mekanisme der ser rigtig ud i koden og hvis indgangsbetingelse intet kan
opfylde. Disse tests holder den levende.
"""
from __future__ import annotations

from core.services import autonomous_goals, long_horizon_goals
from core.services.heartbeat_phases import (
    _aktive_maal,
    _identify_priorities,
    sense_phase,
)


def _maal(goal_id: str, title: str, priority: str = "high") -> dict:
    return {"goal_id": goal_id, "title": title, "priority": priority}


def _tom_autonom(monkeypatch) -> None:
    """Efterlign den målte tilstand: butikken har intet aktivt mål."""
    monkeypatch.setattr(
        autonomous_goals, "list_goals", lambda **kw: [], raising=True,
    )


def test_aktive_maal_laeser_langhorisont_naar_den_andre_butik_er_tom(monkeypatch):
    """Det præcise målte tilfælde: aktivt mål findes KUN i long_horizon_goals."""
    _tom_autonom(monkeypatch)
    monkeypatch.setattr(
        long_horizon_goals, "list_active_goals",
        lambda **kw: [_maal("goal_f49be41158cf", "Bevis pålidelighed over tid", "100")],
        raising=True,
    )

    maal = _aktive_maal(limit=5)

    assert len(maal) == 1
    assert maal[0]["goal_id"] == "goal_f49be41158cf"


def test_aktive_maal_laeser_begge_butikker(monkeypatch):
    """Et mål i hver butik skal begge med — ingen butik er enerådende."""
    monkeypatch.setattr(
        autonomous_goals, "list_goals",
        lambda **kw: [_maal("a-1", "Fra den gamle butik")], raising=True,
    )
    monkeypatch.setattr(
        long_horizon_goals, "list_active_goals",
        lambda **kw: [_maal("b-1", "Fra den levende butik")], raising=True,
    )

    ids = {m["goal_id"] for m in _aktive_maal(limit=5)}

    assert ids == {"a-1", "b-1"}


def test_aktive_maal_dedup_paa_goal_id(monkeypatch):
    """Samme mål i begge butikker må ikke tælles to gange."""
    ens = _maal("goal-samme", "Samme mål")
    monkeypatch.setattr(autonomous_goals, "list_goals", lambda **kw: [ens], raising=True)
    monkeypatch.setattr(long_horizon_goals, "list_active_goals", lambda **kw: [ens], raising=True)

    assert len(_aktive_maal(limit=5)) == 1


def test_aktive_maal_taaler_at_en_butik_kaster(monkeypatch):
    """En brækkende butik må ikke gøre sansningen blind for den anden."""
    def _braek(**kw):
        raise RuntimeError("butik nede")

    monkeypatch.setattr(autonomous_goals, "list_goals", _braek, raising=True)
    monkeypatch.setattr(
        long_horizon_goals, "list_active_goals",
        lambda **kw: [_maal("b-1", "Den raske butik")], raising=True,
    )

    maal = _aktive_maal(limit=5)

    assert [m["goal_id"] for m in maal] == ["b-1"]


def test_prioritering_fyrer_naar_maalet_kun_ligger_i_langhorisont(monkeypatch):
    """Regressionen: uden denne gren gik hjerteslaget til productive_idle."""
    _tom_autonom(monkeypatch)
    monkeypatch.setattr(
        long_horizon_goals, "list_active_goals",
        lambda **kw: [_maal("goal_f49be41158cf", "Bevis pålidelighed over tid")],
        raising=True,
    )

    # Præcis den tilstand de seks målte tik stod i: ingen fejl, intet pres,
    # ingen fejl-verifikationer — kun et aktivt mål.
    priorities = _identify_priorities({
        "failed_verifies": 0,
        "unverified_mutations": 0,
        "context_pressure_level": "comfortable",
        "errors_last_hour": 0,
        "active_goals": _aktive_maal(limit=5),
    })

    assert "advance_goals" in priorities


def test_sense_phase_ser_maalet_i_langhorisont_butikken(monkeypatch):
    """Enden af kæden: signalet hjerteslaget læser, skal indeholde målet."""
    _tom_autonom(monkeypatch)
    monkeypatch.setattr(
        long_horizon_goals, "list_active_goals",
        lambda **kw: [_maal("goal_f49be41158cf", "Bevis pålidelighed over tid")],
        raising=True,
    )

    signals = sense_phase(name="test")

    titler = [g.get("title") for g in signals.get("active_goals") or []]
    assert "Bevis pålidelighed over tid" in titler
