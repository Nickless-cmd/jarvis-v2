"""Append-only session-ledger — Fase 1 af DeepSeek-harness-spec'en.

Domæne: `session_events` (turens kanoniske hændelser) og
`session_write_leases` (hvem der må skrive til én session lige nu).

Spec: `docs/specs/2026-09-08-deepseek-harness-lessons-for-jarvis.md`, Fase 1.
Inventar: `docs/specs/2026-09-08-phase0-source-of-truth-inventory.md`.

## Hvorfor en ledger ved siden af `chat_messages`

`chat_messages` er i dag kanonisk og har PRÆCIS ÉN skrivende fil (målt 8/9-2026).
Det er en god udgangsposition, men rækkerne er en TILSTAND, ikke en historik: de
kan opdateres, og der er ingen rækkefølge man kan afspille. Ledgeren tilføjer det
der mangler — én uforanderlig, nummereret hændelsesrække pr. session.

`events`-tabellen kunne ikke bruges: den er telemetri og beskæres efter 14 dage
(`events_retention.py` kalder den selv «the unbounded events telemetry table»).
En tabel der beskæres kan ikke være kanonisk.

## De tre invarianter

1. **Sekvensen er tæt og pr. session.** `seq` starter på 1 og har ingen huller.
   Uden det kan man ikke afgøre om man har hele historikken.

2. **Append er idempotent på `event_id`.** Samme hændelse leveret to gange —
   ved gentagelse, genstart eller dobbelt-levering — giver ÉN række. Uden det
   ville en genafspilning fordoble turen.

3. **Kun lease-ejeren må skrive, og kun med sin egen mønt.** Et `fencing_token`
   stiger monotont pr. erhvervelse. Mister man leasen og skriver bagefter med
   sin gamle mønt, afvises skrivningen — også selvom man tror man stadig ejer
   sessionen. Det er forskellen på en lås og en lease: en lås kan man tro man
   har; en mønt kan man vise at man har.

Læsning kræver INGEN lease. En læser må aldrig kunne blokere en skriver, og en
skrivebeskyttet inspektion må aldrig efterlade spor.
"""
from __future__ import annotations

import json as _json
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.db_core import (
    _install_ensure_once_cache_for,
    connect,
)

