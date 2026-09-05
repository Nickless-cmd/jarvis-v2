"""Valg af vision-model (2026-09-05).

Bjørns argument: `deepseek-v4-flash-vision-exp` er SAMME model som den der
svarer ham, bare med syn, og prisen er den samme med og uden. Så valget skal
være hans — men et vision-kald må ikke blive endnu et kald hovedbogen ikke
kender til.
"""
from __future__ import annotations

import pytest

from core.services import vision_backend as VB


@pytest.fixture
def no_config(monkeypatch):
    monkeypatch.setattr("core.runtime.secrets.read_runtime_key", lambda *_a, **_k: None)


@pytest.mark.parametrize("model,expected", [
    ("gemma4:31b-cloud", "ollama"),
    ("qwen2.5vl:3b", "ollama"),
    ("deepseek-v4-flash:cloud", "ollama"),      # tag → ollama, ikke API'et
    ("deepseek-v4-flash-vision-exp", "deepseek"),
    ("", "ollama"),
])
def test_the_model_name_decides_when_nothing_is_configured(no_config, model, expected):
    assert VB.resolve_vision_provider(model) == expected


@pytest.mark.parametrize("model,expected", [
    ("gemma4:31b-cloud", True),      # familien er multimodal — navnet alene betyder syn
    ("gemma4:7b", True),
    ("deepseek-v4-flash-vision-exp", True),
    ("qwen2.5vl:3b", True),
    ("glm-5.3-flash:cloud", False),  # den blinde variant
    ("gemma3:27b", False),           # kun gemma4-familien
    ("", False),
])
def test_which_models_can_see(model, expected):
    assert VB.model_can_see(model) == expected


def test_an_explicit_choice_wins(monkeypatch):
    monkeypatch.setattr("core.runtime.secrets.read_runtime_key",
                        lambda key, *a, **k: "deepseek" if key == "vision_provider" else None)
    assert VB.resolve_vision_provider("gemma4:31b-cloud") == "deepseek"
    monkeypatch.setattr("core.runtime.secrets.read_runtime_key",
                        lambda key, *a, **k: "ollama" if key == "vision_provider" else None)
    assert VB.resolve_vision_provider("deepseek-v4-flash-vision-exp") == "ollama"


def test_nonsense_config_falls_back_to_the_name(monkeypatch):
    monkeypatch.setattr("core.runtime.secrets.read_runtime_key",
                        lambda key, *a, **k: "banan" if key == "vision_provider" else None)
    assert VB.resolve_vision_provider("deepseek-v4-flash-vision-exp") == "deepseek"


def test_ollama_is_used_for_ollama_models(no_config, monkeypatch):
    seen = {}
    monkeypatch.setattr("core.services.visual_memory._describe_via_ollama",
                        lambda b64, *, model, prompt=None: seen.update(
                            model=model, prompt=prompt) or "en roed cirkel")
    out = VB.describe(image_b64="Zm9v", model="gemma4:31b-cloud", prompt="hvad ser du?")
    assert out == {"text": "en roed cirkel", "provider": "ollama", "model": "gemma4:31b-cloud"}
    assert seen["prompt"] == "hvad ser du?"


def test_the_deepseek_call_books_its_own_cost(no_config, monkeypatch):
    rows: list[dict] = []
    monkeypatch.setattr("core.costing.ledger.record_cost", lambda **kw: rows.append(kw))
    monkeypatch.setattr("core.runtime.secrets.read_runtime_key",
                        lambda key, *a, **k: "k" if key == "deepseek_api_key" else None)

    class _Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return None
        def read(self):
            return (b'{"choices":[{"message":{"content":"backup er roed"}}],'
                    b'"usage":{"prompt_tokens":1200,"completion_tokens":40,'
                    b'"prompt_cache_hit_tokens":0,"prompt_cache_miss_tokens":1200}}')

    monkeypatch.setattr(VB.urllib.request, "urlopen", lambda req, timeout=None: _Resp())
    out = VB.describe(image_b64="Zm9v", model="deepseek-v4-flash-vision-exp",
                      prompt="hvad fejlede?", run_id="visible-1")
    assert out["text"] == "backup er roed" and out["provider"] == "deepseek"
    assert len(rows) == 1
    row = rows[0]
    assert row["lane"] == "vision" and row["run_id"] == "visible-1"
    assert row["input_tokens"] == 1200 and row["cost_usd"] > 0


def test_vision_costs_the_same_as_the_model_without_sight():
    """Bjoerns praemis, gjort til en paastand koden holder paa."""
    from core.services.llm_pricing import compute_cost_usd
    blind = compute_cost_usd("deepseek", "deepseek-v4-flash",
                             cache_miss_tokens=1_000_000, output_tokens=1000)
    seeing = compute_cost_usd("deepseek", "deepseek-v4-flash-vision-exp",
                              cache_miss_tokens=1_000_000, output_tokens=1000)
    assert seeing == blind > 0, "vision-varianten maa ikke prises til 0 og forsvinde"


def test_a_missing_key_fails_loudly(no_config):
    with pytest.raises(RuntimeError, match="deepseek_api_key"):
        VB.describe_via_deepseek("Zm9v", model="deepseek-v4-flash-vision-exp", prompt="?")


def test_the_surface_says_whether_it_costs_money(no_config, monkeypatch):
    monkeypatch.setattr("core.services.attachment_service._vision_model",
                        lambda: "deepseek-v4-flash-vision-exp")
    s = VB.build_vision_backend_surface()
    assert s["provider"] == "deepseek" and s["paid"] is True
    monkeypatch.setattr("core.services.attachment_service._vision_model",
                        lambda: "gemma4:31b-cloud")
    assert VB.build_vision_backend_surface()["paid"] is False
