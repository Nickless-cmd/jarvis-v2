"""Streaming openai-compat client: output-budget + extra_body i payloaden.

4/9-2026: 4096 max_tokens laa haardkodet i BAADE foelge-runderne og den
streamede foerste pas. DeepSeek thinking-mode taeller raesonneringen med →
length uden tekst. Budgettet er nu provider-skaleret (followup_output_budget).
"""
from __future__ import annotations

from contextlib import contextmanager

import core.services.cheap_provider_runtime as cheap
import core.services.cheap_provider_runtime_streaming as streaming


class _FakeResponse:
    status_code = 200
    headers: dict = {}

    def __init__(self, lines):
        self._lines = list(lines)

    def iter_lines(self):
        return iter(self._lines)

    def iter_text(self):
        return iter(self._lines)

    def iter_bytes(self):
        return iter(l.encode() for l in self._lines)

    def read(self):
        return b""


def _capture_payload(monkeypatch) -> dict:
    seen: dict = {}

    @contextmanager
    def fake_stream(method, url, *, json=None, headers=None, timeout=None):  # noqa: A002
        seen["url"] = url
        seen["payload"] = json
        yield _FakeResponse(["data: [DONE]", ""])

    monkeypatch.setattr(streaming.httpx, "stream", fake_stream)
    monkeypatch.setattr(cheap, "_require_credentials",
                        lambda **kw: {"api_key": "fake-test-key"}, raising=False)  # pragma: allowlist secret
    monkeypatch.setattr(cheap, "provider_runtime_defaults",
                        lambda pid: {"base_url": "https://api.test/v1"}, raising=False)
    return seen


def _drain(provider: str, model: str, extra_body=None):
    return list(streaming._iter_openai_compatible_chat_events(
        provider=provider, model=model, auth_profile="default",
        base_url="https://api.test/v1",
        messages=[{"role": "user", "content": "hej"}], extra_body=extra_body))


def test_deepseek_stream_budget_fits_reasoning_and_merges_thinking_params(monkeypatch):
    seen = _capture_payload(monkeypatch)
    _drain("deepseek", "deepseek-v4-flash", extra_body={"thinking": {"type": "disabled"}})
    p = seen["payload"]
    assert p["max_tokens"] == 32_768
    assert p["thinking"] == {"type": "disabled"}
    assert p["stream"] is True and p["model"] == "deepseek-v4-flash"


def test_cheap_lane_providers_keep_4096(monkeypatch):
    seen = _capture_payload(monkeypatch)
    _drain("groq", "llama-3.3-70b")
    assert seen["payload"]["max_tokens"] == 4096
    assert "thinking" not in seen["payload"]
