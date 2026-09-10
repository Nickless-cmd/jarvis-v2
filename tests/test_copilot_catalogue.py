"""Hvad Copilot-abonnementet faktisk giver — spurgt, ikke antaget.

Bjoern 10/9-2026: de gratis modeller kostede en hel eftermiddag. MAALT paa
API'et samme dag:

  * 56 modeller, og ALLE chat-modeller kan kalde vaerktoejer. Det problem der
    kostede eftermiddagen findes ikke i denne pool.
  * MULTIPLIER-MODELLEN FINDES IKKE MERE: «Your billing plan has changed to
    usage-based billing and model multipliers no longer apply.» Repoets
    opdeling i copilot-free (0x) og copilot-premium (1x+) beskriver noget der
    ikke eksisterer.
  * KATALOGET VAR FORAELDET: `claude-sonnet-4.6` og `gemini-3.1-pro-preview`
    staar i config og findes ikke paa API'et.

Rangeringen er GITHUB'S EGEN (`model_picker_category`), ikke min fornemmelse.
"""
from __future__ import annotations

from core.services.copilot_catalogue import OPGAVE_TIER, _brugbar, rangeret


def test_opgaverne_har_hver_sin_praeference():
    assert OPGAVE_TIER["kode"][0] == "powerful", (
        "kodearbejde skal have den staerke model foerst — et forkert svar "
        "koster en runde mere, og saa er den dyre model den billigste")
    assert OPGAVE_TIER["research"][0] == "versatile"
    assert OPGAVE_TIER["let"][0] == "lightweight"


def test_kun_modeller_der_kan_kalde_vaerktoejer():
    """Uden vaerktoejskald fabrikerer den. Det er hele grunden til at vi er her."""
    # `supported_endpoints` hoerer nu MED til at vaere brugbar: en model der
    # ikke kan naas via husets protokol er ikke et valg, uanset hvor god den
    # er. Foerste udgave af denne test udelod feltet — den kodede altsaa den
    # ufuldstaendige definition.
    _ep = ["/chat/completions"]
    assert _brugbar({"capabilities": {"type": "chat",
                                      "supports": {"tool_calls": True}},
                     "supported_endpoints": _ep,
                     "model_picker_enabled": True}) is True
    assert _brugbar({"capabilities": {"type": "chat",
                                      "supports": {"tool_calls": False}},
                     "supported_endpoints": _ep,
                     "model_picker_enabled": True}) is False


def test_type_laeses_paa_CAPABILITIES_ikke_paa_topniveau():
    """Foerste udgave laeste `m["type"]`, fik None, og kasserede alle 56
    modeller — og noedplanen skjulte det, fordi `fra_katalog=False` saa ud som
    «API'et svarede ikke»."""
    assert _brugbar({"capabilities": {"type": "chat",
                                      "supports": {"tool_calls": True}},
                     "supported_endpoints": ["/chat/completions"],
                     "model_picker_enabled": True, "type": None}) is True


def test_noedplanen_siger_HVORFOR(monkeypatch):
    """«Kunne ikke spoerge» og «spurgte, fik intet brugbart» er to forskellige
    fejl — den ene er netvaerket, den anden er os."""
    import core.services.copilot_catalogue as c

    monkeypatch.setattr(c, "hent_modeller", lambda **kw: [])
    r = c.rangeret("kode")
    assert r["fra_katalog"] is False
    assert "svarede ikke" in r["note"]

    monkeypatch.setattr(c, "hent_modeller",
                        lambda **kw: [{"id": "x", "capabilities": {}}])
    r2 = c.rangeret("kode")
    assert r2["fra_katalog"] is False
    assert "INGEN passerede filteret" in r2["note"]
    assert r2["hentede"] == 1


