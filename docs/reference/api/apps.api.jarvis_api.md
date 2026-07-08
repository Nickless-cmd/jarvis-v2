# `apps.api.jarvis_api` — reference

> Generated 2026-07-08 from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `apps/api/jarvis_api/__init__.py`

_(no top-level classes or functions)_

## `apps/api/jarvis_api/app.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_runtime_services_enabled` | `()` | — | [src](../../../apps/api/jarvis_api/app.py#L135) |
| function | `create_app` | `()` | — | [src](../../../apps/api/jarvis_api/app.py#L140) |

## `apps/api/jarvis_api/mcp_server.py`
_Jarvis MCP server — exposes memory, identity, state, and chat via Streamable HTTP._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `jarvis_memory_read` | `()` | Read Jarvis' cross-session memory (MEMORY.md). | [src](../../../apps/api/jarvis_api/mcp_server.py#L34) |
| function | `jarvis_memory_write` | `(content)` | Overwrite Jarvis' cross-session memory (MEMORY.md). | [src](../../../apps/api/jarvis_api/mcp_server.py#L47) |
| function | `jarvis_chat_sessions` | `(limit=…)` | List Jarvis' chat sessions with metadata. | [src](../../../apps/api/jarvis_api/mcp_server.py#L58) |
| function | `jarvis_chat_history` | `(session_id, limit=…)` | Get messages from a specific Jarvis chat session. | [src](../../../apps/api/jarvis_api/mcp_server.py#L67) |
| function | `jarvis_identity` | `()` | Read Jarvis' identity files (SOUL.md, IDENTITY.md, USER.md). | [src](../../../apps/api/jarvis_api/mcp_server.py#L86) |
| function | `jarvis_cognitive_state` | `()` | Get Jarvis' current cognitive state: inner voice, self-model, retained memory. | [src](../../../apps/api/jarvis_api/mcp_server.py#L102) |
| function | `jarvis_retained_memories` | `(limit=…)` | Get Jarvis' cross-session retained memory records. | [src](../../../apps/api/jarvis_api/mcp_server.py#L118) |
| function | `jarvis_events` | `(limit=…, kind=…)` | Get recent Jarvis eventbus events, optionally filtered by kind prefix. | [src](../../../apps/api/jarvis_api/mcp_server.py#L127) |
| function | `jarvis_chat` | `(message, session_id=…)` | Send a message to Jarvis through his visible run pipeline. | [src](../../../apps/api/jarvis_api/mcp_server.py#L143) |
| function | `resource_memory` | `()` | Jarvis' cross-session memory. | [src](../../../apps/api/jarvis_api/mcp_server.py#L210) |
| function | `resource_identity` | `()` | Jarvis' combined identity files. | [src](../../../apps/api/jarvis_api/mcp_server.py#L218) |
| function | `resource_chat_session` | `(session_id)` | A specific Jarvis chat session with all messages. | [src](../../../apps/api/jarvis_api/mcp_server.py#L233) |
| function | `_get_or_create_mcp_session` | `()` | Return or create a persistent MCP chat session. | [src](../../../apps/api/jarvis_api/mcp_server.py#L248) |
| function | `jarvis_central_status` | `()` | Central-helbred: status (green/yellow/red), uløste flag/incidents, degrading-clusters, | [src](../../../apps/api/jarvis_api/mcp_server.py#L271) |
| function | `jarvis_central_diagnostics` | `()` | Fuld central-diagnostik: uløste incidents (fuld besked), anomalier, root-causes, | [src](../../../apps/api/jarvis_api/mcp_server.py#L296) |
| function | `jarvis_central_timeseries` | `()` | Per-nerve tidsserie MERGET på tværs af processer (runtime+api). Lukker cross-proces- | [src](../../../apps/api/jarvis_api/mcp_server.py#L317) |
| function | `jarvis_central_nerve` | `(nerve)` | Seneste observationer/beslutninger for én central-nerve (fx central_meta, lifecycle, | [src](../../../apps/api/jarvis_api/mcp_server.py#L333) |
| function | `jarvis_central_resolve` | `()` | Luk (resolve) alle uløste central-flag/incidents. Rydder tavlen efter review. | [src](../../../apps/api/jarvis_api/mcp_server.py#L352) |
| function | `jarvis_memory_search` | `(query, limit=…)` | Søg Jarvis' sansninger/hukommelse (sensory memory) semantisk. Sparer at grave manuelt. | [src](../../../apps/api/jarvis_api/mcp_server.py#L371) |
| function | `jarvis_central_command` | `(line)` | FULD central-terminal (write): status/incidents/trace/nerve/toggle/resolve/scan/providers. | [src](../../../apps/api/jarvis_api/mcp_server.py#L385) |
| function | `jarvis_central_shadow` | `()` | M1 skygge-lag: hvad Centralen VILLE gøre (reaktioner fra lærings-forslag) + prædiktioner | [src](../../../apps/api/jarvis_api/mcp_server.py#L400) |
| function | `jarvis_chat_search` | `(query, limit=…)` | Søg Jarvis' chat-historik (samtaler med Bjørn) på tekst. Sparer manuel DB-gravning. | [src](../../../apps/api/jarvis_api/mcp_server.py#L416) |
| function | `_safe_dict` | `(obj)` | Convert a DB record to a JSON-safe dict. | [src](../../../apps/api/jarvis_api/mcp_server.py#L437) |
| function | `create_mcp_app` | `()` | Create the ASGI app for mounting in FastAPI. | [src](../../../apps/api/jarvis_api/mcp_server.py#L451) |

## `apps/api/jarvis_api/sse_v2_events.py`
_SSE v2 event-dataclasses — Anthropic-style streaming protocol._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_sse_format` | `(event_name, data)` | SSE-format: event + data + blank line. | [src](../../../apps/api/jarvis_api/sse_v2_events.py#L28) |
| class | `MessageStart` | `` | Markerer starten på et nyt assistant-svar. | [src](../../../apps/api/jarvis_api/sse_v2_events.py#L34) |
| method | `MessageStart.to_sse_line` | `(self)` | Returnér message_start SSE-blokken med run-metadata og nul-usage. | [src](../../../apps/api/jarvis_api/sse_v2_events.py#L46) |
| class | `ContentBlockStart` | `` | Markerer start på en content-block (text, thinking, eller tool_use). | [src](../../../apps/api/jarvis_api/sse_v2_events.py#L62) |
| method | `ContentBlockStart.to_sse_line` | `(self)` | Returnér content_block_start SSE-blokken; content_block afhænger af block_type. | [src](../../../apps/api/jarvis_api/sse_v2_events.py#L74) |
| class | `ContentBlockDelta` | `` | Inkrementelt indhold til en aktiv content-block. | [src](../../../apps/api/jarvis_api/sse_v2_events.py#L96) |
| method | `ContentBlockDelta.to_sse_line` | `(self)` | Returnér content_block_delta SSE-blokken; delta-feltet afhænger af delta_type. | [src](../../../apps/api/jarvis_api/sse_v2_events.py#L108) |
| class | `ContentBlockStop` | `` | Markerer at en bestemt content-block er færdig. | [src](../../../apps/api/jarvis_api/sse_v2_events.py#L125) |
| method | `ContentBlockStop.to_sse_line` | `(self)` | Returnér content_block_stop SSE-blokken for den angivne block-index. | [src](../../../apps/api/jarvis_api/sse_v2_events.py#L133) |
| class | `MessageDelta` | `` | Opdaterer message-level metadata mod slutningen. | [src](../../../apps/api/jarvis_api/sse_v2_events.py#L142) |
| method | `MessageDelta.to_sse_line` | `(self)` | Returnér message_delta SSE-blokken med stop_reason og final usage-tal. | [src](../../../apps/api/jarvis_api/sse_v2_events.py#L154) |
| class | `MessageStop` | `` | Sidste event — assistant-svaret er færdigt. | [src](../../../apps/api/jarvis_api/sse_v2_events.py#L169) |
| method | `MessageStop.to_sse_line` | `(self)` | Returnér den afsluttende message_stop SSE-blok. | [src](../../../apps/api/jarvis_api/sse_v2_events.py#L172) |
| class | `Ping` | `` | Keepalive event hver ~5s under streaming. | [src](../../../apps/api/jarvis_api/sse_v2_events.py#L178) |
| method | `Ping.to_sse_line` | `(self)` | Returnér ping keepalive SSE-blokken. | [src](../../../apps/api/jarvis_api/sse_v2_events.py#L185) |
| class | `SystemEvent` | `` | Jarvis-specifik extension der ikke passer i Anthropic-skema. | [src](../../../apps/api/jarvis_api/sse_v2_events.py#L191) |
| method | `SystemEvent.to_sse_line` | `(self)` | Returnér system_event SSE-blokken med kind og payload. | [src](../../../apps/api/jarvis_api/sse_v2_events.py#L205) |

