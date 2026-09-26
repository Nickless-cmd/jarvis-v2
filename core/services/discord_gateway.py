"""Discord gateway — runs discord.py in a dedicated daemon thread.

Completely isolated from FastAPI's asyncio loop. Inbound messages trigger
start_autonomous_run() which writes the response to the session; an eventbus
subscriber picks up channel.chat_message_appended events for Discord sessions
and routes them back to Discord.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import queue
import re
import threading
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("uvicorn.error")

# Runtime process URL — where the gateway actually runs. API process
# dispatches send intents here via HTTP because _outbound_queue is
# module-local and can't cross process boundaries.
_RUNTIME_DISPATCH_URL = os.environ.get(
    "JARVIS_RUNTIME_URL", "http://127.0.0.1:8011"
).rstrip("/")

# ── State ──────────────────────────────────────────────────────────────

_client: Any = None          # discord.Client instance
_loop: asyncio.AbstractEventLoop | None = None
_thread: threading.Thread | None = None
_thread_running: bool = False
_outbound_task: Any = None   # strong ref til _send_outbound_loop-task (må ikke GC'es → "Task destroyed but pending")

_outbound_queue: queue.Queue = queue.Queue()  # (channel_id: int, text: str)

# Sessions owned by Discord: {session_id → discord_channel_id}
_discord_sessions: dict[str, int] = {}
_discord_sessions_lock = threading.Lock()

# ── Streaming (message-edit) ───────────────────────────────────────────
# Bjørn 26/9-2026: Discord føltes langsommere end desk, fordi svaret blev
# bufferet og dumpet FØRST når kørslen var færdig — tre prikker og ingen tekst.
# Løsningen er Discords egen teknik: send en placeholder med det samme og
# redigér den mens teksten kommer ind.
#
# Live-teksten læses fra run_follow-bufferen, der ligger i SAMME proces som
# gatewayen (jarvis-runtime, JARVIS_ENABLE_RUNTIME_SERVICES=1) for Discord-runs
# → ingen HTTP nødvendig. Den ENDELIGE tekst ejes fortsat af
# _eventbus_subscriber_loop; streameren laver kun preview.
#
# Discord-rate-limit: 5 redigeringer pr. 5 sek. pr. kanal → hold ~1,6 s mellem.
_STREAM_EDIT_INTERVAL_S = 1.6
_STREAM_POLL_S = 0.6
_STREAM_MAX_S = 900.0        # absolut loft på én preview-session
_STREAM_PLACEHOLDER = "…"
_STREAM_MAX_CHARS = 1900     # Discord-beskedloft minus margin

# session_id → {"message", "accumulated", "last_edit", "finished", "stopped", "channel_id"}
_stream_state: dict[str, dict] = {}
_stream_lock = threading.Lock()


def get_discord_channel_for_session(session_id: str) -> int | None:
    """Lookup which Discord channel (if any) ejer denne session.

    Returnerer channel_id hvis sessionen blev oprettet via Discord-DM/channel,
    ellers None. Bruges af visible_runs.py til at sende tool-progress status
    tilbage til Discord under lange agentic loops.

    Opslag-strategi (2026-06-11 fix efter Bjørn observation: in-memory
    dict tabt efter restart):
      1. Tjek in-memory _discord_sessions først (hurtigst)
      2. Hvis ikke fundet: tjek chat_sessions.title for "Discord" præfiks.
         Hvis ja → returnér owner-DM channel ID (fallback for kendte
         Discord-bound sessioner, samme strategi som _resolve_channel_
         for_session bruger til closure-gate notifikationer)
      3. Ellers: None (sessionen er ikke Discord-bound, send intet)
    """
    if not session_id:
        return None
    sid = str(session_id)

    # 1. In-memory lookup (hurtigst)
    with _discord_sessions_lock:
        cached = _discord_sessions.get(sid)
        if cached:
            return cached

    # 2. DB-fallback: er det en Discord-titled session?
    try:
        from core.runtime.db import connect
        with connect() as conn:
            row = conn.execute(
                "SELECT title FROM chat_sessions WHERE session_id = ?",
                (sid,),
            ).fetchone()
        if row:
            title = str(row[0] if not isinstance(row, dict) else row.get("title") or "")
            if title.startswith("Discord") or "Discord DM" in title:
                # Owner DM channel — samme fallback som
                # _resolve_channel_for_session bruger. Hardcoded fordi
                # Bjørn er eneste Discord-bruger der får DM med Jarvis
                # i den nuværende deployment.
                # Cache i in-memory dict så næste opslag er hurtigt.
                owner_dm = 1474048593219555461
                with _discord_sessions_lock:
                    _discord_sessions[sid] = owner_dm
                return owner_dm
    except Exception as exc:
        logger.debug("get_discord_channel_for_session db-lookup fejl: %s", exc)

    return None

# Channels currently typing: cleared when outbound message is sent
_typing_channels: set[int] = set()
_typing_lock = threading.Lock()

# Rate limiting for non-owner users: {user_id → last_response_time}
_user_last_response: dict[int, float] = {}
_RATE_LIMIT_SECONDS = 10.0

# Status tracking
_status: dict[str, Any] = {
    "connected": False,
    "guild_name": None,
    "last_message_at": None,
    "message_count": 0,
    "connect_error": None,
}

# Eventbus subscriber thread
_sub_thread: threading.Thread | None = None
_sub_running: bool = False

# Deduplication: track recently-processed Discord message IDs.
# Prevents double-processing from reconnect re-delivery or Intents.all() quirks.
_seen_message_ids: set[str] = set()
_seen_message_ids_lock = threading.Lock()
_SEEN_MESSAGE_IDS_MAX = 200

# Cross-process status sharing: the gateway owns a module-level `_status`
# dict, but tools in other processes (jarvis-api) can't see it. We mirror
# status to runtime_state_kv so any reader sees the same truth.
_STATUS_KV_KEY = "discord_gateway.status"
_STATUS_STALE_AFTER = 120.0  # seconds before persisted state is suspect
_STATUS_HB_INTERVAL = 30.0   # seconds between heartbeat refreshes

_hb_thread: threading.Thread | None = None
_hb_running: bool = False


def _persist_status() -> None:
    """Mirror current _status to runtime_state_kv for cross-process readers."""
    try:
        from core.runtime.db import set_runtime_state_value
        set_runtime_state_value(_STATUS_KV_KEY, {
            "connected": _status["connected"],
            "guild_name": _status["guild_name"],
            "last_message_at": _status["last_message_at"],
            "message_count": _status["message_count"],
            "connect_error": _status["connect_error"],
            "active_discord_sessions": len(_discord_sessions),
            "updated_at": datetime.now(UTC).isoformat(),
        })
    except Exception as exc:
        logger.debug("discord_gateway: persist_status failed: %s", exc)


def _status_heartbeat_loop() -> None:
    """Refresh persisted status every _STATUS_HB_INTERVAL seconds.

    Without this, a silent crash (no `connected=False` write) would leave a
    stale 'connected=True' in the KV forever. The heartbeat's fresh timestamp
    lets readers detect staleness.
    """
    while _hb_running:
        _persist_status()
        for _ in range(int(_STATUS_HB_INTERVAL * 10)):
            if not _hb_running:
                return
            time.sleep(0.1)


def get_discord_status() -> dict[str, Any]:
    """Return current gateway status.

    Reads from runtime_state_kv so processes that don't own the gateway
    (jarvis-api) still see the correct state. Falls back to module-local
    state only when nothing has been persisted yet.
    """
    try:
        from core.runtime.db import get_runtime_state_value
        persisted = get_runtime_state_value(_STATUS_KV_KEY, None)
    except Exception:
        persisted = None

    if isinstance(persisted, dict) and persisted.get("updated_at"):
        stale = True
        try:
            updated = datetime.fromisoformat(str(persisted["updated_at"]))
            age = (datetime.now(UTC) - updated).total_seconds()
            stale = age > _STATUS_STALE_AFTER
        except Exception:
            pass
        out = {
            "connected": bool(persisted.get("connected")) and not stale,
            "guild_name": persisted.get("guild_name"),
            "last_message_at": persisted.get("last_message_at"),
            "message_count": int(persisted.get("message_count") or 0),
            "connect_error": persisted.get("connect_error"),
            "active_discord_sessions": int(persisted.get("active_discord_sessions") or 0),
            "stale": stale,
        }
        return out

    return {
        "connected": _status["connected"],
        "guild_name": _status["guild_name"],
        "last_message_at": _status["last_message_at"],
        "message_count": _status["message_count"],
        "connect_error": _status["connect_error"],
        "active_discord_sessions": len(_discord_sessions),
        "stale": False,
    }


def _is_gateway_owner() -> bool:
    """True if the discord client thread is running in this process."""
    return _thread is not None and _thread.is_alive()


def _dispatch_to_runtime(action: str, args: dict) -> dict:
    """Forward a send intent to the runtime process via internal HTTP."""
    url = f"{_RUNTIME_DISPATCH_URL}/api/internal/discord/dispatch"
    payload = json.dumps({"action": action, "args": args}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:200]
        return {"status": "error", "reason": f"runtime-http-{exc.code}: {detail}"}
    except Exception as exc:
        return {"status": "error", "reason": f"runtime-dispatch-failed: {exc}"}


def send_discord_message(channel_id: int, text: str) -> None:
    """Thread-safe: queue a message to be sent to a Discord channel.

    Runs locally if this process owns the gateway; otherwise dispatches
    to the runtime process via internal HTTP.
    """
    # Communication guard — backstop: scrub hård afslutnings-fraser
    # (godnat/sov godt) før de når Bjørn. Bløde fraser røres ikke.
    try:
        from core.services.communication_guard import guard_channel_text
        scrubbed = guard_channel_text(text, "discord")
        if text and not scrubbed.strip():
            return  # hele beskeden var en afslutnings-frase → send ingenting
        text = scrubbed
    except Exception:
        pass
    if _is_gateway_owner():
        _outbound_queue.put_nowait((channel_id, text))
        return
    result = _dispatch_to_runtime(
        "send_message", {"channel_id": int(channel_id), "text": str(text)}
    )
    if result.get("status") == "error":
        logger.warning(
            "discord_gateway: cross-process send failed: %s", result.get("reason")
        )


def start_discord_typing(channel_id: int) -> None:
    """Tænd «Jarvis skriver…» og hold den kørende indtil næste besked sendes.

    Erstatter tekst-progress-linjerne i Discord-kanalen. De gav Bjørn besked
    om at Jarvis var i live, men efterlod én besked pr. værktøjsrunde — rod
    uden værdi (målt 26/9-2026: ét svar gav otte «Runde N»-linjer ovenover
    selve teksten). Typing-indikatoren siger det samme uden at skrive i
    kanalen, og `_typing_loop` fornyer den hvert 8. sek, så den dækker hele
    kørslen — også de 3+ min hvor første LLM-kald tænker.

    Thread-safe. Lægges i outbound-køen når denne proces ejer gatewayen, så
    `_send_outbound_loop` kan starte loop'en i dens egen event-loop (kalderen
    kører i en anden tråd). Ellers dispatches intentet til runtime-processen.
    """
    if _is_gateway_owner():
        _outbound_queue.put_nowait({"channel_id": int(channel_id), "typing": True})
        return
    _dispatch_to_runtime("start_typing", {"channel_id": int(channel_id)})


def _download_attachment(attachment: Any, session_id: str) -> dict:
    """Download a single discord.Attachment via attachment_service."""
    from core.services.attachment_service import download_and_store
    return download_and_store(
        url=attachment.url,
        filename=attachment.filename,
        mime_type=attachment.content_type or "",
        size_bytes=attachment.size,
        session_id=session_id,
        channel_type="discord",
    )


def _build_attachment_prefix(attachments: list, session_id: str) -> str:
    """Build content prefix lines for all attachments in a Discord message."""
    if not attachments:
        return ""
    lines = []
    for att in attachments:
        result = _download_attachment(att, session_id)
        if result["status"] == "ok":
            aid = result["attachment_id"]
            mime = att.content_type or "?"
            size_kb = round(att.size / 1024, 1)
            lines.append(
                f"[Fil modtaget: {att.filename} ({mime}, {size_kb} KB) — id: {aid}]"
            )
        else:
            reason = result.get("reason", "ukendt fejl")
            lines.append(f"[Fil kunne ikke hentes: {att.filename} — {reason}]")
    return "\n".join(lines) + "\n"


def _validate_send_path(path: str) -> tuple[bool, str]:
    from core.services.attachment_service import validate_send_path
    return validate_send_path(path)


def send_discord_file(channel_id: int, text: str, file_path: str) -> dict:
    """Queue a file send to a Discord channel. Validates path first."""
    if _is_gateway_owner():
        ok, err = _validate_send_path(file_path)
        if not ok:
            return {"status": "error", "reason": err}
        _outbound_queue.put_nowait({"channel_id": channel_id, "text": text, "file_path": file_path})
        return {"status": "queued", "channel_id": channel_id, "file_path": file_path}
    return _dispatch_to_runtime(
        "send_file",
        {"channel_id": int(channel_id), "text": str(text), "file_path": str(file_path)},
    )


def _open_dm_and_send(
    recipient_discord_id: int,
    text: str,
    timeout: float,
    max_retries: int = 3,
    retry_delay: float = 5.0,
) -> dict[str, object]:
    """Open DM channel with a Discord user and queue a message. Gateway-process only.

    Retries up to `max_retries` times with `retry_delay` seconds between attempts.
    Transient Discord API errors (rate-limit, network blip, timeout) are retried;
    permanent errors (not-connected, unknown user) are NOT retried.
    """
    first_attempt_ts = time.monotonic()

    for attempt in range(1, max_retries + 1):
        # ── Connection check (not retried — if gateway is down, waiting won't help) ──
        if not _status["connected"] or _client is None or _loop is None:
            if attempt == 1:
                return {"status": "error", "reason": "discord-not-connected"}
            # Subsequent attempts: gateway may have reconnected, so retry once
            time.sleep(retry_delay)
            continue

        # ── Remaining timeout for this attempt ──
        elapsed = time.monotonic() - first_attempt_ts
        remaining_timeout = max(timeout - elapsed, timeout / 2)

        async def _open() -> int:
            user = await _client.fetch_user(recipient_discord_id)
            dm_channel = await user.create_dm()
            return dm_channel.id

        try:
            future = asyncio.run_coroutine_threadsafe(_open(), _loop)
            channel_id = future.result(timeout=remaining_timeout)
            send_discord_message(channel_id, text)
            if attempt > 1:
                logger.info(
                    "discord_gateway: DM to %d succeeded on attempt %d",
                    recipient_discord_id, attempt,
                )
            return {"status": "sent", "channel_id": channel_id}
        except Exception as exc:
            reason = str(exc)
            # ── Distinguish permanent from transient errors ──
            exc_lower = reason.lower()
            is_transient = any(
                marker in exc_lower
                for marker in [
                    "timeout", "rate limit", "rate_limit",
                    "429", "500", "502", "503", "504",
                    "temporary", "try again", "connection",
                    "reset", "refused", "broken pipe",
                    "http exception", "gateway timeout",
                    "unknown error",
                ]
            )
            if not is_transient:
                # Permanent error: don't retry
                return {"status": "error", "reason": reason}

            if attempt < max_retries:
                delay = retry_delay * attempt  # linear backoff: 5s, 10s, 15s
                logger.warning(
                    "discord_gateway: DM to %d attempt %d/%d failed (%s) — retrying in %.0fs",
                    recipient_discord_id, attempt, max_retries, reason, delay,
                )
                time.sleep(delay)
            else:
                logger.error(
                    "discord_gateway: DM to %d failed after %d attempts: %s",
                    recipient_discord_id, max_retries, reason,
                )
                return {"status": "error", "reason": f"DM failed after {max_retries} attempts: {reason}"}

    return {"status": "error", "reason": "DM failed — unexpected retry exhaustion"}


def send_dm_to_owner(text: str, timeout: float = 10.0) -> dict[str, object]:
    """Send a DM directly to the owner via owner_discord_id.

    ## Testmiljøet må ALDRIG nå hans telefon

    Bjørn fik to alarmer 12/9-2026 kl. 22:36 og 22:45: «⚠️ Self-repair failed:
    X — Action: control_daemon → test failure». Ingen af delene var ægte.
    `tests/test_self_repair_integration.py` opretter et mønster med `name="X"`,
    og fejl-stien kalder `_notify_owner_async` → hertil. Der stod ingen
    tilsvarende række i `self_repair_attempts` overhovedet; beskeden kom fra en
    testkørsel.

    Vagten sidder HER og ikke hos den enkelte kalder, fordi der er fem af dem
    (self_repair_engine, process_watcher, restart_self_tools,
    simple_tools_native, og gatewayen selv). En vagt pr. kalder ville skulle
    huskes hver gang der kommer en sjette. Denne skal huskes én gang.

    Samme markør som `central_timeseries` allerede bruger.
    """
    import os
    if "PYTEST_CURRENT_TEST" in os.environ:
        logger.info("discord: DM til ejeren DROPPET (testmiljø): %s", str(text)[:80])
        return {"status": "skipped", "reason": "pytest"}
    if not _is_gateway_owner():
        return _dispatch_to_runtime(
            "send_dm_to_owner",
            {"text": str(text), "timeout": float(timeout)},
        )
    from core.services.discord_config import load_discord_config
    cfg = load_discord_config()
    if not cfg:
        return {"status": "error", "reason": "discord-not-configured"}
    return _open_dm_and_send(int(cfg["owner_discord_id"]), text, timeout)


def send_dm_to_user(
    recipient_discord_id: str,
    text: str,
    timeout: float = 10.0,
) -> dict[str, object]:
    """DM a known Discord user by ID.

    Recipient must be registered in users.json (privacy boundary — Jarvis
    must not be able to DM arbitrary Discord users he somehow learns the
    ID of). Returns {status:'sent', channel_id, recipient_name} on success.
    """
    if not _is_gateway_owner():
        return _dispatch_to_runtime(
            "send_dm_to_user",
            {
                "recipient_discord_id": str(recipient_discord_id),
                "text": str(text),
                "timeout": float(timeout),
            },
        )

    from core.identity.users import load_users
    users = load_users()
    recipient = next(
        (u for u in users if str(u.discord_id) == str(recipient_discord_id)),
        None,
    )
    if recipient is None:
        return {
            "status": "error",
            "reason": (
                f"unknown-recipient: discord_id {recipient_discord_id} is not "
                f"in users.json — refusing to DM unknown user"
            ),
        }

    result = _open_dm_and_send(int(recipient_discord_id), text, timeout)
    if result.get("status") == "sent":
        result["recipient_name"] = recipient.name
    return result


def _get_or_create_discord_session(
    channel_id: int,
    is_dm: bool,
    owner_discord_id: str,
    author_id: str = "",
) -> str:
    """Return session_id for this Discord channel. Creates session if needed.

    DM sessions: ONE per author_id — så Bjørn og Michelle ikke deler DM-historie.
    Public channel sessions: one per channel_id (multi-user by design).
    """
    from core.services.chat_sessions import (
        create_chat_session,
        list_chat_sessions,
    )

    if is_dm:
        # DM: one dedicated session PER user — crucial for multi-user isolation.
        # Backwards-compat: gammel "Discord DM"-session uden user-suffix bliver
        # automatisk forladet (ny title-struktur); eksisterende chat-history
        # ligger under den gamle session.
        target_title = (
            f"Discord DM — {author_id}" if author_id
            else "Discord DM"
        )
        for s in list_chat_sessions():
            if s.get("title") == target_title:
                return str(s["id"])
        return str(create_chat_session(title=target_title)["id"])
    else:
        # Public channel: one session per channel (flere brugere kan dele)
        target_title = f"Discord #{channel_id}"
        for s in list_chat_sessions():
            if s.get("title") == target_title:
                return str(s["id"])
        return str(create_chat_session(title=target_title)["id"])


# Kode-fence-linje (``` eller ~~~), evt. med sprog-tag. Bruges til at holde
# styr på om en chunk slutter inde i en kodeblok.
_FENCE_LINE_RE = re.compile(r"^\s*(`{3,}|~{3,})")


def _is_table_row(line: str) -> bool:
    """En tabel-række: starter med `|` og har mindst to pipe-tegn (`| a | b |`)."""
    s = line.strip()
    return s.startswith("|") and s.count("|") >= 2


def _is_table_separator(line: str) -> bool:
    """True for GFM-separatorrækken (`| --- | :--: |`) der skelner header fra data."""
    s = line.strip()
    if not s.startswith("|"):
        return False
    cells = [c.strip() for c in s.strip("|").split("|")]
    return bool(cells) and all(re.fullmatch(r":?-{1,}:?", c) for c in cells)


def _wrap_tables_for_discord(text: str) -> str:
    """Pak GFM-tabeller i kode-fences — Discord tegner dem ikke ellers.

    Normalizeren (`markdown_structure.normalize_markdown_structure`) kører for
    ALLE kanaler og producerer rigtige GFM-tabeller. Discord har ingen
    tabel-renderer: rækkerne står som rå `| a | b |`-tegn. Indholdet i en
    ```-blok tegnes monospace og på linje, så tabellen bliver læsbar igen.
    Rører ikke tabeller der allerede står inde i en fence."""
    if "|" not in text:
        return text
    lines = text.split("\n")
    out: list[str] = []
    fence: str | None = None
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _FENCE_LINE_RE.match(line)
        if m:
            fence = None if fence else m.group(1)
            out.append(line)
            i += 1
            continue
        if (
            fence is None
            and _is_table_row(line)
            and i + 1 < len(lines)
            and _is_table_separator(lines[i + 1])
        ):
            j = i
            while j < len(lines) and _is_table_row(lines[j]):
                j += 1
            out.append("```")
            out.extend(lines[i:j])
            out.append("```")
            i = j
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


