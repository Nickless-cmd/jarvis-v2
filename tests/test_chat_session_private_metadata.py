from dataclasses import dataclass

from core.services.chat_session_private_metadata import encrypt_session_text


def test_explicit_member_title_is_encrypted_before_first_message(monkeypatch):
    import core.identity.users as users
    import core.services.keyring_store as keys

    @dataclass
    class User:
        discord_id: str = "member-id"
        role: str = "member"
        workspace: str = "member-workspace"

    monkeypatch.setattr(users, "load_users", lambda: [User()])
    monkeypatch.setattr(keys, "get_user_key", lambda _uid: b"x" * 32)
    title = encrypt_session_text("private title", "new-session", user_id="member-id")
    assert title.startswith("enc:v1:")
    assert "private title" not in title
