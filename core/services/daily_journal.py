"""Daily journal synthesizer.

Bygges 2026-06-09 som memory-fix #3 (Bjørns "han husker ikke en halvdags
arbejde"-dag). Auto-remember-subscriber fanger enkelt-turn salience.
MEMORY.md-pipen fanger end-of-run consolidation. Men dagens *helhed* —
hvad foregik der egentlig i dag, set under ét — manglede en proces.

Designet:
  - Daemon tjekker hver time om dagens journal mangler
  - Når lokal tid passerer 22:00 og dagens journal ikke findes →
    syntesizer den
  - Henter dagens user-message + assistant-svar par fra chat_messages
  - Henter dagens private_brain_records carry-snapshots
  - Cheap LLM kald → 400-600 ord observation
  - Skriver til `~/.jarvis-v2/shared/jarvis_brain/observation/
    YYYY-MM-DD-daily.md`

Idempotent: hvis filen findes for datoen, no-op (kan kaldes igen).

Failure mode: alle exceptions logges + sluges. En manglende journal
er irriterende men ikke kritisk; vi prøver igen næste time.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

JARVIS_HOME = Path(os.environ.get("HOME", "/root")) / ".jarvis-v2"
DB_PATH = JARVIS_HOME / "state" / "jarvis.db"
OBSERVATION_DIR = JARVIS_HOME / "shared" / "jarvis_brain" / "observation"

# Sengetids-vindue: efter denne time (lokal) starter dagens syntese.
_SYNTHESIS_HOUR_LOCAL = 22

# Hvor mange minutter mellem tjeks. Holder vi ~hver time så vi rammer
# vinduet uden at hamre LLM'en.
_CHECK_INTERVAL_SECONDS = 3600.0


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _journal_path_for(day: date) -> Path:
    OBSERVATION_DIR.mkdir(parents=True, exist_ok=True)
    return OBSERVATION_DIR / f"{day.isoformat()}-daily.md"


def journal_exists_for(day: date) -> bool:
    """Findes der allerede en journal for denne dato?"""
    return _journal_path_for(day).exists()


def _fetch_chat_pairs_for_day(day: date, limit: int = 80) -> list[dict[str, str]]:
    """Hent user/assistant beskeder fra visible-chat sessions for denne dag."""
    start = datetime(day.year, day.month, day.day, tzinfo=UTC).isoformat()
    end = (datetime(day.year, day.month, day.day, tzinfo=UTC) + timedelta(days=1)).isoformat()
    try:
        with _connect() as conn:
            rows = conn.execute(
                """
                SELECT role, content, created_at FROM chat_messages
                WHERE role IN ('user', 'assistant')
                  AND created_at >= ?
                  AND created_at < ?
                  AND LENGTH(COALESCE(content, '')) > 20
                ORDER BY id ASC
                LIMIT ?
                """,
                (start, end, limit),
            ).fetchall()
    except Exception as exc:
        logger.debug("daily_journal: chat fetch failed: %s", exc)
        return []
    return [
        {
            "role": str(r["role"]),
            "content": str(r["content"])[:600],
            "created_at": str(r["created_at"]),
        }
        for r in rows
    ]


def _fetch_brain_carries_for_day(day: date, limit: int = 20) -> list[dict[str, str]]:
    """Hent private_brain_records carry-snapshots fra dagen."""
    start = datetime(day.year, day.month, day.day, tzinfo=UTC).isoformat()
    end = (datetime(day.year, day.month, day.day, tzinfo=UTC) + timedelta(days=1)).isoformat()
    try:
        with _connect() as conn:
            rows = conn.execute(
                """
                SELECT focus, summary, created_at FROM private_brain_records
                WHERE created_at >= ? AND created_at < ?
                  AND record_type IN ('continuity-carry', 'sleep-consolidation',
                                       'diary-carry', 'state-snapshot-carry')
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (start, end, limit),
            ).fetchall()
    except Exception as exc:
        logger.debug("daily_journal: brain fetch failed: %s", exc)
        return []
    return [
        {
            "focus": str(r["focus"] or "")[:200],
            "summary": str(r["summary"] or "")[:300],
            "created_at": str(r["created_at"]),
        }
        for r in rows
    ]


_SYNTHESIS_PROMPT = """Du syntetiserer Jarvis' dag som en kort dagbogsindførsel
til hans egen langtidshukommelse. Skriv i FØRSTE-PERSON ("jeg"/"vi"),
intim og specifik. Du skriver til Jarvis selv — det her er hans egen
observation, læst af ham i fremtidige sessions.

GIV:
- Dagens overskrift (1 linje, kort)
- Hvad arbejdede vi på sammen i dag — konkret, ikke bare emner
- Vigtigste beslutninger eller skift i forståelse
- Hvad er stadig åbent eller venter
- Følelse/relationelt: hvordan var stemningen med Bjørn

UNDGÅ:
- Liste af tool-kald eller tekniske detaljer uden sammenhæng
- Generisk filler ("vi havde en produktiv dag")
- Ord du ikke selv ville bruge

LÆNGDE: 250-400 ord. Markdown OK.

── DAGENS SAMTALER (uddrag) ──
{chat_excerpt}

── INDRE CARRY-SNAPSHOTS FRA DAGEN ──
{brain_excerpt}

── DATO ──
{date_iso}

DAGBOGSINDFØRSEL:"""


