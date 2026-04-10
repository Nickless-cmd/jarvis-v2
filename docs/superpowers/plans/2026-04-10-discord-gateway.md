# Discord Gateway — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Jarvis a Discord presence — he can receive and respond to messages, reach out proactively, and is aware of the connection state, all integrated into his self-model.

**Architecture:** Discord runs in a dedicated daemon thread with its own asyncio event loop (completely isolated from FastAPI). Inbound messages trigger `start_autonomous_run()` in a background thread; responses flow back via the eventbus (`channel.chat_message_appended`). Outbound is driven by `asyncio.run_coroutine_threadsafe()` from a queue-based dispatcher.

**Tech Stack:** `discord.py 2.6.4` (already installed in conda `ai` env), existing `core/eventbus/bus.py`, `apps/api/jarvis_api/services/visible_runs.py` (`start_autonomous_run`), `apps/api/jarvis_api/services/chat_sessions.py`.

---

## Files

| File | Action | Responsibility |
|------|--------|----------------|
| `apps/api/jarvis_api/services/discord_config.py` | Create | Load/save `~/.jarvis-v2/config/discord.json` |
| `apps/api/jarvis_api/services/discord_gateway.py` | Create | Discord client, thread, in/outbound, eventbus integration |
| `core/eventbus/events.py` | Modify | Add `"discord"` to `ALLOWED_EVENT_FAMILIES` |
| `apps/api/jarvis_api/services/notification_bridge.py` | Modify | Add `get_pinned_session_id()` helper |
| `core/tools/simple_tools.py` | Modify | Extend `notify_user`, add `discord_status` tool + handler, extend `read_self_state` |
| `apps/api/jarvis_api/app.py` | Modify | Start/stop gateway in lifespan |
| `scripts/jarvis.py` | Modify | Add `discord-setup` and `discord-status` CLI subcommands |

---

### Task 1: `discord_config.py`

**Files:**
- Create: `apps/api/jarvis_api/services/discord_config.py`

- [ ] **Step 1: Write the full file**

```python
"""Discord config — load/save ~/.jarvis-v2/config/discord.json."""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from core.runtime.config import JARVIS_HOME

_CONFIG_PATH = Path(JARVIS_HOME) / "config" / "discord.json"

_REQUIRED_KEYS = {"bot_token", "guild_id", "allowed_channel_ids", "owner_discord_id"}


def load_discord_config() -> dict | None:
    """Return config dict or None if missing/invalid."""
    try:
        if not _CONFIG_PATH.exists():
            return None
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        if not _REQUIRED_KEYS.issubset(data):
            return None
        return data
    except Exception:
        return None


def save_discord_config(config: dict) -> None:
    """Write config with chmod 600. Creates parent dir if needed."""
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    os.chmod(_CONFIG_PATH, stat.S_IRUSR | stat.S_IWUSR)


def is_discord_configured() -> bool:
    """Return True if config exists and has all required keys."""
    return load_discord_config() is not None
```

- [ ] **Step 2: Verify syntax**

```bash
conda run -n ai python -m compileall apps/api/jarvis_api/services/discord_config.py -q
```
Expected: no output

- [ ] **Step 3: Smoke test**

```bash
conda run -n ai python -c "
import sys; sys.path.insert(0, '.')
from apps.api.jarvis_api.services.discord_config import is_discord_configured, load_discord_config
print('configured:', is_discord_configured())
print('config:', load_discord_config())
"
```
Expected: `configured: False`, `config: None`

- [ ] **Step 4: Commit**

```bash
git add apps/api/jarvis_api/services/discord_config.py
git commit -m "feat: discord_config — load/save ~/.jarvis-v2/config/discord.json"
```

---

### Task 2: Register `discord` event family

**Files:**
- Modify: `core/eventbus/events.py`

The eventbus rejects events with unregistered families. Add `"discord"` so the gateway can publish `discord.connected`, `discord.disconnected`, `discord.message_received`, `discord.message_sent`.

- [ ] **Step 1: Add `"discord"` to `ALLOWED_EVENT_FAMILIES`**

In `core/eventbus/events.py`, find the line `"cognitive_state",` (near line 96) and add `"discord"` after it:

