# Chatview + auto-compact — grounded readonly-analyse (2026-07-07)

Readonly. Ingen kode ændret. Verificeret mod live-repo. Formål: præcis rod-årsag til at
chatview føles "massiv og upålidelig", + auto-compact-billedet, som grundlag for én
konsistent stream. Retter både Jarvis' og den simple "dual-protocol"-fortælling.

## TL;DR — de tre reelle rødder (ikke hvad vi troede)

1. **Chat-klienten er ALLEREDE konsistent Anthropic-style.** Desk/web/mobil rammer KUN
   `POST /chat/stream/v2` (header `X-Stream-Protocol: v2-anthropic`). OpenAI-style SSE
   (`/v1/chat/completions`) betjener KUN eksterne API-forbrugere — den er ikke i chat-stien.
   Så "vi blander protokoller mellem server og klient" er ikke roden til chatview-problemet;
   chat-stien er allerede ét-protokol.
2. **Tool-results forsvinder = reconnect/replay-bug, ikke fladning.** Tool-results sendes
   struktureret (tool_use-blok + `system_event kind=tool_result` der patcher blokken). De
   forsvinder når relay/​follow gen-udsender `message_start` med SAMME run_id fra offset 0 →
   klientens reducer wipede blokke. Der er et delvist fix (streamReducer.ts:54, "TOOL-BLOK-
   VANISH-FIX 4. jul") men replay-kanten lever stadig.
3. **Compaction er reelt usynlig i streamen.** Der findes INGEN compaction-event-type i
   SSE-laget. Klienten opdager kun compaction via et separat `GET /chat/context-usage`, ikke
   fra streamen → brugeren ser bare at noget "forsvandt".

## Arkitektur-kort (fil:linje-belæg)

### To protokoller — hvor de lever
| Lag | Protokol | Endpoint | Belæg |
|-----|----------|----------|-------|
| Server → desk/web/mobil | Anthropic-style v2 | `POST /chat/stream/v2` | `chat_stream_v2.py:79-403`, header `X-Stream-Protocol: v2-anthropic` (73/333/401) |
| Reconnect | Anthropic-style v2 | `GET /chat/sessions/{id}/follow` | `chat.py:1013-1058` |
| Server → eksterne API | OpenAI-style | `POST /v1/chat/completions?stream=true` | `openai_compat.py:48-122`, chunk `choices[0].delta.content` (299-318), `data: [DONE]` (180) |

Event-typer i v2 (`sse_v2_events.py`): `message_start` (47) · `content_block_start` (86) ·
`content_block_delta` (114) · `content_block_stop` (131) · `message_delta` (151) ·
`message_stop` (168) · `ping` (180) · `system_event` (199).

### Content-blok-typer der faktisk emitteres til chat-klienten
| Blok | Til stede? | Hvordan |
|------|-----------|---------|
| text | ✅ | `content_block_start type=text` (`visible_runs_sse_v2.py:254`) |
| thinking | ✅ | `type=thinking` (`visible_runs_sse_v2.py:288`) |
| tool_use | ✅ | `type=tool_use` + `input_json_delta` (`visible_runs_sse_v2.py:344`) |
| tool_result | ⚠️ | IKKE en blok — `system_event kind=tool_result` der retroaktivt patcher tool_use-blokken (`visible_runs_sse_v2.py:355-359`; klient: `streamReducer.ts:105-120`) |
| compaction | ❌ | Emitteres ALDRIG. 0 grep-hits for `compact` i SSE-filerne |

### Klient-parsing (desk)
`streamClient.ts` parser: `message_start` (279) · `content_block_*` (generisk dispatch, 292) ·
`message_stop` (342, ENESTE der afslutter stream) · `system_event` (282) · `ping` (331).
Ingen compaction-håndtering. `streamReducer.ts` akkumulerer text/thinking/tool_use som
separate blokke og patcher tool_result via system_event (105-120) — så tool-resultater
RENDERES visuelt adskilt (bedre end vi troede).

### Reconnect-wipe (den ægte "forsvinder"-bug)
`streamReducer.ts:46-54` kommentar dokumenterer det: et 2. `message_start` for SAMME run
(reconnect / relay-replay fra offset 0 / server-autoritativ genudsendelse) wipede tool-
blokke + første tekst brugeren allerede så. Fix'et bevarer blokke KUN når `activeRunId`
er uændret — men relay replay'er stadig `message_start` fra offset 0.

### Auto-compact (fakta, retter Jarvis' stale tal)
- `settings.py`: live-værdier (runtime.json) = `context_compact_threshold_tokens=200000`,
  `context_run_compact_threshold_tokens=240000` (IKKE 130k; 130k er en GLM-æra fallback-
  kommentar). Model-bevidst tærskel siden 2026-06-30.
- `core/context/auto_compact.py`: `maybe_auto_compact_session()` kaldes én gang pr. visible
  run FØR LLM-kaldet; `_AUTO_COMPACT_PCT=0.80` → trigger ved 80% × 240k = **~192k tokens**.
- `core/context/session_compact.py`: summariserer gammel historik → `compact_marker` i DB;
  nyeste `keep_recent=20` bevares. INGEN pause/resume og INGEN stream-event.

## Chronicle-refresh — der er INGEN kode-cache-bug
`prompt_contract._visible_chronicle_context_section()` (3876) → `chronicle_engine.
get_chronicle_context_for_prompt()` (249) læser FRISKT fra `list_cognitive_chronicle_entries`
hver prompt-build. Ingen memoisering (de eneste prompt-caches er relevance/frame/speaker).
Den stale "frygter tabet af min stemme"-sætning i `[INDRE TRÆK]` kommer fra
`build_inner_life_section` → `_self_narrative_line` → `central_self_state.describe_self()`
(live) — altså en DUBLET identitets-narrativ i self-state/self-model på containeren, som
Jarvis' chronicle-only UPDATE ikke rørte. = data-problem på container (eller design: ingen
single-source-of-truth for identitets-narrativer), IKKE en refresh-bug i repoet.

