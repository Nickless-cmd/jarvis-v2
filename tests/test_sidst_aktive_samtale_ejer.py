from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from core.services.autonomous_run_digest import post_referat
from core.services.proactivity_bridge import _persist_as_chat, _sidst_aktive_samtale


def _indsæt_session(isolated_runtime, session_id: str, owner: str, alder_minutter: int) -> None:
    tidspunkt = (datetime.now(UTC) - timedelta(minutes=alder_minutter)).isoformat()
    with isolated_runtime.db.connect() as conn:
        conn.execute(
            """INSERT INTO chat_sessions
                   (session_id, title, created_at, updated_at, owner_user_id)
               VALUES (?, ?, ?, ?, ?)""",
            (session_id, session_id, tidspunkt, tidspunkt, owner),
        )


def _bind_ejer(monkeypatch) -> None:
    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id", lambda: "bjorn")


def test_bjoerns_session_vaelges_selv_om_mikkels_er_nyere(
    isolated_runtime, monkeypatch,
):
    _bind_ejer(monkeypatch)
    _indsæt_session(isolated_runtime, "chat-bjorn", "bjorn", 10)
    _indsæt_session(isolated_runtime, "chat-mikkel", "mikkel", 1)

    assert _sidst_aktive_samtale() == "chat-bjorn"


def test_kun_mikkels_session_giver_tomt_resultat(isolated_runtime, monkeypatch):
    _bind_ejer(monkeypatch)
    _indsæt_session(isolated_runtime, "chat-mikkel", "mikkel", 1)

    assert _sidst_aktive_samtale() == ""


def test_kun_ejerloes_session_giver_tomt_resultat(isolated_runtime, monkeypatch):
    _bind_ejer(monkeypatch)
    _indsæt_session(isolated_runtime, "chat-legacy", "", 1)

    assert _sidst_aktive_samtale() == ""


def test_post_referat_med_tomt_sessionopslag_skriver_intet():
    with patch("core.services.proactivity_bridge._sidst_aktive_samtale", return_value=""), \
         patch("core.services.notification_bridge.send_session_notification") as send:
        assert post_referat(
            run_id="run-1",
            session_id="auto-dream-1",
            output="Jeg gennemgik nattens noter.",
        ) == ""

    send.assert_not_called()


def test_persist_med_tomt_sessionopslag_opretter_ikke_global_silo():
    with patch("core.services.proactivity_bridge._sidst_aktive_samtale", return_value=""), \
         patch("core.services.chat_sessions.get_or_create_named_session") as create, \
         patch("core.services.notification_bridge.send_session_notification") as send:
        assert _persist_as_chat("bjorn", "En proaktiv besked") == ""

    create.assert_not_called()
    send.assert_not_called()


def test_fallback_til_ejerstemplet_silo_leverer_beskeden(isolated_runtime, monkeypatch):
    """Er der ingen frisk samtale, men siloen ER hans, skal beskeden ikke tabes.

    12/11-2026: siloen stod uden ejerstempel og blev derfor et frit maal. Den er
    nu stempelt, og fallbacken kraever stemplet eksplicit — ellers skrives intet.
    """
    from core.services import proactivity_bridge as B

    _indsæt_session(isolated_runtime, B._PROACTIVITY_SESSION_ID, "bjorn", 5)
    skrevet: list[dict] = []

    monkeypatch.setattr(B, "_sidst_aktive_samtale", lambda: "")
    monkeypatch.setattr(
        "core.services.notification_bridge.send_session_notification",
        lambda *a, **kw: skrevet.append(kw) or {"ok": True},
    )
    monkeypatch.setattr(
        "core.services.notification_bridge.delivery_succeeded", lambda _svar: True,
    )

    assert B._persist_as_chat("bjorn", "En proaktiv besked") == B._PROACTIVITY_SESSION_ID
    assert skrevet and skrevet[0]["session_id"] == B._PROACTIVITY_SESSION_ID


def test_fallback_naegtes_naar_siloen_er_fremmed(isolated_runtime, monkeypatch):
    """En silo der tilhoerer en ANDEN maa aldrig bruges som fallback."""
    from core.services import proactivity_bridge as B

    _indsæt_session(isolated_runtime, B._PROACTIVITY_SESSION_ID, "mikkel", 5)
    skrevet: list[dict] = []

    monkeypatch.setattr(B, "_sidst_aktive_samtale", lambda: "")
    monkeypatch.setattr(
        "core.services.notification_bridge.send_session_notification",
        lambda *a, **kw: skrevet.append(kw) or {"ok": True},
    )

    assert B._persist_as_chat("bjorn", "En proaktiv besked") == ""
    assert skrevet == []
