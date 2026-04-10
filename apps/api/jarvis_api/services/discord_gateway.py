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

logger = logging.getLogger(__name__)

# ── State ──────────────────────────────────────────────────────────────

_client: Any = None          # discord.Client instance
_loop: asyncio.AbstractEventLoop | None = None
_thread: threading.Thread | None = None
_thread_running: bool = False

_outbound_queue: queue.Queue = queue.Queue()  # (channel_id: int, text: str)

# Sessions owned by Discord: {session_id → discord_channel_id}
_discord_sessions: dict[str, int] = {}
_discord_sessions_lock = threading.Lock()

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


def _get_or_create_discord_session(channel_id: int, is_dm: bool, owner_discord_id: str) -> str:
    """Return session_id for this Discord channel. Creates session if needed."""
    from apps.api.jarvis_api.services.chat_sessions import (
        create_chat_session,
        get_chat_session,
        list_chat_sessions,
    )
    from apps.api.jarvis_api.services.notification_bridge import get_pinned_session_id

    if is_dm:
        # DM: use the currently pinned webchat session, or fall back to discord-owner
        pinned = get_pinned_session_id()
        if pinned and get_chat_session(pinned):
            return pinned
        # Look for existing Discord DM session
        for s in list_chat_sessions():
            if s.get("title") == "Discord DM":
                return str(s["session_id"])
        return str(create_chat_session(title="Discord DM")["session_id"])
    else:
        # Public channel: one session per channel
        target_title = f"Discord #{channel_id}"
        for s in list_chat_sessions():
            if s.get("title") == target_title:
                return str(s["session_id"])
        return str(create_chat_session(title=target_title)["session_id"])


def _split_message(text: str, limit: int) -> list[str]:
    """Split text into chunks of at most `limit` characters."""
    if len(text) <= limit:
        return [text]
    chunks = []
    while text:
        chunks.append(text[:limit])
        text = text[limit:]
    return chunks


async def _send_outbound_loop() -> None:
    """Asyncio coroutine that drains the outbound queue and sends to Discord."""
    while _thread_running:
        try:
            channel_id, text = _outbound_queue.get_nowait()
        except queue.Empty:
            await asyncio.sleep(0.2)
            continue
        try:
            if _client:
                channel = _client.get_channel(channel_id)
                if channel is None:
                    channel = await _client.fetch_channel(channel_id)
                for chunk in _split_message(text, 1900):
                    await channel.send(chunk)
                _status["message_count"] += 1
                _status["last_message_at"] = datetime.now(UTC).isoformat()
                from core.eventbus.bus import event_bus
                event_bus.publish("discord.message_sent", {
                    "channel_id": str(channel_id),
                    "length": len(text),
                })
        except Exception as exc:
            logger.warning("discord_gateway: failed to send to channel %s: %s", channel_id, exc)


async def _run_client(config: dict) -> None:
    """Main coroutine: set up discord client and run until stopped."""
    import discord

    global _client

    intents = discord.Intents.default()
    intents.message_content = True
    intents.dm_messages = True

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
            import discord as _discord
            # Ignore our own messages
            if message.author == _client.user:
                return
            # Determine channel type
            is_dm = isinstance(message.channel, _discord.DMChannel)
            ch_id_log = getattr(message.channel, "id", "?")
            guild_id_log = getattr(getattr(message, "guild", None), "id", "DM")
            logger.debug(
                "discord on_message: author=%s is_dm=%s guild=%s channel=%s content=%r",
                message.author.id, is_dm, guild_id_log, ch_id_log, (message.content or "")[:60],
            )
            # For guild messages: only respond in allowed channels
            if not is_dm:
                if message.guild is None or message.guild.id != guild_id:
                    logger.debug("discord on_message: guild mismatch (%s != %s), ignoring", guild_id_log, guild_id)
                    return
                if message.channel.id not in allowed_channel_ids:
                    logger.debug("discord on_message: channel %s not in allowed %s, ignoring", ch_id_log, allowed_channel_ids)
                    return
            # DM: only accept from owner
            if is_dm and str(message.author.id) != owner_discord_id:
                logger.debug("discord on_message: DM from non-owner %s, ignoring", message.author.id)
                return

            is_owner = str(message.author.id) == owner_discord_id

            # Rate limit non-owner users
            if not is_owner:
                now = time.monotonic()
                last = _user_last_response.get(message.author.id, 0.0)
                if now - last < _RATE_LIMIT_SECONDS:
                    logger.debug("discord on_message: rate-limiting user %s", message.author.id)
                    return
                _user_last_response[message.author.id] = now

            content = message.content.strip()
            if not content:
                logger.debug("discord on_message: empty content, ignoring")
                return

            channel_id = message.channel.id
            logger.info("discord on_message: handling message from %s (owner=%s) in channel %s", message.author.id, is_owner, channel_id)
            session_id = _get_or_create_discord_session(channel_id, is_dm, owner_discord_id)

            # Register this session so the eventbus listener knows to route responses here
            with _discord_sessions_lock:
                _discord_sessions[session_id] = channel_id

            # Persist user message
            from apps.api.jarvis_api.services.chat_sessions import append_chat_message
            append_chat_message(session_id=session_id, role="user", content=content)

            # Publish received event
            from core.eventbus.bus import event_bus
            event_bus.publish("discord.message_received", {
                "channel_id": str(channel_id),
                "user_id": str(message.author.id),
                "is_owner": is_owner,
                "is_dm": is_dm,
            })

            # Trigger autonomous run (fire-and-forget in its own thread)
            from apps.api.jarvis_api.services.visible_runs import start_autonomous_run
            threading.Thread(
                target=start_autonomous_run,
                args=(content,),
                kwargs={"session_id": session_id},
                daemon=True,
                name=f"discord-run-{session_id[-8:]}",
            ).start()
            logger.info("discord on_message: autonomous run started for session %s", session_id)
        except Exception as exc:
            logger.error("discord on_message: unhandled error: %s", exc, exc_info=True)

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
    """Background thread: watch eventbus for assistant responses in Discord sessions."""
    from core.eventbus.bus import event_bus
    sub = event_bus.subscribe()
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
            if kind != "channel.chat_message_appended":
                continue
            payload = item.get("payload") or {}
            session_id = str(payload.get("session_id") or "")
            with _discord_sessions_lock:
                channel_id = _discord_sessions.get(session_id)
            if channel_id is None:
                continue
            msg = payload.get("message") or {}
            role = str(msg.get("role") or "")
            if role != "assistant":
                continue
            content = str(msg.get("content") or "").strip()
            if not content:
                continue
            send_discord_message(channel_id, content)
    finally:
        event_bus.unsubscribe(sub)


def start_discord_gateway() -> None:
    """Start gateway if config exists. Safe to call unconditionally."""
    global _thread, _sub_thread, _sub_running

    from apps.api.jarvis_api.services.discord_config import load_discord_config
    config = load_discord_config()
    if not config or not config.get("enabled", True):
        logger.info("discord_gateway: not configured, skipping")
        return

    if _thread and _thread.is_alive():
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
