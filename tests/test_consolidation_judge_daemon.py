"""Tests for core.services.consolidation_judge_daemon — oprydnings-grenene.

Dækker to fejl målt 5/10-2026:

  1. `_enforce_reject` importerede `update_decision_status`, som ikke findes
     NOGEN steder i kodebasen. ImportError blev slugt af `except Exception`,
     så hele revoke-grenen var død kode — den kunne aldrig rydde noget.
     Den rigtige funktion er `set_status`.

  2. `list_decisions(status="active", limit=50)` skjulte de nederste 30 af 80
     aktive beslutninger. Sorteringen er `priority DESC`, så skæringen flyttede
     sig — og en beslutning der skulle ryddes kunne ligge i det skjulte bånd.
"""
from __future__ import annotations


def _alle_aktive(n: int = 60, graense: int = 50) -> list[dict]:
    return [
        {
            "decision_id": f"d{i}",
            "directive": f"x{i}",
            "priority": 100 - i,
            "adherence_score": (0.1 if i >= graense else 0.9),
        }
        for i in range(n)
    ]


def _falsk_liste(alle: list[dict], *, status: str = "active", limit: int | None = 50):
    """Respekterer `limit` — så testen kun består når grenen spørger uden grænse."""
    raekker = sorted(alle, key=lambda d: -int(d["priority"]))
    return raekker if limit is None else raekker[: int(limit)]


def _stille_bus(monkeypatch) -> None:
    """Daemp `publish` PAA det aegte bus-objekt — udskift ikke modul-navnet.

    MAALT 6/10-2026: den gamle udgave gjorde `monkeypatch.setattr(cjd,
    "event_bus", _StilleBus)`. `cjd.event_bus` ER singletonen
    (`cjd.event_bus is bus.event_bus`), saa lappen lagde en attrappe ind i
    modulet. Et modul der importeres FOERSTE gang i det vindue binder
    attrappen for altid — og `monkeypatch` gendanner kun modul-navnet, aldrig
    kopien inde i det modul der naaede at importere den. Vagten
    `test_event_bus_singleton_maa_ikke_udskiftes.py` fangede det.

    At lappe metoden paa det aegte objekt rammer enhver der holder bussen,
    foer eller efter — og `monkeypatch` ruller den tilbage.
    """
    from core.services import consolidation_judge_daemon as cjd

    monkeypatch.setattr(cjd.event_bus, "publish", lambda *_a, **_k: None,
                        raising=False)


def test_set_status_findes_i_db_decisions():
    """Revoke-grenen importerer `set_status` — den SKAL findes i butikken."""
    from core.runtime import db_decisions

    assert hasattr(db_decisions, "set_status"), (
        "revoke-grenen importerer en funktion der ikke findes — grenen dør i stilhed"
    )


def test_revoke_kalder_set_status_for_alle_aktive(monkeypatch):
    """Grenen skal VIRKE og se hele listen — ikke kun de første 50."""
    from core.runtime import db_decisions
    from core.services import consolidation_judge_daemon as cjd

    alle = _alle_aktive()
    revoked: list[tuple[str, str]] = []

    monkeypatch.setattr(db_decisions, "list_decisions",
                        lambda **kw: _falsk_liste(alle, **kw))
    monkeypatch.setattr(db_decisions, "set_status",
                        lambda did, st: revoked.append((did, st)) or {})
    _stille_bus(monkeypatch)

    cjd._enforce_reject({"item_type": "broken_decisions", "choice": "revoke"})

    assert revoked, "revoke-grenen gjorde intet — importen eller kaldet fejler"
    assert ("d50", "revoked") in revoked, (
        "beslutningen laa uden for de foerste 50 — skaeringen skjuler den for oprydningen"
    )


def test_recommit_ser_alle_aktive(monkeypatch):
    """Samme skaering i recommit-grenen."""
    from core.runtime import db_decisions
    from core.services import consolidation_judge_daemon as cjd

    alle = _alle_aktive()
    limits: list[object] = []

    def fanger(**kw):
        limits.append(kw.get("limit"))
        return _falsk_liste(alle, **kw)

    monkeypatch.setattr(db_decisions, "list_decisions", fanger)
    _stille_bus(monkeypatch)

    cjd._enforce_accept({"item_type": "broken_decisions", "choice": "recommit"})

    assert limits, "recommit-grenen kaldte ikke list_decisions"
    assert all(lim is None for lim in limits), (
        f"grenen spoerger med en graense ({limits}) — den skjuler beslutninger"
    )
