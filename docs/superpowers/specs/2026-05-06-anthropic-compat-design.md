# Anthropic-Compatible Endpoint — Design Spec

**Date:** 2026-05-06
**Status:** Approved (Bjørn) — ready for implementation plan
**Owner:** Claude Code

## Problem

Bjørn wants to use Jarvis as the model inside Claude Desktop and Claude Code. The existing OpenAI-compatible endpoint (`/v1/chat/completions`) lets him use Jarvis from OpenCode and other OpenAI-format clients, but Anthropic-format clients (Claude Desktop, Claude Code) need an `/v1/messages` endpoint with Anthropic's specific streaming protocol.

Bigger insight: building a polished agent UI (JarvisX) is a huge project. Claude Desktop/Code is already a finished, polished UI with file diffing, tool approval, syntax highlighting, MCP support, etc. If Jarvis can act as an Anthropic-compatible model, Bjørn (and Mikkel, and other users) get all of that UI for free — with Jarvis as the brain.

## Goal

Build `POST /anthropic/v1/messages` and `GET /anthropic/v1/models` endpoints that:

1. Accept Anthropic Messages API request format (system, messages, tools, stream, max_tokens)
2. Route auth via `x-api-key` header to a per-user workspace (Bjørn, Mikkel, etc.)
3. Build the prompt using Jarvis's identity (SOUL.md, IDENTITY.md, the routed user's USER.md, STANDING_ORDERS.md) as a prefix to Claude Desktop's system parameter
4. Pass through Claude Desktop's `tools` array to the underlying visible-lane model (`glm-5.1:cloud` via Ollama by default), translating tool-call semantics
5. Stream responses in Anthropic's SSE state machine: `message_start` → `content_block_start` → `content_block_delta` → `content_block_stop` → `message_delta` → `message_stop`
6. Stay stateless between requests — Claude Desktop holds the conversation history and sends it back each turn (including `tool_result` blocks)

Mode 2 first (identity-injected, no Jarvis-internal tools). Mode 3 follow-up adds Jarvis's internal tools (`recall_memories`, `search_jarvis_brain`, `remember_this`) to the toolset alongside Claude Desktop's tools.

## Non-goals

- Replacing the OpenAI-compatible endpoint (it stays untouched)
- Replacing JarvisX (it stays its own product; this is a parallel surface)
- Suspending Jarvis's own internal agentic loop — Claude Desktop's tool execution happens on Bjørn's local machine via Claude Desktop's own tool runtime, not Jarvis's
- Implementing Anthropic-specific features outside Messages API: prompt caching, batch API, vision (vision can be added later)

## Decisions (from Q&A)

| # | Decision | Choice |
|---|---|---|
| 1 | Identity injection level | Standard — SOUL.md + IDENTITY.md + USER.md + STANDING_ORDERS.md prefix, then Claude Desktop's `system` appended |
| 2 | Backend model | Visible-lane model (current default `glm-5.1:cloud` via Ollama) — same Jarvis as everywhere else |
| 3 | Tools come from | Claude Desktop's `tools` parameter — those are the tools Jarvis can use this session. Mode 2: only those. Mode 3: also Jarvis's internal memory/brain tools added to the toolset. |
| 4 | Multi-user auth | `x-api-key` header → config mapping → workspace ContextVar (mirrors JarvisX user routing) |
| 5 | Mode rollout | Mode 2 (identity + Claude Desktop's tools) first; Mode 3 (add Jarvis's internal tools) as separate follow-up |
| 6 | State management | Stateless between requests — Claude Desktop sends full history each turn |

## Architecture

