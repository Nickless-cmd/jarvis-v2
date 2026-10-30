"""Persistence for the runtime learning/outcome signal tables.

Split out of core/runtime/db.py per the boy-scout rule. Owns the schema for
`runtime_action_outcomes` and `runtime_learning_signals`
(ensure_runtime_signals_tables + the additive target_domain migration) plus
their record/recent CRUD and row-mapping helpers.
"""
from __future__ import annotations

import json as _json
import sqlite3
from uuid import uuid4

from core.runtime.db_core import connect


def ensure_runtime_signals_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_action_outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            outcome_id TEXT NOT NULL UNIQUE,
            action_id TEXT NOT NULL,
            decision_mode TEXT NOT NULL,
            decision_reason TEXT NOT NULL DEFAULT '',
            decision_score REAL NOT NULL DEFAULT 0,
            payload_json TEXT NOT NULL DEFAULT '{}',
            result_status TEXT NOT NULL,
            result_summary TEXT NOT NULL DEFAULT '',
            result_json TEXT NOT NULL DEFAULT '{}',
            recorded_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_action_outcomes_lookup
        ON runtime_action_outcomes(action_id, recorded_at DESC)
        """
    )
    # 28/10-2026: den manglende PIL. Alt andet i denne fil INSERT'er en ny raekke;
    # denne tabel er den ENESTE der OPDATERER en vaegt. Maalt foer den fandtes:
    # runtime_action_outcomes havde 274.614 raekker, men decision_score havde kun
    # 6 distinkte vaerdier for 257.027 ok-raekker — et facit-notat skrevet EFTER
    # udfaldet kan ikke have paavirket det valg det beskriver. `term` er her
    # handlingens identitet (action_id), fordi det er den noegle valget slaar op med.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS central_word_weights (
            term TEXT PRIMARY KEY,
            weight REAL NOT NULL DEFAULT 0.5,
            n_samples INTEGER NOT NULL DEFAULT 0,
            last_updated TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_learning_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            outcome_id TEXT NOT NULL,
            source_action_id TEXT NOT NULL,
            target_action_id TEXT NOT NULL DEFAULT '',
            target_family TEXT NOT NULL DEFAULT '',
            target_domain TEXT NOT NULL DEFAULT '',
            signal_key TEXT NOT NULL,
            signal_weight REAL NOT NULL DEFAULT 0,
            signal_count INTEGER NOT NULL DEFAULT 1,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            recorded_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_learning_signals_lookup
        ON runtime_learning_signals(signal_key, target_family, target_action_id, recorded_at DESC)
        """
    )
    try:
        conn.execute(
            """
            ALTER TABLE runtime_learning_signals
            ADD COLUMN target_domain TEXT NOT NULL DEFAULT ''
            """
        )
    except sqlite3.OperationalError:
        pass


def _runtime_action_outcome_from_row(row: sqlite3.Row) -> dict[str, object]:
    payload_raw = str(row["payload_json"] or "{}")
    result_raw = str(row["result_json"] or "{}")
    try:
        payload = _json.loads(payload_raw)
    except Exception:
        payload = {}
    try:
        result = _json.loads(result_raw)
    except Exception:
        result = {}
    return {
        "outcome_id": row["outcome_id"],
        "action_id": row["action_id"],
        "decision_mode": row["decision_mode"],
        "decision_reason": row["decision_reason"],
        "decision_score": float(row["decision_score"] or 0.0),
        "payload": payload if isinstance(payload, dict) else {},
        "result_status": row["result_status"],
        "result_summary": row["result_summary"],
        "result": result if isinstance(result, dict) else {},
        "recorded_at": row["recorded_at"],
    }


