"""Ægte ollama-cost med cache-felter (10/10-2026, Bjørn).

Baggrunden (målt 10/10-2026): hver eneste ollama-række i `costs` stod bogført
til `cost_usd=0.0` — 38M tokens til glm-5.2 med nul kroner. To fejl gav det:

1. `compute_cost_usd` spurgte `PRICING`, som KUN indeholder deepseek. Ollamas
   priser lå hele tiden i `OLLAMA_PRICING` og blev aldrig læst.
2. Ollama-adapteren læste `prompt_eval_count` men ikke
   `prompt_eval_cached_count`, så cache-hittet var 0 for alle kald — og prisen
   blev derfor beregnet som fuld input-pris.

Testsene her låser begge: prisen skal ramme Ollamas egen faktura, og
cache-splittet skal overleve fra svaret og ind i regnskabet.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.services.llm_pricing import (
    compute_cost_usd,
    er_myldretid,
    er_ollama_myldretid,
    ollama_input_pris_per_m,
)
from core.services.visible_model_ollama import _cache_split

# Fredag kl. 09:00 UTC — DeepSeeks myldretid, Ollamas off-peak.
_DS_PEAK = datetime(2026, 10, 9, 9, 0, tzinfo=UTC)
# Fredag kl. 14:00 UTC — Ollamas myldretid, DeepSeeks off-peak.
_OLL_PEAK = datetime(2026, 10, 9, 14, 0, tzinfo=UTC)
# Samme fredag kl. 09:00 UTC — off-peak for BEGGE. De fire faktura-målinger
# blev taget her, og det betyder noget: deepseek-v4.1-flash er den ENESTE
# ollama-model med en peak-pris, så dens måling ville være dobbelt i myldretiden.
_OLL_OFFPEAK = _DS_PEAK


# ── 1. Pris-beregneren kender ollama (var 0.0 for ALT) ────────────────────────


def test_ollama_kald_prissaettes_ikke_til_nul() -> None:
    """Kernen i fejlen: denne var 0.0, uanset tokens."""
    pris = compute_cost_usd("ollama", "glm-5.2:cloud", input_tokens=9017, output_tokens=20)
    assert pris > 0.0


@pytest.mark.parametrize(
    "model, kw, maalt",
    [
        # De fire tal er målt direkte på Ollamas balance-delta, ikke regnet.
        ("glm-5.3-flash:cloud", {"input_tokens": 7221, "output_tokens": 22}, 0.00110),
        ("glm-5.3-flash:cloud", {"input_tokens": 7221, "cache_hit_tokens": 7040,
                                 "cache_miss_tokens": 181, "output_tokens": 46}, 0.00027),
        ("glm-5.2:cloud", {"input_tokens": 9017, "output_tokens": 20}, 0.01271),
        ("deepseek-v4.1-flash:cloud", {"input_tokens": 34032, "output_tokens": 10}, 0.00512),
    ],
)
def test_prisen_rammer_ollamas_egen_faktura(model: str, kw: dict, maalt: float) -> None:
    """Inden for 5% af hvad balancen faktisk faldt. Ellers er tabellen forkert."""
    beregnet = compute_cost_usd("ollama", model, at=_OLL_OFFPEAK, **kw)
    assert beregnet == pytest.approx(maalt, rel=0.05)


def test_deepseek_i_ollama_myldretid_koster_dobbelt() -> None:
    """Den ene model hvor vinduet betyder noget — og grunden til at Ollama har
    sit eget vindue: prises den med DeepSeeks tider, er halvdelen af døgnet
    forkert."""
    kw = {"input_tokens": 10_000}
    off = compute_cost_usd("ollama", "deepseek-v4.1-flash:cloud", at=_OLL_OFFPEAK, **kw)
    peak = compute_cost_usd("ollama", "deepseek-v4.1-flash:cloud", at=_OLL_PEAK, **kw)
    assert peak == pytest.approx(off * 2)


def test_cache_satsen_er_billigere_end_input_satsen() -> None:
    """Uden dette ville cache-splittet være ligegyldigt at måle."""
    koldt = compute_cost_usd("ollama", "glm-5.2:cloud", input_tokens=10_000, at=_OLL_PEAK)
    cachet = compute_cost_usd("ollama", "glm-5.2:cloud", cache_hit_tokens=10_000,
                              cache_miss_tokens=0, at=_OLL_PEAK)
    assert cachet < koldt / 3


def test_ukendt_model_klemmes_til_nul() -> None:
    """Fail-safe: en model vi ikke kender prisen på må ikke opfinde en pris."""
    assert compute_cost_usd("ollama", "helt-ny-model:cloud", input_tokens=1000) == 0.0


def test_ollama_a2_prissaettes_ogsaa() -> None:
    """Michelles konto er en anden konto — men priserne er de samme."""
    assert compute_cost_usd("ollama-a2", "gemma4:31b-cloud", input_tokens=1000) > 0.0


def test_deepseek_lanen_er_uaendret() -> None:
    """Grenen må ikke røre den vej der virkede i forvejen."""
    assert compute_cost_usd("deepseek", "deepseek-v4-flash", input_tokens=1000) > 0.0
    assert compute_cost_usd("deepseek", "deepseek-v4-flash", input_tokens=1000) == pytest.approx(
        compute_cost_usd("deepseek", "deepseek-v4-flash", cache_miss_tokens=1000)
    )


def test_andre_providers_endnu_nul() -> None:
    """Kun deepseek og ollama er prissat. Resten må ikke få en gættet pris."""
    assert compute_cost_usd("nvidia-nim", "noget", input_tokens=1000) == 0.0


# ── 2. Ollamas myldre-vindue er et ANDET end DeepSeeks ───────────────────────


def test_de_to_myldre_vinduer_er_forskellige() -> None:
    """Blander man dem, priser man den forkerte halvdel af døgnet.

    Målt 10/10-2026: på 2.973 cloud-kald ville DeepSeeks vindue kalde 13% for
    myldretid mod Ollamas 22% — 262 kald forkert klassificeret.
    """
    assert er_myldretid(_DS_PEAK) is True
    assert er_ollama_myldretid(_DS_PEAK) is False
    assert er_myldretid(_OLL_PEAK) is False
    assert er_ollama_myldretid(_OLL_PEAK) is True


def test_ollama_weekend_er_altid_off_peak() -> None:
    loerdag = datetime(2026, 10, 10, 14, 0, tzinfo=UTC)
    assert er_ollama_myldretid(loerdag) is False


def test_ollama_ukendt_tid_priseres_som_myldretid() -> None:
    """Ukendt skal koste det dyre, ikke det billige — fejlretningen peger opad."""
    assert er_ollama_myldretid("ikke-et-tidspunkt") is True


def test_input_pris_enheden_er_pr_million() -> None:
    """glm-5.2 koster $1,40/M. Blev enheden læst som pr. token, ville loftet
    slippe alt igennem — den tavse enhedsfælde navnet er sat for at forhindre."""
    assert ollama_input_pris_per_m("glm-5.2:cloud", at=_OLL_PEAK) == pytest.approx(1.40)


def test_input_pris_ukendt_er_none_ikke_nul() -> None:
    """Et loft der læste «ukendt» som «gratis» ville slippe det det skulle fange."""
    assert ollama_input_pris_per_m("helt-ny-model:cloud") is None


# ── 3. Cache-splittet ud af svaret ───────────────────────────────────────────


def test_cache_split_laeser_ollamas_felt() -> None:
    """Det eksakte felt, målt i et rigtigt cloud-svar 10/10-2026."""
    hit, miss = _cache_split({"prompt_eval_cached_count": 7040}, 7221)
    assert (hit, miss) == (7040, 181)


def test_cache_split_uden_felt_er_alt_miss() -> None:
    """Lokale modeller og ældre daemons har ikke feltet → den dyre side."""
    assert _cache_split({}, 5000) == (0, 5000)


def test_cache_split_klemmer_hit_til_prompten() -> None:
    """Uoverensstemmelse mellem de to felter må ikke give negativ miss."""
    hit, miss = _cache_split({"prompt_eval_cached_count": 9999}, 100)
    assert (hit, miss) == (100, 0)
    assert miss >= 0


def test_cache_split_negativt_felt_bliver_nul() -> None:
    assert _cache_split({"prompt_eval_cached_count": -5}, 100) == (0, 100)
