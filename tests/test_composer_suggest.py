"""Forslag i komponisten — hvad der skrives videre mens man skriver.

## Hvorfor lokalt og ikke den betalte lane

Et forslag er baggrundsarbejde, ikke Bjørns tur. Reglen han har gentaget mange
gange — og som blev håndhævet i koden 14/9 — er at den betalte DeepSeek-API kun
må bruges i hans egne kørsler. Et forslag fyrer mens han *skriver*, altså før
der overhovedet er en tur. Derfor lokal ollama, og kun lokal.

Der er en grund mere, og den vejer tungere: **udkastet forlader aldrig
maskinen.** Halvskrevne sætninger er det mest private der findes i en
samtale — de indeholder det man fortryder, omformulerer eller sletter.

## Hvorfor et kort loft på ventetiden

`semantic_memory._ollama_base_url` bærer husets erfaring: recall-embeds
konkurrerede med det synlige svar om GPU-ollamaen og køede **28–91 sekunder**.
Et forslag der kommer efter et sekund er allerede uinteressant — brugeren har
skrevet videre. Derfor et hårdt loft, og tomt svar frem for et sent.
"""
from __future__ import annotations

import pytest

from core.runtime import db_composer_jarvis as dj
from core.services import composer_suggest as cs


# ─────────────────────────────────────────────────────────── hvad der sendes

def test_forslaget_er_KUN_fortsaettelsen(monkeypatch):
    """Modellen gentager gerne hele sætningen. Gjorde vi ikke noget, ville
    komponisten vise «kan du tjekke kan du tjekke om…»."""
    monkeypatch.setattr(cs, "_kald_model",
                        lambda *a, **k: "kan du lige tjekke om der er fejl i filen")
    assert cs.foreslaa("kan du lige tjekke om der er") == " fejl i filen"


def test_gentagelse_med_ANDEN_store_bogstaver_fanges_ogsaa():
    """Modellen retter gerne begyndelsesbogstavet. Et match der kræver samme
    kasse ville lade gentagelsen slippe igennem."""
    assert cs._afkort("kan du lige", "Kan du lige tjekke det") == " tjekke det"


def test_et_svar_der_IKKE_gentager_bruges_som_det_er():
    """`_afkort` svarer kun paa «hvor meget er gentagelse». Mellemrummet der
    haefter fortsaettelsen paa det sidste ord, saettes i `foreslaa` — ét sted,
    saa det ikke afhaenger af om modellen huskede at skrive det."""
    assert cs._afkort("kan du lige", " tjekke det") == "tjekke det"


def test_foreslaa_HAEFTER_fortsaettelsen_paa_med_et_mellemrum(monkeypatch):
    monkeypatch.setattr(cs, "_kald_model", lambda *a, **k: "tjekke det")
    assert cs.foreslaa("kan du lige") == " tjekke det"


def test_tegnsaetning_haefter_UDEN_mellemrum(monkeypatch):
    """«…tjekke det» + «, tak» — ikke «…tjekke det , tak»."""
    monkeypatch.setattr(cs, "_kald_model", lambda *a, **k: ", tak")
    assert cs.foreslaa("kan du lige tjekke det") == ", tak"


def test_kun_FOERSTE_linje(monkeypatch):
    """En komponist-linje er én linje. Resten er modellen der begynder at
    skrive svaret i stedet for forslaget."""
    monkeypatch.setattr(cs, "_kald_model", lambda *a, **k: " se på det\n\nHer er hvad jeg fandt:")
    assert cs.foreslaa("kan du lige") == " se på det"


def test_omsluttende_anfoerselstegn_fjernes(monkeypatch):
    """Maalt 14/9: qwen svarede `"kan du lige tjekke om der er fejl?"` — med
    citationstegn om hele sætningen."""
    monkeypatch.setattr(cs, "_kald_model", lambda *a, **k: '"kan du lige tjekke det"')
    assert cs.foreslaa("kan du lige") == " tjekke det"


def test_forslaget_er_KORT(monkeypatch):
    """Et langt forslag er ikke et forslag, det er et svar. Klippes ved et
    ordskel, ikke midt i et ord — et halvt ord ligner en fejl."""
    monkeypatch.setattr(cs, "_kald_model", lambda *a, **k: " " + "ord " * 60)
    ud = cs.foreslaa("skriv")
    assert len(ud) <= cs.MAKS_TEGN
    assert not ud.endswith("or")