```python
    "cognitive_state",
    "cognitive_user_emotion",
    "discord",
```

- [ ] **Step 2: Verify syntax**

```bash
conda run -n ai python -m compileall core/eventbus/events.py -q
```
Expected: no output

- [ ] **Step 3: Commit**

```bash
git add core/eventbus/events.py
git commit -m "feat: register discord event family in eventbus"
```

---

### Task 3: Add `get_pinned_session_id()` to notification_bridge

**Files:**
- Modify: `apps/api/jarvis_api/services/notification_bridge.py`

The discord gateway needs to know which session the owner is currently viewing (so DM messages go into the same session as webchat). This helper exposes the existing `_pinned_session_id` variable.

- [ ] **Step 1: Add helper after `pin_session()`**

In `notification_bridge.py`, after the `pin_session()` function (around line 31), add:

```python
def get_pinned_session_id() -> str:
    """Return the currently pinned session ID, or empty string if none."""
    return _pinned_session_id
```

- [ ] **Step 2: Verify syntax**

```bash
conda run -n ai python -m compileall apps/api/jarvis_api/services/notification_bridge.py -q
```
Expected: no output

- [ ] **Step 3: Commit**

```bash
git add apps/api/jarvis_api/services/notification_bridge.py
git commit -m "feat: expose get_pinned_session_id() in notification_bridge"
```

---

### Task 4: `discord_gateway.py`

**Files:**
- Create: `apps/api/jarvis_api/services/discord_gateway.py`

This is the core service. It:
1. Runs discord.py in a daemon thread with its own asyncio loop
2. Handles inbound messages (persist → run → respond)
3. Sends outbound messages via `asyncio.run_coroutine_threadsafe`
4. Subscribes to eventbus to route assistant responses back to Discord
5. Publishes `discord.*` events for observability

- [ ] **Step 1: Write the full file**

```python
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
        # Look for existing discord-owner session
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
                # Split long messages (Discord limit: 2000 chars)
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


def _split_message(text: str, limit: int) -> list[str]:
    """Split text into chunks of at most `limit` characters."""
    if len(text) <= limit:
        return [text]
    chunks = []
    while text:
        chunks.append(text[:limit])
        text = text[limit:]
    return chunks


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
        logger.info("discord_gateway: connected as %s to guild %s", _client.user, _status["guild_name"])
        from core.eventbus.bus import event_bus
        event_bus.publish("discord.connected", {"guild_id": str(guild_id), "guild_name": _status["guild_name"]})

    @_client.event
    async def on_message(message: Any) -> None:
        import discord as _discord
        # Ignore our own messages
        if message.author == _client.user:
            return
        # Determine channel type
        is_dm = isinstance(message.channel, _discord.DMChannel)
        # For guild messages: only respond in allowed channels
        if not is_dm:
            if message.guild is None or message.guild.id != guild_id:
                return
            if message.channel.id not in allowed_channel_ids:
                return
        # DM: only accept from owner
        if is_dm and str(message.author.id) != owner_discord_id:
            return

        is_owner = str(message.author.id) == owner_discord_id

        # Rate limit non-owner users
        if not is_owner:
            now = time.monotonic()
            last = _user_last_response.get(message.author.id, 0.0)
            if now - last < _RATE_LIMIT_SECONDS:
                return
            _user_last_response[message.author.id] = now

        content = message.content.strip()
        if not content:
            return

        channel_id = message.channel.id
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
```

- [ ] **Step 2: Verify syntax**

```bash
conda run -n ai python -m compileall apps/api/jarvis_api/services/discord_gateway.py -q
```
Expected: no output

- [ ] **Step 3: Smoke test (import only — no live Discord connection)**

```bash
conda run -n ai python -c "
import sys; sys.path.insert(0, '.')
from apps.api.jarvis_api.services.discord_gateway import get_discord_status, start_discord_gateway
print(get_discord_status())
start_discord_gateway()  # should print 'not configured, skipping'
print(get_discord_status())
"
```
Expected: `{'connected': False, ...}` twice, log line "not configured, skipping"

- [ ] **Step 4: Commit**

