"""Fejemaskinen skriver DIREKTE i registret — så politikken skal være
utvetydig, og værnene skal holde. Alt kører gennem injicerede kroge; ingen
test rører en udbyder eller en rigtig fil.
"""
from core.services.model_catalogue_sweep import (
    beslut, egnet_til_agentarbejde, foreslaa_navn, kandidater_for, sweep_provider,
)


def _r(**kw):
    grund = {"callable": True, "tools": True, "follows": True, "code": True,
             "score": 100, "error": "", "sprunget": []}
    grund.update(kw)
    return grund


# ── politik ─────────────────────────────────────────────────────────────────

def test_en_model_der_ikke_svarer_slaas_fra_med_grunden():
    aktiv, grund = beslut(_r(callable=False, score=0, error="410 Gone"))
    assert aktiv is False and "410 Gone" in grund


def test_en_hoej_score_forbliver_aktiv():
    assert beslut(_r())[0] is True


def test_sprungne_delproever_naevnes_i_grunden():
    aktiv, grund = beslut(_r(score=100, sprunget=["code"]))
    assert aktiv is True and "code" in grund


def test_kun_modeller_der_kan_BRUGE_et_vaerktoejsresultat_duer_til_agenter():
    """En der kalder og ignorerer svaret ligner en der arbejder. Det var
    præcis explore-fejlen 7/9."""
    assert egnet_til_agentarbejde(_r()) is True
    assert egnet_til_agentarbejde(_r(follows=False, score=65)) is False
    # høj nok score, men uden follows → stadig nej
    assert egnet_til_agentarbejde(_r(follows=False, score=90)) is False


# ── kandidat-udvælgelse ─────────────────────────────────────────────────────

def test_registrerede_proeves_ALTID():
    ud = kandidater_for("p", registrerede=["a", "b"], fra_api=[], statiske=[])
    assert ud == ["a", "b"]


def test_nye_er_begraensede_saa_en_uskyldig_udbyder_ikke_haemres():
    """OpenRouter lister 430. At prøve dem alle ville tage timer."""
    ud = kandidater_for("p", registrerede=["a"], statiske=[],
                        fra_api=[f"m{i}" for i in range(50)], maks_nye=3)
    assert ud[0] == "a" and len(ud) == 4


def test_gratis_modeller_proeves_foerst():
    ud = kandidater_for("p", registrerede=[], statiske=[],
                        fra_api=["dyr-model", "billig:free"], maks_nye=1)
    assert ud == ["billig:free"]


def test_kataloget_vejer_tungere_end_udbyderens_reklame():
    ud = kandidater_for("p", registrerede=[], statiske=["verificeret"],
                        fra_api=["reklame:free"], maks_nye=1)
    assert ud == ["verificeret"]


# ── værnet ──────────────────────────────────────────────────────────────────

def test_slaar_ALDRIG_alt_fra_hos_en_udbyder_paa_én_koersel(monkeypatch):
    """En dårlig dag må ikke tømme puljen — cheap lane må aldrig dø.

    Fejlen her er ÆGTE (410 Gone), ikke forbigående: forbigående fejl har
    deres eget værn (`beslut` → None). Det her er værnet mod at ALT hos én
    udbyder dumper på én kørsel, fx fordi udbyderen er nede."""
    import core.services.model_catalogue_sweep as sw
    monkeypatch.setattr(sw, "_registrerede_modeller", lambda p: (["a", "b"], "default"))
    skrevet = []
    rapport = sw.sweep_provider(
        "nvidia-nim",
        hent_modeller=lambda p, prof: [],
        proev=lambda **kw: _r(callable=False, score=0, error="410 Gone"),
        skriv=lambda **kw: skrevet.append(kw) or True,
    )
    assert skrevet == [], "rørte registret selvom ALT dumpede"
    assert "rører intet" in rapport["fejl"]


def test_en_enkelt_doed_model_slaas_fra_naar_andre_lever(monkeypatch):
    import core.services.model_catalogue_sweep as sw
    monkeypatch.setattr(sw, "_registrerede_modeller", lambda p: (["god", "doed"], "default"))
    skrevet = []

    def proev(**kw):
        return _r() if kw["model"] == "god" else _r(callable=False, score=0, error="410")

    r = sw.sweep_provider("nvidia-nim", hent_modeller=lambda p, prof: [],
                          proev=proev,
                          skriv=lambda **kw: (skrevet.append((kw["model"], kw["aktiv"])), True)[1])
    assert ("doed", False) in skrevet and ("god", True) in skrevet
    assert [x["model"] for x in r["slaaet_fra"]] == ["doed"]
    assert r["agent_egnede"] == ["god"]


