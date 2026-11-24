"""Chiffertekst maa ikke ende i deep-refleksionens prompt.

Maalt 24/11-2026: `recent_visible_runs` dekrypterer kun naar `user_id` sendes
med — `reveal_preview` returnerer ellers teksten uaendret. `deep_reflection_slot`
laeser uden `user_id`, saa en medlems-koersel gav `enc:...` direkte ind i
refleksions-prompten. Samme fejlklasse som dommeren der laeste base64 som svar.
"""
from __future__ import annotations

from datetime import UTC, datetime

import core.runtime.db as db_mod
from core.services import chat_crypto
from core.services import deep_reflection_slot as slot


def _raekke(preview: str) -> dict[str, object]:
    return {
        "started_at": datetime.now(UTC).isoformat(),
        "text_preview": preview,
        "lane": "visible",
        "status": "completed",
    }


def test_krypteret_preview_springes_over(monkeypatch):
    hemmelig = chat_crypto.krypter("Michelles private svar", "medlem-x")
    assert chat_crypto.er_krypteret(hemmelig), "forudsatning: teksten er krypteret"

    raekker = [_raekke(hemmelig), _raekke("et almindeligt svar")]
    monkeypatch.setattr(db_mod, "recent_visible_runs", lambda **kw: raekker)
    monkeypatch.setattr(db_mod, "list_private_brain_records", lambda **kw: [])

    samlet = "\n".join(slot._chronicle_summary())

    assert "et almindeligt svar" in samlet
    assert hemmelig[:40] not in samlet
    assert "enc:" not in samlet


def test_klartekst_bevares_uændret(monkeypatch):
    raekker = [_raekke("et helt almindeligt svar uden kryptering")]
    monkeypatch.setattr(db_mod, "recent_visible_runs", lambda **kw: raekker)
    monkeypatch.setattr(db_mod, "list_private_brain_records", lambda **kw: [])

    samlet = "\n".join(slot._chronicle_summary())

    assert "et helt almindeligt svar uden kryptering" in samlet
