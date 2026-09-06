"""Gentagne anmodninger → regel-forslag (lærings-sløjfe 2026-09-04, blok C).

Tredje gang Bjørn beder om det samme er det ikke en anmodning længere, det er
en regel han ikke burde skulle gentage. Indtil nu kunne intet i systemet se det:

* `session_topics` talte emner op hver tredje tur — 5.112 rækker, ingen læser,
  og sektionen stod på prompt-sortlisten siden 22/6.
* `candidate_tracking._message_matches_candidate` kunne genkende gentagelse for
  præcis FEM hårdkodede canonical keys. En anmodning formuleret i ord uden for
  de fem mønstre gav ingen bevis-optrapning overhovedet.

Nu: spørgsmål 2 i lærings-sløjfen ("hvad bad han om, i fem ord") giver en
normaliseret anmodning pr. tur. Den tælles her på tværs af sessioner. Ved
`_MATURE_AT_MENTIONS` gentagelser fordelt på mindst `_MATURE_AT_SESSIONS`
sessioner stilles ÉT spørgsmål i den proaktive kø. Bjørns ja skriver linjen i
`## Kerne` med begrundelse; hans nej gemmes, så han ikke bliver spurgt igen.

Rettelser går samme vej: anden gang han retter det samme, aktiverer
lessons-lageret lektien af sig selv (`_ACTIVATE_AT_EVIDENCE = 2`) — her
tilføjes forslaget om at gøre den til en fast Kerne-linje.
"""
from __future__ import annotations

import logging
import re
import sqlite3
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.runtime.db import connect

logger = logging.getLogger(__name__)

# En anmodning skal gentages tre gange over mindst to samtaler; en RETTELSE
# skal kun gentages én gang. At blive rettet om det samme to gange er allerede
# for meget — lessons-lageret aktiverer selv lektien ved to (`_ACTIVATE_AT_EVIDENCE`).
_MATURE_AT_MENTIONS = 3
_MATURE_AT_SESSIONS = 2
_CORRECTION_AT_MENTIONS = 2
_CORRECTION_AT_SESSIONS = 1
_MIN_LENGTH = 8
_STEM_CHARS = 6
# Under dette er det to forskellige anmodninger. Over: samme anmodning, andre ord.
_SAME_REQUEST_SIMILARITY = 0.6
_TERM_RE = re.compile(r"[0-9A-Za-zÆØÅæøå]+")
_STOP = frozenset({
    "kan", "du", "lige", "vil", "skal", "det", "den", "der", "til", "fra", "med",
    "for", "som", "jeg", "mig", "min", "mine", "og", "en", "et", "at", "please",
    "the", "you", "can", "would", "could", "my", "and", "for", "with",
})

STATUS_OPEN = "open"
STATUS_ASKED = "asked"
STATUS_RULE = "rule"
STATUS_DECLINED = "declined"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _stems(text: str) -> set[str]:
    """Betydningsbærende ord, forkortet til deres første `_STEM_CHARS` tegn.

    Dansk boejer i ENDEN af ordet, saa en praefiks-afkortning faar «commit»,
    «committe» og «committer» til at falde sammen — uden en ordbog. Grovt, men
    det er praecis den variation Bjoern skriver i: samme anmodning, ny boejning.
    """
    out: set[str] = set()
    for raw in _TERM_RE.findall(str(text or "").replace("-", " ")):
        term = raw.lower()
        if len(term) < 3 or term in _STOP:
            continue
        out.add(term[:_STEM_CHARS])
    return out


def normalize(text: str) -> str:
    """Anmodningens stammer, sorteret — noeglen en anmodning gemmes under."""
    return " ".join(sorted(_stems(text)))[:200]


def similarity(a: str, b: str) -> float:
    """Jaccard mellem to anmodningers stammer (0-1)."""
    sa, sb = _stems(a), _stems(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS repeated_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL UNIQUE,
            norm_text TEXT NOT NULL UNIQUE,
            text TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT 'request',
            status TEXT NOT NULL DEFAULT 'open',
            mention_count INTEGER NOT NULL DEFAULT 1,
            session_ids TEXT NOT NULL DEFAULT '',
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            decided_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_repeated_requests_status "
        "ON repeated_requests(status, last_seen)"
    )


