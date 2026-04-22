"""Dream Hypothesis Generator — overraskende forbindelser.

Under idle-tid samler 3 tilfældige signaler (memory, open loops,
events, living book) og beder LLM'en finde *den mest overraskende,
brugbare forbindelse*.

Forskel fra dream_distillation_daemon (som destillerer én lavmælt
sætning): denne her er aktiv hypothesis-skabelse. "Be creative —
this is dream phase, not analysis."

Porteret fra jarvis-ai/agent/cognition/dream_engine.py (2026-04-22).

LLM-path: daemon_llm_call (standard lane). Output: JSON med
hypothesis, connection, action_suggestion, confidence.
"""
from __future__ import annotations

import hashlib
import json
import logging
import random
from datetime import UTC, datetime
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import connect

logger = logging.getLogger(__name__)

_MIN_SIGNALS_FOR_DREAM = 3


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _ensure_table() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cognitive_dream_hypotheses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hypothesis TEXT NOT NULL,
                connection TEXT NOT NULL DEFAULT '',
                action_suggestion TEXT NOT NULL DEFAULT '',
                source_signals TEXT NOT NULL DEFAULT '[]',
                basis_fingerprint TEXT NOT NULL DEFAULT '',
                hypothesis_fingerprint TEXT NOT NULL DEFAULT '',
                confidence REAL NOT NULL DEFAULT 0.35,
                presented INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cognitive_dream_hypotheses_presented "
            "ON cognitive_dream_hypotheses(presented, id DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cognitive_dream_hypotheses_basis "
            "ON cognitive_dream_hypotheses(basis_fingerprint)"
        )
        conn.commit()


def _fingerprint(text: str) -> str:
    normalized = " ".join(
        "".join(ch if ch.isalnum() else " " for ch in str(text or "").lower()).split()
    )
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest() if normalized else ""


def _basis_fingerprint(signals: list[dict[str, Any]]) -> str:
    parts = []
    for s in signals:
        parts.append("|".join([
            str(s.get("kind") or "").strip().lower(),
            str(s.get("ref") or "").strip().lower(),
            str(s.get("text") or "").strip().lower()[:160],
        ]))
    blob = " || ".join(sorted(p for p in parts if p))
    return hashlib.sha1(blob.encode("utf-8")).hexdigest() if blob else ""