# CommonMark thematic break (`---`, `***`, `___`) på sin egen linje. Discord
# tegner den ikke — den står som rå tekst.
_THEMATIC_BREAK_RE = re.compile(r"^\s*([-*_])(?:\s*\1){2,}\s*$")

# ATX-header med 4+ hashes. Discord har kun #/##/### — dybere står som rå tekst.
_ATX_DEEP_RE = re.compile(r"^(\s{0,3})(#{4,})(\s+)")

_DISCORD_RULE = "─" * 30


def _downgrade_unsupported_for_discord(text: str) -> str:
    """Nedgrader markdown Discord ikke tegner, så det ikke står som rå tegn.

    - `---` (thematic break) → en box-drawing-linje der læses som skillelinje.
    - `####`+ overskrift → `###` (Discords dybeste). Samme visuelle vægt som
      desk' mindste overskrift — nærmeste match.
    Kode-fences lades i fred (samme fence-sporing som tabel-wrapperen)."""
    if not text:
        return text
    lines = text.split("\n")
    out: list[str] = []
    fence: str | None = None
    for line in lines:
        m = _FENCE_LINE_RE.match(line)
        if m:
            fence = None if fence else m.group(1)
            out.append(line)
            continue
        if fence is None:
            if _THEMATIC_BREAK_RE.match(line):
                out.append(_DISCORD_RULE)
                continue
            dm = _ATX_DEEP_RE.match(line)
            if dm:
                out.append(f"{dm.group(1)}###{dm.group(3)}{line[dm.end():]}")
                continue
        out.append(line)
    return "\n".join(out)


