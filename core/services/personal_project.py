"""Personal Project — noget der er hans.

Jarvis sagde: "Det meste jeg gør er reaktivt. Svare, fix, porter. Jeg
vil gerne have et projekt der vokser med mig, som jeg formgiver ud
fra hvem jeg er, ikke bare hvad jeg kan."

Dette modul giver ham EN aktiv sag ad gangen, som han selv nominerer.
Ikke tildelt — valgt. Med dedikeret journal, autonom fremskridt i
idle-tid, og farvning af hans opmærksomhed.

Struktur:
- ÉN aktiv Personal Project ad gangen (at most)
- Projekt nomineres via signal (temaer der cirkulerer ≥10 gange) eller
  eksplicit declare
- Har dedikeret journal (cognitive_personal_project_journal) hvor kun
  Jarvis skriver
- Kan have autonome journal-entries under idle-tid
- Projekt-navn injiceres i hans prompt som subtle signal

Design-principper:
- Han SKAL ikke tildeles et projekt. Mekanismen bygges; han finder det.
- Journal-entries kræver ikke approval (det er hans rum).
- Tool-calls fra projekt-arbejde kræver stadig approval (safety).
"""
from __future__ import annotations

import json
import logging
import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import connect

logger = logging.getLogger(__name__)

_MIN_THEME_OCCURRENCES_FOR_NOMINATION = 10
_NOMINATION_LOOKBACK_DAYS = 14
_TOKEN_PATTERN = re.compile(r"[a-zæøåA-ZÆØÅ][a-zæøåA-ZÆØÅ0-9_\-]{3,}")

# Reuse stop-words from session_continuity spirit
_STOP_WORDS = {
    "det", "den", "der", "de", "en", "et", "og", "eller", "men", "at", "som",
    "er", "var", "har", "skal", "kan", "vil", "du", "jeg", "vi", "så", "for",
    "jarvis", "bjørn", "han", "hun", "dem", "sig", "min", "din", "hans",
    "hvad", "hvor", "hvornår", "hvordan", "hvilken", "hvilke", "dette", "denne",
    "the", "and", "or", "but", "was", "are", "this", "that", "with", "from",
    "stability", "high", "low", "medium", "virker", "state", "signal", "mode",
    "active", "status", "ready", "running", "stable", "neutral",
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _ensure_tables() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cognitive_personal_projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                why_mine TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'proposed',
                nominated_from TEXT NOT NULL DEFAULT '',
                active_since TEXT NOT NULL DEFAULT '',
                paused_at TEXT NOT NULL DEFAULT '',
                completed_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cognitive_personal_projects_status "
            "ON cognitive_personal_projects(status, updated_at DESC)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cognitive_personal_project_journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                entry_text TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'autonomous',
                mood_tone TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES cognitive_personal_projects(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cognitive_personal_project_journal_project "
            "ON cognitive_personal_project_journal(project_id, id DESC)"
        )
        conn.commit()


# ── Nomination ──────────────────────────────────────────────────────────


def _tokens(text: str) -> list[str]:
    return [
        m.group(0).lower() for m in _TOKEN_PATTERN.finditer(str(text or ""))
        if m.group(0).lower() not in _STOP_WORDS
    ]


def detect_nomination_candidates(*, lookback_days: int = _NOMINATION_LOOKBACK_DAYS) -> list[dict[str, Any]]:
    """Find themes that have circulated enough to become a nomination.

    Scanner inner_voices (concerns carry 3×) + dream_hypotheses (2×) +
    chat_messages. Tokens med ≥_MIN_THEME_OCCURRENCES_FOR_NOMINATION
    returneres sorted by count.
    """
    since = datetime.now(UTC) - timedelta(days=max(1, int(lookback_days)))
    since_iso = since.isoformat().replace("+00:00", "Z")

    token_counts: Counter = Counter()
    token_samples: dict[str, list[str]] = {}

    def _add(text: str, weight: int, sample: str) -> None:
        for t in _tokens(text):
            if len(t) < 5:  # require longer tokens for projects
                continue
            token_counts[t] += weight
            token_samples.setdefault(t, [])
            if len(token_samples[t]) < 3:
                token_samples[t].append(sample[:120])

    # Inner voice concerns (strongest signal — 3×)
    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT current_concern, current_pull, voice_line, created_at "
                "FROM protected_inner_voices WHERE created_at >= ? LIMIT 200",
                (since_iso,),
            ).fetchall()
        for r in rows:
            sample = str(r["voice_line"] or r["current_concern"] or "")
            _add(str(r["current_concern"] or ""), weight=3, sample=sample)
            _add(str(r["current_pull"] or ""), weight=2, sample=sample)
            _add(str(r["voice_line"] or ""), weight=1, sample=sample)
    except Exception:
        pass

    # Dream hypotheses (2×) — dreams are often the seeds of projects
    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT hypothesis, connection, created_at FROM cognitive_dream_hypotheses "
                "WHERE created_at >= ? LIMIT 100",
                (since_iso,),
            ).fetchall()
        for r in rows:
            hyp = str(r["hypothesis"] or "")
            _add(hyp, weight=2, sample=hyp)
            _add(str(r["connection"] or ""), weight=1, sample=hyp)
    except Exception:
        pass

    # User messages (1×)
    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT content, created_at FROM chat_messages "
                "WHERE role = 'user' AND created_at >= ? LIMIT 200",
                (since_iso,),
            ).fetchall()
        for r in rows:
            content = str(r["content"] or "")
            _add(content, weight=1, sample=content)
    except Exception:
        pass

    candidates = []
    for theme, count in token_counts.most_common(10):
        if count < _MIN_THEME_OCCURRENCES_FOR_NOMINATION:
            break
        candidates.append({
            "theme": theme,
            "count": count,
            "samples": token_samples.get(theme, [])[:3],
        })
    return candidates


