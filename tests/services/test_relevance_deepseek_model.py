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