def test_noedplanen_er_ikke_tom():
    """En noedplan der ligner en maaling er vaerre end ingen liste — men en
    tom noedplan er ubrugelig."""
    import core.services.copilot_catalogue as c

    for opgave in OPGAVE_TIER:
        assert c._NOEDPLAN, "noedplanen er tom"
        assert rangeret(opgave, maks=2)["modeller"], opgave


# ── KOBLINGEN: kataloget skal faktisk BRUGES af explore ─────────────────
#
# Jarvis maalte den foerste udgave: to nye filer, nul sletninger, nul imports.
# Modulet svarede korrekt fra API'et — og INGEN kaldte det. Jeg sagde «koblet
# ind» om noget der ikke var det, i selve den commit der skulle koble det.
#
# «Virker det?» giver ja begge steder. Kun «hvem kalder det?» giver svaret.

def test_explore_bruger_kataloget():
    import inspect

    from core.tools import simple_tools_explore as e

    kilde = inspect.getsource(e._exec_explore)
    assert "copilot_catalogue" in kilde, (
        "explore kalder ikke kataloget — modulet har stadig nul forbrugere")
    assert "rangeret" in kilde


def test_poolen_bruges_ogsaa_paa_RUNDE_0():
    """Runde 0 koerte default-modellen helt uden egnetheds-port — og det var
    praecis dér nemotron kom ind og fabrikerede tre gange i traek."""
    import inspect

    from core.tools import simple_tools_explore as e

    kilde = inspect.getsource(e._exec_explore)
    i_pool = kilde.index("_ubrugte = ")
    i_runde = kilde.index("elif runde:")
    assert i_pool < i_runde, (
        "poolen konsulteres foerst paa runde 1 — runde 0 er stadig udaekket")


def test_opgaven_afgoer_hvilken_tier():
    """`kode` skal have den staerke model, `research` den alsidige."""
    import inspect

    from core.tools import simple_tools_explore as e

    kilde = inspect.getsource(e._exec_explore)
    assert '"opgave"' in kilde and '"research"' in kilde


def test_manglende_katalog_stopper_ikke_explore():
    """Kan kataloget ikke naas, falder vi tilbage til den gamle rotation frem
    for at stoppe. En kilde der er nede maa ikke tage vaerktoejet med sig."""
    import inspect

    from core.tools import simple_tools_explore as e

    kilde = inspect.getsource(e._exec_explore)
    i = kilde.index("copilot_catalogue")
    assert "except Exception" in kilde[i:i + 500]
    assert "elif runde:" in kilde, "den gamle rotation er fjernet i stedet for bevaret"


# ── LISTET ER IKKE KALDBAR — for tredje gang i dette hus ────────────────
#
# Jarvis' femte koersel. Kataloget hentede `supported_endpoints` og LAESTE det
# aldrig. MAALT 10/9-2026: 32 af 56 modeller kan ikke naas via
# `/chat/completions`, som er den protokol huset taler.
#
# Konsekvensen saa ud som et modelproblem: `research`-poolen var
# gpt-5.6-terra, grok-4.5, grok-4.6 (alle doede) og gemini-3.8-flash
# (levende) — og `_EXPLORE_MAKS_RUNDER = 3`. Rotationen koerte de tre doede og
# stoppede ÉT skridt foer den der virker. Hver fejl faldt tilbage til
# `copilot-free/gpt-4.1`, hvor faldbacken er TEKST-ONLY med vilje: husets
# bedste vaerktoejskalder fik «laes denne fil» uden vaerktoejer og gaettede.
#
# OG FELTET LOVER FOR MEGET. `gpt-5.4` staar med `/chat/completions` og svarer
# HTTP 400. Derfor to lag: feltet er en PAASTAND, historikken er en MAALING.

def test_modeller_uden_chat_completions_frasorteres():
    grund = {"capabilities": {"type": "chat", "supports": {"tool_calls": True}},
             "model_picker_enabled": True}
    assert _brugbar({**grund, "supported_endpoints": ["/chat/completions"]}) is True
    assert _brugbar({**grund, "supported_endpoints": ["/responses"]}) is False
    assert _brugbar({**grund, "supported_endpoints": []}) is False


