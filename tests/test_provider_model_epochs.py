"""Hvilken model SVAREDE — ikke hvilken vi bad om.

Opgave 2 i world-self-model-truth. En udbyder kan svare med en anden model end
den man bad om: et alias der peger et nyt sted, en stille opgradering, en
faldback. Beder man om `deepseek-chat` og faar `deepseek-flash`, er alt hvad
runtimen «ved» om sin egen model foraeldet uden at nogen har aendret noget.

EPOKER, IKKE EN TAELLER. Den samme observation gentaget hundrede gange er ét
faktum om verden. En AENDRING er derimod en begivenhed — en ny epoke — og det
er skiftet der er interessant, ikke maengden.

BEVIS-BUNDET, som resten af grenen: er der ingen model i svaret, er der intet
observeret, og saa opstaar der ingen epoke. Fravaer er ikke en observation.
"""
from __future__ import annotations

from core.services.provider_model_epochs import (
    current_model_epoch,
    record_model_observation,
)


def test_foerste_observation_aabner_en_epoke(isolated_runtime):
    e = record_model_observation(provider="deepseek", requested_model="deepseek-chat",
                                 observed_model="deepseek-chat")
    assert e["epoch_id"]
    assert e["observed_model"] == "deepseek-chat"
    assert e["observation_count"] == 1
    assert current_model_epoch(provider="deepseek",
                               requested_model="deepseek-chat")["epoch_id"] == e["epoch_id"]


def test_gentagne_ens_observationer_er_SAMME_epoke(isolated_runtime):
    """Hundrede ens observationer er ét faktum, ikke hundrede."""
    foerste = record_model_observation(provider="p", requested_model="m", observed_model="m")
    for _ in range(4):
        senere = record_model_observation(provider="p", requested_model="m", observed_model="m")
    assert senere["epoch_id"] == foerste["epoch_id"]
    assert senere["observation_count"] == 5


def test_en_AENDRING_aabner_en_ny_epoke(isolated_runtime):
    """Det er skiftet der er begivenheden."""
    a = record_model_observation(provider="deepseek", requested_model="deepseek-chat",
                                 observed_model="deepseek-chat")
    b = record_model_observation(provider="deepseek", requested_model="deepseek-chat",
                                 observed_model="deepseek-flash")
    assert b["epoch_id"] != a["epoch_id"]
    assert b["observation_count"] == 1
    assert b["previous_observed_model"] == "deepseek-chat"
    assert current_model_epoch(provider="deepseek",
                               requested_model="deepseek-chat")["observed_model"] == "deepseek-flash"


def test_alias_uoverensstemmelse_registreres_som_saadan(isolated_runtime):
    """Beder man om ét og faar et andet, er det vaerd at kunne se — det er
    grunden til at overhovedet maale."""
    e = record_model_observation(provider="p", requested_model="alias-navn",
                                 observed_model="det-rigtige-navn")
    assert e["mismatch"] is True
    ens = record_model_observation(provider="p", requested_model="x", observed_model="x")
    assert ens["mismatch"] is False


def test_intet_observeret_giver_INGEN_epoke(isolated_runtime):
    """Fravaer er ikke en observation. Et svar uden model-metadata betyder at
    vi ikke ved det — ikke at modellen hedder tom streng."""
    assert record_model_observation(provider="p", requested_model="m",
                                    observed_model="") is None
    assert current_model_epoch(provider="p", requested_model="m") is None


def test_epoker_holdes_adskilt_pr_udbyder_og_oenske(isolated_runtime):
    a = record_model_observation(provider="p1", requested_model="m", observed_model="x")
    b = record_model_observation(provider="p2", requested_model="m", observed_model="x")
    c = record_model_observation(provider="p1", requested_model="anden", observed_model="x")
    assert len({a["epoch_id"], b["epoch_id"], c["epoch_id"]}) == 3


def test_ukendt_kombination_giver_None_ikke_en_tom_epoke(isolated_runtime):
    assert current_model_epoch(provider="findes", requested_model="ikke") is None


# ── koblingen: bliver observationen faktisk bogfoert? ───────────────────

def test_adapteren_bogfoerer_observationen():
    """Et lager over model-epoker som INGEN fylder ville vaere endnu et lag
    ingen bruger. Testen laeser kaldstedet, fordi adapteren kraever en levende
    udbyder for at koere igennem."""
    import inspect

    from core.services import visible_model_adapters as a

    kilde = inspect.getsource(a)
    assert "record_model_observation(" in kilde, (
        "adapteren bogfoerer aldrig hvad udbyderen svarede med")
    assert "observed_model=str(ev.get(\"observed_model\")" in kilde


