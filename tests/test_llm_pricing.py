"""Pris-tabellen — pengeregningen bag hvert kald.

Den vigtigste egenskab er ikke at tallene er præcise, men at en model vi
FAKTISK bruger aldrig prises til 0,0 og dermed forsvinder ud af regnskabet.
Det skete for de agentiske runder indtil 5/9, og vi opdagede det først da
saldoen var faldet $12 mod en hovedbog der sagde $2,28.
"""
from __future__ import annotations

import pytest

from core.services.llm_pricing import PRICING, compute_cost_usd

_MODELS_IN_USE = [
    "deepseek-v4-flash",
    "deepseek-v4-pro",
    "deepseek-v4-flash-vision-exp",
    "deepseek-chat",       # legacy-alias
    "deepseek-reasoner",   # legacy-alias
]


@pytest.mark.parametrize("model", _MODELS_IN_USE)
def test_no_model_we_use_is_priced_at_zero(model):
    assert compute_cost_usd("deepseek", model, cache_miss_tokens=1_000_000) > 0


def test_sight_costs_the_same_as_no_sight():
    """Bjørns præmis 5/9, gjort til noget koden holder på."""
    kw = {"cache_miss_tokens": 1_000_000, "output_tokens": 1_000, "cache_hit_tokens": 5_000}
    assert (compute_cost_usd("deepseek", "deepseek-v4-flash-vision-exp", **kw)
            == compute_cost_usd("deepseek", "deepseek-v4-flash", **kw))


def test_a_cache_hit_is_far_cheaper_than_a_miss():
    """Hele grunden til at vi måler hit og miss hver for sig."""
    hit = compute_cost_usd("deepseek", "deepseek-v4-flash", cache_hit_tokens=1_000_000)
    miss = compute_cost_usd("deepseek", "deepseek-v4-flash", cache_miss_tokens=1_000_000)
    assert miss > hit * 10


def test_unknown_cache_split_is_charged_as_miss():
    """Konservativt: ved vi ikke om det var cachet, antager vi det dyre."""
    a = compute_cost_usd("deepseek", "deepseek-v4-flash", input_tokens=1_000_000)
    b = compute_cost_usd("deepseek", "deepseek-v4-flash", cache_miss_tokens=1_000_000)
    assert a == b


def test_an_unknown_provider_is_free_not_guessed():
    assert compute_cost_usd("ollama", "gemma4:31b-cloud", cache_miss_tokens=1_000_000) == 0.0
    assert compute_cost_usd("deepseek", "en-model-vi-ikke-kender", input_tokens=10_000) == 0.0


def test_zero_tokens_costs_nothing():
    assert compute_cost_usd("deepseek", "deepseek-v4-flash") == 0.0


def test_the_table_only_prices_what_it_can_source():
    """Tabellens egen docstring siger at kun DeepSeek er priset. Sniger der sig
    en gratis-provider ind med en pris, er et tal blevet gættet."""
    assert {p for p, _m in PRICING} == {"deepseek"}


# ─────────────────────────────────────────────────────────────────────────
# Myldretid (14/9-2026)
#
# Tabellens docstring sagde «DeepSeek V4 har INGEN off-peak-rabat» og var
# verificeret 13. juli. Efterprøvet mod api-docs.deepseek.com 14/9: der ER en
# rabat, peak er præcis det dobbelte af off-peak, og HVER eneste linje i
# tabellen var forkert. Værst: output på flash stod til 0,28 mod 0,60/1,20, og
# pro's cache-hit til 0,003625 mod 0,022 — en faktor 6.
#
# Det er tredje gang hovedbogen har underrapporteret. Filens egen docstring
# fortæller om den forrige: saldoen faldt $12 mod en hovedbog der sagde $2,28.
# Fejlretningen er derfor ikke kun nye tal, men at tiden bliver et INPUT —
# en pris uden et tidspunkt kan ikke være rigtig mere end halvdelen af tiden.
# ─────────────────────────────────────────────────────────────────────────

from datetime import datetime, timezone  # noqa: E402

from core.services import llm_pricing as lp  # noqa: E402


def _t(dag: int, time_: int) -> datetime:
    """2026-09-dag kl. time_ UTC. 14/9-2026 er en mandag."""
    return datetime(2026, 9, dag, time_, 0, tzinfo=timezone.utc)


def test_myldretid_koster_det_DOBBELTE():
    """Kilden siger det med rene ord: off-peak er præcis det halve af peak."""
    kw = {"cache_miss_tokens": 1_000_000, "output_tokens": 1_000_000}
    billig = compute_cost_usd("deepseek", "deepseek-v4-flash", at=_t(14, 12), **kw)
    dyr = compute_cost_usd("deepseek", "deepseek-v4-flash", at=_t(14, 2), **kw)
    assert abs(dyr - billig * 2) < 1e-12


