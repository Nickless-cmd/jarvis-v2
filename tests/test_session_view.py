"""Samtalens visningstilstand — Claude Desktops normal/thinking/verbose (19/9-2026)."""
from __future__ import annotations

import pytest

from core.runtime.db import connect
from core.services.session_view import hent_visning, saet_visning, vil_have_tanke_resume


@pytest.fixture
def sid(isolated_runtime):
    s = "visning-test-1"
    with connect() as c:
        c.execute("INSERT INTO chat_sessions (session_id, title, created_at, updated_at) "
                  "VALUES (?, 'T', ?, ?)", (s, "2026-09-19T00:00:00+00:00", "2026-09-19T00:00:00+00:00"))
    return s


def test_standard_er_normal(sid):
    assert hent_visning(sid) == "normal"
    assert vil_have_tanke_resume(sid) is False


def test_skift_til_thinking_huskes_og_taender_resumeet(sid):
    assert saet_visning(sid, "thinking")["status"] == "ok"
    assert hent_visning(sid) == "thinking"
    assert vil_have_tanke_resume(sid) is True


def test_verbose_laver_intet_resume(sid):
    saet_visning(sid, "verbose")
    assert vil_have_tanke_resume(sid) is False


def test_ukendt_visning_afvises(sid):
    svar = saet_visning(sid, "fuld")
    assert svar["status"] == "error" and "ukendt visning" in svar["error"]
    assert hent_visning(sid) == "normal"


def test_ukendt_samtale(isolated_runtime):
    assert saet_visning("findes-ikke", "thinking")["status"] == "error"
    assert hent_visning("findes-ikke") == "normal"
    assert vil_have_tanke_resume("findes-ikke") is False


def test_en_ugyldig_gemt_vaerdi_falder_tilbage_til_normal(sid):
    """Deres `Dt()`: en ukendt streng falder tilbage frem for at crashe."""
    hent_visning(sid)  # sikrer kolonnen
    with connect() as c:
        c.execute("UPDATE chat_sessions SET transcript_view = 'noget' WHERE session_id = ?", (sid,))
    assert hent_visning(sid) == "normal"


def test_ruten_afviser_en_andens_samtale(sid, monkeypatch):
    from fastapi import HTTPException
    from apps.api.jarvis_api.routes import chat_session_view as rute
    import core.services.chat_sessions as cs
    import core.identity.workspace_context as wc
    monkeypatch.setattr(cs, "get_session_owner", lambda s: "bruger-a")
    monkeypatch.setattr(wc, "current_user_id", lambda: "bruger-b")
    with pytest.raises(HTTPException) as e:
        rute.chat_set_session_view(sid, rute.SessionViewRequest(view="thinking"))
    assert e.value.status_code == 403
    assert hent_visning(sid) == "normal"


def test_ruten_saetter_for_ejeren(sid, monkeypatch):
    from apps.api.jarvis_api.routes import chat_session_view as rute
    import core.services.chat_sessions as cs
    import core.identity.workspace_context as wc
    monkeypatch.setattr(cs, "get_session_owner", lambda s: "bruger-a")
    monkeypatch.setattr(wc, "current_user_id", lambda: "bruger-a")
    assert rute.chat_set_session_view(sid, rute.SessionViewRequest(view="thinking"))["view"] == "thinking"
    assert rute.chat_session_view(sid)["view"] == "thinking"
