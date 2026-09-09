"""Persistering af følelses-signaler: ÉN arbejdstråd, ikke én pr. signal.

Målt 9/9-2026. Den gamle kode startede en NY tråd pr. signal, og
`db_core.connect()` er thread-local pooled — så hver tråd fik en HELT NY
sqlite-forbindelse. Puljen blev indført for at stoppe 1.091 connects pr.
prompt-assembly; en tråd pr. signal omgik den fuldstændigt.

Reproducerbart som «database is locked» på brugerens EGEN besked.

(`CREATE TABLE IF NOT EXISTS` var uden skyld: målt til 0,7 µs og ingen lås
overhovedet på en eksisterende tabel. Den stod bare først i funktionen, så en
netop startet tråd blev fanget dér i stak-dumpet.)
"""
from __future__ import annotations

import queue
import threading
import time

import pytest

from core.services import emotion_concepts as EC


def _toem_koe():
    while not EC._persist_koe.empty():
        try:
            EC._persist_koe.get_nowait()
        except queue.Empty:
            break


@pytest.fixture(autouse=True)
def _ren_koe():
    """Tøm køen både FØR og EFTER.

    Efter er det vigtige: en test der fylder køen mens arbejderen er spærret,
    efterlader signalerne dér. Når monkeypatchen rulles tilbage ved testens
    slutning, bliver `_safe_persist` den ÆGTE igen — og arbejderen tømmer så
    køen med rigtige databaseskrivninger ind i de FØLGENDE tests.

    Målt: den lækage alene løftede fejlraten i nabo-testene fra 1/12 til 4/20.
    En test der forurener sine naboer er værre end ingen test.
    """
    _toem_koe()
    EC._persist_tabt = 0
    yield
    _toem_koe()


def _sig(navn="ro"):
    return {"concept": navn, "intensity": 0.5, "created_at": "2026-09-09T12:00:00+00:00"}


def _traade(praefiks="emotion-concepts-persist"):
    return [t for t in threading.enumerate() if t.name.startswith(praefiks)]


def test_hundrede_signaler_giver_HOEJST_EN_ny_traad(monkeypatch):
    """Kernen: en tråd pr. signal blev til en sqlite-forbindelse pr. signal.

    Målt på DELTA og ikke på et absolut antal. Testfiksturerne genindlæser
    moduler, hvorefter `_persist_worker` står som None mens den gamle tråd
    lever videre på en forældreløs kø — så det absolutte tal siger noget om
    testkørslens historik, ikke om den egenskab der prøves her.

    (I drift genindlæses moduler ikke, så der er én arbejder.)
    """
    monkeypatch.setattr(EC, "_safe_persist", lambda s: None)
    foer = len(_traade())
    for i in range(100):
        EC._persist_async(_sig(f"c{i}"))
    time.sleep(0.3)
    assert len(_traade()) - foer <= 1


def test_arbejderen_genbruges_paa_tvaers_af_kald(monkeypatch):
    monkeypatch.setattr(EC, "_safe_persist", lambda s: None)
    EC._persist_async(_sig())
    time.sleep(0.1)
    foerste = EC._persist_worker
    EC._persist_async(_sig())
    assert EC._persist_worker is foerste


def test_signalerne_naar_faktisk_frem(monkeypatch):
    set_igennem = []
    monkeypatch.setattr(EC, "_safe_persist", lambda s: set_igennem.append(s["concept"]))
    for n in ("ro", "glæde", "uro"):
        EC._persist_async(_sig(n))
    for _ in range(50):
        if len(set_igennem) == 3:
            break
        time.sleep(0.02)
    assert sorted(set_igennem) == ["glæde", "ro", "uro"]


def test_en_FEJLENDE_skrivning_draeber_ikke_arbejderen(monkeypatch):
    """Ellers ville ét dårligt signal stoppe al persistering bagefter."""
    kald = []
    def _knald(s):
        kald.append(s["concept"])
        if s["concept"] == "dårlig":
            raise RuntimeError("i stykker")
    monkeypatch.setattr(EC, "_safe_persist", _knald)
    EC._persist_async(_sig("dårlig"))
    EC._persist_async(_sig("god"))
    for _ in range(50):
        if "god" in kald:
            break
        time.sleep(0.02)
    assert "god" in kald and EC._persist_koe_status()["arbejder_lever"]


def test_koeen_er_BEGRAENSET_og_taber_hoejlydt(monkeypatch, caplog):
    """En kø der løber over betyder at skrivningen ikke kan følge med, og dét
    skal kunne ses. Et følelses-signal er observabilitet — det må ikke kunne
    skade det det måler."""
    import logging
    # bloker arbejderen, saa koeen fyldes
    spaerre = threading.Event()
    monkeypatch.setattr(EC, "_safe_persist", lambda s: spaerre.wait(2.0))
    with caplog.at_level(logging.WARNING):
        for i in range(EC._persist_koe.maxsize + 40):
            EC._persist_async(_sig(f"c{i}"))
    spaerre.set()
    assert EC._persist_tabt > 0
    assert "persist-kø fuld" in caplog.text


def test_et_tabt_signal_kaster_ikke(monkeypatch):
    spaerre = threading.Event()
    monkeypatch.setattr(EC, "_safe_persist", lambda s: spaerre.wait(1.0))
    for i in range(EC._persist_koe.maxsize + 5):
        EC._persist_async(_sig(f"c{i}"))     # kaster ikke
    spaerre.set()


def test_status_kan_aflaeses():
    st = EC._persist_koe_status()
    assert set(st) == {"i_koe", "tabt", "arbejder_lever"}
