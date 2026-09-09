"""Drift-detektion — er ledgeren og `chat_messages` enige?

Spec: Fase 1, «drift detection reports no mismatch for canary fixtures».

## Hvad skygge-tilstanden er til for

I `shadow` skrives der BEGGE steder, og ledgeren afgør ingenting. Det er kun
værd at gøre hvis nogen faktisk SAMMENLIGNER. Uden en sammenligning er skyggen
bare dobbelt arbejde der giver falsk tryghed: man har skrevet begge steder i
uger og ved stadig ikke om de er enige.

Derfor er dette den funktion der bestemmer om et skifte må ske. Kriteriet er
ikke «ledgeren virker» — det er «ledgeren giver PRÆCIS det samme».

## Hvad der sammenlignes, og hvad der ikke gør

Sammenligningen sker på det der udgør samtalen: rolle, indhold, ræsonnement,
`content_json` og tidsstemplet — i rækkefølge. Alt det Fase 0 fandt at læserne
faktisk bruger.

`message_id` sammenlignes IKKE. Det oprindelige skrive-kald finder sit id med
`uuid4()`, projektoren udleder sit af hændelsen — de kan aldrig blive ens, og
skulle heller ikke: id'et er en nøgle, ikke indhold. At kræve dem ens ville
gøre hver eneste session til en falsk uenighed og dermed gøre målingen
værdiløs.

## Den må ikke skrive noget

En sammenligning der ændrer det den måler, måler ikke. Derfor folder den til
en SIDESTILLET udregning i hukommelsen frem for at køre projektoren — at kalde
projektoren ville skrive rækkerne den skal sammenlignes med.
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

#: Felterne der udgør samtalen. `message_id` står bevidst ikke her.
SAMMENLIGNES = ("role", "content", "reasoning_content", "content_json", "created_at")


def _normaliser_json(v: Any) -> str:
    """`content_json` kan være tekst ét sted og et objekt et andet. Det er
    ikke uenighed om INDHOLD, kun om form — så begge sider måles som tekst
    med samme nøglerækkefølge."""
    if v in (None, ""):
        return ""
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except Exception:
            return v
    try:
        return json.dumps(v, ensure_ascii=False, sort_keys=True)
    except Exception:
        return str(v)


def _felt(raekke: dict[str, Any], navn: str) -> str:
    if navn == "content_json":
        return _normaliser_json(raekke.get(navn))
    return str(raekke.get(navn) or "")


def _fra_ledger(session_id: str) -> list[dict[str, Any]]:
    """Fold i HUKOMMELSEN. At kalde projektoren ville skrive de rækker vi
    netop skal sammenligne med — og så målte vi vores eget svar."""
    from core.runtime.db_session_ledger import read_session_events
    from core.services.projection_chat_messages import _raekke, valider

    ud: list[dict[str, Any]] = []
    for e in read_session_events(session_id):
        if str(e.get("kind") or "") != "message":
            continue
        if valider(e.get("payload") or {}) is not None:
            continue
        ud.append(_raekke(str(e["session_id"]), e))
    return ud


def _fra_tabellen(session_id: str) -> list[dict[str, Any]]:
    from core.runtime.db import connect
    with connect() as conn:
        rows = conn.execute(
            "SELECT role, content, reasoning_content, content_json, created_at "
            "FROM chat_messages WHERE session_id = ? AND role != 'compact_marker' "
            "ORDER BY id", (str(session_id or ""),),
        ).fetchall()
    return [{"role": r[0], "content": r[1], "reasoning_content": r[2],
             "content_json": r[3], "created_at": r[4]} for r in rows]


def compare(session_id: str) -> dict[str, Any]:
    """Sammenlign de to sider. `enige` er svaret på om sessionen må skifte.

    Uenigheder returneres HVER FOR SIG med position og felt. En bool alene
    ville sige at noget er galt uden at sige hvad — og så bliver den ignoreret.
    """
    ledger = _fra_ledger(session_id)
    tabel = _fra_tabellen(session_id)

    uenigheder: list[dict[str, Any]] = []
    for i in range(max(len(ledger), len(tabel))):
        a = ledger[i] if i < len(ledger) else None
        b = tabel[i] if i < len(tabel) else None
        if a is None:
            uenigheder.append({"plads": i, "felt": "*", "ledger": None,
                               "tabel": _felt(b, "role")})
            continue
        if b is None:
            uenigheder.append({"plads": i, "felt": "*", "ledger": _felt(a, "role"),
                               "tabel": None})
            continue
        for f in SAMMENLIGNES:
            if _felt(a, f) != _felt(b, f):
                uenigheder.append({"plads": i, "felt": f,
                                   "ledger": _felt(a, f)[:200],
                                   "tabel": _felt(b, f)[:200]})

    return {
        "session_id": str(session_id),
        "enige": not uenigheder,
        "ledger_beskeder": len(ledger),
        "tabel_beskeder": len(tabel),
        "uenigheder": uenigheder,
    }


def may_cut_over(session_id: str) -> tuple[bool, str]:
    """Må denne session skifte til `ledger`?

    Tre ting skal holde, og de er alle tre negative erfaringer:

    * Ledgeren må ikke være TOM. En tom ledger og en tom sammenligning ser ens
      ud — og et skifte dér ville gøre en samtale til ingenting.
    * Siderne skal være enige.
    * Sessionen skal allerede være i `shadow`. Et spring direkte fra `legacy`
      ville betyde at ledgeren aldrig har været prøvet mod virkeligheden.
    """
    from core.runtime.db_session_ledger import storage_mode

    mode = storage_mode(session_id)
    if mode != "shadow":
        return False, f"sessionen er {mode!r}, ikke 'shadow'"
    r = compare(session_id)
    if r["ledger_beskeder"] == 0:
        return False, "ledgeren er tom — en tom sammenligning beviser ingenting"
    if not r["enige"]:
        return False, f"{len(r['uenigheder'])} uenighed(er), første: {r['uenigheder'][0]}"
    return True, f"{r['ledger_beskeder']} beskeder, ingen uenigheder"