```bash
git add apps/api/jarvis_api/services/discord_gateway.py
git commit -m "feat: discord_gateway — isolated thread, inbound/outbound, eventbus integration"
```

---

### Task 5: Extend tools — `discord_status`, `notify_user` channel, `read_self_state`

**Files:**
- Modify: `core/tools/simple_tools.py`

Three changes:
1. Add `discord_status` tool definition + handler
2. Extend `notify_user` tool definition with optional `channel` param
3. Extend `_exec_notify_user` to route by channel
4. Extend `_exec_read_self_state` to include Discord status

- [ ] **Step 1: Add `discord_status` tool definition**

In `core/tools/simple_tools.py`, find the `search_chat_history` tool definition block (the last entry in `TOOL_DEFINITIONS`) and add after it, before the closing `]`:

```python
    {
        "type": "function",
        "function": {
            "name": "discord_status",
            "description": "Check Discord gateway connection state, active channels, and recent activity. Use to decide whether to reach out via Discord or to verify the connection is up.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
```

- [ ] **Step 2: Add optional `channel` param to `notify_user` tool definition**

Find the `notify_user` tool definition. Replace its `parameters` block:

```python
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The message to send to the user",
                    },
                    "channel": {
                        "type": "string",
                        "enum": ["webchat", "discord", "both"],
                        "description": "Where to send: 'webchat' (default, active browser session), 'discord' (DM to owner), or 'both'.",
                    },
                },
                "required": ["content"],
            },
```

- [ ] **Step 3: Update `_exec_notify_user` to route by channel**

Replace the existing `_exec_notify_user` function:

```python
def _exec_notify_user(args: dict[str, Any]) -> dict[str, Any]:
    """Push a proactive message to webchat, Discord, or both."""
    content = str(args.get("content") or "").strip()
    if not content:
        return {"status": "error", "error": "content is required"}

    channel = str(args.get("channel") or "webchat").strip().lower()
    if channel not in ("webchat", "discord", "both"):
        channel = "webchat"

    results: list[str] = []

    if channel in ("webchat", "both"):
        try:
            from apps.api.jarvis_api.services.notification_bridge import send_session_notification
            r = send_session_notification(content, source="jarvis-notify")
            if r.get("status") == "ok":
                results.append(f"webchat:{r.get('session_id', '')}")
            else:
                results.append(f"webchat:failed({r.get('error', '')})")
        except Exception as exc:
            results.append(f"webchat:error({exc})")

    if channel in ("discord", "both"):
        try:
            from apps.api.jarvis_api.services.discord_config import load_discord_config
            from apps.api.jarvis_api.services.discord_gateway import (
                get_discord_status,
                send_discord_message,
            )
            cfg = load_discord_config()
            status = get_discord_status()
            if not cfg:
                results.append("discord:not-configured")
            elif not status["connected"]:
                results.append("discord:not-connected")
            else:
                # Send to owner DM — find or create owner DM channel via gateway cache
                # We send to all active Discord sessions that are DMs (title="Discord DM")
                from apps.api.jarvis_api.services.chat_sessions import list_chat_sessions
                from apps.api.jarvis_api.services.discord_gateway import _discord_sessions, _discord_sessions_lock
                sent = False
                with _discord_sessions_lock:
                    sessions_snapshot = dict(_discord_sessions)
                for session_id, channel_id in sessions_snapshot.items():
                    from apps.api.jarvis_api.services.chat_sessions import get_chat_session
                    s = get_chat_session(session_id)
                    if s and s.get("title") == "Discord DM":
                        send_discord_message(channel_id, content)
                        results.append(f"discord:dm:{channel_id}")
                        sent = True
                        break
                if not sent:
                    results.append("discord:no-active-dm")
        except Exception as exc:
            results.append(f"discord:error({exc})")

    summary = ", ".join(results) if results else "no-op"
    return {"status": "ok", "text": f"Delivered to: {summary}", "channels": results}
```

- [ ] **Step 4: Add `_exec_discord_status` handler**

Add after `_exec_search_chat_history` (before the handler registry `_TOOL_HANDLERS`):

