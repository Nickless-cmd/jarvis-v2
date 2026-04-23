# Channel Attachments — File & Image Support for Discord and Telegram

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable Jarvis to receive and send files and images (all types) via Discord and Telegram, with a shared attachment service that downloads, stores, and exposes attachments as tools Jarvis can actively use.

**Architecture:** A new `attachment_service.py` handles all download/storage/DB logic centrally. Both gateways call into it on inbound messages and use it as reference for outbound sends. Jarvis gets `read_attachment` and `list_attachments` tools to analyze and reference received files.

**Tech Stack:** discord.py (attachments API), Telegram Bot API (getFile + sendPhoto/sendDocument/sendAudio/sendVideo), SQLite (`channel_attachments` table), existing vision model via `visual_memory._describe_via_ollama`, existing `~/.jarvis-v2/uploads/` storage path.

---

## Components

### New files
- `core/services/attachment_service.py` — download, storage, DB persistence, retrieval
- `tests/test_attachment_service.py`
- `tests/test_discord_gateway_attachments.py`
- `tests/test_telegram_gateway_attachments.py`
- `tests/test_simple_tools_attachments.py`

### Modified files
- `core/runtime/db.py` — new `channel_attachments` table + CRUD functions
- `core/services/discord_gateway.py` — extract inbound attachments, support outbound file sends
- `core/services/telegram_gateway.py` — extract inbound media (photo/document/audio/video), support outbound file sends
- `core/tools/simple_tools.py` — `read_attachment` + `list_attachments` tools; extend `discord_channel` send + `send_telegram_message` with optional `file_path`

---

## Database Schema

New table `channel_attachments`:

```sql
CREATE TABLE IF NOT EXISTS channel_attachments (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    attachment_id TEXT    NOT NULL UNIQUE,   -- UUID
    session_id    TEXT    NOT NULL,
    channel_type  TEXT    NOT NULL,          -- "discord" | "telegram" | "web"
    filename      TEXT    NOT NULL,
    mime_type     TEXT    NOT NULL DEFAULT "",
    size_bytes    INTEGER NOT NULL DEFAULT 0,
    local_path    TEXT    NOT NULL,
    source_url    TEXT    NOT NULL DEFAULT "",
    created_at    TEXT    NOT NULL
)
```

CRUD functions in `db.py`:
- `store_channel_attachment(attachment_id, session_id, channel_type, filename, mime_type, size_bytes, local_path, source_url)` → None
- `get_channel_attachment(attachment_id)` → dict | None
- `list_channel_attachments(session_id, limit=20)` → list[dict]

---

## attachment_service.py Interface

```python
MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

def download_and_store(
    *,
    url: str,
    filename: str,
    mime_type: str,
    size_bytes: int,
    session_id: str,
    channel_type: str,  # "discord" | "telegram"
    http_headers: dict[str, str] | None = None,
) -> dict:
    """Download file from URL and store locally.
    
    Returns:
        {"status": "ok", "attachment_id": str, "local_path": str}
        {"status": "error", "reason": str}  # too_large | download_failed | disk_error
    """

def get_attachment(attachment_id: str) -> dict | None:
    """Return attachment metadata dict or None if not found."""

def list_attachments(session_id: str, limit: int = 20) -> list[dict]:
    """Return recent attachments for session, newest first."""

def read_attachment_content(attachment_id: str) -> dict:
    """Read attachment for Jarvis context.
    
    - image/*: calls vision model, returns description
    - text/*: returns file content (truncated at 8000 chars)
    - application/pdf: returns first 8000 chars via text extraction
    - other: returns metadata + hex preview (first 64 bytes)
    
    Returns: {"status": "ok", "type": str, "content": str, "filename": str}
    """

_ALLOWED_SEND_ROOTS = [
    Path(JARVIS_HOME) / "uploads",
    Path(JARVIS_HOME) / "workspaces",
]

def validate_send_path(path: str) -> tuple[bool, str]:
    """Return (ok, error_message). Checks file exists, readable, under 50 MB,
    within allowed roots."""
```

Storage path: `~/.jarvis-v2/uploads/{session_id}/{uuid4}_{filename}`

---

## Inbound Data Flow

### Discord
```
on_message() in discord_gateway.py
  ├── existing: extract message.content
  └── NEW: for attachment in message.attachments:
        result = attachment_service.download_and_store(
            url=attachment.url,
            filename=attachment.filename,
            mime_type=attachment.content_type or "",
            size_bytes=attachment.size,
            session_id=session_id,
            channel_type="discord",
        )
        if result["status"] == "ok":
            content_prefix += f"[Fil modtaget: {filename} ({mime}) — id: {id}]\n"
        else:
            content_prefix += f"[Fil kunne ikke hentes: {filename} — {reason}]\n"
      content_raw = content_prefix + (message.content or "")
```

### Telegram
Telegram does not include a direct download URL in updates. The gateway must:

1. Detect media type from update dict:
   - `photo` → list of sizes, use last (largest): `photo[-1]["file_id"]`
   - `document` → `document["file_id"]`, `document["file_name"]`, `document["mime_type"]`
   - `audio` → `audio["file_id"]`, `audio["file_name"]`, `audio["mime_type"]`
   - `video` → `video["file_id"]`, `video["mime_type"]`
   - `voice` → `voice["file_id"]`, mime_type `audio/ogg`
   - `sticker` → `sticker["file_id"]`, mime_type `image/webp`