# ── beskeden til mobilen ────────────────────────────────────────────────────

from core.services.model_catalogue_sweep import sammendrag, underret_ejeren


def test_ingen_aendringer_giver_INGEN_push():
    """En ugentlig «alt er som før» bliver ignoreret indtil den uge hvor den
    ikke er det."""
    assert sammendrag([{"provider": "p", "uaendret": 9, "slaaet_fra": [],
                        "nye": [], "genoplivet": [], "fejl": ""}]) == ""


def test_beskeden_naevner_hvad_der_faktisk_skete():
    b = sammendrag([{
        "provider": "nvidia-nim",
        "slaaet_fra": [{"model": "meta/llama-3.1-8b", "grund": "410"}],
        "nye": [{"model": "minimax-m3", "score": 100}],
        "genoplivet": [], "fejl": "",
    }])
    assert "Slået fra" in b and "meta/llama-3.1-8b" in b
    assert "Nye" in b and "minimax-m3" in b


def test_et_uroert_vaern_naevnes_ogsaa():
    b = sammendrag([{"provider": "groq", "slaaet_fra": [], "nye": [],
                     "genoplivet": [], "fejl": "alle kandidater dumpede — rører intet."}])
    assert "Rørte ikke" in b and "groq" in b


def test_pushen_gaar_KUN_til_ejeren(monkeypatch):
    import core.services.model_catalogue_sweep as sw

    class Ejer:
        discord_id = "ejer-123"

    monkeypatch.setattr("core.identity.users.get_owner", lambda: Ejer())
    sendt = []
    assert underret_ejeren("noget skete", send=lambda uid, m, t: sendt.append((uid, m, t)) or True)
    assert sendt == [("ejer-123", "noget skete", "Cheap lane")]


def test_ingen_ejer_giver_ingen_push(monkeypatch):
    monkeypatch.setattr("core.identity.users.get_owner", lambda: None)
    assert underret_ejeren("noget", send=lambda *a: True) is False


def test_tom_besked_sendes_aldrig():
    assert underret_ejeren("", send=lambda *a: True) is False
    assert underret_ejeren("   ", send=lambda *a: True) is False


def test_en_udbyder_der_vaelter_stopper_ikke_de_andre(monkeypatch):
    import core.services.model_catalogue_sweep as sw

    def sur(p, **kw):
        if p == "a":
            raise RuntimeError("nede")
        return {"provider": p, "proevet": 1, "slaaet_fra": [], "nye": [],
                "genoplivet": [], "agent_egnede": [], "uaendret": 1, "fejl": ""}

    monkeypatch.setattr(sw, "sweep_provider", sur)
    ud = sw.sweep_alle(providers=["a", "b"], underret=False)
    assert len(ud["rapporter"]) == 2
    assert "nede" in ud["rapporter"][0]["fejl"]


def test_en_katalogmodel_meldes_ikke_som_NY_hver_uge(monkeypatch):
    """Første kørsel meldte gemma4:31b-cloud som ny, selvom den stod i puljen —
    den kom bare fra static_models, ikke fra registret. En push man lærer at
    ignorere er værre end ingen push."""
    import core.services.model_catalogue_sweep as sw
    monkeypatch.setattr(sw, "_registrerede_modeller", lambda p: ([], "default"))
    monkeypatch.setattr(sw, "CHEAP_PROVIDER_DEFAULTS", None, raising=False)
    from core.services.cheap_provider_catalogue import CHEAP_PROVIDER_DEFAULTS as C
    assert "gemma4:31b-cloud" in C["ollama-a2"]["static_models"]

    r = sw.sweep_provider("ollama-a2", hent_modeller=lambda p, prof: [],
                          proev=lambda **kw: _r(), skriv=lambda **kw: False)
    assert r["nye"] == [], "en katalog-model blev meldt som ny"
    assert r["proevet"] == 1