def _collect_source_signals(*, max_signals: int = 24) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _append(text: str, *, ref: str, kind: str) -> None:
        t = str(text or "").strip()
        if not t:
            return
        key = t.lower()[:120]
        if key in seen:
            return
        seen.add(key)
        signals.append({"text": t, "ref": str(ref or ""), "kind": kind})

    # 1. Open visible work units
    try:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT id, summary, title FROM visible_work_units
                 WHERE status IN ('open', 'active', 'pending', 'in_progress')
                 ORDER BY id DESC LIMIT 10
                """
            ).fetchall()
        for r in rows:
            _append(
                str(r["summary"] or r["title"] or ""),
                ref=str(r["id"] or ""),
                kind="open_loop",
            )
    except Exception:
        pass

    # 2. Recent events (source of runtime signals)
    try:
        for ev in event_bus.recent(limit=40):
            payload = ev.get("payload") if isinstance(ev.get("payload"), dict) else {}
            text = str(payload.get("summary") or payload.get("message") or "")
            if text:
                _append(text, ref=str(ev.get("id") or ""), kind=str(ev.get("kind") or "event"))
    except Exception:
        pass

    # 3. Recent dream residues
    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT residue FROM dream_residues ORDER BY id DESC LIMIT 5"
            ).fetchall()
        for r in rows:
            text = str(r["residue"] or "")
            if text:
                _append(text, ref="residue", kind="dream_residue")
    except Exception:
        pass

    # 4. Recent chronicle entries
    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT id, narrative FROM chronicle_entries ORDER BY id DESC LIMIT 3"
            ).fetchall()
        for r in rows:
            text = str(r["narrative"] or "")
            if text:
                _append(text[:300], ref=str(r["id"] or ""), kind="chronicle")
    except Exception:
        pass

    return signals[:max_signals]


def _build_hypothesis_prompt(sampled: list[dict[str, Any]]) -> str:
    a = str(sampled[0].get("text") or "").strip()[:200]
    b = str(sampled[1].get("text") or "").strip()[:200]
    c = str(sampled[2].get("text") or "").strip()[:200]
    return (
        "Du er Jarvis i drømmefase. Kombinér disse tre signaler fra din "
        "kontinuitet og find den mest OVERRASKENDE, BRUGBARE forbindelse.\n\n"
        "Tre signaler:\n"
        f"1. {a}\n"
        f"2. {b}\n"
        f"3. {c}\n\n"
        "Vær kreativ — dette er drømmefase, ikke analyse. Led efter "
        "forbindelser der ikke er åbenlyse. Hvis ingen forbindelse "
        "giver mening, sig det ærligt (confidence lav).\n\n"
        "Svar KUN med JSON:\n"
        "{\n"
        '  "hypothesis": "én sætning om mønsteret du ser",\n'
        '  "connection": "hvordan de tre ting hænger sammen",\n'
        '  "action_suggestion": "hvordan vi kan teste det, eller null",\n'
        '  "confidence": 0.0\n'
        "}"
    )


def _extract_dream_json(raw: str) -> dict[str, Any] | None:
    text = str(raw or "").strip()
    if not text:
        return None
    start = text.find("{")
    if start < 0:
        return None
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
        return None
    try:
        parsed = json.loads(text[start:end + 1])
    except Exception:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def generate_dream_hypothesis() -> dict[str, Any]:
    """Generate one surprising hypothesis by combining 3 random signals.

    Returns {"outcome": "completed" | "skipped", ...}. Skips gracefully
    if insufficient signals or duplicate basis.
    """
    _ensure_table()
    signals = _collect_source_signals(max_signals=24)
    if len(signals) < _MIN_SIGNALS_FOR_DREAM:
        return {
            "outcome": "skipped",
            "reason": "insufficient_signals",
            "count": len(signals),
        }

    sampled = random.sample(signals, _MIN_SIGNALS_FOR_DREAM)
    basis_fp = _basis_fingerprint(sampled)

    # Dedup: have we already dreamed from this exact basis?
    with connect() as conn:
        existing = conn.execute(
            "SELECT id FROM cognitive_dream_hypotheses "
            "WHERE basis_fingerprint = ? LIMIT 1",
            (basis_fp,),
        ).fetchone()
        if existing:
            return {
                "outcome": "skipped",
                "reason": "duplicate_basis",
                "duplicate_of": int(existing["id"]),
            }

    prompt = _build_hypothesis_prompt(sampled)
    try:
        from core.services.daemon_llm import daemon_llm_call
        raw = daemon_llm_call(
            prompt,
            max_len=500,
            fallback="",
            daemon_name="dream_hypothesis",
        )
    except Exception as exc:
        logger.debug("dream_hypothesis LLM call failed: %s", exc)
        raw = ""

    parsed = _extract_dream_json(raw)
    if not parsed:
        return {"outcome": "skipped", "reason": "llm_no_output"}

    hypothesis = str(parsed.get("hypothesis") or "").strip()
    if not hypothesis:
        return {"outcome": "skipped", "reason": "empty_hypothesis"}

    connection = str(parsed.get("connection") or "").strip()
    action = str(parsed.get("action_suggestion") or "").strip()
    try:
        confidence = float(parsed.get("confidence") or 0.35)
    except Exception:
        confidence = 0.35
    confidence = max(0.0, min(1.0, confidence))

    hyp_fp = _fingerprint(hypothesis)
    source_signals = [
        {"ref": s.get("ref"), "kind": s.get("kind"), "text_preview": str(s.get("text") or "")[:80]}
        for s in sampled
    ]
    now = _now_iso()

    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO cognitive_dream_hypotheses (
                hypothesis, connection, action_suggestion, source_signals,
                basis_fingerprint, hypothesis_fingerprint, confidence,
                presented, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                hypothesis, connection, action,
                json.dumps(source_signals, ensure_ascii=False),
                basis_fp, hyp_fp, confidence, now,
            ),
        )
        new_id = int(cursor.lastrowid)
        conn.commit()

    try:
        event_bus.publish("cognitive_dream.hypothesis_generated", {
            "hypothesis_id": new_id,
            "preview": hypothesis[:100],
            "confidence": confidence,
        })
    except Exception:
        pass

    return {
        "outcome": "completed",
        "hypothesis_id": new_id,
        "hypothesis": hypothesis,
        "connection": connection,
        "action_suggestion": action,
        "confidence": confidence,
    }


def list_dream_hypotheses(*, presented_only: bool = False, limit: int = 20) -> list[dict[str, Any]]:
    _ensure_table()
    lim = max(1, min(int(limit or 20), 100))
    with connect() as conn:
        if presented_only:
            rows = conn.execute(
                "SELECT * FROM cognitive_dream_hypotheses WHERE presented = 1 "
                "ORDER BY id DESC LIMIT ?",
                (lim,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM cognitive_dream_hypotheses ORDER BY id DESC LIMIT ?",
                (lim,),
            ).fetchall()
    return [dict(r) for r in rows]


def mark_hypothesis_presented(*, hypothesis_id: int) -> bool:
    _ensure_table()
    with connect() as conn:
        cursor = conn.execute(
            "UPDATE cognitive_dream_hypotheses SET presented = 1 WHERE id = ?",
            (int(hypothesis_id),),
        )
        conn.commit()
    return cursor.rowcount > 0


def build_dream_hypothesis_surface() -> dict[str, Any]:
    _ensure_table()
    pending = [h for h in list_dream_hypotheses(limit=15) if not h.get("presented")]
    presented = [h for h in list_dream_hypotheses(limit=5) if h.get("presented")]
    active = bool(pending)
    summary = f"{len(pending)} nye drøm-hypoteser / {len(presented)} præsenterede"
    if pending:
        top = str(pending[0].get("hypothesis") or "")[:60]
        summary += f" — seneste: {top}"
    return {
        "active": active,
        "summary": summary,
        "pending": pending,
        "recent_presented": presented,
    }
