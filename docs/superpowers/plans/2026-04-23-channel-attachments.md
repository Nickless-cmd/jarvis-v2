# Channel Attachments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable Jarvis to receive and send files/images (all types) via Discord and Telegram using a shared attachment service.

**Architecture:** `core/services/attachment_service.py` handles all download/storage/DB logic. Discord and Telegram gateways call into it on inbound messages. Jarvis gets `read_attachment` and `list_attachments` tools. Outbound file sends extend existing gateway send functions.

**Tech Stack:** discord.py attachments API, Telegram Bot API (getFile/sendPhoto/sendDocument/sendAudio/sendVideo), SQLite (`channel_attachments` table in `core/runtime/db.py`), existing vision model (`visual_memory._describe_via_ollama`), `~/.jarvis-v2/uploads/` storage.

---

## File Map

| File | Change |
|------|--------|
| `core/runtime/db.py` | Add `_ensure_channel_attachments_table`, `store_channel_attachment`, `get_channel_attachment`, `list_channel_attachments` |
| `core/services/attachment_service.py` | **NEW** — download, store, read, validate |
| `core/services/discord_gateway.py` | Extract inbound attachments in `on_message()`; extend `_send_outbound_loop` + add `send_discord_file()` |
| `core/services/telegram_gateway.py` | Extract inbound media in `_poll_loop()`; add `send_telegram_file()` |
| `core/tools/simple_tools.py` | Add `read_attachment` + `list_attachments` tool defs + executors; extend `discord_channel` send + `send_telegram_message` |
| `tests/test_attachment_service.py` | **NEW** |
| `tests/test_discord_gateway_attachments.py` | **NEW** |
| `tests/test_telegram_gateway_attachments.py` | **NEW** |
| `tests/test_simple_tools_attachments.py` | **NEW** |

---

## Task 1: DB — channel_attachments table and CRUD

**Files:**
- Modify: `core/runtime/db.py` (append at end, after `web_cache_lookup`)

- [ ] **Step 1: Write failing tests**

Create `tests/test_channel_attachments_db.py`:

```python
# tests/test_channel_attachments_db.py
from __future__ import annotations
import pytest


def _get_db():
    from core.runtime.db import connect, _ensure_channel_attachments_table
    conn = connect()
    _ensure_channel_attachments_table(conn)
    return conn


def test_store_and_get_attachment(tmp_path):
    from core.runtime.db import store_channel_attachment, get_channel_attachment
    conn = _get_db()
    store_channel_attachment(
        conn=conn,
        attachment_id="abc-123",
        session_id="sess-1",
        channel_type="discord",
        filename="photo.jpg",
        mime_type="image/jpeg",
        size_bytes=12345,
        local_path="/tmp/photo.jpg",
        source_url="https://cdn.discord.com/photo.jpg",
    )
    conn.commit()
    row = get_channel_attachment(conn=conn, attachment_id="abc-123")
    assert row is not None
    assert row["filename"] == "photo.jpg"
    assert row["channel_type"] == "discord"
    assert row["size_bytes"] == 12345


def test_get_unknown_returns_none():
    from core.runtime.db import get_channel_attachment
    conn = _get_db()
    assert get_channel_attachment(conn=conn, attachment_id="does-not-exist") is None


def test_list_channel_attachments_scoped_to_session():
    from core.runtime.db import store_channel_attachment, list_channel_attachments
    conn = _get_db()
    store_channel_attachment(
        conn=conn, attachment_id="s1-a", session_id="sess-A", channel_type="discord",
        filename="a.jpg", mime_type="image/jpeg", size_bytes=100,
        local_path="/tmp/a.jpg", source_url="",
    )
    store_channel_attachment(
        conn=conn, attachment_id="s2-b", session_id="sess-B", channel_type="telegram",
        filename="b.pdf", mime_type="application/pdf", size_bytes=200,
        local_path="/tmp/b.pdf", source_url="",
    )
    conn.commit()
    rows_a = list_channel_attachments(conn=conn, session_id="sess-A")
    assert all(r["session_id"] == "sess-A" for r in rows_a)
    ids_a = [r["attachment_id"] for r in rows_a]
    assert "s1-a" in ids_a
    assert "s2-b" not in ids_a
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /media/projects/jarvis-v2
conda activate ai && python -m pytest tests/test_channel_attachments_db.py -v
```

Expected: FAIL — `cannot import name '_ensure_channel_attachments_table'`

- [ ] **Step 3: Add DB functions to `core/runtime/db.py`**

Append after the `web_cache_lookup` function (after line ~32870):

```python
# ---------------------------------------------------------------------------
# Channel Attachments
# ---------------------------------------------------------------------------

def _ensure_channel_attachments_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS channel_attachments (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            attachment_id TEXT    NOT NULL UNIQUE,
            session_id    TEXT    NOT NULL,
            channel_type  TEXT    NOT NULL,
            filename      TEXT    NOT NULL,
            mime_type     TEXT    NOT NULL DEFAULT '',
            size_bytes    INTEGER NOT NULL DEFAULT 0,
            local_path    TEXT    NOT NULL,
            source_url    TEXT    NOT NULL DEFAULT '',
            created_at    TEXT    NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_channel_attachments_session "
        "ON channel_attachments(session_id)"
    )


def store_channel_attachment(
    *,
    conn: sqlite3.Connection,
    attachment_id: str,
    session_id: str,
    channel_type: str,
    filename: str,
    mime_type: str,
    size_bytes: int,
    local_path: str,
    source_url: str,
) -> None:
    _ensure_channel_attachments_table(conn)
    now = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT OR IGNORE INTO channel_attachments
            (attachment_id, session_id, channel_type, filename, mime_type,
             size_bytes, local_path, source_url, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (attachment_id, session_id, channel_type, filename, mime_type,
         size_bytes, local_path, source_url, now),
    )


def get_channel_attachment(
    *, conn: sqlite3.Connection, attachment_id: str
) -> dict | None:
    _ensure_channel_attachments_table(conn)
    row = conn.execute(
        """
        SELECT attachment_id, session_id, channel_type, filename, mime_type,
               size_bytes, local_path, source_url, created_at
        FROM channel_attachments WHERE attachment_id = ?
        """,
        (attachment_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def list_channel_attachments(
    *, conn: sqlite3.Connection, session_id: str, limit: int = 20
) -> list[dict]:
    _ensure_channel_attachments_table(conn)
    rows = conn.execute(
        """
        SELECT attachment_id, session_id, channel_type, filename, mime_type,
               size_bytes, local_path, source_url, created_at
        FROM channel_attachments
        WHERE session_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (session_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]
```

