"""Regression coverage for pragmatic repair and boundaries in chat mode."""
from __future__ import annotations

from types import SimpleNamespace

from core.services import visible_model
from core.services.visible_chat_pragmatics import (
    CHAT_MODE_CONVERSATION_CONTRACT,
    apply_chat_mode_conversation_contract,
)
from core.tools.tool_scoping import tool_scope


def test_contract_is_injected_only_in_chat_scope() -> None:
    with tool_scope("chat"):
        chat = apply_chat_mode_conversation_contract("BASE")
    with tool_scope("code"):
        code = apply_chat_mode_conversation_contract("BASE")
    with tool_scope(""):
        unbound = apply_chat_mode_conversation_contract("BASE")

    assert CHAT_MODE_CONVERSATION_CONTRACT in chat
    assert code == "BASE"
    assert unbound == "BASE"


def test_contract_covers_reaction_correction_and_stop_signal() -> None:
    text = " ".join(CHAT_MODE_CONVERSATION_CONTRACT.lower().split())

    assert "reaktion" in text and "bogstavelige svar" in text
    assert "korrektion" in text and "genfortolk" in text
    assert '"gå væk"' in text and "grænsesignal" in text
    assert "stil ikke et nyt spørgsmål" in text


def test_both_visible_provider_shapes_receive_chat_contract(monkeypatch) -> None:
    assembly = SimpleNamespace(text="BASE", transcript_messages=[])
    monkeypatch.setattr(
        visible_model, "_build_visible_prompt_assembly", lambda **_: assembly,
    )

    with tool_scope("chat"):
        typed = visible_model._build_visible_input(
            "Gå væk", session_id="s", provider="ollama", model="m",
        )
        plain = visible_model._build_visible_chat_messages_for_github(
            "Gå væk", session_id="s", provider="deepseek", model="m",
        )

    assert CHAT_MODE_CONVERSATION_CONTRACT in typed[0]["content"][0]["text"]
    assert CHAT_MODE_CONVERSATION_CONTRACT in plain[0]["content"]


def test_code_mode_provider_shape_does_not_receive_chat_contract(monkeypatch) -> None:
    assembly = SimpleNamespace(text="BASE", transcript_messages=[])
    monkeypatch.setattr(
        visible_model, "_build_visible_prompt_assembly", lambda **_: assembly,
    )

    with tool_scope("code"):
        plain = visible_model._build_visible_chat_messages_for_github(
            "stop serveren", session_id="s", provider="deepseek", model="m",
        )

    assert plain[0]["content"] == "BASE"
