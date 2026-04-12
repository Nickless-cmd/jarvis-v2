# File & Image Attachments Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Allow users to drag/drop or select images (max 25) and archive files (zip/tar/rar, max 200 MB) in the webchat composer, with Jarvis able to analyze images and work with archive contents.

**Architecture:** Eager upload on attach (files sent immediately to server, before message send). Attachment IDs bundled with chat message. Backend injects file paths into run context so Jarvis can call existing `analyze_image` and new `read_archive` tools.

**Tech Stack:** React (frontend), FastAPI (upload endpoint + file serve endpoint), SQLite (no schema change — attachments stored as JSON in message metadata), Python `zipfile`/`tarfile`/`rarfile` (archive handling).

---

## Components

### 1. Upload API — `apps/api/jarvis_api/routes/attachments.py` (new)

**Endpoint:** `POST /attachments/upload`
- Accepts multipart form: `file` (UploadFile) + `session_id` (str)
- Validates session exists
- Validates file size ≤ 200 MB
- Validates image count ≤ 25 per session (for mime type `image/*`)
- Saves to `~/.jarvis-v2/uploads/{session_id}/{uuid4_hex}_{original_filename}`
- Returns JSON: `{id, filename, mime_type, size_bytes, server_path}`

**Endpoint:** `GET /attachments/{attachment_id}`
- Serves the file (for browser preview in transcript)
- Returns 404 if not found, 403 if session mismatch (session_id passed as query param)

**In-memory registry:** `dict[attachment_id, AttachmentMeta]` — simple dict, no DB.  
`AttachmentMeta`: `id`, `session_id`, `filename`, `mime_type`, `size_bytes`, `server_path`.

Router registered in `apps/api/jarvis_api/app.py`.

---

### 2. Composer UI — `apps/ui/src/components/chat/Composer.jsx` (modify)

**Drop zone:**
- Whole composer area has `onDragOver` / `onDrop` handlers
- Visual highlight (`drop-active` class) while dragging over
- Accepted: `image/*`, `.zip`, `.tar`, `.tar.gz`, `.tar.bz2`, `.rar`

**Attachment tray** (shown when attachments exist, above textarea):
- Images: 72×72px thumbnail (using `URL.createObjectURL` for local preview before upload completes), filename label, × remove button, upload progress bar at bottom
- Archives: icon card (📦/🗜️), filename, file size, × remove button
- Status line: "N vedhæftede · M uploades stadig"

**Upload flow per file:**
1. File selected/dropped → add to local state with `status: 'uploading'`, local object URL
2. `POST /attachments/upload` with `FormData`
3. On success: update state with `status: 'done'`, `attachment_id`, `server_path`
4. On failure: update state with `status: 'error'`, show error label on thumbnail

**Send:**
- `handleSend()` collects `attachment_ids` of all `status: 'done'` attachments
- Calls `onSend(message, { approvalMode, attachmentIds })`
- Clears attachment tray after send

**`+` button:** Opens `<input type="file" multiple accept="image/*,.zip,.tar,.rar" />` click

---

### 3. Message send adapter — `apps/ui/src/lib/adapters.js` (modify)

`streamMessage()` adds `attachment_ids` to the JSON body:
```js
body: JSON.stringify({ message: content, session_id: sessionId, attachment_ids: attachmentIds ?? [] })
```

---

### 4. Transcript preview — `apps/ui/src/components/chat/ChatTranscript.jsx` (modify)

**User messages with attachments:**
- Attachments stored on message object: `message.attachments = [{id, filename, mime_type}]`
- Images rendered as thumbnails above the message bubble (style B)
  - `src="/attachments/{id}?session_id={sessionId}"`
  - Click opens fullscreen overlay (same pattern as Mermaid overlay)
- Archive attachments rendered as small pill (📦 filename) below thumbnails

**Fullscreen overlay:** Reuse existing Mermaid overlay CSS classes. `<img>` fills overlay inner.

**`useUnifiedShell.js`:** When building the user message object after send, attach `attachments` from the sent `attachmentIds` (look up metadata from local attachment state).

---

### 5. Chat API — `apps/api/jarvis_api/routes/chat.py` (modify)

`ChatStreamRequest` adds:
```python
attachment_ids: list[str] = []
```

Before calling `start_visible_run`, resolve attachment metadata and build context block:
```
[Attached: foto1.jpg (image, /home/bs/.jarvis-v2/uploads/.../foto1.jpg), projekt.zip (archive, 14MB, /home/bs/.jarvis-v2/uploads/.../projekt.zip)]
```

Prepend to `request.message` before passing to `start_visible_run`.

---

### 6. Archive tool — `core/tools/simple_tools.py` (modify)

New tool: `read_archive`

```python
def _exec_read_archive(args: dict) -> dict:
    """List or extract a zip/tar/rar archive."""
```

Parameters:
- `archive_path` (str, required) — absolute path to archive
- `extract` (bool, default False) — if True, extract to sibling dir
- `extract_path` (str, optional) — override extract destination

Behaviour:
- **List only** (`extract=False`): returns `{file_list: [...], count: N, status: "ok"}`
- **Extract** (`extract=True`): extracts to `{archive_path}_extracted/`, returns `{extracted_to: str, file_list: [...], status: "ok"}`
- Supports: `.zip` (zipfile), `.tar`/`.tar.gz`/`.tar.bz2`/`.tgz` (tarfile), `.rar` (rarfile — optional dep, graceful error if not installed)
- Rejects paths outside `~/.jarvis-v2/` (security: no path traversal)

Tool definition added to `TOOL_DEFINITIONS`. Handler added to `_TOOL_HANDLERS`.

---

## Data Flow

```
1. User drops file
   → Composer: local preview, status=uploading
   → POST /attachments/upload → {id, server_path}
   → Composer: status=done, attachment_id stored

2. User sends message
   → POST /chat/stream {message, session_id, attachment_ids: ["abc", "def"]}
   → API resolves attachment metadata
   → Builds context block, prepends to message
   → start_visible_run(message_with_context, session_id)
   → Jarvis sees file paths, calls analyze_image / read_archive as needed

3. Transcript renders user message
   → thumbnails above bubble (images)
   → pill badges (archives)
   → click thumbnail → fullscreen overlay
```

---

## Constraints & Error Cases

- Max 25 images per session (enforced at upload, error returned)
- Max 200 MB per file (enforced at upload, error returned)
- Upload fails: thumbnail shows error state, file excluded from send
- Archive format unsupported: `read_archive` returns `{error: "...", status: "error"}`
- RAR without `rarfile` installed: returns helpful install message
- Upload dir created on first use: `~/.jarvis-v2/uploads/{session_id}/`
- No cleanup implemented (out of scope for this spec — manual or future TTL)

---

## Out of Scope

- Persistent attachment storage across sessions
- Automatic cleanup / TTL on uploads dir
- Sending attachments from Jarvis to user
- Video or audio files
