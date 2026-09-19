"""Enheder — hvem må styre denne computer, og hvem må bruge code mode.

Bjørn 19/9-2026 valgte fire ting fra Jarvis' kortlægning af Codex' fjernstyring
(codex-remote-control.md): et enhedsregister med fjernelse pr. enhed, code mode
der kræver en tilføjet enhed, «tillad på computeren først», og TOTP ved parring.
Codex binder adgangen til en *enrollment* — en post i en klientliste — ikke til
et token eller en proces, og en post kan fjernes for sig.

## To slags poster

- **telefon** — registreres når en parrings-kode indløses. Posten får et id, og
  det id står i telefonens token som claim `enhed`. Token-fornyelse bærer det
  videre (et `jti` skifter ved hver fornyelse og duer derfor ikke som nøgle).
  Fjernes en telefon, afvises dens tokens OVERALT med det samme
  (`jarvisx_auth.verify_token` slår `enhed` op her).
- **computer** — en desk-installation, genkendt på tokenets `app_id`. Registreres
  fra desk selv (med TOTP), og automatisk når reglen slås til. Fjernes en
  computer, lukker kun dens code mode — ikke hele desk, så man ikke kan låse sig
  selv ude af den app man retter det fra.

`jarvis-mobile` er telefonens `app_id` ved Google-login og kan ALDRIG blive en
computer: så kunne en telefon kalde sig desk.

## Reglen

`kraev_aktivt()` er et flag (runtime_state_kv). Slukket: alt som før. Tændt:
code mode kræver at tokenet matcher en aktiv post for samme bruger
(`maa_bruge_kode`). Tændes af ejeren fra desk — med TOTP.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from core.runtime.db import connect

__all__ = [
    "registrer_telefon", "registrer_computer", "liste", "fjern", "telefon_status",
    "maa_bruge_kode", "kraev_aktivt", "saet_kraev", "TELEFON_APP_ID",
]

TELEFON_APP_ID = "jarvis-mobile"
_KRAV_NOEGLE = "enheds_krav"


def _sikr(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS enheder ("
        "id TEXT PRIMARY KEY, user_id TEXT NOT NULL, type TEXT NOT NULL, "
        "noegle TEXT NOT NULL, navn TEXT NOT NULL DEFAULT '', platform TEXT NOT NULL DEFAULT '', "
        "oprettet REAL NOT NULL, sidst_set REAL NOT NULL DEFAULT 0, "
        "status TEXT NOT NULL DEFAULT 'aktiv')"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_enheder_bruger ON enheder(user_id, status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_enheder_noegle ON enheder(noegle)")


def _raekke(r) -> dict[str, Any]:
    return {"id": r[0], "user_id": r[1], "type": r[2], "navn": r[4], "platform": r[5],
            "oprettet": r[6], "sidst_set": r[7], "status": r[8]}


def registrer_telefon(user_id: str, *, navn: str = "", platform: str = "") -> dict[str, Any]:
    """En ny telefon. Id'et bliver tokenets `enhed`-claim."""
    uid = (user_id or "").strip()
    if not uid:
        raise ValueError("user_id mangler")
    eid = f"enh-{uuid.uuid4().hex[:16]}"
    nu = time.time()
    with connect() as conn:
        _sikr(conn)
        conn.execute(
            "INSERT INTO enheder (id, user_id, type, noegle, navn, platform, oprettet, sidst_set) "
            "VALUES (?, ?, 'telefon', ?, ?, ?, ?, ?)",
            (eid, uid, eid, (navn or "Telefon")[:80], (platform or "")[:40], nu, nu),
        )
    return {"id": eid, "type": "telefon", "navn": (navn or "Telefon")[:80]}


