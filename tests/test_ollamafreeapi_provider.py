from __future__ import annotations

from core.runtime.ollamafreeapi_provider import (
    call_ollamafreeapi,
    collapse_messages_to_prompt,
)


def test_collapse_messages_to_prompt_preserves_roles() -> None:
    prompt = collapse_messages_to_prompt(
        [
            {"role": "system", "content": "You are a classifier."},
            {"role": "user", "content": "happy or sad?"},
        ]
    )

    assert "SYSTEM: You are a classifier." in prompt
    assert "USER: happy or sad?" in prompt


def test_call_ollamafreeapi_returns_ollama_compatible_shape(monkeypatch) -> None:
    monkeypatch.setattr(
        "core.runtime.ollamafreeapi_provider._client",
        lambda: type(
            "_FakeClient",
            (),
            {"chat": staticmethod(lambda prompt, model=None, timeout=30: "happy")},
        )(),
    )

    result = call_ollamafreeapi(model="llama3.2:3b", prompt='One word: "Sunny day"')

    assert result["message"]["content"] == "happy"
    assert result["done"] is True
    assert isinstance(result["total_duration"], int)
