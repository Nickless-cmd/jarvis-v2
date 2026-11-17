"""Titel-læsningen må ikke læse samtalen — og de tre assembly-kaldere må ikke gøre det.

Målt 16-17/11-2026: `get_chat_session` kostede 214-318 ms pr. kald på sessioner med
8.000 beskeder, og prompt-assemblyen kaldte den tre gange pr. besked for at læse en titel.
"""
import sqlite3

import pytest

from core.services.chat_sessions import append_chat_message, create_chat_session
from core.services.session_header import get_session_title


def _fyld(session_id: str, n: int = 6) -> None:
    for i in range(n):
        append_chat_message(session_id=session_id, role="user" if i % 2 == 0 else "assistant",
                            content=f"besked {i}")


def test_titlen_laeses_og_ukendt_session_giver_none(isolated_runtime):
    s = create_chat_session(title="Discord DM")
    assert get_session_title(s["id"]) == "Discord DM"
    assert get_session_title("findes-ikke") is None
    assert get_session_title("") is None
    assert get_session_title(None) is None  # type: ignore[arg-type]


def test_samme_titel_som_get_chat_session_giver(isolated_runtime):
    """Titlen skal være BYTE-IDENTISK med den gamle vej, ellers skifter kanalen."""
    from core.services.chat_sessions import get_chat_session
    for titel in ("Discord DM", "Telegram #drift", "", "New chat"):
        s = create_chat_session(title=titel)
        _fyld(s["id"], 2)
        assert get_session_title(s["id"]) == get_chat_session(s["id"])["title"], titel


def test_titlen_laeses_uden_at_roere_besked_tabellen(isolated_runtime):
    """Fejler hvis nogen bytter den ud med get_chat_session: der SELECT'er fra chat_messages."""
    s = create_chat_session(title="Stor samtale")
    _fyld(s["id"], 30)
    set_ = []
    import core.services.session_header as mod
    orig = mod.connect

    class _Spor:
        def __init__(self, c): self._c = c
        def __enter__(self): self._conn = self._c.__enter__(); self._conn.set_trace_callback(set_.append); return self._conn
        def __exit__(self, *a): return self._c.__exit__(*a)

    mod.connect = lambda *a, **k: _Spor(orig(*a, **k))
    try:
        assert get_session_title(s["id"]) == "Stor samtale"
    finally:
        mod.connect = orig
    assert set_, "ingen SQL set"
    assert not any("chat_messages" in q for q in set_), set_


def test_kanal_sektionen_og_synlighedsloftet_kalder_ikke_get_chat_session(isolated_runtime, monkeypatch):
    """De to kaldere der kun skal bruge titlen må ikke betale for hele samtalen."""
    import core.services.chat_sessions as cs
    from core.services.prompt_sections.jarvis_brain_facts import _ceiling_from_session_id

    def _forbudt(*a, **k):
        raise AssertionError("get_chat_session kaldt — hele samtalen blev læst")

    # Sessionerne oprettes FØRST: create_chat_session kalder selv get_chat_session.
    web = create_chat_session(title="New chat")          # webchat -> ejerens egen flade
    discord = create_chat_session(title="Discord DM")    # parses som "discord" -> mindst privilegium
    ukendt = create_chat_session(title="Noget helt andet")
    monkeypatch.setattr(cs, "get_chat_session", _forbudt)
    assert _ceiling_from_session_id(web["id"]) == "intimate"
    assert _ceiling_from_session_id(discord["id"]) == "public_safe"
    assert _ceiling_from_session_id(ukendt["id"]) == "public_safe"
    assert _ceiling_from_session_id("findes-ikke") == "public_safe"


def test_recall_henter_ikke_samtalen_for_at_finde_brugeren(isolated_runtime, monkeypatch):
    import core.services.chat_sessions as cs
    from core.identity import owner_resolver
    from core.services.prompt_sections.memory_recall import _resolve_user_id

    s = create_chat_session(title="x")  # FØR patchen: oprettelsen læser selv samtalen
    monkeypatch.setattr(cs, "get_chat_session",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("hele samtalen læst")))
    monkeypatch.setattr(owner_resolver, "get_owner_discord_id", lambda: "4711")
    assert _resolve_user_id(s["id"]) == "4711"
    assert _resolve_user_id("") == "4711"
