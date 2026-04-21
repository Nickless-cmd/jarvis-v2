# File & Image Attachments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users drag/drop images (max 25) and archive files (zip/tar/rar, max 200 MB) into the webchat composer; Jarvis sees uploaded file paths in context and can analyze images and list/extract archives.

**Architecture:** Eager upload — files POST to `/attachments/upload` immediately on select/drop, returning an `attachment_id`. On send, IDs are bundled with the chat message; the backend resolves paths and prepends a context block to the run. Images appear as clickable thumbnails above user message bubbles in the transcript (fullscreen on click). Archives appear as icon pills.

**Tech Stack:** FastAPI `UploadFile` + `Form` (upload endpoint), `FileResponse` (serve endpoint), Python `zipfile`/`tarfile` (archive listing/extraction), React state + `URL.createObjectURL` (composer tray previews), same CSS overlay pattern as existing Mermaid diagrams.

---

## File Map

| Action | Path | Purpose |
|--------|------|---------|
| Create | `apps/api/jarvis_api/routes/attachments.py` | Upload + serve endpoints, in-memory registry |
| Modify | `apps/api/jarvis_api/app.py` | Register attachments router |
| Modify | `apps/api/jarvis_api/routes/chat.py` | Add `attachment_ids` to request, inject context |
| Modify | `core/tools/simple_tools.py` | Add `read_archive` tool |
| Modify | `apps/ui/src/components/chat/Composer.jsx` | Attachment tray, drag/drop, eager upload |
| Modify | `apps/ui/src/lib/adapters.js` | Add `uploadAttachment()`, add `attachment_ids` to `streamMessage` |
| Modify | `apps/ui/src/app/ChatPage.jsx` | Pass `sessionId` + forward opts from `onSend` |
| Modify | `apps/ui/src/app/useUnifiedShell.js` | Accept `attachmentMeta` in `handleSend`, store on user message |
| Modify | `apps/ui/src/components/chat/ChatTranscript.jsx` | Render attachment thumbnails + lightbox |
| Modify | `apps/ui/src/styles/global.css` | Styles for tray, thumbnails, lightbox |
| Create | `tests/test_read_archive.py` | Tests for archive tool |
| Create | `tests/test_attachments_api.py` | Tests for upload/serve endpoints |

---

### Task 1: `read_archive` tool

**Files:**
- Create: `tests/test_read_archive.py`
- Modify: `core/tools/simple_tools.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_read_archive.py`:

```python
"""Tests for the read_archive tool."""
from __future__ import annotations

import os
import tarfile
import zipfile
from pathlib import Path

import pytest


# Patch the allowed prefix so tests can use /tmp paths
@pytest.fixture(autouse=True)
def patch_home(monkeypatch, tmp_path):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)


def _make_zip(dest: Path, files: dict[str, str]) -> Path:
    zp = dest / "test.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return zp


def _make_tar_gz(dest: Path, files: dict[str, str]) -> Path:
    tp = dest / "test.tar.gz"
    with tarfile.open(tp, "w:gz") as tf:
        for name, content in files.items():
            import io
            data = content.encode()
            ti = tarfile.TarInfo(name=name)
            ti.size = len(data)
            tf.addfile(ti, io.BytesIO(data))
    return tp


def test_list_zip(tmp_path):
    from core.tools.simple_tools import _exec_read_archive
    zp = _make_zip(tmp_path / ".jarvis-v2", {"hello.txt": "hi", "sub/world.py": "x"})
    (tmp_path / ".jarvis-v2").mkdir(parents=True, exist_ok=True)
    zp = _make_zip(tmp_path / ".jarvis-v2", {"hello.txt": "hi", "sub/world.py": "x"})
    result = _exec_read_archive({"archive_path": str(zp)})
    assert result["status"] == "ok"
    assert result["count"] == 2
    assert "hello.txt" in result["file_list"]
    assert "sub/world.py" in result["file_list"]
    assert "extracted_to" not in result


def test_extract_zip(tmp_path):
    from core.tools.simple_tools import _exec_read_archive
    base = tmp_path / ".jarvis-v2"
    base.mkdir(parents=True, exist_ok=True)
    zp = _make_zip(base, {"readme.txt": "hello"})
    result = _exec_read_archive({"archive_path": str(zp), "extract": True})
    assert result["status"] == "ok"
    assert "extracted_to" in result
    extracted = Path(result["extracted_to"])
    assert (extracted / "readme.txt").exists()


def test_list_tar_gz(tmp_path):
    from core.tools.simple_tools import _exec_read_archive
    base = tmp_path / ".jarvis-v2"
    base.mkdir(parents=True, exist_ok=True)
    tp = _make_tar_gz(base, {"a.py": "print(1)", "b.txt": "hello"})
    result = _exec_read_archive({"archive_path": str(tp)})
    assert result["status"] == "ok"
    assert result["count"] == 2


def test_path_outside_jarvis_rejected(tmp_path):
    from core.tools.simple_tools import _exec_read_archive
    # /tmp is NOT inside ~/.jarvis-v2 (mocked as tmp_path)
    result = _exec_read_archive({"archive_path": "/etc/passwd"})
    assert result["status"] == "error"
    assert "jarvis" in result["error"].lower() or "~/.jarvis" in result["error"]


def test_missing_archive_path(tmp_path):
    from core.tools.simple_tools import _exec_read_archive
    result = _exec_read_archive({})
    assert result["status"] == "error"


def test_unsupported_format(tmp_path):
    from core.tools.simple_tools import _exec_read_archive
    base = tmp_path / ".jarvis-v2"
    base.mkdir(parents=True, exist_ok=True)
    f = base / "file.7z"
    f.write_bytes(b"x")
    result = _exec_read_archive({"archive_path": str(f)})
    assert result["status"] == "error"
    assert "Unsupported" in result["error"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_read_archive.py -v 2>&1 | head -40
```

Expected: FAIL with `ImportError` or `AttributeError` — `_exec_read_archive` does not exist yet.

- [ ] **Step 3: Implement `_exec_read_archive` in `core/tools/simple_tools.py`**

Add the function **before** `_exec_wolfram_query` (around line 1673). Insert after the blank line following `_exec_analyze_image`:

```python
def _exec_read_archive(args: dict[str, Any]) -> dict[str, Any]:
    """List or extract a zip / tar / rar archive.

    Security: only allows paths inside ~/.jarvis-v2/ to prevent path traversal.
    """
    archive_path = str(args.get("archive_path") or "").strip()
    if not archive_path:
        return {"error": "archive_path is required", "status": "error"}

    allowed_prefix = str((Path.home() / ".jarvis-v2").resolve())
    resolved = str(Path(archive_path).resolve())
    if not resolved.startswith(allowed_prefix):
        return {
            "error": f"archive_path must be inside ~/.jarvis-v2/ (got: {archive_path})",
            "status": "error",
        }

    path = Path(archive_path)
    if not path.exists():
        return {"error": f"File not found: {archive_path}", "status": "error"}

    extract = bool(args.get("extract", False))
    extract_path_arg = str(args.get("extract_path") or "").strip()
    name_lower = path.name.lower()

    try:
        if name_lower.endswith(".zip"):
            import zipfile as _zipfile
            with _zipfile.ZipFile(path) as zf:
                file_list = zf.namelist()
                if extract:
                    dest = Path(extract_path_arg) if extract_path_arg else path.parent / f"{path.stem}_extracted"
                    dest.mkdir(parents=True, exist_ok=True)
                    zf.extractall(dest)
        elif any(name_lower.endswith(ext) for ext in (".tar.gz", ".tgz", ".tar.bz2", ".tar")):
            import tarfile as _tarfile
            with _tarfile.open(path) as tf:
                file_list = tf.getnames()
                if extract:
                    dest = Path(extract_path_arg) if extract_path_arg else path.parent / f"{path.stem}_extracted"
                    dest.mkdir(parents=True, exist_ok=True)
                    tf.extractall(dest)
        elif name_lower.endswith(".rar"):
            try:
                import rarfile as _rarfile
            except ImportError:
                return {
                    "error": "rarfile package not installed. Run: pip install rarfile",
                    "status": "error",
                }
            with _rarfile.RarFile(path) as rf:
                file_list = rf.namelist()
                if extract:
                    dest = Path(extract_path_arg) if extract_path_arg else path.parent / f"{path.stem}_extracted"
                    dest.mkdir(parents=True, exist_ok=True)
                    rf.extractall(dest)
        else:
            return {
                "error": f"Unsupported archive format: {path.suffix}. Supported: .zip, .tar, .tar.gz, .tgz, .tar.bz2, .rar",
                "status": "error",
            }
    except Exception as exc:
        return {"error": f"Archive operation failed: {exc}", "status": "error"}

    result: dict[str, Any] = {"file_list": file_list, "count": len(file_list), "status": "ok"}
    if extract:
        result["extracted_to"] = str(dest)
    return result
```

- [ ] **Step 4: Add tool definition to `TOOL_DEFINITIONS`**

After the `analyze_image` definition block (after line ~327 in simple_tools.py), add:

```python
    {
        "type": "function",
        "function": {
            "name": "read_archive",
            "description": "List the contents of a zip/tar/rar archive, or extract it. Use to inspect uploaded archive files sent by the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "archive_path": {
                        "type": "string",
                        "description": "Absolute path to the archive file (must be inside ~/.jarvis-v2/)",
                    },
                    "extract": {
                        "type": "boolean",
                        "description": "If true, extract the archive. Default false (list only).",
                    },
                    "extract_path": {
                        "type": "string",
                        "description": "Where to extract (default: sibling directory named <stem>_extracted)",
                    },
                },
                "required": ["archive_path"],
            },
        },
    },
```

- [ ] **Step 5: Register handler in `_TOOL_HANDLERS`**

In the `_TOOL_HANDLERS` dict (around line 3094, after `"analyze_image": _exec_analyze_image`), add:

