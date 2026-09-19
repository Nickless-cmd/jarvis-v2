"""Tænke-resuméet til visningen «thinking» (19/9-2026)."""
from __future__ import annotations

import core.services.tool_round_label as trl
from core.services import tanke_resume as tr


def test_ingen_tanke_intet_kald(monkeypatch):
    kaldt = []
    monkeypatch.setattr(trl, "_kald_model", lambda p: kaldt.append(p) or "x y")
    assert tr.tanke_resume("   ") == ""
    assert kaldt == []


def test_modellen_ser_HALEN_af_taenkningen(monkeypatch):
    """Konklusionen står sidst; en lang monolog må ikke skubbe den ud."""
    set_: list[str] = []
    monkeypatch.setattr(trl, "_kald_model", lambda p: set_.append(p) or "Ville tjekke ruten først")
    tanke = "a" * 5000 + " SLUTNINGEN"
    assert tr.tanke_resume(tanke, "ret fejlen") == "Ville tjekke ruten først"
    assert "SLUTNINGEN" in set_[0]
    assert "a" * 2000 not in set_[0]
    assert "Brugeren bad om: ret fejlen" in set_[0]


def test_ryddes_til_én_linje_uden_pynt(monkeypatch):
    monkeypatch.setattr(trl, "_kald_model", lambda p: '«Mistænkte cachen for at være forældet.»\nForklaring: ...')
    assert tr.tanke_resume("tanke") == "Mistænkte cachen for at være forældet"


def test_klippes_ved_et_ordskel(monkeypatch):
    monkeypatch.setattr(trl, "_kald_model", lambda p: "ord " * 40)
    ud = tr.tanke_resume("tanke")
    assert len(ud) <= tr.MAKS_RESUME and not ud.endswith(" ")


def test_et_noegent_ord_er_intet_resume(monkeypatch):
    monkeypatch.setattr(trl, "_kald_model", lambda p: "Tænkte")
    assert tr.tanke_resume("tanke") == ""


def test_en_fejl_vaelter_intet(monkeypatch):
    def boom(p):
        raise TimeoutError("lokal model svarer ikke")
    monkeypatch.setattr(trl, "_kald_model", boom)
    assert tr.tanke_resume("tanke") == ""