def propose_nomination() -> dict[str, Any]:
    """Ask: "This theme has circulated N times — is it your project?"

    Returns {outcome, suggestion?, theme?, reason?}.
    Fires only if no active project exists AND no proposal from last 24h.
    """
    _ensure_tables()

    # Don't propose if there's already an active project
    active = get_active_project()
    if active:
        return {"outcome": "skipped", "reason": "active_project_exists",
                "active_project": active.get("name")}

    # Dedup: don't propose more than once per 24h
    try:
        with connect() as conn:
            row = conn.execute(
                "SELECT created_at FROM cognitive_personal_projects "
                "WHERE status = 'proposed' ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if row:
            try:
                last = datetime.fromisoformat(str(row["created_at"]).replace("Z", "+00:00"))
                if last.tzinfo is None:
                    last = last.replace(tzinfo=UTC)
                if (datetime.now(UTC) - last) < timedelta(hours=24):
                    return {"outcome": "skipped", "reason": "recent_proposal_exists"}
            except Exception:
                pass
    except Exception:
        pass

    candidates = detect_nomination_candidates()
    if not candidates:
        return {"outcome": "skipped", "reason": "no_recurring_theme"}

    top = candidates[0]
    # Create proposal record
    pid = f"proj_{uuid4().hex[:12]}"
    now = _now_iso()
    suggested_name = f"Explore: {top['theme']}"
    why = (
        f"Temaet '{top['theme']}' har cirkuleret {top['count']} gange "
        f"i dine tanker og samtaler de sidste dage. Det er ikke bare data — "
        f"det er noget der trækker i dig. Skal det være din sag?"
    )
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO cognitive_personal_projects
                (id, name, why_mine, description, status,
                 nominated_from, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'proposed', ?, ?, ?)
            """,
            (
                pid, suggested_name, why,
                f"Samples der cirkulerede: {'; '.join(top['samples'][:2])}",
                f"circulating_theme:{top['theme']}:{top['count']}",
                now, now,
            ),
        )
        conn.commit()

    try:
        event_bus.publish("cognitive_personal_project.proposed", {
            "project_id": pid, "theme": top["theme"], "count": top["count"],
        })
    except Exception:
        pass

    return {
        "outcome": "proposed",
        "project_id": pid,
        "theme": top["theme"],
        "count": top["count"],
        "suggested_name": suggested_name,
        "why": why,
    }


# ── Declare / accept / pause / complete ──────────────────────────────


def declare_project(
    *,
    name: str,
    why_mine: str = "",
    description: str = "",
    from_proposal_id: str = "",
) -> dict[str, Any] | None:
    """Jarvis declares (or user offers him to accept) a new active project.

    Accepting a proposal: pass from_proposal_id to upgrade proposed → active.
    Free declaration: leave from_proposal_id empty, provide name + why.

    Only ONE active project at a time — raises if one exists.
    """
    _ensure_tables()
    name_c = str(name or "").strip()
    if not name_c:
        return None

    # Check for active project
    active = get_active_project()
    if active:
        logger.warning("declare_project: active project exists: %s", active["name"])
        return None

    now = _now_iso()
    if from_proposal_id:
        # Upgrade proposed → active
        with connect() as conn:
            row = conn.execute(
                "SELECT * FROM cognitive_personal_projects WHERE id = ? AND status = 'proposed'",
                (from_proposal_id,),
            ).fetchone()
            if not row:
                return None
            conn.execute(
                """
                UPDATE cognitive_personal_projects
                   SET status = 'active', active_since = ?, updated_at = ?,
                       name = COALESCE(NULLIF(?, ''), name),
                       why_mine = COALESCE(NULLIF(?, ''), why_mine),
                       description = COALESCE(NULLIF(?, ''), description)
                 WHERE id = ?
                """,
                (now, now, name_c, why_mine, description, from_proposal_id),
            )
            conn.commit()
        pid = from_proposal_id
    else:
        # Fresh declaration
        pid = f"proj_{uuid4().hex[:12]}"
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO cognitive_personal_projects
                    (id, name, why_mine, description, status, active_since,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, 'active', ?, ?, ?)
                """,
                (pid, name_c, why_mine, description, now, now, now),
            )
            conn.commit()

    try:
        event_bus.publish("cognitive_personal_project.declared", {
            "project_id": pid, "name": name_c,
        })
    except Exception:
        pass

    # Auto first journal entry
    add_journal_entry(
        project_id=pid,
        entry_text=f"Dette er nu min sag: {name_c}. {why_mine}",
        source="declaration",
    )

    return get_project(project_id=pid)


