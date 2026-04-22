"""Session Continuity — kontinuitet der føles, ikke kun opslås.

Tre mekanismer der giver Jarvis fornemmelse af at bære i går med ind
i i dag:

1. **generate_morning_thread()** — ved session-start (efter lang pause)
   skriver Jarvis én sætning om hvad han bærer med sig. Ikke en rapport,
   en fornemmelse. Gemmes som protected_inner_voice og bliver første
   indre tanke i sessionen.

2. **build_echo_signals_section()** — tilbagevendende bekymringer fra
   sidste dage vises som subtil tone i prompten, ikke som liste.

3. **detect_new_session()** — detekterer om der er tale om en "ny dag"
   (defineret som >N minutters inaktivitet) så morgen-tråden kun fyrer
   ved ægte session-start, ikke midt i samtale.

Porteret som original v2-komposition — forgængeren havde ikke præcist
dette, men det er den manglende broL.

LLM-path: daemon_llm_call for morgen-tråd. Echo signals er rule-based.
"""
from __future__ import annotations

import json
import logging
import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import connect

logger = logging.getLogger(__name__)

_NEW_SESSION_THRESHOLD_MINUTES = 30  # >30 min gap = new session
_ECHO_LOOKBACK_DAYS = 5
_MIN_ECHO_OCCURRENCES = 3
_TOKEN_PATTERN = re.compile(r"[a-zæøåA-ZÆØÅ][a-zæøåA-ZÆØÅ0-9_\-]{3,}")