def _split_message(text: str, limit: int) -> list[str]:
    """Split text into chunks of at most `limit` characters.

    Linjebevidst: bryder ved linjeskift frem for midt i en linje, og holder
    styr på åbne kode-fences — en fence der krydser grænsen lukkes ved
    chunk-slut og genåbnes ved næste chunks start, så Discord ikke viser
    halve kodeblokke. En enkelt linje længere end `limit` hard-splittes."""
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    cur: list[str] = []
    cur_len = 0
    fence: str | None = None

    for line in text.split("\n"):
        add = len(line) + (1 if cur else 0)
        # En åben fence koster en ekstra lukke-linje ved chunk-slut — hold
        # plads til den, så ingen chunk overskrider loftet.
        budget = limit - (len(fence) + 1 if fence else 0)
        if cur and cur_len + add > budget:
            # Luk en åben fence i den chunk vi forlader, og genåbn i næste —
            # ellers står resten af koden som løs tekst hos Discord.
            body = "\n".join(cur)
            if fence:
                body = body + "\n" + fence
            chunks.append(body)
            cur = []
            cur_len = 0
            if fence:
                cur.append(fence)
                cur_len = len(fence)
                add = len(line) + 1
        if not cur and len(line) > limit:
            # Enkelt linje større end hele loftet: hard-split (kan ikke brydes
            # ved linjeskift). Fence-linjer er korte og rammer aldrig her.
            for k in range(0, len(line), limit):
                chunks.append(line[k:k + limit])
            continue
        cur.append(line)
        cur_len += add
        m = _FENCE_LINE_RE.match(line)
        if m:
            fence = None if fence else m.group(1)
    if cur:
        chunks.append("\n".join(cur))
    return chunks


