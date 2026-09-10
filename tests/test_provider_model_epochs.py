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