# ───────────────────────────────────────────────── hvornaar der IKKE spoerges

def test_for_KORT_udkast_spoerger_slet_ikke(monkeypatch):
    """Under nogle faa tegn er der intet at gaette paa, og et forslag ville
    vaere stoej der flimrer ved hvert tastetryk."""
    kaldt: list[int] = []
    monkeypatch.setattr(cs, "_kald_model", lambda *a, **k: kaldt.append(1) or "x")
    assert cs.foreslaa("ka") == ""
    assert kaldt == []


def test_tomt_udkast_spoerger_ikke(monkeypatch):
    monkeypatch.setattr(cs, "_kald_model", lambda *a, **k: pytest.fail("spurgte alligevel"))
    assert cs.foreslaa("") == ""
    assert cs.foreslaa("   ") == ""


def test_et_FAERDIGT_udkast_faar_intet_forslag(monkeypatch):
    """Slutter sætningen paa tegnsaetning, er brugeren faerdig. At foreslaa
    videre dér er at tale i munden paa ham."""
    monkeypatch.setattr(cs, "_kald_model", lambda *a, **k: pytest.fail("spurgte alligevel"))
    for slut in ("kan du tjekke det?", "gør det.", "ja!", "vent:"):
        assert cs.foreslaa(slut) == ""


def test_et_MEGET_langt_udkast_spoerger_ikke(monkeypatch):
    """Skriver han et helt afsnit, ved han hvad han vil. Og prompten skal ikke
    vokse ubegraenset."""
    monkeypatch.setattr(cs, "_kald_model", lambda *a, **k: pytest.fail("spurgte alligevel"))
    assert cs.foreslaa("x " * 400) == ""


# ─────────────────────────────────────────────────────────── den maa ikke gøre skade

