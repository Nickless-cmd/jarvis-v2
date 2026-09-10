"""Hvilken model SVAREDE — ikke hvilken vi bad om.

En udbyder kan svare med en anden model end den man beder om: et alias der
peger et nyt sted, en stille opgradering, en faldback. Beder man om
`deepseek-chat` og faar `deepseek-flash`, er alt hvad runtimen «ved» om sin
egen model foraeldet uden at nogen har aendret noget — og det er praecis den
slags skift der ellers foerst opdages som «han opfoerer sig anderledes i dag».

EPOKER, IKKE EN TAELLER. Den samme observation gentaget hundrede gange er ét
faktum om verden; en AENDRING er en begivenhed. Derfor gemmes skiftene, ikke
maengden — men taellingen foelger med, saa man kan se hvor godt et faktum er
understoettet.

BEVIS-BUNDET, som resten af verdens-modellen: er der ingen model i svaret, er
der intet observeret, og der opstaar ingen epoke. Fravaer er ikke en
observation, og en tom streng er ikke et modelnavn.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.runtime.db_core import connect

logger = logging.getLogger(__name__)


def _ensure(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS provider_model_epochs (
            epoch_id TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            requested_model TEXT NOT NULL,
            observed_model TEXT NOT NULL,
            previous_observed_model TEXT NOT NULL DEFAULT '',
            mismatch INTEGER NOT NULL DEFAULT 0,
            observation_count INTEGER NOT NULL DEFAULT 0,
            first_seen_at TEXT NOT NULL DEFAULT '',
            last_seen_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_pme_lookup "
        "ON provider_model_epochs (provider, requested_model, last_seen_at DESC)"
    )


def _row(r: sqlite3.Row | None) -> dict[str, Any] | None:
    if r is None:
        return None
    return {
        "epoch_id": str(r["epoch_id"]),
        "provider": str(r["provider"]),
        "requested_model": str(r["requested_model"]),
        "observed_model": str(r["observed_model"]),
        "previous_observed_model": str(r["previous_observed_model"] or ""),
        "mismatch": bool(r["mismatch"]),
        "observation_count": int(r["observation_count"] or 0),
        "first_seen_at": str(r["first_seen_at"] or ""),
        "last_seen_at": str(r["last_seen_at"] or ""),
    }


def current_model_epoch(*, provider: str, requested_model: str) -> dict[str, Any] | None:
    """Den epoke der gaelder nu, eller `None` hvis vi aldrig har observeret noget.

    `None` betyder «vi ved det ikke» — ikke «ingen model». Kalderen skal kunne
    skelne, ellers bliver uvidenhed til en paastand.
    """
    p, m = str(provider or "").strip(), str(requested_model or "").strip()
    if not p and not m:
        return None
    try:
        with connect() as conn:
            _ensure(conn)
            return _row(conn.execute(
                "SELECT * FROM provider_model_epochs "
                "WHERE provider = ? AND requested_model = ? "
                "ORDER BY last_seen_at DESC, rowid DESC LIMIT 1",
                (p, m),
            ).fetchone())
    except Exception:
        logger.warning("kunne ikke laese model-epoke", exc_info=True)
        return None


def record_model_observation(*, provider: str, requested_model: str,
                             observed_model: str) -> dict[str, Any] | None:
    """Bogfoer hvad udbyderen FAKTISK svarede med.

    Returnerer epoken — den gaeldende hvis intet aendrede sig, en ny hvis
    modellen skiftede. `None` naar der intet blev observeret.
    """
    p = str(provider or "").strip()
    m = str(requested_model or "").strip()
    o = str(observed_model or "").strip()
    if not o:
        return None                     # fravaer er ikke en observation
    nu = datetime.now(UTC).isoformat()
    try:
        with connect() as conn:
            _ensure(conn)
            nuv = _row(conn.execute(
                "SELECT * FROM provider_model_epochs "
                "WHERE provider = ? AND requested_model = ? "
                "ORDER BY last_seen_at DESC, rowid DESC LIMIT 1",
                (p, m),
            ).fetchone())

            if nuv is not None and nuv["observed_model"] == o:
                conn.execute(
                    "UPDATE provider_model_epochs "
                    "SET observation_count = observation_count + 1, last_seen_at = ? "
                    "WHERE epoch_id = ?",
                    (nu, nuv["epoch_id"]),
                )
                conn.commit()
                nuv["observation_count"] += 1
                nuv["last_seen_at"] = nu
                return nuv

            ny = {
                "epoch_id": f"epoch-{uuid4().hex}",
                "provider": p, "requested_model": m, "observed_model": o,
                "previous_observed_model": (nuv or {}).get("observed_model", ""),
                "mismatch": bool(m and o and m != o),
                "observation_count": 1,
                "first_seen_at": nu, "last_seen_at": nu,
            }
            conn.execute(
                "INSERT INTO provider_model_epochs (epoch_id, provider, "
                "requested_model, observed_model, previous_observed_model, "
                "mismatch, observation_count, first_seen_at, last_seen_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ny["epoch_id"], p, m, o, ny["previous_observed_model"],
                 int(ny["mismatch"]), 1, nu, nu),
            )
            conn.commit()
            if ny["previous_observed_model"]:
                logger.info("model-epoke skiftede for %s/%s: %s -> %s",
                            p, m, ny["previous_observed_model"], o)
            return ny
    except Exception:
        # En observation maa aldrig kunne vaelte den tur der frembragte den.
        logger.warning("kunne ikke bogfoere model-observation", exc_info=True)
        return None