def _runtime_learning_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    metadata_raw = str(row["metadata_json"] or "{}")
    try:
        metadata = _json.loads(metadata_raw)
    except Exception:
        metadata = {}
    return {
        "signal_id": row["signal_id"],
        "outcome_id": row["outcome_id"],
        "source_action_id": row["source_action_id"],
        "target_action_id": row["target_action_id"],
        "target_family": row["target_family"],
        "target_domain": row["target_domain"],
        "signal_key": row["signal_key"],
        "signal_weight": float(row["signal_weight"] or 0.0),
        "signal_count": int(row["signal_count"] or 1),
        "metadata": metadata if isinstance(metadata, dict) else {},
        "recorded_at": row["recorded_at"],
    }


def recent_runtime_action_outcomes(limit: int = 10) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                outcome_id,
                action_id,
                decision_mode,
                decision_reason,
                decision_score,
                payload_json,
                result_status,
                result_summary,
                result_json,
                recorded_at
            FROM runtime_action_outcomes
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [_runtime_action_outcome_from_row(row) for row in rows]


def recent_runtime_learning_signals(limit: int = 25) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                signal_id,
                outcome_id,
                source_action_id,
                target_action_id,
                target_family,
                target_domain,
                signal_key,
                signal_weight,
                signal_count,
                metadata_json,
                recorded_at
            FROM runtime_learning_signals
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [_runtime_learning_signal_from_row(row) for row in rows]


