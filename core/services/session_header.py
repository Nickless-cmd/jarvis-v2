"""Sessionens titel UDEN at læse samtalen.

Prompt-assemblyen skal bruge en samtales TITEL for at afgøre kanal og
synlighedsloft. Den hentede den med `get_chat_session`, som henter, dekrypterer
og parser HVER besked i samtalen — målt 16-17/11-2026 til 214-318 ms pr. kald
på de største sessioner (8.000 beskeder), og assemblyen kaldte den tre gange pr.
besked. Det er ca. 0,3-0,9 s ventetid pr. besked for at læse ét felt.

Vagten `scripts/verify_history_reads.py` forbyder allerede nye kaldere af
`get_chat_session`; her er den lette læsning den peger på for titlen.
"""
from __future__ import annotations

from core.runtime.db import connect
from core.services.chat_session_private_metadata import decrypt_session_text


def get_session_title(session_id: str) -> str | None:
    """Den læsbare titel, eller ``None`` når sessionen ikke findes.

    Samme tekst som `get_chat_session(...)["title"]`: en tom titel hedder
    «New chat», og en krypteret titel dekrypteres. Én rækkes læsning, ingen
    beskeder.
    """
    sid = (session_id or "").strip()
    if not sid:
        return None
    with connect() as conn:
        row = conn.execute(
            "SELECT title FROM chat_sessions WHERE session_id = ?", (sid,)
        ).fetchone()
    if row is None:
        return None
    return decrypt_session_text(str(row[0] or "New chat"), sid)
