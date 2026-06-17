"""Hugging Face-connector: søg/info via Hub API (mocket httpx)."""
from __future__ import annotations

import httpx

import core.services.hf_connector as hf


class _Resp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload


def _mock(monkeypatch, status, payload):
    monkeypatch.setattr(hf, "_headers", lambda: {"Authorization": "Bearer x"})
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _Resp(status, payload))


def test_search_models(monkeypatch):
    _mock(monkeypatch, 200, [
        {"id": "org/llm-da", "downloads": 1234, "likes": 5, "tags": ["da", "llm"]},
    ])
    res = hf.search_models("danish", limit=5)
    assert res["status"] == "ok" and res["count"] == 1
    assert res["models"][0]["id"] == "org/llm-da"
    assert res["models"][0]["downloads"] == 1234


def test_model_info(monkeypatch):
    _mock(monkeypatch, 200, {"id": "org/m", "downloads": 9, "likes": 2,
                             "pipeline_tag": "text-generation", "tags": ["t"], "library_name": "transformers"})
    res = hf.model_info("org/m")
    assert res["status"] == "ok" and res["pipeline_tag"] == "text-generation"
    assert res["library"] == "transformers"


def test_not_found(monkeypatch):
    _mock(monkeypatch, 404, {})
    assert hf.model_info("org/missing")["error"] == "hf_not_found"


def test_query_required(monkeypatch):
    _mock(monkeypatch, 200, [])
    assert hf.search_models("")["error"] == "query_required"
    assert hf.model_info("")["error"] == "model_id_required"
