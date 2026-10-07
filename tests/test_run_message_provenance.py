from types import SimpleNamespace

from core.services import visible_model
from core.services.run_autonomy_context import reset_autonomous, set_autonomous, set_run_identity


def test_recurring_task_is_labeled_as_runtime_input_on_both_provider_paths(monkeypatch):
    monkeypatch.setattr(
        visible_model, "_build_visible_prompt_assembly",
        lambda **_kwargs: SimpleNamespace(text="Systeminstruks", transcript_messages=[]),
    )
    token = set_autonomous(True)
    set_run_identity("autonomous-test", "recurring")
    try:
        typed = visible_model._build_visible_input("Send morgenbrief", session_id=None,
                                                   provider="ollama", model="x")
        plain = visible_model._build_visible_chat_messages_for_github(
            "Send morgenbrief", session_id=None, provider="deepseek", model="x")
    finally:
        set_run_identity("", "")
        reset_autonomous(token)

    for content in (typed[-1]["content"][0]["text"], plain[-1]["content"]):
        assert "AUTOMATISK RUNTIME-OPGAVE" in content
        assert "ikke en ny besked fra Bjørn" in content
        assert content.endswith("Send morgenbrief")
    assert "ikke en ny besked fra Bjørn" in typed[0]["content"][0]["text"]
    assert "ikke en ny besked fra Bjørn" in plain[0]["content"]


def test_persisted_recurring_turn_is_labeled_without_duplication(monkeypatch):
    monkeypatch.setattr(
        visible_model, "_build_visible_prompt_assembly",
        lambda **_kwargs: SimpleNamespace(
            text="Systeminstruks",
            transcript_messages=[{"role": "user", "content": "Send morgenbrief"}],
        ),
    )
    token = set_autonomous(True)
    set_run_identity("autonomous-test", "recurring")
    try:
        typed = visible_model._build_visible_input("Send morgenbrief", session_id=None,
                                                   provider="ollama", model="x")
        plain = visible_model._build_visible_chat_messages_for_github(
            "Send morgenbrief", session_id=None, provider="deepseek", model="x")
    finally:
        set_run_identity("", "")
        reset_autonomous(token)

    for messages in (typed, plain):
        assert len([item for item in messages if item["role"] == "user"]) == 1
        content = messages[-1]["content"]
        if isinstance(content, list):
            content = content[0]["text"]
        assert content.count("AUTOMATISK RUNTIME-OPGAVE") == 1
        assert "ikke en ny besked fra Bjørn" in content