async def _typing_loop(channel_id: int) -> None:
    """Keep showing 'typing...' indicator until the outbound message is sent."""
    tick = 0
    while True:
        with _typing_lock:
            if channel_id not in _typing_channels:
                break
        try:
            if _client:
                await _client.http.send_typing(channel_id)
                if tick == 0:
                    try:
                        from core.eventbus.bus import event_bus as _ebus_t
                        _ebus_t.publish("discord.typing_started", {"channel_id": str(channel_id)})
                    except Exception:
                        pass
        except Exception as e:
            try:
                from core.eventbus.bus import event_bus as _ebus_t
                _ebus_t.publish("discord.typing_error", {"channel_id": str(channel_id), "error": str(e)})
            except Exception:
                pass
        tick += 1
        await asyncio.sleep(8)


def _extract_text_deltas(frames: list[str]) -> str:
    """Træk svarteksten ud af v2-SSE-frames.

    Kun ``content_block_delta`` med ``delta.type == "text_delta"`` tælles med —
    ``thinking_delta`` (reasoning) springes over, så preview'en viser svaret og
    ikke tankerne bag det.
    """
    out: list[str] = []
    for frame in frames:
        if "content_block_delta" not in frame:
            continue
        for line in frame.split("\n"):
            if not line.startswith("data:"):
                continue
            try:
                payload = json.loads(line[5:].strip())
            except (ValueError, TypeError):  # ikke-JSON-linje i frame → spring over
                continue
            delta = payload.get("delta")
            if not isinstance(delta, dict):
                continue
            if delta.get("type") == "text_delta" and delta.get("text"):
                out.append(str(delta["text"]))
    return "".join(out)


