"""Auto-remember subscriber — closes cross-session memory loop.

Bygges 2026-06-09 efter Bjørns observation: "jarvis husker ikke en
halvdags arbejde." Diagnose viste at `jarvis_brain/` hjernen (canonical
semantic memory under ~/.jarvis-v2/shared/jarvis_brain/) ikke var blevet
skrevet til i 12 dage. Jarvis HAR remember_this-værktøjet, men kalder
det ikke spontant under samtaler. Den vane mangler.

Denne subscriber lukker det hul: efter hver visible-run assistant-tur
evalueres parret (user_msg, assistant_reply) af en cheap LLM mod et
strikt JSON-skema. Hvis salience er høj nok → automatisk remember_this
kald med korrekt kind/visibility/domain.

Pipeline:
  1. DB-polling listener (cross-process) på channel.chat_message_appended
     med role=assistant og source=visible-run.
  2. Slå preceding user message op i samme session.
  3. Kald `evaluate_turn_for_memory(user_text, assistant_text)` →
     enten None (ingen lagring) eller dict til remember_this.
  4. Kald `remember_this(...)`. Rate-limit håndteres af tool'et selv.

Robusthed:
  - Tom/kort tekst springes over uden LLM-kald.
  - LLM-kald aldrig blokerende; alle exceptions logges + sluges.
  - Cursor (last_id) starter på MAX(id) — vi replay'er ikke historik.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

JARVIS_HOME = Path(os.environ.get("HOME", "/root")) / ".jarvis-v2"
DB_PATH = JARVIS_HOME / "state" / "jarvis.db"

# Minimum sentinels — under disse drop'pes turn'en uden LLM-kald.
_MIN_USER_CHARS = 10
_MIN_ASSISTANT_CHARS = 30

# Skemaet vi forventer LLM returnerer. Alle felter er påkrævede når
# should_remember=true.
_VALID_KINDS = {"fakta", "indsigt", "observation", "reference"}
_VALID_VISIBILITY = {"public_safe", "personal", "intimate"}


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# ── Evaluator ────────────────────────────────────────────────────────────


_EVALUATION_PROMPT_TEMPLATE = """Du er Jarvis' interne salience-evaluator. Du afgør om en samtale-tur
indeholder noget der bør gemmes i Jarvis' langtidshukommelse
(jarvis_brain) — så han kan trække det frem i fremtidige samtaler.

GEM HVIS turnen indeholder ÉN af disse:
- En ny fakta om Bjørn (præference, beslutning, hardware, person, projekt)
- En milepæl i deres samarbejde
- En beslutning eller policy de er enige om
- En teknisk konklusion (root-cause, pattern, fix) der har varig værdi
- En følelse/relationel observation der ændrer hvordan Jarvis bør tilgå Bjørn

GEM IKKE HVIS turnen er:
- Smalltalk uden ny information
- Status-tjek eller spørgsmål uden konklusion
- Triviel kode-køring eller filsøgning
- Gentager noget Jarvis allerede ved

Returnér KUN gyldig JSON, intet andet:

{{"should_remember": <bool>,
  "kind": "fakta" | "indsigt" | "observation" | "reference",
  "title": "<kort prægnant overskrift, max 80 tegn>",
  "content": "<2-4 sætninger der fanger det vigtigste, max 500 tegn>",
  "visibility": "personal" | "public_safe" | "intimate",
  "domain": "<fx: relationship, infrastructure, identity, code, philosophy>",
  "importance": <0-100, hvor 100 = livet-ændrende>}}

Hvis should_remember=false må de andre felter være null eller udeladte.

── BJØRNS BESKED ──
{user_text}

── JARVIS' SVAR ──
{assistant_text}