- [ ] **Step 4: Run tests — expect pass**

```bash
conda activate ai && python -m pytest tests/test_channel_attachments_db.py -v
```

Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add core/runtime/db.py tests/test_channel_attachments_db.py
git commit -m "feat(db): add channel_attachments table and CRUD functions"
```

---

## Task 2: attachment_service.py — core service

**Files:**
- Create: `core/services/attachment_service.py`
- Test: `tests/test_attachment_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_attachment_service.py`:

```python
# tests/test_attachment_service.py
from __future__ import annotations
import json
import os
import pytest


# ---------------------------------------------------------------------------
# download_and_store
# ---------------------------------------------------------------------------

def test_download_and_store_returns_ok(tmp_path, monkeypatch):
    import core.services.attachment_service as svc
    monkeypatch.setattr(svc, "_UPLOAD_ROOT", tmp_path)

    def fake_download(url, headers):
        return b"fake image data"

    monkeypatch.setattr(svc, "_http_download", fake_download)
    monkeypatch.setattr(svc, "_db_store", lambda **kw: None)

    result = svc.download_and_store(
        url="https://cdn.discord.com/photo.jpg",
        filename="photo.jpg",
        mime_type="image/jpeg",
        size_bytes=100,
        session_id="sess-1",
        channel_type="discord",
    )
    assert result["status"] == "ok"
    assert "attachment_id" in result
    saved = tmp_path / "sess-1" / f"{result['attachment_id']}_photo.jpg"
    assert saved.exists()
    assert saved.read_bytes() == b"fake image data"


def test_download_and_store_rejects_too_large(monkeypatch):
    import core.services.attachment_service as svc
    result = svc.download_and_store(
        url="https://cdn.discord.com/big.zip",
        filename="big.zip",
        mime_type="application/zip",
        size_bytes=svc.MAX_SIZE_BYTES + 1,
        session_id="sess-1",
        channel_type="discord",
    )
    assert result["status"] == "error"
    assert result["reason"] == "too_large"


def test_download_and_store_handles_download_failure(tmp_path, monkeypatch):
    import core.services.attachment_service as svc
    monkeypatch.setattr(svc, "_UPLOAD_ROOT", tmp_path)

    def fail_download(url, headers):
        raise OSError("timeout")

    monkeypatch.setattr(svc, "_http_download", fail_download)

    result = svc.download_and_store(
        url="https://cdn.discord.com/photo.jpg",
        filename="photo.jpg",
        mime_type="image/jpeg",
        size_bytes=100,
        session_id="sess-1",
        channel_type="discord",
    )
    assert result["status"] == "error"
    assert result["reason"] == "download_failed"


# ---------------------------------------------------------------------------
# get_attachment / list_attachments
# ---------------------------------------------------------------------------

def test_get_attachment_returns_metadata(monkeypatch):
    import core.services.attachment_service as svc
    fake_row = {
        "attachment_id": "abc-123", "session_id": "sess-1",
        "channel_type": "discord", "filename": "photo.jpg",
        "mime_type": "image/jpeg", "size_bytes": 100,
        "local_path": "/tmp/photo.jpg", "source_url": "", "created_at": "2026-04-23T00:00:00",
    }
    monkeypatch.setattr(svc, "_db_get", lambda attachment_id: fake_row)
    result = svc.get_attachment("abc-123")
    assert result["filename"] == "photo.jpg"


def test_get_attachment_returns_none_for_unknown(monkeypatch):
    import core.services.attachment_service as svc
    monkeypatch.setattr(svc, "_db_get", lambda attachment_id: None)
    assert svc.get_attachment("unknown-id") is None


def test_list_attachments_returns_list(monkeypatch):
    import core.services.attachment_service as svc
    fake_rows = [
        {"attachment_id": "x1", "filename": "a.jpg", "session_id": "sess-1",
         "channel_type": "discord", "mime_type": "image/jpeg", "size_bytes": 1,
         "local_path": "", "source_url": "", "created_at": ""},
    ]
    monkeypatch.setattr(svc, "_db_list", lambda session_id, limit: fake_rows)
    rows = svc.list_attachments("sess-1")
    assert len(rows) == 1
    assert rows[0]["filename"] == "a.jpg"


# ---------------------------------------------------------------------------
# read_attachment_content
# ---------------------------------------------------------------------------

def test_read_attachment_content_unknown_id(monkeypatch):
    import core.services.attachment_service as svc
    monkeypatch.setattr(svc, "_db_get", lambda attachment_id: None)
    result = svc.read_attachment_content("unknown")
    assert result["status"] == "error"
    assert result["reason"] == "not-found"


def test_read_attachment_content_text_file(tmp_path, monkeypatch):
    import core.services.attachment_service as svc
    txt = tmp_path / "note.txt"
    txt.write_text("hello world")
    row = {
        "attachment_id": "t1", "filename": "note.txt", "mime_type": "text/plain",
        "local_path": str(txt), "session_id": "s", "channel_type": "discord",
        "size_bytes": 11, "source_url": "", "created_at": "",
    }
    monkeypatch.setattr(svc, "_db_get", lambda aid: row)
    result = svc.read_attachment_content("t1")
    assert result["status"] == "ok"
    assert result["type"] == "text"
    assert "hello world" in result["content"]


def test_read_attachment_content_image_calls_vision(tmp_path, monkeypatch):
    import base64
    import core.services.attachment_service as svc
    img = tmp_path / "pic.jpg"
    img.write_bytes(b"\xff\xd8\xff")  # minimal JPEG header
    row = {
        "attachment_id": "i1", "filename": "pic.jpg", "mime_type": "image/jpeg",
        "local_path": str(img), "session_id": "s", "channel_type": "discord",
        "size_bytes": 3, "source_url": "", "created_at": "",
    }
    monkeypatch.setattr(svc, "_db_get", lambda aid: row)
    called = {}
    def fake_vision(b64, *, model, prompt=None):
        called["b64"] = b64
        return "a nice photo"
    monkeypatch.setattr(svc, "_call_vision", fake_vision)
    result = svc.read_attachment_content("i1")
    assert result["status"] == "ok"
    assert result["type"] == "image"
    assert "a nice photo" in result["content"]
    assert "b64" in called


# ---------------------------------------------------------------------------
# validate_send_path
# ---------------------------------------------------------------------------

def test_validate_send_path_rejects_outside_roots(tmp_path, monkeypatch):
    import core.services.attachment_service as svc
    monkeypatch.setattr(svc, "_ALLOWED_SEND_ROOTS", [tmp_path / "uploads"])
    ok, err = svc.validate_send_path("/etc/passwd")
    assert not ok
    assert "not-allowed" in err


