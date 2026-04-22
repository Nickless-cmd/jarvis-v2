"""Discord gateway — runs discord.py in a dedicated daemon thread.

Completely isolated from FastAPI's asyncio loop. Inbound messages trigger
start_autonomous_run() which writes the response to the session; an eventbus
subscriber picks up channel.chat_message_appended events for Discord sessions
and routes them back to Discord.
"""
from __future__ import annotations

import asyncio
import logging
import queue
import threading
import time
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("uvicorn.error")

# ── State ──────────────────────────────────────────────────────────────

_client: Any = None          # discord.Client instance
_loop: asyncio.AbstractEventLoop | None = None
_thread: threading.Thread | None = None
_thread_running: bool = False

_outbound_queue: queue.Queue = queue.Queue()  # (channel_id: int, text: str)

# Sessions owned by Discord: {session_id → discord_channel_id}
_discord_sessions: dict[str, int] = {}
_discord_sessions_lock = threading.Lock()

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


def get_discord_status() -> dict[str, Any]:
    """Return current gateway status."""
    return {
        "connected": _status["connected"],
        "guild_name": _status["guild_name"],
        "last_message_at": _status["last_message_at"],
        "message_count": _status["message_count"],
        "connect_error": _status["connect_error"],
        "active_discord_sessions": len(_discord_sessions),
    }


def send_discord_message(channel_id: int, text: str) -> None:
    """Thread-safe: queue a message to be sent to a Discord channel."""
    _outbound_queue.put_nowait((channel_id, text))


def send_dm_to_owner(text: str, timeout: float = 10.0) -> dict[str, object]:
    """Send a DM directly to the owner via owner_discord_id.

    Does not require an active session — opens the DM channel if needed.
    Returns {"status": "sent"} or {"status": "error", "reason": str}.
    """
    if not _status["connected"] or _client is None or _loop is None:
        return {"status": "error", "reason": "discord-not-connected"}

    from core.services.discord_config import load_discord_config
    cfg = load_discord_config()
    if not cfg:
        return {"status": "error", "reason": "discord-not-configured"}

    owner_id = int(cfg["owner_discord_id"])

    async def _open_and_queue() -> int:
        user = await _client.fetch_user(owner_id)
        dm_channel = await user.create_dm()
        return dm_channel.id

    try:
        future = asyncio.run_coroutine_threadsafe(_open_and_queue(), _loop)
        channel_id = future.result(timeout=timeout)
        send_discord_message(channel_id, text)
        return {"status": "sent", "channel_id": channel_id}
    except Exception as exc:
        return {"status": "error", "reason": str(exc)}


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


def _split_message(text: str, limit: int) -> list[str]:
    """Split text into chunks of at most `limit` characters."""
    if len(text) <= limit:
        return [text]
    chunks = []
    while text:
        chunks.append(text[:limit])
        text = text[limit:]
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


async def _send_outbound_loop() -> None:
    """Asyncio coroutine that drains the outbound queue and sends to Discord."""
    while _thread_running:
        try:
            channel_id, text = _outbound_queue.get_nowait()
        except queue.Empty:
            await asyncio.sleep(0.2)
            continue
        # Stop typing indicator before sending
        with _typing_lock:
            _typing_channels.discard(channel_id)
        logger.info("discord_outbound: dequeued channel=%s len=%d", channel_id, len(text))
        try:
            if _client:
                channel = _client.get_channel(channel_id)
                logger.info("discord_outbound: get_channel=%s", channel)
                if channel is None:
                    channel = await _client.fetch_channel(channel_id)
                    logger.info("discord_outbound: fetch_channel=%s", channel)
                for chunk in _split_message(text, 1900):
                    await channel.send(chunk)
                logger.info("discord_outbound: sent ok to channel=%s", channel_id)
                _status["message_count"] += 1
                _status["last_message_at"] = datetime.now(UTC).isoformat()
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

            content = content_raw.strip()
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

            # Persist user message
            from core.services.chat_sessions import append_chat_message
            append_chat_message(session_id=session_id, role="user", content=content)

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

            # Resolve workspace binding based on user lookup
            if registered_user is not None:
                workspace_name = registered_user.workspace
                user_display = registered_user.name
            elif is_owner_id_match:
                # Owner known via owner_discord_id but not in users.json yet
                # (bootstrap case) — use 'default' workspace
                workspace_name = "default"
                user_display = "Bjørn"
            else:
                # Public channel with unregistered user → shared public workspace
                workspace_name = "public"
                user_display = str(getattr(message.author, "name", author_id_str))

            # Trigger autonomous run with workspace context bound
            def _run_in_context(
                _content: str, _session_id: str, _user_id: str,
                _workspace: str, _display: str,
            ) -> None:
                from core.identity.workspace_context import set_context, reset_context
                from core.services.visible_runs import start_autonomous_run
                token = set_context(
                    workspace_name=_workspace,
                    user_id=_user_id,
                    user_display_name=_display,
                )
                try:
                    start_autonomous_run(_content, session_id=_session_id)
                finally:
                    reset_context(token)

            threading.Thread(
                target=_run_in_context,
                args=(content, session_id, author_id_str, workspace_name, user_display),
                daemon=True,
                name=f"discord-run-{session_id[-8:]}",
            ).start()
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

    # Run outbound loop alongside the client
    asyncio.ensure_future(_send_outbound_loop())
    try:
        await _client.start(bot_token)
    except Exception as exc:
        _status["connected"] = False
        _status["connect_error"] = str(exc)
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
        _loop.close()
        _loop = None


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
            elif kind in ("runtime.autonomous_run_completed", "memory.visible_run_postprocess_completed"):
                session_id = str(payload.get("session_id") or "")
                pending = _pending.pop(session_id, None)
                if pending:
                    channel_id, content = pending
                    logger.info("discord_sub: flushing to channel=%s len=%d (trigger=%s)", channel_id, len(content), kind)
                    send_discord_message(channel_id, content)
                else:
                    logger.debug("discord_sub: %s sid=%s — no pending", kind.split(".")[-1], session_id[:12])

    finally:
        logger.warning("discord_sub: subscriber loop exited")
        event_bus.unsubscribe(sub)


def start_discord_gateway() -> None:
    """Start gateway if config exists. Safe to call unconditionally."""
    global _thread, _sub_thread, _sub_running

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
    logger.info("discord_gateway: started")


def stop_discord_gateway() -> None:
    """Stop the gateway gracefully."""
    global _sub_running, _thread_running
    _sub_running = False
    _thread_running = False
    if _loop and _client:
        try:
            asyncio.run_coroutine_threadsafe(_client.close(), _loop)
        except Exception:
            pass
    logger.info("discord_gateway: stopped")
