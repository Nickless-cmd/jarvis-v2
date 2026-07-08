---
status: færdig
audited: 2026-07-08
ground_truth: "Verified against: (1) apps/api/jarvis_api/routes/chat.py — POST /chat/stream returns StreamingResponse(media_type="text/event-stream"); (2) apps/api/jarvis_api/routes/chat_stream_v2.py — POST /chat/stream/v2 returns SSE-formatted streams; (3) apps/api/jarvis_api/routes/live.py — "
---
# Jarvis V2 Transports

## Chat transport
Use HTTP streaming or SSE for assistant reply streaming.

## Realtime/control-plane transport
Use WebSocket for:
- live events
- token telemetry
- tool activity
- Mission Control stream
- approvals
- heartbeat
- channel status

## Rule
Do not force chat streaming and control-plane events into one opaque transport.