def test_validate_send_path_rejects_missing_file(tmp_path, monkeypatch):
    import core.services.attachment_service as svc
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    monkeypatch.setattr(svc, "_ALLOWED_SEND_ROOTS", [uploads])
    ok, err = svc.validate_send_path(str(uploads / "missing.jpg"))
    assert not ok
    assert "not-found" in err


def test_validate_send_path_accepts_valid_file(tmp_path, monkeypatch):
    import core.services.attachment_service as svc
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    f = uploads / "file.jpg"
    f.write_bytes(b"data")
    monkeypatch.setattr(svc, "_ALLOWED_SEND_ROOTS", [uploads])
    ok, err = svc.validate_send_path(str(f))
    assert ok
    assert err == ""
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate ai && python -m pytest tests/test_attachment_service.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'core.services.attachment_service'`

- [ ] **Step 3: Create `core/services/attachment_service.py`**

```python
"""attachment_service — download, store, and read channel attachments.

Shared by discord_gateway and telegram_gateway. Handles all file I/O and
DB persistence so gateways contain no download/storage logic.
"""
from __future__ import annotations

import base64
import logging
import mimetypes
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from core.runtime.config import JARVIS_HOME

logger = logging.getLogger(__name__)

MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
_MAX_TEXT_CHARS = 8_000
_UPLOAD_ROOT = JARVIS_HOME / "uploads"

_ALLOWED_SEND_ROOTS: list[Path] = [
    JARVIS_HOME / "uploads",
    JARVIS_HOME / "workspaces",
]


# ---------------------------------------------------------------------------
# Internal helpers (monkeypatchable in tests)
# ---------------------------------------------------------------------------

def _http_download(url: str, headers: dict[str, str] | None) -> bytes:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def _db_store(
    *,
    attachment_id: str,
    session_id: str,
    channel_type: str,
    filename: str,
    mime_type: str,
    size_bytes: int,
    local_path: str,
    source_url: str,
) -> None:
    from core.runtime.db import (
        _ensure_channel_attachments_table,
        connect,
        store_channel_attachment,
    )
    with connect() as conn:
        _ensure_channel_attachments_table(conn)
        store_channel_attachment(
            conn=conn,
            attachment_id=attachment_id,
            session_id=session_id,
            channel_type=channel_type,
            filename=filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            local_path=local_path,
            source_url=source_url,
        )
        conn.commit()


def _db_get(attachment_id: str) -> dict | None:
    from core.runtime.db import (
        _ensure_channel_attachments_table,
        connect,
        get_channel_attachment,
    )
    with connect() as conn:
        _ensure_channel_attachments_table(conn)
        return get_channel_attachment(conn=conn, attachment_id=attachment_id)


def _db_list(session_id: str, limit: int) -> list[dict]:
    from core.runtime.db import (
        _ensure_channel_attachments_table,
        connect,
        list_channel_attachments,
    )
    with connect() as conn:
        _ensure_channel_attachments_table(conn)
        return list_channel_attachments(conn=conn, session_id=session_id, limit=limit)


def _call_vision(image_b64: str, *, model: str, prompt: str | None = None) -> str:
    from core.services.visual_memory import _describe_via_ollama
    return _describe_via_ollama(image_b64, model=model, prompt=prompt)


