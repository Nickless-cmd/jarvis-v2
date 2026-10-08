"""Member prompts must use the member's identity and own conversation only."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException


def test_member_visible_prompt_cannot_inherit_owner_profile(tmp_path, monkeypatch):
    from core.identity import users
    from core.identity.workspace_context import set_context, reset_context
    from core.runtime import workspace_paths
    from core.services import chat_sessions, visible_model

    member = SimpleNamespace(discord_id="michelle-id", workspace="michelle",
                             name="Michelle", role="partner")
    monkeypatch.setattr(users, "find_user_by_discord_id", lambda uid: member if uid == "michelle-id" else None)
    monkeypatch.setattr(workspace_paths, "workspace_dir", lambda uid: tmp_path / "michelle")
    monkeypatch.setattr(chat_sessions, "get_session_owner", lambda sid: "michelle-id")
    monkeypatch.setattr(chat_sessions, "recent_chat_session_messages", lambda sid, limit: [
        {"role": "user", "content": "Hvad ved du om mig?"},
        {"role": "assistant", "content": "Bjørns private ejerprofil"},
    ])
    monkeypatch.setattr(visible_model, "build_visible_chat_prompt_assembly",
                        lambda **kw: pytest.fail("owner assembly was used for member"))
    root = tmp_path / "michelle"
    root.mkdir()
    (root / "USER.md").write_text("Michelle kan lide grøn te", encoding="utf-8")
    (root / "MEMORY.md").write_text("Michelle har egen hukommelse", encoding="utf-8")
    shared = tmp_path / "shared"
    shared.mkdir()
    (shared / "USER.md").write_text("Bjørns private ejerprofil", encoding="utf-8")

    token = set_context(workspace_name="michelle", user_id="michelle-id", role="partner")
    try:
        assembly = visible_model._build_visible_prompt_assembly(
            provider="ollama", model="test", user_message="Hvad ved du om mig?",
            session_id="michelle-session",
        )
    finally:
        reset_context(token)
    assert "Michelle" in assembly.text
    assert "grøn te" in assembly.text
    assert "Bjørns private" not in assembly.text
    assert assembly.transcript_messages == [{"role": "user", "content": "Hvad ved du om mig?"}]


def test_member_visible_prompt_rejects_foreign_session(tmp_path, monkeypatch):
    from core.identity import users
    from core.identity.workspace_context import set_context, reset_context
    from core.services import chat_sessions, visible_model

    member = SimpleNamespace(discord_id="michelle-id", workspace="michelle",
                             name="Michelle", role="partner")
    monkeypatch.setattr(users, "find_user_by_discord_id", lambda uid: member if uid == "michelle-id" else None)
    monkeypatch.setattr(chat_sessions, "get_session_owner", lambda sid: "bjorn-id")
    token = set_context(workspace_name="michelle", user_id="michelle-id", role="partner")
    try:
        with pytest.raises(PermissionError, match="own session"):
            visible_model._build_visible_prompt_assembly(
                provider="ollama", model="test", user_message="Hej",
                session_id="foreign-session",
            )
    finally:
        reset_context(token)


@pytest.mark.asyncio
async def test_stream_v2_rejects_foreign_session_before_message_is_saved(monkeypatch):
    from apps.api.jarvis_api.routes import chat_stream_v2
    from core.identity import session_access
    from apps.api.jarvis_api.routes.chat import ChatStreamRequest

    monkeypatch.setattr(chat_stream_v2, "get_chat_session", lambda sid: {"session_id": sid})
    monkeypatch.setattr(session_access, "maa_tilgaa_session", lambda sid: False)
    with pytest.raises(HTTPException) as exc:
        await chat_stream_v2.chat_stream_v2(
            ChatStreamRequest(session_id="foreign", message="Hej")
        )
    assert exc.value.status_code == 403
