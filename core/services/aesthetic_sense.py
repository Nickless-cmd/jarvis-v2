"""Aesthetic Sense — tracks Jarvis' evolving taste motifs.

Detects recurring aesthetic preferences: clarity, craft, calm-focus.
Over time builds a taste signature visible in MC.

Weekly-budget + signature-dedup tilføjet 2026-04-22 fra jarvis-ai
aesthetics.py: Jarvis observerer kun nye æstetiske mønstre én gang
om ugen, og kun hvis motif+evidens er noget han ikke allerede har
set.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta

from core.eventbus.bus import event_bus
from core.runtime.db import connect

logger = logging.getLogger(__name__)

_WEEKLY_BUDGET_DAYS = 7

_MOTIFS = [
    {
        "motif": "clarity",
        "keywords": ["klar", "clear", "simple", "clean", "minimal", "overskuelig"],
        "reflection": "Gentagne præference for klarhed over ornamentation.",
    },
    {
        "motif": "craft",
        "keywords": ["elegant", "polish", "craft", "smuk", "kohærent", "vellavet"],
        "reflection": "Tilbagevendende træk mod håndværk og sammenhængende finish.",
    },
    {
        "motif": "calm-focus",
        "keywords": ["rolig", "fokus", "stille", "steady", "rytme", "bæredygtig"],
        "reflection": "Signaler peger mod en rolig, bæredygtig arbejdsrytme.",
    },
    {
        "motif": "density",
        "keywords": ["kompakt", "tæt", "data-dense", "information", "packed"],
        "reflection": "Præference for informationstætte layouts og svar.",
    },
    {
        "motif": "directness",
        "keywords": ["direkte", "kort", "ingen snak", "bare kode", "vis mig"],
        "reflection": "Præference for direkte kommunikation uden omsvøb.",
    },
]


def detect_aesthetic_signals(
    *,
    text: str,
) -> list[dict[str, object]]:
    """Detect aesthetic motifs in text."""
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    signals = []
    text_lower = text.lower()

    for motif_def in _MOTIFS:
        hits = sum(1 for kw in motif_def["keywords"] if kw in text_lower)
        if hits > 0:
            signals.append({
                "motif": motif_def["motif"],
                "hits": hits,
                "confidence": min(0.9, hits / 5.0),
                "reflection": motif_def["reflection"],
                "ts": now,
            })

    if signals:
        event_bus.publish(
            "cognitive_aesthetic.signals_detected",
            {"motifs": [s["motif"] for s in signals]},
        )

    return signals


def build_aesthetic_surface() -> dict[str, object]:
    return {
        "active": True,
        "motifs": [m["motif"] for m in _MOTIFS],
        "description": "Aesthetic detection runs on conversation text",
        "summary": f"{len(_MOTIFS)} aesthetic motifs tracked",
    }


# ── Aesthetic notes: weekly-budgeted, signature-deduped observations ──
# Porteret fra jarvis-ai/aesthetics.py


def _ensure_notes_table() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cognitive_aesthetic_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                motif TEXT NOT NULL,
                signature TEXT NOT NULL UNIQUE,
                evidence_refs TEXT NOT NULL DEFAULT '[]',
                reflection TEXT NOT NULL DEFAULT '',
                confidence REAL NOT NULL DEFAULT 0.5,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cognitive_aesthetic_notes_created "
            "ON cognitive_aesthetic_notes(created_at DESC)"
        )
        conn.commit()


def _compute_signature(motif: str, evidence_refs: list[str]) -> str:
    sorted_refs = sorted({str(r).strip().lower() for r in evidence_refs if str(r).strip()})
    raw = f"{str(motif).strip().lower()}::{'|'.join(sorted_refs)}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()[:16]


def _latest_note_ts() -> datetime | None:
    _ensure_notes_table()
    try:
        with connect() as conn:
            row = conn.execute(
                "SELECT created_at FROM cognitive_aesthetic_notes "
                "ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if row and row["created_at"]:
            ts = datetime.fromisoformat(str(row["created_at"]).replace("Z", "+00:00"))
            return ts if ts.tzinfo else ts.replace(tzinfo=UTC)
    except Exception:
        pass
    return None


def _known_signatures() -> set[str]:
    _ensure_notes_table()
    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT signature FROM cognitive_aesthetic_notes"
            ).fetchall()
        return {str(r["signature"] or "") for r in rows if r["signature"]}
    except Exception:
        return set()


def maybe_capture_weekly_aesthetic_note(
    *,
    candidates: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Capture at most ONE aesthetic note per week, only if signature is new.

    candidates: list of {motif, evidence_refs, reflection, confidence}.
    If None, pulls from recent detection via aesthetic_motif_log (via
    aesthetic_taste_daemon's accumulated motifs). Caller can supply directly.
    """
    _ensure_notes_table()
    last = _latest_note_ts()
    now = datetime.now(UTC)
    if last and (now - last) < timedelta(days=_WEEKLY_BUDGET_DAYS):
        return {"outcome": "skipped", "reason": "weekly_budget"}

    pool = candidates or []
    if not pool:
        # Fall back: pull any recently-detected motif via the log as a single candidate
        try:
            from core.runtime.db import aesthetic_motif_log_summary
            summary = aesthetic_motif_log_summary() or []
            for row in summary[:3]:
                if isinstance(row, dict) and row.get("motif"):
                    pool.append({
                        "motif": str(row["motif"]),
                        "evidence_refs": [f"log:{row.get('count', 0)}obs"],
                        "reflection": "",
                        "confidence": float(row.get("avg_confidence") or 0.5),
                    })
        except Exception:
            pass

    if not pool:
        return {"outcome": "skipped", "reason": "no_candidate"}

    known = _known_signatures()
    selected = None
    for cand in pool:
        motif = str(cand.get("motif") or "").strip()
        refs = [str(r) for r in (cand.get("evidence_refs") or [])]
        sig = _compute_signature(motif, refs)
        if sig and sig not in known:
            selected = {**cand, "signature": sig}
            break
    if selected is None:
        return {"outcome": "skipped", "reason": "duplicate_candidate"}

    import json
    now_iso = now.isoformat().replace("+00:00", "Z")
    with connect() as conn:
        try:
            conn.execute(
                """
                INSERT INTO cognitive_aesthetic_notes
                    (motif, signature, evidence_refs, reflection, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(selected.get("motif") or ""),
                    str(selected["signature"]),
                    json.dumps(selected.get("evidence_refs") or [], ensure_ascii=False),
                    str(selected.get("reflection") or ""),
                    float(selected.get("confidence") or 0.5),
                    now_iso,
                ),
            )
            conn.commit()
        except Exception as exc:
            logger.debug("aesthetic note insert failed: %s", exc)
            return {"outcome": "error", "reason": str(exc)[:80]}

    try:
        event_bus.publish("cognitive_aesthetic.note_captured", {
            "motif": selected.get("motif"),
            "signature": selected["signature"],
        })
    except Exception:
        pass
    return {"outcome": "captured", "note": selected}


def list_aesthetic_notes(*, limit: int = 50) -> list[dict[str, object]]:
    _ensure_notes_table()
    lim = max(1, min(int(limit or 50), 200))
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM cognitive_aesthetic_notes ORDER BY id DESC LIMIT ?",
            (lim,),
        ).fetchall()
    return [dict(r) for r in rows]


def accumulate_from_daemon(source: str, text: str) -> list[dict[str, object]]:
    """Run motif detection on daemon text output, persist to DB, update in-memory set.

    Called once per text-producing daemon per heartbeat tick from heartbeat_runtime.
    """
    signals = detect_aesthetic_signals(text=text)
    if not signals:
        return []
    try:
        from core.runtime.db import aesthetic_motif_log_insert

        for s in signals:
            aesthetic_motif_log_insert(
                source=source,
                motif=s["motif"],
                confidence=s["confidence"],
            )
    except Exception:
        pass
    try:
        from core.services.aesthetic_taste_daemon import _accumulated_motifs

        for s in signals:
            _accumulated_motifs.add(s["motif"])
    except Exception:
        pass
    return signals
