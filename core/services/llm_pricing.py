"""Central LLM-pris-tabel + cost-beregner (WS2, 13. jul 2026).

Kilde: api-docs.deepseek.com (verificeret 13. jul). Priser i USD pr. 1M tokens.
DeepSeek V4 har INGEN off-peak-rabat. Legacy deepseek-chat/reasoner mapper til
v4-flash (label normaliseres i record_cost). Kun DeepSeek prises her (WS2-scope);
andre providers → 0.0 indtil WS8/Fase 2.
"""
from __future__ import annotations

_M = 1_000_000.0

# (provider, model) -> USD pr. token
PRICING: dict[tuple[str, str], dict[str, float]] = {
    ("deepseek", "deepseek-v4-flash"): {"cache_hit": 0.0028 / _M, "cache_miss": 0.14 / _M, "output": 0.28 / _M},
    ("deepseek", "deepseek-v4-pro"): {"cache_hit": 0.003625 / _M, "cache_miss": 0.435 / _M, "output": 0.87 / _M},
}

# legacy-aliaser → v4-flash-priser
_ALIAS = {"deepseek-chat": "deepseek-v4-flash", "deepseek-reasoner": "deepseek-v4-flash"}


def compute_cost_usd(
    provider: str,
    model: str,
    *,
    cache_hit_tokens: int = 0,
    cache_miss_tokens: int = 0,
    output_tokens: int = 0,
    input_tokens: int = 0,
) -> float:
    """Beregn cost_usd fra tokens × pris. Returnerer 0.0 for ukendte (provider, model).

    Cache-split ukendt (hit=miss=0) men input_tokens>0 → al input som cache_miss (konservativt).
    """
    key = (provider, _ALIAS.get(model, model))
    p = PRICING.get(key)
    if not p:
        return 0.0
    hit = int(cache_hit_tokens or 0)
    miss = int(cache_miss_tokens or 0)
    if hit == 0 and miss == 0 and int(input_tokens or 0) > 0:
        miss = int(input_tokens)
    return hit * p["cache_hit"] + miss * p["cache_miss"] + int(output_tokens or 0) * p["output"]