#: Hvor længe en lease holder uden fornyelse. Kort nok til at en død proces
#: ikke spærrer en session i timevis; langt nok til at et almindeligt langt run
#: ikke taber den under sig.
DEFAULT_LEASE_TTL_S = 300


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _ensure_session_ledger_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS session_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            seq INTEGER NOT NULL,
            event_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(session_id, seq),
            UNIQUE(session_id, event_id)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_session_events_sid_seq "
        "ON session_events(session_id, seq)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS session_write_leases (
            session_id TEXT PRIMARY KEY,
            owner TEXT NOT NULL,
            fencing_token INTEGER NOT NULL,
            acquired_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
        """
    )


# ── lease ────────────────────────────────────────────────────────────────

def acquire_write_lease(
    session_id: str, *, owner: str, ttl_s: int = DEFAULT_LEASE_TTL_S,
    now: datetime | None = None,
) -> int | None:
    """Tag skrive-ejerskabet over én session. Returnér møntet, eller None.

    Møntet stiger MONOTONT for sessionen — også når en udløbet lease overtages.
    Det er dét der gør en gammel ejer harmløs: hans mønt er mindre end den
    nuværende, og hans skrivninger afvises uden at han behøver opdage det selv.
    """
    sid = str(session_id or "").strip()
    ejer = str(owner or "").strip()
    if not sid or not ejer:
        return None
    nu = now or _now()
    with connect() as conn:
        _ensure_session_ledger_table(conn)
        row = conn.execute(
            "SELECT owner, fencing_token, expires_at FROM session_write_leases "
            "WHERE session_id = ?", (sid,),
        ).fetchone()
        if row is not None:
            nuv_ejer, mont, udloeb = str(row[0]), int(row[1]), str(row[2])
            aktiv = _parse(udloeb) > nu
            if aktiv and nuv_ejer != ejer:
                return None                     # en anden ejer den lige nu
            ny_mont = mont if (aktiv and nuv_ejer == ejer) else mont + 1
            conn.execute(
                "UPDATE session_write_leases SET owner = ?, fencing_token = ?, "
                "acquired_at = ?, expires_at = ? WHERE session_id = ?",
                (ejer, ny_mont, _iso(nu), _iso(nu + timedelta(seconds=ttl_s)), sid),
            )
            return ny_mont
        conn.execute(
            "INSERT INTO session_write_leases "
            "(session_id, owner, fencing_token, acquired_at, expires_at) "
            "VALUES (?, ?, 1, ?, ?)",
            (sid, ejer, _iso(nu), _iso(nu + timedelta(seconds=ttl_s))),
        )
        return 1


def release_write_lease(session_id: str, *, owner: str, token: int) -> bool:
    """Giv ejerskabet fra sig. Kun den nuværende ejer med den rigtige mønt kan.

    Idempotent: at slippe noget man ikke ejer er ikke en fejl, det er en no-op.
    """
    sid = str(session_id or "").strip()
    with connect() as conn:
        _ensure_session_ledger_table(conn)
        cur = conn.execute(
            "DELETE FROM session_write_leases WHERE session_id = ? AND owner = ? "
            "AND fencing_token = ?", (sid, str(owner or ""), int(token)),
        )
        return cur.rowcount > 0


def lease_state(session_id: str) -> dict[str, Any] | None:
    """Diagnostik: hvem ejer sessionen, med hvilken mønt, hvor længe."""
    with connect() as conn:
        _ensure_session_ledger_table(conn)
        row = conn.execute(
            "SELECT owner, fencing_token, acquired_at, expires_at "
            "FROM session_write_leases WHERE session_id = ?",
            (str(session_id or ""),),
        ).fetchone()
    if row is None:
        return None
    return {
        "owner": str(row[0]), "fencing_token": int(row[1]),
        "acquired_at": str(row[2]), "expires_at": str(row[3]),
    }


# ── append ───────────────────────────────────────────────────────────────

class LeaseLost(RuntimeError):
    """Skrivningen blev afvist: leasen er væk eller møntet er forældet."""


def append_session_events(
    session_id: str, *, owner: str, token: int, events: list[dict[str, Any]],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Tilføj hændelser ATOMISK og IDEMPOTENT.

    Enten lander hele batchen, eller også lander intet — en halv tur i ledgeren
    er værre end ingen, fordi den ser komplet ud.

    Allerede kendte `event_id`'er springes over uden at bryde batchen; det er
    dét der gør en genlevering harmløs. Returnerer hvor mange der blev skrevet,
    hvor mange der var kendt i forvejen, og sessionens nye sekvens.

    Rejser `LeaseLost` hvis møntet ikke er det nuværende. Tjekket sker INDE i
    transaktionen, så en lease der skifter ejer midt i en skrivning ikke kan
    smutte forbi.
    """
    sid = str(session_id or "").strip()
    if not sid:
        raise ValueError("session_id påkrævet")
    if not events:
        return {"written": 0, "duplicates": 0, "seq": current_seq(sid)}
    nu = now or _now()
    with connect() as conn:
        _ensure_session_ledger_table(conn)
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute(
                "SELECT owner, fencing_token, expires_at FROM session_write_leases "
                "WHERE session_id = ?", (sid,),
            ).fetchone()
            if row is None:
                raise LeaseLost(f"ingen lease på {sid}")
            if str(row[0]) != str(owner) or int(row[1]) != int(token):
                raise LeaseLost(
                    f"forældet mønt: {token} mod nuværende {row[1]} (ejer {row[0]})"
                )
            if _parse(str(row[2])) <= nu:
                raise LeaseLost(f"leasen på {sid} er udløbet")

            seq = int(conn.execute(
                "SELECT COALESCE(MAX(seq), 0) FROM session_events WHERE session_id = ?",
                (sid,),
            ).fetchone()[0])
            skrevet = dubletter = 0
            for e in events:
                eid = str(e.get("event_id") or "").strip()
                if not eid:
                    raise ValueError("hver hændelse skal have et event_id")
                findes = conn.execute(
                    "SELECT 1 FROM session_events WHERE session_id = ? AND event_id = ?",
                    (sid, eid),
                ).fetchone()
                if findes is not None:
                    dubletter += 1
                    continue
                seq += 1
                conn.execute(
                    "INSERT INTO session_events "
                    "(session_id, seq, event_id, kind, payload_json, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (sid, seq, eid, str(e.get("kind") or "event"),
                     _json.dumps(e.get("payload") or {}, ensure_ascii=False), _iso(nu)),
                )
                skrevet += 1
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    return {"written": skrevet, "duplicates": dubletter, "seq": seq}


# ── læsning (ingen lease) ────────────────────────────────────────────────