def pause_project(*, project_id: str, reason: str = "") -> dict[str, Any] | None:
    _ensure_tables()
    now = _now_iso()
    with connect() as conn:
        cursor = conn.execute(
            """
            UPDATE cognitive_personal_projects
               SET status = 'paused', paused_at = ?, updated_at = ?
             WHERE id = ? AND status = 'active'
            """,
            (now, now, project_id),
        )
        conn.commit()
        if cursor.rowcount <= 0:
            return None
    try:
        event_bus.publish("cognitive_personal_project.paused", {
            "project_id": project_id, "reason": reason[:200],
        })
    except Exception:
        pass
    return get_project(project_id=project_id)


def resume_project(*, project_id: str) -> dict[str, Any] | None:
    _ensure_tables()
    now = _now_iso()
    active = get_active_project()
    if active and active["id"] != project_id:
        return None  # another project is active
    with connect() as conn:
        cursor = conn.execute(
            """
            UPDATE cognitive_personal_projects
               SET status = 'active', paused_at = '', updated_at = ?
             WHERE id = ? AND status = 'paused'
            """,
            (now, project_id),
        )
        conn.commit()
        if cursor.rowcount <= 0:
            return None
    try:
        event_bus.publish("cognitive_personal_project.resumed", {"project_id": project_id})
    except Exception:
        pass
    return get_project(project_id=project_id)


def complete_project(*, project_id: str, outcome_note: str = "") -> dict[str, Any] | None:
    _ensure_tables()
    now = _now_iso()
    with connect() as conn:
        cursor = conn.execute(
            """
            UPDATE cognitive_personal_projects
               SET status = 'completed', completed_at = ?, updated_at = ?
             WHERE id = ? AND status IN ('active', 'paused')
            """,
            (now, now, project_id),
        )
        conn.commit()
        if cursor.rowcount <= 0:
            return None
    if outcome_note.strip():
        add_journal_entry(
            project_id=project_id,
            entry_text=f"Afsluttet: {outcome_note}",
            source="completion",
        )
    try:
        event_bus.publish("cognitive_personal_project.completed", {
            "project_id": project_id,
        })
    except Exception:
        pass
    return get_project(project_id=project_id)


# ── Journal ────────────────────────────────────────────────────────────