def test_de_to_myldre_vinduer_er_BEGGE_med():
    """01-04 OG 06-10. Et vindue der mangler er penge der forsvinder tavst —
    og det halve af myldretiden ligger i det andet vindue."""
    for time_ in (1, 2, 3, 6, 7, 8, 9):
        assert lp.er_myldretid(_t(14, time_)) is True, f"kl. {time_} skulle vaere peak"
    for time_ in (0, 4, 5, 10, 11, 23):
        assert lp.er_myldretid(_t(14, time_)) is False, f"kl. {time_} skulle vaere off-peak"


def test_weekend_er_ALDRIG_myldretid():
    """19/9 er en lørdag, 20/9 en søndag. Kilden: «Monday through Friday»."""
    for dag in (19, 20):
        for time_ in (1, 2, 3, 6, 7, 8, 9):
            assert lp.er_myldretid(_t(dag, time_)) is False


def test_fredag_ER_myldretid_men_ikke_loerdag():
    """Grænsen mellem uge og weekend er præcis der en fejl-en-af ville gemme
    sig, og fredagens myldretid er en femtedel af al myldretid."""
    assert lp.er_myldretid(_t(18, 2)) is True    # fredag
    assert lp.er_myldretid(_t(19, 2)) is False   # loerdag


def test_UKENDT_tidspunkt_prises_som_MYLDRETID():
    """Samme retning som «ukendt cache-split → miss» ovenfor: når vi ikke ved
    det, gætter vi den DYRE vej.

    Underrapportering er den fejl der er sket tre gange, fordi den er tavs —
    en for høj regning bliver opdaget og spurgt om, en for lav gør ikke.
    """
    kw = {"cache_miss_tokens": 1_000_000}
    ukendt = compute_cost_usd("deepseek", "deepseek-v4-flash", at="ikke en dato", **kw)
    peak = compute_cost_usd("deepseek", "deepseek-v4-flash", at=_t(14, 2), **kw)
    assert ukendt == peak


def test_et_NAIVT_tidsstempel_laeses_som_UTC():
    """Hovedbogens `created_at` er UTC uden tidszone. Blev det læst som lokal
    tid, ville hele myldre-vinduet rykke to timer og prise de forkerte kald —
    huset er faldet i den fælde før (DB=UTC, journal=lokal).

    Forbehold: på en maskine der KØRER UTC er de to adfærd identiske, og så kan
    ingen test skelne dem. Den her fanger fejlen fordi runtime'en står i
    København. Det er en ægte begrænsning, ikke et hul der kan lukkes.
    """
    assert lp.er_myldretid(datetime(2026, 9, 14, 2, 0)) is True
    assert lp.er_myldretid(datetime(2026, 9, 14, 12, 0)) is False


def test_en_ISO_streng_fra_hovedbogen_virker():
    """`compute_cost_usd` kaldes ved genberegning direkte på en DB-række."""
    assert lp.er_myldretid("2026-09-14T02:30:00+00:00") is True
    assert lp.er_myldretid("2026-09-14 02:30:00") is True
    assert lp.er_myldretid("2026-09-14T12:30:00Z") is False


def test_priserne_matcher_KILDEN():
    """De ni tal fra api-docs.deepseek.com, efterprøvet 14/9-2026. Står de her,
    kan næste læser se HVAD der blev verificeret og ikke kun HVORNÅR."""
    flash = PRICING[("deepseek", "deepseek-v4-flash")]
    assert flash["cache_hit"] == (0.003 / 1_000_000, 0.006 / 1_000_000)
    assert flash["cache_miss"] == (0.15 / 1_000_000, 0.30 / 1_000_000)
    assert flash["output"] == (0.60 / 1_000_000, 1.20 / 1_000_000)
    pro = PRICING[("deepseek", "deepseek-v4-pro")]
    assert pro["cache_hit"] == (0.022 / 1_000_000, 0.044 / 1_000_000)
    assert pro["cache_miss"] == (0.66 / 1_000_000, 1.32 / 1_000_000)
    assert pro["output"] == (1.98 / 1_000_000, 3.96 / 1_000_000)


def test_output_er_DYRERE_end_input_miss():
    """Den gamle tabel havde output til 0,28 mod miss 0,14 — halvt så dyrt som
    sandheden. Forholdet er en egenskab ved modellen, ikke et tal at huske."""
    for model in ("deepseek-v4-flash", "deepseek-v4-pro"):
        p = PRICING[("deepseek", model)]
        assert p["output"][0] > p["cache_miss"][0]


def test_tabellen_siger_HVORNAAR_den_er_efterproevet():
    """Den forrige tabel var 63 dage gammel og sagde det ikke noget sted en
    maskine kunne læse — kun i en docstring ingen kiggede på."""
    assert lp.VERIFICERET == "2026-09-14"