def record_runtime_action_outcome(
    *,
    action_id: str,
    decision_mode: str,
    decision_reason: str,
    decision_score: float,
    payload_json: dict[str, object] | None,
    result_status: str,
    result_summary: str,
    result_json: dict[str, object] | None,
    recorded_at: str,
) -> dict[str, object]:
    outcome_id = f"rao-{uuid4().hex[:12]}"
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO runtime_action_outcomes (
                outcome_id,
                action_id,
                decision_mode,
                decision_reason,
                decision_score,
                payload_json,
                result_status,
                result_summary,
                result_json,
                recorded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                outcome_id,
                action_id,
                decision_mode,
                decision_reason,
                float(decision_score or 0.0),
                _json.dumps(payload_json or {}, ensure_ascii=False, sort_keys=True),
                result_status,
                result_summary,
                _json.dumps(result_json or {}, ensure_ascii=False, sort_keys=True),
                recorded_at,
            ),
        )
        conn.commit()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                outcome_id,
                action_id,
                decision_mode,
                decision_reason,
                decision_score,
                payload_json,
                result_status,
                result_summary,
                result_json,
                recorded_at
            FROM runtime_action_outcomes
            WHERE outcome_id = ?
            """,
            (outcome_id,),
        ).fetchone()
    if row is None:
        raise RuntimeError("runtime action outcome was not persisted")
    return _runtime_action_outcome_from_row(row)


def record_runtime_learning_signal(
    *,
    outcome_id: str,
    source_action_id: str,
    target_action_id: str,
    target_family: str,
    target_domain: str,
    signal_key: str,
    signal_weight: float,
    signal_count: int,
    metadata_json: dict[str, object] | None,
    recorded_at: str,
) -> dict[str, object]:
    signal_id = f"rls-{uuid4().hex[:12]}"
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO runtime_learning_signals (
                signal_id,
                outcome_id,
                source_action_id,
                target_action_id,
                target_family,
                target_domain,
                signal_key,
                signal_weight,
                signal_count,
                metadata_json,
                recorded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal_id,
                outcome_id,
                source_action_id,
                target_action_id,
                target_family,
                target_domain,
                signal_key,
                float(signal_weight or 0.0),
                int(signal_count or 1),
                _json.dumps(metadata_json or {}, ensure_ascii=False, sort_keys=True),
                recorded_at,
            ),
        )
        conn.commit()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                signal_id,
                outcome_id,
                source_action_id,
                target_action_id,
                target_family,
                target_domain,
                signal_key,
                signal_weight,
                signal_count,
                metadata_json,
                recorded_at
            FROM runtime_learning_signals
            WHERE signal_id = ?
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        raise RuntimeError("runtime learning signal was not persisted")
    return _runtime_learning_signal_from_row(row)


# ── Vaegt-loekken (28/10-2026) ────────────────────────────────────────────
# Skrive-vejen: udfaldet flytter vaegten. Laese-vejen: valget konsulterer den.
# Foer dette fandtes kun en SNAPSHOT (summarize_executive_feedback) der blev
# genberegnet ved hver laesning ud fra de SAMME raa raekker — den kunne pr.
# konstruktion ikke flytte sig over tid. Det saa ud som akkumulering, men var
# en re-derivation.

# Hvad et udfald peger imod. Bevidst groft: et udfald er ikke en finmasket
# dom, og en vaegt der bevaege sig i spring paa 0.01 ville vaere stoj.
_OUTCOME_TARGET = {
    "executed": 1.0,
    "recorded": 1.0,
    "sent": 1.0,
    "success": 1.0,
    "ok": 1.0,
    "proposed": 0.6,   # skete ikke — halvt fremskridt, ikke et nej
    "blocked": 0.25,
    "failed": 0.0,
    "error": 0.0,
}


def outcome_target(status: str) -> float:
    """Et udfalds retning som tal i [0,1]. Ukendt status giver 0.5 (neutral)."""
    return _OUTCOME_TARGET.get(str(status or "").strip().lower(), 0.5)


def load_action_weights(terms: list[str] | None = None) -> dict[str, dict[str, object]]:
    """Laese-vejen: persisterede vaegte pr. term (action_id).

    Kaldes FOER valget. Returnerer ``{term: {weight, n_samples, last_updated}}``.
    En term der aldrig er set mangler i mappet — kalderen skal behandle det som
    «ingen viden», ikke som neutral vaegt 0.5. Forskellen er hele pointen.
    """
    with connect() as conn:
        ensure_runtime_signals_tables(conn)
        if terms:
            placeholders = ",".join("?" for _ in terms)
            rows = conn.execute(
                f"SELECT term, weight, n_samples, last_updated "
                f"FROM central_word_weights WHERE term IN ({placeholders})",
                tuple(terms),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT term, weight, n_samples, last_updated FROM central_word_weights"
            ).fetchall()
    return {
        str(row["term"]): {
            "weight": float(row["weight"]),
            "n_samples": int(row["n_samples"]),
            "last_updated": str(row["last_updated"]),
        }
        for row in rows
    }


def apply_action_weight_update(
    *,
    term: str,
    outcome_status: str,
    recorded_at: str,
) -> dict[str, object]:
    """Skrive-vejen: udfaldet flytter vaegten — UPDATE, ikke INSERT.

    Vaegten er et loebende gennemsnit mod udfaldets retning::

        weight <- weight + rate * (target - weight),  rate = 1/(n_samples+1)

    Læringsraten er AFledt af forloebet, ikke valgt frit: jo flere samples, jo
    mindre flytter den enkelte observation. En haandplukket konstant ville vaere
    en indstilling, ikke en laering.

    Atomisk i ÉN saetning: der er ingen laes-saa-skriv-der kan skilles ad, saa to
    samtidige udfald kan ikke overskrive hinandens sample-tal.
    """
    key = str(term or "").strip()
    if not key:
        return {}
    target = outcome_target(outcome_status)
    with connect() as conn:
        ensure_runtime_signals_tables(conn)
        conn.execute(
            """
            INSERT INTO central_word_weights (term, weight, n_samples, last_updated)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(term) DO UPDATE SET
                weight = central_word_weights.weight
                    + (1.0 / (central_word_weights.n_samples + 1.0))
                    * (? - central_word_weights.weight),
                n_samples = central_word_weights.n_samples + 1,
                last_updated = excluded.last_updated
            """,
            (key, target, recorded_at, target),
        )
        conn.commit()
        row = conn.execute(
            "SELECT term, weight, n_samples, last_updated "
            "FROM central_word_weights WHERE term = ?",
            (key,),
        ).fetchone()
    if row is None:
        raise RuntimeError("action weight was not persisted")
    return {
        "term": str(row["term"]),
        "weight": float(row["weight"]),
        "n_samples": int(row["n_samples"]),
        "last_updated": str(row["last_updated"]),
    }
