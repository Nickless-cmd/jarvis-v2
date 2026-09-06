"""Proactive candidates — the ONE queue for "Jarvis wants to tell Bjørn something".

Replaces the two nudge wells as a decision surface (redesign 2026-09-04):

* `outbound_nudges` (DB): 506 nudges/7 days, 0 ever sent, 89 % "Autonom run ✓
  færdig"; the prompt asked Jarvis to call a tool that did not exist, from
  inside a block that told him never to mention it.
* `nudge_broend.json`: 751 pending, all autonomous-run telemetry, 0 sent.

Now:
* telemetry ("run finished") never becomes a candidate — it is an event;
* real messages land here with a priority and are delivered by
  `proactivity_bridge` (presence-gated, digest, cap) — no tool call needed;
* in conversation, at most ONE relevant pending item is shown as a
  "Siden sidst" line, and it counts as delivered when Jarvis mentions it.

Statuses: pending → surfaced (sent by the bridge) | mentioned (Jarvis said it
in a reply) | dismissed | expired.
"""
from __future__ import annotations

import logging
import re
import sqlite3
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from core.runtime.db import connect

logger = logging.getLogger(__name__)

PRIORITIES = ("low", "medium", "high", "critical")
_URGENT = frozenset({"high", "critical"})
_DEDUPE_HOURS = 24
_EXPIRE_DAYS = 7
_MAX_PENDING = 100

_TERM_RE = re.compile(r"[0-9A-Za-zÆØÅæøå]+")
_STOP = frozenset({
    "hvad", "hvor", "hvilken", "hvilket", "hvilke", "hvorfor", "hvornår", "hvordan",
    "blev", "var", "har", "havde", "det", "der", "den", "til", "fra", "med", "for", "som",
    "jeg", "mig", "du", "dig", "vores", "mine", "dine", "siger", "sagde", "om", "og", "kan",
    "skal", "ikke", "eller", "the", "what", "when", "where", "why", "how", "did", "does",
    "was", "were", "about", "with", "from", "your", "run", "autonom", "reviewe", "vil",
})

_SHOWN: dict[str, tuple[float, list[str]]] = {}
_SHOWN_TTL_S = 900.0


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _terms(text: str) -> set[str]:
    out: set[str] = set()
    for raw in _TERM_RE.findall(str(text or "").replace("-", " ")):
        t = raw.lower()
        if len(t) >= 3 and t not in _STOP:
            out.add(t)
    return out


def lexical_coverage(query: str, text: str) -> float:
    q = _terms(query)
    if not q:
        return 0.0
    return min(1.0, len(q & _terms(text)) / max(1, min(len(q), 5)))


def _norm_text(text: str) -> str:
    return " ".join(str(text or "").lower().split())[:300]


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS proactive_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT '',
            text TEXT NOT NULL,
            norm_text TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'medium',
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            surfaced_at TEXT NOT NULL DEFAULT '',
            mentioned_run_id TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_proactive_candidates_status ON proactive_candidates(status, created_at)")


def _row(r: Any) -> dict[str, Any]:
    if isinstance(r, sqlite3.Row):
        return dict(r)
    cols = ["id", "candidate_id", "source", "kind", "text", "norm_text", "priority", "status",
            "created_at", "updated_at", "surfaced_at", "mentioned_run_id"]
    return dict(zip(cols, r))


def normalize_priority(importance: str) -> str:
    v = str(importance or "").strip().lower()
    if v in PRIORITIES:
        return v
    if v in {"normal", ""}:
        return "medium"
    return "medium"


def add_candidate(*, source: str, text: str, priority: str = "medium", kind: str = "") -> dict[str, Any]:
    """Queue a message for Bjørn. Deduped on normalized text within 24 h.
    Returns {"status": "added"|"duplicate"|"skipped", "candidate_id": ...}."""
    body = " ".join(str(text or "").split()).strip()
    if len(body) < 8:
        return {"status": "skipped", "reason": "empty"}
    norm = _norm_text(body)
    now = _now_iso()
    cutoff = (datetime.now(UTC) - timedelta(hours=_DEDUPE_HOURS)).isoformat()
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        ensure_table(conn)
        dup = conn.execute(
            "SELECT candidate_id FROM proactive_candidates WHERE norm_text = ? AND created_at > ? "
            "AND status IN ('pending', 'surfaced', 'mentioned') LIMIT 1",
            (norm, cutoff),
        ).fetchone()
        if dup is not None:
            return {"status": "duplicate", "candidate_id": dup[0]}
        cid = f"pc-{uuid4().hex[:12]}"
        conn.execute(
            "INSERT INTO proactive_candidates (candidate_id, source, kind, text, norm_text, priority, "
            "status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)",
            (cid, str(source or "unknown")[:80], str(kind or "")[:50], body[:1000], norm,
             normalize_priority(priority), now, now),
        )
        # cap: the oldest pending beyond the limit expire
        rows = conn.execute(
            "SELECT candidate_id FROM proactive_candidates WHERE status='pending' ORDER BY created_at DESC"
        ).fetchall()
        if len(rows) > _MAX_PENDING:
            old = [r[0] for r in rows[_MAX_PENDING:]]
            conn.execute(
                f"UPDATE proactive_candidates SET status='expired', updated_at=? WHERE candidate_id IN "
                f"({','.join('?' for _ in old)})", [now, *old],
            )
        conn.commit()
    return {"status": "added", "candidate_id": cid}


