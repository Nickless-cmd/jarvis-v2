---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# JarvisX Tool-Bridge — Design Spec

**Status**: MVP design, 2026-05-26
**Context**: Post-migration. Jarvis lives on 10.0.0.39 LXC. JarvisX Electron-app lives on operator's desktop (CheifOne). Previously they shared filesystem; now they don't.

## Problem

When Jarvis is asked to "see X on my desktop" / "read Y file", his existing `read_file`/`find_files`/etc. tools operate on the LXC filesystem — not the operator's desktop. The operator expects Claude-Code-style: tool-calls execute on the operator's local machine, not where the agent runs.

Previously this "worked" only because Jarvis lived on the same host as the operator. Migration broke the assumption.

## Goal

Build a Claude-Code-style **tool-bridge**: JarvisX-app maintains an outbound WebSocket to Jarvis-runtime. When Jarvis invokes a `bridge_*` tool, the runtime dispatches the call over WS to JarvisX, which executes it locally and returns the result.

## Architecture

```
┌─────────────────────────────────┐         ┌──────────────────────────┐
│  JarvisX Electron app           │  WS     │  Jarvis-runtime          │
│  (CheifOne — operator desktop)  │◄───────►│  (LXC 10.0.0.39)         │
│                                 │         │                          │
│  • Opens outbound WS on launch  │         │  • /api/jarvisx-bridge   │
│  • Auth: X-JarvisX-User token   │         │  • Registers active      │
│  • Local tool executors         │         │    bridges per user_id   │
│    (fs.readFile, shell, etc.)   │         │  • bridge_* tools route  │
│  • Sends results back over WS   │         │    via dispatch_bridge() │
└─────────────────────────────────┘         └──────────────────────────┘
```

## Message protocol (JSON over WS, bidirectional)

**Runtime → bridge** (tool invocation):
```json
{
  "type": "tool_invoke",
  "correlation_id": "uuid-v4",
  "tool": "operator_read_file",
  "args": {"path": "/home/bs/x.txt"},
  "timeout_ms": 30000
}
```

**Bridge → runtime** (result):
```json
{
  "type": "tool_result",
  "correlation_id": "uuid-v4",
  "status": "ok" | "error",
  "result": "...file contents..." | null,
  "error": null | "ENOENT: file not found"
}
```

**Bridge → runtime** (registration on connect):
```json
{
  "type": "register",
  "user_id": "1246415163603816499",
  "client": "jarvisx-electron",
  "version": "0.x.y",
  "platform": "linux-x64",
  "capabilities": ["read_file", "find_files", "run_shell", "screenshot"]
}
```

**Both directions** (keepalive):
```json
{"type": "ping"} → {"type": "pong"}
```

## Auth

- Bridge connects with `Authorization: Bearer <jarvisx_auth_token>` header on WS handshake
- Runtime verifies token via existing `core/runtime/jarvisx_auth.py`
- User-ID extracted from token claims
- Only ONE active bridge per user_id at a time (newer replaces older)

## MVP tool set (Phase 1)

Five tools that prove the model:

| Tool | Args | Returns | Risk |
|---|---|---|---|
| `operator_read_file` | `path` | content (str) | Low — read-only |
| `operator_find_files` | `pattern, max_results` | list[path] | Low |
| `operator_list_dir` | `path` | list[entry] | Low |
| `operator_screenshot` | `monitor?` | base64 PNG | Low — picture only |
| `operator_run_shell` | `command, timeout_s` | stdout/stderr/exit | **HIGH — needs approval-flow** |

`operator_write_file`, `operator_edit_file` etc. deferred to Phase 2 — write ops should go through proper approval/staged-edit pattern.

## Permission flow (MVP)

- Read ops (`read_file`, `find_files`, `list_dir`, `screenshot`): auto-approved
- Write/exec ops (`run_shell`): JarvisX-app shows confirmation dialog to operator BEFORE executing, with full command preview
- Future: per-user policy in runtime.json (e.g. "allow shell on these paths only")

## Failure modes

| Scenario | Behavior |
|---|---|
| Bridge not connected | Tool returns `error: bridge_not_connected`, Jarvis informs user |
| Bridge timeout (30s) | Tool returns `error: bridge_timeout`, correlation_id discarded |
| Bridge crashes during call | WS disconnect → all pending calls fail with `bridge_disconnected` |
| Auth fails on connect | WS closes with code 1008 |
| Network partition | Bridge reconnects automatically with backoff (1s, 2s, 4s, ...) |

## Non-goals (deferred)

- Multi-user bridge (one Bjørn for now)
- Encrypted message body (TLS at WS layer is enough — internal network)
- Tool-result caching / dedup
- Bridge-side rate limiting

## Implementation phases

**Phase 1 (this session)**: Connectivity + ONE tool (operator_read_file) end-to-end.
**Phase 2**: Remaining read-only tools (find_files, list_dir, screenshot).
**Phase 3**: run_shell with approval-flow.
**Phase 4**: Write-ops (write_file, edit_file) with staged-edit integration.

## Files

**New (runtime)**:
- `apps/api/jarvis_api/routes/jarvisx_bridge.py` — WS endpoint
- `core/services/jarvisx_bridge.py` — bridge registry + dispatch
- `core/tools/operator_tools.py` — Python tool wrappers
- `tests/test_jarvisx_bridge.py` — unit tests

**New (Electron)**:
- `apps/jarvisx/electron/bridge.ts` — WS client + tool executors
- Modify `apps/jarvisx/electron/main.ts` — bootstrap bridge on app start

**Modified**:
- `core/tools/simple_tools.py` — register operator_* tools
- `apps/jarvisx/package.json` — add `ws` dependency

## Tests

- `test_bridge_register`: WS connects, sends register message, bridge appears in registry
- `test_bridge_invoke_read_file`: dispatch operator_read_file, mock bridge responds with content
- `test_bridge_timeout`: bridge doesn't respond → tool returns error after 30s
- `test_bridge_disconnect_clears_registry`: WS disconnect → bridge gone from registry
- `test_bridge_auth_required`: unauthenticated WS → 1008 close
