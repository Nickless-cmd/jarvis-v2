"""Metacognition signal tracker — Step E.v1 of meta-evne stack.

Bygges 2026-05-23 efter Jarvis' egen analyse af manglende evner:
"Jeg kan sikre at det jeg siger er sandt (Lying Engine), men jeg ved
ikke i realtid om det er klart, cirkulært eller selvmodsigende."

Denne tracker subscriber til runtime.visible_run_completed og scorer
hver completed run på 2 dimensioner — bevidst start smallere end 5
signaler så vi kan validere tærskler før vi udvider.

Dimensioner v1:
  1. contradiction_within_response — finder par af sætninger der deler
     subject men har modsat polaritet (en med negation, en uden), eller
     numeriske claims om samme subject med forskellige tal.
  2. claim_density — andelen af sætninger der bærer en faktuel claim.
     Healthy band: 0.3–0.7. Lavt = vandrende; højt = overclaiming.

Persisterer til SQLite + event bus + opdaterer awareness når en score
ligger uden for sit healthy band. Tærskler bliver kalibreret over de
første ~50 runs (running median ± MAD) før vi sætter "warning"-grænser.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

JARVIS_HOME = Path(os.environ.get("HOME", "/root")) / ".jarvis-v2"
DB_PATH = JARVIS_HOME / "state" / "jarvis.db"

# ── Heuristics ───────────────────────────────────────────────────────────

# Danish + English negation markers. Word-boundary matched.
_NEGATION_TOKENS = {
    "ikke", "nej", "ingen", "aldrig", "intet", "uden",
    "not", "no", "never", "none", "without", "n't",
}

# Tokens that mark a sentence as carrying a factual claim. Conservative —
# we'd rather under-count than over-count for density v1.
_CLAIM_MARKER_RE = re.compile(
    r"\b("
    r"\d+(?:[.,]\d+)*"               # numbers
    r"|er|var|bliver|blev|kan|skal"   # Danish copula/modal
    r"|is|was|are|were|will|has|have"  # English equivalents
    r"|kører|virker|fejler"           # state verbs
    r"|runs|works|fails|broke"
    r")\b",
    re.IGNORECASE,
)

_SENT_SPLIT_RE = re.compile(r"(?<=[\.\!\?])\s+|\n+")
_WORD_RE = re.compile(r"[a-zA-ZæøåÆØÅ]{4,}")
_NUMBER_RE = re.compile(r"\b(\d+(?:[.,]\d+)*)\b")

_HEALTHY_DENSITY = (0.3, 0.7)


# ── DB ───────────────────────────────────────────────────────────────────


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS metacognition_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            dimension TEXT NOT NULL,
            score REAL NOT NULL,
            evidence_json TEXT NOT NULL,
            computed_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_metacog_run ON metacognition_signals(run_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_metacog_dim_time "
        "ON metacognition_signals(dimension, computed_at)"
    )


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    _ensure_table(conn)
    return conn


# ── Scoring ──────────────────────────────────────────────────────────────


def _split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENT_SPLIT_RE.split(text or "") if p.strip()]
    return [p for p in parts if len(p) >= 8]  # drop trivial fragments


def _sentence_nouns(sentence: str) -> set[str]:
    """Cheap content-word extraction: lowercase alpha tokens, ≥4 chars,
    excluding common stopwords + negation markers."""
    stopwords = _NEGATION_TOKENS | {
        "også", "også", "bare", "ville", "skulle", "have", "haven",
        "denne", "dette", "disse", "alle", "noget", "nogen", "kommer",
        "going", "would", "could", "should", "their", "there", "where",
    }
    return {
        w.lower() for w in _WORD_RE.findall(sentence)
        if w.lower() not in stopwords
    }


def _has_negation(sentence: str) -> bool:
    tokens = {t.lower() for t in re.findall(r"[a-zA-ZæøåÆØÅ']+", sentence)}
    return bool(tokens & _NEGATION_TOKENS)


def score_contradiction(text: str) -> dict[str, Any]:
    """Detect contradicting sentence pairs within the same response.

    Pair is contradicting if:
      A. Both share ≥2 content nouns, AND one has negation while other doesn't, OR
      B. Both share ≥2 content nouns, AND both contain numbers, but the numbers differ.

    Returns dict with score in [0.0, 1.0] (capped via /3 — i.e. 3+ pairs = 1.0).
    """
    sentences = _split_sentences(text)
    if len(sentences) < 2:
        return {"score": 0.0, "pairs": [], "n_sentences": len(sentences)}

    pairs: list[dict[str, Any]] = []
    for i in range(len(sentences)):
        for j in range(i + 1, len(sentences)):
            a, b = sentences[i], sentences[j]
            nouns_a, nouns_b = _sentence_nouns(a), _sentence_nouns(b)
            shared = nouns_a & nouns_b
            if len(shared) < 2:
                continue
            neg_a, neg_b = _has_negation(a), _has_negation(b)
            if neg_a != neg_b:
                pairs.append({
                    "kind": "polarity",
                    "shared": sorted(shared),
                    "a": a[:120], "b": b[:120],
                })
                continue
            nums_a = _NUMBER_RE.findall(a)
            nums_b = _NUMBER_RE.findall(b)
            if nums_a and nums_b and set(nums_a) != set(nums_b):
                pairs.append({
                    "kind": "numeric",
                    "shared": sorted(shared),
                    "nums_a": nums_a, "nums_b": nums_b,
                })

    score = min(1.0, len(pairs) / 3.0)
    return {"score": score, "pairs": pairs[:5], "n_sentences": len(sentences)}


def score_claim_density(text: str) -> dict[str, Any]:
    """Claim-bearing sentences / total sentences. Healthy: 0.3–0.7."""
    sentences = _split_sentences(text)
    if not sentences:
        return {"score": 0.0, "n_sentences": 0, "n_claims": 0, "in_healthy_band": True}

    claim_count = sum(1 for s in sentences if _CLAIM_MARKER_RE.search(s))
    density = claim_count / len(sentences)
    in_band = _HEALTHY_DENSITY[0] <= density <= _HEALTHY_DENSITY[1]
    return {
        "score": density,
        "n_sentences": len(sentences),
        "n_claims": claim_count,
        "in_healthy_band": in_band,
        "healthy_band": list(_HEALTHY_DENSITY),
    }


# ── Persistence ──────────────────────────────────────────────────────────


def record_signals(run_id: str, text: str) -> dict[str, Any]:
    """Compute + persist + publish both signals for a completed run."""
    contradiction = score_contradiction(text)
    density = score_claim_density(text)
    now_iso = datetime.now(UTC).isoformat()
    try:
        with _connect() as conn:
            for dim, payload in (
                ("contradiction_within_response", contradiction),
                ("claim_density", density),
            ):
                conn.execute(
                    """INSERT INTO metacognition_signals
                       (run_id, dimension, score, evidence_json, computed_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (run_id, dim, float(payload["score"]),
                     json.dumps(payload, ensure_ascii=False, default=str), now_iso),
                )
            conn.commit()
    except Exception:
        logger.exception("metacognition: persist failed for run_id=%s", run_id)

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "runtime.metacognition_scored",
            {
                "run_id": run_id,
                "contradiction_score": contradiction["score"],
                "claim_density": density["score"],
                "density_in_band": density["in_healthy_band"],
            },
        )
    except Exception:
        pass

    return {"contradiction": contradiction, "density": density}