def _row(r: Any) -> dict[str, Any]:
    return dict(r) if isinstance(r, sqlite3.Row) else dict(r or {})


def _sessions(raw: str) -> list[str]:
    return [s for s in str(raw or "").split("|") if s]


def note_request(
    *, text: str, session_id: str = "", kind: str = "request",
) -> dict[str, Any]:
    """Tæl én anmodning. Returnerer rækken plus ``matured`` når den nu er en regel-kandidat."""
    body = " ".join(str(text or "").split()).strip()
    norm = normalize(body)
    if len(body) < _MIN_LENGTH or not norm:
        return {"status": "skipped", "reason": "too-short"}
    sid = str(session_id or "").strip()
    now = _now()
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        ensure_table(conn)
        existing = _row(conn.execute(
            "SELECT * FROM repeated_requests WHERE norm_text = ?", (norm,)).fetchone() or {})
        if not existing:
            # Ikke ordret den samme — men er det den samme ANMODNING? Bjoern
            # skriver sjaeldent det samme to gange paa praecis samme maade.
            for row in conn.execute(
                "SELECT * FROM repeated_requests ORDER BY last_seen DESC LIMIT 200"
            ).fetchall():
                cand = _row(row)
                if str(cand.get("kind") or "request") != str(kind or "request"):
                    continue
                if similarity(body, str(cand.get("text") or "")) >= _SAME_REQUEST_SIMILARITY:
                    existing = cand
                    norm = str(cand.get("norm_text") or norm)
                    break
        if not existing:
            rid = f"req-{uuid4().hex[:12]}"
            conn.execute(
                "INSERT INTO repeated_requests (request_id, norm_text, text, kind, status, "
                "mention_count, session_ids, first_seen, last_seen) "
                "VALUES (?, ?, ?, ?, 'open', 1, ?, ?, ?)",
                (rid, norm, body[:400], str(kind or "request")[:40], sid, now, now),
            )
            conn.commit()
            return {"status": "new", "request_id": rid, "mention_count": 1,
                    "session_count": 1 if sid else 0, "matured": False}
        sessions = _sessions(existing.get("session_ids", ""))
        if sid and sid not in sessions:
            sessions.append(sid)
        mentions = int(existing.get("mention_count") or 0) + 1
        conn.execute(
            "UPDATE repeated_requests SET mention_count = ?, session_ids = ?, "
            "text = ?, last_seen = ? WHERE norm_text = ?",
            (mentions, "|".join(sessions[-20:]), body[:400], now, norm),
        )
        conn.commit()
    is_correction = str(kind or "") == "correction"
    need_mentions = _CORRECTION_AT_MENTIONS if is_correction else _MATURE_AT_MENTIONS
    need_sessions = _CORRECTION_AT_SESSIONS if is_correction else _MATURE_AT_SESSIONS
    matured = (
        str(existing.get("status") or "") == STATUS_OPEN
        and mentions >= need_mentions
        and len(sessions) >= need_sessions
    )
    return {
        "status": "counted", "request_id": str(existing.get("request_id") or ""),
        "mention_count": mentions, "session_count": len(sessions), "matured": matured,
        "text": body,
    }


def build_question(*, text: str, mention_count: int, session_count: int, kind: str) -> str:
    """Det ene spørgsmål Bjørn får at se. Konkret, med tallet der udløste det."""
    body = " ".join(str(text or "").split()).strip().rstrip(".")
    if kind == "correction":
        return (
            f"Du har rettet mig om det samme {mention_count} gange: «{body}». "
            "Skal jeg gøre det til en fast regel i Kerne, så jeg ikke skal rettes igen?"
        )
    return (
        f"Du har bedt om det samme {mention_count} gange fordelt på "
        f"{session_count} samtaler: «{body}». Skal det være en fast regel, "
        "så du ikke skal bede om det?"
    )


