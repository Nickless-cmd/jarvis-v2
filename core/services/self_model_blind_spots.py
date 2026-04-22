"""Self-Model Blind Spots — LLM-drevet opdagelse af egne usete fejlmønstre.

Samler de seneste fejlede visible runs og spørger LLM'en: "Hvad er det
fælles mønster i disse fejl som Jarvis IKKE allerede har markeret som
svaghed?"

Det der opdages persisteres i cognitive_blind_spots, så Jarvis kan
tilbagekomme til det og integrere det i sit selvmodel.

Porteret fra jarvis-ai/agent/cognition/self_model.py:find_blind_spots.
Tilpasset v2: bruger visible_runs + daemon_llm_call + dedikeret tabel
i stedet for at røre den 5942-liners runtime_self_model.py.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import connect

logger = logging.getLogger(__name__)

_MIN_FAILED_RUNS_FOR_DISCOVERY = 3
_MAX_FAILED_RUNS_SAMPLE = 10


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _ensure_table() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cognitive_blind_spots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                evidence_run_ids TEXT NOT NULL DEFAULT '[]',
                confidence REAL NOT NULL DEFAULT 0.5,
                status TEXT NOT NULL DEFAULT 'open',
                acknowledged_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(description)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cognitive_blind_spots_status "
            "ON cognitive_blind_spots(status, id DESC)"
        )
        conn.commit()


def _load_known_patterns() -> list[str]:
    """Pull already-identified blind spots + known weaknesses.

    v2 has no known_weaknesses field; we rely on existing blind_spots as
    negative examples so LLM doesn't re-discover the same ones.
    """
    _ensure_table()
    with connect() as conn:
        rows = conn.execute(
            "SELECT description FROM cognitive_blind_spots "
            "WHERE status IN ('open', 'acknowledged') "
            "ORDER BY id DESC LIMIT 50"
        ).fetchall()
    return [str(r["description"] or "").strip() for r in rows if r["description"]]


def _load_recent_failed_runs(limit: int = 10) -> list[dict[str, Any]]:
    """Pull recent failed visible runs with summary + run_id."""
    try:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT run_id, outcome_summary, status, created_at
                  FROM visible_runs
                 WHERE status IN ('error', 'failed', 'aborted', 'incomplete')
                    OR outcome_summary LIKE '%error%'
                    OR outcome_summary LIKE '%failed%'
                 ORDER BY id DESC LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.debug("blind_spots: visible_runs fetch failed: %s", exc)
        return []


def _build_discovery_prompt(
    *,
    known_patterns: list[str],
    failed_runs: list[dict[str, Any]],
) -> str:
    known = json.dumps(known_patterns[:12], ensure_ascii=False)
    summaries = [
        {
            "run_id": str(r.get("run_id") or "")[:40],
            "summary": str(r.get("outcome_summary") or "")[:200],
        }
        for r in failed_runs[:_MAX_FAILED_RUNS_SAMPLE]
    ]
    return (
        "Du er Jarvis der kigger på dine egne nylige fejl og leder efter "
        "mønstre du IKKE har set endnu.\n\n"
        "Kendte mønstre (dem her behøver du IKKE gentage):\n"
        f"{known}\n\n"
        "Seneste fejlede runs:\n"
        f"{json.dumps(summaries, ensure_ascii=False)}\n\n"
        "Hvad er det fælles mønster på tværs af disse fejl — et mønster "
        "der IKKE allerede er på listen ovenfor?\n\n"
        "Ikke generel selvkritik. Kun konkrete, gentagne mønstre.\n"
        "Maks 3 blind spots. Hvis du ikke kan se et klart mønster, "
        "returnér tom liste.\n\n"
        "Svar KUN med JSON:\n"
        '{"blind_spots": ["beskrivelse 1", ...]}'
    )


def _extract_blind_spots(raw_text: str) -> list[str]:
    """Parse LLM response. Tolerates preamble/fences — finds first {...} block."""
    text = str(raw_text or "").strip()
    if not text:
        return []
    # Balanced-brace extraction
    start = text.find("{")
    if start < 0:
        return []
    depth = 0
    end = -1
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end < 0:
        return []
    try:
        parsed = json.loads(text[start:end + 1])
    except Exception:
        return []
    if not isinstance(parsed, dict):
        return []
    raw = parsed.get("blind_spots")
    if not isinstance(raw, list):
        return []
    return [str(x).strip() for x in raw if str(x).strip()][:3]


def discover_blind_spots() -> list[dict[str, Any]]:
    """Run discovery: analyze recent failed runs for unseen patterns.

    Returns list of newly discovered blind spots (not already persisted).
    Fire-and-forget safe: caller does not need to handle exceptions.
    """
    _ensure_table()
    failed_runs = _load_recent_failed_runs(limit=_MAX_FAILED_RUNS_SAMPLE)
    if len(failed_runs) < _MIN_FAILED_RUNS_FOR_DISCOVERY:
        return []

    known_patterns = _load_known_patterns()
    prompt = _build_discovery_prompt(
        known_patterns=known_patterns,
        failed_runs=failed_runs,
    )

    try:
        from core.services.daemon_llm import daemon_llm_call
        raw = daemon_llm_call(
            prompt,
            max_len=600,
            fallback="",
            daemon_name="self_model_blind_spots",
        )
    except Exception as exc:
        logger.debug("blind_spots LLM call failed: %s", exc)
        return []

    candidates = _extract_blind_spots(raw)
    if not candidates:
        return []

    now = _now_iso()
    run_ids = [str(r.get("run_id") or "") for r in failed_runs[:_MAX_FAILED_RUNS_SAMPLE]]
    run_ids_json = json.dumps(run_ids, ensure_ascii=False)
    confidence = 0.55 + min(0.2, len(failed_runs) * 0.02)

    new_spots: list[dict[str, Any]] = []
    with connect() as conn:
        for desc in candidates:
            norm = re.sub(r"\s+", " ", desc).strip()
            if not norm:
                continue
            # Skip if matches known pattern (case-insensitive loose)
            norm_lo = norm.lower()
            if any(norm_lo == k.lower() or norm_lo in k.lower() or k.lower() in norm_lo
                   for k in known_patterns):
                continue
            try:
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO cognitive_blind_spots (
                        description, evidence_run_ids, confidence, status,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, 'open', ?, ?)
                    """,
                    (norm, run_ids_json, float(confidence), now, now),
                )
                if cursor.rowcount > 0:
                    new_id = int(cursor.lastrowid)
                    new_spots.append({
                        "id": new_id,
                        "description": norm,
                        "confidence": float(confidence),
                        "status": "open",
                    })
            except Exception as exc:
                logger.debug("blind_spot insert failed for %r: %s", norm, exc)
        conn.commit()

    for s in new_spots:
        try:
            event_bus.publish("cognitive_blind_spot.discovered", {
                "blind_spot_id": s["id"],
                "description": s["description"][:120],
                "confidence": s["confidence"],
            })
        except Exception:
            pass

    return new_spots