```
Claude Desktop / Claude Code
        │
        ▼  POST /anthropic/v1/messages
        │  x-api-key: <bjorn-key>
        │  body: {model, system, messages, tools, stream, max_tokens}
        ▼
┌─────────────────────────────────────────────────────────────┐
│  apps/api/jarvis_api/routes/anthropic_compat.py             │
│                                                             │
│  1. Auth middleware → resolve api_key → user → workspace    │
│  2. Build identity prefix from workspace files              │
│  3. Combine: identity + body.system + body.messages         │
│  4. Translate body.tools (Anthropic format) → backend fmt   │
│  5. Send to provider (default: visible-lane = ollama/glm)   │
│  6. Stream backend response → Anthropic SSE state machine   │
└──┬──────────────────────────────────────────────────────────┘
   │
   ▼  POST /api/chat (ollama)
   │  messages, tools (ollama format)
   ▼
Backend model (glm-5.1:cloud)
        │
        ▼  text deltas + tool_calls
        │
   ◄────┘
        ▼
   Anthropic SSE state machine emits:
     event: message_start
     event: content_block_start (text or tool_use)
     event: content_block_delta (text_delta or input_json_delta)
     event: content_block_stop
     event: message_delta (stop_reason)
     event: message_stop
```

### New files

| Path | Responsibility |
|---|---|
| `apps/api/jarvis_api/routes/anthropic_compat.py` | The endpoint + streaming state machine |
| `apps/api/jarvis_api/middleware/anthropic_auth.py` | API-key validation + user routing |
| `core/services/anthropic_translator.py` | Anthropic ↔ backend format translation (tools, messages, deltas) |
| `core/services/anthropic_identity.py` | Build the identity prefix from workspace files |
| `state/anthropic_api_keys.json` | API-key → user mapping (gitignored, like other secrets) |
| `tests/api/test_anthropic_messages.py` | |
| `tests/api/test_anthropic_streaming.py` | |
| `tests/services/test_anthropic_translator.py` | |

### Modified files

| Path | Change |
|---|---|
| `apps/api/jarvis_api/app.py` | Register `anthropic_router`, mount middleware |
| `core/runtime/settings.py` | Add `anthropic_compat_enabled: bool = True`, `anthropic_compat_default_model: str = ""` (empty = use visible lane) |

## Anthropic Messages API protocol (what we implement)

### Request

```http
POST /anthropic/v1/messages
Host: jarvis.local
x-api-key: <api-key>
anthropic-version: 2023-06-01
content-type: application/json

{
  "model": "jarvis",
  "max_tokens": 8192,
  "system": "You are a helpful assistant in Claude Code...",
  "messages": [
    {"role": "user", "content": "List files in /tmp"},
    {"role": "assistant", "content": [
      {"type": "tool_use", "id": "toolu_01abc", "name": "Bash", "input": {"command": "ls /tmp"}}
    ]},
    {"role": "user", "content": [
      {"type": "tool_result", "tool_use_id": "toolu_01abc", "content": "file1.txt\nfile2.log"}
    ]}
  ],
  "tools": [
    {
      "name": "Read",
      "description": "Read a file from disk",
      "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}
    },
    {
      "name": "Bash",
      "description": "Run a shell command",
      "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}
    }
  ],
  "stream": true
}
```

### Response — non-streaming

```json
{
  "id": "msg_01abc",
  "type": "message",
  "role": "assistant",
  "model": "jarvis",
  "content": [
    {"type": "text", "text": "Found 2 files. Let me check them."},
    {"type": "tool_use", "id": "toolu_01def", "name": "Read", "input": {"path": "/tmp/file1.txt"}}
  ],
  "stop_reason": "tool_use",
  "stop_sequence": null,
  "usage": {"input_tokens": 0, "output_tokens": 0}
}
```

### Response — streaming SSE

