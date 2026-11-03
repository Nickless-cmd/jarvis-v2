"""Vagt for glemsels-wiringen i recall (3/11-2026).

Baggrund (målt): `get_relevant_experiential_memories` filtrerede på
`WHERE decay_score < 0.9` i `cognitive_experiential_memories`. Den kolonne
skrives kun ÉT sted i koden — `db_experiential_memory.py:71`, som sætter den
til `0.0` ved forstærkning. Målt i den levende DB: 9 rækker, NUL med
`decay_score > 0`, max 0,0. Filteret matchede altså hver eneste række og
udelukkede intet: det påstod en glemsel der ikke fandtes i den tabel.

Den ægte henfald bor i `forgetting_curve`-registret, nøglet på
`sha256(focus|summary)[:16]` med `content_preview` som første 100 tegn af
indholdet. De to systemer deler navn, men ikke nøglerum — broen er
`content_preview`, som kan matches mod rækkens egen tekst.

Vagterne her låser at recall bruger den ÆGTE decay, og at en faldet post
faktisk udelades. Uden dem kan filteret glide tilbage til at læse en kolonne
der altid står på nul, og se ud som om det virker.
"""
from __future__ import annotations

import pytest

from core.runtime import db_runtime_misc as misc


class _Row(dict):
    """sqlite3.Row-lignende: indeksérbar på kolonnenavn."""

    def __getitem__(self, key):
        return dict.__getitem__(self, key)


def _raekke(memory_id: str, tekst: str, *, importance: float = 0.5) -> _Row:
    return _Row(
        memory_id=memory_id,
        narrative=tekst,
        user_mood="neutral",
        key_lesson="",
        topic="",
        importance=importance,
        decay_score=0.0,  # kolonnen der altid står på nul
        reinforcement_count=0,
        created_at="2026-11-03T00:00:00+00:00",
    )


@pytest.fixture
def stub_db(monkeypatch):
    """Erstat DB-laget så testen måler filtreringen, ikke databasen."""
    raekker: list[_Row] = []

    class _Conn:
        def execute(self, *_a, **_k):
            return type("Cur", (), {"fetchall": lambda self: list(raekker)})()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(misc, "connect", lambda: _Conn())
    monkeypatch.setattr(
        "core.runtime.db_cognitive._ensure_cognitive_experiential_memories_table",
        lambda conn: None,
    )
    return raekker


def _stub_register(monkeypatch, register: dict) -> None:
    monkeypatch.setattr(
        "core.services.forgetting_curve._load", lambda: register
    )


def test_faldet_post_udelades(stub_db, monkeypatch):
    """En post hvis preview står i registeret med decay >= 0,9 skal væk.

    Det er hele pointen: før blev den aldrig udelukket, uanset hvor faldet den
    var, fordi filteret læste en kolonne der altid er 0,0.
    """
    stub_db.append(_raekke("exp-1", "en faldet erindring om et gammelt emne"))
    stub_db.append(_raekke("exp-2", "en frisk erindring om noget andet"))
    _stub_register(monkeypatch, {
        "h1": {"content_preview": "en faldet erindring om et gammelt emne", "decay_score": 0.95},
        "h2": {"content_preview": "en frisk erindring om noget andet", "decay_score": 0.10},
    })

    resultat = misc.get_relevant_experiential_memories(context="erindring", limit=5)
    ids = [m["memory_id"] for m in resultat]
    assert "exp-1" not in ids, "faldet post slap igennem filteret"
    assert "exp-2" in ids


def test_decay_kommer_fra_registeret_ikke_kolonnen(stub_db, monkeypatch):
    """Den returnerede decay skal være registerets tal, ikke kolonnens nul."""
    stub_db.append(_raekke("exp-1", "en erindring med maalt henfald"))
    _stub_register(monkeypatch, {
        "h1": {"content_preview": "en erindring med maalt henfald", "decay_score": 0.42},
    })

    resultat = misc.get_relevant_experiential_memories(context="erindring", limit=5)
    assert len(resultat) == 1
    assert resultat[0]["decay_score"] == pytest.approx(0.42)


def test_usporet_raekke_faar_decay_nul(stub_db, monkeypatch):
    """En række registeret ikke kender er ikke falmende — den er usporet.

    Målt 3/11: 0 af 9 SQL-rækker matchede et register-preview. De to systemer
    sporer helt forskellige erindringer, så fravær af match er det normale —
    og må ikke tolkes som henfald.
    """
    stub_db.append(_raekke("exp-1", "en erindring ingen har sporet"))
    _stub_register(monkeypatch, {
        "h1": {"content_preview": "noget helt andet indhold", "decay_score": 0.99},
    })

    resultat = misc.get_relevant_experiential_memories(context="erindring", limit=5)
    assert len(resultat) == 1
    assert resultat[0]["decay_score"] == 0.0


def test_manglende_register_goer_recall_blind_ikke_doed(stub_db, monkeypatch):
    """Kaster registeret, skal recall stadig svare med decay 0."""
    stub_db.append(_raekke("exp-1", "en erindring"))

    def _braek():
        raise RuntimeError("register utilgængeligt")

    monkeypatch.setattr("core.services.forgetting_curve._load", _braek)

    resultat = misc.get_relevant_experiential_memories(context="erindring", limit=5)
    assert len(resultat) == 1
    assert resultat[0]["decay_score"] == 0.0