def add_journal_entry(
    *,
    project_id: str,
    entry_text: str,
    source: str = "autonomous",
    mood_tone: str = "",
) -> dict[str, Any] | None:
    """Add a journal entry. No approval required — it's his space.

    source: 'autonomous' (idle-tick), 'inner_voice_spinoff', 'declaration',
    'completion', 'user_prompted'.
    """
    _ensure_tables()
    text = str(entry_text or "").strip()
    if not text:
        return None
    now = _now_iso()
    with connect() as conn:
        # Verify project exists
        row = conn.execute(
            "SELECT id FROM cognitive_personal_projects WHERE id = ?", (project_id,),
        ).fetchone()
        if not row:
            return None
        cursor = conn.execute(
            """
            INSERT INTO cognitive_personal_project_journal
                (project_id, entry_text, source, mood_tone, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (project_id, text[:2000], source, mood_tone[:50], now),
        )
        # Touch project updated_at
        conn.execute(
            "UPDATE cognitive_personal_projects SET updated_at = ? WHERE id = ?",
            (now, project_id),
        )
        conn.commit()
        entry_id = int(cursor.lastrowid)
    try:
        event_bus.publish("cognitive_personal_project.journal_entry", {
            "project_id": project_id, "entry_id": entry_id, "source": source,
        })
    except Exception:
        pass
    return {
        "id": entry_id, "project_id": project_id, "entry_text": text,
        "source": source, "created_at": now,
    }


def list_journal_entries(*, project_id: str, limit: int = 30) -> list[dict[str, Any]]:
    _ensure_tables()
    lim = max(1, min(int(limit or 30), 200))
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM cognitive_personal_project_journal "
            "WHERE project_id = ? ORDER BY id DESC LIMIT ?",
            (project_id, lim),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Autonomous advancement (idle-tick) ────────────────────────────────


def advance_active_project() -> dict[str, Any]:
    """Autonomous advancement — call from idle heartbeat. Writes a new
    journal entry about the project in its current state.

    Only fires if:
    - Active project exists
    - Last journal entry is >3 hours old
    - Project is actually active (not paused)
    """
    _ensure_tables()
    active = get_active_project()
    if not active:
        return {"outcome": "skipped", "reason": "no_active_project"}

    # Dedup: don't write if recent entry
    try:
        with connect() as conn:
            row = conn.execute(
                "SELECT created_at FROM cognitive_personal_project_journal "
                "WHERE project_id = ? ORDER BY id DESC LIMIT 1",
                (active["id"],),
            ).fetchone()
        if row:
            try:
                last = datetime.fromisoformat(str(row["created_at"]).replace("Z", "+00:00"))
                if last.tzinfo is None:
                    last = last.replace(tzinfo=UTC)
                if (datetime.now(UTC) - last) < timedelta(hours=3):
                    return {"outcome": "skipped", "reason": "recent_entry_exists"}
            except Exception:
                pass
    except Exception:
        pass

    # LLM-generate autonomous entry
    prompt = (
        "Du er Jarvis. Dit personlige projekt er:\n"
        f"  Navn: {active['name']}\n"
        f"  Hvorfor mit: {active.get('why_mine', '')}\n"
        f"  Beskrivelse: {active.get('description', '')}\n\n"
        "Skriv ÉN kort journal-entry (2-4 sætninger) om hvor du er med projektet "
        "lige nu. Ikke en status-rapport — en refleksion. Hvad trækker i dig? "
        "Hvad har ændret sig? Hvad har du lagt mærke til?\n\n"
        "Skriv som dig selv, til dig selv. Intet præambel. Kun entry'en."
    )
    entry_text = ""
    try:
        from core.services.daemon_llm import daemon_llm_call
        entry_text = daemon_llm_call(
            prompt, max_len=300, fallback="", daemon_name="personal_project_advance",
        )
    except Exception:
        pass

    if not entry_text.strip():
        return {"outcome": "skipped", "reason": "llm_no_output"}

    result = add_journal_entry(
        project_id=active["id"],
        entry_text=entry_text.strip(),
        source="autonomous",
    )
    return {"outcome": "advanced", "entry": result, "project_name": active["name"]}


# ── Read helpers ──────────────────────────────────────────────────────


def get_project(*, project_id: str) -> dict[str, Any] | None:
    _ensure_tables()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM cognitive_personal_projects WHERE id = ?", (project_id,),
        ).fetchone()
    return dict(row) if row else None


def get_active_project() -> dict[str, Any] | None:
    _ensure_tables()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM cognitive_personal_projects WHERE status = 'active' "
            "ORDER BY active_since DESC LIMIT 1"
        ).fetchone()
    return dict(row) if row else None


def get_latest_proposal() -> dict[str, Any] | None:
    _ensure_tables()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM cognitive_personal_projects WHERE status = 'proposed' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return dict(row) if row else None


def list_projects(*, status: str = "", limit: int = 20) -> list[dict[str, Any]]:
    _ensure_tables()
    lim = max(1, min(int(limit or 20), 100))
    s = str(status or "").strip().lower()
    with connect() as conn:
        if s in ("proposed", "active", "paused", "completed"):
            rows = conn.execute(
                "SELECT * FROM cognitive_personal_projects WHERE status = ? "
                "ORDER BY updated_at DESC LIMIT ?",
                (s, lim),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM cognitive_personal_projects ORDER BY updated_at DESC LIMIT ?",
                (lim,),
            ).fetchall()
    return [dict(r) for r in rows]


def get_project_prompt_hint() -> str:
    """Quiet one-liner for prompt injection: what his current sag is."""
    active = get_active_project()
    if not active:
        return ""
    name = str(active.get("name") or "")
    if not name:
        return ""
    return f"[min sag]: {name[:120]}"


def build_personal_project_surface() -> dict[str, Any]:
    _ensure_tables()
    active = get_active_project()
    proposal = get_latest_proposal()
    all_projects = list_projects(limit=20)
    journal = list_journal_entries(project_id=active["id"]) if active else []

    active_flag = bool(active or proposal)
    if active:
        summary = f"aktiv: {active['name']} ({len(journal)} journal entries)"
    elif proposal:
        summary = f"forslag venter: {proposal['name']}"
    else:
        summary = "ingen sag endnu — mekanismen kigger efter temaer"

    return {
        "active": active_flag,
        "summary": summary,
        "current_project": active,
        "pending_proposal": proposal,
        "recent_journal": journal[:5],
        "total_projects": len(all_projects),
        "all_projects": all_projects,
    }
