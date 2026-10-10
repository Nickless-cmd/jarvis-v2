"""En fyret `schedule_task` skal efterlade en VARIG række i indbakken.

Bjørn 10/10-2026: «så skal vi sørge for dit reminder tool faktisk når din
inbox.» Målt samme dag: `schedule_task` skriver til `scheduled_tasks` og fyrer
via nudge → initiativkø → autonomt run — men rører ALDRIG `inbox_items`.
Indbakken viste opgaven som «PÅ VEJ» laest fra `scheduled_tasks`-tabellen, saa
rækken forsvandt i samme øjeblik opgaven fyrede. Efter fyringen fandtes der
intet spor i indbakken af at noget var lovet og indfriet.

Reglen her: registreringen sker ved FYRINGEN (ikke ved bookingen), fordi det er
dér posten bliver aktuel. `scheduled` staar i `IKKE_GATENDE_KILDETYPER` — en
planlagt opgave er husets, ikke en forpligtelse der maa naegte en mutation.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

import pytest

from core.runtime import db_inbox


@pytest.fixture
def inbox_db(monkeypatch, tmp_path):
    sti = tmp_path / "sched.db"

    @contextmanager
    def _connect():
        k = sqlite3.connect(sti)
        k.row_factory = sqlite3.Row
        try:
            yield k
            k.commit()
        finally:
            k.close()

    monkeypatch.setattr(db_inbox, "connect", _connect)
    monkeypatch.setattr(db_inbox, "_skema_klar", False)
    return sti


def test_scheduled_er_ikke_gatende():
    """En planlagt opgave maa ikke kunne naegte en mutation."""
    from core.services.inbox_state import IKKE_GATENDE_KILDETYPER

    assert "scheduled" in IKKE_GATENDE_KILDETYPER


def test_registrering_skriver_en_aaben_post(inbox_db):
    from core.services.scheduled_inbox import registrer_fyret_opgave

    r = registrer_fyret_opgave(
        bruger_id="bjorn", task_id="sched-abc123",
        focus="Foelg op paa success-rate-karantaenen")
    assert r["status"] == "ok", r

    post = db_inbox.hent(bruger_id="bjorn", kilde_id="sched-abc123")
    assert post is not None
    assert post["kildetype"] == "scheduled"
    assert post["status"] == db_inbox.STATUS_AABEN
    # Husets post: synlig, men gater ikke.
    assert not post["kraever_handling"]


def test_registrering_er_idempotent(inbox_db):
    """Samme task maa ikke give to rækker — polleren kan ramme den to gange."""
    from core.services.scheduled_inbox import registrer_fyret_opgave

    registrer_fyret_opgave(bruger_id="bjorn", task_id="sched-x", focus="a")
    registrer_fyret_opgave(bruger_id="bjorn", task_id="sched-x", focus="a")

    poster = db_inbox.liste(bruger_id="bjorn")
    assert len([p for p in poster if p["kilde_id"] == "sched-x"]) == 1


def test_tom_bruger_eller_task_afvises(inbox_db):
    from core.services.scheduled_inbox import registrer_fyret_opgave

    assert registrer_fyret_opgave(bruger_id="", task_id="t", focus="a")["status"] == "fejl"
    assert registrer_fyret_opgave(bruger_id="bjorn", task_id="", focus="a")["status"] == "fejl"


def test_fejl_i_registreringen_vaelter_ikke_fyringen(inbox_db, monkeypatch):
    """En fejlet indbakke-skrivning maa ikke forhindre at opgaven fyrer."""
    from core.services import scheduled_inbox as si
    from core.services import inbox_state

    def braender(**kw):
        raise RuntimeError("db nede")

    # `registrer_kilde` importeres LOKALT i funktionen, saa patchen skal ramme
    # kilden — ikke modulet.
    monkeypatch.setattr(inbox_state, "registrer_kilde", braender)
    r = si.registrer_fyret_opgave(bruger_id="bjorn", task_id="t", focus="a")
    assert r["status"] == "fejl"