def registrer_computer(user_id: str, app_id: str, *, navn: str = "") -> dict[str, Any]:
    """En desk-installation. Idempotent pr. bruger og app_id (genaktiverer en fjernet)."""
    uid = (user_id or "").strip()
    aid = (app_id or "").strip()
    if not uid:
        raise ValueError("user_id mangler")
    if not aid or aid == TELEFON_APP_ID:
        raise ValueError("Denne klient er ikke en desk-installation (intet app_id)")
    nu = time.time()
    with connect() as conn:
        _sikr(conn)
        r = conn.execute(
            "SELECT id FROM enheder WHERE user_id = ? AND type = 'computer' AND noegle = ?", (uid, aid),
        ).fetchone()
        if r:
            conn.execute("UPDATE enheder SET status = 'aktiv', sidst_set = ? WHERE id = ?", (nu, r[0]))
            return {"id": r[0], "type": "computer", "navn": navn or "Computer"}
        eid = f"enh-{uuid.uuid4().hex[:16]}"
        conn.execute(
            "INSERT INTO enheder (id, user_id, type, noegle, navn, platform, oprettet, sidst_set) "
            "VALUES (?, ?, 'computer', ?, ?, 'desk', ?, ?)",
            (eid, uid, aid, (navn or "Computer")[:80], nu, nu),
        )
    return {"id": eid, "type": "computer", "navn": (navn or "Computer")[:80]}


def liste(user_id: str) -> list[dict[str, Any]]:
    """Brugerens aktive enheder, nyeste først."""
    with connect() as conn:
        _sikr(conn)
        rows = conn.execute(
            "SELECT id, user_id, type, noegle, navn, platform, oprettet, sidst_set, status "
            "FROM enheder WHERE user_id = ? AND status = 'aktiv' ORDER BY oprettet DESC",
            ((user_id or "").strip(),),
        ).fetchall()
    return [_raekke(r) for r in rows]


def fjern(enheds_id: str, user_id: str) -> bool:
    """Fjern én enhed — kun brugerens egen. En telefons tokens dør med det samme."""
    with connect() as conn:
        _sikr(conn)
        cur = conn.execute(
            "UPDATE enheder SET status = 'fjernet' WHERE id = ? AND user_id = ? AND status = 'aktiv'",
            ((enheds_id or "").strip(), (user_id or "").strip()),
        )
    return cur.rowcount == 1


def telefon_status(enheds_id: str) -> str | None:
    """'aktiv' / 'fjernet' for en telefon-post, None hvis ukendt."""
    eid = (enheds_id or "").strip()
    if not eid:
        return None
    with connect() as conn:
        _sikr(conn)
        r = conn.execute(
            "SELECT status FROM enheder WHERE id = ? AND type = 'telefon'", (eid,),
        ).fetchone()
    return str(r[0]) if r else None


def maa_bruge_kode(user_id: str, *, enhed: str = "", app_id: str = "") -> bool:
    """Matcher tokenet en AKTIV post for brugeren?"""
    uid = (user_id or "").strip()
    if not uid:
        return False
    with connect() as conn:
        _sikr(conn)
        if enhed:
            r = conn.execute(
                "SELECT 1 FROM enheder WHERE id = ? AND user_id = ? AND type = 'telefon' AND status = 'aktiv'",
                (enhed, uid),
            ).fetchone()
            if r:
                conn.execute("UPDATE enheder SET sidst_set = ? WHERE id = ?", (time.time(), enhed))
                return True
        if app_id and app_id != TELEFON_APP_ID:
            r = conn.execute(
                "SELECT id FROM enheder WHERE noegle = ? AND user_id = ? AND type = 'computer' AND status = 'aktiv'",
                (app_id, uid),
            ).fetchone()
            if r:
                conn.execute("UPDATE enheder SET sidst_set = ? WHERE id = ?", (time.time(), r[0]))
                return True
    return False


def kraev_aktivt() -> bool:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(_KRAV_NOEGLE, {})
        return isinstance(v, dict) and v.get("aktiv") is True
    except Exception:
        return False


def saet_kraev(aktiv: bool, *, af: str = "") -> None:
    from core.runtime.db_core import set_runtime_state_value
    set_runtime_state_value(_KRAV_NOEGLE, {"aktiv": bool(aktiv), "af": af, "tid": time.time()})
