"""`get_protected_inner_voice(offset=...)` — at kunne gå ét skridt tilbage.

Tilføjet 2026-09-05 fordi 1-2 % af de gemte `voice_line` er instruks-ekko
(«The user asks me to respond as Jarvis … as a JSON object») og [INDRE LIV]
altid viser den NYESTE. Uden offset ville en forurenet nyeste efterlade ham helt
uden stemme-linje; med den springer visningen videre til den seneste rene.
"""

from __future__ import annotations

import inspect

from core.runtime.db_private_notes import get_protected_inner_voice


def test_offset_er_et_keyword_argument():
    """Signaturen er kontrakten mod visible_inner_life._voice_line."""
    sig = inspect.signature(get_protected_inner_voice)
    assert "offset" in sig.parameters
    p = sig.parameters["offset"]
    assert p.kind is inspect.Parameter.KEYWORD_ONLY
    assert p.default == 0


def test_uden_argumenter_giver_den_nyeste():
    """Bagudkompatibilitet: alle eksisterende kaldesteder sender intet."""
    ud = get_protected_inner_voice()
    assert ud is None or isinstance(ud, dict)
    if isinstance(ud, dict):
        assert "voice_line" in ud and "created_at" in ud


def test_offset_flytter_baglaens_i_tid():
    """offset=1 må ikke give den samme række som offset=0."""
    nyeste = get_protected_inner_voice(offset=0)
    naeste = get_protected_inner_voice(offset=1)
    if nyeste is None or naeste is None:
        return  # tom tabel i dette miljø — intet at sammenligne
    assert nyeste.get("voice_id") != naeste.get("voice_id")
    if nyeste.get("created_at") and naeste.get("created_at"):
        assert str(nyeste["created_at"]) >= str(naeste["created_at"])


def test_negativ_offset_behandles_som_nul():
    """Et skævt kald må ikke give en SQL-fejl."""
    assert get_protected_inner_voice(offset=-5) == get_protected_inner_voice(offset=0)


def test_offset_ud_over_tabellen_giver_none():
    assert get_protected_inner_voice(offset=10_000_000) is None
