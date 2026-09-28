"""Forslag i komponisten — et bud på den NÆSTE besked.

## Hvem der foreslår (ændret 28/9-2026)

Forslaget kommer udelukkende fra Jarvis selv, gennem værktøjet
`suggest_next_message`. Den lokale model (qwen3:4b) skrev tidligere et bud når
han ikke selv lagde et ned; den blev droppet efter Bjørns måling og dom: «drop
den anden models forslag og kun bruge dine... den anden model viser lorte
forslag». Af 428 viste forslag kom 411 fra modellen, og de blev valgt 2,9 % af
gangene mod 23,5 % for hans egne.

Den anden vej — fortsættelsen af en halvskreven sætning — er også fjernet
(28/9-2026): ingen flade brugte den. Modulet kalder derfor ikke længere nogen
model, og der findes ikke en eneste test her der patcher et model-kald: der er
intet kald at patche.
"""
from __future__ import annotations

import pytest

from core.runtime import db_composer_jarvis as dj
from core.services import composer_suggest as cs


# ──────────────────────────────────────────────── der kaldes INGEN model

def test_modulet_kalder_INGEN_model():
    """Kilde-vagt. Både den lokale models forslag og fortsættelses-formen er
    væk; tilbage står Jarvis' eget forslag. Der må ikke ligge et model-kald
    eller en model-adresse tilbage — heller ikke en betalt lane."""
    import inspect
    kilde = inspect.getsource(cs)
    assert "urllib" not in kilde
    assert "11434" not in kilde        # ingen ollama-adresse
    assert "deepseek" not in kilde     # ingen betalt lane
    assert "openai" not in kilde


# ──────────────────────────────────── forslag til den NAESTE besked (17/9)
#
# Bjoern: «det kommer dumpende mens jeg skriver, det er virkelig traels» — og
# «auto suggest skal jo vaere ud fra konteksten af DIN besked». Forslaget er
# altsaa ikke resten af hans saetning, men et bud paa hvad han kunne sige nu,
# vist dér hvor pladsholderen staar. Kilden er samtalen, ikke tastetrykkene.


def _samtale(*par):
    return [{"role": r, "content": c} for r, c in par]


def test_uden_SESSION_spoerges_der_ikke():
    assert cs.foreslaa_naeste("") == ""
    assert cs.foreslaa_naeste("   ") == ""


def test_en_TOM_samtale_giver_intet_forslag(monkeypatch):
    """Foerste besked i en ny samtale er hans egen. Der er intet at foreslaa
    ud fra, og GreetingHero staar der i forvejen."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: [])
    assert cs.foreslaa_naeste("s1") == ""


def test_mens_HANS_besked_venter_paa_svar_foreslaas_intet(monkeypatch):
    """Sidste besked er hans egen → turen er i gang. At foreslaa den naeste
    besked dér er at tale i munden paa et svar der er paa vej."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: _samtale(
        ("assistant", "Det er rettet."), ("user", "og deploy det"),
    ))
    assert cs.foreslaa_naeste("s1") == ""


def test_en_DB_fejl_giver_tomt_og_kaster_ikke(monkeypatch):
    monkeypatch.setattr(cs, "_samtale",
                        lambda sid: (_ for _ in ()).throw(RuntimeError("laast")))
    assert cs.foreslaa_naeste("s1") == ""


# ───────────────────────────── en STUMP giver intet forslag (17/9-2026)
#
# Maalt paa ti aegte samtaler: assistentens sidste besked kan vaere en stump —
# «4.», «OK», «Generation cancelled.» — og der er intet naeste skridt at bygge
# paa. Det gaelder ogsaa et forslag fra Jarvis selv: uden noget at bygge paa
# ville det vaere et bud uden grundlag.

