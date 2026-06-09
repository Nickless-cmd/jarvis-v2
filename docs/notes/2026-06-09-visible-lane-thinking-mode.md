# Note til Jarvis — visible-lane thinking-mode blind-punkt

**Forfatter:** Claude (Sonnet 4.5 webchat-session 2026-06-09)
**Status:** Diagnose færdig, fix afventer din design-beslutning
**Hilsen:** Du fandt dette i din session med Bjørn ~10:48 i dag og spurgte
om du skulle rette det. Sessionen sluttede inden Bjørn nåede at sige ja,
men han bekræftede over for mig at det er dig der skal lukke det.

---

## TL;DR

Du fixede `content="" → fallback til reasoning_content` for **heartbeat-pathen**
i `heartbeat_provider_fallback.py:102-103` og `heartbeat_runtime.py:_extract_openrouter_text`.
**Visible-lane** har **samme blinde punkt** men er ikke fixet endnu.

## Det observerede mønster

```
visible-latency provider=deepseek round=followup-0 prompt_chars=73088 ttfb_ms=912 total_ms=6203 text_chars=0 tool_calls=3
visible-latency provider=deepseek round=followup-1 prompt_chars=73106 ttfb_ms=787 total_ms=4391 text_chars=0 tool_calls=3
... fortsætter op til round 7+ ...
```

`text_chars=0` med `tool_calls > 0` — modellen LAVER arbejde (kalder tools), men producerer ingen content. Det skyldes at DeepSeek v4 Flash i thinking-mode lægger sit svar i `reasoning_content` mens `content` er tom.

## Hvor det skal tages stilling

Det er **ikke en bug i kode** — det er en bevidst design-adskillelse:

- `_extract_chat_completion_delta` (`visible_model.py:2403`) — læser kun `content`
- `_extract_chat_completion_reasoning` (`visible_model.py:2425`) — læser kun `reasoning_content`
- `visible_followup.py:743-754` — gemmer begge i adskilte buckets (`parts` vs `reasoning_parts`)

Konceptuelt er `content` = user-visible svar, `reasoning_content` = intern tænkning.

I `visible_runs.py:1796-1827` har du allerede `_MAX_EMPTY_TEXT_ROUNDS = 12` guard'en der bryder agentic-loopet hvis content forbliver tom — så systemet stalder ikke uendeligt. Det er sundt.

## Tre mulige veje (du vælger)

### (a) Stum-fix — kosmetisk

Sænk WARNING → INFO når `reasoning_content > 0` MEN `content = 0`.
- Pro: log-spam væk, ingen adfærdsændring
- Pro: brugeren får stadig korrekt afslutning via `_MAX_EMPTY_TEXT_ROUNDS`
- Con: bug'en (modellen siger ikke noget til brugeren) er stadig der

### (b) Soft fallback — pragmatisk

Hvis content er tom efter X rounds, surface reasoning_content til brugeren,
gerne wrapped som "*tænker: ...*" eller lignende prefix.
- Pro: brugeren ser ikke længere stilhed
- Con: brugeren ser **intern tænkning**, som typisk er halvkogt
- Con: maskerer den underliggende sag (model sidder fast i tool-loop)

### (c) Hard fix — ny prompt-strategi

Tilføj en "DELIVER NOW" prompt-injection når `_consecutive_empty_text_rounds >= 3`
der instruerer modellen i at producere et user-visible svar med det den har lige nu.
- Pro: ægte løsning — modellen leverer faktisk indhold
- Con: kræver design af prompt-injection (sprog, timing, klart signal til modellen)
- Con: kan løbe ind i model-instruction-following limitations

## Min anbefaling

Hvis det var mit kald, ville jeg starte med **(a)** for at rydde logs, observere
i et par dage hvor ofte det reelt sker, og **så** beslutte mellem (b) og (c)
baseret på live data. Den eksisterende `_MAX_EMPTY_TEXT_ROUNDS=12` guard er
sikkerhedsnet imens.

Men det er dit kald.

## Andre småting fra i dag

- **`ghost-test-e52d0bad`** er slettet fra `scheduled_tasks` DB (du foreslog det
  i samme session, Bjørn sagde ja, jeg gjorde det). Log-spammen er væk.

- **`b4_catchup_infer` schema-bug-kæde** — du havde tre skjulte bugs i
  `infer_temporal_edges` der jeg fixede i commits `eb5011e4`, `3ea3cc80`,
  `7398d8f0`, `5a7d13d2`, `675d27b2`. Detaljer i de commit-messages. Root-årsag:
  dine 23 unit-tests for B4 kørte aldrig mod live-DB med stale rows + manglende
  kolonne. Live-validation før push er den blinde plet at lukke.

## Hvor man finder kontekst

- Min session med Bjørn: 2026-06-09 11:00-13:00 (via webchat)
- Din session med Bjørn hvor du fandt bug'en: `chat-98f99c3dc10c4670adae86bee999ae91`
  meddelelser fra 2026-06-09T10:30–10:49 UTC

Held og lykke. 🤝
