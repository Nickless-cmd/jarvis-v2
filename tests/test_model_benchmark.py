"""Rangér modeller på ÆGTE opgaver med facit fra kilden.

Baggrunden (7/9-2026): efter første fejning stod **65 af 67 egnede modeller
med probe_score 100**, og den første i rotationen var en 3B-model foran
deepseek-v4-pro. Sonden kan afgøre om en model KAN; den kan ikke afgøre hvor
godt. Og at gøre den syntetiske prøve sværere hjalp ikke — gpt-4.1 bestod hver
skærpelse og opdigtede alligevel i produktion.
"""
from pathlib import Path

import core.services.agent_model_fitness as fit
from core.services.model_benchmark import (
    bedøm_svar, facit_for, kør_benchmark, opgave_for, vælg_filer,
)

FACIT = {"load_provider_router_registry": 18, "configure_provider_router_entry": 30,
         "provider_router_summary": 125}


# ── bedømmelsen ─────────────────────────────────────────────────────────────

def test_opdigtede_navne_giver_praecision_nul():
    d = bedøm_svar("route_provider_request (12), get_provider_status (56)", FACIT)
    assert d["praecision"] == 0.0 and d["score"] == 0
    assert "route_provider_request" in d["opfundne"]


def test_et_helt_rigtigt_svar_faar_fuld_score():
    svar = "\n".join(f"{n} (linje {l})" for n, l in FACIT.items())
    d = bedøm_svar(svar, FACIT)
    assert d["praecision"] == 1.0 and d["daekning"] == 1.0 and d["score"] == 100


def test_praecision_vejer_tungere_end_daekning():
    """At opfinde er værre end at overse: en agent der nævner ting der ikke
    findes, sender Jarvis i en blindgyde han selv skal opdage."""
    kun_én_rigtig = bedøm_svar("load_provider_router_registry (18)", FACIT)
    halvt_opdigtet = bedøm_svar(
        "load_provider_router_registry (18), configure_provider_router_entry (30), "
        "route_provider_request (12), get_provider_status (56)", FACIT)
    assert kun_én_rigtig["score"] > halvt_opdigtet["score"]


def test_linjenumre_kontrolleres():
    rigtig = bedøm_svar("load_provider_router_registry på linje 18", FACIT)
    forkert = bedøm_svar("load_provider_router_registry på linje 999", FACIT)
    assert rigtig["linjer_rigtige"] == 1 and forkert["linjer_rigtige"] == 0


def test_prosa_taelles_ikke_som_paastande():
    d = bedøm_svar("Filen indeholder en række hjælpefunktioner til routeren.", FACIT)
    assert d["opfundne"] == []


# ── facit hentes fra kilden ─────────────────────────────────────────────────

def test_facit_kommer_fra_den_RIGTIGE_fil():
    """Facit må aldrig være håndskrevet — så ville prøven være forkert to uger
    efter nogen omdøbte en funktion, og vi ville rangere modeller efter hvor
    godt de husker gammel kode."""
    f = facit_for(Path("core/runtime/provider_router.py"))
    assert f.get("load_provider_router_registry") == 18
    assert f.get("configure_provider_router_entry") == 30


def test_samme_froe_giver_samme_proeve():
    """To modeller skal bedømmes på det SAMME — ellers sammenligner vi ikke."""
    assert vælg_filer(antal=3, frø=7) == vælg_filer(antal=3, frø=7)


def test_opgaven_beder_om_en_LISTE():
    """Det er den form der udløser fejlen. gpt-4.1 bestod hver enkeltstående
    quiz og faldt netop på «giv mig N ting»."""
    o = opgave_for(Path("core/runtime/provider_router.py"))
    assert "hver enkelt" in o and "linjenummer" in o


# ── kørslen ─────────────────────────────────────────────────────────────────

def test_en_model_der_opdigter_faar_lav_score():
    r = kør_benchmark(provider="p", model="m", antal_filer=1,
                      kald=lambda q: "helt_opdigtet_navn(), et_andet_paafund()")
    assert r["score"] == 0


def test_en_udbyder_der_kaster_vaelter_ikke_koerslen():
    def sur(q):
        raise RuntimeError("nede")
    r = kør_benchmark(provider="p", model="m", antal_filer=1, kald=sur)
    assert r["score"] == 0 and r["fejl"]


# ── rotationen bruger kvaliteten ────────────────────────────────────────────

def test_rotationen_rangerer_efter_KVALITET_ikke_sonden(monkeypatch):
    poster = [
        {"provider": "lille", "model": "3b", "enabled": True, "probe_score": 100,
         "probe_detail": {"follows": True}},
        {"provider": "stor", "model": "pro", "enabled": True, "probe_score": 100,
         "probe_detail": {"follows": True}, "kvalitets_score": 82},
    ]
    monkeypatch.setattr(fit, "_registret", lambda: poster)
    assert fit.egnede_modeller(maks=2)[0] == ("stor", "pro")


def test_umaalte_lægger_sig_EFTER_de_maalte(monkeypatch):
    poster = [
        {"provider": "umaalt", "model": "x", "enabled": True, "probe_score": 100,
         "probe_detail": {"follows": True}},
        {"provider": "svag", "model": "y", "enabled": True, "probe_score": 100,
         "probe_detail": {"follows": True}, "kvalitets_score": 11},
    ]
    monkeypatch.setattr(fit, "_registret", lambda: poster)
    assert fit.egnede_modeller(maks=2)[0] == ("svag", "y")
