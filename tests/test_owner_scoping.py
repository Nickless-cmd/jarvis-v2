"""Owner-scoping: tomt user_id fra owner-authed klient → udled ejerens discord_id."""
from apps.api.jarvis_api.routes.agent_loop import _owner_scoped_user_id


def test_owner_empty_resolves_owner_id(monkeypatch):
    monkeypatch.setattr("core.identity.owner_resolver.get_owner_discord_id", lambda: "owner-123")
    assert _owner_scoped_user_id("", "owner") == "owner-123"
    assert _owner_scoped_user_id(None, "owner") == "owner-123"


def test_explicit_user_id_unchanged(monkeypatch):
    monkeypatch.setattr("core.identity.owner_resolver.get_owner_discord_id", lambda: "owner-123")
    assert _owner_scoped_user_id("member-9", "owner") == "member-9"


def test_non_owner_empty_stays_empty(monkeypatch):
    monkeypatch.setattr("core.identity.owner_resolver.get_owner_discord_id", lambda: "owner-123")
    assert _owner_scoped_user_id("", "member") == ""