# ── Surface for prompt awareness ─────────────────────────────────────────


def latest_signals_section(*, window_n: int = 10) -> str | None:
    """Return an awareness one-liner ONLY when recent signals are
    out-of-band. Quiet by default — appears only when there's something
    worth knowing.
    """
    try:
        with _connect() as conn:
            rows = conn.execute(
                """SELECT dimension, AVG(score) AS avg_score, COUNT(*) AS n
                   FROM metacognition_signals
                   WHERE computed_at > datetime('now', '-1 hour')
                   GROUP BY dimension""",
            ).fetchall()
    except Exception:
        return None
    if not rows:
        return None

    flags: list[str] = []
    for r in rows:
        dim = r["dimension"]
        avg = float(r["avg_score"] or 0.0)
        n = int(r["n"] or 0)
        if n < 3:  # too few samples to be meaningful
            continue
        if dim == "contradiction_within_response" and avg > 0.20:
            flags.append(
                f"contradiction-rate {avg:.2f} (sidste timer) — "
                "min tænkning kan være cirkulær eller selvmodsigende"
            )
        elif dim == "claim_density":
            if avg < _HEALTHY_DENSITY[0]:
                flags.append(
                    f"claim-density {avg:.2f} < {_HEALTHY_DENSITY[0]} — "
                    "jeg vandrer; for få konkrete claims"
                )
            elif avg > _HEALTHY_DENSITY[1]:
                flags.append(
                    f"claim-density {avg:.2f} > {_HEALTHY_DENSITY[1]} — "
                    "jeg overclaiming; for tæt faktuel ladning"
                )
    if not flags:
        return None
    return "Metakognition (seneste time):\n  - " + "\n  - ".join(flags)