@pytest.mark.parametrize("stump", ["4.", "OK", "Generation cancelled.", "Ja."])
def test_en_STUMP_til_sidst_giver_intet_forslag(monkeypatch, stump):
    """Der er intet naeste skridt at bygge paa — heller ikke for Jarvis selv."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: _samtale(("assistant", stump)))
    assert cs.foreslaa_naeste("s1") == ""


# ─────────────────────────────────────────────────── fladen skal kunne NAAS

def test_ruten_er_MONTERET_i_appen():
    """En flade ingen kan naa er husets hyppigste fejl. `_runtime_work_surface`
    var korrekt, komplet og usynlig i maanedsvis af praecis den grund."""
    from apps.api.jarvis_api.app import app
    stier = {getattr(r, "path", "") for r in app.routes}
    assert "/composer/suggest" in stier


def test_ruten_svarer_TOMT_frem_for_at_fejle(monkeypatch):
    """Et forslag er en bekvemmelighed. En klient der skulle haandtere
    fejlkoder for at kunne skrive videre, ville holde op med at virke af en
    grund der ikke rager den."""
    from apps.api.jarvis_api.routes import composer_suggest_routes as r
    monkeypatch.setattr(cs, "foreslaa_naeste_detaljer",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    assert r.suggest(r.Udkast(session_id="s1")) == {
        "forslag": "", "forslag_id": "", "kilde_besked_id": ""}


def test_ruten_baerer_forslaget_igennem(monkeypatch):
    from apps.api.jarvis_api.routes import composer_suggest_routes as r
    monkeypatch.setattr(cs, "foreslaa_naeste_detaljer", lambda s: {
        "forslag": "naeste til " + s, "forslag_id": "cs-x", "kilde_besked_id": "m1"})
    assert r.suggest(r.Udkast(session_id="s1"))["forslag"] == "naeste til s1"


def test_ruten_taaler_en_tom_krop():
    from apps.api.jarvis_api.routes import composer_suggest_routes as r
    assert r.suggest(r.Udkast()) == {
        "forslag": "", "forslag_id": "", "kilde_besked_id": ""}


def test_et_GAMMELT_kald_med_udkast_ignoreres(monkeypatch):
    """Feltet `udkast` stod i kontrakten indtil 28/9-2026. En klient der ikke
    er opdateret sender det stadig — det skal ignoreres, ikke fejle, og svaret
    skal vaere praecis det samme som uden."""
    from apps.api.jarvis_api.routes import composer_suggest_routes as r
    monkeypatch.setattr(cs, "foreslaa_naeste_detaljer", lambda s: {
        "forslag": "naeste til " + s, "forslag_id": "cs-x", "kilde_besked_id": "m1"})
    svar = r.suggest(r.Udkast(**{"udkast": "kan du lige", "session_id": "s1"}))
    assert svar["forslag"] == "naeste til s1"


# ─────────────────────────────────────────────── valget (fase 2, 20/9-2026)
#
# Bjoern: «vi skal gemme brugerens valg, dvs. om de brugte den suggested (tab)
# i composer eller skrev der egen besked saa naeste forslag bliver mere
# mig/maalrettet». Forslaget skal derfor baere et id ud til klienten, saa
# klienten kan melde tilbage hvad der skete med netop DET forslag.


def test_INTET_forslag_giver_tomme_id(monkeypatch):
    """Der er ikke noget at melde tilbage om — og en klient der fik et id uden
    et forslag, ville oprette en raekke for noget der aldrig blev vist."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: [])
    d = cs.foreslaa_naeste_detaljer("s1")
    assert d == {"forslag": "", "forslag_id": "", "kilde_besked_id": ""}


def test_ruten_registrerer_VIST_og_derefter_valget(isolated_runtime, monkeypatch):
    from apps.api.jarvis_api.routes import composer_suggest_routes as rute
    from core.runtime import db_composer_choice as dc

    rute.choice(rute.Valg(forslag_id="cs-9", session_id="s1",
                          forslag="Ret det og koer testene igen",
                          kilde_besked_id="message-3", valg="vist"))
    assert dc.seneste_valg()[0]["valg"] == "vist"
    rute.choice(rute.Valg(forslag_id="cs-9", valg="accepteret"))
    assert dc.seneste_valg()[0]["valg"] == "accepteret"


def test_ruten_fejler_ALDRIG(isolated_runtime, monkeypatch):
    """Komponisten maa ikke kunne gaa i stykker af en telemetri-skrivning."""
    from apps.api.jarvis_api.routes import composer_suggest_routes as rute
    from core.runtime import db_composer_choice as dc

    monkeypatch.setattr(dc, "noter_vist",
                        lambda **k: (_ for _ in ()).throw(RuntimeError("basen er nede")))
    assert rute.choice(rute.Valg(forslag_id="cs-1", session_id="s1",
                                 forslag="x", valg="vist")) == {"ok": True}


