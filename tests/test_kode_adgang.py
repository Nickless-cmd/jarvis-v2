"""Reglen «code mode kræver tilføjet enhed» — fejl-adfærden (19/9-2026).

Selve reglen er dækket i test_db_devices; her det der kun hører til
`kode_adgang`: at den lukker når registret fejler mens reglen er TÆNDT.
"""
from __future__ import annotations

import core.identity.owner_resolver as orr
import core.identity.workspace_context as wc
from core.identity import kode_adgang as ka
from core.runtime import db_devices as dd


def test_registret_fejler_mens_reglen_er_taendt_saa_lukker_den(monkeypatch):
    # Reglen gælder kun ejeren (31/10-2026), så testen sigter eksplicit på
    # ejerens id. Uden det ville "u1" være et medlem — og et medlem slipper
    # korrekt igennem uden at registret spørges, hvilket er en anden adfærd
    # end den denne test måler.
    monkeypatch.setattr(dd, "kraev_aktivt", lambda: True)
    monkeypatch.setattr(wc, "current_user_id", lambda: "u1")
    monkeypatch.setattr(wc, "current_token_enhed", lambda: ("enh-x", ""))
    monkeypatch.setattr(orr, "owner_user_id", lambda: "u1")
    def boom(*a, **k):
        raise RuntimeError("databasen hikker")
    monkeypatch.setattr(dd, "maa_bruge_kode", boom)
    assert ka.kode_tilladt() is False


def test_slukket_regel_rører_ikke_registret(monkeypatch):
    monkeypatch.setattr(dd, "kraev_aktivt", lambda: False)
    def boom(*a, **k):
        raise AssertionError("må ikke kaldes")
    monkeypatch.setattr(dd, "maa_bruge_kode", boom)
    assert ka.kode_tilladt() is True


def test_internt_kald_roerer_ikke_et_utilgaengeligt_register(monkeypatch):
    monkeypatch.setattr(wc, "current_user_id", lambda: "")

    def boom():
        raise RuntimeError("stale test-database")

    monkeypatch.setattr(dd, "kraev_aktivt", boom)
    assert ka.kode_tilladt() is True


def test_forklaringen_siger_hvor_man_tilfoejer_enheden():
    assert "Enheder" in ka.KODE_NAEGTET and "totrinskode" in ka.KODE_NAEGTET