def test_stroemmen_opsamler_modelnavnet_foer_choices_tjekket():
    """Modelnavnet staar paa selve event'et, ogsaa paa usage-only-chunks. Laeses
    det efter `if not choices: continue`, taber en stroem hvis sidste chunk kun
    baerer usage sit modelnavn."""
    import inspect

    from core.services import cheap_provider_runtime_streaming as st

    kilde = inspect.getsource(st)
    i_model = kilde.index('_m = event.get("model")')
    i_choices = kilde.index('choices = event.get("choices")')
    assert i_model < i_choices, (
        "modelnavnet laeses efter choices-tjekket — usage-only-chunks taber det")


# ── epoken paa FALDBACK-SOEMMEN (10/9-2026) ─────────────────────────────
#
# `provider_model_epochs` blev bygget for at svare paa «svarede den model jeg
# bad om?» — og var ikke koblet paa den ene soem hvor svaret oftest er nej.
#
# Da explore bad om `copilot-premium/grok-4.6` og fik `copilot-free/gpt-4.1`,
# blev byttet aldrig registreret: `agent_runs` sagde det ene, cost-ledgeren
# det andet, og INGEN tabel sagde at de var uenige. Jarvis fandt det ved at
# holde de to tabeller op mod hinanden.
#
# Byttet er ikke en regnskabsdetalje. Faldbacken er TEKST-ONLY med vilje, saa
# den fjerner ogsaa vaerktoejerne: en agent der skulle laese en fil faar en
# model der kun kan gaette. Det er forskellen paa et svar og et gaet.

def test_faldback_soemmen_bogfoerer_hvem_der_svarede():
    import inspect

    from core.services import non_visible_lane_execution as x

    kilde = inspect.getsource(x.execute_with_role_or_fallback)
    i_fb = kilde.index("execute_cheap_lane_via_pool(message=_prompt_for_estimate,\n"
                       "                                          skip_providers=skip")
    efter = kilde[i_fb:]
    assert "record_model_observation(" in efter, (
        "faldbacken bogfoerer stadig ikke hvem der svarede i stedet")
    assert "requested_model=primary_model" in efter


def test_ogsaa_den_GODE_vej_bogfoeres():
    """Et instrument der kun registrerer fejl, kan ikke sige at noget er
    raskt: «vi har aldrig set den svare» ville ikke kunne skelnes fra «den
    svarer altid som sig selv»."""
    import inspect

    from core.services import non_visible_lane_execution as x

    kilde = inspect.getsource(x.execute_with_role_or_fallback)
    assert kilde.count("record_model_observation(") == 2, (
        "kun én af de to grene bogfoerer")


def test_bogfoeringen_kan_ikke_vaelte_kaldet():
    import inspect

    from core.services import non_visible_lane_execution as x

    kilde = inspect.getsource(x.execute_with_role_or_fallback)
    for i in [i for i in range(len(kilde))
              if kilde.startswith("record_model_observation(", i)]:
        assert "except Exception" in kilde[i:i + 700], (
            "en observation kan vaelte det den observerer")


def test_observeret_navn_roeber_udbyder_skiftet():
    """Faldbacken skifter ofte OGSAA udbyder (copilot-premium ->
    copilot-free), og epoke-tabellen har kun ét provider-felt. Uden dette
    ville raekken sige «grok-4.6 -> gpt-4.1» uden at roebe at huset ogsaa
    skiftede leverandoer — og saa ligner et LEVERANDOER-skifte et
    model-skifte."""
    from core.services.non_visible_lane_execution import _observeret_navn as f

    assert f({"provider": "copilot-premium", "model": "kimi-k3"},
             "copilot-premium") == "kimi-k3"
    assert f({"provider": "copilot-free", "model": "gpt-4.1"},
             "copilot-premium") == "copilot-free/gpt-4.1"
    assert f({}, "copilot-premium") == "", (
        "et tomt svar maa ikke blive til et modelnavn")


def test_tomt_observeret_navn_giver_INGEN_epoke(isolated_runtime):
    """Fravaer er ikke en observation — ogsaa naar faldbacken svarede uden at
    sige hvem."""
    assert record_model_observation(provider="p", requested_model="m",
                                    observed_model="") is None
