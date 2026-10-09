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
    # Assistent-turen har ingen created_at → droppet (fail closed). Kun
    # brugerens egen tur står tilbage.
    assert assembly.transcript_messages == [{"role": "user", "content": "Hvad ved du om mig?"}]


def _member_env(monkeypatch, tmp_path, history):
    from types import SimpleNamespace as _SN

    from core.identity import users
    from core.runtime import workspace_paths
    from core.services import chat_sessions

    member = _SN(discord_id="michelle-id", workspace="michelle",
                 name="Michelle", role="partner")
    monkeypatch.setattr(users, "find_user_by_discord_id",
                        lambda uid: member if uid == "michelle-id" else None)
    monkeypatch.setattr(workspace_paths, "workspace_dir", lambda uid: tmp_path / "michelle")
    monkeypatch.setattr(chat_sessions, "get_session_owner", lambda sid: "michelle-id")
    monkeypatch.setattr(chat_sessions, "recent_chat_session_messages",
                        lambda sid, limit: history)
    root = tmp_path / "michelle"
    root.mkdir(exist_ok=True)
    (root / "USER.md").write_text("Michelle kan lide grøn te", encoding="utf-8")


def _member_assembly(monkeypatch, tmp_path, history, user_message="Er du sikker?"):
    from core.identity.workspace_context import set_context, reset_context
    from core.services import visible_model

    _member_env(monkeypatch, tmp_path, history)
    token = set_context(workspace_name="michelle", user_id="michelle-id", role="partner")
    try:
        return visible_model._build_visible_prompt_assembly(
            provider="ollama", model="test", user_message=user_message,
            session_id="michelle-session",
        )
    finally:
        reset_context(token)


def test_member_prompt_includes_recent_assistant_turns(monkeypatch, tmp_path):
    """Efter isolerings-fixet skal Jarvis kunne se sine egne svar i tråden."""
    assembly = _member_assembly(monkeypatch, tmp_path, [
        {"role": "user", "content": "Hvad hedder min kat?", "created_at": "2026-10-09T10:00:00+00:00"},
        {"role": "assistant", "content": "Din kat hedder Mille.", "created_at": "2026-10-09T10:00:05+00:00"},
        {"role": "user", "content": "Er du sikker?", "created_at": "2026-10-09T10:01:00+00:00"},
    ])
    assert [m["role"] for m in assembly.transcript_messages] == ["user", "assistant", "user"]
    assert "Mille" in assembly.transcript_messages[1]["content"]


def test_member_prompt_drops_pre_fix_assistant_turns(monkeypatch, tmp_path):
    """Assistent-ture fra FØR 8/10-isoleringen må ikke føres tilbage."""
    assembly = _member_assembly(monkeypatch, tmp_path, [
        {"role": "user", "content": "Hej", "created_at": "2026-10-07T10:00:00+00:00"},
        {"role": "assistant", "content": "Bjørn bor i Svendborg", "created_at": "2026-10-07T10:00:05+00:00"},
        {"role": "user", "content": "Ok", "created_at": "2026-10-09T10:00:00+00:00"},
        {"role": "assistant", "content": "Fint", "created_at": "2026-10-09T10:00:05+00:00"},
    ])
    contents = [m["content"] for m in assembly.transcript_messages]
    assert "Bjørn bor i Svendborg" not in contents       # før fixet → væk
    assert "Fint" in contents                            # efter fixet → med
    assert [m["role"] for m in assembly.transcript_messages] == ["user", "user", "assistant"]


def test_member_prompt_redacts_secrets_in_transcript(monkeypatch, tmp_path):
    """En hemmelighed i en tidligere tur maskeres før den går i prompten."""
    nogle = "sk-" + "A1b2C3d4E5f6G7h8I9j0"
    assembly = _member_assembly(monkeypatch, tmp_path, [
        {"role": "assistant", "content": f"nøglen er {nogle}", "created_at": "2026-10-09T10:00:05+00:00"},
    ], user_message="hvad er nøglen?")
    tekst = assembly.transcript_messages[0]["content"]
    assert nogle not in tekst
    assert "hemmelighed fjernet" in tekst


def test_member_prompt_includes_learned_section(monkeypatch, tmp_path):
    """`## Lært` fra medlemmets EGEN USER.md læses ind — med partnerens navn."""
    from core.identity import users
    from core.runtime import workspace_paths
    from core.services import chat_sessions

    member = SimpleNamespace(discord_id="michelle-id", workspace="michelle",
                             name="Michelle", role="partner")
    monkeypatch.setattr(users, "find_user_by_discord_id",
                        lambda uid: member if uid == "michelle-id" else None)
    monkeypatch.setattr(workspace_paths, "workspace_dir", lambda uid: tmp_path / "michelle")
    monkeypatch.setattr(chat_sessions, "get_session_owner", lambda sid: "michelle-id")
    monkeypatch.setattr(chat_sessions, "recent_chat_session_messages",
                        lambda sid, limit: [])
    root = tmp_path / "michelle"
    root.mkdir()
    (root / "USER.md").write_text(
        "## Lært\n- Michelle vil have korte svar uden emoji (2026-10-09, sagt eksplicit)\n",
        encoding="utf-8",
    )

    from core.identity.workspace_context import set_context, reset_context
    from core.services import visible_model

    token = set_context(workspace_name="michelle", user_id="michelle-id", role="partner")
    try:
        assembly = visible_model._build_visible_prompt_assembly(
            provider="ollama", model="test",
            user_message="Vil du have korte svar fremover?",
            session_id="michelle-session",
        )
    finally:
        reset_context(token)
    assert "Lært om Michelle" in assembly.text
    assert "korte svar uden emoji" in assembly.text
    assert "Lært om Bjørn" not in assembly.text


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