def test_en_MODELFEJL_giver_tomt_og_kaster_ikke(monkeypatch):
    """Komponisten skal skrive videre uanset. Et forslag er en bekvemmelighed,
    ikke en funktion man kan miste."""
    monkeypatch.setattr(cs, "_kald_model",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    assert cs.foreslaa("kan du lige tjekke") == ""


def test_et_TOMT_modelsvar_giver_tomt(monkeypatch):
    monkeypatch.setattr(cs, "_kald_model", lambda *a, **k: "")
    assert cs.foreslaa("kan du lige tjekke") == ""


def test_et_svar_der_kun_ER_udkastet_giver_tomt(monkeypatch):
    """Modellen gentog og tilfoejede intet. Et tomt forslag er aerligt; et
    forslag der foreslaar det man allerede har skrevet, er stoej."""
    monkeypatch.setattr(cs, "_kald_model", lambda *a, **k: "kan du lige tjekke")
    assert cs.foreslaa("kan du lige tjekke") == ""


# ─────────────────────────────────────────────────── den betalte lane er FORBUDT

def test_der_bruges_en_LOKAL_model():
    """Kilde-vagt paa den regel Bjoern har gentaget mange gange: den betalte
    DeepSeek-API er kun til hans egne ture. Et forslag fyrer FOER der er en tur.

    Og udkastet er det mest private i en samtale — halvskrevne saetninger
    indeholder det man fortryder og sletter. Det maa ikke forlade maskinen.
    """
    import inspect
    kilde = inspect.getsource(cs)
    assert "127.0.0.1" in kilde or "_ollama_base_url" in kilde
    assert "deepseek.com" not in kilde


def test_ventetiden_har_et_KORT_loft():
    """Huset har erfaringen skrevet ned: recall-embeds koeede 28-91 sekunder
    bag det synlige svar paa samme GPU-ollama. Et forslag der kommer efter et
    sekund er allerede uinteressant."""
    assert cs.TIMEOUT_S <= 2.0


def test_modellen_kan_saettes_uden_kode_deploy():
    """Bjoern har qwen paa sin GPU i dag; i morgen er det en anden."""
    assert cs.MODEL_NOEGLE == "composer_suggest_model"


# ──────────────────────────────────── forslag til den NAESTE besked (17/9)
#
# Bjoern: «det kommer dumpende mens jeg skriver, det er virkelig traels» — og
# «auto suggest skal jo vaere ud fra konteksten af DIN besked». Forslaget er
# altsaa ikke resten af hans saetning, men et bud paa hvad han kunne sige nu,
# vist dér hvor pladsholderen staar. Kilden er samtalen, ikke tastetrykkene.


def _samtale(*par):
    return [{"role": r, "content": c} for r, c in par]


def test_uden_SESSION_spoerges_der_ikke(monkeypatch):
    monkeypatch.setattr(cs, "_kald_model", lambda p: pytest.fail("spurgte alligevel"))
    assert cs.foreslaa_naeste("") == ""
    assert cs.foreslaa_naeste("   ") == ""


def test_en_TOM_samtale_giver_intet_forslag(monkeypatch):
    """Foerste besked i en ny samtale er hans egen. Der er intet at foreslaa
    ud fra, og GreetingHero staar der i forvejen."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: [])
    monkeypatch.setattr(cs, "_kald_model", lambda p: pytest.fail("spurgte alligevel"))
    assert cs.foreslaa_naeste("s1") == ""


def test_mens_HANS_besked_venter_paa_svar_foreslaas_intet(monkeypatch):
    """Sidste besked er hans egen → turen er i gang. At foreslaa den naeste
    besked dér er at tale i munden paa et svar der er paa vej."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: _samtale(
        ("assistant", "Det er rettet."), ("user", "og deploy det"),
    ))
    monkeypatch.setattr(cs, "_kald_model", lambda p: pytest.fail("spurgte alligevel"))
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
    """Der er intet naeste skridt at bygge paa — hverken for en model eller
    for Jarvis selv."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: _samtale(("assistant", stump)))
    monkeypatch.setattr(cs, "_kald_model", lambda p: pytest.fail("spurgte alligevel"))
    assert cs.foreslaa_naeste("s1") == ""


def test_ruten_vaelger_tilstand_efter_om_der_ER_et_udkast(monkeypatch):
    """Samme endpoint, to tilstande. Mobilen sender et udkast og skal stadig
    faa fortsaettelsen; desk sender et tomt felt og skal have naeste besked."""
    from apps.api.jarvis_api.routes import composer_suggest_routes as r
    monkeypatch.setattr(cs, "foreslaa", lambda u: " tjekke det")
    # Naeste-formen gaar siden 20/9-2026 gennem `foreslaa_naeste_detaljer`,
    # fordi klienten skal have et id at melde sit valg tilbage paa.
    monkeypatch.setattr(cs, "foreslaa_naeste_detaljer", lambda s: {
        "forslag": f"naeste til {s}", "forslag_id": "cs-x", "kilde_besked_id": "m1"})
    assert r.suggest(r.Udkast(udkast="kan du lige", session_id="s1"))["forslag"] == " tjekke det"
    assert r.suggest(r.Udkast(udkast="   ", session_id="s1"))["forslag"] == "naeste til s1"
    assert r.suggest(r.Udkast(session_id="s1"))["forslag"] == "naeste til s1"


# ─────────────────────────────────────────────────── fladen skal kunne NAAS

def test_ruten_er_MONTERET_i_appen():
    """En flade ingen kan naa er husets hyppigste fejl. `_runtime_work_surface`
    var korrekt, komplet og usynlig i maanedsvis af praecis den grund."""
    from apps.api.jarvis_api.app import app
    stier = {getattr(r, "path", "") for r in app.routes}
    assert "/composer/suggest" in stier


def test_ruten_svarer_TOMT_frem_for_at_fejle(monkeypatch):
    """Et forslag er en bekvemmelighed. En klient der skulle haandtere
    fejlkoder for at kunne skrive videre, ville holde op med at virke naar
    GPU'en var optaget."""
    from apps.api.jarvis_api.routes import composer_suggest_routes as r
    monkeypatch.setattr(cs, "foreslaa",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    # Svaret bærer siden 20/9-2026 også `forslag_id` og `kilde_besked_id`
    # (fase 2), men tomme her: der er intet forslag at melde et valg om.
    assert r.suggest(r.Udkast(udkast="kan du lige tjekke")) == {
        "forslag": "", "forslag_id": "", "kilde_besked_id": ""}


def test_ruten_baerer_forslaget_igennem(monkeypatch):
    from apps.api.jarvis_api.routes import composer_suggest_routes as r
    monkeypatch.setattr(cs, "foreslaa", lambda u: " tjekke det")
    assert r.suggest(r.Udkast(udkast="kan du lige"))["forslag"] == " tjekke det"


def test_ruten_taaler_en_tom_krop():
    from apps.api.jarvis_api.routes import composer_suggest_routes as r
    assert r.suggest(r.Udkast()) == {
        "forslag": "", "forslag_id": "", "kilde_besked_id": ""}


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


def test_MOBILENS_form_har_intet_valg_at_registrere(monkeypatch):
    """Fortsaettelses-formen har ingen Tab-tast at trykke paa i et felt man
    skriver i. Tomme id'er, saa der ikke opstaar raekker uden et valg."""
    from apps.api.jarvis_api.routes import composer_suggest_routes as rute

    monkeypatch.setattr(cs, "_kald_model", lambda p: "tjekke det")
    svar = rute.suggest(rute.Udkast(udkast="kan du lige", session_id="s1"))
    assert svar["forslag"].strip() == "tjekke det"
    assert svar["forslag_id"] == "" and svar["kilde_besked_id"] == ""


# ──────────────────────────────── Jarvis' EGET forslag (24/9-2026)
#
# Bjoern: «i chatview er det dig selv der saetter ord paa runderne... det
# burde endelig osse vaere dig der kommer med forslag i composer?» Raekke-
# foelgen er hele pointen:
#
#   Jarvis' eget forslag (hvis det findes)  ->  den lokale model (ellers)
#
# Lageret selv (gem/tag/kig/forbrug) er testet i test_db_composer_jarvis.py,
# og vaerktoejet han kalder i test_composer_suggest_tools.py. Her proves KUN
# raekkefoelgen: hvornaar hans forslag vinder, og hvornaar det viger.


_ASSISTENT_SVAR = "Det er rettet og verificeret — testene er groenne igen."


def _med_svar(monkeypatch, session: str = "s1"):
    """En samtale der slutter med et rigtigt svar fra Jarvis."""
    monkeypatch.setattr(cs, "_samtale", lambda sid: [{
        "role": "assistant", "message_id": "message-42", "content": _ASSISTENT_SVAR}])


def test_JARVIS_forslag_vinder_og_modellen_spoerges_SLET_IKKE(isolated_runtime, monkeypatch):
    """Kernetesten. Ligger der et forslag fra Jarvis, maa den lokale model ikke
    kaldes — hverken for at overskrive det eller for at spilde et GPU-kald."""
    _med_svar(monkeypatch)
    monkeypatch.setattr(cs, "_kald_model",
                        lambda *a, **k: pytest.fail("spurgte den lokale model alligevel"))
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
    er aerligere end et daarligt forslag. Modellen maa ikke spoerges."""
    _med_svar(monkeypatch)
    monkeypatch.setattr(cs, "_kald_model",
                        lambda *a, **k: pytest.fail("spurgte den lokale model alligevel"))
    assert cs.foreslaa_naeste_detaljer("s1") == {
        "forslag": "", "forslag_id": "", "kilde_besked_id": ""}


def test_efter_forbrug_staar_feltet_TOMT_igen(isolated_runtime, monkeypatch):
    """Forslaget forbruges ved laesning. Naeste hentning i samme session giver
    intet — der er ingen model at falde tilbage til laengere."""
    _med_svar(monkeypatch)
    monkeypatch.setattr(cs, "_kald_model",
                        lambda *a, **k: pytest.fail("spurgte den lokale model alligevel"))
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


def test_den_GAMLE_streng_form_svarer_ogsaa_med_hans_forslag(isolated_runtime, monkeypatch):
    """Mobilen kalder `foreslaa_naeste` og må ikke braekke."""
    _med_svar(monkeypatch)
    monkeypatch.setattr(cs, "_kald_model", lambda *a, **k: pytest.fail("spurgte modellen"))
    dj.gem_forslag(session_id="s1", forslag="deploy det til ct105")
    assert cs.foreslaa_naeste("s1") == "deploy det til ct105"


def test_ruten_svarer_med_hans_forslag_og_dets_id(isolated_runtime, monkeypatch):
    from apps.api.jarvis_api.routes import composer_suggest_routes as rute

    _med_svar(monkeypatch)
    monkeypatch.setattr(cs, "_kald_model", lambda *a, **k: pytest.fail("spurgte modellen"))
    dj.gem_forslag(session_id="s1", forslag="Ret det og koer testene igen")

    svar = rute.suggest(rute.Udkast(udkast="", session_id="s1"))
    assert svar["forslag"] == "Ret det og koer testene igen"
    assert svar["forslag_id"].startswith("cj-")
    assert svar["kilde_besked_id"] == "message-42"
