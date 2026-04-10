# Discord Gateway — Design Spec

**Date:** 2026-04-10  
**Status:** Approved

---

## Goal

Give Jarvis a Discord presence: he can receive messages, respond to them, and reach out proactively — just like he does in webchat. He is aware of the connection state and can act on it himself.

---

## Architecture Overview

Discord runs in a **dedicated daemon thread with its own asyncio event loop**, completely isolated from FastAPI's event loop. This is the fix for the old blocking problem where discord.py's asyncio loop conflicted with FastAPI's.

```
FastAPI (main asyncio loop)
    │
    ├── _outbound_queue (thread-safe Queue)
    │       ↑ main thread puts (channel_id, message)
    │       ↓ discord thread reads and sends
    │
    └── eventbus
            → discord.connected / discord.disconnected
            → discord.message_received / discord.message_sent
```

Inbound Discord messages → discord thread calls into `run_visible_run()` (sync-compatible) directly. No shared event loop, no blocking.

---

## Files

| File | Action | Responsibility |
|------|--------|----------------|
| `apps/api/jarvis_api/services/discord_config.py` | Create | Load/save `~/.jarvis-v2/config/discord.json` |
| `apps/api/jarvis_api/services/discord_gateway.py` | Create | Discord client, thread management, in/outbound queues, eventbus integration |
| `core/tools/simple_tools.py` | Modify | Extend `notify_user()`, extend `read_self_state()`, add `discord_status` tool |
| `apps/api/jarvis_api/app.py` | Modify | Start/stop gateway in lifespan |
| `scripts/jarvis.py` | Modify | Add `discord setup/start/stop/status` subcommands |

---

## Config

Stored at `~/.jarvis-v2/config/discord.json` with `chmod 600`. Never committed to git.

```json
{
  "bot_token": "...",
  "guild_id": "1474039062284206161",
  "allowed_channel_ids": ["..."],
  "owner_discord_id": "1474039062284203496",
  "enabled": true
}
```

`discord_config.py` exposes:
- `load_discord_config() -> dict | None` — returns None if file missing or malformed
- `save_discord_config(config: dict) -> None` — writes with chmod 600
- `is_discord_configured() -> bool`

---

## Discord Gateway Service

`discord_gateway.py` provides:

```python
def start_discord_gateway() -> None   # called from app.py lifespan
def stop_discord_gateway() -> None    # called from app.py lifespan
def send_discord_message(channel_id: str, text: str) -> None  # thread-safe
def get_discord_status() -> dict      # connection state, last activity
```

### Thread model

```python
_outbound_queue: queue.Queue  # (channel_id, text) tuples

def _discord_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_run_client())

thread = threading.Thread(target=_discord_thread, daemon=True, name="discord-gateway")
thread.start()
```

### Inbound message handling

```python
async def on_message(message):
    # 1. Ignore bots
    # 2. Ignore messages outside allowed guild/channels
    # 3. Determine session and permission level
    # 4. Persist message to chat_messages
    # 5. Call run_visible_run(message, session_id, tools_enabled=is_owner)
    # 6. Send response back to Discord channel
```

### Eventbus events published

| Event | Payload |
|-------|---------|
| `discord.connected` | `{"guild_id": "..."}` |
| `discord.disconnected` | `{"reason": "..."}` |
| `discord.message_received` | `{"channel_id", "user_id", "is_owner", "is_dm"}` |
| `discord.message_sent` | `{"channel_id", "length"}` |

---

## Session Mapping

| Source | Session ID | Tools enabled |
|--------|-----------|---------------|
| Discord DM (owner) | Pinned webchat session (fallback: `discord-owner`) | Yes |
| Discord public channel | `discord-channel-{channel_id}` | No (owner can still trigger) |
| Webchat | `chat-{uuid}` (unchanged) | Yes |

**DM continuity:** Owner writes in Discord DM → message goes into the currently pinned webchat session. If no session is pinned, create/reuse `discord-owner`. This means the conversation continues naturally across webchat and Discord — Jarvis remembers exactly where you left off.

**Public channel:** All users in the channel share one session per channel. Jarvis sees the full conversation flow.

---

## Security Model

- `owner_discord_id` from config is the single source of truth for owner identity
- **Owner** → full execution pipeline, tools enabled, all commands
- **Others** → conversational mode only, no tools, no system access
- **Whitelist** → only respond in configured `allowed_channel_ids` + DM from owner; ignore everything else
- **Rate limit** → max 1 response per 10 seconds per non-owner user

---

## Channel Awareness (Self-Model Integration)

### `read_self_state` extension

Discord status added to the existing `read_self_state` tool output:

```
Discord: connected | channels: #general | dm: active | last_message: 3m ago
```

### New tool: `discord_status`

```json
{
  "name": "discord_status",
  "description": "Check Discord gateway connection state, active channels, and recent activity. Use to decide whether to reach out via Discord."
}
```

Returns: connection state, guild name, active channels, last message timestamp, message count.

### `notify_user()` channel extension

`notify_user(content, channel)` where `channel` is one of:
- `"webchat"` — current default, sends to pinned webchat session
- `"discord"` — sends DM to owner via Discord
- `"both"` — sends to both

Jarvis decides which channel based on context (e.g., if owner has been on Discord recently, prefer Discord).

---

## CLI — `scripts/jarvis.py discord`

```bash
python scripts/jarvis.py discord setup     # interactive wizard
python scripts/jarvis.py discord status    # show connection state
python scripts/jarvis.py discord start     # start gateway (if API running)
python scripts/jarvis.py discord stop      # stop gateway (if API running)
```

**Setup wizard steps:**
1. Prompt for bot token → validate by calling Discord API (`GET /users/@me`)
2. Prompt for guild ID
3. Prompt for one or more channel IDs
4. Prompt for owner Discord user ID
5. Save to `~/.jarvis-v2/config/discord.json` with `chmod 600`
6. Print success + next steps

---

## Startup Integration

`app.py` lifespan extended:

```python
from apps.api.jarvis_api.services.discord_gateway import (
    start_discord_gateway,
    stop_discord_gateway,
)

# startup:
if is_discord_configured():
    start_discord_gateway()

# shutdown:
stop_discord_gateway()
```

Gateway starts automatically if configured. If not configured, it's silently skipped — no errors.

---

## Non-goals

- No slash commands (Discord's `/` system) — plain messages only
- No multi-guild support — one guild only
- No message editing/deletion tracking
- No voice channels
