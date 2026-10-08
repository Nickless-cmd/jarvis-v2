from core.services.visible_preview_crypto import protect_preview, reveal_preview
from core.services.visible_preview_crypto import member_for_run
import pytest


def test_preview_round_trip_for_member(monkeypatch):
    from dataclasses import dataclass
    import core.identity.users as users
    import core.services.keyring_store as keys

    @dataclass
    class User:
        discord_id: str = "member-id"
        role: str = "member"
        workspace: str = "member-workspace"

    monkeypatch.setattr(users, "load_users", lambda: [User()])
    monkeypatch.setattr(keys, "get_user_key", lambda _uid: b"x" * 32)
    stored = protect_preview("private preview", "member-id")
    assert stored.startswith("enc:v1:")
    assert reveal_preview(stored, "member-id") == "private preview"
    assert reveal_preview(stored, None) == stored


def test_authenticated_member_without_key_cannot_write_preview(monkeypatch):
    import core.identity.workspace_context as context
    monkeypatch.setattr(context, "current_role", lambda: "member")
    with pytest.raises(RuntimeError, match="member key"):
        member_for_run(type("Run", (), {"user_id": "unknown", "session_id": "unknown"})())
