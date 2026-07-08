---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# /chat/stream/v2 — Anthropic-style SSE protocol for Jarvis

**Status:** spec
**Author:** Claude (med Bjørn)
**Created:** 2026-06-10

## Mål

Etablér et nyt SSE-endpoint `/chat/stream/v2` der taler en Anthropic-style protokol
(message_start → content_block_* → message_stop) som **fundament** for den nye
`jarvis-desk` app der bygges parallelt med JarvisX.

Eksisterende `/chat/stream` rører vi ikke — JarvisX bruger den uændret.

## Hvorfor

Nuværende SSE-protokol har vokset organisk med 10+ ad hoc event-typer
(delta, working_step, capability, heartbeat, turn_changelog, steer_received,
approval_request, done, etc.). Hver klient skal håndtere hver event-type manuelt
og der findes ingen formel kontrakt.

Anthropic's API-protokol er principielt designet med:
- **Indekserede content blocks** for at supportere interleaved tekst/thinking/tool_use
- **Streaming af tool-args** (input_json_delta) så UI kan vise partial tool-arguments
- **Thinking som separat stream** (thinking_delta) for reasoning-modeller
- **Indbygget ping** (hver 5s) i stedet for ad hoc keepalive
- **Klar stop_reason** kommunikation
- **Standardiseret** — kan i fremtiden ramme Claude API direkte uden frontend-ændringer

## Wire-protocol

### Anthropic-base events (1:1 fra Claude API)

```
event: message_start
data: {"type":"message_start","message":{"id":"visible-xxx","model":"deepseek-v4-flash",
       "session_id":"chat-xxx","lane":"primary","provider":"deepseek",
       "usage":{"input_tokens":0,"output_tokens":0}}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hej "}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"thinking_delta","thinking":"..."}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: content_block_start
data: {"type":"content_block_start","index":1,
       "content_block":{"type":"tool_use","id":"toolu_xxx","name":"bash_session_run","input":{}}}

event: content_block_delta
data: {"type":"content_block_delta","index":1,
       "delta":{"type":"input_json_delta","partial_json":"{\"command\":\"ls"}}

event: content_block_stop
data: {"type":"content_block_stop","index":1}

event: message_delta
data: {"type":"message_delta","delta":{"stop_reason":"end_turn"},
       "usage":{"output_tokens":127,"cache_hit_tokens":11008}}

event: message_stop
data: {"type":"message_stop"}

event: ping
data: {"type":"ping"}
```

### Jarvis-extension events (system_event-wrapper)

Domæne-specifikke ting som ikke passer i Anthropic-skema → indpakkes som
`system_event` med struktureret payload, så klienter let kan ignorere typer
de ikke kender:

```
event: system_event
data: {"type":"system_event","kind":"capability","payload":{
       "type":"tool_approved","tool":"operator_bash","auto":true}}

event: system_event
data: {"type":"system_event","kind":"approval_request","payload":{
       "approval_id":"approval-xxx","tool":"operator_bash","action":"sudo rm",
       "risk":"destructive","classification":"destructive"}}

event: system_event
data: {"type":"system_event","kind":"steer_received","payload":{
       "content":"...","at":"2026-06-10T17:23:00Z"}}

event: system_event
data: {"type":"system_event","kind":"working_step","payload":{
       "action":"bash_session_run","detail":"ls /tmp","step":3,"status":"running"}}

event: system_event
data: {"type":"system_event","kind":"turn_changelog","payload":{...}}
```

## Arkitektur

```
Klient (jarvis-desk)
    ↓ GET /chat/stream/v2?session_id=xxx
    
apps/api/jarvis_api/routes/chat_stream_v2.py
    ↓ kalder
    
core/services/visible_runs.py::stream_visible_chat(...)  ← uændret
    ↓ yielder eksisterende SSE-events
    
core/services/visible_runs_sse_v2.py::translate_to_v2(legacy_iter)  ← NY
    ↓ konverterer hvert legacy event til Anthropic-style
    
apps/api/jarvis_api/sse_v2_events.py  ← NY
    Event-dataclasses + to_sse_line() metoder
    ↓ wire-formatted SSE-streng
    
Klient parser standardiseret protokol
```

## Translatering

Mapping fra legacy → v2:

| Legacy event | V2 emission |
|--------------|-------------|
| (run start) | `message_start` + `content_block_start(index=0, type=text)` |
| `delta` | `content_block_delta(index=current_text_block, text_delta)` |
| `working_step` | `system_event(kind=working_step)` |
| `capability` | `system_event(kind=capability)` |
| `approval_request` | `system_event(kind=approval_request)` |
| `steer_received` | `system_event(kind=steer_received)` |
| `turn_changelog` | `system_event(kind=turn_changelog)` |
| `heartbeat` | (skip — v2 har sin egen ping) |
| `done` | `content_block_stop(index=last)` + `message_delta(usage)` + `message_stop` |

Translator-state der skal holdes per-stream:
- Current text-block index (starter 0, øges når thinking eller tool-use indskydes)
- Current thinking-block index (når reasoning_content modtages)
- Current tool-use block indices (per tool_call_id)
- Akkumuleret input_json for hver tool-use (til to vise partial JSON)
- Background ping-task (hver 5s yielder ping)

## Implementation phases

### Phase 1 — Skeleton (denne session)
- `apps/api/jarvis_api/sse_v2_events.py` med event-dataclasses
- `core/services/visible_runs_sse_v2.py` med basic translator (text-delta + done)
- `apps/api/jarvis_api/routes/chat_stream_v2.py` med endpoint
- Wire-test med curl: send besked, se v2-format komme ud

### Phase 2 — Komplet feature-parity
- Thinking_delta support (reasoning_content fra DeepSeek)
- Tool-use blocks (working_step → tool_use + input_json_delta)
- Alle system_event types
- Ping-task hver 5s

### Phase 3 — Klient-bibliotek
- TypeScript SSE-parser i `apps/jarvis-desk/src/lib/streamClient.ts`
- React-hook `useStream()` der konsumerer protokollen

## Backward-kompatibilitet

`/chat/stream` ændres ikke. JarvisX bliver ved med at virke uændret.

Når jarvis-desk når feature-parity og er stabilt → vi kan deprecate
`/chat/stream` på sigt. Men ingen presse.

## Test-strategi

For hver Phase: lille pytest der mocker en visible-run og sammenligner
output med forventet v2-event sekvens. Integration test med curl mod
live api server som sanity check.