def _vision_model() -> str:
    try:
        from core.services.visual_memory import _DEFAULT_MODEL
        return _DEFAULT_MODEL
    except Exception:
        return "qwen2.5vl:7b"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def download_and_store(
    *,
    url: str,
    filename: str,
    mime_type: str,
    size_bytes: int,
    session_id: str,
    channel_type: str,
    http_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Download file from URL and persist to uploads/ + DB.

    Returns {"status": "ok", "attachment_id": str, "local_path": str}
         or {"status": "error", "reason": str}
    """
    if size_bytes > MAX_SIZE_BYTES:
        return {"status": "error", "reason": "too_large", "size_bytes": size_bytes}

    attachment_id = str(uuid.uuid4())
    dest_dir = _UPLOAD_ROOT / session_id
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning("attachment_service: mkdir failed: %s", exc)
        return {"status": "error", "reason": "disk_error"}

    safe_filename = Path(filename).name or "file"
    local_path = dest_dir / f"{attachment_id}_{safe_filename}"

    try:
        data = _http_download(url, http_headers)
    except Exception as exc:
        logger.warning("attachment_service: download failed for %s: %s", url, exc)
        return {"status": "error", "reason": "download_failed"}

    try:
        local_path.write_bytes(data)
    except OSError as exc:
        logger.warning("attachment_service: write failed: %s", exc)
        return {"status": "error", "reason": "disk_error"}

    if not mime_type:
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    try:
        _db_store(
            attachment_id=attachment_id,
            session_id=session_id,
            channel_type=channel_type,
            filename=safe_filename,
            mime_type=mime_type,
            size_bytes=len(data),
            local_path=str(local_path),
            source_url=url,
        )
    except Exception as exc:
        logger.warning("attachment_service: db store failed: %s", exc)

    return {
        "status": "ok",
        "attachment_id": attachment_id,
        "local_path": str(local_path),
    }


def get_attachment(attachment_id: str) -> dict | None:
    """Return attachment metadata dict, or None if not found."""
    try:
        return _db_get(attachment_id)
    except Exception:
        return None


def list_attachments(session_id: str, limit: int = 20) -> list[dict]:
    """Return recent attachments for session, newest first."""
    try:
        return _db_list(session_id, limit)
    except Exception:
        return []


def read_attachment_content(attachment_id: str) -> dict[str, Any]:
    """Read attachment content for Jarvis.

    image/*        → vision model description
    text/*         → file text (truncated at 8000 chars)
    application/pdf → first 8000 chars via text extraction
    other          → metadata + hex preview
    """
    row = _db_get(attachment_id)
    if row is None:
        return {"status": "error", "reason": "not-found"}

    mime = str(row.get("mime_type") or "")
    local_path = str(row.get("local_path") or "")
    filename = str(row.get("filename") or "")

    if mime.startswith("image/"):
        try:
            data = Path(local_path).read_bytes()
            b64 = base64.b64encode(data).decode("ascii")
            model = _vision_model()
            description = _call_vision(
                b64,
                model=model,
                prompt="Beskriv indholdet af dette billede kortfattet på dansk.",
            )
            return {"status": "ok", "type": "image", "content": description, "filename": filename}
        except Exception as exc:
            logger.warning("attachment_service: vision failed for %s: %s", attachment_id, exc)
            return {
                "status": "ok",
                "type": "image",
                "content": f"[Billede: {filename} — vision fejlede: {exc}]",
                "filename": filename,
            }

    if mime.startswith("text/") or mime == "application/json":
        try:
            text = Path(local_path).read_text(encoding="utf-8", errors="replace")
            return {
                "status": "ok",
                "type": "text",
                "content": text[:_MAX_TEXT_CHARS],
                "filename": filename,
            }
        except Exception as exc:
            return {"status": "error", "reason": f"read-failed: {exc}"}

    if mime == "application/pdf":
        try:
            data = Path(local_path).read_bytes()
            # Extract printable ASCII as a rough text approximation
            text = data.decode("latin-1", errors="replace")
            printable = "".join(c if c.isprintable() or c in "\n\t" else " " for c in text)
            return {
                "status": "ok",
                "type": "pdf",
                "content": printable[:_MAX_TEXT_CHARS],
                "filename": filename,
            }
        except Exception as exc:
            return {"status": "error", "reason": f"read-failed: {exc}"}

    # Fallback: metadata + hex preview
    try:
        data = Path(local_path).read_bytes()
        preview = data[:64].hex()
    except Exception:
        preview = ""
    return {
        "status": "ok",
        "type": "binary",
        "content": (
            f"Fil: {filename}\nType: {mime}\n"
            f"Størrelse: {row.get('size_bytes', 0)} bytes\n"
            f"Hex preview: {preview}"
        ),
        "filename": filename,
    }


def validate_send_path(path: str) -> tuple[bool, str]:
    """Return (ok, error_message) for outbound file send.

    Checks: path within allowed roots, file exists and readable, under 50 MB.
    """
    p = Path(path).resolve()
    allowed = any(
        str(p).startswith(str(root.resolve()))
        for root in _ALLOWED_SEND_ROOTS
    )
    if not allowed:
        return False, "not-allowed"
    if not p.exists():
        return False, "not-found"
    if not p.is_file():
        return False, "not-a-file"
    size = p.stat().st_size
    if size > MAX_SIZE_BYTES:
        return False, f"file-too-large:{size}"
    return True, ""
```

- [ ] **Step 4: Run tests — expect pass**

```bash
conda activate ai && python -m pytest tests/test_attachment_service.py -v
```

Expected: 11 tests PASS

- [ ] **Step 5: Commit**

```bash
git add core/services/attachment_service.py tests/test_attachment_service.py
git commit -m "feat(attachments): add attachment_service with download, store, read, validate"
```

---

## Task 3: Discord gateway — inbound attachments + outbound file send

**Files:**
- Modify: `core/services/discord_gateway.py`
- Test: `tests/test_discord_gateway_attachments.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_discord_gateway_attachments.py`:

```python
# tests/test_discord_gateway_attachments.py
from __future__ import annotations
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_attachment(filename="photo.jpg", content_type="image/jpeg", size=1000,
                           url="https://cdn.discord.com/photo.jpg"):
    class FakeAttachment:
        pass
    a = FakeAttachment()
    a.filename = filename
    a.content_type = content_type
    a.size = size
    a.url = url
    return a


# ---------------------------------------------------------------------------
# _build_attachment_prefix
# ---------------------------------------------------------------------------

def test_build_attachment_prefix_ok(monkeypatch):
    import core.services.discord_gateway as gw
    monkeypatch.setattr(
        "core.services.discord_gateway._download_attachment",
        lambda att, session_id: {"status": "ok", "attachment_id": "abc-123"},
    )
    att = _make_fake_attachment()
    prefix = gw._build_attachment_prefix([att], session_id="sess-1")
    assert "abc-123" in prefix
    assert "photo.jpg" in prefix
    assert "[Fil modtaget:" in prefix


def test_build_attachment_prefix_download_failure(monkeypatch):
    import core.services.discord_gateway as gw
    monkeypatch.setattr(
        "core.services.discord_gateway._download_attachment",
        lambda att, session_id: {"status": "error", "reason": "download_failed"},
    )
    att = _make_fake_attachment()
    prefix = gw._build_attachment_prefix([att], session_id="sess-1")
    assert "[Fil kunne ikke hentes:" in prefix
    assert "photo.jpg" in prefix


def test_build_attachment_prefix_empty_list():
    import core.services.discord_gateway as gw
    assert gw._build_attachment_prefix([], session_id="sess-1") == ""


# ---------------------------------------------------------------------------
# send_discord_file
# ---------------------------------------------------------------------------

def test_send_discord_file_validates_path(monkeypatch):
    import core.services.discord_gateway as gw
    monkeypatch.setattr(
        "core.services.discord_gateway._validate_send_path",
        lambda path: (False, "not-allowed"),
    )
    result = gw.send_discord_file(channel_id=123, text="hi", file_path="/etc/passwd")
    assert result["status"] == "error"
    assert "not-allowed" in result["reason"]


def test_send_discord_file_queues_on_valid_path(monkeypatch, tmp_path):
    import core.services.discord_gateway as gw
    f = tmp_path / "file.jpg"
    f.write_bytes(b"data")
    monkeypatch.setattr(
        "core.services.discord_gateway._validate_send_path",
        lambda path: (True, ""),
    )
    queued = []
    monkeypatch.setattr(gw._outbound_queue, "put_nowait", lambda item: queued.append(item))
    result = gw.send_discord_file(channel_id=456, text="here", file_path=str(f))
    assert result["status"] == "queued"
    assert len(queued) == 1
    assert queued[0]["file_path"] == str(f)
    assert queued[0]["channel_id"] == 456
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate ai && python -m pytest tests/test_discord_gateway_attachments.py -v
```

Expected: FAIL — `cannot import name '_build_attachment_prefix'`

- [ ] **Step 3: Add attachment helpers to `discord_gateway.py`**

At the top of `core/services/discord_gateway.py`, after the existing imports, add:

```python
def _download_attachment(attachment: Any, session_id: str) -> dict:
    """Download a single discord.Attachment to attachment_service."""
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
    """Build content prefix lines for all attachments in a message."""
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
    ok, err = _validate_send_path(file_path)
    if not ok:
        return {"status": "error", "reason": err}
    _outbound_queue.put_nowait({"channel_id": channel_id, "text": text, "file_path": file_path})
    return {"status": "queued", "channel_id": channel_id, "file_path": file_path}
```

- [ ] **Step 4: Wire attachment prefix into `on_message()`**

In `discord_gateway.py`, find the line (around line 332):
```python
            content = content_raw.strip()
            if not content:
```

Replace with:

```python
            # Extract file attachments and build content prefix
            attachment_prefix = ""
            try:
                if message.attachments:
                    attachment_prefix = _build_attachment_prefix(
                        list(message.attachments), session_id=_get_or_create_discord_session(
                            message.channel.id, is_dm, owner_discord_id, author_id=author_id_str,
                        )
                    )
            except Exception as _att_exc:
                logger.warning("discord on_message: attachment handling failed: %s", _att_exc)

            content = (attachment_prefix + content_raw).strip()
            if not content:
```

- [ ] **Step 5: Extend `_send_outbound_loop()` to handle file_path**

In `discord_gateway.py`, find `_send_outbound_loop()`. Replace the queue get and send logic:

```python
async def _send_outbound_loop() -> None:
    """Asyncio coroutine that drains the outbound queue and sends to Discord."""
    while _thread_running:
        try:
            item = _outbound_queue.get_nowait()
        except queue.Empty:
            await asyncio.sleep(0.2)
            continue

        # Support both old tuple format and new dict format
        if isinstance(item, tuple):
            channel_id, text = item
            file_path = None
        else:
            channel_id = item["channel_id"]
            text = item.get("text", "")
            file_path = item.get("file_path")

        with _typing_lock:
            _typing_channels.discard(channel_id)
        logger.info("discord_outbound: dequeued channel=%s len=%d file=%s", channel_id, len(text), file_path)
        try:
            if _client:
                channel = _client.get_channel(channel_id)
                if channel is None:
                    channel = await _client.fetch_channel(channel_id)
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
                from core.eventbus.bus import event_bus
                event_bus.publish("discord.message_sent", {
                    "channel_id": str(channel_id),
                    "length": len(text),
                })
            else:
                logger.warning("discord_outbound: _client is None, dropping message")
        except Exception as exc:
            logger.warning("discord_gateway: failed to send to channel %s: %s", channel_id, exc)
```

- [ ] **Step 6: Run tests — expect pass**

```bash
conda activate ai && python -m pytest tests/test_discord_gateway_attachments.py -v
```

Expected: 5 tests PASS

- [ ] **Step 7: Verify syntax**

```bash
conda activate ai && python -m compileall core/services/discord_gateway.py -q
```

Expected: no output (no errors)

- [ ] **Step 8: Commit**

```bash
git add core/services/discord_gateway.py tests/test_discord_gateway_attachments.py
git commit -m "feat(discord): extract inbound attachments + send_discord_file outbound"
```

---

## Task 4: Telegram gateway — inbound media + outbound file send

**Files:**
- Modify: `core/services/telegram_gateway.py`
- Test: `tests/test_telegram_gateway_attachments.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_telegram_gateway_attachments.py`:

```python
# tests/test_telegram_gateway_attachments.py
from __future__ import annotations
import pytest


# ---------------------------------------------------------------------------
# _resolve_telegram_file_url
# ---------------------------------------------------------------------------

def test_resolve_telegram_file_url(monkeypatch):
    import core.services.telegram_gateway as gw

    def fake_api_get(token, method, payload):
        return {"ok": True, "result": {"file_path": "photos/file_42.jpg"}}

    monkeypatch.setattr(gw, "_api_get", fake_api_get)
    url = gw._resolve_telegram_file_url(token="tok123", file_id="FILE_ID_X")
    assert url == "https://api.telegram.org/file/bottok123/photos/file_42.jpg"


def test_resolve_telegram_file_url_api_failure(monkeypatch):
    import core.services.telegram_gateway as gw

    monkeypatch.setattr(gw, "_api_get", lambda t, m, p: {"ok": False})
    result = gw._resolve_telegram_file_url(token="tok", file_id="bad")
    assert result is None


# ---------------------------------------------------------------------------
# _extract_telegram_media
# ---------------------------------------------------------------------------

def test_extract_telegram_media_photo():
    import core.services.telegram_gateway as gw
    msg = {
        "photo": [
            {"file_id": "small", "file_size": 100},
            {"file_id": "large", "file_size": 5000},
        ]
    }
    items = gw._extract_telegram_media(msg)
    assert len(items) == 1
    assert items[0]["file_id"] == "large"
    assert items[0]["mime_type"] == "image/jpeg"
    assert items[0]["filename"] == "photo.jpg"


def test_extract_telegram_media_document():
    import core.services.telegram_gateway as gw
    msg = {
        "document": {
            "file_id": "doc123",
            "file_name": "report.pdf",
            "mime_type": "application/pdf",
            "file_size": 50000,
        }
    }
    items = gw._extract_telegram_media(msg)
    assert len(items) == 1
    assert items[0]["file_id"] == "doc123"
    assert items[0]["filename"] == "report.pdf"
    assert items[0]["mime_type"] == "application/pdf"


def test_extract_telegram_media_text_only():
    import core.services.telegram_gateway as gw
    msg = {"text": "hello world"}
    assert gw._extract_telegram_media(msg) == []


# ---------------------------------------------------------------------------
# _build_telegram_attachment_prefix
# ---------------------------------------------------------------------------

def test_build_telegram_attachment_prefix_ok(monkeypatch):
    import core.services.telegram_gateway as gw

    monkeypatch.setattr(gw, "_resolve_telegram_file_url",
                        lambda token, file_id: "https://api.telegram.org/file/botX/f.jpg")
    monkeypatch.setattr(
        "core.services.telegram_gateway._download_tg_attachment",
        lambda url, filename, mime, size, session_id: {
            "status": "ok", "attachment_id": "tg-abc"
        },
    )
    items = [{"file_id": "F1", "filename": "pic.jpg", "mime_type": "image/jpeg", "file_size": 1000}]
    prefix = gw._build_telegram_attachment_prefix(items, token="tok", session_id="sess-t")
    assert "[Fil modtaget:" in prefix
    assert "tg-abc" in prefix
    assert "pic.jpg" in prefix


# ---------------------------------------------------------------------------
# send_telegram_file
# ---------------------------------------------------------------------------

def test_send_telegram_file_rejects_invalid_path(monkeypatch):
    import core.services.telegram_gateway as gw
    monkeypatch.setattr(
        "core.services.telegram_gateway._validate_send_path",
        lambda path: (False, "not-allowed"),
    )
    result = gw.send_telegram_file(text="hi", file_path="/etc/passwd")
    assert result["status"] == "error"


def test_send_telegram_file_sends_photo(monkeypatch, tmp_path):
    import core.services.telegram_gateway as gw
    f = tmp_path / "pic.jpg"
    f.write_bytes(b"\xff\xd8\xff")
    monkeypatch.setattr(
        "core.services.telegram_gateway._validate_send_path",
        lambda path: (True, ""),
    )
    sent = {}
    def fake_post(token, method, data, files):
        sent["method"] = method
        sent["files"] = list(files.keys())
        return {"ok": True, "result": {"message_id": 99}}
    monkeypatch.setattr(gw, "_api_post_file", fake_post)
    monkeypatch.setattr(gw, "_load_config", lambda: {"token": "T", "chat_id": "123"})
    result = gw.send_telegram_file(text="here", file_path=str(f))
    assert result["status"] == "sent"
    assert sent["method"] == "sendPhoto"
    assert "photo" in sent["files"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate ai && python -m pytest tests/test_telegram_gateway_attachments.py -v
```

Expected: FAIL — `cannot import name '_resolve_telegram_file_url'`

- [ ] **Step 3: Add attachment helpers to `telegram_gateway.py`**

After the existing `_api()` function in `telegram_gateway.py`, add:

```python
import mimetypes as _mimetypes


def _api_get(token: str, method: str, payload: dict) -> dict:
    """HTTP GET to Telegram Bot API (for getFile)."""
    import urllib.parse
    params = urllib.parse.urlencode(payload)
    url = f"https://api.telegram.org/bot{token}/{method}?{params}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _api_post_file(token: str, method: str, data: dict, files: dict) -> dict:
    """HTTP POST with multipart/form-data to Telegram Bot API (for sendPhoto etc.)."""
    import io
    import http.client
    import urllib.parse

    boundary = "---JarvisBoundary"
    body_parts = []
    for key, value in data.items():
        body_parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n".encode()
        )
    for field, (filename, content, mime) in files.items():
        body_parts.append(
            (
                f"--{boundary}\r\n"
                f"Content-Disposition: form-data; name=\"{field}\"; filename=\"{filename}\"\r\n"
                f"Content-Type: {mime}\r\n\r\n"
            ).encode() + content + b"\r\n"
        )
    body_parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(body_parts)

    parsed = urllib.parse.urlparse(f"https://api.telegram.org/bot{token}/{method}")
    conn = http.client.HTTPSConnection(parsed.netloc, timeout=60)
    conn.request(
        "POST", parsed.path,
        body=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    resp = conn.getresponse()
    return json.loads(resp.read())


def _resolve_telegram_file_url(*, token: str, file_id: str) -> str | None:
    """Call getFile to get download URL for a Telegram file_id."""
    try:
        result = _api_get(token, "getFile", {"file_id": file_id})
        if not result.get("ok"):
            return None
        file_path = result.get("result", {}).get("file_path")
        if not file_path:
            return None
        return f"https://api.telegram.org/file/bot{token}/{file_path}"
    except Exception as exc:
        logger.warning("telegram_gateway: getFile failed for %s: %s", file_id, exc)
        return None


def _extract_telegram_media(msg: dict) -> list[dict]:
    """Extract media items from a Telegram message dict.

    Returns list of dicts with: file_id, filename, mime_type, file_size.
    """
    items = []

    # Photo: list of sizes — use largest
    if "photo" in msg:
        photos = msg["photo"]
        if photos:
            largest = photos[-1]
            size = largest.get("file_size", 0)
            if size <= 20 * 1024 * 1024:
                items.append({
                    "file_id": largest["file_id"],
                    "filename": "photo.jpg",
                    "mime_type": "image/jpeg",
                    "file_size": size,
                })

    for media_type, default_mime, default_name in [
        ("document", "", ""),
        ("audio", "audio/mpeg", "audio.mp3"),
        ("video", "video/mp4", "video.mp4"),
        ("voice", "audio/ogg", "voice.ogg"),
        ("sticker", "image/webp", "sticker.webp"),
    ]:
        if media_type in msg:
            m = msg[media_type]
            size = m.get("file_size", 0)
            if size > 20 * 1024 * 1024:
                continue
            items.append({
                "file_id": m["file_id"],
                "filename": m.get("file_name") or default_name,
                "mime_type": m.get("mime_type") or default_mime,
                "file_size": size,
            })

    return items


def _download_tg_attachment(
    url: str, filename: str, mime: str, size: int, session_id: str
) -> dict:
    from core.services.attachment_service import download_and_store
    return download_and_store(
        url=url,
        filename=filename,
        mime_type=mime,
        size_bytes=size,
        session_id=session_id,
        channel_type="telegram",
    )


def _build_telegram_attachment_prefix(
    media_items: list[dict], *, token: str, session_id: str
) -> str:
    if not media_items:
        return ""
    lines = []
    for item in media_items:
        url = _resolve_telegram_file_url(token=token, file_id=item["file_id"])
        if url is None:
            lines.append(f"[Fil kunne ikke hentes: {item['filename']} — getFile fejlede]")
            continue
        result = _download_tg_attachment(
            url, item["filename"], item["mime_type"], item["file_size"], session_id
        )
        if result["status"] == "ok":
            aid = result["attachment_id"]
            size_kb = round(item["file_size"] / 1024, 1)
            lines.append(
                f"[Fil modtaget: {item['filename']} ({item['mime_type']}, {size_kb} KB) — id: {aid}]"
            )
        else:
            lines.append(
                f"[Fil kunne ikke hentes: {item['filename']} — {result.get('reason', '?')}]"
            )
    return "\n".join(lines) + "\n"


def _validate_send_path(path: str) -> tuple[bool, str]:
    from core.services.attachment_service import validate_send_path
    return validate_send_path(path)


def send_telegram_file(text: str, file_path: str, chat_id: str | int | None = None) -> dict:
    """Send a file to owner (or chat_id) via Telegram."""
    ok, err = _validate_send_path(file_path)
    if not ok:
        return {"status": "error", "reason": err}

    cfg = _load_config()
    if not cfg:
        return {"status": "error", "reason": "telegram-not-configured"}

    target = str(chat_id) if chat_id else cfg["chat_id"]
    mime = _mimetypes.guess_type(file_path)[0] or "application/octet-stream"

    if mime.startswith("image/"):
        method, field = "sendPhoto", "photo"
    elif mime.startswith("audio/"):
        method, field = "sendAudio", "audio"
    elif mime.startswith("video/"):
        method, field = "sendVideo", "video"
    else:
        method, field = "sendDocument", "document"

    filename = Path(file_path).name
    try:
        data = Path(file_path).read_bytes()
        result = _api_post_file(
            cfg["token"],
            method,
            data={"chat_id": target, "caption": text or ""},
            files={field: (filename, data, mime)},
        )
        if result.get("ok"):
            return {"status": "sent", "method": method, "message_id": result.get("result", {}).get("message_id")}
        return {"status": "error", "reason": str(result.get("description", "unknown"))}
    except Exception as exc:
        return {"status": "error", "reason": str(exc)}
```

- [ ] **Step 4: Wire media extraction into `_poll_loop()`**

In `telegram_gateway.py`, find this section in `_poll_loop()`:

```python
                chat_id = msg.get("chat", {}).get("id")
                text = (msg.get("text") or "").strip()

                # Only accept messages from owner
                if str(chat_id) != owner_chat_id or not text:
                    continue
```

Replace with:

```python
                chat_id = msg.get("chat", {}).get("id")
                text = (msg.get("text") or "").strip()

                # Only accept messages from owner
                if str(chat_id) != owner_chat_id:
                    continue

                # Extract media attachments and build prefix
                attachment_prefix = ""
                try:
                    media_items = _extract_telegram_media(msg)
                    if media_items:
                        session_id_for_att = _get_or_create_session(chat_id)
                        attachment_prefix = _build_telegram_attachment_prefix(
                            media_items, token=token, session_id=session_id_for_att
                        )
                except Exception as _att_exc:
                    logger.warning("telegram_gateway: attachment handling failed: %s", _att_exc)

                content = (attachment_prefix + text).strip()
                if not content:
                    continue
                text = content  # use enriched content as the message text
```

Also add `from pathlib import Path` to the imports if not already present.

- [ ] **Step 5: Run tests — expect pass**

```bash
conda activate ai && python -m pytest tests/test_telegram_gateway_attachments.py -v
```

Expected: 8 tests PASS

- [ ] **Step 6: Verify syntax**

```bash
conda activate ai && python -m compileall core/services/telegram_gateway.py -q
```

- [ ] **Step 7: Commit**

```bash
git add core/services/telegram_gateway.py tests/test_telegram_gateway_attachments.py
git commit -m "feat(telegram): extract inbound media + send_telegram_file outbound"
```

---

## Task 5: Tools — read_attachment, list_attachments, extend discord/telegram sends

**Files:**
- Modify: `core/tools/simple_tools.py`
- Test: `tests/test_simple_tools_attachments.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_simple_tools_attachments.py`:

```python
# tests/test_simple_tools_attachments.py
from __future__ import annotations
import pytest


def _dispatch(name, args):
    from core.tools.simple_tools import dispatch_tool
    return dispatch_tool(name, args)


# ---------------------------------------------------------------------------
# read_attachment
# ---------------------------------------------------------------------------

def test_read_attachment_unknown_id(monkeypatch):
    import core.services.attachment_service as svc
    monkeypatch.setattr(svc, "_db_get", lambda aid: None)
    result = _dispatch("read_attachment", {"attachment_id": "unknown"})
    assert result["status"] == "error"


def test_read_attachment_text_file(tmp_path, monkeypatch):
    import core.services.attachment_service as svc
    f = tmp_path / "note.txt"
    f.write_text("hello")
    row = {
        "attachment_id": "t1", "filename": "note.txt", "mime_type": "text/plain",
        "local_path": str(f), "session_id": "s", "channel_type": "discord",
        "size_bytes": 5, "source_url": "", "created_at": "",
    }
    monkeypatch.setattr(svc, "_db_get", lambda aid: row)
    result = _dispatch("read_attachment", {"attachment_id": "t1"})
    assert result["status"] == "ok"
    assert "hello" in result["content"]


def test_read_attachment_image_calls_vision(tmp_path, monkeypatch):
    import core.services.attachment_service as svc
    f = tmp_path / "pic.jpg"
    f.write_bytes(b"\xff\xd8\xff")
    row = {
        "attachment_id": "i1", "filename": "pic.jpg", "mime_type": "image/jpeg",
        "local_path": str(f), "session_id": "s", "channel_type": "discord",
        "size_bytes": 3, "source_url": "", "created_at": "",
    }
    monkeypatch.setattr(svc, "_db_get", lambda aid: row)
    monkeypatch.setattr(svc, "_call_vision", lambda b64, model, prompt=None: "nice sunset")
    result = _dispatch("read_attachment", {"attachment_id": "i1"})
    assert result["status"] == "ok"
    assert "nice sunset" in result["content"]


# ---------------------------------------------------------------------------
# list_attachments
# ---------------------------------------------------------------------------

def test_list_attachments_returns_list(monkeypatch):
    import core.services.attachment_service as svc
    fake = [{"attachment_id": "x1", "filename": "a.jpg", "session_id": "s",
             "channel_type": "discord", "mime_type": "image/jpeg",
             "size_bytes": 1, "local_path": "", "source_url": "", "created_at": ""}]
    monkeypatch.setattr(svc, "_db_list", lambda session_id, limit: fake)
    result = _dispatch("list_attachments", {"session_id": "s"})
    assert result["status"] == "ok"
    assert len(result["attachments"]) == 1


# ---------------------------------------------------------------------------
# discord_channel send with file_path
# ---------------------------------------------------------------------------

def test_discord_channel_send_file_validates_path(monkeypatch):
    import core.services.discord_gateway as gw
    monkeypatch.setattr(gw, "_validate_send_path", lambda p: (False, "not-allowed"))
    result = _dispatch("discord_channel", {
        "action": "send", "channel_id": "123456",
        "content": "hi", "file_path": "/etc/passwd",
    })
    assert result["status"] == "error"
    assert "not-allowed" in str(result)


# ---------------------------------------------------------------------------
# send_telegram_message with file_path
# ---------------------------------------------------------------------------

def test_send_telegram_message_with_file_path(monkeypatch, tmp_path):
    import core.services.telegram_gateway as gw
    f = tmp_path / "img.jpg"
    f.write_bytes(b"\xff\xd8\xff")
    monkeypatch.setattr(gw, "_validate_send_path", lambda p: (True, ""))
    monkeypatch.setattr(gw, "_load_config", lambda: {"token": "T", "chat_id": "123"})
    monkeypatch.setattr(gw, "_api_post_file",
                        lambda tok, method, data, files: {"ok": True, "result": {"message_id": 5}})
    result = _dispatch("send_telegram_message", {"content": "here", "file_path": str(f)})
    assert result["status"] == "ok"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate ai && python -m pytest tests/test_simple_tools_attachments.py -v
```

Expected: FAIL — `dispatch_tool` does not have `read_attachment` or `list_attachments`

- [ ] **Step 3: Add tool definitions to `TOOLS` list in `simple_tools.py`**

After the `web_scrape` tool definition (after line ~358), add:

```python
    {
        "type": "function",
        "function": {
            "name": "read_attachment",
            "description": (
                "Læs indholdet af en modtaget fil (billede, dokument, tekstfil). "
                "Billeder analyseres via vision-model og returnerer en dansk beskrivelse. "
                "Tekstfiler returneres direkte. Bruges med attachment_id fra "
                "'[Fil modtaget: ...]' beskeder."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "attachment_id": {
                        "type": "string",
                        "description": "UUID fra [Fil modtaget: navn — id: UUID] besked",
                    },
                },
                "required": ["attachment_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_attachments",
            "description": "Vis liste over filer modtaget i den aktuelle session.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID (valgfri — bruges aktuel session hvis tom)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max antal resultater (default 10)",
                    },
                },
                "required": [],
            },
        },
    },
```

- [ ] **Step 4: Add executor functions in `simple_tools.py`**

After `_exec_web_scrape` (after line ~2322), add:

```python
def _exec_read_attachment(args: dict[str, Any]) -> dict[str, Any]:
    attachment_id = str(args.get("attachment_id") or "").strip()
    if not attachment_id:
        return {"status": "error", "reason": "attachment_id is required"}
    from core.services.attachment_service import read_attachment_content
    return read_attachment_content(attachment_id)


def _exec_list_attachments(args: dict[str, Any]) -> dict[str, Any]:
    session_id = str(args.get("session_id") or "").strip()
    limit = int(args.get("limit") or 10)
    from core.services.attachment_service import list_attachments
    rows = list_attachments(session_id, limit=limit)
    return {"status": "ok", "attachments": rows, "count": len(rows)}
```

- [ ] **Step 5: Add to dispatch dict in `simple_tools.py`**

In the `_TOOL_DISPATCH` dict (around line 4728), add after `"web_scrape"`:

```python
    "read_attachment": _exec_read_attachment,
    "list_attachments": _exec_list_attachments,
```

- [ ] **Step 6: Extend `_exec_send_telegram_message` with optional `file_path`**

Replace the existing `_exec_send_telegram_message` function:

```python
def _exec_send_telegram_message(args: dict[str, Any]) -> dict[str, Any]:
    content = str(args.get("content") or "").strip()
    file_path = str(args.get("file_path") or "").strip()
    if file_path:
        try:
            from core.services.telegram_gateway import send_telegram_file
            result = send_telegram_file(text=content, file_path=file_path)
            if result["status"] == "sent":
                return {"status": "ok", "text": f"Telegram fil sendt (id={result.get('message_id')})"}
            return {"status": "error", "text": f"Telegram fil fejlede: {result.get('reason')}"}
        except Exception as exc:
            return {"status": "error", "text": f"Telegram fil fejl: {exc}"}
    if not content:
        return {"status": "error", "text": "No content provided."}
    try:
        from core.services.telegram_gateway import send_message
        result = send_message(content)
        if result["status"] == "sent":
            return {"status": "ok", "text": f"Telegram message sent (id={result.get('message_id')})"}
        return {"status": "error", "text": f"Telegram failed: {result.get('reason')}"}
    except Exception as exc:
        return {"status": "error", "text": f"Telegram error: {exc}"}
```

Also add `"file_path"` parameter to the `send_telegram_message` tool definition in the `TOOLS` list. Find the `send_telegram_message` tool definition and add:

```python
                    "file_path": {
                        "type": "string",
                        "description": "Valgfri sti til fil der skal sendes (fra uploads/ eller workspaces/)",
                    },
```

- [ ] **Step 7: Extend `discord_channel` send action with `file_path`**

In `_exec_discord_channel`, find the `elif action == "send":` block. After the existing content check, add file_path handling before the `async def _do_send()` definition:

```python
        file_path = str(args.get("file_path") or "").strip()
        if file_path:
            from core.services.discord_gateway import send_discord_file
            return send_discord_file(
                channel_id=channel_id, text=content, file_path=file_path
            )
```

Also add `"file_path"` to the `discord_channel` tool definition parameters:

```python
                    "file_path": {
                        "type": "string",
                        "description": "Valgfri sti til fil der skal sendes (fra uploads/ eller workspaces/)",
                    },
```

- [ ] **Step 8: Run all attachment tests**

```bash
conda activate ai && python -m pytest tests/test_simple_tools_attachments.py tests/test_attachment_service.py tests/test_channel_attachments_db.py tests/test_discord_gateway_attachments.py tests/test_telegram_gateway_attachments.py -v
```

Expected: all tests PASS

- [ ] **Step 9: Verify syntax**

```bash
conda activate ai && python -m compileall core/tools/simple_tools.py -q
```

- [ ] **Step 10: Commit**

```bash
git add core/tools/simple_tools.py tests/test_simple_tools_attachments.py
git commit -m "feat(tools): add read_attachment + list_attachments; extend discord/telegram sends with file_path"
```

---

## Self-Review

**Spec coverage:**
- ✓ DB `channel_attachments` table — Task 1
- ✓ `attachment_service.py` with `download_and_store`, `get_attachment`, `list_attachments`, `read_attachment_content`, `validate_send_path` — Task 2
- ✓ Discord inbound attachment extraction — Task 3
- ✓ Discord outbound `send_discord_file` — Task 3
- ✓ Telegram inbound media extraction (photo/document/audio/video/voice/sticker) — Task 4
- ✓ Telegram `getFile` URL resolution — Task 4
- ✓ Telegram outbound `send_telegram_file` with mime routing — Task 4
- ✓ `read_attachment` tool — Task 5
- ✓ `list_attachments` tool — Task 5
- ✓ Extended `discord_channel` send with `file_path` — Task 5
- ✓ Extended `send_telegram_message` with `file_path` — Task 5
- ✓ Path whitelist security — `validate_send_path` in attachment_service
- ✓ Size limit 50 MB — `MAX_SIZE_BYTES` check in `download_and_store`
- ✓ Telegram 20 MB getFile limit — skipped in `_extract_telegram_media` with `size > 20 MB`
- ✓ Error messages in Danish content prefix — `[Fil modtaget:]` / `[Fil kunne ikke hentes:]`

**Type consistency check:**
- `download_and_store` returns `{"status": "ok", "attachment_id": str, "local_path": str}` — used consistently in Task 3 and 4 gateway helpers ✓
- `validate_send_path` returns `tuple[bool, str]` — used in Task 3 `send_discord_file`, Task 4 `send_telegram_file`, Task 5 tool executors ✓
- `_db_get` / `_db_list` are monkeypatched in tests matching the real signature ✓
- `send_discord_file` returns `{"status": "queued", ...}` or `{"status": "error", ...}` — consistent with tool executor check ✓