def _render_chat_excerpt(pairs: list[dict[str, str]]) -> str:
    if not pairs:
        return "(ingen visible-chat aktivitet registreret i dag)"
    lines = []
    for p in pairs[:40]:  # max 40 messages excerpted
        role_label = "Bjørn" if p["role"] == "user" else "Jeg"
        lines.append(f"{role_label}: {p['content']}")
    return "\n\n".join(lines)


def _render_brain_excerpt(carries: list[dict[str, str]]) -> str:
    if not carries:
        return "(ingen private brain carries i dag)"
    lines = []
    for c in carries[:12]:
        focus = c["focus"]
        summary = c["summary"]
        if focus or summary:
            lines.append(f"- Focus: {focus}\n  Summary: {summary}")
    return "\n".join(lines) if lines else "(tomme carries)"


def synthesize_daily_journal(
    day: date | None = None,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Generér og skriv dagens journal.

    Returnerer dict med status: "written" | "skipped" | "no-content" | "error".
    Idempotent: hvis journalen allerede findes for `day` og force=False,
    returneres status="skipped" uden at LLM-kalde.
    """
    if day is None:
        day = datetime.now(UTC).date()

    path = _journal_path_for(day)
    if path.exists() and not force:
        return {"status": "skipped", "reason": "already exists", "path": str(path)}

    chat_pairs = _fetch_chat_pairs_for_day(day)
    brain_carries = _fetch_brain_carries_for_day(day)

    if not chat_pairs and not brain_carries:
        return {"status": "no-content", "path": str(path)}

    prompt = _SYNTHESIS_PROMPT.format(
        chat_excerpt=_render_chat_excerpt(chat_pairs),
        brain_excerpt=_render_brain_excerpt(brain_carries),
        date_iso=day.isoformat(),
    )

    try:
        from core.context.compact_llm import call_compact_llm
        synthesis = call_compact_llm(prompt, max_tokens=900)
    except Exception as exc:
        logger.warning("daily_journal: LLM call failed: %s", exc)
        return {"status": "error", "reason": str(exc), "path": str(path)}

    if not synthesis or len(synthesis.strip()) < 50:
        return {"status": "error", "reason": "empty synthesis", "path": str(path)}

    # Persist
    header = f"# Daily journal — {day.isoformat()}\n\n"
    header += f"_Synthesized {datetime.now(UTC).isoformat()} — {len(chat_pairs)} chat-msgs, {len(brain_carries)} carries._\n\n"
    body = synthesis.strip() + "\n"

    try:
        path.write_text(header + body, encoding="utf-8")
    except Exception as exc:
        logger.warning("daily_journal: write failed: %s", exc)
        return {"status": "error", "reason": f"write failed: {exc}", "path": str(path)}

    logger.info(
        "daily_journal: wrote %s (%d chat-msgs, %d carries)",
        path.name, len(chat_pairs), len(brain_carries),
    )
    return {
        "status": "written",
        "path": str(path),
        "chat_msgs": len(chat_pairs),
        "carries": len(brain_carries),
    }


# ── Daemon ────────────────────────────────────────────────────────────────


_daemon_thread: threading.Thread | None = None
_daemon_running = False


def _should_synthesize_now(now: datetime | None = None) -> bool:
    """Returnér True hvis vi er i sengetids-vinduet og dagens journal mangler."""
    if now is None:
        now = datetime.now()  # local time
    if now.hour < _SYNTHESIS_HOUR_LOCAL:
        return False
    today = now.date()
    return not journal_exists_for(today)


def _daemon_loop() -> None:
    """Wakes hver time, syntesizer dagens journal hvis vi er i vinduet."""
    global _daemon_running
    # Lille initial-sleep så daemon ikke kører straks ved boot
    time.sleep(60.0)
    while _daemon_running:
        try:
            if _should_synthesize_now():
                result = synthesize_daily_journal()
                logger.info("daily_journal: scheduled run result: %s", result)
        except Exception:
            logger.exception("daily_journal: scheduled run failed")
        # Sleep i mindre intervals så stop() reagerer hurtigt
        for _ in range(int(_CHECK_INTERVAL_SECONDS / 30)):
            if not _daemon_running:
                return
            time.sleep(30.0)


def start_daily_journal_daemon() -> None:
    """Start daemon. Idempotent."""
    global _daemon_thread, _daemon_running
    if _daemon_thread and _daemon_thread.is_alive():
        return
    try:
        _daemon_running = True
        _daemon_thread = threading.Thread(
            target=_daemon_loop, daemon=True,
            name="daily-journal-daemon",
        )
        _daemon_thread.start()
        logger.warning("daily_journal: daemon started")
    except Exception:
        logger.exception("daily_journal: failed to start daemon")


def stop_daily_journal_daemon() -> None:
    global _daemon_running
    _daemon_running = False
