"""Cheap lane: en model der tænker budgettet op er ikke en død model (17/9-2026, poolside)."""
import pytest

from core.services.cheap_provider_reasoning_budget import REASONING_RETRY_BUDGET, reasoning_exhausted


def _svar(content, *, finish="stop", reasoning=None, reasoning_tokens=None):
    msg = {"content": content}
    if reasoning is not None:
        msg["reasoning"] = reasoning
    usage = {}
    if reasoning_tokens is not None:
        usage["completion_tokens_details"] = {"reasoning_tokens": reasoning_tokens}
    return {"choices": [{"message": msg, "finish_reason": finish}], "usage": usage}


def test_klassificering():
    assert reasoning_exhausted(_svar(None, finish="length", reasoning="Brugeren vil have..."))
    assert reasoning_exhausted(_svar(None, finish="length", reasoning_tokens=248))
    assert not reasoning_exhausted(_svar(None, finish="length"))             # intet spor af tænkning
    assert not reasoning_exhausted(_svar(None, finish="stop", reasoning="x"))  # ikke budget-stop


def _stub(monkeypatch, svar):
    from core.services import cheap_provider_runtime as facade
    sendt = []

    def fake_http_json(url, *, provider, payload=None, **kw):
        sendt.append(dict(payload or {}))
        return (svar[min(len(sendt), len(svar)) - 1], {})

    monkeypatch.setattr(facade, "_require_credentials", lambda *, profile, provider: {"api_key": "k"})
    monkeypatch.setattr(facade, "provider_runtime_defaults", lambda provider: {"base_url": "https://x/v1"})
    monkeypatch.setattr(facade, "_http_json", fake_http_json)
    return sendt


def _kald():
    from core.services.cheap_provider_runtime_adapters import _execute_openai_compatible_chat
    return _execute_openai_compatible_chat(provider="poolside", model="laguna", auth_profile="default",
                                           base_url="https://x/v1", message="pong?",
                                           extra_body={"max_tokens": 64})


def test_nyt_forsoeg_med_stort_budget_redder_svaret(monkeypatch):
    sendt = _stub(monkeypatch, [_svar(None, finish="length", reasoning_tokens=248), _svar("pong")])
    assert _kald()["text"] == "pong"
    assert [p["max_tokens"] for p in sendt] == [64, REASONING_RETRY_BUDGET]


def test_kun_eet_nyt_forsoeg_og_ærlig_fejlkode(monkeypatch):
    from core.services.cheap_provider_runtime_adapters import CheapProviderError
    sendt = _stub(monkeypatch, [_svar(None, finish="length", reasoning="tænker...")])
    with pytest.raises(CheapProviderError) as fejl:
        _kald()
    assert fejl.value.code == "reasoning-exhausted"
    assert len(sendt) == 2


def test_ægte_tomt_svar_prøves_ikke_igen(monkeypatch):
    from core.services.cheap_provider_runtime_adapters import CheapProviderError
    sendt = _stub(monkeypatch, [_svar(None)])
    with pytest.raises(CheapProviderError) as fejl:
        _kald()
    assert fejl.value.code == "empty-response"
    assert len(sendt) == 1
