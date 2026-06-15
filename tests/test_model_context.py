"""Per-model context-vinduer + model-bevidst beskeds-trimning."""
from __future__ import annotations

from core.services.model_context import (
    model_context_window, effective_context_limit, fit_messages_to_window,
)


def test_window_lookup_by_family():
    assert model_context_window("deepseek", "deepseek-v4-flash") == 1_000_000
    assert model_context_window("ollama", "glm-5.1:cloud") == 200_000
    assert model_context_window("github-copilot", "gpt-4o") == 128_000
    assert model_context_window("x", "ukendt-model-xyz") == 0


def test_effective_limit_is_first_ceiling():
    # GLM (200k) < compact (240k) → 200k; deepseek (1M) > compact → compact.
    assert effective_context_limit("ollama", "glm-5.1:cloud", 240_000) == 200_000
    assert effective_context_limit("deepseek", "flash", 200_000) == 200_000


def test_fit_unknown_window_is_noop():
    msgs = [{"role": "user", "content": "x" * 100}]
    out, dropped = fit_messages_to_window(msgs, provider="x", model="ukendt")
    assert dropped == 0 and out == msgs


def test_fit_trims_oldest_to_fit_glm():
    # Realistisk system (~50k) + historik der tilsammen sprænger GLM 200k.
    system = {"role": "system", "content": "S" * (50_000 * 4)}  # ~50k tokens
    history = [{"role": "user" if i % 2 == 0 else "assistant",
                "content": "h" * (20_000 * 4)} for i in range(8)]  # 8 × ~20k = 160k
    msgs = [system, *history]
    out, dropped = fit_messages_to_window(
        msgs, provider="ollama", model="glm-5.1:cloud",
        output_budget=16_000, tools_reserve=16_000, safety_margin=4_000,
    )
    assert dropped > 0
    assert out[0]["role"] == "system"            # system bevares
    assert len(out) >= 3                          # mindst system + 2 nyeste
    # Samlet skal nu være under budgettet (200k - 16k - 16k - 4k = 164k).
    total = sum(len(str(m["content"])) // 4 for m in out)
    assert total <= 164_000