async def _stream_run_to_discord(channel_id: int, session_id: str) -> None:
    """Send en placeholder og redigér den mens runnet streamer (message-edit).

    Live-teksten læses fra run_follow-bufferen (samme proces). Den ENDELIGE
    tekst ejes af _eventbus_subscriber_loop: streameren laver kun preview, så
    en halv formateret sluttekst aldrig står i kanalen.
    """
    if not _client:
        return
    state: dict[str, Any] = {
        "message": None,
        "accumulated": "",
        "last_edit": 0.0,
        "last_rendered": "",
        "finished": False,
        "stopped": False,
        "channel_id": int(channel_id),
    }
    with _stream_lock:
        _stream_state[session_id] = state
    try:
        from core.services.run_follow import snapshot_from

        channel = _client.get_channel(channel_id)
        if channel is None:
            channel = await _client.fetch_channel(channel_id)
        if channel is None:
            return
        state["message"] = await channel.send(_STREAM_PLACEHOLDER)
        idx = 0
        started = time.monotonic()
        while True:
            with _stream_lock:
                if state["finished"]:
                    break
            frames, done, idx = snapshot_from(session_id, idx)
            chunk = _extract_text_deltas(frames)
            if chunk:
                state["accumulated"] += chunk
            now = time.monotonic()
            acc = state["accumulated"]
            if acc:
                preview = _wrap_tables_for_discord(acc[:_STREAM_MAX_CHARS])
                preview = _downgrade_unsupported_for_discord(preview)
                # Redigér KUN når teksten faktisk har ændret sig — ellers brænder
                # vi Discords rate-limit-budget (5 edits/5 s) på ingenting.
                if preview != state["last_rendered"] and (now - state["last_edit"]) >= _STREAM_EDIT_INTERVAL_S:
                    try:
                        await state["message"].edit(content=preview)
                        state["last_rendered"] = preview
                        state["last_edit"] = now
                    except Exception:
                        logger.debug("discord stream: edit failed (rate-limit?)", exc_info=True)
            if done or (now - started) > _STREAM_MAX_S:
                break
            await asyncio.sleep(_STREAM_POLL_S)
    except Exception:
        logger.debug("discord stream: preview aborted", exc_info=True)
    finally:
        state["stopped"] = True
        # Hvis abonnenten ikke har overtaget (finished), rydder vi selv op —
        # ellers lækker state når et run dør uden completed-event.
        if not state["finished"]:
            with _stream_lock:
                _stream_state.pop(session_id, None)


async def _apply_edit_intent(item: dict) -> None:
    """Redigér streamerens placeholder til den ENDELIGE tekst.

    Kaldes fra _send_outbound_loop (asyncio-loop'en). Ingen placeholder →
    fald tilbage til normal send, så et svar aldrig tabes.
    """
    session_id = str(item.get("edit_session") or "")
    channel_id = int(item.get("channel_id") or 0)
    text = str(item.get("text") or "")
    with _stream_lock:
        st = _stream_state.pop(session_id, None)
    msg = (st or {}).get("message")
    if msg is None:
        if text:
            send_discord_message(channel_id, text)
        return
    text = _wrap_tables_for_discord(text)
    text = _downgrade_unsupported_for_discord(text)
    with _typing_lock:
        _typing_channels.discard(channel_id)
    logger.info("discord_outbound: edit final channel=%s len=%d", channel_id, len(text))
    try:
        chunks = _split_message(text, 1900)
        await msg.edit(content=chunks[0])
        for chunk in chunks[1:]:
            await msg.channel.send(chunk)
        _status["message_count"] += 1
        _status["last_message_at"] = datetime.now(UTC).isoformat()
        _persist_status()
        from core.eventbus.bus import event_bus
        event_bus.publish("discord.message_sent", {
            "channel_id": str(channel_id),
            "length": len(text),
        })
    except Exception as exc:
        logger.warning("discord_gateway: edit failed channel=%s: %s", channel_id, exc)


def _finalize_stream_or_send(session_id: str, channel_id: int, content: str) -> None:
    """Ved run-slut: redigér streamerens placeholder til den endelige tekst,
    eller send en ny besked hvis der ingen placeholder findes.

    Kaldes fra _eventbus_subscriber_loop (egen tråd). Venter kort på at
    streameren stopper, så en gammel preview ikke overskriver final-teksten.
    """
    with _stream_lock:
        st = _stream_state.get(session_id)
    if st is not None and st.get("message") is not None:
        logger.info("discord_sub: finalizing stream channel=%s len=%d", channel_id, len(content))
        st["finished"] = True
        deadline = time.monotonic() + 3.0
        while not st.get("stopped") and time.monotonic() < deadline:
            time.sleep(0.05)
        _outbound_queue.put_nowait({
            "edit_session": session_id,
            "channel_id": int(channel_id),
            "text": content,
        })
        return
    with _stream_lock:
        _stream_state.pop(session_id, None)
    logger.info("discord_sub: flushing to channel=%s len=%d", channel_id, len(content))
    send_discord_message(channel_id, content)


async def _send_outbound_loop() -> None:
    """Asyncio coroutine that drains the outbound queue and sends to Discord."""
    while _thread_running:
        try:
            item = _outbound_queue.get_nowait()
        except queue.Empty:
            await asyncio.sleep(0.2)
            continue

        # Support both old tuple format (channel_id, text) and new dict format
        if isinstance(item, tuple):
            channel_id, text = item
            file_path = None
        else:
            channel_id = item["channel_id"]
            text = item.get("text", "")
            file_path = item.get("file_path")

        # Typing-intent: tænd «skriver…» uden at sende en besked. Bruges ved
        # run-start i stedet for de gamle tekst-linjer, der fyldte kanalen.
        # Lægges i køen frem for at kalde _typing_loop direkte, fordi kaldet
        # kommer fra en anden tråd end gatewayens event-loop.
        if not isinstance(item, tuple) and item.get("typing"):
            with _typing_lock:
                if channel_id not in _typing_channels:
                    _typing_channels.add(channel_id)
                    asyncio.ensure_future(_typing_loop(channel_id))
            continue

        # Edit-intent: streameren har vist en placeholder — redigér den til den
        # ENDELIGE tekst (ejet af _eventbus_subscriber_loop) i stedet for at
        # sende en ny besked.
        if not isinstance(item, tuple) and item.get("edit_session"):
            await _apply_edit_intent(item)
            continue

        # Discord tegner ikke GFM-tabeller — pak dem i kode-fences. Kun
        # Discord; normalizeren og desk/webchat er urørt.
        if text:
            text = _wrap_tables_for_discord(text)
            text = _downgrade_unsupported_for_discord(text)

        # Stop typing indicator before sending
        with _typing_lock:
            _typing_channels.discard(channel_id)
        logger.info("discord_outbound: dequeued channel=%s len=%d file=%s", channel_id, len(text), file_path)
        try:
            if _client:
                channel = _client.get_channel(channel_id)
                logger.info("discord_outbound: get_channel=%s", channel)
                if channel is None:
                    channel = await _client.fetch_channel(channel_id)
                    logger.info("discord_outbound: fetch_channel=%s", channel)
                if file_path:
                    import discord as _discord_lib
                    await channel.send(
                        content=text or None,
                        file=_discord_lib.File(file_path),
                    )
                else:
                    for chunk in _split_message(text, 1900):
                        await channel.send(chunk)
                logger.info("discord_outbound: sent ok to channel=%s", channel_id)
                _status["message_count"] += 1
                _status["last_message_at"] = datetime.now(UTC).isoformat()
                _persist_status()
                from core.eventbus.bus import event_bus
                event_bus.publish("discord.message_sent", {
                    "channel_id": str(channel_id),
                    "length": len(text),
                })
            else:
                logger.warning("discord_outbound: _client is None, dropping message")
        except Exception as exc:
            logger.warning("discord_gateway: failed to send to channel %s: %s", channel_id, exc)


