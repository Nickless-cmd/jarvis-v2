# tests/services/test_relevance_deepseek_model.py
from core.services import prompt_relevance_backend as prb


def test_deepseek_relevance_uses_v4flash_and_disables_thinking(monkeypatch):
    captured = {}

    def _fake_exec(**kwargs):
        captured["model"] = kwargs.get("model")
        captured["extra_body"] = kwargs.get("extra_body")
        return {"text": "{}"}

    import core.services.cheap_provider_runtime as cpr
    monkeypatch.setattr(cpr, "_execute_openai_compatible_chat", _fake_exec)

    call = prb._call_openai_compat_relevance(
        provider="deepseek",
        prompt="rank these",
        model="deepseek-chat",
        timeout=6,
    )

    assert captured["model"] == "deepseek-v4-flash"
    assert captured["extra_body"] == {"thinking": {"type": "disabled"}}
    # The BoundedLLMCall should also carry the honest label.
    assert call.model == "deepseek-v4-flash"


def test_deepseek_relevance_writes_costs_row(monkeypatch):
    """A successful deepseek relevance call must log exactly one costs row
    with the real token counts threaded from the result dict."""
    recorded = []

    def _fake_exec(**kwargs):
        return {
            "text": "{}",
            "input_tokens": 123,
            "output_tokens": 7,
            "cache_hit_tokens": 100,
            "cache_miss_tokens": 23,
        }

    def _fake_record_cost(**kwargs):
        recorded.append(kwargs)

    import core.services.cheap_provider_runtime as cpr
    import core.costing.ledger as ledger
    monkeypatch.setattr(cpr, "_execute_openai_compatible_chat", _fake_exec)
    monkeypatch.setattr(ledger, "record_cost", _fake_record_cost)

    call = prb._call_openai_compat_relevance(
        provider="deepseek",
        prompt="rank these",
        model="deepseek-chat",
        timeout=6,
    )

    assert call.success is True
    assert len(recorded) == 1
    row = recorded[0]
    assert row["lane"] == "relevance"
    assert row["provider"] == "deepseek"
    assert row["model"] == "deepseek-v4-flash"
    assert row["input_tokens"] == 123
    assert row["output_tokens"] == 7
    assert row["cost_usd"] == 0.0
    assert row["cache_hit_tokens"] == 100
    assert row["cache_miss_tokens"] == 23