def read_session_events(
    session_id: str, *, from_seq: int = 0, to_seq: int | None = None,
) -> list[dict[str, Any]]:
    """Læs hændelser i rækkefølge. Halvåbent interval: (from_seq, to_seq].

    Kræver INGEN lease og skriver ingenting — en skrivebeskyttet inspektion må
    aldrig efterlade spor, heller ikke en oprettet tabel-række.
    """
    sid = str(session_id or "").strip()
    sql = ("SELECT seq, event_id, kind, payload_json, created_at FROM session_events "
           "WHERE session_id = ? AND seq > ?")
    args: list[Any] = [sid, int(from_seq)]
    if to_seq is not None:
        sql += " AND seq <= ?"
        args.append(int(to_seq))
    sql += " ORDER BY seq"
    with connect() as conn:
        _ensure_session_ledger_table(conn)
        rows = conn.execute(sql, tuple(args)).fetchall()
    ud: list[dict[str, Any]] = []
    for r in rows:
        try:
            payload = _json.loads(str(r[3]))
        except Exception:
            payload = {}
        ud.append({"seq": int(r[0]), "event_id": str(r[1]), "kind": str(r[2]),
                   "payload": payload, "created_at": str(r[4])})
    return ud


def current_seq(session_id: str) -> int:
    """Sessionens højeste sekvensnummer — 0 hvis ledgeren er tom for den."""
    with connect() as conn:
        _ensure_session_ledger_table(conn)
        row = conn.execute(
            "SELECT COALESCE(MAX(seq), 0) FROM session_events WHERE session_id = ?",
            (str(session_id or ""),),
        ).fetchone()
    return int(row[0]) if row else 0


def _parse(value: str) -> datetime:
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return datetime.min.replace(tzinfo=UTC)


_install_ensure_once_cache_for(__name__)


# ── storage_mode: hvilken kilde er kanonisk for denne session ────────────
#
# KOLONNE-EJERSKAB. `chat_sessions` skrives af `core/services/chat_sessions.py`
# (og af `security_guard.py`, der ejer `locked*`-kolonnerne). Dette modul ejer
# ÉN kolonne — `storage_mode` — og rører ingen andre. Det er samme mønster som
# inventaret allerede registrerede for security_guard: delt tabel, disjunkte
# kolonner, erklæret.
#
# Kolonnen bor på sessions-rækken frem for i en sidetabel, fordi en session så
# ikke KAN findes uden en tilstand. En sidetabel kunne drive fra rækken, og et
# spørgsmål om «hvad er sandheden for denne session» må ikke kunne have to svar.

#: Rækkefølgen ER kontrakten: man kan kun rykke fremad.
STORAGE_MODES = ("legacy", "shadow", "ledger")


def _ensure_storage_mode_column(conn: sqlite3.Connection) -> None:
    kolonner = {str(r[1]) for r in conn.execute("PRAGMA table_info(chat_sessions)")}
    if "storage_mode" not in kolonner:
        conn.execute(
            "ALTER TABLE chat_sessions ADD COLUMN storage_mode TEXT NOT NULL "
            "DEFAULT 'legacy'"
        )


def storage_mode(session_id: str) -> str:
    """Hvilken kilde er kanonisk for denne session?

    `legacy` — `chat_messages` er sandheden (alle sessioner i dag).
    `shadow` — der skrives BEGGE steder; ledgeren sammenlignes, men afgør intet.
    `ledger` — `session_events` er sandheden; `chat_messages` er en projektion.

    En ukendt session er `legacy`. Det er det sikre svar: en tom ledger må
    aldrig kunne læses som «der er ingen historik».
    """
    with connect() as conn:
        _ensure_storage_mode_column(conn)
        row = conn.execute(
            "SELECT storage_mode FROM chat_sessions WHERE session_id = ?",
            (str(session_id or ""),),
        ).fetchone()
    if row is None or not str(row[0] or "").strip():
        return "legacy"
    mode = str(row[0]).strip()
    return mode if mode in STORAGE_MODES else "legacy"


def advance_storage_mode(session_id: str, *, to: str) -> bool:
    """Ryk EN session fremad. Envejs — der er ingen vej tilbage.

    Skiftet er envejs fordi et tilbageskift ville gøre allerede committede
    ledger-hændelser til noget der skal genfortolkes. Spec'ens Fase 1-kriterium
    siger det direkte: «rollback does not reinterpret or delete committed ledger
    events». At forbyde vejen tilbage er billigere end at kunne gå den sikkert.

    Returnerer False hvis skiftet ville gå baglæns, sidelæns eller til en ukendt
    tilstand — uden at ændre noget.
    """
    sid = str(session_id or "").strip()
    maal = str(to or "").strip()
    if not sid or maal not in STORAGE_MODES:
        return False
    nu = storage_mode(sid)
    if STORAGE_MODES.index(maal) <= STORAGE_MODES.index(nu):
        return False
    with connect() as conn:
        _ensure_storage_mode_column(conn)
        cur = conn.execute(
            "UPDATE chat_sessions SET storage_mode = ? WHERE session_id = ?",
            (maal, sid),
        )
        return cur.rowcount > 0