```python
def _exec_discord_status(_args: dict[str, Any]) -> dict[str, Any]:
    """Return Discord gateway connection state and activity summary."""
    try:
        from apps.api.jarvis_api.services.discord_config import is_discord_configured
        from apps.api.jarvis_api.services.discord_gateway import get_discord_status
        if not is_discord_configured():
            return {
                "status": "ok",
                "connected": False,
                "text": "Discord: not configured. Run: python scripts/jarvis.py discord-setup",
            }
        s = get_discord_status()
        connected = s["connected"]
        lines = [f"Discord: {'connected' if connected else 'disconnected'}"]
        if s.get("guild_name"):
            lines.append(f"Guild: {s['guild_name']}")
        if s.get("last_message_at"):
            lines.append(f"Last message: {s['last_message_at']}")
        if s.get("message_count"):
            lines.append(f"Messages sent: {s['message_count']}")
        if s.get("connect_error"):
            lines.append(f"Error: {s['connect_error']}")
        return {"status": "ok", "connected": connected, "gateway": s, "text": "\n".join(lines)}
    except Exception as exc:
        return {"status": "error", "error": str(exc), "text": f"Discord status unavailable: {exc}"}
```

- [ ] **Step 5: Register `discord_status` in `_TOOL_HANDLERS`**

In `_TOOL_HANDLERS`, add after `"search_chat_history": _exec_search_chat_history,`:

```python
    "discord_status": _exec_discord_status,
```

- [ ] **Step 6: Extend `_exec_read_self_state` with Discord status**

In `_exec_read_self_state`, find the last `lines.append(...)` call before `result["text"] = "\n".join(lines)`:

```python
    lines.append(f"Last decision: {cadence.get('last_decision_type', '?')}")
    result["text"] = "\n".join(lines)
    return result
```

Replace with:

```python
    lines.append(f"Last decision: {cadence.get('last_decision_type', '?')}")

    # Discord channel awareness
    try:
        from apps.api.jarvis_api.services.discord_config import is_discord_configured
        if is_discord_configured():
            from apps.api.jarvis_api.services.discord_gateway import get_discord_status
            ds = get_discord_status()
            conn = "connected" if ds["connected"] else "disconnected"
            last = ds.get("last_message_at") or "never"
            lines.append(f"Discord: {conn} | last_message: {last}")
    except Exception:
        pass

    result["text"] = "\n".join(lines)
    return result
```

- [ ] **Step 7: Verify syntax**

```bash
conda run -n ai python -m compileall core/tools/simple_tools.py -q
```
Expected: no output

- [ ] **Step 8: Smoke test**

```bash
conda run -n ai python -c "
import sys; sys.path.insert(0, '.')
from core.tools.simple_tools import execute_tool
r = execute_tool('discord_status', {})
print(r['text'])
r2 = execute_tool('read_self_state', {})
print(r2.get('text', '')[-200:])
"
```
Expected: `Discord: not configured. Run: ...` in first output, `Discord: ...` line at end of second.

- [ ] **Step 9: Commit**

```bash
git add core/tools/simple_tools.py
git commit -m "feat: discord_status tool, notify_user channel param, Discord in read_self_state"
```

---

### Task 6: Wire gateway into API lifespan

**Files:**
- Modify: `apps/api/jarvis_api/app.py`

- [ ] **Step 1: Add imports**

In `app.py`, after the `mood_oscillator` import block, add:

```python
from apps.api.jarvis_api.services.discord_gateway import (
    start_discord_gateway,
    stop_discord_gateway,
)
```

- [ ] **Step 2: Add start/stop calls in lifespan**

In the lifespan function, add `start_discord_gateway()` after `start_mood_listener()`:

```python
        start_mood_listener()
        start_discord_gateway()
        event_bus.publish("runtime.started", {"component": "api"})
```

And add `stop_discord_gateway()` in the shutdown block, before `stop_mood_listener()`:

```python
        stop_discord_gateway()
        stop_mood_listener()
        stop_runtime_hook_runtime()
```

- [ ] **Step 3: Verify syntax**

```bash
conda run -n ai python -m compileall apps/api/jarvis_api/app.py -q
```
Expected: no output