def mark_asked(request_id: str) -> int:
    with connect() as conn:
        ensure_table(conn)
        cur = conn.execute(
            "UPDATE repeated_requests SET status = ?, last_seen = ? "
            "WHERE request_id = ? AND status = ?",
            (STATUS_ASKED, _now(), str(request_id or ""), STATUS_OPEN),
        )
        conn.commit()
        return int(cur.rowcount or 0)


def record_decision(*, request_id: str, accepted: bool) -> dict[str, Any]:
    """Bjørns svar. Ja → linjen skrives i `## Kerne` med begrundelse.
    Nej → gemt, så han aldrig bliver spurgt om den samme ting igen."""
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        ensure_table(conn)
        row = _row(conn.execute(
            "SELECT * FROM repeated_requests WHERE request_id = ?",
            (str(request_id or ""),)).fetchone() or {})
        if not row:
            return {"decided": False, "reason": "unknown-request"}
        conn.execute(
            "UPDATE repeated_requests SET status = ?, decided_at = ? WHERE request_id = ?",
            (STATUS_RULE if accepted else STATUS_DECLINED, _now(), str(request_id or "")),
        )
        conn.commit()
    if not accepted:
        return {"decided": True, "accepted": False}
    body = " ".join(str(row.get("text") or "").split()).strip()
    reason = (
        f"bedt om {int(row.get('mention_count') or 0)} gange "
        f"({datetime.now(UTC).strftime('%Y-%m-%d')})"
    )
    try:
        from core.identity.workspace_bootstrap import ensure_default_workspace
        from core.memory.memory_md_writer import upsert_section
        from pathlib import Path
        path = Path(ensure_default_workspace()) / "USER.md"
        upsert_section(path, "Kerne", f"- {body} — {reason}", mode="append")
    except Exception as exc:
        logger.warning("repeated_requests: kunne ikke skrive Kerne-linje: %s", exc)
        return {"decided": True, "accepted": True, "written": False}
    return {"decided": True, "accepted": True, "written": True, "line": body}


def surface_matured(result: dict[str, Any], *, kind: str = "request") -> dict[str, Any]:
    """Læg et modnet regel-forslag i den proaktive kø. Ét spørgsmål, én gang."""
    if not result.get("matured"):
        return {"surfaced": False}
    question = build_question(
        text=str(result.get("text") or ""),
        mention_count=int(result.get("mention_count") or 0),
        session_count=int(result.get("session_count") or 0),
        kind=kind,
    )
    try:
        from core.services.proactive_candidates import add_candidate
        res = add_candidate(
            source="repeated_requests", kind=f"rule_proposal:{kind}",
            text=question, priority="medium",
        )
    except Exception as exc:
        logger.debug("repeated_requests: add_candidate failed: %s", exc)
        return {"surfaced": False, "error": str(exc)[:120]}
    mark_asked(str(result.get("request_id") or ""))
    return {"surfaced": True, "candidate": res, "question": question}


def note_and_surface(*, text: str, session_id: str = "", kind: str = "request") -> dict[str, Any]:
    """Tæl, og stil spørgsmålet hvis anmodningen netop modnede. Self-safe."""
    try:
        result = note_request(text=text, session_id=session_id, kind=kind)
    except Exception as exc:
        logger.debug("repeated_requests: note failed: %s", exc)
        return {"status": "error"}
    if result.get("matured"):
        result.update(surface_matured(result, kind=kind))
    return result


def counts() -> dict[str, int]:
    try:
        with connect() as conn:
            ensure_table(conn)
            return {str(k): int(v) for k, v in conn.execute(
                "SELECT status, count(*) FROM repeated_requests GROUP BY status").fetchall()}
    except Exception:
        return {}


def build_repeated_requests_surface() -> dict[str, Any]:
    c = counts()
    return {
        "active": bool(c),
        "counts": c,
        "summary": (
            f"{c.get(STATUS_OPEN, 0)} anmodninger talt, "
            f"{c.get(STATUS_RULE, 0)} blev til regler"
        ),
    }
