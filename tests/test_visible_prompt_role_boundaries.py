"""Regression tests for visible prompt role and duplication boundaries."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from core.services import visible_model
from core.services.prompt_contract import DYNAMIC_TAIL_SENTINEL


USER_TEXT = "Det var ikke mig; beskeden findes kun én gang i databasen."
DYNAMIC_TEXT = "[user_temperature_field]\nAffect-sat denne tur\nSelf-signals"


def _assembly():
    return SimpleNamespace(
        text=f"STABLE SYSTEM{DYNAMIC_TAIL_SENTINEL}{DYNAMIC_TEXT}",
        transcript_messages=[{"role": "user", "content": USER_TEXT}],
    )


def _assert_role_boundary(messages: list[dict[str, str]]) -> None:
    user_messages = [m for m in messages if m.get("role") == "user"]
    assert [m.get("content") for m in user_messages] == [USER_TEXT]
    assert sum(str(m.get("content") or "").count(USER_TEXT) for m in messages) == 1
    assert all(DYNAMIC_TEXT not in str(m.get("content") or "") for m in user_messages)
    assert any(
        m.get("role") == "system" and DYNAMIC_TEXT in str(m.get("content") or "")
        for m in messages
    )


def test_openai_compatible_request_keeps_current_user_once_and_dynamic_tail_system_role(
    monkeypatch,
) -> None:
    monkeypatch.setattr(visible_model, "_build_visible_prompt_assembly", lambda **_: _assembly())

    messages = visible_model._build_visible_chat_messages_for_github(
        USER_TEXT,
        session_id="chat-test",
        provider="deepseek",
        model="deepseek-v4-flash",
    )

    _assert_role_boundary(messages)


def test_ollama_request_keeps_dynamic_tail_out_of_user_role(monkeypatch) -> None:
    monkeypatch.setattr(visible_model, "_build_visible_prompt_assembly", lambda **_: _assembly())

    items = visible_model._build_visible_input(
        USER_TEXT,
        session_id="chat-test",
        provider="ollama",
        model="qwen3.5:9b",
    )
    messages = [
        {
            "role": item.get("role"),
            "content": "\n".join(
                str(part.get("text") or "")
                for part in item.get("content") or []
                if isinstance(part, dict)
            ),
        }
        for item in items
    ]

    _assert_role_boundary(messages)


def test_user_role_compact_marker_does_not_suppress_current_message(monkeypatch) -> None:
    assembly = SimpleNamespace(
        text=f"STABLE SYSTEM{DYNAMIC_TAIL_SENTINEL}{DYNAMIC_TEXT}",
        transcript_messages=[
            {"role": "user", "content": "[Komprimeret historik: tidligere samtale]"},
        ],
    )
    monkeypatch.setattr(visible_model, "_build_visible_prompt_assembly", lambda **_: assembly)

    messages = visible_model._build_visible_chat_messages_for_github(
        USER_TEXT,
        session_id="chat-test",
        provider="deepseek",
        model="deepseek-v4-flash",
    )

    assert any(m.get("role") == "user" and m.get("content") == USER_TEXT for m in messages)


def test_failed_compaction_then_next_request_has_no_duplicate_or_user_role_prompt_tail(
    monkeypatch,
) -> None:
    from core.services.prompt_sections import transcript_sections

    provider_error = (
        "Sorry, to prevent abuse of free resources, accounts that have not "
        "been recharged can only try 10 times. Top up at "
        "https://console.aihubmix.com/topup"
    )
    old_messages = [
        {"role": "user", "content": "Vi jagter prompt-lækagen."},
        {"role": "assistant", "content": "Jeg følger request-pipelinen."},
    ]
    with patch("core.context.compact_llm.call_compact_llm", return_value=provider_error), patch.object(
        transcript_sections, "_ground_truth_for", return_value=""
    ):
        summarise = transcript_sections._make_structured_summariser(session_id="chat-test")
        compact_summary = summarise(old_messages)

    assert "Mechanical fallback" in compact_summary
    assert "aihubmix" not in compact_summary.lower()

    assembly = SimpleNamespace(
        text=f"STABLE SYSTEM{DYNAMIC_TAIL_SENTINEL}{DYNAMIC_TEXT}",
        transcript_messages=[
            {
                "role": "user",
                "content": f"[Komprimeret historik:\n{compact_summary}]",
            },
            {"role": "assistant", "content": "Forstået."},
            {"role": "user", "content": USER_TEXT},
        ],
    )
    monkeypatch.setattr(visible_model, "_build_visible_prompt_assembly", lambda **_: assembly)

    messages = visible_model._build_visible_chat_messages_for_github(
        USER_TEXT,
        session_id="chat-test",
        provider="deepseek",
        model="deepseek-v4-flash",
    )

    current_user = [m for m in messages if m.get("role") == "user" and USER_TEXT in m["content"]]
    assert current_user == [{"role": "user", "content": USER_TEXT}]
    assert DYNAMIC_TEXT not in "\n".join(m["content"] for m in messages if m["role"] == "user")