async def _run_client(config: dict) -> None:
    """Main coroutine: set up discord client and run until stopped."""
    import discord

    global _client

    intents = discord.Intents.all()

    _client = discord.Client(intents=intents)
    bot_token = config["bot_token"]
    guild_id = int(config["guild_id"])
    allowed_channel_ids = {int(c) for c in config.get("allowed_channel_ids", [])}
    owner_discord_id = str(config["owner_discord_id"])

    @_client.event
    async def on_ready() -> None:
        _status["connected"] = True
        _status["connect_error"] = None
        guild = _client.get_guild(guild_id)
        _status["guild_name"] = guild.name if guild else str(guild_id)
        _persist_status()
        logger.info(
            "discord_gateway: connected as %s to guild %s",
            _client.user,
            _status["guild_name"],
        )
        from core.eventbus.bus import event_bus
        event_bus.publish("discord.connected", {
            "guild_id": str(guild_id),
            "guild_name": _status["guild_name"],
        })

    @_client.event
    async def on_message(message: Any) -> None:
        try:
            from core.eventbus.bus import event_bus as _ebus
            _ebus.publish("discord.message_any", {
                "author": str(getattr(message.author, "id", "?")),
                "channel": str(getattr(message.channel, "id", "?")),
            })
        except Exception:
            pass
        try:
            import discord as _discord
            # Ignore our own messages
            if message.author == _client.user:
                return
            # Deduplicate by Discord message ID (guards against reconnect re-delivery)
            msg_id = str(getattr(message, "id", "") or "")
            if msg_id:
                with _seen_message_ids_lock:
                    if msg_id in _seen_message_ids:
                        logger.info("discord on_message: skipping duplicate message_id=%s", msg_id)
                        return
                    _seen_message_ids.add(msg_id)
                    # Trim set to avoid unbounded growth
                    if len(_seen_message_ids) > _SEEN_MESSAGE_IDS_MAX:
                        _seen_message_ids.discard(next(iter(_seen_message_ids)))
            # Determine channel type
            is_dm = isinstance(message.channel, _discord.DMChannel)
            ch_id = getattr(message.channel, "id", "?")
            guild_id_actual = getattr(getattr(message, "guild", None), "id", None)
            content_raw = message.content or ""
            # Diagnostic event — shows every check value
            try:
                from core.eventbus.bus import event_bus as _ebus2
                _ebus2.publish("discord.debug_check", {
                    "author": str(getattr(message.author, "id", "?")),
                    "is_dm": is_dm,
                    "guild_actual": str(guild_id_actual),
                    "guild_expected": str(guild_id),
                    "channel": str(ch_id),
                    "channel_allowed": str(ch_id in allowed_channel_ids) if not is_dm else "n/a",
                    "owner_match": str(message.author.id) == owner_discord_id,
                    "content_len": len(content_raw),
                    "owner_discord_id": owner_discord_id,
                })
            except Exception:
                pass
            # For guild messages: only respond in allowed channels
            if not is_dm:
                if message.guild is None or message.guild.id != guild_id:
                    return
                if message.channel.id not in allowed_channel_ids:
                    return
                # Don't barge in when the user is talking to a different bot.
                # If the message @-mentions another bot AND not us, the human
                # is addressing them — stay out. Mentioning no bots OR us
                # explicitly OR a mix that includes us → we participate.
                try:
                    mentioned = list(message.mentions or [])
                    other_bots_mentioned = [
                        u for u in mentioned
                        if getattr(u, "bot", False) and u.id != _client.user.id
                    ]
                    we_are_mentioned = _client.user in mentioned
                    if other_bots_mentioned and not we_are_mentioned:
                        logger.info(
                            "discord on_message: skipping — another bot mentioned (%s) not us",
                            ",".join(str(u) for u in other_bots_mentioned),
                        )
                        return
                except Exception:
                    pass
            # User resolution — lookup in users.json (multi-user support).
            # Owner via owner_discord_id is always allowed. Other registered
            # users (role=member) are allowed in DM. Unknown users: accepted
            # only in public channels (routed to shared 'public' workspace),
            # never in DM.
            author_id_str = str(message.author.id)
            is_owner_id_match = author_id_str == owner_discord_id

            try:
                from core.identity.users import find_user_by_discord_id
                registered_user = find_user_by_discord_id(author_id_str)
            except Exception:
                registered_user = None

            # DM policy: owner + any registered member allowed; unknown rejected
            if is_dm and not is_owner_id_match and registered_user is None:
                return

            is_owner = is_owner_id_match or (
                registered_user is not None and registered_user.role == "owner"
            )

            # Rate limit non-owner users
            if not is_owner:
                now = time.monotonic()
                last = _user_last_response.get(message.author.id, 0.0)
                if now - last < _RATE_LIMIT_SECONDS:
                    return
                _user_last_response[message.author.id] = now

            # Extract file attachments and build content prefix
            attachment_prefix = ""
            try:
                if message.attachments:
                    _att_session = _get_or_create_discord_session(
                        message.channel.id, is_dm, owner_discord_id, author_id=author_id_str,
                    )
                    attachment_prefix = _build_attachment_prefix(
                        list(message.attachments), session_id=_att_session
                    )
            except Exception as _att_exc:
                logger.warning("discord on_message: attachment handling failed: %s", _att_exc)

            content = (attachment_prefix + content_raw).strip()
            if not content:
                try:
                    from core.eventbus.bus import event_bus as _ebus3
                    _ebus3.publish("discord.debug_empty_content", {
                        "author": str(getattr(message.author, "id", "?")),
                        "channel": str(ch_id),
                        "is_dm": is_dm,
                    })
                except Exception:
                    pass
                return

            channel_id = message.channel.id
            logger.info("discord on_message: handling message from %s (owner=%s) in channel %s", message.author.id, is_owner, channel_id)
            session_id = _get_or_create_discord_session(
                channel_id, is_dm, owner_discord_id, author_id=author_id_str,
            )

            # Register this session so the eventbus listener knows to route responses here
            with _discord_sessions_lock:
                _discord_sessions[session_id] = channel_id

            # Owner-override (§6.3): `!override <kode>` / `!revoke-override`.
            # Verificeres mod owners TOTP-seed; aktiverer owner-kontrol for DENNE
            # session uden normal beskedhåndtering. Thin wire — logikken er ren i
            # override_command. Best-effort: fejl må aldrig spærre normal chat.
            try:
                from core.services.override_command import handle_override_command
                from core.identity.users import get_owner, get_totp_seed
                _owner = get_owner()
                _seed = get_totp_seed(discord_id=_owner.discord_id) if _owner else ""
                _ov = handle_override_command(content_raw, session_id=session_id, owner_seed=_seed)
                if _ov is not None:
                    send_discord_message(channel_id, str(_ov.get("reply") or ""))
                    return
            except Exception:
                logger.exception("discord on_message: override-handler fejlede")

            # Resolve workspace + display BEFORE persisting so the inbound
            # user message gets stamped with the correct user_id and workspace
            # (otherwise the worker thread sets context too late, the row gets
            # empty user_id, and the model can't tell speakers apart).
            # Rolle bindes EKSPLICIT (sikkerhed): uden dette var alle discord-
            # brugere unbound→owner. Owner→owner; registreret bruger→sin rolle;
            # ukendt (offentlig kanal)→guest (mest restriktiv). Override kan
            # elevere en member-session via effective_role (§6.0).
            if is_owner_id_match:
                user_role = "owner"
            elif registered_user is not None:
                user_role = str(getattr(registered_user, "role", "member") or "member").lower()
            else:
                user_role = "guest"

            if registered_user is not None:
                workspace_name = registered_user.workspace
                user_display = registered_user.name
            elif is_owner_id_match:
                # Owner is not in users.json (unlikely but defensive). Look up
                # the owner record to get the correct workspace; fall back to
                # "bjorn" rather than "default" so we never recreate the old
                # workspaces/default/ directory.
                try:
                    from core.identity.users import get_owner
                    _owner = get_owner()
                    workspace_name = _owner.workspace if _owner else "bjorn"
                    user_display = _owner.name if _owner else "Bjørn"
                except Exception:
                    workspace_name = "bjorn"
                    user_display = "Bjørn"
            else:
                workspace_name = "public"
                user_display = str(getattr(message.author, "name", author_id_str))

            # Persist user message with explicit speaker identity
            from core.services.chat_sessions import append_chat_message
            _user_msg = append_chat_message(
                session_id=session_id,
                role="user",
                content=content,
                user_id=author_id_str,
                workspace_name=workspace_name,
            )

            # Spor B (16. jun): annoncér brugerbeskeden som channel.chat_message_appended,
            # så session_inbox ser Discord-sessionen som AKTIV (ellers springer daemon-
            # notifikationer køen over og afbryder midt i et run) + så de kognitive pollere
            # (theory_of_mind/metacognition/affect) ser Discord-brugerne. Echo-subscriber'en
            # springer den over (source != visible-run, role != assistant).
            _announce_user_message_appended(session_id, _user_msg)

            # Publish received event
            from core.eventbus.bus import event_bus
            event_bus.publish("discord.message_received", {
                "channel_id": str(channel_id),
                "user_id": str(message.author.id),
                "is_owner": is_owner,
                "is_dm": is_dm,
            })

            # Start typing indicator
            with _typing_lock:
                _typing_channels.add(channel_id)
            asyncio.ensure_future(_typing_loop(channel_id))

            # workspace_name + user_display already resolved above before persist

            # Trigger autonomous run with workspace context bound
            def _run_in_context(
                _content: str, _session_id: str, _user_id: str,
                _workspace: str, _display: str, _role: str,
            ) -> None:
                from core.identity.workspace_context import set_context, reset_context
                from core.services.visible_runs import start_autonomous_run
                token = set_context(
                    workspace_name=_workspace,
                    user_id=_user_id,
                    user_display_name=_display,
                    role=_role,
                    session_id=_session_id,  # → effective_role kan slå override op
                )
                try:
                    start_autonomous_run(_content, session_id=_session_id, follow=True)
                finally:
                    reset_context(token)

            threading.Thread(
                target=_run_in_context,
                args=(content, session_id, author_id_str, workspace_name, user_display, user_role),
                daemon=True,
                name=f"discord-run-{session_id[-8:]}",
            ).start()
            # Streaming (message-edit): follow=True tee'er runnets v2-frames til
            # run_follow-bufferen; streameren læser dem og redigerer placeholder'en
            # mens svaret vokser — i stedet for tre prikker og ingenting.
            try:
                asyncio.ensure_future(_stream_run_to_discord(channel_id, session_id))
            except Exception:
                logger.debug("discord on_message: stream start failed", exc_info=True)
            logger.info(
                "discord on_message: run started session=%s user=%s workspace=%s",
                session_id, user_display, workspace_name,
            )
        except Exception as exc:
            logger.error("discord on_message: unhandled error: %s", exc, exc_info=True)
            try:
                import traceback
                from core.eventbus.bus import event_bus as _ebus_err
                _ebus_err.publish("discord.error", {
                    "error": str(exc),
                    "traceback": traceback.format_exc()[-500:],
                })
            except Exception:
                pass

    # Run outbound loop alongside the client. HOLD en stærk modul-reference (6. jul): uden
    # den kan Python GC'e den ventende task → "Task was destroyed but it is pending" (fyrede
    # 20×/dag). Cancel en evt. tidligere loop (reconnect kalder _run_client igen) så vi ikke
    # ophober forældreløse outbound-loops.
    global _outbound_task
    if _outbound_task is not None and not _outbound_task.done():
        _outbound_task.cancel()
    _outbound_task = asyncio.ensure_future(_send_outbound_loop())
    try:
        await _client.start(bot_token)
    except Exception as exc:
        _status["connected"] = False
        _status["connect_error"] = str(exc)
        _persist_status()
        logger.error("discord_gateway: client error: %s", exc)


