"""Fejemaskinen skriver DIREKTE i registret — så politikken skal være
utvetydig, og værnene skal holde. Alt kører gennem injicerede kroge; ingen
test rører en udbyder eller en rigtig fil.
"""
from core.services.model_catalogue_sweep import (
    beslut, egnet_til_agentarbejde, kandidater_for, sweep_provider,
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
    """En travl dag eller en netværkshikke må ikke tømme puljen — cheap lane
    må aldrig dø."""
    skrevet = []
    rapport = sweep_provider(
        "nvidia-nim",
        hent_modeller=lambda p, prof: [],
        proev=lambda **kw: _r(callable=False, score=0, error="timeout"),
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
    # gemma-4-31b STÅR i cerebras' static_models
    ændret = sw._skriv_registret(provider="cerebras", model="gemma-4-31b", aktiv=False,
                                 grund="Payment required", score=0,
                                 detalje={"follows": False}, profil="default")
    d = json.loads(f.read_text())
    post = [m for m in d["models"] if m["model"] == "gemma-4-31b"]
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
