from __future__ import annotations


def test_resolve_copilot_profile_prefers_requested_profile(monkeypatch):
    import core.auth.copilot_session as session

    monkeypatch.setattr(
        session,
        "get_provider_state",
        lambda *, profile, provider: {"status": "active"}
        if profile == "chosen"
        else None,
    )
    monkeypatch.setattr(session, "list_auth_profiles", lambda: [])

    assert session.resolve_copilot_profile("chosen") == "chosen"


def test_resolve_copilot_profile_finds_dedicated_profile(monkeypatch):
    import core.auth.copilot_session as session

    monkeypatch.setattr(
        session,
        "get_provider_state",
        lambda *, profile, provider: {"status": "active"}
        if profile == "copilot"
        else None,
    )
    monkeypatch.setattr(
        session, "list_auth_profiles", lambda: [{"profile": "copilot"}]
    )

    assert session.resolve_copilot_profile("default") == "copilot"
