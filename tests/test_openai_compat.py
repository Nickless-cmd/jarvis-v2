"""Tests for OpenAI-compatible proxy endpoint."""
from __future__ import annotations

import importlib


def _get_module():
    mod = importlib.import_module("apps.api.jarvis_api.routes.openai_compat")
    return importlib.reload(mod)


def test_module_imports():
    mod = _get_module()
    assert hasattr(mod, "router")


def test_resolve_model_provider_ollama_cloud():
    mod = _get_module()
    provider, model = mod._resolve_model_provider("minimax-m2.7:cloud")
    assert provider == "ollama"
    assert model == "minimax-m2.7:cloud"


def test_resolve_model_provider_glm():
    mod = _get_module()
    provider, model = mod._resolve_model_provider("glm-5.1:cloud")
    assert provider == "ollama"
    assert model == "glm-5.1:cloud"


def test_resolve_model_provider_qwen():
    mod = _get_module()
    provider, model = mod._resolve_model_provider("qwen3.5:397b-cloud")
    assert provider == "ollama"
    assert model == "qwen3.5:397b-cloud"


def test_resolve_model_provider_gemma():
    mod = _get_module()
    provider, model = mod._resolve_model_provider("gemma4:32b-cloud")
    assert provider == "ollama"
    assert model == "gemma4:32b-cloud"


def test_resolve_model_provider_openai():
    mod = _get_module()
    provider, model = mod._resolve_model_provider("gpt-4o")
    assert provider == "openai"
    assert model == "gpt-4o"


def test_resolve_model_provider_copilot():
    mod = _get_module()
    provider, model = mod._resolve_model_provider("copilot/gpt-4o")
    assert provider == "github-copilot"
    assert model == "gpt-4o"


def test_resolve_model_provider_jarvis_default():
    mod = _get_module()
    provider, model = mod._resolve_model_provider("jarvis")
    assert isinstance(provider, str)
    assert isinstance(model, str)


def test_resolve_model_provider_empty_default():
    mod = _get_module()
    provider, model = mod._resolve_model_provider("")
    assert isinstance(provider, str)
    assert isinstance(model, str)


def test_build_openai_response_format():
    mod = _get_module()
    resp = mod._build_completion_response(
        run_id="test-123",
        model="minimax-m2.7:cloud",
        content="Hello",
        input_tokens=10,
        output_tokens=5,
    )
    assert resp["object"] == "chat.completion"
    assert resp["model"] == "minimax-m2.7:cloud"
    assert resp["choices"][0]["message"]["content"] == "Hello"
    assert resp["choices"][0]["finish_reason"] == "stop"
    assert resp["usage"]["prompt_tokens"] == 10
    assert resp["usage"]["completion_tokens"] == 5
    assert resp["usage"]["total_tokens"] == 15


def test_build_streaming_chunk_format():
    mod = _get_module()
    chunk = mod._build_stream_chunk(
        run_id="test-123",
        model="minimax-m2.7:cloud",
        delta_content="Hej",
    )
    assert chunk["object"] == "chat.completion.chunk"
    assert chunk["choices"][0]["delta"]["content"] == "Hej"
