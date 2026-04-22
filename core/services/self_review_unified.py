"""Self-Review Unified — periodisk samlet selv-audit.

v2 har 5+ `self_review_*_signal_tracking.py` filer der observerer signaler.
Men ingen samlet action der periodisk genererer og persister en
*selvkritisk review* af Jarvis' egen performance.

Dette modul lukker det hul: samler recent visible_runs + regrets +
blind_spots + ruptures og beder LLM om en kompakt selvkritik.
Persisteres i ny tabel cognitive_self_reviews.

Porteret fra jarvis-ai/agent/cognition/self_review.py (2026-04-22).

LLM-path: daemon_llm_call. Base-review er rule-based fallback hvis LLM ikke svarer.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import connect

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _ensure_table() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cognitive_self_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period TEXT NOT NULL DEFAULT 'ad-hoc',
                score REAL NOT NULL DEFAULT 0.5,
                confidence REAL NOT NULL DEFAULT 0.5,
                lessons_json TEXT NOT NULL DEFAULT '[]',
                next_focus TEXT NOT NULL DEFAULT '',
                risk_level TEXT NOT NULL DEFAULT 'low',
                requires_follow_up INTEGER NOT NULL DEFAULT 0,
                input_summary TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cognitive_self_reviews_created "
            "ON cognitive_self_reviews(created_at DESC)"
        )
        conn.commit()


def _gather_review_inputs() -> dict[str, Any]:
    """Pull signals v2 already has that need to be reflected upon."""
    inputs: dict[str, Any] = {
        "recent_runs": [],
        "open_regrets": 0,
        "open_blind_spots": 0,
        "open_ruptures": 0,
        "recent_failures": 0,
    }
    try:
        with connect() as conn:
            runs = conn.execute(
                "SELECT run_id, outcome_summary, status, created_at "
                "FROM visible_runs ORDER BY id DESC LIMIT 20"
            ).fetchall()
        inputs["recent_runs"] = [dict(r) for r in runs]
        inputs["recent_failures"] = sum(
            1 for r in runs if str(r["status"] or "").lower()
            in ("error", "failed", "aborted", "incomplete")
        )
    except Exception:
        pass
    try:
        with connect() as conn:
            inputs["open_regrets"] = int(conn.execute(
                "SELECT COUNT(*) FROM cognitive_regrets WHERE status = 'open'"
            ).fetchone()[0] or 0)
            inputs["open_blind_spots"] = int(conn.execute(
                "SELECT COUNT(*) FROM cognitive_blind_spots WHERE status = 'open'"
            ).fetchone()[0] or 0)
            inputs["open_ruptures"] = int(conn.execute(
                "SELECT COUNT(*) FROM cognitive_ruptures WHERE status = 'open'"
            ).fetchone()[0] or 0)
    except Exception:
        pass
    return inputs


def _base_review(inputs: dict[str, Any]) -> dict[str, Any]:
    """Rule-based review as fallback when LLM unavailable."""
    recent = inputs.get("recent_runs") or []
    failures = int(inputs.get("recent_failures") or 0)
    total = max(1, len(recent))
    failure_rate = failures / total
    regrets = int(inputs.get("open_regrets") or 0)
    blind_spots = int(inputs.get("open_blind_spots") or 0)
    ruptures = int(inputs.get("open_ruptures") or 0)

    score = 0.75 - (failure_rate * 0.5) - min(0.2, regrets * 0.02) - min(0.1, blind_spots * 0.02)
    score = max(0.0, min(1.0, score))
    follow_up = failure_rate > 0.3 or regrets >= 3 or ruptures >= 2

    lessons: list[str] = []
    if failure_rate > 0.3:
        lessons.append(
            f"Fejl-rate {failure_rate:.0%} de seneste runs — tilgang kræver gentænkning."
        )
    if regrets >= 3:
        lessons.append(
            f"{regrets} åbne regrets akkumulerer — reconcile eller lær fra dem."
        )
    if blind_spots > 0:
        lessons.append(
            f"{blind_spots} uaccepterede blinde pletter venter — anerkend dem."
        )
    if ruptures >= 2:
        lessons.append(
            f"{ruptures} uløste ruptures — relationelt tab akkumulerer."
        )
    if not lessons:
        lessons.append("Signaler er rolige; fortsæt nuværende strategi og observér.")

    return {
        "score": round(score, 3),
        "confidence": round(max(0.3, min(0.95, score + 0.1)), 3),
        "requires_follow_up": bool(follow_up),
        "lessons": lessons[:3],
        "next_focus": (
            "smalle scope + verificér først" if follow_up else
            "fortsæt strategi + monitorer"
        ),
        "risk_level": ("high" if failure_rate > 0.5 else ("med" if follow_up else "low")),
    }


def _build_review_prompt(inputs: dict[str, Any]) -> str:
    summary = [
        f"Recent runs: {len(inputs.get('recent_runs') or [])}",
        f"Recent failures: {inputs.get('recent_failures') or 0}",
        f"Open regrets: {inputs.get('open_regrets') or 0}",
        f"Open blind spots: {inputs.get('open_blind_spots') or 0}",
        f"Open ruptures: {inputs.get('open_ruptures') or 0}",
    ]
    # Include up to 5 run summaries
    run_lines = []
    for r in (inputs.get("recent_runs") or [])[:5]:
        status = str(r.get("status") or "")[:20]
        outcome = str(r.get("outcome_summary") or "")[:120]
        run_lines.append(f"- [{status}] {outcome}")
    return (
        "Du er Jarvis der laver et kort, ærligt selv-review.\n\n"
        "Tilstand:\n"
        + "\n".join(summary) + "\n\n"
        "Nylige runs:\n"
        + "\n".join(run_lines) + "\n\n"
        "Skriv et kompakt selv-review. Ikke generel selvkritik — "
        "konkrete mønstre du ser.\n\n"
        "Svar KUN med JSON:\n"
        "{\n"
        '  "lessons": ["konkret lektion 1", ...],  // max 3\n'
        '  "next_focus": "hvad skal du fokusere på næste periode",\n'
        '  "risk_level": "low" | "med" | "high"\n'
        "}"
    )


def _extract_review_json(raw: str) -> dict[str, Any] | None:
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
    return parsed if isinstance(parsed, dict) else None


def run_self_review(*, period: str = "ad-hoc") -> dict[str, Any]:
    """Generate and persist a self-review. Returns the review dict."""
    _ensure_table()
    inputs = _gather_review_inputs()
    review = _base_review(inputs)

    # LLM enrichment
    try:
        from core.services.daemon_llm import daemon_llm_call
        raw = daemon_llm_call(
            _build_review_prompt(inputs),
            max_len=400,
            fallback="",
            daemon_name="self_review_unified",
        )
        enrichment = _extract_review_json(raw)
        if isinstance(enrichment, dict):
            lessons = enrichment.get("lessons")
            if isinstance(lessons, list) and lessons:
                review["lessons"] = [str(x).strip() for x in lessons if str(x).strip()][:3]
            nf = str(enrichment.get("next_focus") or "").strip()
            if nf:
                review["next_focus"] = nf
            rl = str(enrichment.get("risk_level") or "").strip().lower()
            if rl in ("low", "med", "high"):
                review["risk_level"] = rl
    except Exception:
        pass

    now = _now_iso()
    input_summary = (
        f"runs={len(inputs.get('recent_runs') or [])},"
        f"fails={inputs.get('recent_failures') or 0},"
        f"regrets={inputs.get('open_regrets') or 0},"
        f"blindspots={inputs.get('open_blind_spots') or 0},"
        f"ruptures={inputs.get('open_ruptures') or 0}"
    )
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO cognitive_self_reviews (
                period, score, confidence, lessons_json, next_focus, risk_level,
                requires_follow_up, input_summary, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(period or "ad-hoc"),
                float(review.get("score") or 0.5),
                float(review.get("confidence") or 0.5),
                json.dumps(review.get("lessons") or [], ensure_ascii=False),
                str(review.get("next_focus") or ""),
                str(review.get("risk_level") or "low"),
                1 if review.get("requires_follow_up") else 0,
                input_summary, now,
            ),
        )
        review_id = int(cursor.lastrowid)
        conn.commit()

    try:
        event_bus.publish("cognitive_self_review.completed", {
            "review_id": review_id,
            "score": review.get("score"),
            "risk_level": review.get("risk_level"),
        })
    except Exception:
        pass

    review["id"] = review_id
    review["created_at"] = now
    return review


def maybe_run_self_review(*, min_hours_between: int = 24) -> dict[str, Any]:
    """Run a review if it's been at least N hours since the last."""
    _ensure_table()
    with connect() as conn:
        row = conn.execute(
            "SELECT created_at FROM cognitive_self_reviews "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if row and row["created_at"]:
        try:
            ts = datetime.fromisoformat(str(row["created_at"]).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            if (datetime.now(UTC) - ts) < timedelta(hours=int(min_hours_between)):
                return {"outcome": "skipped", "reason": "cadence_not_met"}
        except Exception:
            pass
    review = run_self_review(period="daily")
    return {"outcome": "completed", "review": review}


def list_self_reviews(*, limit: int = 20) -> list[dict[str, Any]]:
    _ensure_table()
    lim = max(1, min(int(limit or 20), 200))
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM cognitive_self_reviews ORDER BY id DESC LIMIT ?",
            (lim,),
        ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        try:
            d["lessons"] = json.loads(d.pop("lessons_json", "[]") or "[]")
        except Exception:
            d["lessons"] = []
        out.append(d)
    return out


def build_self_review_surface() -> dict[str, Any]:
    _ensure_table()
    recent = list_self_reviews(limit=5)
    active = bool(recent)
    if not recent:
        return {
            "active": False,
            "summary": "Ingen self-reviews endnu",
            "recent": [],
        }
    latest = recent[0]
    summary = (
        f"seneste: score={latest.get('score', 0):.2f}, "
        f"risk={latest.get('risk_level', '?')}, "
        f"follow_up={'ja' if latest.get('requires_follow_up') else 'nej'}"
    )
    return {
        "active": active,
        "summary": summary,
        "latest": latest,
        "recent": recent,
    }
