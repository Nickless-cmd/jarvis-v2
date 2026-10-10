"""Indbakken skal kunne VÆKKE — ikke kun gate.

Bjørn 10/10-2026: «skal inbox kunne vække dig, på den hvis du ikk er i et
aktivt run?» Svaret var nej: `inbox_gate` blokerer kun mutationer INDE i et
run, og intet starter et run fordi en post findes. En `kraever_handling=1`-post
uden dispatcher ventede til næste heartbeat eller hans næste besked.

Det er hullet: en forpligtelse der kræver handling bør ikke kunne stå og vente
på at nogen tilfældigvis kører.

Vækkeren er bevidst KONSERVATIV:
  * kun poster der faktisk gater (`kraever_handling` + verificeret ejer)
  * kun når INTET run er i gang
  * kun én vækning pr. post — ellers bliver den en kæde der skriver i hans chat
  * self-safe: enhver fejl → ingen vækning, aldrig en væltet poller
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

import pytest

from core.runtime import db_inbox


@pytest.fixture
def inbox_db(monkeypatch, tmp_path):
    sti = tmp_path / "idle.db"

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


def _post(bruger="bjorn", id="wake-1", **kw) -> dict:
    r = db_inbox.opret_eller_hent(
        bruger_id=bruger, kildetype=kw.pop("kildetype", "wakeup"), kilde_id=id,
        oprettende_run_id="visible-abc",
        verificeret_ejer=kw.pop("ejer", db_inbox.EJER_JARVIS),
        kraever_handling=kw.pop("kraever_handling", True),
        beskrivelse=kw.pop("beskrivelse", "foelg op"), **kw)
    assert r["status"] == "ok", r
    return r["post"]


# ── hvem må vække ───────────────────────────────────────────────────────────

def test_kun_gatende_poster_vaekker(inbox_db):
    """En informerende post (huset/ukendt) må ikke starte et run."""
    from core.services.inbox_idle_waker import kandidater

    _post(id="husets", ejer=db_inbox.EJER_HUSET, kraever_handling=False)
    _post(id="ukendt", ejer=db_inbox.EJER_UKENDT, kraever_handling=False)
    _post(id="min", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)

    ids = [p["kilde_id"] for p in kandidater("bjorn")]
    assert ids == ["min"]


def test_afgjorte_poster_vaekker_ikke(inbox_db):
    from core.services.inbox_idle_waker import kandidater

    _post(id="aaben", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    _post(id="lukket", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    db_inbox.afgoer(bruger_id="bjorn", kilde_id="lukket",
                    ny_status=db_inbox.STATUS_DONE, grund="test")

    ids = [p["kilde_id"] for p in kandidater("bjorn")]
    assert ids == ["aaben"]


def test_anden_brugers_poster_vaekker_ikke_mig(inbox_db):
    """Husstanden har flere brugere — en post for en anden må ikke starte mit run."""
    from core.services.inbox_idle_waker import kandidater

    _post(bruger="mikkel", id="hans", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    assert kandidater("bjorn") == []


# ── hvornår den må fyre ─────────────────────────────────────────────────────

def test_aktivt_run_blokerer_vaekning(inbox_db, monkeypatch):
    """Kører der noget, må vækkeren ikke starte et konkurrerende run."""
    from core.services import inbox_idle_waker as w

    _post(id="min", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    monkeypatch.setattr(w, "_noget_koerer", lambda: True)
    startet = []
    monkeypatch.setattr(w, "_start_run", lambda tekst, **kw: startet.append(tekst))

    r = w.vaek_paa_aabne_poster(bruger_id="bjorn")
    assert r["vaekket"] == 0
    assert startet == []


def test_ingen_aktivt_run_vaekker(inbox_db, monkeypatch):
    from core.services import inbox_idle_waker as w

    _post(id="min", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    monkeypatch.setattr(w, "_noget_koerer", lambda: False)
    startet = []
    monkeypatch.setattr(w, "_start_run", lambda tekst, **kw: startet.append(tekst))

    r = w.vaek_paa_aabne_poster(bruger_id="bjorn")
    assert r["vaekket"] == 1
    assert len(startet) == 1
    assert "min" in startet[0]


def test_samme_post_vaekker_kun_en_gang(inbox_db, monkeypatch):
    """Uden dette ville hver poll-runde starte et nyt run — en kæde i hans chat."""
    from core.services import inbox_idle_waker as w

    _post(id="min", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    monkeypatch.setattr(w, "_noget_koerer", lambda: False)
    startet = []
    monkeypatch.setattr(w, "_start_run", lambda tekst, **kw: startet.append(tekst))

    assert w.vaek_paa_aabne_poster(bruger_id="bjorn")["vaekket"] == 1
    assert w.vaek_paa_aabne_poster(bruger_id="bjorn")["vaekket"] == 0
    assert len(startet) == 1


def test_loft_pr_runde(inbox_db, monkeypatch):
    """Ti aabne poster maa ikke blive ti runs i samme runde."""
    from core.services import inbox_idle_waker as w

    for i in range(10):
        _post(id=f"p{i}", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    monkeypatch.setattr(w, "_noget_koerer", lambda: False)
    startet = []
    monkeypatch.setattr(w, "_start_run", lambda tekst, **kw: startet.append(tekst))

    r = w.vaek_paa_aabne_poster(bruger_id="bjorn")
    assert r["vaekket"] == w.MAKS_PR_RUNDE
    assert len(startet) == w.MAKS_PR_RUNDE


# ── self-safe ───────────────────────────────────────────────────────────────

def test_fejl_i_laesningen_vaelter_ikke_polleren(inbox_db, monkeypatch):
    from core.services import inbox_idle_waker as w

    def braender(**kw):
        raise RuntimeError("db nede")

    monkeypatch.setattr(w, "kandidater", braender)
    r = w.vaek_paa_aabne_poster(bruger_id="bjorn")
    assert r["status"] == "ok"
    assert r["vaekket"] == 0


def test_fejl_i_run_start_efterlader_ikke_post_som_vaekket(inbox_db, monkeypatch):
    """Kaster run-start, maa posten IKKE markeres — saa proeves den igen."""
    from core.services import inbox_idle_waker as w

    _post(id="min", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    monkeypatch.setattr(w, "_noget_koerer", lambda: False)

    def braender(tekst, **kw):
        raise RuntimeError("kunne ikke starte")

    monkeypatch.setattr(w, "_start_run", braender)
    r = w.vaek_paa_aabne_poster(bruger_id="bjorn")
    assert r["vaekket"] == 0
    # anden runde proever igen — posten er ikke brændt af
    startet = []
    monkeypatch.setattr(w, "_start_run", lambda tekst, **kw: startet.append(tekst))
    assert w.vaek_paa_aabne_poster(bruger_id="bjorn")["vaekket"] == 1
