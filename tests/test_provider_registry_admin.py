"""Skrivevejen til provider-registret — den der aldrig har fundets.

`configure_provider_router_entry` saetter ALTID `enabled: True`. Der var ingen
vej til at slaa noget fra uden at redigere filen i haanden, og derfor kunne en
knap i desk ikke andet end at lyve.
"""
from __future__ import annotations

import json

import pytest

from core.services import provider_registry_admin as A


@pytest.fixture
def registret(tmp_path, monkeypatch):
    fil = tmp_path / "provider_router.json"
    fil.write_text(json.dumps({
        "providers": [
            {"provider": "alfa", "auth_mode": "api_key", "auth_profile": "default",
             "base_url": "https://alfa/v1", "enabled": True},
            {"provider": "beta", "auth_mode": "none", "auth_profile": "default",
             "base_url": "https://beta/v1", "enabled": True},
        ],
        "models": [
            {"provider": "alfa", "model": "m1", "lane": "cheap", "enabled": True},
            {"provider": "alfa", "model": "m2", "lane": "cheap", "enabled": True},
            {"provider": "beta", "model": "b1", "lane": "local", "enabled": False},
        ],
    }), encoding="utf-8")
    import core.runtime.config as cfg
    monkeypatch.setattr(cfg, "PROVIDER_ROUTER_FILE", fil, raising=False)
    monkeypatch.setattr(A, "_fil", lambda: fil)
    import core.runtime.provider_router as pr
    monkeypatch.setattr(pr, "PROVIDER_ROUTER_FILE", fil, raising=False)
    monkeypatch.setattr(pr, "load_provider_router_registry",
                        lambda: json.loads(fil.read_text(encoding="utf-8")))
    monkeypatch.setattr(pr, "_credentials_ready", lambda **kw: True)
    return fil


def _laes(fil):
    return json.loads(fil.read_text(encoding="utf-8"))


def test_hele_registret_kommer_med(registret):
    ud = A.fuld_registrering()
    assert ud["opsummering"] == {"udbydere": 2, "modeller": 3, "aktive_modeller": 2}
    assert ud["lanes"]["cheap"] == {"i_alt": 2, "aktive": 2}
    alfa = next(u for u in ud["udbydere"] if u["provider"] == "alfa")
    assert alfa["model_count"] == 2 and alfa["enabled_model_count"] == 2


def test_en_model_kan_slaas_FRA_og_TIL_igen(registret):
    A.saet_model_aktiv(provider="alfa", model="m1", aktiv=False, grund="for dyr")
    m = next(x for x in _laes(registret)["models"] if x["model"] == "m1")
    assert m["enabled"] is False and m["disabled_reason"] == "for dyr" and m["disabled_at"]

    A.saet_model_aktiv(provider="alfa", model="m1", aktiv=True)
    m = next(x for x in _laes(registret)["models"] if x["model"] == "m1")
    # Grunden skal VAEK igen — ellers staar der «for dyr» paa en aktiv model.
    assert m["enabled"] is True and "disabled_reason" not in m and "disabled_at" not in m


def test_ukendt_model_skriver_INTET(registret):
    foer = registret.read_text(encoding="utf-8")
    ud = A.saet_model_aktiv(provider="alfa", model="findes-ikke", aktiv=False)
    assert ud["status"] == "error"
    assert registret.read_text(encoding="utf-8") == foer


def test_en_hel_udbyder_kan_slaas_fra(registret):
    A.saet_udbyder_aktiv(provider="beta", aktiv=False, grund="nede")
    p = next(x for x in _laes(registret)["providers"] if x["provider"] == "beta")
    assert p["enabled"] is False
    # Modellernes EGNE flag roeres ikke — de skal kunne huskes naar den taendes igen.
    assert _laes(registret)["models"][2]["enabled"] is False


def test_fjern_udbyder_tager_dens_modeller_med(registret):
    ud = A.fjern_udbyder(provider="alfa")
    assert ud["fjernede_modeller"] == 2 and ud["legitimation_bevaret"] is True
    r = _laes(registret)
    assert [p["provider"] for p in r["providers"]] == ["beta"]
    assert all(m["provider"] != "alfa" for m in r["models"])


def test_hver_skrivning_tager_backup_og_kan_rulles_tilbage(registret):
    A.saet_model_aktiv(provider="alfa", model="m1", aktiv=False)
    A.fjern_udbyder(provider="alfa")
    assert len(A.backups()) >= 2

    ud = A.gendan_backup()          # nyeste backup = tilstanden FOER fjernelsen
    assert ud["status"] == "ok"
    assert any(m["provider"] == "alfa" for m in _laes(registret)["models"])


def test_gendan_naegter_stier_uden_for_mappen(registret):
    assert A.gendan_backup(sti="../../../etc/passwd")["status"] == "error"


def test_aendringen_udsendes_saa_den_kan_ses_bagefter(registret, monkeypatch):
    set_ud = []
    import core.eventbus.bus as bus
    monkeypatch.setattr(bus.event_bus, "publish",
                        lambda kind, payload=None, **kw: set_ud.append((kind, payload)))
    A.saet_model_aktiv(provider="alfa", model="m2", aktiv=False, grund="fejler")
    assert set_ud and set_ud[0][0] == "runtime.provider_registry_changed"
    assert set_ud[0][1]["provider"] == "alfa" and set_ud[0][1]["handling"] == "model_inaktiv"