def test_en_katalogmodel_kan_slaas_FRA_selvom_den_ikke_stod_i_registret(monkeypatch, tmp_path):
    """Blind vinkel 7/9: «tilføj ikke en model der dumpede» gjorde at cerebras'
    modeller — som kun lever i static_models — aldrig kunne slås fra. Sonden
    dømte dem 0 («Payment required»), og dommen blev tavst kasseret."""
    import json
    import core.services.model_catalogue_sweep as sw
    from core.runtime import config as cfg

    f = tmp_path / "provider_router.json"
    f.write_text(json.dumps({"providers": [], "models": []}))
    monkeypatch.setattr(cfg, "PROVIDER_ROUTER_FILE", f)

    tilføjet = []

    def falsk_reg(**kw):
        d = json.loads(f.read_text())
        d["models"].append({"provider": kw["provider"], "model": kw["model"],
                            "lane": "cheap", "enabled": True})
        f.write_text(json.dumps(d))
        tilføjet.append(kw["model"])

    monkeypatch.setattr("core.runtime.provider_router.configure_provider_router_entry", falsk_reg)
    # Modellen hentes FRA kataloget, ikke skrevet i haanden.
    #
    # 1/10-2026: her stod `gemma-4-31b`, som blev fjernet fra cerebras'
    # static_models 27/9 («model-not-found og væk fra /models»). Et navn der
    # ikke findes i kataloget kan ikke slås fra, så testen målte ingenting og
    # gik rød — den var ikke i stykker, den var efterladt. Bindes den til
    # listen, følger den kataloget næste gang det skifter.
    from core.services.cheap_provider_catalogue import CHEAP_PROVIDER_DEFAULTS as _KAT
    model = _KAT["cerebras"]["static_models"][0]
    ændret = sw._skriv_registret(provider="cerebras", model=model, aktiv=False,
                                 grund="Payment required", score=0,
                                 detalje={"follows": False}, profil="default")
    d = json.loads(f.read_text())
    post = [m for m in d["models"] if m["model"] == model]
    assert post and post[0]["enabled"] is False
    assert "Payment required" in post[0]["disabled_reason"]


def test_en_tilfaeldig_ny_model_der_dumper_tilfoejes_IKKE(monkeypatch, tmp_path):
    """Den har ingen plads at miste — at skrive den ind ville bare fylde."""
    import json
    import core.services.model_catalogue_sweep as sw
    from core.runtime import config as cfg
    f = tmp_path / "provider_router.json"
    f.write_text(json.dumps({"providers": [], "models": []}))
    monkeypatch.setattr(cfg, "PROVIDER_ROUTER_FILE", f)
    assert sw._skriv_registret(provider="cerebras", model="en-helt-ny-model",
                               aktiv=False, grund="404", score=0,
                               detalje={}, profil="default") is False
    assert json.loads(f.read_text())["models"] == []


def test_et_rate_limit_er_ikke_en_dom():
    """Første kørsel slog nvidia-nim/minimax-m3 fra på et 429 — en model der
    var verificeret minutter forinden. Delprøverne var beskyttet mod
    forbigående fejl; den FØRSTE var ikke."""
    aktiv, grund = beslut(_r(callable=False, score=0,
                             error='CheapProviderError: {"status":429,"title":"Too Many Requests"}'))
    assert aktiv is None, "en travl udbyder må ikke koste modellen dens plads"
    assert "kunne ikke prøves" in grund


def test_en_aegte_doed_model_slaas_stadig_fra():
    aktiv, _ = beslut(_r(callable=False, score=0, error="410 Gone — end of life"))
    assert aktiv is False


def test_ikke_afgjorte_modeller_roeres_ikke(monkeypatch):
    import core.services.model_catalogue_sweep as sw
    monkeypatch.setattr(sw, "_registrerede_modeller", lambda p: (["m"], "default"))
    skrevet = []
    r = sw.sweep_provider("nvidia-nim", hent_modeller=lambda p, prof: [],
                          proev=lambda **kw: _r(callable=False, score=0, error="429 rate limit"),
                          skriv=lambda **kw: skrevet.append(kw) or True)
    assert skrevet == [], "skrev selvom dommen var uafgjort"
    assert r["ikke_afgjort"][0]["model"] == "m"


# ── navne-drift: opdater mod provideren frem for at fjerne ──────────────────
#
# Bjørn 10/10-2026: «De steder det handler om model not found skal vi opdatere
# vores model katalog mod provideren frem for at fjerne dem.» Udbyderne fjerner
# suffikser (":free") og flytter gratis-modeller til betalte slugs — navnet
# ændrer sig, modellen gør ikke. Fejemaskinen HENTER allerede udbyderens liste;
# her oversættes ét navn til et andet i stedet for at slå slottet fra.

def test_foreslaa_navn_finder_providerens_nye_navn():
    nyt = foreslaa_navn("vendor/model-v2:beta", "Model not exist.",
                        ["vendor/model-v2:stable", "noget/andet"])
    assert nyt == "vendor/model-v2:stable"


def test_foreslaa_navn_omdoeber_ikke_gratis_til_betalt():
    """Bjørn 10/10-2026: «vi bruger deres free pool». Flytter en gratis model
    til en betalt slug, er det IKKE en navne-drift vi følger — slottet skal
    blive i free pool (eller slås fra), ikke begynde at betale."""
    assert foreslaa_navn("minimax/minimax-m3:free", "Model not exist.",
                         ["minimax/minimax-m3"]) is None
    assert foreslaa_navn("nvidia/nemotron-3-nano-30b-a3b:free",
                         "unavailable for free. The paid version is available now",
                         ["nvidia/nemotron-3-nano-30b-a3b"]) is None