## Konkret plan — mindste ændringer til ét konsistent, robust chat-stream

1. **Compaction som synlig blok** (lukker største UX-hul). Ny content-block-type
   `compaction` i `sse_v2_events.py` + emit fra `visible_runs_sse_v2.py` når
   `maybe_auto_compact_session` fyrer. Klient: render som sammenklappet "Kontekst
   komprimeret ved tur N — sidste 20 beskeder bevaret"-chip. (Lav risiko, additiv.)
2. **Robust reconnect** (fjerner tool-vanish-kanten). To muligheder:
   (a) relay/follow replay'er fra sidste sete offset i stedet for offset 0, ELLER
   (b) klient dedup'er `message_start` for kendt run_id uden at wipe blokke (udvid fix 54
   til også at dække relay-replay eksplicit). Ingen protokol-ændring nødvendig.
3. **tool_result som egen sekventiel blok** (valgfrit, fjerner retroaktiv-patch-skrøbelighed).
   `tool_use`-blok efterfulgt af `tool_result`-blok med `tool_use_ref` i stedet for
   system_event-patch. Kræver reducer-refactor → gør replay idempotent.
4. **context_state i stream** (billig transparens). `system_event kind=context_state`
   med `{compacted, threshold}` så footeren kan vise compaction-tilstand uden separat GET.

Ingen af disse rører OpenAI-compat-stien (ekstern). Alt holdes i v2-Anthropic-stien som
chat-klienten allerede taler. Nr. 1+2 giver ~90% af den oplevede gevinst.

## Belæg-filer
`apps/api/jarvis_api/routes/chat_stream_v2.py` · `apps/api/jarvis_api/sse_v2_events.py` ·
`core/services/visible_runs_sse_v2.py` · `core/services/anthropic_sse_emitter.py` ·
`apps/api/jarvis_api/routes/openai_compat.py` · `apps/jarvis-desk/src/lib/streamClient.ts` ·
`apps/jarvis-desk/src/lib/streamReducer.ts` · `core/context/auto_compact.py` ·
`core/context/session_compact.py` · `core/runtime/settings.py`