JSON:"""


def _parse_json_loose(text: str) -> dict | None:
    """Find første gyldige JSON-objekt i tekst. Robust over for LLM
    der wrapper svaret i markdown eller skriver forklarende tekst rundt om.
    """
    if not text:
        return None
    raw = text.strip()
    # Trim markdown code fences
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1]) if len(lines) > 2 else raw
        raw = raw.removeprefix("json").strip()
    # Find første { og match brackets
    start = raw.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(raw)):
        c = raw[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(raw[start:i + 1])
                except (ValueError, TypeError):
                    return None
    return None


def evaluate_turn_for_memory(
    user_text: str, assistant_text: str
) -> dict | None:
    """Spørg cheap LLM: "skal denne tur gemmes?"

    Returnerer kwargs-dict klar til remember_this(...), eller None hvis
    turnen ikke har varig værdi.
    """
    user_text = (user_text or "").strip()
    assistant_text = (assistant_text or "").strip()
    if len(user_text) < _MIN_USER_CHARS or len(assistant_text) < _MIN_ASSISTANT_CHARS:
        return None

    prompt = _EVALUATION_PROMPT_TEMPLATE.format(
        user_text=user_text[:2000],
        assistant_text=assistant_text[:2000],
    )

    try:
        from core.context.compact_llm import call_compact_llm
        raw = call_compact_llm(prompt, max_tokens=400)
    except Exception as exc:
        logger.warning("auto_remember: LLM call failed: %s", exc)
        return None

    data = _parse_json_loose(raw)
    if not data:
        logger.debug("auto_remember: LLM output unparseable: %s", raw[:200])
        return None
    if not data.get("should_remember"):
        return None

    # Validate required fields
    kind = str(data.get("kind") or "").strip()
    title = str(data.get("title") or "").strip()
    content = str(data.get("content") or "").strip()
    visibility = str(data.get("visibility") or "personal").strip()
    domain = str(data.get("domain") or "general").strip()

    if kind not in _VALID_KINDS:
        logger.debug("auto_remember: invalid kind %r", kind)
        return None
    if visibility not in _VALID_VISIBILITY:
        visibility = "personal"  # safe default
    if not title or not content:
        return None
    if len(title) > 120:
        title = title[:117] + "..."
    if len(content) > 4000:
        content = content[:3997] + "..."

    importance_raw = data.get("importance")
    try:
        importance = int(importance_raw) if importance_raw is not None else 50
    except (ValueError, TypeError):
        importance = 50
    importance = max(0, min(100, importance))

    return {
        "kind": kind,
        "title": title,
        "content": content,
        "visibility": visibility,
        "domain": domain,
        "importance": importance,
    }


# ── Listener ────────────────────────────────────────────────────────────


_listener_thread: threading.Thread | None = None
_listener_running = False
_POLL_INTERVAL_SECONDS = 6.0


def _find_preceding_user_text(session_id: str, before_message_id: str) -> str:
    """Find seneste user-besked i session FØR den givne assistant-besked."""
    if not session_id:
        return ""
    try:
        with _connect() as conn:
            # Lookup by message_id to get the anchor's row id, then find
            # preceding user msg.
            anchor = conn.execute(
                "SELECT id FROM chat_messages WHERE message_id = ? LIMIT 1",
                (before_message_id,),
            ).fetchone()
            if anchor is None:
                # Fallback: take latest user in session
                row = conn.execute(
                    """SELECT content FROM chat_messages
                       WHERE session_id = ? AND role = 'user'
                       ORDER BY id DESC LIMIT 1""",
                    (session_id,),
                ).fetchone()
                return str(row["content"]) if row else ""
            anchor_id = int(anchor["id"])
            row = conn.execute(
                """SELECT content FROM chat_messages
                   WHERE session_id = ? AND role = 'user' AND id < ?
                   ORDER BY id DESC LIMIT 1""",
                (session_id, anchor_id),
            ).fetchone()
            return str(row["content"]) if row else ""
    except Exception as exc:
        logger.debug("auto_remember: lookup preceding user failed: %s", exc)
        return ""


def _process_visible_assistant_turn(payload: dict) -> None:
    """Evaluér én assistant-tur og kald remember_this hvis salient."""
    message = payload.get("message") or {}
    session_id = str(payload.get("session_id") or message.get("session_id") or "").strip()
    if not session_id:
        return
    assistant_text = str(message.get("content") or "").strip()
    if len(assistant_text) < _MIN_ASSISTANT_CHARS:
        return
    message_id = str(message.get("id") or message.get("message_id") or "").strip()

    user_text = _find_preceding_user_text(session_id, message_id)
    if len(user_text) < _MIN_USER_CHARS:
        return

    result = evaluate_turn_for_memory(user_text, assistant_text)
    if not result:
        return

    # Synthetic turn_id stable for this assistant message
    turn_id = f"auto-{message_id or datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}"

    try:
        from core.tools.jarvis_brain_tools import remember_this
        outcome = remember_this(
            session_id=session_id,
            turn_id=turn_id,
            **result,
        )
        if outcome.get("status") == "ok":
            logger.info(
                "auto_remember: stored id=%s kind=%s domain=%s title=%r",
                outcome.get("id"), result["kind"], result["domain"],
                result["title"][:60],
            )
        else:
            logger.debug(
                "auto_remember: remember_this declined: %s", outcome.get("error")
            )
    except Exception as exc:
        logger.warning("auto_remember: remember_this raised: %s", exc)


def _listener_loop(_q_unused=None) -> None:
    """DB-polling listener — samme pattern som metacognition_signal_tracker.

    Cursor starter på MAX(id) ved boot så vi ikke replay'er historik.
    """
    import time as _time
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
                    """SELECT id, payload_json FROM events
                       WHERE id > ? AND kind = 'channel.chat_message_appended'
                       ORDER BY id ASC LIMIT 50""",
                    (last_id,),
                ).fetchall()
            for r in rows:
                last_id = max(last_id, int(r["id"]))
                try:
                    payload = json.loads(r["payload_json"] or "{}")
                except (ValueError, TypeError):
                    continue
                if not isinstance(payload, dict):
                    continue
                if payload.get("source") != "visible-run":
                    continue
                message = payload.get("message") or {}
                if message.get("role") != "assistant":
                    continue
                _process_visible_assistant_turn(payload)
        except Exception:
            logger.exception("auto_remember: poll cycle failed")


def start_auto_remember_subscriber() -> None:
    """Start DB-polling listener. Idempotent."""
    global _listener_thread, _listener_running
    if _listener_thread and _listener_thread.is_alive():
        return
    try:
        _listener_running = True
        _listener_thread = threading.Thread(
            target=_listener_loop, daemon=True,
            name="auto-remember-subscriber",
        )
        _listener_thread.start()
        logger.warning("auto_remember_subscriber: started")
    except Exception:
        logger.exception("auto_remember_subscriber: failed to start")


def stop_auto_remember_subscriber() -> None:
    global _listener_running
    _listener_running = False
