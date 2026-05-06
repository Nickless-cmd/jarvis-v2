import json
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def isolated_keys(tmp_path, monkeypatch):
    from apps.api.jarvis_api.middleware import anthropic_auth as ah
    keys_path = tmp_path / "keys.json"
    keys_path.write_text(json.dumps({
        "keys": {"jvs-test-key": {"user": "bjorn", "workspace": "default"}}
    }))
    monkeypatch.setattr(ah, "_KEYS_PATH", keys_path)
    monkeypatch.setattr(ah, "_REPO_KEYS_PATH", keys_path)
    ah.invalidate_cache()


@pytest.fixture
def app_with_router(isolated_keys, monkeypatch):
    # Mock backend Ollama call so test doesn't need a live server.
    def fake_ollama_chat_non_stream(payload):
        return {
            "message": {
                "role": "assistant",
                "content": "Hej Bjørn 🤍",
                "tool_calls": [],
            },
            "done": True,
            "done_reason": "stop",
        }
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.anthropic_compat._ollama_chat_non_stream",
        fake_ollama_chat_non_stream,
    )
    # Mock backend model resolver so it doesn't try to read from runtime config
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.anthropic_compat._resolve_backend_model",
        lambda requested: "test-model",
    )
    from apps.api.jarvis_api.routes.anthropic_compat import router
    app = FastAPI()
    app.include_router(router)
    return app


def test_models_endpoint(app_with_router):
    with TestClient(app_with_router) as c:
        r = c.get("/anthropic/v1/models")
        assert r.status_code == 200
        data = r.json()
        ids = [m["id"] for m in data["data"]]
        assert "jarvis" in ids


def test_messages_missing_api_key_returns_401(app_with_router):
    with TestClient(app_with_router) as c:
        r = c.post("/anthropic/v1/messages", json={
            "model": "jarvis",
            "max_tokens": 100,
            "messages": [{"role": "user", "content": "hej"}],
        })
        assert r.status_code == 401
        body = r.json()
        assert body["type"] == "error"
        assert body["error"]["type"] == "authentication_error"


def test_messages_invalid_api_key_returns_401(app_with_router):
    with TestClient(app_with_router) as c:
        r = c.post("/anthropic/v1/messages",
            headers={"x-api-key": "wrong-key"},
            json={"model": "jarvis", "max_tokens": 100, "messages": [{"role": "user", "content": "hej"}]},
        )
        assert r.status_code == 401


def test_messages_non_streaming_returns_anthropic_format(app_with_router):
    with TestClient(app_with_router) as c:
        r = c.post("/anthropic/v1/messages",
            headers={"x-api-key": "jvs-test-key"},
            json={
                "model": "jarvis",
                "max_tokens": 100,
                "messages": [{"role": "user", "content": "hej"}],
                "stream": False,
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["type"] == "message"
        assert body["role"] == "assistant"
        assert body["model"] == "jarvis"
        assert body["content"][0]["type"] == "text"
        assert "Hej Bjørn" in body["content"][0]["text"]
        assert body["stop_reason"] == "end_turn"
