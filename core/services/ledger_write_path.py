"""Skrivevejen for en session hvor LEDGEREN er sandheden.

Spec: Fase 1 — «only the projector can write compatibility rows for ledger
sessions».

## Hvad der vender om ved et skifte

For `legacy` og `shadow` skrives rækken i `chat_messages`, og ledgeren følger
efter (eller lader være). For `ledger` er det modsat: hændelsen skrives i
ledgeren, og RÆKKEN er noget projektoren laver bagefter. Ingen anden vej ind.

Det er hele forskellen på en tabel man skriver i, og en tabel man udleder.

## Hvorfor et handle og ikke bare et append

Skygge-skrivningen bruger `append_unowned` — én transaktion, ingen lease — og
det er rigtigt DÉR, fordi ledgeren ikke er sandheden og en forkert rækkefølge
kun bliver til en uenighed nogen opdager.

Her er den sandheden. En anden proces der skriver ind i den samme sekvens
samtidig, ville ikke give en uenighed man kan måle sig frem til; den ville give
en samtale hvor svaret kom før spørgsmålet, og ingen kopi at sammenligne med.
Derfor: lease, fencing-mønt, og en projektion der køres af handlet selv.

## Rækkefølgen er ikke til forhandling

    hændelse committes  →  projektor kører  →  rækken findes

Kalderen får først sin besked tilbage når rækken findes, for ellers ville et
kald kunne returnere en besked som ingen læser kan se endnu.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class LedgerWriteFailed(RuntimeError):
    """Skrivningen nåede ikke ledgeren. Kalderen har IKKE fået sin besked gemt."""


def append_message(session_id: str, *, role: str, content: str,
                   created_at: str | None = None, user_id: str = "",
                   workspace_name: str = "", reasoning_content: str = "",
                   git_sha: str = "", content_json: Any = None,
                   message_id: str | None = None,
                   owner: str = "chat") -> dict[str, Any]:
    """Skriv én besked gennem ledgeren og lad projektoren lave rækken.

    Kaster hvis skriveretten ikke kunne tages, eller hvis skrivningen fejlede.
    Det er MED VILJE anderledes end skygge-skrivningen: her er der ingen anden
    kopi af beskeden, så en tavs fejl ville være tabt data.
    """
    from core.runtime.session_handle import open_for_write

    sid = str(session_id or "").strip()
    mid = str(message_id or f"message-{uuid4().hex}")
    ts = str(created_at or datetime.now(UTC).isoformat())

    h = open_for_write(sid, owner=owner)
    if not h.writable:
        raise LedgerWriteFailed(
            f"kunne ikke tage skriveretten til {sid!r} "
            f"(format={h.format!r}) — en anden proces skriver, eller "
            "sessionen kan ikke skrives i sit format"
        )
    with h:
        h.append({
            "event_id": mid,
            "kind": "message",
            "payload": {
                "message_id": mid, "role": str(role), "content": str(content),
                "user_id": str(user_id or ""),
                "workspace_name": str(workspace_name or ""),
                "reasoning_content": str(reasoning_content or ""),
                "git_sha": str(git_sha or ""),
                "content_json": content_json, "created_at": ts,
            },
        })
        # `close()` flusher OG projicerer. Fejler flushen, kaster den — og det
        # skal den: kalderen har ingen anden kopi af beskeden.
    return {"message_id": mid, "created_at": ts, "role": str(role),
            "content": str(content)}