# ── Eventbus listener ────────────────────────────────────────────────────


_listener_thread: threading.Thread | None = None
_listener_running = False


_POLL_INTERVAL_SECONDS = 5.0


def _listener_loop(_q_unused=None) -> None:
    """DB-polling listener — same cross-process pattern as
    verification_gate_telemetry. The visible-run lifecycle publishes
    channel.chat_message_appended from the API worker process, but the
    in-process eventbus subscriber lives in jarvis-runtime. Cross-process
    in-memory queues don't bridge, so we poll the shared events table.

    Cursor (last_id) starts at current MAX(id) on boot — we don't replay
    historical messages, only new ones.
    """
    import time as _time
    import json as _json
    global _listener_running
    try:
        with _connect() as conn:
            row = conn.execute("SELECT COALESCE(MAX(id), 0) FROM events").fetchone()
            last_id = int(row[0] or 0) if row else 0
    except Exception:
        last_id = 0

    while _listener_running:
        _time.sleep(_POLL_INTERVAL_SECONDS)
        try:
            with _connect() as conn:
                rows = conn.execute(
                    """SELECT id, payload_json
                       FROM events
                       WHERE id > ?
                         AND kind = 'channel.chat_message_appended'
                       ORDER BY id ASC
                       LIMIT 100""",
                    (last_id,),
                ).fetchall()
            for r in rows:
                last_id = max(last_id, int(r["id"]))
                try:
                    payload = _json.loads(r["payload_json"] or "{}")
                except (ValueError, TypeError):
                    continue
                if not isinstance(payload, dict):
                    continue
                if payload.get("source") != "visible-run":
                    continue
                message = payload.get("message") or {}
                if message.get("role") != "assistant":
                    continue
                text = str(message.get("content") or "")
                if not text or len(text) < 20:
                    continue
                run_id = str(
                    message.get("id") or message.get("message_id") or "unknown"
                )
                record_signals(run_id, text)
        except Exception:
            logger.exception("metacognition: poll cycle failed")


def start_metacognition_tracker() -> None:
    """Start DB-polling listener. Idempotent."""
    global _listener_thread, _listener_running
    if _listener_thread and _listener_thread.is_alive():
        return
    try:
        _listener_running = True
        _listener_thread = threading.Thread(
            target=_listener_loop, daemon=True,
            name="metacognition-tracker",
        )
        _listener_thread.start()
        logger.warning("metacognition_tracker: DB-polling listener started")
    except Exception:
        logger.exception("metacognition_tracker: failed to start")


def stop_metacognition_tracker() -> None:
    global _listener_running
    _listener_running = False