# ──────────────────────────────── Jarvis' EGET forslag (24/9-2026)
#
# Bjoern: «i chatview er det dig selv der saetter ord paa runderne... det
# burde endelig osse vaere dig der kommer med forslag i composer?» Raekke-
# foelgen er hele pointen:
#
#   Jarvis' eget forslag (hvis det findes)  ->  ellers staar feltet TOMT
#
# Lageret selv (gem/tag/kig/forbrug) er testet i test_db_composer_jarvis.py,
# og vaerktoejet han kalder i test_composer_suggest_tools.py. Her proves KUN
# hvornaar hans forslag vinder — og hvornaar feltet staar tomt.


_ASSISTENT_SVAR = "Det er rettet og verificeret — testene er groenne igen."


def _med_svar(monkeypatch, session: str = "s1"):
    """En samtale der slutter med et rigtigt svar fra Jarvis."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: [{
        "role": "assistant", "message_id": "message-42", "content": _ASSISTENT_SVAR}])


def test_JARVIS_forslag_vinder(isolated_runtime, monkeypatch):
    """Kernetesten. Ligger der et forslag fra Jarvis, er det HANS ord der
    moeder brugeren — og id'et baerer hans praefiks, saa telemetrien kan se
    hvor det kom fra."""
    _med_svar(monkeypatch)
    dj.gem_forslag(session_id="s1", forslag="Vis mig de to der står i karantaene")

    d = cs.foreslaa_naeste_detaljer("s1")
    assert d["forslag"] == "Vis mig de to der står i karantaene"
    # Id'et baerer Jarvis' praefiks, saa telemetrien kan se hvor det kom fra.
    assert d["forslag_id"].startswith("cj-")
    # Kilde-beskeden er den FAKTISKE sidste besked — ikke noget Jarvis gættede.
    assert d["kilde_besked_id"] == "message-42"


def test_uden_hans_forslag_staar_FELTET_TOMT(isolated_runtime, monkeypatch):
    """Den lokale model blev droppet 28/9-2026: «drop den anden models forslag
    og kun bruge dine». Uden et eget forslag er der intet bud — og et tomt felt
    er aerligere end et daarligt forslag."""
    _med_svar(monkeypatch)
    assert cs.foreslaa_naeste_detaljer("s1") == {
        "forslag": "", "forslag_id": "", "kilde_besked_id": ""}


def test_efter_forbrug_staar_feltet_TOMT_igen(isolated_runtime, monkeypatch):
    """Forslaget forbruges ved laesning. Naeste hentning i samme session giver
    intet — der er ingen model at falde tilbage til laengere."""
    _med_svar(monkeypatch)
    dj.gem_forslag(session_id="s1", forslag="fra Jarvis")

    assert cs.foreslaa_naeste_detaljer("s1")["forslag"] == "fra Jarvis"
    assert cs.foreslaa_naeste_detaljer("s1")["forslag"] == ""


def test_hans_forslag_bruges_ikke_naar_turen_IKKE_er_faerdig(isolated_runtime, monkeypatch):
    """Står der en ubesvaret besked fra Bjørn, er turen i gang. Så er der
    ingen «naeste besked» at foreslå — og forslaget skal blive liggende."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: _samtale(
        ("assistant", _ASSISTENT_SVAR), ("user", "og hvad med den anden?")))
    dj.gem_forslag(session_id="s1", forslag="fra Jarvis")

    assert cs.foreslaa_naeste_detaljer("s1")["forslag"] == ""
    assert dj.kig_forslag(session_id="s1") is not None, "forslaget skal vente, ikke forbruges"


def test_hans_forslag_bruges_ikke_paa_en_STUMP(isolated_runtime, monkeypatch):
    monkeypatch.setattr(cs, "_samtale", lambda sid: _samtale(("assistant", "OK.")))
    dj.gem_forslag(session_id="s1", forslag="fra Jarvis")
    assert cs.foreslaa_naeste_detaljer("s1")["forslag"] == ""
