"""`deepseek-v4-flash` er et legacy-navn — og huset kendte det seks steder.

Verificeret mod API'en 1/10-2026 ved at sende et kald med hvert navn og læse
`model` i svaret: `deepseek-v4-flash` og `deepseek-chat` svarer begge som
`deepseek-flash`, og `GET /models` udstiller kun `deepseek-flash` og
`deepseek-v4-pro`.

Navnet lå i SEKS medlemskabstests og TO pristabeller, og de var allerede drevet
fra hinanden: `vision_backend` brugte det kanoniske navn, mens thinking-testen
og begge pristabeller kun kendte det gamle. Et skift af `visible_model_name`
ville derfor have slået thinking fra OG sendt prisen til nul — hver for sig og i
stilhed. Testene her pinner at BEGGE navne opfører sig ens.
"""
from __future__ import annotations

import pytest

from core.services.deepseek_modelnavne import (
    KANONISK_FLASH,
    er_flash,
    er_thinking_model,
)
from core.services.llm_pricing import compute_cost_usd

BEGGE = ("deepseek-flash", "deepseek-v4-flash")


# ── Thinking-testen ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("model", BEGGE + ("deepseek-v4-pro", "deepseek-reasoner"))
def test_thinking_modeller_genkendes(model):
    assert er_thinking_model(model, provider="deepseek") is True


def test_en_anden_udbyder_med_samme_navn_er_ikke_deepseeks(model="deepseek-flash"):
    """Kaldsstederne tjekker provider i forvejen — et navn alene siger ikke hvem
    der svarer."""
    assert er_thinking_model(model, provider="ollama") is False
    assert er_thinking_model(model, provider="") is False


@pytest.mark.parametrize("model", ["glm-5.2", "claude-sonnet-5", "", "deepseek-flash-x"])
def test_fremmede_navne_er_ikke_thinking_modeller(model):
    assert er_thinking_model(model, provider="deepseek") is False


# ── Pristabel 1: llm_pricing ────────────────────────────────────────────────

def test_begge_navne_prises_ENS_og_over_nul():
    """Kernen. Stod kun det gamle navn i tabellen, ville et skift af
    konfigurationen prise hvert kald til 0,0 — og kaldene ville forsvinde ud af
    regnskabet uden en eneste fejl."""
    priser = {
        m: compute_cost_usd("deepseek", m, cache_hit_tokens=1_000_000,
                            cache_miss_tokens=100_000, output_tokens=10_000,
                            at="2026-10-01T12:00:00+00:00")
        for m in BEGGE
    }
    assert priser["deepseek-flash"] > 0.0, "det kanoniske navn prises til nul"
    assert priser["deepseek-flash"] == priser["deepseek-v4-flash"]


def test_et_ukendt_navn_prises_stadig_til_nul():
    """Aliaset maa ikke blive en dør for hvad som helst."""
    assert compute_cost_usd("deepseek", "deepseek-opfundet",
                            cache_miss_tokens=1_000_000) == 0.0


# ── Pristabel 2: cheap_provider_runtime_adapters ────────────────────────────

@pytest.mark.parametrize("model", BEGGE)
def test_den_anden_pristabel_kender_begge_navne(model):
    """Der er TO pristabeller i huset. Den her returnerede `None` for alt andet
    end det gamle navn, og `None` bliver til pris 0 længere nede."""
    from core.services.cheap_provider_runtime_adapters import _deepseek_price_table
    t = _deepseek_price_table(model)
    assert t is not None, f"{model} gav None → prisen ville blive nul"
    assert _deepseek_price_table("deepseek-flash") == _deepseek_price_table("deepseek-v4-flash")


def test_pro_er_ikke_flash():
    from core.services.cheap_provider_runtime_adapters import _deepseek_price_table
    assert er_flash("deepseek-v4-pro") is False
    assert _deepseek_price_table("deepseek-v4-pro") is not None
    assert _deepseek_price_table("deepseek-v4-pro") != _deepseek_price_table(KANONISK_FLASH)


# ── Synet, som allerede kendte det kanoniske navn ───────────────────────────

@pytest.mark.parametrize("model", BEGGE + ("deepseek-v4-flash-vision-exp",))
def test_synet_genkender_alle_flash_navne(model):
    from core.services.vision_backend import model_can_see
    assert model_can_see(model) is True
