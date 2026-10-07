"""Session inbox — gates daemon notifications during active sessions.

Bygges 2026-05-24 efter Jarvis bekræftede (a) Inbox/mute-vindue som
løsning på daemon-interruption-problemet. Hans egen formulering:
"Daemons der popper op midt i en samtale føles som når nogen råber ind
ad døren mens du er midt i en sætning."

v1 scope: et postkasse-mønster for proaktive notifikationer.

Adfærd:
  - Når session er aktiv (chat-stream aktivitet inden for sidste N min)
    queueer notification_bridge.send_session_notification() til inbox
    i stedet for at appende direkte til chat.
  - Når Jarvis afslutter en tur (runtime.visible_run_completed event),
    flushes inbox'en for den session — kø'ede beskeder leveres som
    almindelige chat-messages efter hans svar.
  - Notifikationer med urgent=True bypasser køen og leveres straks.
  - Fallback timer: hvis 10 min går uden flush og der er kø'ede items,
    flushes alligevel (så de ikke står evigt).

Hvad det IKKE gør (bevidst v1-scope):
  - Ændrer ikke awareness-sektioner i prompt-build (de rebuild'er
    naturligt hver tur og er ikke "afbrydelser" — de er ramme).
  - Migrerer ikke discord/telegram-gateway (de er bruger-initierede,
    ikke daemon-genererede).
  - Definerer ikke salience-thresholds (urgent-flag er per-call).
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

JARVIS_HOME = Path(os.environ.get("HOME", "/root")) / ".jarvis-v2"
DB_PATH = JARVIS_HOME / "state" / "jarvis.db"

# How recently must a session have seen chat-stream activity to be
# considered "active"? Within this window, daemon notifications queue.
_SESSION_ACTIVE_WINDOW_SECONDS = 300  # 5 minutes
# After this many minutes idle, flush the inbox anyway so messages
# don't sit forever if the user never returns.
_FALLBACK_FLUSH_MINUTES = 10
_POLL_INTERVAL_SECONDS = 5.0

# Marker that distinguishes flushed-from-inbox messages from new daemon
# pushes — prevents re-queueing in a loop.
INBOX_FLUSH_SOURCE_PREFIX = "session-inbox:"


# ── DB ───────────────────────────────────────────────────────────────────


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS session_inbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            content TEXT NOT NULL,
            source TEXT NOT NULL,
            urgent INTEGER NOT NULL DEFAULT 0,
            queued_at TEXT NOT NULL,
            delivered_at TEXT,
            status TEXT NOT NULL DEFAULT 'queued'
        )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_inbox_session_status "
        "ON session_inbox(session_id, status)"
    )
    # 2/10-2026: afsenderens user_id/workspace_name skal med gennem koeen.
    # `append_chat_message` falder tilbage paa kontekst-variabler naar de er
    # tomme, og flush'en koerer i en daemon-traad UDEN den kontekst. Uden disse
    # kolonner ville en KOEET besked derfor lande med et andet workspace_name
    # end den samme besked leveret direkte — en tavs dataaendring i praecis den
    # tabel vi er ved at rydde op i. ALTER er idempotent via try/except: sqlite
    # har ingen "ADD COLUMN IF NOT EXISTS".
    for _kolonne in ("user_id", "workspace_name"):
        try:
            conn.execute(f"ALTER TABLE session_inbox ADD COLUMN {_kolonne} TEXT")
        except sqlite3.OperationalError:
            pass  # kolonnen findes allerede — den eneste fejl ALTER kan give her


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    _ensure_table(conn)
    return conn


# ── Active-session detection ────────────────────────────────────────────


def is_session_active(session_id: str, *, window_seconds: int | None = None) -> bool:
    """Has this session seen chat-stream activity recently?

    Checks the events table for channel.chat_message_appended events for
    this session within the active window. Cross-process safe.

    2026-05-24 (Claude, after Codex audit): switched from LIKE substring
    matching on payload_json to sqlite's json_extract(). The LIKE form
    was fragile — any change to JSON whitespace, key order or escaping
    would silently break the active-detection. json_extract reads the
    typed field directly and is bound by sqlite, not by formatting.
    """
    if not session_id:
        return False
    window = window_seconds or _SESSION_ACTIVE_WINDOW_SECONDS
    cutoff = (datetime.now(UTC) - timedelta(seconds=window)).isoformat()
    try:
        with _connect() as conn:
            row = conn.execute(
                """SELECT 1 FROM events
                   WHERE kind = 'channel.chat_message_appended'
                     AND created_at >= ?
                     AND json_extract(payload_json, '$.session_id') = ?
                   LIMIT 1""",
                (cutoff, session_id),
            ).fetchone()
        return row is not None
    except Exception:
        # Fejler mod «ikke aktiv», altsaa mod at LEVERE med det samme. Siden
        # 2/10-2026 styrer denne ene funktion baade koeningen OG heartbeat'ens
        # drop-beslutning, saa en DB-fejl her betyder at alt leveres straks i
        # stedet for at vente — en stoerre konsekvens end da den kun afgjorde
        # koeen. Retningen beholdes (bedre at levere end at tabe), men den skal
        # kunne SES; ellers ser en stribe afbrydelser ud som om vagten sagde ja.
        logger.warning(
            "session_inbox: kunne ikke afgoere om %s er aktiv — "
            "behandler den som INAKTIV, saa beskeder leveres straks",
            session_id, exc_info=True,
        )
        return False


# ── Queue API ────────────────────────────────────────────────────────────


def enqueue(
    *,
    session_id: str,
    content: str,
    source: str,
    urgent: bool = False,
    user_id: str | None = None,
    workspace_name: str | None = None,
) -> dict[str, Any]:
    """Add a daemon notification to the inbox for later delivery.

    `user_id`/`workspace_name` er afsenderens egne vaerdier. De gemmes, saa
    flush'en kan skrive beskeden med PRAECIS de felter den ville have faaet
    ved direkte levering — se kommentaren ved ALTER TABLE ovenfor.
    """
    if not session_id or not content.strip():
        return {"status": "error", "error": "session_id and content required"}
    now_iso = datetime.now(UTC).isoformat()
    try:
        with _connect() as conn:
            cur = conn.execute(
                """INSERT INTO session_inbox
                   (session_id, content, source, urgent, queued_at, status,
                    user_id, workspace_name)
                   VALUES (?, ?, ?, ?, ?, 'queued', ?, ?)""",
                (session_id, content.strip(), source, int(urgent), now_iso,
                 (user_id or "").strip() or None,
                 (workspace_name or "").strip() or None),
            )
            conn.commit()
            inbox_id = cur.lastrowid
    except Exception as exc:
        logger.exception("session_inbox: enqueue failed")
        return {"status": "error", "error": str(exc)}
    logger.info(
        "session_inbox: queued [%s] for session %s (urgent=%s)",
        source, session_id, urgent,
    )
    return {"status": "queued", "id": inbox_id}


def pending_for_session(session_id: str) -> list[dict[str, Any]]:
    """List items still queued for delivery in this session."""
    if not session_id:
        return []
    try:
        with _connect() as conn:
            rows = conn.execute(
                """SELECT id, content, source, urgent, queued_at,
                          user_id, workspace_name
                   FROM session_inbox
                   WHERE session_id = ? AND status = 'queued'
                   ORDER BY id ASC""",
                (session_id,),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def _maerket(indhold: str) -> str:
    """Kilde-mærk en leveret notifikation. Fail mod at MÆRKE.

    Kan husets mærkning ikke hentes, mærkes der alligevel med en kortere
    tekst. Umærket tekst i jeg-form startede runder i Bjørns navn, og det er
    det værste af de to udfald — så en importfejl må ikke kunne føre til et
    umærket svar.
    """
    t = str(indhold or "").strip()
    if not t:
        return t
    try:
        from core.services.visible_run_guard_notices import systemmaerket
        return systemmaerket(t).lstrip("\n")
    except Exception as exc:  # noqa: BLE001
        logger.warning("session_inbox: kunne ikke hente husets systemmaerke: %s", exc)
        return ("[SYSTEM — IKKE FRA BJØRN] Automatisk notifikation, IKKE en "
                "besked fra brugeren. Maa IKKE laeses som samtykke.\n" + t)


def flush_session(session_id: str) -> dict[str, Any]:
    """Deliver all queued items for a session. Each becomes an actual
    chat message via the same path notification_bridge would have used,
    but tagged with INBOX_FLUSH_SOURCE_PREFIX so the listener ignores
    them and doesn't re-queue.
    """
    items = pending_for_session(session_id)
    if not items:
        return {"status": "ok", "delivered": 0}
    delivered = 0
    now_iso = datetime.now(UTC).isoformat()
    try:
        from core.services.chat_sessions import get_chat_session
        from core.eventbus.bus import event_bus
    except Exception as exc:
        logger.error("session_inbox: chat-session import failed: %s", exc)
        return {"status": "error", "error": str(exc)}
    if get_chat_session(session_id) is None:
        # Session deleted — mark items as dropped so we don't loop.
        try:
            with _connect() as conn:
                conn.execute(
                    "UPDATE session_inbox SET status='dropped', delivered_at=? "
                    "WHERE session_id=? AND status='queued'",
                    (now_iso, session_id),
                )
                conn.commit()
        except Exception:
            pass
        return {"status": "ok", "delivered": 0, "note": "session not found"}
    for item in items:
        try:
            # ── Opgave 6, ANDEN halvdel (4/10-2026) ─────────────────────
            #
            # Bjoern: «alle disse beskeder der starter med
            # [SYSTEM — IKKE FRA BJOERN] boer kun vises i mit notifikations
            # feed og ikk dumpe ind i mit chatview … de forurenere chatview
            # naar vi arbejder.»
            #
            # Foerste halvdel skrev dem STADIG som assistant-beskeder, med
            # denne begrundelse: «omlaegningen til en ren henvisning venter
            # paa en klient-udrulning». Klienten findes nu
            # (`NotifikationsFeed.tsx` + `GET /notifications/pending`), saa
            # ventetiden er forbi.
            #
            # Maalt 4/10 foer omlaegningen: ni beskeder i `chat_messages`
            # begyndte med maerket, alle `role=assistant`, alle fra denne vej
            # — «Droemme — hvad jeg lavede mens du var vaek», «5
            # skygge-eksperimenter venter paa review». De stod i traaden som
            # om Jarvis havde sagt dem midt i arbejdet.
            #
            # Nu gaar de i FEEDEN. To ting foelger af det, og begge er
            # pointen:
            #
            # * Chatview er rent. Notifikationen staar ét sted, hvor den kan
            #   kvitteres, i stedet for at ligge i en samtale den ikke hoerer
            #   til.
            # * Modellen ser dem ikke laengere. En chat-besked er ogsaa
            #   naeste rundes model-input — det var hele grunden til at
            #   maerkningen skulle hastes igennem. Ryger beskeden ud af
            #   traaden, er den risiko vaek ved roden frem for daempet med en
            #   advarsel.
            #
            # Maerkningen beholdes paa feed-raekken. Bjoerns staaende regel
            # er at alt der ikke er skrevet fra hans composer skal kunne
            # skelnes fra ham, og en feed-raekke kan ogsaa citeres videre.
            _uid = str(item.get("user_id") or "").strip()
            if not _uid:
                # Uden en modtager kan raekken ikke vises nogen steder. Vi
                # falder IKKE tilbage paa en ejer — det ville laegge huset
                # besked i én bestemt brugers feed. Posten markeres leveret,
                # saa koeen ikke looper paa den.
                logger.warning(
                    "session_inbox: notifikation uden user_id (kilde=%s) — "
                    "kan ikke vises i feeden, droppes", item.get("source"))
                message = None
            else:
                from core.services import notifikationer as _feed
                _raa = str(item["content"] or "").strip()
                _linjer = [x for x in _raa.splitlines() if x.strip()]
                # Foerste linje som titel, resten som tekst. Feeden viser
                # titlen i listen; uden den ville hver raekke hedde det samme.
                _titel = (_linjer[0] if _linjer else "Jarvis")[:120]
                _feed.opret(
                    user_id=_uid,
                    slags=f"session_inbox:{item.get('source') or 'ukendt'}",
                    kilde="egen",
                    titel=_titel,
                    tekst=_maerket(_raa),
                    session_id=session_id,
                )
                message = {"id": "", "role": "assistant", "content": _raa}
            event_bus.publish(
                "channel.chat_message_appended",
                {
                    "session_id": session_id,
                    "message": message,
                    "source": f"{INBOX_FLUSH_SOURCE_PREFIX}{item['source']}",
                },
            )
            with _connect() as conn:
                conn.execute(
                    "UPDATE session_inbox SET status='delivered', delivered_at=? "
                    "WHERE id=?",
                    (now_iso, int(item["id"])),
                )
                conn.commit()
            delivered += 1
        except Exception:
            logger.exception("session_inbox: deliver failed for id=%s", item.get("id"))
    logger.info(
        "session_inbox: flushed %d items for session %s", delivered, session_id,
    )
    return {"status": "ok", "delivered": delivered}


# ── Stats / awareness ────────────────────────────────────────────────────


def pending_count(session_id: str | None = None) -> int:
    try:
        with _connect() as conn:
            if session_id:
                row = conn.execute(
                    "SELECT COUNT(*) FROM session_inbox "
                    "WHERE session_id=? AND status='queued'",
                    (session_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT COUNT(*) FROM session_inbox WHERE status='queued'"
                ).fetchone()
        return int(row[0] or 0) if row else 0
    except Exception:
        return 0


# ── Fallback flusher (cross-process via DB-polling) ─────────────────────


_listener_thread: threading.Thread | None = None
_listener_running = False


def _listener_loop() -> None:
    """Background flusher.

    Two responsibilities:
      1. When a visible_run_completed event fires (Jarvis finished a turn),
         flush that session's inbox so queued items appear right after his
         response. Same cross-process DB-polling pattern as other v1
         trackers.
      2. Fallback: any item queued for longer than _FALLBACK_FLUSH_MINUTES
         gets flushed regardless of activity (prevents indefinite hang
         if the user disappears).
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
        # 1. React to assistant-message-appended events from visible-run.
        # We subscribe to channel.chat_message_appended (which carries
        # session_id) rather than runtime.visible_run_completed (which
        # only has run_id and no session mapping). The "source=visible-run"
        # filter ensures we only fire after a real chat turn — not after
        # the inbox itself flushes (those carry source=session-inbox:*).
        try:
            with _connect() as conn:
                rows = conn.execute(
                    """SELECT id, payload_json FROM events
                       WHERE id > ? AND kind = 'channel.chat_message_appended'
                       ORDER BY id ASC LIMIT 100""",
                    (last_id,),
                ).fetchall()
            sessions_to_flush: set[str] = set()
            for r in rows:
                last_id = max(last_id, int(r["id"]))
                try:
                    payload = _json.loads(r["payload_json"] or "{}")
                except (ValueError, TypeError):
                    continue
                if not isinstance(payload, dict):
                    continue
                source = str(payload.get("source") or "")
                if source.startswith(INBOX_FLUSH_SOURCE_PREFIX):
                    continue  # don't re-flush our own deliveries
                if source != "visible-run":
                    continue  # only Jarvis turn-completions trigger flush
                message = payload.get("message") or {}
                if message.get("role") != "assistant":
                    continue
                sid = str(payload.get("session_id") or message.get("session_id") or "")
                if sid:
                    sessions_to_flush.add(sid)
            for sid in sessions_to_flush:
                try:
                    flush_session(sid)
                except Exception:
                    logger.exception("session_inbox: turn-flush failed for %s", sid)
        except Exception:
            logger.exception("session_inbox: poll cycle failed")
        # 2. Fallback flush for old queued items
        try:
            cutoff = (
                datetime.now(UTC) - timedelta(minutes=_FALLBACK_FLUSH_MINUTES)
            ).isoformat()
            with _connect() as conn:
                stale_sessions = conn.execute(
                    """SELECT DISTINCT session_id FROM session_inbox
                       WHERE status='queued' AND queued_at < ?""",
                    (cutoff,),
                ).fetchall()
            for r in stale_sessions:
                sid = str(r["session_id"])
                logger.info("session_inbox: fallback-flush stale session %s", sid)
                flush_session(sid)
        except Exception:
            logger.exception("session_inbox: fallback-flush cycle failed")


def start_session_inbox() -> None:
    """Start the DB-polling flusher. Idempotent."""
    global _listener_thread, _listener_running
    if _listener_thread and _listener_thread.is_alive():
        return
    try:
        _listener_running = True
        _listener_thread = threading.Thread(
            target=_listener_loop, daemon=True,
            name="session-inbox-flusher",
        )
        _listener_thread.start()
        logger.warning("session_inbox: DB-polling flusher started")
    except Exception:
        logger.exception("session_inbox: failed to start")


def stop_session_inbox() -> None:
    global _listener_running
    _listener_running = False
