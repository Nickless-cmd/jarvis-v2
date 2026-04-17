"""Smoke test for core.services.ollama_visible_prompt.

Visible prompt serialization should preserve both the internal system block and
the user/assistant conversation in Ollama-friendly formats.
"""

from core.services import ollama_visible_prompt


def test_visible_prompt_serialization_keeps_system_and_conversation_text() -> None:
    items = [
        {"role": "system", "content": [{"text": "Follow the mission."}]},
        {"role": "user", "content": [{"text": "Hej Jarvis"}]},
        {"role": "assistant", "content": [{"text": "Hej Bjørn"}]},
    ]

    prompt = ollama_visible_prompt.serialize_ollama_visible_prompt(items)
    messages = ollama_visible_prompt.serialize_ollama_chat_messages(items)

    assert "Internal system instructions" in prompt
    assert "User:\nHej Jarvis" in prompt
    assert messages[0] == {"role": "system", "content": "Follow the mission."}
    assert messages[1]["role"] == "user"
