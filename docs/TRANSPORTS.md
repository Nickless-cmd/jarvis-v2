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
