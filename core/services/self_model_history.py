"""Selv-modellens oejebliksbilleder, versioneret saa de kan SAMMENLIGNES.

`record_private_self_model` skrev ét billede ad gangen: uden nummer, uden
kaede tilbage til det forrige, og uden en maade at se hvad der aendrede sig.
Et selvbillede man ikke kan holde op mod gaarsdagens er en paastand, ikke en
historie — man kan laese hvad Jarvis mener om sig selv i dag, men ikke om det
er nyt, og ikke hvad der fik det til at skifte.

TRE VALG BAERER RESTEN:

  * VERSIONER ER MONOTONE, og hvert billede peger paa sin forgaenger. Uden
    kaeden kan man ikke sige «dette afloeste hint».
  * INDHOLDS-HASHEN ER DETERMINISTISK, saa «intet aendrede sig» kan afgoeres
    uden at laese teksten.
  * ET NYT BILLEDE MED SAMME INDHOLD ER IKKE EN AENDRING. En kadence der
    koerer hver time ville ellers producere 24 «aendringer» om dagen og
    drukne de aegte.

Og proveniensen foelger med — koersel, model-epoke, hvad der udloeste den. Et
selvbillede uden spor tilbage kan man ikke stille sig kritisk over for.
"""
from __future__ import annotations

import hashlib
import logging
import sqlite3
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.runtime.db_core import connect

logger = logging.getLogger(__name__)

#: Felterne der UDGOER selvbilledet. Hashen daekker praecis disse — ikke
#: tidsstempler, ikke id'er — saa to billeder med samme indhold er ens.
INDHOLDSFELTER = (
    "identity_focus",
    "preferred_work_mode",
    "recurring_tension",
    "growth_direction",
    "confidence",
)


def _ensure(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS self_model_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            version INTEGER NOT NULL,
            previous_snapshot_id TEXT NOT NULL DEFAULT '',
            content_hash TEXT NOT NULL DEFAULT '',
            identity_focus TEXT NOT NULL DEFAULT '',
            preferred_work_mode TEXT NOT NULL DEFAULT '',
            recurring_tension TEXT NOT NULL DEFAULT '',
            growth_direction TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT '',
            source_run_id TEXT NOT NULL DEFAULT '',
            model_epoch_id TEXT NOT NULL DEFAULT '',
            producer_trigger TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_sms_version "
        "ON self_model_snapshots (version DESC)"
    )


def content_hash(felter: dict[str, Any]) -> str:
    """Deterministisk hash over INDHOLDET alene."""
    raa = "\x1f".join(str(felter.get(k) or "").strip() for k in INDHOLDSFELTER)
    return hashlib.sha256(raa.encode("utf-8")).hexdigest()[:16]


def _row(r: sqlite3.Row) -> dict[str, Any]:
    return {
        "snapshot_id": str(r["snapshot_id"]),
        "version": int(r["version"]),
        "previous_snapshot_id": str(r["previous_snapshot_id"] or ""),
        "content_hash": str(r["content_hash"] or ""),
        **{k: str(r[k] or "") for k in INDHOLDSFELTER},
        "source": str(r["source"] or ""),
        "source_run_id": str(r["source_run_id"] or ""),
        "model_epoch_id": str(r["model_epoch_id"] or ""),
        "producer_trigger": str(r["producer_trigger"] or ""),
        "created_at": str(r["created_at"] or ""),
    }