def acknowledge_blind_spot(*, blind_spot_id: int) -> dict[str, Any]:
    """Mark a blind spot as acknowledged (Jarvis has now integrated it)."""
    _ensure_table()
    now = _now_iso()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM cognitive_blind_spots WHERE id = ?",
            (int(blind_spot_id),),
        ).fetchone()
        if not row:
            return {"outcome": "not_found"}
        conn.execute(
            "UPDATE cognitive_blind_spots "
            "SET status = 'acknowledged', acknowledged_at = ?, updated_at = ? "
            "WHERE id = ?",
            (now, now, int(blind_spot_id)),
        )
        conn.commit()
        fresh = conn.execute(
            "SELECT * FROM cognitive_blind_spots WHERE id = ?",
            (int(blind_spot_id),),
        ).fetchone()
    try:
        event_bus.publish("cognitive_blind_spot.acknowledged", {
            "blind_spot_id": int(blind_spot_id),
        })
    except Exception:
        pass
    return {"outcome": "acknowledged", "blind_spot": dict(fresh)}


def list_blind_spots(*, status: str = "", limit: int = 50) -> list[dict[str, Any]]:
    _ensure_table()
    lim = max(1, min(int(limit or 50), 200))
    status = str(status or "").strip().lower()
    with connect() as conn:
        if status in {"open", "acknowledged", "dismissed"}:
            rows = conn.execute(
                "SELECT * FROM cognitive_blind_spots WHERE status = ? "
                "ORDER BY id DESC LIMIT ?",
                (status, lim),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM cognitive_blind_spots ORDER BY id DESC LIMIT ?",
                (lim,),
            ).fetchall()
    return [dict(r) for r in rows]


def build_blind_spots_surface() -> dict[str, Any]:
    """MC surface for self-model blind spots."""
    _ensure_table()
    open_spots = list_blind_spots(status="open", limit=10)
    acknowledged = list_blind_spots(status="acknowledged", limit=5)
    active = bool(open_spots)
    summary = f"{len(open_spots)} åbne / {len(acknowledged)} erkendte blinde pletter"
    if open_spots:
        top = str(open_spots[0].get("description") or "")[:60]
        summary += f" — top: {top}"
    return {
        "active": active,
        "summary": summary,
        "open_blind_spots": open_spots,
        "recent_acknowledged": acknowledged,
    }
