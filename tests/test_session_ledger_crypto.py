from dataclasses import dataclass
import pytest

from core.runtime.session_ledger_crypto import protect_event, reveal_event


def test_message_content_and_blocks_round_trip(monkeypatch):
    import core.identity.users as users
    import core.services.keyring_store as keys

    @dataclass
    class User:
        discord_id: str = "member-id"
        role: str = "member"
        workspace: str = "member-workspace"

    monkeypatch.setattr(users, "load_users", lambda: [User()])
    monkeypatch.setattr(keys, "get_user_key", lambda _uid: b"x" * 32)
    event = {"kind": "message", "payload": {
        "user_id": "member-id", "content": "secret", "content_json": [{"text": "secret"}],
    }}
    protected = protect_event("session", event)
    assert protected["payload"]["content"].startswith("enc:v1:")
    assert protected["payload"]["content_json"].startswith("enc:v1:")
    assert reveal_event("session", protected) == event


def test_authenticated_member_without_key_cannot_write_ledger(monkeypatch):
    import core.identity.workspace_context as context
    monkeypatch.setattr(context, "current_role", lambda: "member")
    with pytest.raises(RuntimeError, match="member key"):
        protect_event("unknown-session", {"kind": "message", "payload": {
            "user_id": "unknown", "content": "private"}})