def _discord_thread_func(config: dict) -> None:
    """Entry point for the daemon thread."""
    global _loop, _thread_running
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _thread_running = True
    try:
        _loop.run_until_complete(_run_client(config))
    except Exception as exc:
        logger.error("discord_gateway: thread error: %s", exc)
    finally:
        _thread_running = False
        _status["connected"] = False
        _persist_status()
        _loop.close()
        _loop = None


def _announce_user_message_appended(session_id: str, message: dict) -> None:
    """Udsend channel.chat_message_appended for en Discord-brugerbesked (Spor B).

    session_inbox.is_session_active() + de kognitive pollere (theory_of_mind/
    metacognition/affect_modulation) læser denne event fra events-tabellen. Discord
    udsendte den aldrig for brugerbeskeder → sessionen så inaktiv ud → daemon-
    notifikationer sprang køen over og afbrød midt i runs. Samme form som visible_runs;
    source="discord-gateway" + role="user" gør at den udgående echo-subscriber
    (kræver source=visible-run, role=assistant) springer den over. Fail-soft."""
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("channel.chat_message_appended", {
            "session_id": session_id,
            "message": message,
            "source": "discord-gateway",
        })
    except Exception:
        pass


def _eventbus_subscriber_loop() -> None:
    """Background thread: watch eventbus for assistant responses in Discord sessions.

    Buffers the latest assistant message per session and only delivers it when
    the run is fully complete (memory.visible_run_postprocess_completed). This
    prevents intermediate agentic-loop messages (between tool calls) from being
    sent as separate Discord messages.
    """
    from core.eventbus.bus import event_bus
    sub = event_bus.subscribe()
    # session_id → (channel_id, content) — latest buffered assistant message
    _pending: dict[str, tuple[int, str]] = {}
    try:
        while _sub_running:
            try:
                item = sub.get(timeout=1.0)
            except queue.Empty:
                continue
            if item is None:
                break
            if not isinstance(item, dict):
                continue
            kind = item.get("kind", "")
            payload = item.get("payload") or {}

            # Buffer latest assistant message from visible runs
            if kind == "channel.chat_message_appended":
                session_id = str(payload.get("session_id") or "")
                with _discord_sessions_lock:
                    channel_id = _discord_sessions.get(session_id)
                if channel_id is None:
                    continue
                source = str(payload.get("source") or "")
                if source and source != "visible-run":
                    continue
                msg = payload.get("message") or {}
                if str(msg.get("role") or "") != "assistant":
                    continue
                content = str(msg.get("content") or "").strip()
                if content:
                    logger.info("discord_sub: buffering reply session=%s channel=%s len=%d", session_id[:12], channel_id, len(content))
                    _pending[session_id] = (channel_id, content)

            # Flush buffer when run is fully complete (before memory postprocess)
            elif kind in (
                "runtime.autonomous_run_completed",
                "runtime.autonomous_run_interrupted",
                "memory.visible_run_postprocess_completed",
            ):
                session_id = str(payload.get("session_id") or "")
                pending = _pending.pop(session_id, None)
                if pending:
                    channel_id, content = pending
                    _finalize_stream_or_send(session_id, int(channel_id), content)
                else:
                    logger.debug("discord_sub: %s sid=%s — no pending", kind.split(".")[-1], session_id[:12])

            # 2026-05-22 (Claude): silent-run detection — run completed
            # with tool-calls but no visible text. Without this, Bjørn
            # sees "Jarvis is typing..." that never finishes. Emit a
            # status message so he knows what happened.
            elif kind == "runtime.run_ended_silent":
                session_id = str(payload.get("session_id") or "")
                run_id = str(payload.get("run_id") or "")
                unique_tools = list(payload.get("unique_tools") or [])
                tool_count = int(payload.get("tool_call_count") or 0)
                # Look up the channel via in-flight registry, falling
                # back to the owner DM if we can't resolve.
                channel_id = _resolve_channel_for_session(session_id)
                if channel_id and unique_tools:
                    summary = (
                        f"_(auto-status fra run-closure-gate)_\n"
                        f"Jeg afsluttede en agentic run uden at returnere tekst. "
                        f"Tools brugt: **{', '.join(unique_tools[:6])}** "
                        f"({tool_count} total). Run-id `{run_id[:12]}`.\n"
                        f"Hvis du venter på et svar — sig til hvad du så efter."
                    )
                    try:
                        send_discord_message(channel_id, summary)
                        logger.info(
                            "discord_sub: silent-run auto-status sent to channel=%s run=%s",
                            channel_id, run_id[:12],
                        )
                    except Exception:
                        logger.debug("discord_sub: silent-run send failed", exc_info=True)

            # 2026-05-22 (Claude): unstaged-changes notification —
            # Bjørn was hitting "Jarvis edited code but didn't commit" pattern
            # repeatedly. Surface it explicitly so he knows there's a working-tree
            # diff sitting after the run.
            elif kind == "runtime.run_left_unstaged_changes":
                session_id = str(payload.get("session_id") or "")
                run_id = str(payload.get("run_id") or "")
                summary = dict(payload.get("summary") or {})
                paths = list(summary.get("paths") or [])
                count = int(summary.get("count") or 0)
                truncated = bool(summary.get("truncated"))
                channel_id = _resolve_channel_for_session(session_id)
                if channel_id and paths:
                    listing = "\n".join(f"  • `{p}`" for p in paths)
                    more = f"\n  …og {count - len(paths)} mere" if truncated else ""
                    notice = (
                        f"⚠️ _(run-closure-gate)_ Run `{run_id[:12]}` efterlod **{count} "
                        f"uncommitted ændring(er)** i working tree:\n"
                        f"{listing}{more}\n"
                        f"Husk at committe — eller bed mig om det."
                    )
                    try:
                        send_discord_message(channel_id, notice)
                        logger.info(
                            "discord_sub: unstaged-changes notice sent to channel=%s run=%s count=%d",
                            channel_id, run_id[:12], count,
                        )
                    except Exception:
                        logger.debug("discord_sub: unstaged-changes send failed", exc_info=True)

    finally:
        logger.warning("discord_sub: subscriber loop exited")
        event_bus.unsubscribe(sub)


