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


def test_kvote_politik_gemmes_paa_udbyderprofilen(registret):
    ud = A.saet_kvote_politik(
        provider="alfa", auth_profile="default",
        windows=[{"period": "month", "unit": "tokens", "limit": 1234}],
    )
    provider = next(p for p in _laes(registret)["providers"] if p["provider"] == "alfa")
    assert ud["status"] == "ok"
    assert provider["quota_policy"][0]["limit"] == 1234
    assert A.fuld_registrering()["udbydere"][0]["quota_policy"][0]["unit"] == "tokens"


def test_kvote_politik_kraever_cheap_lane_og_gyldigt_vindue(registret):
    assert A.saet_kvote_politik(
        provider="beta", auth_profile="default",
        windows=[{"period": "month", "unit": "tokens", "limit": 100}],
    )["status"] == "error"
    assert A.saet_kvote_politik(
        provider="alfa", auth_profile="default",
        windows=[{"period": "year", "unit": "tokens", "limit": 100}],
    )["status"] == "error"


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


# ── tilfoejelse og lane-flytning (16/9-2026) ─────────────────────────────

def test_en_ny_model_kan_tilfoejes(registret, monkeypatch):
    kaldt = {}
    import core.runtime.provider_router as pr

    def _fake(**kw):
        kaldt.update(kw)
        data = _laes(registret)
        data["models"].append({"provider": kw["provider"], "model": kw["model"],
                               "lane": kw["lane"], "enabled": True})
        registret.write_text(json.dumps(data), encoding="utf-8")
        return {"credentials_saved": bool(kw.get("api_key"))}

    monkeypatch.setattr(pr, "configure_provider_router_entry", _fake)
    ud = A.tilfoej(provider="ny", model="m9", lane="cheap", base_url="https://ny/v1")
    assert ud["status"] == "ok" and ud["noegle_gemt"] is False
    assert any(m["model"] == "m9" for m in _laes(registret)["models"])
    assert kaldt["set_visible"] is False       # tilfoejelse maa ALDRIG skifte hans synlige model


def test_noeglen_naar_aldrig_tilbage_i_svaret(registret, monkeypatch):
    import core.runtime.provider_router as pr
    monkeypatch.setattr(pr, "configure_provider_router_entry",
                        lambda **kw: {"credentials_saved": True})
    ud = A.tilfoej(provider="ny", model="m9", api_key="hemmelig-noegle")
    assert ud["noegle_gemt"] is True
    assert "hemmelig-noegle" not in json.dumps(ud)


def test_lane_kan_flyttes(registret):
    ud = A.saet_lane(provider="alfa", model="m1", lane="local")
    assert ud["fra"] == "cheap" and ud["til"] == "local"
    m = next(x for x in _laes(registret)["models"] if x["model"] == "m1")
    assert m["lane"] == "local" and m["enabled"] is True   # flytning er ikke en slukning


def test_lane_paa_ukendt_model_skriver_intet(registret):
    foer = registret.read_text(encoding="utf-8")
    assert A.saet_lane(provider="alfa", model="findes-ikke", lane="local")["status"] == "error"
    assert registret.read_text(encoding="utf-8") == foer
