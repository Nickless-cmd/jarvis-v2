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