def record_self_model_snapshot(
    *,
    identity_focus: str,
    preferred_work_mode: str,
    recurring_tension: str,
    growth_direction: str,
    confidence: str,
    source: str = "",
    source_run_id: str = "",
    model_epoch_id: str = "",
    producer_trigger: str = "",
    created_at: str = "",
) -> dict[str, Any]:
    """Skriv ét billede og kaed det til det forrige."""
    felter = {
        "identity_focus": identity_focus,
        "preferred_work_mode": preferred_work_mode,
        "recurring_tension": recurring_tension,
        "growth_direction": growth_direction,
        "confidence": confidence,
    }
    nu = created_at or datetime.now(UTC).isoformat()
    with connect() as conn:
        _ensure(conn)
        forrige = conn.execute(
            "SELECT snapshot_id, version FROM self_model_snapshots "
            "ORDER BY version DESC LIMIT 1"
        ).fetchone()
        version = int(forrige["version"]) + 1 if forrige else 1
        billede = {
            "snapshot_id": f"self-{uuid4().hex}",
            "version": version,
            "previous_snapshot_id": str(forrige["snapshot_id"]) if forrige else "",
            "content_hash": content_hash(felter),
            **{k: str(v or "").strip() for k, v in felter.items()},
            "source": str(source or ""),
            "source_run_id": str(source_run_id or ""),
            "model_epoch_id": str(model_epoch_id or ""),
            "producer_trigger": str(producer_trigger or ""),
            "created_at": nu,
        }
        conn.execute(
            "INSERT INTO self_model_snapshots (snapshot_id, version, "
            "previous_snapshot_id, content_hash, identity_focus, "
            "preferred_work_mode, recurring_tension, growth_direction, "
            "confidence, source, source_run_id, model_epoch_id, "
            "producer_trigger, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            tuple(billede[k] for k in (
                "snapshot_id", "version", "previous_snapshot_id", "content_hash",
                *INDHOLDSFELTER, "source", "source_run_id", "model_epoch_id",
                "producer_trigger", "created_at")),
        )
        conn.commit()
    return billede


def list_self_model_snapshots(*, limit: int = 20, before: str = "",
                              after: str = "") -> list[dict[str, Any]]:
    """Nyeste foerst. `before`/`after` afgraenser paa tidsstempel."""
    q = ["SELECT * FROM self_model_snapshots WHERE 1=1"]
    p: list[Any] = []
    if str(before or "").strip():
        q.append("AND created_at < ?")
        p.append(str(before).strip())
    if str(after or "").strip():
        q.append("AND created_at > ?")
        p.append(str(after).strip())
    q.append("ORDER BY version DESC LIMIT ?")
    p.append(max(1, int(limit)))
    with connect() as conn:
        _ensure(conn)
        return [_row(r) for r in conn.execute("\n".join(q), tuple(p)).fetchall()]


def compare_self_model_snapshots(older_id: str, newer_id: str) -> dict[str, Any]:
    """Hvad aendrede sig mellem to billeder?

    `changed=None` naar sammenligningen ikke KAN laves. En umulig
    sammenligning maa ikke se ud som «ingen aendring» — det er forskellen paa
    at vide at intet skete og ikke at vide noget.
    """
    with connect() as conn:
        _ensure(conn)
        raekker = {
            str(r["snapshot_id"]): _row(r)
            for r in conn.execute(
                "SELECT * FROM self_model_snapshots WHERE snapshot_id IN (?, ?)",
                (str(older_id or ""), str(newer_id or "")),
            ).fetchall()
        }
    a, b = raekker.get(str(older_id or "")), raekker.get(str(newer_id or ""))
    if a is None or b is None:
        mangler = [i for i, v in ((older_id, a), (newer_id, b)) if v is None]
        return {"changed": None, "changed_fields": [], "fields": {},
                "reason": f"ukendt oejebliksbillede: {', '.join(map(str, mangler))}"}
    forskelle = {k: {"from": a[k], "to": b[k]}
                 for k in INDHOLDSFELTER if a[k] != b[k]}
    return {
        "changed": bool(forskelle),
        "changed_fields": sorted(forskelle),
        "fields": forskelle,
        "older": {"snapshot_id": a["snapshot_id"], "version": a["version"]},
        "newer": {"snapshot_id": b["snapshot_id"], "version": b["version"]},
        "reason": "",
    }


def build_self_model_history_surface(*, limit: int = 10) -> dict[str, Any]:
    """Fladen: de seneste billeder, og hvad der skiftede mellem de to nyeste."""
    billeder = list_self_model_snapshots(limit=max(2, int(limit)))
    seneste_skift: dict[str, Any] = {"changed": None, "reason": "for faa billeder"}
    if len(billeder) >= 2:
        seneste_skift = compare_self_model_snapshots(
            billeder[1]["snapshot_id"], billeder[0]["snapshot_id"])
    return {
        "snapshots": billeder[:int(limit)],
        "snapshot_count": len(billeder),
        "latest_change": seneste_skift,
    }