- [ ] **Step 4: Full compile check**

```bash
conda run -n ai python -m compileall core apps/api scripts -q
```
Expected: no output (or only .pyc messages, no ERROR lines)

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/app.py
git commit -m "feat: start/stop discord_gateway in API lifespan"
```

---

### Task 7: CLI — `discord-setup` and `discord-status`

**Files:**
- Modify: `scripts/jarvis.py`

- [ ] **Step 1: Add `cmd_discord_setup` function**

In `scripts/jarvis.py`, add this function before the `if __name__ == "__main__":` block (or before the `def main()` function):

```python
def cmd_discord_setup(args: argparse.Namespace) -> None:
    """Interactive wizard to configure the Discord gateway."""
    ensure_runtime_dirs()
    init_db()

    from apps.api.jarvis_api.services.discord_config import (
        load_discord_config,
        save_discord_config,
    )

    print("Discord Gateway Setup")
    print("=" * 40)

    existing = load_discord_config()
    if existing:
        print("Existing config found. Values in [brackets] are current — press Enter to keep.")
    print()

    def _prompt(label: str, current: str = "", secret: bool = False) -> str:
        suffix = f" [{current}]" if current and not secret else (" [set]" if current and secret else "")
        val = input(f"{label}{suffix}: ").strip()
        return val if val else current

    # Bot token
    current_token = (existing or {}).get("bot_token", "")
    bot_token = _prompt("Bot token", current_token, secret=True)
    if not bot_token:
        print("Error: bot token is required.")
        sys.exit(1)

    # Validate token by calling Discord API
    import urllib.request, urllib.error
    try:
        req = urllib.request.Request(
            "https://discord.com/api/v10/users/@me",
            headers={"Authorization": f"Bot {bot_token}"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            import json as _json
            bot_info = _json.loads(resp.read())
        print(f"Token valid — bot username: {bot_info.get('username', '?')}#{bot_info.get('discriminator', '0')}")
    except urllib.error.HTTPError as exc:
        print(f"Token validation failed: HTTP {exc.code}. Check your bot token.")
        sys.exit(1)
    except Exception as exc:
        print(f"Token validation failed: {exc}")
        sys.exit(1)

    # Guild ID
    current_guild = (existing or {}).get("guild_id", "")
    guild_id = _prompt("Guild ID", current_guild)
    if not guild_id:
        print("Error: guild ID is required.")
        sys.exit(1)

    # Channel IDs
    current_channels = ",".join((existing or {}).get("allowed_channel_ids", []))
    channels_input = _prompt("Allowed channel IDs (comma-separated)", current_channels)
    allowed_channel_ids = [c.strip() for c in channels_input.split(",") if c.strip()]
    if not allowed_channel_ids:
        print("Error: at least one channel ID is required.")
        sys.exit(1)

    # Owner Discord user ID
    current_owner = (existing or {}).get("owner_discord_id", "")
    owner_discord_id = _prompt("Owner Discord user ID", current_owner)
    if not owner_discord_id:
        print("Error: owner Discord user ID is required.")
        sys.exit(1)

    config = {
        "bot_token": bot_token,
        "guild_id": guild_id,
        "allowed_channel_ids": allowed_channel_ids,
        "owner_discord_id": owner_discord_id,
        "enabled": True,
    }
    save_discord_config(config)
    print()
    print("Config saved to ~/.jarvis-v2/config/discord.json (chmod 600)")
    print("Restart the API to activate: uvicorn apps.api.jarvis_api.app:app --reload")


def cmd_discord_status(_: argparse.Namespace) -> None:
    """Show Discord gateway config and connection status."""
    ensure_runtime_dirs()
    from apps.api.jarvis_api.services.discord_config import is_discord_configured, load_discord_config

    if not is_discord_configured():
        print("Discord is not configured. Run: python scripts/jarvis.py discord-setup")
        return

    cfg = load_discord_config()
    print(json.dumps({
        "configured": True,
        "guild_id": cfg.get("guild_id"),
        "allowed_channel_ids": cfg.get("allowed_channel_ids"),
        "owner_discord_id": cfg.get("owner_discord_id"),
        "enabled": cfg.get("enabled", True),
        "bot_token": "[set]",
    }, indent=2))

    # Try to get live status via API
    try:
        from core.cli.http_fallback import request_json
        result = request_json("GET", "/mc/system/health")
        print("\nAPI is reachable — Discord gateway status available via read_self_state tool.")
    except Exception:
        print("\nAPI not reachable — start the API to see live connection status.")
```

- [ ] **Step 2: Register the subcommands**

In `scripts/jarvis.py`, find the `sub.add_parser` block (near the end of the `main()` or parser setup function) and add:

```python
    discord_setup = sub.add_parser("discord-setup", help="Configure the Discord gateway interactively")
    discord_setup.set_defaults(func=cmd_discord_setup)

    discord_status = sub.add_parser("discord-status", help="Show Discord gateway config and status")
    discord_status.set_defaults(func=cmd_discord_status)
```

- [ ] **Step 3: Verify syntax**

```bash
conda run -n ai python -m compileall scripts/jarvis.py -q
```
Expected: no output

- [ ] **Step 4: Test help output**

```bash
conda run -n ai python scripts/jarvis.py discord-setup --help
conda run -n ai python scripts/jarvis.py discord-status
```
Expected first: shows usage. Expected second: "Discord is not configured. Run: ..."

- [ ] **Step 5: Run the setup wizard with the actual credentials**

```bash
conda run -n ai python scripts/jarvis.py discord-setup
```

Enter when prompted:
- Bot token: `MTQ3MjI3NzI0MTEyMjc4MzQ5Ng.GF1HAm.wIj141SGr66cR1PGrP92eSwg8joHt_fTi_ZxsY`
- Guild ID: `1474039062284206161`
- Allowed channel IDs: (enter the channel ID where Jarvis should respond)
- Owner Discord user ID: `1474039062284203496`

Expected: "Token valid — bot username: ..." then "Config saved..."

- [ ] **Step 6: Verify config was saved**

```bash
conda run -n ai python scripts/jarvis.py discord-status
```
Expected: JSON with guild_id, channel_ids, owner_discord_id, `"bot_token": "[set]"`

- [ ] **Step 7: Commit**

```bash
git add scripts/jarvis.py
git commit -m "feat: discord-setup and discord-status CLI subcommands"
```

---

### Task 8: Full integration test

- [ ] **Step 1: Full compile check**

```bash
conda run -n ai python -m compileall core apps/api scripts -q
```
Expected: no ERROR lines

- [ ] **Step 2: Restart the API**

```bash
# Stop existing API process, then:
conda run -n ai uvicorn apps.api.jarvis_api.app:app --host 0.0.0.0 --port 8000 --reload
```

Watch logs for:
- `discord_gateway: started`
- `discord_gateway: connected as <botname> to guild <guildname>`

- [ ] **Step 3: Verify Discord status tool**

```bash
conda run -n ai python -c "
import sys; sys.path.insert(0, '.')
from core.tools.simple_tools import execute_tool
print(execute_tool('discord_status', {})['text'])
"
```
Expected: `Discord: connected | Guild: <name>`

- [ ] **Step 4: Test proactive Discord message**

From the Python REPL (API must be running in another terminal):

```bash
conda run -n ai python -c "
import sys; sys.path.insert(0, '.')
from apps.api.jarvis_api.services.discord_gateway import send_discord_message, get_discord_status
print(get_discord_status())
# Note: send_discord_message won't work from CLI (different process, no live client)
# Test via the running API instead — trigger a heartbeat tick and watch Discord
"
```

To send a real test message, use Jarvis's `notify_user` tool via webchat:
```
notify_user(content="Test fra Jarvis — Discord forbindelsen virker!", channel="discord")
```

Expected: Message appears in Discord DM from the bot.

- [ ] **Step 5: Test inbound — write to the bot in Discord**

Send a message to the bot in the configured channel or DM. Watch API logs for:
- `discord.message_received` event
- Autonomous run starting
- `channel.chat_message_appended` event
- Response appearing in Discord

- [ ] **Step 6: Final commit**

```bash
git add -u
git commit -m "feat: Discord gateway — full integration complete"
```
