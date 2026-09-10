"""Ét krav ad gangen, og en nedkoeling der overlever en genstart.

Kadence-producenterne vogtede sig selv med en MODUL-GLOBAL (`_last_run_at`).
To ting foelger af det, og begge bider i dette hus:

  * En genstart glemmer nedkoelingen. Producenten koerer igen med det samme,
    uanset hvor kort tid siden den koerte.
  * `jarvis-api` og `jarvis-runtime` koerer SAMME app, saa de har hver sin
    kopi af den globale. Begge kan koere den samme producent i samme minut.

Kravet ligger derfor i databasen. En LEASE med udloeb sikrer at en doed proces
ikke laaser producenten for evigt — det er samme afvejning som agenternes
proces-maerke: hellere give slip for tidligt end at haenge for altid.

EN FEJLET KOERSEL ER IKKE ET NEDKOELINGS-MAERKE. Kun et gennemfoert pas
saetter `last_success_at`. Ellers ville en producent der fejler hurtigt faa lov
at fejle igen og igen, mens en der fejler LANGSOMT ville blive holdt ude af sin
egen fejl.
"""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.runtime.db_core import connect

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ClaimResult:
    claimed: bool
    lease_token: str = ""
    reason: str = ""


def _ensure(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cadence_producer_claims (
            name TEXT PRIMARY KEY,
            lease_token TEXT NOT NULL DEFAULT '',
            leased_until TEXT NOT NULL DEFAULT '',
            last_success_at TEXT NOT NULL DEFAULT '',
            last_attempt_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cadence_idempotency_keys (
            scope TEXT NOT NULL,
            key TEXT NOT NULL,
            claimed_at TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (scope, key)
        )
        """
    )


def _dt(raa: object) -> datetime | None:
    t = str(raa or "").strip()
    if not t:
        return None
    try:
        d = datetime.fromisoformat(t.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=UTC)
    except Exception:
        return None


def claim_producer(name: str, *, cooldown_minutes: int, lease_seconds: int,
                   now: datetime | None = None) -> ClaimResult:
    """Tag kravet paa en producent, hvis den er moden og ledig."""
    n = str(name or "").strip()
    if not n:
        return ClaimResult(False, reason="name-required")
    nu = now or datetime.now(UTC)
    if nu.tzinfo is None:
        nu = nu.replace(tzinfo=UTC)
    try:
        with connect() as conn:
            _ensure(conn)
            r = conn.execute(
                "SELECT * FROM cadence_producer_claims WHERE name = ?", (n,)
            ).fetchone()

            if r is not None:
                sidst_ok = _dt(r["last_success_at"])
                if (sidst_ok is not None and cooldown_minutes > 0
                        and nu - sidst_ok < timedelta(minutes=int(cooldown_minutes))):
                    return ClaimResult(False, reason="cooldown-active")
                udloeb = _dt(r["leased_until"])
                if (str(r["lease_token"] or "") and udloeb is not None
                        and nu < udloeb):
                    return ClaimResult(False, reason="lease-held")

            polet = f"lease-{uuid4().hex}"
            indtil = (nu + timedelta(seconds=max(1, int(lease_seconds)))).isoformat()
            conn.execute(
                """
                INSERT INTO cadence_producer_claims (
                    name, lease_token, leased_until, last_success_at, last_attempt_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    lease_token = excluded.lease_token,
                    leased_until = excluded.leased_until,
                    last_attempt_at = excluded.last_attempt_at
                """,
                (n, polet, indtil,
                 str((r["last_success_at"] if r is not None else "") or ""),
                 nu.isoformat()),
            )
            conn.commit()
            return ClaimResult(True, lease_token=polet, reason="claimed")
    except Exception:
        # Kan vi ikke laese kravet, koerer vi IKKE. En producent der koerer
        # fordi vagten var utilgaengelig, er praecis det vagten skal forhindre.
        logger.warning("kunne ikke tage kadence-kravet %s", n, exc_info=True)
        return ClaimResult(False, reason="claim-unavailable")


def complete_producer(name: str, lease_token: str, *, succeeded: bool,
                      now: datetime | None = None) -> bool:
    """Giv kravet fri. KUN et gennemfoert pas saetter nedkoelings-maerket."""
    n = str(name or "").strip()
    polet = str(lease_token or "").strip()
    if not n or not polet:
        return False
    nu = (now or datetime.now(UTC))
    if nu.tzinfo is None:
        nu = nu.replace(tzinfo=UTC)
    try:
        with connect() as conn:
            _ensure(conn)
            r = conn.execute(
                "SELECT lease_token FROM cadence_producer_claims WHERE name = ?", (n,)
            ).fetchone()
            if r is None or str(r["lease_token"] or "") != polet:
                return False              # ikke indehaverens krav at give fri
            if succeeded:
                conn.execute(
                    "UPDATE cadence_producer_claims SET lease_token = '', "
                    "leased_until = '', last_success_at = ? WHERE name = ?",
                    (nu.isoformat(), n),
                )
            else:
                conn.execute(
                    "UPDATE cadence_producer_claims SET lease_token = '', "
                    "leased_until = '' WHERE name = ?", (n,),
                )
            conn.commit()
            return True
    except Exception:
        logger.warning("kunne ikke afslutte kadence-kravet %s", n, exc_info=True)
        return False


def claim_idempotency_key(scope: str, key: str, *,
                          now: datetime | None = None) -> bool:
    """Foerste kalder vinder. Returnerer False hvis noeglen er brugt foer."""
    s, k = str(scope or "").strip(), str(key or "").strip()
    if not s or not k:
        return False
    nu = (now or datetime.now(UTC))
    try:
        with connect() as conn:
            _ensure(conn)
            cur = conn.execute(
                "INSERT OR IGNORE INTO cadence_idempotency_keys (scope, key, claimed_at) "
                "VALUES (?, ?, ?)", (s, k, nu.isoformat()),
            )
            conn.commit()
            return cur.rowcount == 1
    except Exception:
        logger.warning("kunne ikke tage idempotens-noeglen %s/%s", s, k, exc_info=True)
        return False