def test_en_MAALT_uegnet_model_frasorteres_ogsaa():
    """Feltet er en paastand; historikken er en maaling. `gpt-5.4` staar som
    naabar og svarer 400 — saa historikken faar det sidste ord."""
    m = {"id": "gpt-5.4", "capabilities": {"type": "chat",
                                           "supports": {"tool_calls": True}},
         "model_picker_enabled": True,
         "supported_endpoints": ["/chat/completions"]}
    assert _brugbar(m) is True
    assert _brugbar(m, uegnet={"gpt-5.4"}) is False


def test_faa_forsoeg_doemmer_IKKE(isolated_runtime):
    """Samme disciplin som vaerktoejs-porten: to fejl er et spor, ikke en dom.
    Taersklen er lav (3) fordi fejlen HER er deterministisk — HTTP 400, ikke
    en timeout — men den er der."""
    from core.services.copilot_catalogue import _MIN_FORSOEG, _maalt_uegnet

    assert _MIN_FORSOEG >= 3
    assert _maalt_uegnet() == set(), "en tom historik doemte nogen"


def test_noedplanen_indeholder_kun_NAABARE_modeller():
    """Foerste udgave listede gpt-5.6-terra, grok-4.6 og gpt-5.4-mini — alle
    tre svarer kun paa /responses. Noedplanen ville have vaeret lige saa doed
    som den liste den skulle redde os fra."""
    import core.services.copilot_catalogue as c

    doede = {"gpt-5.6-terra", "grok-4.6", "grok-4.5", "gpt-5.4-mini",
             "gpt-5.6-luna", "gpt-5.3-codex", "gpt-5.5", "gpt-6-astra"}
    for tier, navne in c._NOEDPLAN.items():
        assert not (set(navne) & doede), f"{tier} indeholder doede modeller"


def test_poolen_MAALER_naabarhed_frem_for_at_liste_doede():
    """Foerste udgave havde en HAARDKODET liste. Jarvis fandt at jeg dermed
    havde erstattet to doede (claude-fable-*) med FIRE doede
    (claude-opus-4.7/4.8/4.8-fast/5) — alle med `/chat/completions` OG
    `tool_calls` i feltet, mens `claude-sonnet-5` fra samme familie virker."""
    import inspect

    import core.services.copilot_catalogue as c

    assert not hasattr(c, "_MAALT_DOEDE"), (
        "den haardkodede liste er tilbage — den raadner igen")
    assert "_naabar(" in inspect.getsource(c.rangeret)


def test_proeven_sender_IKKE_max_tokens():
    """Den parameter faar `gpt-5.4` til at svare 400. En proeve maa ikke selv
    frembringe den fejl den leder efter."""
    import ast
    import inspect

    import core.services.copilot_catalogue as c

    # Spoerg KODEN, ikke teksten: docstringen naevner `max_tokens` for at
    # forklare hvorfor den ikke bruges, og en ren strengsoegning ville falde
    # over sin egen forklaring. (Fjerde gang det moenster bider i dag.)
    traeet = ast.parse(inspect.getsource(c._naabar).lstrip())
    for knude in ast.walk(traeet):
        if isinstance(knude, ast.Constant) and knude.value == "max_tokens":
            raise AssertionError("proeven sender max_tokens — den frembringer "
                                 "selv den fejl den leder efter")


def test_en_NETVAERKSFEJL_doemmer_ikke_modellen(monkeypatch):
    """Kun et svar fra tjenesten betyder «kan ikke kaldes». En proeve der
    doemmer paa tavshed ville toemme poolen naar linjen vakler."""
    import core.services.copilot_catalogue as c

    c._naabar_cache.clear()
    monkeypatch.setattr(c, "_api_token", lambda: "x")
    monkeypatch.setattr(c.urllib.request, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("netvaerk")))
    assert c._naabar("en-model") is True
    # Det uafgjorte CACHES nu kort (ikke som en dom), saa et tavst blackhole
    # ikke koster 20 s pr. kandidat pr. opslag. Det maa bare aldrig i DB'en.
    assert c._naabar_i_db("en-model") is None