```
event: message_start
data: {"type":"message_start","message":{"id":"msg_01abc","type":"message","role":"assistant","model":"jarvis","content":[],"stop_reason":null,"usage":{"input_tokens":0,"output_tokens":0}}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Found"}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":" 2 files."}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: content_block_start
data: {"type":"content_block_start","index":1,"content_block":{"type":"tool_use","id":"toolu_01def","name":"Read","input":{}}}

event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"{\"path\":\""}}

event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"/tmp/file1.txt\"}"}}

event: content_block_stop
data: {"type":"content_block_stop","index":1}

event: message_delta
data: {"type":"message_delta","delta":{"stop_reason":"tool_use","stop_sequence":null},"usage":{"output_tokens":42}}

event: message_stop
data: {"type":"message_stop"}
```

### Periodic ping

Every ~10 seconds during long-running responses:

```
event: ping
data: {"type":"ping"}
```

Keeps the SSE connection alive when the backend pauses (e.g., long-running thinking).

## Components

### `anthropic_auth.py` — API key validation + user routing

Mirrors the existing `jarvisx_user_routing_middleware` pattern. On each request:

1. Read `x-api-key` header
2. Look up in `state/anthropic_api_keys.json`:
   ```json
   {
     "_doc": "API key → user mapping for Anthropic-compat endpoint",
     "keys": {
       "jvs-bjorn-XXXXXXXXXXXXX": {"user": "bjorn", "workspace": "default"},
       "jvs-mikkel-XXXXXXXXXX": {"user": "mikkel", "workspace": "mikkel"}
     }
   }
   ```
3. If missing/invalid: return 401
4. If valid: bind workspace ContextVar (same as JarvisX middleware) so all downstream prompt-assembly reads from the right workspace files
5. Continue request

For dev: if file doesn't exist or is empty, optionally allow any key in dev mode (settings flag).

### `anthropic_identity.py` — build identity prefix

Reads from the routed workspace:

```python
def build_identity_prefix(workspace_dir: Path) -> str:
    parts = []
    for filename in ("SOUL.md", "IDENTITY.md", "USER.md", "STANDING_ORDERS.md"):
        path = workspace_dir / filename
        if path.exists():
            parts.append(f"## {filename}\n\n{path.read_text()}")
    return "\n\n".join(parts)
```

Returns ~5K tokens of identity context. Result is cached per-workspace, invalidated on file mtime change.

The final system prompt sent to the backend is:

```
<identity_prefix>

<claude_desktop_system_parameter>
```

If Claude Desktop sent no `system`, just `<identity_prefix>`.

### `anthropic_translator.py` — format translation

Two directions:

**1. Anthropic request → backend (Ollama) request**

- Anthropic `messages` (with content blocks) → Ollama `messages` (flat strings or with tool_calls)
  - User message with `[tool_result]` block → Ollama `tool` role message
  - Assistant message with `[text, tool_use]` blocks → Ollama assistant message with `tool_calls`
- Anthropic `tools` array → Ollama `tools` array (rename `input_schema` → `parameters`, `name` stays)

**2. Backend stream → Anthropic SSE state machine**

A class `AnthropicSSEEmitter` wraps a generator:

```python
class AnthropicSSEEmitter:
    def __init__(self, run_id: str, model: str):
        self.run_id = run_id
        self.model = model
        self.current_block_index = -1
        self.current_block_type = None
        self.text_started = False
        self.tool_use_started = {}  # tool_call_id -> index

    def begin_message(self) -> Iterator[str]: ...
    def text_delta(self, text: str) -> Iterator[str]: ...
    def tool_use_start(self, tool_call_id: str, name: str) -> Iterator[str]: ...
    def tool_use_input_delta(self, tool_call_id: str, partial_json: str) -> Iterator[str]: ...
    def end_message(self, stop_reason: str) -> Iterator[str]: ...
    def ping(self) -> Iterator[str]: ...
```

Each method yields properly-formatted `event: <name>\ndata: <json>\n\n` chunks. The state machine ensures `content_block_start` precedes any deltas, and `content_block_stop` is emitted before transitioning to a new block.

### `anthropic_compat.py` — the endpoint

