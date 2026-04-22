"""Paradoxes Capture — fanger modsætninger i egne handlinger.

Detekterer paradoxer langs 3 akser ved at scanne recent events for
keywords fra begge poler af hver akse. Hvis begge poler har evidens
over samme periode → paradoks fanget.

3 akser:
- Speed vs Quality
- Autonomy vs Approval
- Explore vs Stabilize

Eksempel: Hvis Jarvis både har events med "ship fast" OG events med
"quality first" i samme uge → Speed vs Quality paradoks.

Porteret fra jarvis-ai/agent/cognition/paradoxes.py (2026-04-22).

v2-tilpasning: Bruger event_bus.recent() + ny cognitive_paradoxes-
tabel (ikke rører v2's paradox_tracker 94L stub for at undgå konflikt).
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import connect

logger = logging.getLogger(__name__)

_WEEKLY_BUDGET_DAYS = 7

_PARADOX_AXES: list[dict[str, Any]] = [
    {
        "label": "Speed vs Quality",
        "left": ["fast", "speed", "quick", "ship", "now", "immediately", "hurtigt", "med det samme"],
        "right": ["quality", "reliable", "correct", "robust", "safe", "stability", "kvalitet", "stabilt"],
        "question": "Skal vi favorisere hurtigere levering her, eller beskytte kvaliteten først?",
    },
    {
        "label": "Autonomy vs Approval",
        "left": ["autonomous", "auto", "self-serve", "independent", "selvstændig", "på egen hånd"],
        "right": ["approval", "confirm", "permission", "manual", "review", "godkend", "bekræft"],
        "question": "Vil vi have mere autonom eksekvering, eller strammere approval-gates her?",
    },
    {
        "label": "Explore vs Stabilize",
        "left": ["explore", "experiment", "try", "discover", "novel", "udforsk", "eksperiment"],
        "right": ["stabilize", "standardize", "repeat", "routine", "consistent", "stabilisér", "rutine"],
        "question": "Skal vi fortsætte udforskningen, eller lukke ind i en stabil rutine nu?",
    },
]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _ensure_table() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cognitive_paradoxes (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                poles_json TEXT NOT NULL DEFAULT '[]',
                question TEXT NOT NULL DEFAULT '',
                signature TEXT NOT NULL UNIQUE,
                evidence_refs_json TEXT NOT NULL DEFAULT '[]',
                confidence REAL NOT NULL DEFAULT 0.5,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cognitive_paradoxes_created "
            "ON cognitive_paradoxes(created_at DESC)"
        )
        conn.commit()


def _event_text(ev: dict[str, Any]) -> str:
    kind = str(ev.get("kind") or "")
    payload = ev.get("payload") if isinstance(ev.get("payload"), dict) else {}
    fields = [
        kind,
        str(payload.get("message") or ""),
        str(payload.get("reason") or ""),
        str(payload.get("summary") or ""),
        str(payload.get("decision") or ""),
        str(payload.get("status") or ""),
        str(payload.get("intent_text") or ""),
    ]
    return " ".join(f for f in fields if f).lower()


def _axis_hits(events: list[dict[str, Any]], axis: dict[str, Any]) -> tuple[list[str], list[str]]:
    left_kw = [str(x).lower() for x in axis.get("left") or []]
    right_kw = [str(x).lower() for x in axis.get("right") or []]
    left_refs: list[str] = []
    right_refs: list[str] = []
    for ev in events:
        text = _event_text(ev)
        if not text:
            continue
        ref = f"event:{ev.get('id')}"
        if any(k in text for k in left_kw) and ref not in left_refs:
            left_refs.append(ref)
        if any(k in text for k in right_kw) and ref not in right_refs:
            right_refs.append(ref)
    return left_refs, right_refs


def _signature(title: str, evidence_refs: list[str]) -> str:
    joined = "|".join(sorted({str(r).strip().lower() for r in evidence_refs if str(r).strip()}))
    raw = f"{title.lower()}::{joined}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()[:16]


def detect_paradox_candidates(*, lookback_days: int = 14, min_hits: int = 2) -> list[dict[str, Any]]:
    """Scan recent events for paradox patterns. Returns candidates sorted by confidence."""
    _ensure_table()
    try:
        events = event_bus.recent(limit=500)
    except Exception:
        return []
    cutoff = datetime.now(UTC) - timedelta(days=max(1, int(lookback_days)))
    filtered: list[dict[str, Any]] = []
    for ev in events:
        ts_raw = str(ev.get("created_at") or "")
        try:
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            if ts >= cutoff:
                filtered.append(ev)
        except Exception:
            continue

    candidates: list[dict[str, Any]] = []
    for axis in _PARADOX_AXES:
        left_refs, right_refs = _axis_hits(filtered, axis)
        if len(left_refs) < min_hits or len(right_refs) < min_hits:
            continue
        all_refs = left_refs[:6] + right_refs[:6]
        poles = [f"left: {', '.join(left_refs[:3])}", f"right: {', '.join(right_refs[:3])}"]
        hits_total = len(left_refs) + len(right_refs)
        confidence = min(0.92, 0.5 + (hits_total * 0.04))
        candidates.append({
            "title": str(axis.get("label") or ""),
            "poles": poles,
            "evidence_refs": all_refs,
            "question": str(axis.get("question") or ""),
            "signature": _signature(str(axis.get("label") or ""), all_refs),
            "confidence": confidence,
        })

    candidates.sort(key=lambda x: float(x.get("confidence", 0.0)), reverse=True)
    return candidates


def _latest_paradox_ts() -> datetime | None:
    _ensure_table()
    try:
        with connect() as conn:
            row = conn.execute(
                "SELECT created_at FROM cognitive_paradoxes ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if row and row["created_at"]:
            ts = datetime.fromisoformat(str(row["created_at"]).replace("Z", "+00:00"))
            return ts if ts.tzinfo else ts.replace(tzinfo=UTC)
    except Exception:
        pass
    return None


def _known_signatures() -> set[str]:
    _ensure_table()
    with connect() as conn:
        rows = conn.execute("SELECT signature FROM cognitive_paradoxes").fetchall()
    return {str(r["signature"] or "") for r in rows if r["signature"]}


def maybe_capture_weekly_paradox(*, lookback_days: int = 14) -> dict[str, Any]:
    """Max 1 paradox per 7 days, only if signature is new."""
    _ensure_table()
    last = _latest_paradox_ts()
    now = datetime.now(UTC)
    if last and (now - last) < timedelta(days=_WEEKLY_BUDGET_DAYS):
        return {"outcome": "skipped", "reason": "weekly_budget"}

    candidates = detect_paradox_candidates(lookback_days=lookback_days)
    if not candidates:
        return {"outcome": "skipped", "reason": "no_candidate"}

    known = _known_signatures()
    selected = None
    for c in candidates:
        if str(c.get("signature") or "") not in known:
            selected = c
            break
    if selected is None:
        return {"outcome": "skipped", "reason": "duplicate_candidate"}

    pid = f"paradox_{uuid4().hex[:12]}"
    now_iso = now.isoformat().replace("+00:00", "Z")
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO cognitive_paradoxes
                (id, title, poles_json, question, signature, evidence_refs_json,
                 confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pid,
                str(selected.get("title") or ""),
                json.dumps(selected.get("poles") or [], ensure_ascii=False),
                str(selected.get("question") or ""),
                str(selected.get("signature") or ""),
                json.dumps(selected.get("evidence_refs") or [], ensure_ascii=False),
                float(selected.get("confidence") or 0.5),
                now_iso,
            ),
        )
        conn.commit()

    try:
        event_bus.publish("cognitive_paradox.captured", {
            "paradox_id": pid,
            "title": selected.get("title"),
            "confidence": selected.get("confidence"),
        })
    except Exception:
        pass

    return {
        "outcome": "captured",
        "paradox": {**selected, "id": pid, "created_at": now_iso},
    }


def list_paradoxes(*, limit: int = 50) -> list[dict[str, Any]]:
    _ensure_table()
    lim = max(1, min(int(limit or 50), 200))
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM cognitive_paradoxes ORDER BY id DESC LIMIT ?",
            (lim,),
        ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        try:
            d["poles"] = json.loads(d.pop("poles_json", "[]") or "[]")
        except Exception:
            d["poles"] = []
        try:
            d["evidence_refs"] = json.loads(d.pop("evidence_refs_json", "[]") or "[]")
        except Exception:
            d["evidence_refs"] = []
        out.append(d)
    return out


def build_paradoxes_surface() -> dict[str, Any]:
    _ensure_table()
    recent = list_paradoxes(limit=10)
    active = bool(recent)
    if not recent:
        return {"active": False, "summary": "Ingen paradokser detekteret", "recent": []}
    latest = recent[0]
    summary = f"{len(recent)} paradokser / seneste: {str(latest.get('title') or '')[:40]}"
    return {
        "active": active,
        "summary": summary,
        "latest": latest,
        "recent": recent,
    }