def test_et_HTTP_svar_ER_en_dom(monkeypatch):
    import core.services.copilot_catalogue as c

    c._naabar_cache.clear()
    monkeypatch.setattr(c, "_api_token", lambda: "x")

    def _fejl(*a, **k):
        raise c.urllib.error.HTTPError("u", 400, "Bad Request", {}, None)

    monkeypatch.setattr(c.urllib.request, "urlopen", _fejl)
    assert c._naabar("doed-model") is False


def test_proeven_cacher(monkeypatch):
    import core.services.copilot_catalogue as c

    c._naabar_cache.clear()
    kald = {"n": 0}
    monkeypatch.setattr(c, "_api_token", lambda: "x")

    class _Svar:
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def _ok(*a, **k):
        kald["n"] += 1
        return _Svar()

    monkeypatch.setattr(c.urllib.request, "urlopen", _ok)
    for _ in range(5):
        c._naabar("m")
    assert kald["n"] == 1, f"proeven koerte {kald['n']} gange trods cache"


# ── kadencen var et tal der ikke beskrev systemet ───────────────────────
#
# `_NAABAR_TTL = 86400` sagde ét doegn. Cachen var PROCES-LOKAL, og
# `jarvis-api` blev genstartet 56 GANGE i dag — cirka hvert attende minut i de
# travle timer. Den faktiske kadence var ~56 probninger, ikke én.
#
# Det er dagens moenster i en ny form: et tal der er rigtigt hvor det STAAR og
# forkert hvor det BRUGES. Samme figur som `supported_endpoints`. (Jarvis.)

def test_dommen_overlever_en_genstart(isolated_runtime):
    import core.services.copilot_catalogue as c

    c._naabar_cache.clear()
    c._gem_naabar("en-model", False)
    assert c._naabar_i_db("en-model") is False, (
        "dommen overlevede ikke — 56 genstarter koster stadig 56 probninger")
    c._gem_naabar("en-anden", True)
    assert c._naabar_i_db("en-anden") is True


def test_ukendt_model_har_ingen_holdbar_dom(isolated_runtime):
    import core.services.copilot_catalogue as c

    assert c._naabar_i_db("aldrig-proevet") is None, (
        "en umaalt model fik en dom ud af ingenting")


def test_uafgjort_caches_men_gemmes_IKKE(isolated_runtime, monkeypatch):
    """En netvaerksfejl er ikke en maaling af modellen, saa den maa ikke i
    DB'en. Men den skal caches kort — ellers koster et tavst blackhole 20 s
    pr. kandidat pr. opslag, igen og igen."""
    import core.services.copilot_catalogue as c

    c._naabar_cache.clear()
    monkeypatch.setattr(c, "_api_token", lambda: "x")
    monkeypatch.setattr(c.urllib.request, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("blackhole")))
    assert c._naabar("m") is True
    assert "m" in c._naabar_cache, "det uafgjorte blev ikke cachet — blackhole koster igen"
    assert c._naabar_i_db("m") is None, "en netvaerksfejl blev gemt som en dom"


def test_vaerktoejsevnen_er_MAALT_ikke_paastaaet():
    """Feltet `supports.tool_calls` er en paastand. `tool_calling_evidence`
    er en maaling over 935 koersler — og kataloget brugte den ikke, saa
    kaeden var «naabarhed maalt, vaerktoejsevne paastaaet»."""
    import inspect

    import core.services.copilot_catalogue as c

    assert "kan_kalde_vaerktoejer" in inspect.getsource(c._brugbar)