def list_pending(*, limit: int = 20, priorities: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    sql = "SELECT * FROM proactive_candidates WHERE status='pending'"
    params: list[Any] = []
    if priorities:
        sql += f" AND priority IN ({','.join('?' for _ in priorities)})"
        params.extend(priorities)
    sql += " ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, created_at DESC LIMIT ?"
    params.append(int(limit))
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        ensure_table(conn)
        return [_row(r) for r in conn.execute(sql, params).fetchall()]


def mark(candidate_ids: list[str], status: str, *, run_id: str = "") -> int:
    if not candidate_ids:
        return 0
    if status not in {"surfaced", "mentioned", "dismissed", "expired", "pending"}:
        raise ValueError(f"bad status {status}")
    now = _now_iso()
    with connect() as conn:
        ensure_table(conn)
        ph = ",".join("?" for _ in candidate_ids)
        extra = ", surfaced_at=?" if status == "surfaced" else ""
        extra_params = [now] if status == "surfaced" else []
        cur = conn.execute(
            f"UPDATE proactive_candidates SET status=?, updated_at=?{extra}, "
            f"mentioned_run_id=CASE WHEN ? != '' THEN ? ELSE mentioned_run_id END "
            f"WHERE candidate_id IN ({ph}) AND status='pending'",
            [status, now, *extra_params, run_id, run_id, *candidate_ids],
        )
        conn.commit()
        return int(cur.rowcount or 0)


def expire_stale(*, days: int = _EXPIRE_DAYS) -> int:
    cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    now = _now_iso()
    with connect() as conn:
        ensure_table(conn)
        cur = conn.execute(
            "UPDATE proactive_candidates SET status='expired', updated_at=? WHERE status='pending' AND created_at < ?",
            (now, cutoff),
        )
        conn.commit()
        return int(cur.rowcount or 0)


def counts() -> dict[str, int]:
    with connect() as conn:
        ensure_table(conn)
        return {str(k): int(v) for k, v in conn.execute(
            "SELECT status, count(*) FROM proactive_candidates GROUP BY status").fetchall()}


# ── in-conversation surface ─────────────────────────────────────────────


def relevant_for(user_message: str, *, limit: int = 1, min_coverage: float = 0.34) -> list[dict[str, Any]]:
    """Pending items lexically relevant to what Bjørn just wrote (best first)."""
    msg = str(user_message or "").strip()
    if len(msg) < 8:
        return []
    scored = []
    for c in list_pending(limit=60):
        cov = lexical_coverage(msg, f"{c.get('text', '')}")
        if cov >= min_coverage:
            scored.append((cov, c))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [c for _cov, c in scored[:limit]]


def remember_shown(session_id: str, candidate_ids: list[str]) -> None:
    sid = str(session_id or "").strip()
    if not sid or not candidate_ids:
        return
    now = time.time()
    _SHOWN[sid] = (now, list(candidate_ids))
    for k, (ts, _ids) in list(_SHOWN.items()):
        if now - ts > _SHOWN_TTL_S:
            _SHOWN.pop(k, None)


def build_since_last_line(user_message: str, *, session_id: str = "") -> str:
    """At most ONE line: 'Siden sidst: …' when a pending item is relevant to the message."""
    try:
        items = relevant_for(user_message, limit=1)
    except Exception as exc:
        logger.debug("proactive_candidates: relevant_for failed: %s", exc)
        return ""
    if not items:
        return ""
    item = items[0]
    remember_shown(session_id, [str(item.get("candidate_id") or "")])
    text = " ".join(str(item.get("text") or "").split())[:240]
    return f"Siden sidst (relevant for det du skriver — nævn det hvis det passer ind): {text}"


def mark_mentioned_if_overlap(*, session_id: str, answer_text: str, run_id: str = "", min_coverage: float = 0.5) -> int:
    """Auto-deliver: the shown item counts as delivered when Jarvis' answer overlaps it."""
    sid = str(session_id or "").strip()
    item = _SHOWN.get(sid)
    if not item:
        return 0
    ts, ids = item
    if time.time() - ts > _SHOWN_TTL_S or not ids:
        _SHOWN.pop(sid, None)
        return 0
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        ensure_table(conn)
        ph = ",".join("?" for _ in ids)
        rows = [_row(r) for r in conn.execute(
            f"SELECT * FROM proactive_candidates WHERE candidate_id IN ({ph}) AND status='pending'", ids
        ).fetchall()]
    hit = [str(r["candidate_id"]) for r in rows
           if lexical_coverage(str(r.get("text") or ""), answer_text) >= min_coverage]
    if not hit:
        return 0
    _SHOWN.pop(sid, None)
    return mark(hit, "mentioned", run_id=run_id)


# ── bridge integration ──────────────────────────────────────────────────


def bridge_candidates() -> list[dict[str, Any]]:
    """Shape expected by proactivity_bridge.collect_candidates()."""
    out = []
    for c in list_pending(limit=30):
        out.append({
            "kind": str(c.get("kind") or "candidate"),
            "text": str(c.get("text") or ""),
            "priority": str(c.get("priority") or "medium"),
            "source": "proactive_candidates",
            "source_id": str(c.get("candidate_id") or ""),
            "ts": str(c.get("created_at") or ""),
        })
    return out


def build_proactive_candidates_surface() -> dict[str, Any]:
    try:
        c = counts()
    except Exception:
        c = {}
    return {"active": bool(c), "counts": c, "summary": f"{c.get('pending', 0)} pending proactive candidates"}
