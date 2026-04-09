# Jarvis MCP Server + OpenAI-Compatible Proxy

**Date:** 2026-04-09
**Status:** Approved
**Author:** Claude + Bjørn

## Summary

Expose Jarvis V2 as both an MCP server and an OpenAI-compatible API proxy so external tools (Claude Code, Cursor, Windsurf, etc.) can access Jarvis' memory, identity, cognitive state, and chat capabilities — with full session continuity across webchat and editor integrations.

## Goals

1. **MCP server** with passive tools (read/write memory, chat history, identity, state) and one active tool (`jarvis_chat`) that sends messages through the full visible run pipeline
2. **OpenAI-compatible proxy** (`/v1/chat/completions`) that wraps any request with Jarvis' identity, memory, and prompt assembly
3. **Integrated in the existing FastAPI app** — shared DB, eventbus, config, cost tracking
4. **Model flexibility** — client can specify model or fall back to visible lane default

## Non-Goals

- Replacing the webchat UI or Mission Control
- Running MCP as a separate process
- Authentication/multi-user support (single-user local system)
- Tool forwarding (Jarvis' 8 simple tools are for his own use, not exposed via MCP)

---

## Part 1: MCP Server

### Transport

Streamable HTTP via FastMCP, mounted in FastAPI at `/mcp`.

Claude Code configuration:
```bash
claude mcp add --transport http jarvis http://localhost:8010/mcp
```

### Tools — Passive (Read/Write State)

| Tool | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `jarvis_memory_read` | — | string | Full MEMORY.md content |
| `jarvis_memory_write` | `content: str` | confirmation | Overwrite MEMORY.md |
| `jarvis_chat_sessions` | `limit?: int` | session list | List chat sessions with metadata |
| `jarvis_chat_history` | `session_id: str, limit?: int` | message list | Messages from a specific session |
| `jarvis_identity` | — | dict | SOUL.md + IDENTITY.md + USER.md extracts |
| `jarvis_cognitive_state` | — | dict | Inner voice, affective state, self-model snapshot |
| `jarvis_retained_memories` | `limit?: int` | record list | Cross-session retained memory records |
| `jarvis_events` | `limit?: int, kind?: str` | event list | Recent eventbus events, optionally filtered |

### Tools — Active (Visible Lane Conversation)

| Tool | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `jarvis_chat` | `message: str, session_id?: str` | Jarvis' response text | Send message through full visible run pipeline. Jarvis reflects, updates state, builds memory. If no session_id, uses or creates a default MCP session. |

`jarvis_chat` executes a complete visible run:
1. Appends user message to chat_messages
2. Builds prompt assembly (identity, memory, cognitive state, transcript)
3. Resolves provider/model from visible lane config
4. Executes model (with tool calling if applicable)
5. Tracks signals (development focus, goals, world model, etc.)
6. Appends assistant response to chat_messages
7. Records cost
8. Publishes eventbus events
9. Returns the response text

### MCP Resources

| Resource | URI | Description |
|----------|-----|-------------|
| Memory | `jarvis://memory` | MEMORY.md content as text resource |
| Chat session | `jarvis://chat/{session_id}` | Full session with all messages |
| Identity | `jarvis://identity` | Combined identity files |

---

## Part 2: OpenAI-Compatible Proxy

### Endpoint

`POST /v1/chat/completions`

Accepts standard OpenAI chat completion request format. Wraps with Jarvis' identity and prompt assembly before forwarding to the underlying model.

### Request Format

```json
{
  "model": "minimax-m2.7:cloud",
  "messages": [
    {"role": "user", "content": "Hvad lavede vi i går?"}
  ],
  "stream": true,
  "temperature": 0.7
}
```

### Model Routing

| model parameter | Routes to |
|----------------|-----------|
| `"jarvis"` or omitted | Visible lane default from provider-router.json |
| `"minimax-m2.7:cloud"` | Ollama with that model |
| `"glm-5.1:cloud"` | Ollama with that model |
| `"gemma4:32b-cloud"` | Ollama with that model |
| `"gpt-4o"` | OpenAI provider |
| `"copilot/gpt-4o"` | GitHub Copilot provider |

Model-to-provider mapping: if model name contains `:cloud` or is a known Ollama model → ollama. If starts with `gpt-` or `o1-` → openai. If starts with `copilot/` → github-copilot. Otherwise → visible lane default provider.

### Response Format

Standard OpenAI chat completion response:

```json
{
  "id": "jarvis-run-abc123",
  "object": "chat.completion",
  "created": 1712678400,
  "model": "minimax-m2.7:cloud",
  "choices": [
    {
      "index": 0,
      "message": {"role": "assistant", "content": "I går arbejdede vi på..."},
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 1200,
    "completion_tokens": 150,
    "total_tokens": 1350
  }
}
```

Streaming returns `text/event-stream` with OpenAI-format SSE chunks:
```
data: {"id":"jarvis-run-abc123","object":"chat.completion.chunk","choices":[{"delta":{"content":"I går"},"index":0}]}

data: {"id":"jarvis-run-abc123","object":"chat.completion.chunk","choices":[{"delta":{"content":" arbejdede"},"index":0}]}

data: [DONE]
```

### Prompt Assembly

The proxy does NOT pass through client messages verbatim. It:

1. Extracts the latest user message from `messages[]`
2. Optionally extracts a session_id from request headers (`X-Jarvis-Session`) or creates one
3. Builds full prompt assembly via `build_visible_chat_prompt_assembly()` which includes:
   - Jarvis' identity (SOUL, IDENTITY, USER)
   - Memory (MEMORY.md, retained memories)
   - Cognitive state (inner voice, self-model, affective state)
   - Recent transcript from the session
   - Tool calling instructions
4. Sends to model via `stream_visible_model()` or `execute_visible_model()`
5. Records everything in DB (chat_messages, visible_runs, costs, events)

### Session Continuity

- Each proxy conversation gets a chat_session in Jarvis' DB
- Session ID can be passed via `X-Jarvis-Session` header
- If not provided, proxy creates a session titled "Claude Code — {timestamp}"
- Sessions are visible in webchat and Mission Control
- Transcript from previous messages in the session is included in prompt assembly

### Claude Code Configuration

```json
{
  "apiProvider": "openai-compatible",
  "apiBaseUrl": "http://localhost:8010/v1",
  "apiModelId": "jarvis"
}
```

Or with a specific model:
```json
{
  "apiProvider": "openai-compatible",
  "apiBaseUrl": "http://localhost:8010/v1",
  "apiModelId": "minimax-m2.7:cloud"
}
```

---

## Part 3: Integration

### Shared State

Both MCP server and OpenAI proxy run in the same FastAPI process and share:
- SQLite database (chat_sessions, events, costs, visible_runs, memory tables)
- Eventbus (publish/subscribe)
- Provider router configuration
- Identity and memory modules
- Runtime settings

### Eventbus Events

| Event | Source | Description |
|-------|--------|-------------|
| `mcp.tool_invoked` | MCP server | Any MCP tool called |
| `mcp.tool_completed` | MCP server | MCP tool finished |
| `mcp.chat_sent` | MCP jarvis_chat | Message sent through visible lane via MCP |
| `proxy.request_received` | OpenAI proxy | Incoming proxy request |
| `visible.run_started` | Both (via visible_runs) | Visible run started |
| `visible.run_completed` | Both (via visible_runs) | Visible run finished |

Mission Control sees all activity regardless of source (webchat, MCP, proxy).

### Cost Tracking

Both paths record via `record_cost(lane, provider, model, input_tokens, output_tokens, cost_usd)`. Mission Control shows total cost per lane/provider/source.

---

## File Changes

### New Files

| File | Purpose | ~Lines |
|------|---------|--------|
| `apps/api/jarvis_api/mcp_server.py` | FastMCP server with all tools + resources | ~250 |
| `apps/api/jarvis_api/routes/openai_compat.py` | `/v1/chat/completions` endpoint | ~300 |

### Modified Files

| File | Change |
|------|--------|
| `apps/api/jarvis_api/app.py` | Mount MCP server at `/mcp`, include openai_compat router at `/v1` |
| `requirements.txt` or equivalent | Add `fastmcp` dependency |

### Unchanged Files

- `visible_model.py` — used as-is by both MCP and proxy
- `visible_runs.py` — used as-is for `jarvis_chat` and proxy
- `prompt_contract.py` — used as-is for prompt assembly
- `chat_sessions.py` — used as-is for persistence
- `eventbus/bus.py` — used as-is for event publishing
- `provider_router.py` — used as-is for model routing
- All webchat and Mission Control code — untouched

---

## Verification

1. **Syntax check:** `python -m compileall apps/api`
2. **MCP tools test:** `claude mcp add --transport http jarvis http://localhost:8010/mcp` then use tools in Claude Code
3. **Proxy test:** Configure Claude Code with `apiBaseUrl: http://localhost:8010/v1`, send message, verify response
4. **Session continuity:** Send message via proxy, check it appears in webchat session list
5. **Memory read/write:** Use `jarvis_memory_read` in Claude Code, verify MEMORY.md content. Write something, verify it persists.
6. **jarvis_chat:** Send message via MCP `jarvis_chat`, verify Jarvis responds with identity/memory context, verify visible_run created in DB
7. **Cost tracking:** Verify Mission Control shows costs from MCP and proxy usage
8. **Eventbus:** Verify Mission Control live stream shows MCP and proxy events