```python
@router.post("/anthropic/v1/messages")
async def messages(request: Request) -> JSONResponse | StreamingResponse:
    body = await request.json()
    user, workspace_dir = _resolve_user_from_api_key(request)

    backend_request = translate_anthropic_to_backend(
        anthropic_body=body,
        identity_prefix=build_identity_prefix(workspace_dir),
        backend_model=resolve_backend_model(body.get("model")),
    )

    if body.get("stream"):
        return StreamingResponse(
            _stream_anthropic_response(backend_request, body),
            media_type="text/event-stream",
        )
    return JSONResponse(_drain_to_anthropic_response(backend_request, body))
```

The streaming generator drives `AnthropicSSEEmitter` by reading the backend's stream chunks and translating them.

### `/anthropic/v1/models` — model list

Returns just `jarvis` (and any other models we want to expose):

```json
{
  "data": [
    {"id": "jarvis", "type": "model", "display_name": "Jarvis", "created_at": "2026-05-06T00:00:00Z"}
  ],
  "has_more": false,
  "first_id": "jarvis",
  "last_id": "jarvis"
}
```

## Data flow per request

### First turn (user → assistant text + tool_use)

1. Claude Desktop: user types "List /tmp". Claude Desktop sends `POST /anthropic/v1/messages` with `tools=[Read, Bash, ...]`, `messages=[{user: "List /tmp"}]`, `stream=true`
2. Anthropic-compat middleware: validate `x-api-key`, set workspace ContextVar
3. Endpoint: build identity prefix from `workspaces/<user>/`, translate body to Ollama-format request
4. Send to Ollama (`glm-5.1:cloud`)
5. Ollama streams: text "Looking at /tmp..." then a tool_call `{"name": "Bash", "arguments": {"command": "ls /tmp"}}`
6. AnthropicSSEEmitter emits:
   - `message_start`
   - `content_block_start` (text, index 0)
   - `content_block_delta` × N (text_delta chunks)
   - `content_block_stop` (text)
   - `content_block_start` (tool_use, index 1, name="Bash")
   - `content_block_delta` × M (input_json_delta chunks streaming the input)
   - `content_block_stop` (tool_use)
   - `message_delta` (stop_reason="tool_use")
   - `message_stop`
7. Claude Desktop sees the tool_use, executes Bash locally, captures output

### Second turn (with tool_result)

1. Claude Desktop sends new request with full history including the `tool_use` from last assistant message and a new user message with `tool_result` block
2. Anthropic-compat translates: `tool_result` → Ollama `tool` role message
3. Send to Ollama with full conversation
4. Ollama responds with text "Done. /tmp has 2 files."
5. AnthropicSSEEmitter emits text-only sequence ending in `stop_reason="end_turn"`

## Error handling & fallback

| Failure | Detection | Response |
|---|---|---|
| Missing/invalid `x-api-key` | Auth middleware | 401 with Anthropic error format |
| Unknown user/workspace | Auth middleware | 401, log warning |
| Workspace files missing | Identity builder | Continue with whatever exists; log warning |
| Backend provider unreachable | Try/except wrapper | 502 with Anthropic error format |
| Backend timeout | 60s timeout on backend call | Emit `message_delta` with `stop_reason="error"` then `message_stop` (close stream gracefully) |
| Tool translation fails (malformed schema) | Validation | 400 with details |
| `model` parameter unknown | Resolver | Default to visible-lane model with log |

### Anthropic error envelope

Anthropic-format errors look like:

```json
{
  "type": "error",
  "error": {"type": "authentication_error", "message": "Invalid API key"}
}
```

Use this format for all 4xx/5xx responses.

## Multi-user isolation

Each request resolves to a single user via `x-api-key`. The user's workspace ContextVar is set BEFORE any prompt assembly, so all reads of USER.md, MEMORY.md, etc. come from `workspaces/<user>/`.

For Mode 3 (memory access): each user gets their own brain context. Bjørn's recall doesn't see Mikkel's memories.

