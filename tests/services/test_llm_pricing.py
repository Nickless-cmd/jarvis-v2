"""Pris-tabellens absolutte tal — og hvorfor de alle bærer et tidspunkt.

Denne fil fastnaglede tidligere beløb som `0.42` uden at sige HVORNÅR kaldet
skete. Da myldretid kom til (14/9-2026, peak = 2× off-peak), ville de samme
assertions have skiftet resultat efter klokkeslæt: grønne om eftermiddagen,
røde kl. 02 UTC på en tirsdag. En test der afhænger af hvornår den køres,
melder ikke en fejl — den melder et tidspunkt.

`_OFF` og `_PEAK` er derfor faste. 14/9-2026 er en mandag.
"""
from datetime import datetime, timezone

from core.services.llm_pricing import PRICING, compute_cost_usd

_OFF = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)   # mandag, off-peak
_PEAK = datetime(2026, 9, 14, 2, 0, tzinfo=timezone.utc)   # mandag, myldretid


def test_flash_known_tokens():
    # 1M cache_miss + 1M output på flash, off-peak = 0.15 + 0.60 = 0.75
    c = compute_cost_usd("deepseek", "deepseek-v4-flash", at=_OFF,
                         cache_hit_tokens=0, cache_miss_tokens=1_000_000,
                         output_tokens=1_000_000)
    assert abs(c - 0.75) < 1e-9


def test_flash_known_tokens_i_myldretid():
    """Samme kald, dobbelt pris. Det var præcis den halvdel af døgnet den gamle
    tabel ikke kunne se."""
    c = compute_cost_usd("deepseek", "deepseek-v4-flash", at=_PEAK,
                         cache_hit_tokens=0, cache_miss_tokens=1_000_000,
                         output_tokens=1_000_000)
    assert abs(c - 1.50) < 1e-9


def test_flash_cache_hit_cheap():
    c = compute_cost_usd("deepseek", "deepseek-v4-flash", at=_OFF,
                         cache_hit_tokens=1_000_000, cache_miss_tokens=0,
                         output_tokens=0)
    assert abs(c - 0.003) < 1e-9


def test_pro_pricing():
    c = compute_cost_usd("deepseek", "deepseek-v4-pro", at=_OFF,
                         cache_hit_tokens=0, cache_miss_tokens=1_000_000,
                         output_tokens=1_000_000)
    assert abs(c - (0.66 + 1.98)) < 1e-9


def test_legacy_alias_uses_flash_price():
    c = compute_cost_usd("deepseek", "deepseek-chat", at=_OFF,
                         cache_hit_tokens=0, cache_miss_tokens=1_000_000,
                         output_tokens=0)
    assert abs(c - 0.15) < 1e-9  # mapper til flash


def test_unknown_cache_split_treats_input_as_miss():
    # begge cache-kolonner 0 men input_tokens>0 → al input som cache_miss (konservativt)
    c = compute_cost_usd("deepseek", "deepseek-v4-flash", at=_OFF,
                         cache_hit_tokens=0, cache_miss_tokens=0,
                         input_tokens=1_000_000, output_tokens=0)
    assert abs(c - 0.15) < 1e-9


def test_unknown_provider_returns_zero():
    assert compute_cost_usd("ollama", "local", at=_OFF,
                            cache_miss_tokens=1_000_000, output_tokens=1_000_000) == 0.0


def test_pricing_table_has_both_v4_models():
    assert ("deepseek", "deepseek-v4-flash") in PRICING
    assert ("deepseek", "deepseek-v4-pro") in PRICING