```python
    "read_archive": _exec_read_archive,
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_read_archive.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 7: Verify syntax**

```bash
conda activate ai && python -m compileall core/tools/simple_tools.py
```

Expected: `Compiling 'core/tools/simple_tools.py'...` with no errors.

- [ ] **Step 8: Commit**

```bash
git add core/tools/simple_tools.py tests/test_read_archive.py
git commit -m "feat: add read_archive tool (list/extract zip, tar, rar)"
```

---

### Task 2: Attachment upload + serve API

**Files:**
- Create: `apps/api/jarvis_api/routes/attachments.py`
- Modify: `apps/api/jarvis_api/app.py`
- Create: `tests/test_attachments_api.py`

- [ ] **Step 1: Create `apps/api/jarvis_api/routes/attachments.py`**

```python
"""Attachment upload and serve endpoints.

Files are saved to ~/.jarvis-v2/uploads/{session_id}/{uuid}_{filename}.
Metadata is kept in an in-memory registry (_registry) — lost on server restart,
which is acceptable for session-scoped attachments.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from apps.api.jarvis_api.services.chat_sessions import get_chat_session

router = APIRouter(prefix="/attachments", tags=["attachments"])

_MAX_FILE_BYTES = 200 * 1024 * 1024  # 200 MB
_MAX_IMAGES_PER_SESSION = 25
_UPLOAD_DIR = Path.home() / ".jarvis-v2" / "uploads"

_registry: dict[str, "AttachmentMeta"] = {}


@dataclass
class AttachmentMeta:
    id: str
    session_id: str
    filename: str
    mime_type: str
    size_bytes: int
    server_path: str


def get_attachment(attachment_id: str) -> AttachmentMeta | None:
    """Look up attachment metadata by ID (used by chat route for context injection)."""
    return _registry.get(attachment_id)


@router.post("/upload")
async def upload_attachment(
    file: UploadFile,
    session_id: str = Form(...),
) -> dict:
    """Upload a file and return its attachment_id."""
    session_id = session_id.strip()
    if not session_id or get_chat_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Chat session not found")

    mime = file.content_type or "application/octet-stream"

    # Check image limit before reading data
    if mime.startswith("image/"):
        image_count = sum(
            1 for m in _registry.values()
            if m.session_id == session_id and m.mime_type.startswith("image/")
        )
        if image_count >= _MAX_IMAGES_PER_SESSION:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum {_MAX_IMAGES_PER_SESSION} images per session",
            )

    data = await file.read()
    if len(data) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 200 MB limit")

    attachment_id = uuid4().hex
    safe_name = Path(file.filename or "upload").name
    dest_dir = _UPLOAD_DIR / session_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{attachment_id}_{safe_name}"
    dest_path.write_bytes(data)

    meta = AttachmentMeta(
        id=attachment_id,
        session_id=session_id,
        filename=safe_name,
        mime_type=mime,
        size_bytes=len(data),
        server_path=str(dest_path),
    )
    _registry[attachment_id] = meta

    return {
        "id": attachment_id,
        "filename": safe_name,
        "mime_type": mime,
        "size_bytes": len(data),
        "server_path": str(dest_path),
    }


@router.get("/{attachment_id}")
async def serve_attachment(attachment_id: str, session_id: str) -> FileResponse:
    """Serve an uploaded file for browser display."""
    meta = _registry.get(attachment_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    if meta.session_id != session_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if not Path(meta.server_path).exists():
        raise HTTPException(status_code=404, detail="File missing from disk")
    return FileResponse(
        meta.server_path,
        filename=meta.filename,
        media_type=meta.mime_type,
    )
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_attachments_api.py`:

```python
"""Tests for attachment upload and serve endpoints."""
from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Minimal FastAPI app for testing
from fastapi import FastAPI
from apps.api.jarvis_api.routes.attachments import router, _registry

app = FastAPI()
app.include_router(router)
client = TestClient(app)

FAKE_SESSION = "chat-testsession123"


@pytest.fixture(autouse=True)
def clear_registry():
    _registry.clear()
    yield
    _registry.clear()


@pytest.fixture(autouse=True)
def mock_session_and_dir(tmp_path, monkeypatch):
    # Make get_chat_session return something for our test session
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.attachments.get_chat_session",
        lambda sid: {"id": sid} if sid == FAKE_SESSION else None,
    )
    # Redirect uploads to tmp_path
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.attachments._UPLOAD_DIR",
        tmp_path / "uploads",
    )


def test_upload_image_success():
    data = b"\x89PNG\r\n" + b"x" * 100
    response = client.post(
        "/attachments/upload",
        data={"session_id": FAKE_SESSION},
        files={"file": ("photo.png", io.BytesIO(data), "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert "id" in body
    assert body["filename"] == "photo.png"
    assert body["mime_type"] == "image/png"
    assert body["size_bytes"] == len(data)


def test_upload_unknown_session_rejected():
    response = client.post(
        "/attachments/upload",
        data={"session_id": "chat-doesnotexist"},
        files={"file": ("x.txt", io.BytesIO(b"hi"), "text/plain")},
    )
    assert response.status_code == 404


def test_upload_enforces_image_limit(monkeypatch, tmp_path):
    from apps.api.jarvis_api.routes import attachments as att_mod
    # Pre-fill registry with 25 images for this session
    for i in range(25):
        from apps.api.jarvis_api.routes.attachments import AttachmentMeta
        _registry[f"fake-{i}"] = AttachmentMeta(
            id=f"fake-{i}", session_id=FAKE_SESSION,
            filename=f"img{i}.jpg", mime_type="image/jpeg",
            size_bytes=100, server_path="/tmp/fake",
        )
    response = client.post(
        "/attachments/upload",
        data={"session_id": FAKE_SESSION},
        files={"file": ("extra.jpg", io.BytesIO(b"x"), "image/jpeg")},
    )
    assert response.status_code == 400
    assert "25" in response.json()["detail"]


def test_serve_attachment(tmp_path):
    # Upload first
    data = b"hello world"
    resp = client.post(
        "/attachments/upload",
        data={"session_id": FAKE_SESSION},
        files={"file": ("note.txt", io.BytesIO(data), "text/plain")},
    )
    assert resp.status_code == 200
    aid = resp.json()["id"]

    # Serve it
    serve_resp = client.get(f"/attachments/{aid}?session_id={FAKE_SESSION}")
    assert serve_resp.status_code == 200
    assert serve_resp.content == data


def test_serve_wrong_session_rejected(tmp_path):
    data = b"secret"
    resp = client.post(
        "/attachments/upload",
        data={"session_id": FAKE_SESSION},
        files={"file": ("f.txt", io.BytesIO(data), "text/plain")},
    )
    aid = resp.json()["id"]
    resp2 = client.get(f"/attachments/{aid}?session_id=chat-wrongsession")
    assert resp2.status_code == 403


def test_serve_unknown_id():
    resp = client.get(f"/attachments/doesnotexist?session_id={FAKE_SESSION}")
    assert resp.status_code == 404
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_attachments_api.py -v 2>&1 | head -40
```

Expected: some FAIL (module exists but session mock or upload dir patching may not work yet — that's fine, verify it actually runs the test code).

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_attachments_api.py -v
```

Expected: All 6 tests PASS. If any fail, fix the issue before continuing.

- [ ] **Step 5: Register router in `apps/api/jarvis_api/app.py`**

After line 40 (`from apps.api.jarvis_api.routes.system_health import router as system_health_router`), add:

```python
from apps.api.jarvis_api.routes.attachments import router as attachments_router
```

After line 88 (`app.include_router(chat_router)`), add:

```python
    app.include_router(attachments_router)
```

- [ ] **Step 6: Verify syntax**

```bash
conda activate ai && python -m compileall apps/api/jarvis_api/routes/attachments.py apps/api/jarvis_api/app.py
```

Expected: Both compile with no errors.

- [ ] **Step 7: Commit**

```bash
git add apps/api/jarvis_api/routes/attachments.py apps/api/jarvis_api/app.py tests/test_attachments_api.py
git commit -m "feat: attachment upload + serve endpoints with in-memory registry"
```

---

### Task 3: Chat API context injection

**Files:**
- Modify: `apps/api/jarvis_api/routes/chat.py`

- [ ] **Step 1: Extend `ChatStreamRequest` and inject context**

Replace lines 24-26 and 70-87 in `apps/api/jarvis_api/routes/chat.py`:

Change `ChatStreamRequest` from:
```python
class ChatStreamRequest(BaseModel):
    message: str = ""
    session_id: str = ""
```

To:
```python
class ChatStreamRequest(BaseModel):
    message: str = ""
    session_id: str = ""
    attachment_ids: list[str] = []
```

Replace the `chat_stream` function body (lines 71-87):

```python
@router.post("/stream")
async def chat_stream(request: ChatStreamRequest) -> StreamingResponse:
    session_id = request.session_id.strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id must be a non-empty string")
    if get_chat_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # Build attachment context block
    effective_message = request.message
    if request.attachment_ids:
        from apps.api.jarvis_api.routes.attachments import get_attachment
        parts: list[str] = []
        for aid in request.attachment_ids:
            meta = get_attachment(aid)
            if meta:
                size_mb = f"{meta.size_bytes / 1_048_576:.1f}MB"
                parts.append(f"{meta.filename} ({meta.mime_type}, {size_mb}, path={meta.server_path})")
        if parts:
            effective_message = "[Attached files: " + ", ".join(parts) + "]\n\n" + request.message

    append_chat_message(session_id=session_id, role="user", content=effective_message)
    from apps.api.jarvis_api.services.notification_bridge import pin_session
    pin_session(session_id)
    return StreamingResponse(
        start_visible_run(message=effective_message, session_id=session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
```

- [ ] **Step 2: Verify syntax**

```bash
conda activate ai && python -m compileall apps/api/jarvis_api/routes/chat.py
```

Expected: `Compiling 'apps/api/jarvis_api/routes/chat.py'...` no errors.

- [ ] **Step 3: Commit**

```bash
git add apps/api/jarvis_api/routes/chat.py
git commit -m "feat: inject attachment context into chat stream run"
```

---

### Task 4: CSS for attachment tray and transcript

**Files:**
- Modify: `apps/ui/src/styles/global.css`

- [ ] **Step 1: Append attachment styles to global.css**

Append the following at the end of `apps/ui/src/styles/global.css`:

```css
/* ── Attachment tray (Composer) ──────────────────────────────── */

.composer-attachment-tray {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 10px 6px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}

.attachment-thumb {
  position: relative;
  width: 72px;
  height: 72px;
  border-radius: 8px;
  overflow: hidden;
  background: #1a1a1a;
  flex-shrink: 0;
  cursor: pointer;
}

.attachment-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.attachment-thumb-label {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0,0,0,0.55);
  font-size: 8px;
  color: #ccc;
  padding: 2px 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: center;
}

.attachment-thumb-remove {
  position: absolute;
  top: 3px;
  right: 3px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: rgba(0,0,0,0.7);
  border: none;
  color: #fff;
  font-size: 10px;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  opacity: 0;
  transition: opacity 0.15s;
}

.attachment-thumb:hover .attachment-thumb-remove {
  opacity: 1;
}

.attachment-thumb-progress {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 2px;
  background: #40b3b3;
  transition: width 0.1s;
}

.attachment-thumb.error-state {
  border: 1px solid #c04040;
}

.attachment-file-card {
  width: 72px;
  height: 72px;
  border-radius: 8px;
  background: #1e2a2a;
  border: 1px solid #2d4040;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  flex-shrink: 0;
  position: relative;
}

.attachment-file-card-icon {
  font-size: 22px;
  line-height: 1;
}

.attachment-file-card-name {
  font-size: 8px;
  color: #aaa;
  max-width: 64px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: center;
}

.attachment-file-card-size {
  font-size: 8px;
  color: #666;
}

.attachment-file-card .attachment-thumb-remove {
  top: 3px;
  right: 3px;
  opacity: 0;
}

.attachment-file-card:hover .attachment-thumb-remove {
  opacity: 1;
}

.attachment-status-line {
  font-size: 10px;
  color: #666;
  padding: 0 12px 6px;
}

.composer-card.drop-active {
  border-color: #40b3b3 !important;
  box-shadow: 0 0 0 1px #40b3b3 inset;
}

/* ── Attachment thumbnails in transcript ─────────────────────── */

.message-attachment-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 6px;
}

.message-attachment-thumb {
  width: 64px;
  height: 64px;
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  flex-shrink: 0;
}

.message-attachment-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: opacity 0.15s;
}

.message-attachment-thumb:hover img {
  opacity: 0.85;
}

.message-attachment-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: rgba(64,179,179,0.08);
  border: 1px solid rgba(64,179,179,0.2);
  border-radius: 20px;
  padding: 3px 10px 3px 6px;
  font-size: 10px;
  color: #aaa;
  margin-top: 4px;
  margin-right: 4px;
}

/* ── Attachment lightbox overlay ─────────────────────────────── */

.attachment-lightbox-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.88);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  cursor: zoom-out;
}

.attachment-lightbox-inner {
  width: min(90vw, 1200px);
  max-height: 90vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.attachment-lightbox-inner img {
  max-width: 100%;
  max-height: 90vh;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.6);
}
```

- [ ] **Step 2: Build frontend to verify CSS is valid**

```bash
cd /media/projects/jarvis-v2/apps/ui && npm run build 2>&1 | tail -10
```

Expected: build succeeds (or fails only on JS, not CSS parse errors).

- [ ] **Step 3: Commit**

```bash
git add apps/ui/src/styles/global.css
git commit -m "feat: CSS for attachment tray, transcript thumbnails, and lightbox"
```

---

### Task 5: Composer attachment UI

**Files:**
- Modify: `apps/ui/src/components/chat/Composer.jsx`

- [ ] **Step 1: Add `uploadAttachment` to adapters.js**

In `apps/ui/src/lib/adapters.js`, after the `streamMessage` function (after line 4297), add:

```js
  async uploadAttachment(sessionId, file) {
    const form = new FormData()
    form.append('file', file)
    form.append('session_id', sessionId)
    const response = await fetch('/attachments/upload', { method: 'POST', body: form })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.detail || `Upload failed: ${response.status}`)
    }
    return response.json()
  },
```

- [ ] **Step 2: Rewrite Composer.jsx with attachment support**

Replace the full contents of `apps/ui/src/components/chat/Composer.jsx` with:

```jsx
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { ArrowUp, Square, Plus, GitBranch, GitCommit, ShieldCheck, Layers, Activity, Check, X, Monitor } from 'lucide-react'
import { backend } from '../../lib/adapters'

function formatTokens(n) {
  if (!n && n !== 0) return null
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return String(n)
}

function formatDiff(ins, dels) {
  const parts = []
  if (ins > 0) parts.push(`+${ins > 999 ? Math.round(ins / 100) / 10 + 'k' : ins}`)
  if (dels > 0) parts.push(`-${dels > 999 ? Math.round(dels / 100) / 10 + 'k' : dels}`)
  return parts
}

function fileIcon(mime) {
  if (mime.startsWith('image/')) return '🖼️'
  if (mime.includes('zip')) return '📦'
  if (mime.includes('tar') || mime.includes('gzip')) return '🗜️'
  if (mime.includes('rar')) return '🗜️'
  return '📎'
}

function formatBytes(n) {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

export function Composer({
  value,
  onChange,
  onSend,
  onCancel,
  isStreaming,
  selection,
  onSelectionChange,
  lastRunTokens,
  streamingTokenEstimate,
  sessionId,
}) {
  const textareaRef = useRef(null)
  const commitInputRef = useRef(null)
  const fileInputRef = useRef(null)

  const [planMode, setPlanMode] = useState(false)
  const [approvalMode, setApprovalMode] = useState('auto')
  const [gitInfo, setGitInfo] = useState(null)
  const [commitOpen, setCommitOpen] = useState(false)
  const [commitMsg, setCommitMsg] = useState('')
  const [commitState, setCommitState] = useState('idle')
  const [commitError, setCommitError] = useState('')
  const [provider, setProvider] = useState(selection?.currentProvider || '')
  const [model, setModel] = useState(selection?.currentModel || '')
  const [attachments, setAttachments] = useState([])
  // attachments: [{localId, filename, mime, size, status, objectUrl, serverId}]
  // status: 'uploading' | 'done' | 'error'
  const [isDragOver, setIsDragOver] = useState(false)

  const doneAttachments = attachments.filter((a) => a.status === 'done')
  const canSend = (Boolean(value.trim()) || doneAttachments.length > 0) && !isStreaming

  useEffect(() => {
    setProvider(selection?.currentProvider || '')
    setModel(selection?.currentModel || '')
  }, [selection?.currentProvider, selection?.currentModel])

  useEffect(() => {
    async function fetchGit() {
      const info = await backend.getSystemGit()
      setGitInfo(info)
    }
    fetchGit()
    const id = setInterval(fetchGit, 30_000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    if (commitOpen) commitInputRef.current?.focus()
  }, [commitOpen])

  useLayoutEffect(() => {
    const node = textareaRef.current
    if (!node) return
    node.style.height = '0px'
    node.style.height = `${Math.min(node.scrollHeight, 160)}px`
  }, [value])

  const configuredTargets = selection?.availableConfiguredTargets || []
  const providers = useMemo(
    () => [...new Set([selection?.currentProvider || '', ...configuredTargets.map((x) => x.provider)].filter(Boolean))],
    [configuredTargets, selection?.currentProvider]
  )
  const models = useMemo(() => {
    if (provider === 'ollama') {
      const ollamaModels = (selection?.ollamaModels || [])
        .filter((m) => m.name && !m.family?.includes('bert') && !m.name.includes('embed'))
        .map((m) => ({ model: m.name, label: m.name }))
      if (ollamaModels.length) return ollamaModels
    }
    const forProvider = configuredTargets.filter((x) => x.provider === provider)
    return forProvider.length
      ? forProvider.map((x) => ({ model: x.model, label: x.model }))
      : provider === selection?.currentProvider && selection?.currentModel
        ? [{ model: selection.currentModel, label: selection.currentModel }]
        : []
  }, [configuredTargets, provider, selection])

  function handleProviderChange(e) {
    const next = e.target.value
    setProvider(next)
    const first = configuredTargets.find((x) => x.provider === next)
    const nextModel = first?.model || ''
    setModel(nextModel)
    if (nextModel) onSelectionChange?.({ provider: next, model: nextModel, authProfile: first?.authProfile || '' })
  }

  function handleModelChange(e) {
    const next = e.target.value
    setModel(next)
    const candidate = configuredTargets.find((x) => x.model === next)
    onSelectionChange?.({ provider, model: next, authProfile: candidate?.authProfile || '' })
  }

  async function addFiles(files) {
    if (!sessionId) return
    const newItems = Array.from(files).map((file) => ({
      localId: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      filename: file.name,
      mime: file.type || 'application/octet-stream',
      size: file.size,
      status: 'uploading',
      objectUrl: file.type?.startsWith('image/') ? URL.createObjectURL(file) : null,
      serverId: null,
      _file: file,
    }))
    setAttachments((prev) => [...prev, ...newItems])

    for (const item of newItems) {
      try {
        const result = await backend.uploadAttachment(sessionId, item._file)
        setAttachments((prev) =>
          prev.map((a) => a.localId === item.localId ? { ...a, status: 'done', serverId: result.id } : a)
        )
      } catch {
        setAttachments((prev) =>
          prev.map((a) => a.localId === item.localId ? { ...a, status: 'error' } : a)
        )
      }
    }
  }

  function removeAttachment(localId) {
    setAttachments((prev) => {
      const item = prev.find((a) => a.localId === localId)
      if (item?.objectUrl) URL.revokeObjectURL(item.objectUrl)
      return prev.filter((a) => a.localId !== localId)
    })
  }

  function handleSend() {
    if (!canSend) return
    const msg = planMode ? `[Plan mode] ${value.trim()}` : value.trim()
    const attachmentIds = doneAttachments.map((a) => a.serverId)
    const attachmentMeta = doneAttachments.map((a) => ({
      id: a.serverId,
      filename: a.filename,
      mimeType: a.mime,
      objectUrl: a.objectUrl,
    }))
    onSend(msg, { approvalMode, attachmentIds, attachmentMeta })
    setAttachments([])
  }

  function handleDragOver(e) {
    e.preventDefault()
    setIsDragOver(true)
  }

  function handleDragLeave(e) {
    if (!e.currentTarget.contains(e.relatedTarget)) setIsDragOver(false)
  }

  function handleDrop(e) {
    e.preventDefault()
    setIsDragOver(false)
    if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files)
  }

  function openCommit() {
    setCommitMsg('')
    setCommitError('')
    setCommitState('idle')
    setCommitOpen(true)
  }

  function cancelCommit() {
    setCommitOpen(false)
    setCommitMsg('')
    setCommitError('')
    setCommitState('idle')
  }

  async function submitCommit() {
    const msg = commitMsg.trim()
    if (!msg) return
    setCommitState('loading')
    setCommitError('')
    try {
      const result = await backend.gitCommit(msg)
      if (result.ok) {
        setCommitOpen(false)
        setCommitMsg('')
        setCommitState('idle')
        const info = await backend.getSystemGit()
        setGitInfo(info)
      } else {
        setCommitState('error')
        setCommitError(result.error || 'Commit failed')
      }
    } catch (err) {
      setCommitState('error')
      setCommitError(String(err))
    }
  }

  const tokenLabel = isStreaming && streamingTokenEstimate > 0
    ? formatTokens(streamingTokenEstimate)
    : formatTokens(lastRunTokens?.total)

  const diffParts = gitInfo ? formatDiff(gitInfo.insertions, gitInfo.deletions) : []
  const shortBranch = gitInfo?.branch || ''
  const shortPath = gitInfo?.workspace
    ? gitInfo.workspace.replace(/^\/media\/projects\//, '~/')
    : ''
  const hasChanges = (gitInfo?.files_changed || 0) > 0
  const uploadingCount = attachments.filter((a) => a.status === 'uploading').length

  return (
    <section className="composer-shell">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept="image/*,.zip,.tar,.tar.gz,.tgz,.tar.bz2,.rar"
        style={{ display: 'none' }}
        onChange={(e) => { if (e.target.files?.length) addFiles(e.target.files); e.target.value = '' }}
      />

      {commitOpen && (
        <div className="composer-commit-row">
          <GitCommit size={12} strokeWidth={1.8} className="composer-commit-icon" />
          <input
            ref={commitInputRef}
            className="composer-commit-input mono"
            type="text"
            value={commitMsg}
            onChange={(e) => setCommitMsg(e.target.value)}
            placeholder="Commit message…"
            disabled={commitState === 'loading'}
            onKeyDown={(e) => {
              if (e.key === 'Enter') submitCommit()
              if (e.key === 'Escape') cancelCommit()
            }}
          />
          {commitError && (
            <span className="composer-commit-error mono">{commitError}</span>
          )}
          <button className="composer-commit-confirm" onClick={submitCommit}
            disabled={!commitMsg.trim() || commitState === 'loading'} title="Confirm commit" type="button">
            <Check size={12} />
          </button>
          <button className="composer-commit-cancel" onClick={cancelCommit} title="Cancel" type="button">
            <X size={12} />
          </button>
        </div>
      )}

      <div
        className={`composer-card${isStreaming ? ' working' : ''}${isDragOver ? ' drop-active' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {shortBranch && (
          <div className="composer-git-bar">
            <div className="composer-git-bar-left">
              <GitBranch size={11} strokeWidth={1.8} />
              <span className="mono">{shortBranch}</span>
              {diffParts.length > 0 && (
                <span className="composer-diff-stats mono">
                  {diffParts.map((part, i) => (
                    <span key={i} className={part.startsWith('+') ? 'diff-ins' : 'diff-dels'}>{part}</span>
                  ))}
                </span>
              )}
            </div>
            <div className="composer-git-bar-right">
              {hasChanges && !commitOpen && (
                <button className="composer-commit-btn" onClick={openCommit} title="Commit changes" type="button">
                  <GitCommit size={11} strokeWidth={1.8} />
                  <span>Commit changes</span>
                </button>
              )}
            </div>
          </div>
        )}

        {/* Attachment tray */}
        {attachments.length > 0 && (
          <div className="composer-attachment-tray">
            {attachments.map((item) =>
              item.objectUrl ? (
                <div key={item.localId} className={`attachment-thumb${item.status === 'error' ? ' error-state' : ''}`}>
                  <img src={item.objectUrl} alt={item.filename} />
                  <span className="attachment-thumb-label">{item.filename}</span>
                  {item.status === 'uploading' && (
                    <div className="attachment-thumb-progress" style={{ width: '60%' }} />
                  )}
                  <button className="attachment-thumb-remove" onClick={() => removeAttachment(item.localId)}>×</button>
                </div>
              ) : (
                <div key={item.localId} className="attachment-file-card">
                  <span className="attachment-file-card-icon">{fileIcon(item.mime)}</span>
                  <span className="attachment-file-card-name">{item.filename}</span>
                  <span className="attachment-file-card-size">{formatBytes(item.size)}</span>
                  <button className="attachment-thumb-remove" onClick={() => removeAttachment(item.localId)}>×</button>
                </div>
              )
            )}
          </div>
        )}

        <textarea
          ref={textareaRef}
          className="composer-textarea"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
          placeholder={
            isStreaming
              ? 'Jarvis is responding…'
              : planMode
                ? 'Describe what to plan…'
                : 'Message Jarvis…'
          }
          rows={1}
        />

        <div className="composer-toolbar">
          <div className="composer-toolbar-left">
            <button
              className="composer-attach-btn icon-btn subtle"
              type="button"
              title="Attach file or image"
              onClick={() => fileInputRef.current?.click()}
            >
              <Plus size={14} />
            </button>
            <div className="composer-permissions-group" title="Tool approval mode">
              <ShieldCheck size={11} strokeWidth={1.8} className="composer-shield-icon" />
              <select className="composer-select mono" value={approvalMode} onChange={(e) => setApprovalMode(e.target.value)}>
                <option value="auto">Auto</option>
                <option value="ask">Ask permissions</option>
                <option value="trust">Trust all</option>
              </select>
            </div>
          </div>

          <div className="composer-toolbar-right">
            {providers.length > 0 && (
              <div className="composer-model-group">
                <select className="composer-select mono" value={provider} onChange={handleProviderChange} title="Provider">
                  {providers.map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
                {models.length > 0 && (
                  <>
                    <span className="composer-select-sep mono">/</span>
                    <select className="composer-select mono" value={model} onChange={handleModelChange} title="Model">
                      {models.map((m) => <option key={m.model} value={m.model}>{m.label}</option>)}
                    </select>
                  </>
                )}
              </div>
            )}

            {isStreaming ? (
              <button className="send-btn cancel" onClick={onCancel} title="Stop generating">
                <Square size={14} />
              </button>
            ) : (
              <button className="send-btn" onClick={handleSend} disabled={!canSend}
                title={canSend ? 'Send message' : 'Write a message or attach a file first'}>
                <ArrowUp size={16} />
              </button>
            )}
          </div>
        </div>
      </div>

      {attachments.length > 0 && (
        <div className="attachment-status-line">
          {attachments.length} vedhæftet{attachments.length !== 1 ? 'e' : ''}
          {uploadingCount > 0 ? ` · ${uploadingCount} uploades stadig` : ''}
        </div>
      )}

      <div className="composer-footer">
        <div className="composer-footer-left">
          {shortPath && (
            <>
              <Monitor size={10} strokeWidth={1.6} />
              <span className="composer-workspace-path mono">{shortPath}</span>
            </>
          )}
        </div>
        <div className="composer-footer-right">
          <button
            className={`composer-plan-btn${planMode ? ' active' : ''}`}
            onClick={() => setPlanMode(!planMode)}
            title={planMode ? 'Plan mode on — click to disable' : 'Enable plan mode'}
            type="button"
          >
            <Layers size={11} strokeWidth={1.8} />
            <span>Plan</span>
          </button>

          {tokenLabel && (
            <div className="composer-token-count mono"
              title={lastRunTokens ? `In: ${lastRunTokens.input} / Out: ${lastRunTokens.output}` : ''}>
              <Activity size={9} />
              <span>{tokenLabel}</span>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
```

- [ ] **Step 3: Build frontend to verify no errors**

```bash
cd /media/projects/jarvis-v2/apps/ui && npm run build 2>&1 | tail -20
```

Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add apps/ui/src/components/chat/Composer.jsx apps/ui/src/lib/adapters.js
git commit -m "feat: composer attachment tray with drag/drop and eager upload"
```

---

### Task 6: Wire attachment IDs through call chain

**Files:**
- Modify: `apps/ui/src/app/ChatPage.jsx`
- Modify: `apps/ui/src/app/useUnifiedShell.js`
- Modify: `apps/ui/src/lib/adapters.js`

- [ ] **Step 1: Update `adapters.js` `streamMessage` to send `attachment_ids`**

In `apps/ui/src/lib/adapters.js`, find the `streamMessage` function (line 4287). Replace its signature and body:

Change:
```js
async streamMessage({ sessionId, content, onRun, onDelta, onDone, onFailed, onWorkingStep, onCapability, onApprovalRequest }) {
    const response = await fetch('/chat/stream', {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify({ message: content, session_id: sessionId }),
    })
```

To:
```js
async streamMessage({ sessionId, content, attachmentIds = [], onRun, onDelta, onDone, onFailed, onWorkingStep, onCapability, onApprovalRequest }) {
    const response = await fetch('/chat/stream', {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify({ message: content, session_id: sessionId, attachment_ids: attachmentIds }),
    })
```

- [ ] **Step 2: Update `ChatPage.jsx` to pass `sessionId` and forward opts**

In `apps/ui/src/app/ChatPage.jsx`, replace:

```jsx
export function ChatPage({
  activeSession,
  selection,
  error,
  onSelectionChange,
  onRefresh,
  onSend,
  onCancel,
  onRename,
  onDelete,
  isRefreshing,
  isStreaming,
  workingSteps,
  capabilityActivity,
  systemHealth,
  jarvisSurface,
  lastRunTokens,
  streamingTokenEstimate,
}) {
```

With (no change, just note it's unchanged).

Replace the `Composer` usage (lines 48-62):

```jsx
        <Composer
          value={draft}
          onChange={setDraft}
          isStreaming={isStreaming}
          onSend={(msg) => {
            if (isStreaming) return
            onSend(msg)
            setDraft('')
          }}
          onCancel={onCancel}
          selection={selection}
          onSelectionChange={onSelectionChange}
          lastRunTokens={lastRunTokens}
          streamingTokenEstimate={streamingTokenEstimate}
          }}
        />
```

With:

```jsx
        <Composer
          value={draft}
          onChange={setDraft}
          isStreaming={isStreaming}
          onSend={(msg, opts) => {
            if (isStreaming) return
            onSend(msg, opts)
            setDraft('')
          }}
          onCancel={onCancel}
          selection={selection}
          onSelectionChange={onSelectionChange}
          lastRunTokens={lastRunTokens}
          streamingTokenEstimate={streamingTokenEstimate}
          sessionId={activeSession?.id}
        />
```

- [ ] **Step 3: Update `useUnifiedShell.js` to accept and use attachment opts**

In `apps/ui/src/app/useUnifiedShell.js`, replace line 226:

```js
  async function handleSend(content) {
    if (!activeSession || isStreaming) return

    const sessionId = activeSession.id
    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      ts: nowLabel(),
    }
```

With:

```js
  async function handleSend(content, { attachmentIds = [], attachmentMeta = [] } = {}) {
    if (!activeSession || isStreaming) return

    const sessionId = activeSession.id
    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      ts: nowLabel(),
      attachments: attachmentMeta,
    }
```

And replace line 257-259 (the `backend.streamMessage` call start):

```js
      const assistantMessage = await backend.streamMessage({
        sessionId,
        content,
        onRun: (payload) => {
```

With:

```js
      const assistantMessage = await backend.streamMessage({
        sessionId,
        content,
        attachmentIds,
        onRun: (payload) => {
```

- [ ] **Step 4: Build frontend**

```bash
cd /media/projects/jarvis-v2/apps/ui && npm run build 2>&1 | tail -20
```

Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git add apps/ui/src/app/ChatPage.jsx apps/ui/src/app/useUnifiedShell.js apps/ui/src/lib/adapters.js
git commit -m "feat: wire attachment IDs through Composer → ChatPage → useUnifiedShell → API"
```

---

### Task 7: Transcript image previews and lightbox

**Files:**
- Modify: `apps/ui/src/components/chat/ChatTranscript.jsx`

- [ ] **Step 1: Update `ChatTranscript.jsx` to render attachment strips and lightbox**

Replace the full contents of `apps/ui/src/components/chat/ChatTranscript.jsx` with:

```jsx
import { useState, useEffect, useRef } from 'react'
import { Copy, Check, ThumbsUp } from 'lucide-react'
import { MarkdownRenderer } from './MarkdownRenderer'
import { ApprovalCard } from './ApprovalCard'

/**
 * Renders a single assistant message bubble with a hover toolbar.
 */
function MessageWithActions({ message, workingSteps }) {
  const [copied, setCopied] = useState(false)
  const [liked, setLiked] = useState(false)

  function handleCopy() {
    navigator.clipboard.writeText(message.content || '').then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  return (
    <div className="message-group">
      <div className={`message-bubble ${message.pending ? 'pending' : ''}`}>
        {message.pending ? (
          <span
            className="working-shimmer"
            style={{ visibility: workingSteps?.some(s => s.status === 'running') ? 'visible' : 'hidden' }}
          >
            {workingSteps?.find((s) => s.status === 'running')?.detail ||
              workingSteps?.find((s) => s.status === 'running')?.action ||
              'working…'}
          </span>
        ) : null}
        {message.content ? (
          <div className="message-content">
            <MarkdownRenderer content={message.content} streaming={!!message.pending} />
            {message.pending && <span className="streaming-cursor" />}
          </div>
        ) : null}
      </div>
      {!message.pending && (
        <div className="message-actions">
          <button onClick={handleCopy} title="Kopiér besked">
            {copied ? <Check size={12} /> : <Copy size={12} />}
          </button>
          <button
            onClick={() => setLiked((l) => !l)}
            title="Synes godt om"
            className={liked ? 'liked' : ''}
          >
            <ThumbsUp size={12} />
          </button>
        </div>
      )}
    </div>
  )
}

/**
 * Renders attachment thumbnails above a user message bubble.
 * Images are clickable to open the lightbox.
 */
function AttachmentStrip({ attachments, sessionId, onOpenLightbox }) {
  if (!attachments || attachments.length === 0) return null

  const images = attachments.filter((a) => a.mimeType?.startsWith('image/'))
  const files = attachments.filter((a) => !a.mimeType?.startsWith('image/'))

  function srcFor(a) {
    if (a.objectUrl) return a.objectUrl
    if (a.id && sessionId) return `/attachments/${a.id}?session_id=${sessionId}`
    return null
  }

  return (
    <div>
      {images.length > 0 && (
        <div className="message-attachment-strip">
          {images.map((a) => {
            const src = srcFor(a)
            return src ? (
              <div
                key={a.id}
                className="message-attachment-thumb"
                onClick={() => onOpenLightbox({ src, filename: a.filename })}
                title={a.filename}
              >
                <img src={src} alt={a.filename} loading="lazy" />
              </div>
            ) : null
          })}
        </div>
      )}
      {files.map((a) => (
        <span key={a.id} className="message-attachment-pill">
          📎 {a.filename}
        </span>
      ))}
    </div>
  )
}

export function ChatTranscript({ messages, workingSteps, sessionId }) {
  const transcriptRef = useRef(null)
  const hasInitialScrolled = useRef(false)
  const prevMessageCount = useRef(0)
  const [lightbox, setLightbox] = useState(null) // {src, filename} or null

  useEffect(() => {
    const node = transcriptRef.current
    if (!node || messages.length === 0) return

    if (!hasInitialScrolled.current) {
      node.scrollTop = node.scrollHeight
      hasInitialScrolled.current = true
      prevMessageCount.current = messages.length
      return
    }

    if (messages.length > prevMessageCount.current) {
      node.scrollTop = node.scrollHeight
      prevMessageCount.current = messages.length
      return
    }

    prevMessageCount.current = messages.length

    const distanceFromBottom = node.scrollHeight - node.scrollTop - node.clientHeight
    if (distanceFromBottom < 120) node.scrollTop = node.scrollHeight
  }, [messages])

  if (!messages.length) {
    return (
      <section ref={transcriptRef} className="transcript empty-transcript">
        <div className="empty-transcript-copy">
          <p className="eyebrow">Front Door</p>
          <strong>Start a conversation</strong>
          <p className="muted">This session is persisted and will still be here after refresh.</p>
        </div>
      </section>
    )
  }

  return (
    <>
      <section ref={transcriptRef} className="transcript">
        {messages.filter((m) => m.role !== 'tool').map((message) =>
          message.role === 'approval_request' ? (
            <article key={message.id} className="message-row assistant">
              <div className="message-bubble">
                <ApprovalCard approval={message} />
              </div>
            </article>
          ) : (
            <article key={message.id} className={`message-row ${message.role}`}>
              <div className="message-name">
                {message.role === 'assistant' ? 'Jarvis' : 'Du'}
              </div>
              {message.role === 'assistant' ? (
                <MessageWithActions message={message} workingSteps={workingSteps} />
              ) : (
                <div className={`message-bubble ${message.pending ? 'pending' : ''}`}>
                  {message.attachments?.length > 0 && (
                    <AttachmentStrip
                      attachments={message.attachments}
                      sessionId={sessionId}
                      onOpenLightbox={setLightbox}
                    />
                  )}
                  {message.content ? (
                    <div className="message-content">
                      <MarkdownRenderer content={message.content} />
                    </div>
                  ) : null}
                </div>
              )}
              <div className="message-time">{message.ts}</div>
            </article>
          )
        )}
      </section>

      {lightbox && (
        <div className="attachment-lightbox-overlay" onClick={() => setLightbox(null)}>
          <div className="attachment-lightbox-inner" onClick={(e) => e.stopPropagation()}>
            <img src={lightbox.src} alt={lightbox.filename} />
          </div>
        </div>
      )}
    </>
  )
}
```

- [ ] **Step 2: Pass `sessionId` to `ChatTranscript` in `ChatPage.jsx`**

In `apps/ui/src/app/ChatPage.jsx`, replace:

```jsx
        <ChatTranscript messages={activeSession?.messages || []} workingSteps={workingSteps} />
```

With:

```jsx
        <ChatTranscript messages={activeSession?.messages || []} workingSteps={workingSteps} sessionId={activeSession?.id} />
```

- [ ] **Step 3: Build frontend**

```bash
cd /media/projects/jarvis-v2/apps/ui && npm run build 2>&1 | tail -20
```

Expected: build succeeds with no errors.

- [ ] **Step 4: Commit**

```bash
git add apps/ui/src/components/chat/ChatTranscript.jsx apps/ui/src/app/ChatPage.jsx
git commit -m "feat: attachment thumbnails in transcript with lightbox overlay"
```

---

### Task 8: End-to-end manual test

- [ ] **Step 1: Restart the API server**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && uvicorn apps.api.jarvis_api.app:app --host 127.0.0.1 --port 8010 --reload
```

- [ ] **Step 2: Rebuild and open the UI**

```bash
cd /media/projects/jarvis-v2/apps/ui && npm run build
```

Open `http://127.0.0.1:8010` in browser.

- [ ] **Step 3: Test image attach + send**

1. Click `+` button in composer → select a JPG/PNG image
2. Verify: thumbnail appears in tray above textarea
3. Type "Hvad viser dette billede?" and send
4. Verify: user message shows thumbnail above bubble in transcript
5. Click thumbnail → verify lightbox opens fullscreen
6. Verify: Jarvis's reply references the image

- [ ] **Step 4: Test drag/drop**

1. Drag a PNG file onto the composer area
2. Verify: composer card highlights with teal border on hover
3. Drop → verify thumbnail appears

- [ ] **Step 5: Test archive attach**

1. Click `+` → select a `.zip` file
2. Verify: icon card appears with filename and size
3. Send with message "Hvad er i dette arkiv?"
4. Verify: Jarvis calls `read_archive` and lists contents

- [ ] **Step 6: Run all tests**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_read_archive.py tests/test_attachments_api.py -v
```

Expected: all tests PASS.

- [ ] **Step 7: Final commit**

```bash
git add -A
git commit -m "feat: complete file & image attachment system (Sub-projekt N)"
```