def _resolve_channel_for_session(session_id: str) -> str | None:
    """Look up the Discord channel that originated a given session.

    The in-flight registry tracks which channel a session was bound to.
    Falls back to the owner-DM channel if specific lookup fails — that
    matches the existing send_discord_dm tool's behaviour (everything
    routes to Bjørn anyway, see MEMORY.md "Discord DM — known limits").
    """
    try:
        from core.runtime.db import connect
        with connect() as conn:
            row = conn.execute(
                "SELECT channel_id FROM chat_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row and row[0]:
            return str(row[0])
    except Exception:
        pass
    # Fallback to owner DM — Bjørn's channel from MEMORY.md
    return "1474048593219555461"


def start_discord_gateway() -> None:
    """Start gateway if config exists. Safe to call unconditionally."""
    global _thread, _sub_thread, _sub_running, _hb_thread, _hb_running

    from core.services.discord_config import load_discord_config
    config = load_discord_config()
    if not config or not config.get("enabled", True):
        logger.info("discord_gateway: not configured, skipping")
        return

    if (_thread and _thread.is_alive()) or (_sub_thread and _sub_thread.is_alive()):
        logger.info("discord_gateway: already running")
        return

    # Start eventbus subscriber thread
    _sub_running = True
    _sub_thread = threading.Thread(
        target=_eventbus_subscriber_loop,
        daemon=True,
        name="discord-sub",
    )
    _sub_thread.start()

    # Start discord client thread
    _thread = threading.Thread(
        target=_discord_thread_func,
        args=(config,),
        daemon=True,
        name="discord-gateway",
    )
    _thread.start()

    # Start status heartbeat so other processes can see liveness
    _hb_running = True
    _hb_thread = threading.Thread(
        target=_status_heartbeat_loop,
        daemon=True,
        name="discord-status-hb",
    )
    _hb_thread.start()

    logger.info("discord_gateway: started")


def stop_discord_gateway() -> None:
    """Stop the gateway gracefully."""
    global _sub_running, _thread_running, _hb_running
    _sub_running = False
    _thread_running = False
    _hb_running = False
    if _loop and _client:
        try:
            asyncio.run_coroutine_threadsafe(_client.close(), _loop)
        except Exception:
            pass
    _status["connected"] = False
    _persist_status()
    logger.info("discord_gateway: stopped")
