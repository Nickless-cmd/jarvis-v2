from core.services.llm_pricing import compute_cost_usd, PRICING


def test_flash_known_tokens():
    # 1M cache_miss + 1M output på flash = 0.14 + 0.28 = 0.42
    c = compute_cost_usd("deepseek", "deepseek-v4-flash",
                         cache_hit_tokens=0, cache_miss_tokens=1_000_000, output_tokens=1_000_000)
    assert abs(c - 0.42) < 1e-9


def test_flash_cache_hit_cheap():
    c = compute_cost_usd("deepseek", "deepseek-v4-flash",
                         cache_hit_tokens=1_000_000, cache_miss_tokens=0, output_tokens=0)
    assert abs(c - 0.0028) < 1e-9


def test_pro_pricing():
    c = compute_cost_usd("deepseek", "deepseek-v4-pro",
                         cache_hit_tokens=0, cache_miss_tokens=1_000_000, output_tokens=1_000_000)
    assert abs(c - (0.435 + 0.87)) < 1e-9


def test_legacy_alias_uses_flash_price():
    c = compute_cost_usd("deepseek", "deepseek-chat",
                         cache_hit_tokens=0, cache_miss_tokens=1_000_000, output_tokens=0)
    assert abs(c - 0.14) < 1e-9  # mapper til flash


def test_unknown_cache_split_treats_input_as_miss():
    # begge cache-kolonner 0 men input_tokens>0 → al input som cache_miss (konservativt)
    c = compute_cost_usd("deepseek", "deepseek-v4-flash",
                         cache_hit_tokens=0, cache_miss_tokens=0, input_tokens=1_000_000, output_tokens=0)
    assert abs(c - 0.14) < 1e-9


def test_unknown_provider_returns_zero():
    assert compute_cost_usd("ollama", "local", cache_miss_tokens=1_000_000, output_tokens=1_000_000) == 0.0


def test_pricing_table_has_both_v4_models():
    assert ("deepseek", "deepseek-v4-flash") in PRICING
    assert ("deepseek", "deepseek-v4-pro") in PRICING