2. For each media item, resolve download URL:
   ```
   GET https://api.telegram.org/bot{token}/getFile?file_id={file_id}
   → response.result.file_path
   download_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
   ```

3. Call `attachment_service.download_and_store(url=download_url, ...)`

4. Build content prefix identical to Discord pattern.

**File size note:** Telegram Bot API only serves files up to 20 MB via `getFile`. Files 20–50 MB require the local Bot API server — not supported in v1. Files reported > 20 MB are skipped with a note in content.

---

## Outbound Data Flow

### Discord
Extend `_outbound_queue` entries with optional `file_path`:
```python
# Queue entry: {"channel_id": int, "text": str, "file_path": str | None}

# In _send_outbound_loop():
if file_path:
    await channel.send(content=text or None, file=discord.File(file_path))
else:
    for chunk in _split_message(text):
        await channel.send(chunk)
```

New function: `send_discord_file(channel_id: int, text: str, file_path: str) → None`
Puts `{"channel_id": ..., "text": ..., "file_path": ...}` on `_outbound_queue`.

### Telegram
Add `send_telegram_file(text: str, file_path: str, chat_id: int) → dict`:
```python
mime = mimetypes.guess_type(file_path)[0] or ""
if mime.startswith("image/"):
    method = "sendPhoto"
    field = "photo"
elif mime.startswith("audio/"):
    method = "sendAudio"
    field = "audio"
elif mime.startswith("video/"):
    method = "sendVideo"
    field = "video"
else:
    method = "sendDocument"
    field = "document"

with open(file_path, "rb") as f:
    requests.post(
        f"{_BASE}/{method}",
        data={"chat_id": chat_id, "caption": text},
        files={field: f},
        timeout=60,
    )
```

---

## Tools

### `read_attachment`
```python
{
    "name": "read_attachment",
    "description": "Læs indholdet af en modtaget fil. Billeder analyseres via vision-model. Tekstfiler returneres direkte. Andre filer returnerer metadata.",
    "parameters": {
        "attachment_id": {"type": "string", "description": "ID fra [Fil modtaget: ...] besked"}
    }
}
```
Calls `attachment_service.read_attachment_content(attachment_id)`.

### `list_attachments`
```python
{
    "name": "list_attachments",
    "description": "List filer modtaget i den aktuelle session",
    "parameters": {
        "limit": {"type": "integer", "default": 10}
    }
}
```

### Extended `discord_channel` send action
Add optional `file_path: str` parameter. When present, validates path via `attachment_service.validate_send_path()` then calls `send_discord_file()`.

### Extended `send_telegram_message`
Add optional `file_path: str` parameter. When present, validates + calls `send_telegram_file()`.

---

## Security

**Outbound path whitelist** — Jarvis may only send files from:
- `~/.jarvis-v2/uploads/` (received attachments)
- `~/.jarvis-v2/workspaces/` (workspace files)

Files outside these roots → `{"status": "error", "reason": "path-not-allowed"}`.

**Size limits:**
- Inbound: 50 MB max (Discord max 25 MB for free bots, Telegram getFile max 20 MB)
- Outbound: 25 MB Discord, 50 MB Telegram

---

## Error Handling

| Situation | Behaviour |
|-----------|-----------|
| Download network timeout | `[Fil kunne ikke hentes: name — download fejlede]` in content |
| File too large inbound | `[Fil ignoreret: name (X MB) — overstiger grænsen]` in content |
| `read_attachment` unknown ID | `{"status": "error", "reason": "not-found"}` |
| Vision model fails on image | Returns raw attachment metadata + `"vision-failed"` status |
| Disk full on store | Log warning, `{"status": "error", "reason": "disk-error"}` |
| Outbound path not allowed | `{"status": "error", "reason": "path-not-allowed"}` |
| Outbound file too large | `{"status": "error", "reason": "file-too-large", "size_bytes": N}` |

---

## Testing Strategy

All tests are unit tests — no real network calls, Discord client, or Telegram API.

**`tests/test_attachment_service.py`:**
- `download_and_store` saves file to correct path and returns UUID (monkeypatch urllib)
- `store` writes correct row to DB
- `get_attachment` returns metadata for known ID, None for unknown
- File over size limit returns `{"status": "error", "reason": "too_large"}`
- `list_attachments` returns only attachments for given session_id
- `read_attachment_content` on image calls vision function, returns description
- `read_attachment_content` on text file returns file content
- `validate_send_path` rejects paths outside allowed roots

**`tests/test_discord_gateway_attachments.py`:**
- Inbound message with attachment → `download_and_store` called, content contains reference
- Inbound message without attachment → unchanged flow (no attachment calls)
- Outbound with `file_path` → `channel.send(file=discord.File(...))` called
- Outbound with disallowed path → error returned, no send

**`tests/test_telegram_gateway_attachments.py`:**
- Photo update → `getFile` called, file downloaded, reference in content
- Document update → same flow with correct filename/mime
- Text-only update → no attachment calls made
- Outbound image → `sendPhoto` endpoint called with correct field
- Outbound document → `sendDocument` endpoint called

**`tests/test_simple_tools_attachments.py`:**
- `read_attachment` on image → vision model called, description returned
- `read_attachment` on text file → file content returned
- `read_attachment` on unknown ID → `{"status": "error"}`
- `list_attachments` returns correct list
- `discord_channel` send with `file_path` → validates path, calls `send_discord_file`
- `send_telegram_message` with `file_path` → validates path, calls `send_telegram_file`