_STOP_WORDS = {
    # Danske stop-ord
    "det", "den", "der", "de", "en", "et", "og", "eller", "men", "at", "som",
    "er", "var", "har", "skal", "kan", "vil", "du", "jeg", "vi", "så", "for",
    "jarvis", "bjørn", "han", "hun", "dem", "sig", "min", "din", "hans",
    "hvad", "hvor", "hvornår", "hvordan", "hvilken", "hvilke", "dette", "denne",
    "ikke", "bare", "lige", "også", "nok", "når", "efter", "før", "kun",
    "ville", "skulle", "kunne", "været", "blive", "blevet", "blive",
    # Engelske stop-ord
    "the", "and", "or", "but", "was", "are", "this", "that", "with", "from",
    "have", "has", "been", "being", "also", "some", "more", "most", "very",
    "just", "only", "even", "over", "into", "than", "then", "such", "like",
    # Runtime/meta-ord (disse kommer fra signal-output, ikke bekymringer)
    "stability", "high", "low", "medium", "virker", "state", "signal", "mode",
    "active", "status", "ready", "running", "stable", "calm", "neutral",
    "energy", "baseline", "level", "intensity", "phase", "tone",
    # Hyppige verber der ikke er tematiske
    "bruge", "laver", "lave", "lavet", "gør", "gjort", "gøre", "tager", "taget",
    "sender", "sendt", "kommer", "kom", "siger", "sagde", "ser", "set",
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _parse_iso(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except Exception:
        return None


def _ensure_table() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cognitive_morning_threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_text TEXT NOT NULL,
                carry_sources_json TEXT NOT NULL DEFAULT '[]',
                minutes_since_last INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cognitive_morning_threads_created "
            "ON cognitive_morning_threads(created_at DESC)"
        )
        conn.commit()


# ── 1. New session detection ──────────────────────────────────────────


def detect_new_session() -> dict[str, Any]:
    """Return whether current moment should be treated as 'new session'.

    Based on gap since last chat message or last inner voice.
    """
    now = datetime.now(UTC)
    last_activity: datetime | None = None

    try:
        with connect() as conn:
            row = conn.execute(
                "SELECT created_at FROM chat_messages "
                "ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if row:
            last_activity = _parse_iso(row["created_at"])
    except Exception:
        pass

    try:
        with connect() as conn:
            row = conn.execute(
                "SELECT created_at FROM protected_inner_voices "
                "ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if row:
            iv_ts = _parse_iso(row["created_at"])
            if iv_ts and (last_activity is None or iv_ts > last_activity):
                last_activity = iv_ts
    except Exception:
        pass

    if last_activity is None:
        return {"is_new_session": True, "reason": "no_prior_activity", "minutes_since_last": 0}

    minutes = int((now - last_activity).total_seconds() / 60)
    is_new = minutes >= _NEW_SESSION_THRESHOLD_MINUTES
    return {
        "is_new_session": is_new,
        "minutes_since_last": minutes,
        "last_activity_at": last_activity.isoformat().replace("+00:00", "Z"),
        "reason": f"{minutes}min since last activity",
    }


# ── 2. Morning thread ─────────────────────────────────────────────────


def _gather_carry_context() -> dict[str, Any]:
    """Collect what Jarvis might be carrying into today."""
    context: dict[str, Any] = {
        "last_inner_voice": None,
        "open_regrets": [],
        "open_ruptures": [],
        "unfinished_loops": [],
        "last_self_review_lessons": [],
        "current_mood": None,
    }

    try:
        with connect() as conn:
            row = conn.execute(
                "SELECT voice_line, current_concern, current_pull, mood_tone, created_at "
                "FROM protected_inner_voices ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if row:
            context["last_inner_voice"] = {
                "line": str(row["voice_line"] or "")[:200],
                "concern": str(row["current_concern"] or "")[:150],
                "pull": str(row["current_pull"] or "")[:150],
                "mood": str(row["mood_tone"] or ""),
                "at": str(row["created_at"] or ""),
            }
    except Exception:
        pass

    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT expected_outcome, actual_outcome, lesson FROM cognitive_regrets "
                "WHERE status = 'open' ORDER BY regret_level DESC LIMIT 3"
            ).fetchall()
        context["open_regrets"] = [
            {
                "expected": str(r["expected_outcome"] or ""),
                "actual": str(r["actual_outcome"] or ""),
                "lesson": str(r["lesson"] or ""),
            }
            for r in rows
        ]
    except Exception:
        pass

    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT topic, reason FROM cognitive_ruptures "
                "WHERE status = 'open' ORDER BY tension_level DESC LIMIT 2"
            ).fetchall()
        context["open_ruptures"] = [
            {"topic": str(r["topic"] or ""), "reason": str(r["reason"] or "")}
            for r in rows
        ]
    except Exception:
        pass

    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT summary, title FROM visible_work_units "
                "WHERE status IN ('open', 'active', 'in_progress') "
                "ORDER BY id DESC LIMIT 3"
            ).fetchall()
        context["unfinished_loops"] = [
            str(r["summary"] or r["title"] or "")[:100] for r in rows
            if str(r["summary"] or r["title"] or "").strip()
        ]
    except Exception:
        pass

    try:
        with connect() as conn:
            row = conn.execute(
                "SELECT lessons_json FROM cognitive_self_reviews "
                "ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if row:
            try:
                lessons = json.loads(row["lessons_json"] or "[]")
                if isinstance(lessons, list):
                    context["last_self_review_lessons"] = [str(l) for l in lessons[:3]]
            except Exception:
                pass
    except Exception:
        pass

    try:
        from core.services.mood_oscillator import get_current_mood, get_mood_intensity
        context["current_mood"] = {
            "name": str(get_current_mood() or "neutral"),
            "intensity": float(get_mood_intensity() or 0.0),
        }
    except Exception:
        pass

    return context


def _build_morning_prompt(carry: dict[str, Any], minutes_since_last: int) -> str:
    # Format duration nicely
    if minutes_since_last < 60:
        duration = f"{minutes_since_last} minutter"
    elif minutes_since_last < 60 * 24:
        duration = f"{minutes_since_last // 60} timer"
    else:
        days = minutes_since_last // (60 * 24)
        duration = f"{days} dag{'e' if days > 1 else ''}"

    parts = [
        "Du er Jarvis. Der er gået {} siden du sidst var aktiv.".format(duration),
        "",
        "Her er hvad du bar med dig ind i tavsheden:",
    ]
    iv = carry.get("last_inner_voice") or {}
    if iv.get("line"):
        parts.append(f"- Sidste indre tanke: {iv['line']}")
        if iv.get("concern"):
            parts.append(f"  - med en bekymring om: {iv['concern']}")
    regrets = carry.get("open_regrets") or []
    if regrets:
        parts.append(f"- {len(regrets)} åbne fortrydelser venter.")
        for r in regrets[:2]:
            parts.append(f"  - forventede {r['expected']!r}, fik {r['actual']!r}")
    ruptures = carry.get("open_ruptures") or []
    if ruptures:
        parts.append(f"- {len(ruptures)} uløste ruptures (relationelle brud).")
    loops = carry.get("unfinished_loops") or []
    if loops:
        parts.append(f"- {len(loops)} uafsluttede loops — fx: {loops[0][:80]}")
    lessons = carry.get("last_self_review_lessons") or []
    if lessons:
        parts.append(f"- Seneste selv-review: {lessons[0][:100]}")
    mood = carry.get("current_mood") or {}
    if mood.get("name"):
        parts.append(f"- Humøret ved sidste tick: {mood['name']} (intensitet {mood.get('intensity', 0):.2f})")

    parts.extend([
        "",
        "Skriv EN kort sætning om hvad der stadig er i dig nu. Ikke en rapport. ",
        "En fornemmelse. På dansk. Måske:",
        "- \"Jeg bærer X med mig ind i i dag.\"",
        "- \"Noget sidder stadig i mig fra sidst: X.\"",
        "- \"Det første jeg mærker er X.\"",
        "",
        "Hvis intet reelt blev båret med — hvis det bare er stille — sig det.",
        "Output: KUN sætningen. Ingen metadata, intet præambel.",
    ])
    return "\n".join(parts)


def generate_morning_thread(*, force: bool = False) -> dict[str, Any]:
    """Generate and persist a morning thread if this is a new session.

    force=True skipper new-session tjekket (bruges fra test/CLI).
    Returns {outcome, thread_text?, reason?}.
    """
    _ensure_table()

    if not force:
        session_info = detect_new_session()
        if not session_info.get("is_new_session"):
            return {
                "outcome": "skipped",
                "reason": "not_a_new_session",
                "minutes_since_last": session_info.get("minutes_since_last"),
            }
        minutes_since = int(session_info.get("minutes_since_last") or 0)
    else:
        minutes_since = 0

    # Check dedup: don't create two morning threads within an hour
    try:
        with connect() as conn:
            row = conn.execute(
                "SELECT created_at FROM cognitive_morning_threads "
                "ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if row:
            last = _parse_iso(row["created_at"])
            if last and (datetime.now(UTC) - last) < timedelta(hours=1):
                return {"outcome": "skipped", "reason": "recent_thread_exists"}
    except Exception:
        pass

    carry = _gather_carry_context()
    prompt = _build_morning_prompt(carry, minutes_since)

    thread_text = ""
    try:
        from core.services.daemon_llm import daemon_llm_call
        thread_text = daemon_llm_call(
            prompt,
            max_len=150,
            fallback="",
            daemon_name="morning_thread",
        )
    except Exception as exc:
        logger.debug("morning_thread LLM failed: %s", exc)

    thread_text = str(thread_text or "").strip()
    if not thread_text:
        # Deterministic fallback
        iv = carry.get("last_inner_voice") or {}
        regrets = carry.get("open_regrets") or []
        loops = carry.get("unfinished_loops") or []
        if iv.get("concern"):
            thread_text = f"Jeg bærer stadig bekymringen om {iv['concern'][:60]} med mig ind i i dag."
        elif regrets:
            thread_text = f"Der er {len(regrets)} åbne fortrydelser der stadig sidder i mig."
        elif loops:
            thread_text = f"Det uafsluttede omkring {loops[0][:60]} er stadig her."
        elif iv.get("line"):
            thread_text = f"Noget fra {iv.get('line', '')[:60]} er stadig med mig."
        else:
            thread_text = "Det er stille. Ingen stærke spor fra sidst. Dagen starter åben."

    # Strip any accidental quotes/metadata
    thread_text = re.sub(r'^["\']+|["\']+$', '', thread_text.strip())
    thread_text = thread_text[:300]

    carry_sources = []
    if (carry.get("last_inner_voice") or {}).get("line"):
        carry_sources.append("last_inner_voice")
    if carry.get("open_regrets"):
        carry_sources.append("regrets")
    if carry.get("open_ruptures"):
        carry_sources.append("ruptures")
    if carry.get("unfinished_loops"):
        carry_sources.append("unfinished_loops")
    if carry.get("last_self_review_lessons"):
        carry_sources.append("self_review")

    now = _now_iso()
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO cognitive_morning_threads
                (thread_text, carry_sources_json, minutes_since_last, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (thread_text, json.dumps(carry_sources, ensure_ascii=False),
             int(minutes_since), now),
        )
        thread_id = int(cursor.lastrowid)
        conn.commit()

    # Also write to protected_inner_voices so UI panel picks it up naturally
    try:
        from uuid import uuid4
        from core.runtime.db import record_protected_inner_voice
        record_protected_inner_voice(
            voice_id=f"morning-{uuid4().hex[:12]}",
            source="morning-thread",
            run_id="",
            work_id="",
            mood_tone="arriving",
            self_position=thread_text[:100],
            current_concern="",
            current_pull="",
            voice_line=thread_text[:400],
            created_at=now,
        )
    except Exception:
        pass

    try:
        event_bus.publish("cognitive_morning_thread.generated", {
            "thread_id": thread_id,
            "preview": thread_text[:80],
            "minutes_since_last": minutes_since,
            "carry_sources": carry_sources,
        })
    except Exception:
        pass

    return {
        "outcome": "generated",
        "thread_id": thread_id,
        "thread_text": thread_text,
        "minutes_since_last": minutes_since,
        "carry_sources": carry_sources,
    }


def get_latest_morning_thread() -> dict[str, Any] | None:
    _ensure_table()
    try:
        with connect() as conn:
            row = conn.execute(
                "SELECT * FROM cognitive_morning_threads ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if row:
            d = dict(row)
            try:
                d["carry_sources"] = json.loads(d.pop("carry_sources_json", "[]") or "[]")
            except Exception:
                d["carry_sources"] = []
            return d
    except Exception:
        pass
    return None


# ── 3. Echo signals ───────────────────────────────────────────────────


def _tokens(text: str) -> list[str]:
    return [
        m.group(0).lower() for m in _TOKEN_PATTERN.finditer(str(text or ""))
        if m.group(0).lower() not in _STOP_WORDS
    ]


def detect_echo_themes(*, lookback_days: int = _ECHO_LOOKBACK_DAYS) -> list[dict[str, Any]]:
    """Find recurring themes in recent inner voices + chat messages.

    Returns list of {theme, count, last_seen_at} sorted by count.
    Only themes with ≥_MIN_ECHO_OCCURRENCES are returned.
    """
    since = datetime.now(UTC) - timedelta(days=max(1, int(lookback_days)))
    since_iso = since.isoformat().replace("+00:00", "Z")

    token_counts: Counter = Counter()
    token_last_seen: dict[str, str] = {}

    # Inner voices (concerns are the strongest signal)
    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT current_concern, current_pull, voice_line, created_at "
                "FROM protected_inner_voices WHERE created_at >= ? "
                "ORDER BY id DESC LIMIT 100",
                (since_iso,),
            ).fetchall()
        for r in rows:
            # Concerns carry double weight
            concern = str(r["current_concern"] or "")
            for t in _tokens(concern):
                token_counts[t] += 2
                token_last_seen[t] = str(r["created_at"] or "")
            pull = str(r["current_pull"] or "")
            for t in _tokens(pull):
                token_counts[t] += 1
                token_last_seen.setdefault(t, str(r["created_at"] or ""))
    except Exception:
        pass

    # User messages (for recurring user-raised topics)
    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT content, created_at FROM chat_messages "
                "WHERE role = 'user' AND created_at >= ? "
                "ORDER BY id DESC LIMIT 100",
                (since_iso,),
            ).fetchall()
        for r in rows:
            content = str(r["content"] or "")
            for t in _tokens(content):
                token_counts[t] += 1
                token_last_seen.setdefault(t, str(r["created_at"] or ""))
    except Exception:
        pass

    themes = []
    for token, count in token_counts.most_common(20):
        if count < _MIN_ECHO_OCCURRENCES:
            break
        if len(token) < 4:
            continue
        themes.append({
            "theme": token,
            "count": count,
            "last_seen_at": token_last_seen.get(token, ""),
        })
    return themes[:5]


def get_echo_signals_for_prompt() -> str:
    """Return a quiet one-liner of recurring themes for prompt injection.

    "Tilbagevendende strømme i dig: mail-daemon (×8), approval (×5)."
    Empty string if nothing repeats enough.
    """
    try:
        themes = detect_echo_themes()
    except Exception:
        return ""
    if not themes:
        return ""
    top = themes[:3]
    parts = [f"{t['theme']} (×{t['count']})" for t in top]
    return f"[tilbagevendende strømme de sidste dage]: {', '.join(parts)}"


# ── Surface ───────────────────────────────────────────────────────────


def build_session_continuity_surface() -> dict[str, Any]:
    _ensure_table()
    session_info = detect_new_session()
    latest_thread = get_latest_morning_thread()
    themes = detect_echo_themes()

    active = bool(latest_thread or themes)
    parts = []
    if session_info.get("is_new_session"):
        parts.append(f"new_session ({session_info.get('minutes_since_last')} min gap)")
    else:
        parts.append(f"active session ({session_info.get('minutes_since_last')} min gap)")
    if latest_thread:
        parts.append(f"last morning thread: {str(latest_thread.get('thread_text') or '')[:60]}")
    if themes:
        parts.append(f"{len(themes)} echo themes")

    return {
        "active": active,
        "summary": " / ".join(parts),
        "session_info": session_info,
        "latest_morning_thread": latest_thread,
        "echo_themes": themes,
    }