def test_foreslaa_navn_returnerer_None_naar_ingen_ligner():
    assert foreslaa_navn("minimax/minimax-m3:free", "Model not exist.",
                         ["noget/helt-andet"]) is None


def test_foreslaa_navn_roerer_ikke_ved_en_rate_limit():
    """En travl udbyder må ikke få os til at omdøbe en model der er rask."""
    assert foreslaa_navn("vendor/model-v2:beta",
                         '{"status":429,"title":"Too Many Requests"}',
                         ["vendor/model-v2:stable"]) is None


def test_foreslaa_navn_springer_modeller_over_vi_allerede_har():
    assert foreslaa_navn("m:free", "Model not exist.", ["m"], kendte={"m"}) is None


def test_foreslaa_navn_returnerer_ikke_modellen_selv():
    assert foreslaa_navn("m", "Model not exist.", ["m"]) is None


def test_sweep_omdoeber_naar_provideren_har_det_nye_navn(monkeypatch):
    import core.services.model_catalogue_sweep as sw
    monkeypatch.setattr(sw, "_registrerede_modeller",
                        lambda p: (["vendor/model-v2:beta"], "default"))
    skrevet = []

    def proev(**kw):
        if kw["model"].endswith(":beta"):
            return _r(callable=False, score=0, error="Model not exist.")
        return _r(score=95)

    r = sw.sweep_provider(
        "openrouter",
        hent_modeller=lambda p, prof: ["vendor/model-v2:stable"],
        proev=proev,
        skriv=lambda **kw: (skrevet.append((kw["model"], kw["aktiv"])), True)[1],
    )
    assert ("vendor/model-v2:stable", True) in skrevet, "det nye navn blev ikke aktiveret"
    assert r["omdoebt"] and r["omdoebt"][0]["fra"] == "vendor/model-v2:beta"
    assert r["omdoebt"][0]["til"] == "vendor/model-v2:stable"


def test_sweep_omdoeber_IKKE_gratis_til_betalt(monkeypatch):
    """Bjørn 10/10-2026: cheap lane bruger openrouters free pool. Er en gratis
    model flyttet til en betalt slug, omdøbes slottet IKKE — det bliver i free
    pool (slået fra), ikke flyttet til at betale."""
    import core.services.model_catalogue_sweep as sw
    monkeypatch.setattr(sw, "_registrerede_modeller",
                        lambda p: (["minimax/minimax-m3:free"], "default"))
    skrevet = []

    r = sw.sweep_provider(
        "openrouter",
        hent_modeller=lambda p, prof: ["minimax/minimax-m3"],
        proev=lambda **kw: _r(callable=False, score=0, error="Model not exist."),
        skriv=lambda **kw: (skrevet.append((kw["model"], kw["aktiv"])), True)[1],
    )
    assert r["omdoebt"] == [], "en gratis model blev omdøbt til en betalt"
    assert ("minimax/minimax-m3", True) not in skrevet


def test_sweep_omdoeber_IKKE_naar_det_nye_navn_ogsaa_dumper(monkeypatch):
    """Finder vi et nyt navn der også dumper, er der intet vundet — så gælder
    den gamle dom, og slottet slås fra som før."""
    import core.services.model_catalogue_sweep as sw
    monkeypatch.setattr(sw, "_registrerede_modeller",
                        lambda p: (["sund", "vendor/model-v2:beta"], "default"))
    skrevet = []

    def proev(**kw):
        return _r(score=95) if kw["model"] == "sund" else _r(
            callable=False, score=0, error="Model not exist.")

    r = sw.sweep_provider(
        "openrouter",
        hent_modeller=lambda p, prof: ["vendor/model-v2:stable"],
        proev=proev,
        skriv=lambda **kw: (skrevet.append((kw["model"], kw["aktiv"])), True)[1],
        maks_nye=0,
    )
    assert r["omdoebt"] == []
    assert ("vendor/model-v2:beta", False) in skrevet


def test_omdoebt_naevnes_i_beskeden():
    b = sammendrag([{
        "provider": "openrouter", "slaaet_fra": [], "nye": [], "genoplivet": [],
        "fejl": "",
        "omdoebt": [{"fra": "minimax/minimax-m3:free",
                     "til": "minimax/minimax-m3", "score": 95}],
    }])
    assert "Omdøbt" in b and "minimax/minimax-m3" in b