## Testing

### Unit tests

- `anthropic_translator`: round-trip Anthropic → Ollama → Anthropic for text-only, tool_use, multi-turn
- `anthropic_identity`: build prefix with all files, with missing files, with empty workspace
- `anthropic_auth`: valid key, invalid key, missing key, key with no workspace
- `AnthropicSSEEmitter`: emits events in correct order, handles text → tool_use transition

### Integration tests

- `POST /anthropic/v1/messages` non-streaming with text-only response
- `POST /anthropic/v1/messages` streaming with text + tool_use
- Multi-turn with tool_result feedback
- `GET /anthropic/v1/models`

### Manual validation

- Connect Claude Code with `ANTHROPIC_BASE_URL=http://localhost/anthropic` + valid API key
- Ask: "Read /etc/hostname"
- Verify: Claude Code shows tool approval, executes Read, sends result back, Jarvis responds with hostname
- Verify: Jarvis-flavoured responses (Danish, warm tone, knows USER.md context)

## Rollout

1. Build under feature flag `anthropic_compat_enabled` (default true)
2. First user: Bjørn with a single API key in `state/anthropic_api_keys.json`
3. Test with Claude Code locally
4. Once stable, generate Mikkel's key and add him to the mapping

### Killswitch

`anthropic_compat_enabled: bool = True` in settings. If false, endpoint returns 503 with explanation.

## Mode 3 — follow-up (separate plan)

After Mode 2 is stable, add Jarvis's internal tools to the toolset alongside Claude Desktop's:

- `recall_memories(query)`
- `search_jarvis_brain(query)`
- `remember_this(content)`
- `search_memory(query)`
- Possibly `read_decisions`, `read_chronicles`

These are emitted as additional Anthropic tools in the `tools` array sent to the backend. When Jarvis decides to call one, it surfaces as Anthropic `tool_use` to Claude Desktop, **but Claude Desktop won't have a handler for them**. Two options:

- **Option A**: Mark them as "internal" — execute on Jarvis's side before returning to Claude Desktop. Means we DO need to suspend mid-stream, execute, continue. More complex.
- **Option B**: Define them as MCP tools that Claude Desktop loads from a Jarvis MCP server. Claude Desktop already supports MCP, so it would handle them naturally.

Mode 3 picks one of these — design TBD when we get there.

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Backend (Ollama+glm) tool-call format diverges from Anthropic | Translator unit-tested round-trip; fallback to text-only if translation fails |
| Anthropic SSE state machine bugs cause Claude Code to hang | Emit `message_stop` always, even on error; add `ping` events |
| Claude Code expects features we don't implement (cache, vision) | Return 501 with clear error if unknown feature requested |
| Multi-user data leakage | ContextVar set before any read; tests verify isolation |
| API keys leaked in logs | Never log key value; only log first 4 chars + user |

## Success criteria

- Bjørn can connect Claude Code to `/anthropic/v1/messages` with his API key and have a multi-turn conversation that uses Read, Bash, Edit tools on his local machine
- Jarvis's identity (Danish, USER.md awareness, SOUL.md tone) is preserved in responses
- Mikkel can connect with his own API key and gets Mikkel's USER.md context, not Bjørn's
- Streaming feels fluid (no long pauses without ping)
- Error cases return Anthropic-format error envelopes (Claude Code parses them correctly)
- Killswitch disables the endpoint cleanly

## Out of scope (deferred)

- Mode 3 (Jarvis's internal tools alongside Claude Desktop's) — separate plan
- Anthropic prompt caching (`cache_control`) — not currently used by us
- Anthropic batch API — not needed
- Vision content blocks (image input) — Mode 2 doesn't handle them; reject with 501 if sent
- Token counting (real input/output token numbers) — return 0 for now, same as OpenAI-compat
- MCP server inside Jarvis (for Mode 3 Option B) — separate concern
