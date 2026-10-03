"""Tests for samtalens tilladelses-niveau — én sandhed på serveren (20/9-2026).

Værd at holde fast: `ask` er standarden. En tvivl skal koste et spørgsmål, ikke
en mutation. Falder en ukendt værdi igennem til `trust`, åbner den for
værktøjer uden at nogen bad om det — det er den fejl testene her forhindrer.
"""
from __future__ import annotations

import sqlite3

import pytest

from core.services import session_permission as sp


@pytest.fixture()
def db(monkeypatch, tmp_path):
    """En frisk DB med den ene kolonne testen har brug for."""
    sti = tmp_path / "test.db"
    conn = sqlite3.connect(sti)
    conn.execute(
        "CREATE TABLE chat_sessions (session_id TEXT PRIMARY KEY, title TEXT NOT NULL DEFAULT '')"
    )
    conn.execute("INSERT INTO chat_sessions (session_id, title) VALUES ('s1', 'test')")
    conn.commit()
    conn.close()

    import contextlib

    @contextlib.contextmanager
    def _connect():
        c = sqlite3.connect(sti)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()

    monkeypatch.setattr(sp, "connect", _connect)
    return sti


def test_ukendt_samtale_er_ask(db):
    """Den sikre vej: en samtale vi ikke kender maa ikke aabne for fuld adgang."""
    assert sp.hent_permission("findes-ikke") == "ask"


def test_tomt_id_er_ask(db):
    assert sp.hent_permission("") == "ask"
    assert sp.hent_permission(None) == "ask"


def test_kolonnen_laves_dovent(db):
    """Kolonne-migrationen skal vaere idempotent — hent kaldes ved hver åbning."""
    assert sp.hent_permission("s1") == "ask"
    assert sp.hent_permission("s1") == "ask"  # anden gang: ALTER TABLE fejler, sluges


def test_rundtur_ask_til_trust_og_tilbage(db):
    assert sp.saet_permission("s1", "trust")["status"] == "ok"
    assert sp.hent_permission("s1") == "trust"
    assert sp.saet_permission("s1", "ask")["status"] == "ok"
    assert sp.hent_permission("s1") == "ask"


def test_ugyldigt_niveau_afvises(db):
    ud = sp.saet_permission("s1", "maaske")
    assert ud["status"] == "error"
    # Og den maa IKKE have aendret noget undervejs.
    assert sp.hent_permission("s1") == "ask"


def test_ukendt_samtale_kan_ikke_saettes(db):
    """Et skriv til en samtale der ikke findes skal sige det, ikke lykkes stille."""
    ud = sp.saet_permission("findes-ikke", "trust")
    assert ud["status"] == "error"
    assert "findes-ikke" in str(ud["error"])


def test_stort_bogstav_i_niveau_er_gyldigt(db):
    """Klienterne sender småt, men et 'TRUST' fra en gammel klient skal ikke
    stille blive afvist som ukendt — det normaliseres."""
    assert sp.saet_permission("s1", "TRUST")["status"] == "ok"
    assert sp.hent_permission("s1") == "trust"


# ── Arven ved oprettelse (3/10-2026) ──────────────────────────────────────
#
# Bjoern: «composer arver ikk permissions». Maalt: en side-opgave startes i en
# NY samtale, som ingen vaerdi har i `approval_mode`. `hent_permission` svarer
# derfor `ask`, og desks PermissionContext laeser netop serveren naar samtalen
# skifter — saa den OVERSKRIVER brugerens lokale «fuld adgang» med `ask`. Han
# havde givet adgang; den forsvandt i oprettelsen.


def _opret(db, sid: str) -> None:
    import sqlite3
    c = sqlite3.connect(db)
    c.execute("INSERT INTO chat_sessions (session_id, title) VALUES (?, '')", (sid,))
    c.commit()
    c.close()


def test_trust_arves_til_den_nye_samtale(db):
    """Selve fejlen han saa."""
    sp.saet_permission("s1", "trust")
    _opret(db, "s2")
    ud = sp.arv_permission("s2", "s1")
    assert ud == {"approval_mode": "trust", "arvet": True, "fra": "s1"}
    assert sp.hent_permission("s2") == "trust"


def test_ask_arves_IKKE_eksplicit(db):
    """`ask` ER standarden, saa en skrivning ville kun vaere stoej. Og arven
    maa aldrig loefte et niveau NED — det er en mutation uden en anmodning."""
    _opret(db, "s2")
    ud = sp.arv_permission("s2", "s1")
    assert ud["arvet"] is False
    assert ud["grund"] == "foraelderen staar paa standarden"
    assert sp.hent_permission("s2") == "ask"


def test_arven_overskriver_ikke_et_eksisterende_valg_nedad(db):
    """Barnet staar paa `trust`, foraelderen paa `ask` → barnet beholder sit.
    Arven er en gave ved foedslen, ikke en loebende synkronisering."""
    _opret(db, "s2")
    sp.saet_permission("s2", "trust")
    sp.arv_permission("s2", "s1")
    assert sp.hent_permission("s2") == "trust"


def test_et_senere_skift_i_foraelderen_flytter_IKKE_barnet(db):
    """Ellers kunne et `trust`-klik i én samtale haeve privilegier i en anden,
    bagudvirkende. Arven sker KUN ved oprettelsen."""
    sp.saet_permission("s1", "trust")
    _opret(db, "s2")
    sp.arv_permission("s2", "s1")
    sp.saet_permission("s1", "ask")
    assert sp.hent_permission("s2") == "trust", "barnet foelger ikke foraelderen"


def test_ingen_foraelder_giver_standarden(db):
    _opret(db, "s2")
    for fra in ("", "   ", None):
        ud = sp.arv_permission("s2", fra)
        assert ud["arvet"] is False and ud["approval_mode"] == "ask"


def test_arv_til_sig_selv_er_ingen_arv(db):
    sp.saet_permission("s1", "trust")
    ud = sp.arv_permission("s1", "s1")
    assert ud["arvet"] is False


def test_en_ukendt_foraelder_giver_standarden_og_kaster_ikke(db):
    _opret(db, "s2")
    ud = sp.arv_permission("s2", "findes-ikke")
    assert ud["arvet"] is False
    assert sp.hent_permission("s2") == "ask"


def test_arven_kaster_ALDRIG(db, monkeypatch):
    """En mislykket arv maa ikke kunne forhindre at samtalen bliver oprettet.
    Fail-retningen er `ask`, som er den sikre."""
    monkeypatch.setattr(sp, "hent_permission",
                        lambda _s: (_ for _ in ()).throw(RuntimeError("i stykker")))
    ud = sp.arv_permission("s2", "s1")
    assert ud == {"approval_mode": "ask", "arvet": False, "grund": "fejl"}


def test_en_ukendt_NY_samtale_kan_ikke_arve(db):
    """`saet_permission` afviser en samtale der ikke findes — arven skal melde
    det frem for at paastaa at niveauet gaelder."""
    sp.saet_permission("s1", "trust")
    ud = sp.arv_permission("findes-heller-ikke", "s1")
    assert ud["arvet"] is False
    assert ud["approval_mode"] == "ask"
