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
    assert _brugbar({"capabilities": {"type": "chat",
                                      "supports": {"tool_calls": True}},
                     "model_picker_enabled": True}) is True
    assert _brugbar({"capabilities": {"type": "chat",
                                      "supports": {"tool_calls": False}},
                     "model_picker_enabled": True}) is False


def test_type_laeses_paa_CAPABILITIES_ikke_paa_topniveau():
    """Foerste udgave laeste `m["type"]`, fik None, og kasserede alle 56
    modeller — og noedplanen skjulte det, fordi `fra_katalog=False` saa ud som
    «API'et svarede ikke»."""
    assert _brugbar({"capabilities": {"type": "chat",
                                      "supports": {"tool_calls": True}},
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
