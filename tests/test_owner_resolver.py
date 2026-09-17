"""Tests for owner_resolver — især Discord-guarden til wakeup-routing
(Bjørn 2026-06-13: wakeup må aldrig re-engagere i en Discord-session)."""
from __future__ import annotations

from unittest.mock import patch

from core.identity.owner_resolver import (
    resolve_owner_app_session,
    session_is_external_channel,
)


def test_session_is_external_detects_discord():
    with patch("core.services.chat_sessions.get_chat_session", return_value={"title": "Discord DM"}):
        assert session_is_external_channel("s-disc") is True


def test_session_is_external_false_for_webchat():
    with patch("core.services.chat_sessions.get_chat_session", return_value={"title": "New chat"}):
        assert session_is_external_channel("s-app") is False


def test_session_is_external_empty_is_false():
    assert session_is_external_channel("") is False
    assert session_is_external_channel(None) is False


def test_session_is_external_failsafe_on_error():
    # Ved fejl → False (behandl som app), så vi ikke smider en legit session væk.
    with patch("core.services.chat_sessions.get_chat_session", side_effect=RuntimeError("boom")):
        assert session_is_external_channel("s-x") is False


def test_resolve_app_session_skips_discord_returns_app():
    sessions = [{"id": "disc-1"}, {"id": "app-2"}]

    def fake_get(sid):
        return {"id": sid, "title": "Discord DM" if sid.startswith("disc") else "New chat",
                "messages": [{"role": "user", "text": "hej"}]}

    with patch("core.services.chat_sessions.list_chat_sessions", return_value=sessions), \
         patch("core.services.chat_sessions.get_chat_session", side_effect=fake_get), \
         patch("core.services.notification_bridge.get_pinned_session_id", return_value=""), \
         patch("core.identity.owner_resolver.get_owner_discord_id", return_value="owner1"), \
         patch("core.identity.owner_resolver.is_owner_session", return_value=True):
        result = resolve_owner_app_session()
    assert result == "app-2"  # sprang Discord-sessionen over


def test_resolve_app_session_empty_when_only_discord():
    sessions = [{"id": "disc-1"}]

    def fake_get(sid):
        return {"id": sid, "title": "Discord DM", "messages": [{"role": "user", "text": "x"}]}

    with patch("core.services.chat_sessions.list_chat_sessions", return_value=sessions), \
         patch("core.services.chat_sessions.get_chat_session", side_effect=fake_get), \
         patch("core.services.notification_bridge.get_pinned_session_id", return_value=""), \
         patch("core.identity.owner_resolver.get_owner_discord_id", return_value="owner1"), \
         patch("core.identity.owner_resolver.is_owner_session", return_value=True):
        result = resolve_owner_app_session()
    assert result == ""  # ingen app-session → "" (kalder opretter frisk, ikke Discord)


# ── Sidste udvej (17/9-2026) ────────────────────────────────────────────────
# MÅLT: 0 af 502 sessioner er stemplet med owner's user_id, så heuristikkerne i
# is_owner_session kan strukturelt ikke matche. Før svarede resolveren "" for
# enhver wakeup uden eksplicit session — de landede i «auto-wakeup-*» og blev
# aldrig set. Fallback'en vælger den senest aktive APP-session.


def test_fallback_vaelger_senest_aktive_app_session():
    sessions = [{"id": "gammel"}, {"id": "ny"}]

    def fake_get(sid):
        return {
            "id": sid,
            "title": "New chat",
            "updated_at": "2026-09-01T10:00:00+00:00" if sid == "gammel" else "2026-09-17T20:00:00+00:00",
            "messages": [{"role": "user", "text": "hej"}],
        }

    with patch("core.services.chat_sessions.list_chat_sessions", return_value=sessions), \
         patch("core.services.chat_sessions.get_chat_session", side_effect=fake_get), \
         patch("core.services.notification_bridge.get_pinned_session_id", return_value=""), \
         patch("core.identity.owner_resolver.get_owner_discord_id", return_value="owner1"), \
         patch("core.identity.owner_resolver.is_owner_session", return_value=False):
        result = resolve_owner_app_session()
    assert result == "ny"  # senest opdaterede app-session


def test_fallback_springer_discord_og_auto_over():
    sessions = [{"id": "disc-1"}, {"id": "auto-wakeup-20260917"}, {"id": "app-3"}]

    def fake_get(sid):
        titler = {"disc-1": "Discord DM", "auto-wakeup-20260917": "Autonom · Vækning", "app-3": "New chat"}
        opdateret = {
            "disc-1": "2026-09-17T21:00:00+00:00",   # nyest — men ekstern
            "auto-wakeup-20260917": "2026-09-17T20:30:00+00:00",  # naestnyest — men autonom
            "app-3": "2026-09-17T20:00:00+00:00",
        }
        return {"id": sid, "title": titler[sid], "updated_at": opdateret[sid],
                "messages": [{"role": "user", "text": "hej"}]}

    with patch("core.services.chat_sessions.list_chat_sessions", return_value=sessions), \
         patch("core.services.chat_sessions.get_chat_session", side_effect=fake_get), \
         patch("core.services.notification_bridge.get_pinned_session_id", return_value=""), \
         patch("core.identity.owner_resolver.get_owner_discord_id", return_value="owner1"), \
         patch("core.identity.owner_resolver.is_owner_session", return_value=False):
        result = resolve_owner_app_session()
    assert result == "app-3"  # hverken Discord eller auto-*


def test_fallback_ignorerer_session_uden_brugerbeskeder():
    sessions = [{"id": "tom"}, {"id": "brugt"}]

    def fake_get(sid):
        msgs = [{"role": "assistant", "text": "x"}] if sid == "tom" else [{"role": "user", "text": "hej"}]
        return {"id": sid, "title": "New chat", "updated_at": "2026-09-17T20:00:00+00:00",
                "messages": msgs}

    with patch("core.services.chat_sessions.list_chat_sessions", return_value=sessions), \
         patch("core.services.chat_sessions.get_chat_session", side_effect=fake_get), \
         patch("core.services.notification_bridge.get_pinned_session_id", return_value=""), \
         patch("core.identity.owner_resolver.get_owner_discord_id", return_value="owner1"), \
         patch("core.identity.owner_resolver.is_owner_session", return_value=False):
        result = resolve_owner_app_session()
    assert result == "brugt"


def test_fallback_giver_tom_naar_kun_discord_findes():
    sessions = [{"id": "disc-1"}]

    def fake_get(sid):
        return {"id": sid, "title": "Discord DM", "updated_at": "2026-09-17T20:00:00+00:00",
                "messages": [{"role": "user", "text": "hej"}]}

    with patch("core.services.chat_sessions.list_chat_sessions", return_value=sessions), \
         patch("core.services.chat_sessions.get_chat_session", side_effect=fake_get), \
         patch("core.services.notification_bridge.get_pinned_session_id", return_value=""), \
         patch("core.identity.owner_resolver.get_owner_discord_id", return_value="owner1"), \
         patch("core.identity.owner_resolver.is_owner_session", return_value=False):
        result = resolve_owner_app_session()
    assert result == ""  # aldrig en ekstern kanal, selv som sidste udvej
