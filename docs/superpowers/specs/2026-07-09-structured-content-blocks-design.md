# Strukturerede content-blokke: persist + stream + reload (fuld fidelitet)

**Dato:** 2026-07-09
**Status:** Godkendt design → writing-plans
**Ejer:** Bjørn / Claude
**Relaterer:** [[reference_ack_import_floods_eventloop]], desk v0.3.24/v0.3.25 klient-workarounds (gøres overflødige)

---

## 1. Problem

Tool-kort i chat-klienterne (desk + mobil) forsvinder, dukker op efter svaret, eller
mangler helt ved genindlæsning — i både chat- og code-mode. Roden er en **dobbelt-repræsentation**:

- **Live-stream:** `tool_use` sendes som content-blok (Anthropic-stil), men `tool_result`
  sendes som en separat `system_event`-sidekanal. Klienten skal matche de to på `tool_use_id`.
- **Persist:** `chat_messages.content` er en ren markdown-**tekst**streng. Tool-blokke gemmes
  ikke i beskeden; tool-resultater ligger i en separat `tool_results`-tabel, refereret som
  `[tool_navn]:<result_id>` inde i teksten.
- **Reload/reconcile:** når klienten genindlæser en session får den kun tekst tilbage
  (`stringToBlocks` → én tekst-blok). Den klient-side "reconcile-dans" (`mergeServer`)
  forsøger at bevare de streamede tool-blokke, men overskrives af serverens tekst-kun-kopi
  ved gentagne poll-refreshes (særligt i code-mode).

De nuværende fixes (desk v0.3.24/v0.3.25) er klient-side workarounds der re-injicerer
tool-blokke ved hver merge. De behandler symptomet, ikke roden.

**Referencearkitektur (Claude Code, leaked kilde, offentligt på GitHub):** hele
besked-arrayet — inkl. `tool_use`- og `tool_result`-content-blokke — persisteres samlet
(`recordTranscript(messages)`). Klienten renderer direkte fra det persisterede; der er intet
at hente-og-flette bagefter. Det er den model vi kopierer (vores egen rene implementering).

---

## 2. Mål

Én enhedslig content-blok-repræsentation **stream = persist = reload**, så tool-kort aldrig
forsvinder og de klient-side reconcile-workarounds kan fjernes.

**Ikke-mål (uden for scope):**
- Reasoning/thinking-persistering ændres ikke (bliver i `reasoning_content`-kolonnen).
- Hvad LLM'en modtager som kontekst ændres ikke — kontekst-byggeren læser fortsat den flade
  tekst-projektion (se §4). Struktureret model-kontekst er en mulig senere forbedring, ikke
  en del af dette projekt.
- Ingen migration af eksisterende DB-data (serve-on-read i stedet, §6).

---

## 3. Besluttede valg (fra brainstorm)

1. **Fuld fidelitet** — persistér hele turens content-array struktureret.
2. **Fuld wire-alignment** — `tool_result` streames som content-blok, ikke `system_event`.
3. **Serve-on-read** — ingen migration; adapter rekonstruerer gamle sessioner fra tekst +
   `tool_results`-tabellen.
4. **Persist-format = tilgang A** — JSON-kolonne på `chat_messages` som kanonisk kilde;
   tekstkolonnen bliver afledt projektion.
5. **Flag ON fra start** — governed kill-switch, ingen shadow-periode (kan flippes OFF for revert).

---

## 4. Data-model

### 4.1 Skema
Ny kolonne på `chat_messages` ([core/runtime/db_schema.py:475](core/runtime/db_schema.py)):

```sql
content_json TEXT NULL   -- JSON-encoded ordnet array af content-blokke; NULL = gammel besked
```

Additiv, nullable → ingen migration af eksisterende rækker. Tilføjes via den eksisterende
idempotente `ALTER TABLE ... ADD COLUMN`-mønster i schema-opsætningen (samme som andre
sent-tilføjede kolonner; verificér det præcise mønster i Task 1).

### 4.2 Blok-former (Anthropic-tro)

```jsonc
{"type": "text", "text": "..."}
{"type": "tool_use", "id": "toolu_...", "name": "bash", "input": { ... }}
{"type": "tool_result", "tool_use_id": "toolu_...", "status": "done|error",
 "content": "...", "is_error": false}
```

`content_json` = ordnet array, fx:
`[{text}, {tool_use A}, {tool_result A}, {tool_use B}, {tool_result B}, {text}]`.

**Deliberat afvigelse fra Claude Code:** hele turen ligger i **én** assistant-besked
(`content_json` inkl. tool_result-blokke), i stedet for at splitte tool_result ud i en separat
`role=user`-besked. Grunden: vores klient renderer en tur som **én** besked-enhed; et splittet
besked-par ville genindføre præcis den cross-besked-stitching vi fjerner. Vi bevarer fuld
fidelitet på content-array-*strukturen* uden den skrøbelige del. (Server-side `role="tool"`-rækker
og `tool_results`-tabellen bevares uændret for bagudkompatibilitet med de læsere der bruger dem.)

### 4.3 Kanonisk flader
Én ny funktion er den ENESTE vej fra blokke til tekst:

```python
def content_blocks_to_text(blocks: list[dict]) -> str:
    """Flad en content-blok-array til den markdown-tekst-projektion som alle
    tekst-læsere (kontekst-bygger, memory, søgning, contradiction-tracker) bruger.
    Deterministisk og stabil: samme output-form som dagens persisterede tekst."""
```

- `text`-blok → dens `text`.
- `tool_use`-blok → **præcis den form dagens persist bruger** for tool-kald i teksten (verificér
  den nøjagtige nuværende form i Task 1; projektionen skal reproducere den 1:1 — hvad end den er).
- `tool_result`-blok → den eksisterende `[tool_navn]:<ref>`-reference-form (bevarer
  `tool_results`-tabel-koblingen).

Projektionen skal være **bit-stabil** mod hvad `_persist_session_assistant_message` skriver i
dag for en ren-tekst-tur (ingen tool-kald), så eksisterende tekst-læsere ser ingen ændring.

---

## 5. Skrive-sti (persist)

Ved run-slut ([core/services/visible_runs_outcomes.py:78](core/services/visible_runs_outcomes.py),
`_persist_session_assistant_message`):

1. Byg det ordnede blok-array fra det runden allerede kender: tekst-segmenter (den streamede
   assistant-tekst), `tool_use`-blokke (navn + input, fra runde-state), og `tool_result`-blokke
   (status + indhold, fra `tool_results`-tabellen / runde-state).
   **Rækkefølge-kilde (verificér i Task 1):** den ordnede fletning (tekst → tool → tekst) skal
   udledes af runde-eventenes rækkefølge (samme sekvens som streamen sendte). Er den præcise
   interleaving IKKE tilgængelig ved run-slut (kun slut-tekst + tool-liste), degraderer vi
   deterministisk til: alle tekst-segmenter, derefter tool_use/tool_result-par i kald-rækkefølge.
   Klienten renderer korrekt uanset, men den ægte interleaving er at foretrække — Task 1 afgør
   hvad runde-state faktisk bærer.
2. Beregn `content = content_blocks_to_text(blocks)` (den flade projektion).
3. Persistér **atomisk i samme INSERT** ([core/services/chat_sessions.py:422](core/services/chat_sessions.py)):
   `content` (projektion, som i dag) **+** `content_json` (JSON-serialiseret array).

`append_chat_message()` udvides med en valgfri `content_json`-parameter (default `None` →
skriver NULL, uændret adfærd for alle andre kaldere). Sanitizing/leak-guard/markdown-normalisering
køres på tekst-segmenterne som i dag, før projektionen beregnes.

**Flag-gate:** når `structured_content_v2` er OFF skrives `content_json = NULL` (ren nuværende
adfærd). Når ON skrives både projektion + `content_json`.

---

## 6. Serve-on-read adapter (GET)

GET `/chat/sessions/{id}`-serialiseringen
([core/services/chat_sessions.py:283](core/services/chat_sessions.py)) returnerer pr. besked:

- `content` (streng — bevaret, bagudkompatibel for enhver ældre læser).
- `content_json` (array) — via adapter-reglen:

```
hvis række.content_json er sat  → parse og returnér den (kanonisk).
ellers (gammel besked)          → rekonstruér blokke:
    - split content-teksten i text-segmenter + [tool]:<ref>-markører
    - for hver markør: slå resultatet op i tool_results-tabellen
    - byg [text, tool_use?, tool_result, ...] efter bedste evne
    - hvis ingen markører: [{type:"text", text: content}]  (uændret gammel opførsel)
```

Rekonstruktionen er **read-only** (rører aldrig DB'en) og fejl-tolerant: kan en `<ref>` ikke
slås op, degraderes den blok til tekst i stedet for at fejle hele beskeden.

`GET`-endpointet ([apps/api/jarvis_api/routes/chat.py:1178](apps/api/jarvis_api/routes/chat.py))
er uændret — al logik ligger i serialiserings-laget.

---

## 7. Streaming-protokol

`tool_result` flyttes fra `system_event`-sidekanalen
([core/services/visible_runs_sse_v2.py:354](core/services/visible_runs_sse_v2.py)) til et
content-blok-event i Anthropic-stil, adresseret via `tool_use_id`:

- **Ny wire-form:** et `content_block`-agtigt event der bærer
  `{type:"tool_result", tool_use_id, status, content, is_error}` (præcis emitter-form defineres i
  plan; genbrug `anthropic_sse_emitter`-mønsteret fra
  [core/services/anthropic_sse_emitter.py:38](core/services/anthropic_sse_emitter.py)).
- `tool_use` streames allerede som `content_block_start` + `input_json_delta`
  ([core/services/anthropic_translator.py:183](core/services/anthropic_translator.py)) — uændret.
- `message_start` / `message_stop` / tekst-blokke — uændret.

**Flag-gate:** når `structured_content_v2` er OFF sendes `tool_result` som den nuværende
`system_event` (uændret). Når ON sendes det som content-blok. (Klienten læser begge — §8 — så
skiftet er sikkert.)

---

## 8. Klient-reducere (desk + mobil)

**Krav: dual-read i en overgang** — klienten forstår BÅDE gammelt og nyt format, så udrulning
ikke kan brække en levende session.

### 8.1 Load
`getSession` ([apps/jarvis-desk/src/lib/api.ts:184](apps/jarvis-desk/src/lib/api.ts)):
- Er `content_json` til stede på beskeden → brug den direkte som `ContentBlock[]`.
- Ellers → `stringToBlocks(content)` som i dag
  ([apps/jarvis-desk/src/lib/normalizeMessage.ts:6](apps/jarvis-desk/src/lib/normalizeMessage.ts)).

### 8.2 Stream
Reduceren ([apps/jarvis-desk/src/lib/streamReducer.ts:105](apps/jarvis-desk/src/lib/streamReducer.ts)):
- Håndtér `tool_result` via den **nye content-blok-kanal** (associér til `tool_use` via
  `tool_use_id`).
- **Behold også** den eksisterende `system_event`-sti (dual-read) indtil server-flaget er
  verificeret ON i produktion — så fjernes den i en oprydnings-fase.

### 8.3 Reconcile
`mergeServer` ([apps/jarvis-desk/src/contexts/SessionContext.tsx](apps/jarvis-desk/src/contexts/SessionContext.tsx)):
- Når serveren leverer `content_json`, behøver `mergeServer` **ikke** længere re-injicere
  tool-blokke fra lokal state — serverens kopi er allerede komplet.
- v0.3.25's `localToolsByNorm`-re-injektion beholdes som fallback for beskeder uden `content_json`
  (gamle sessioner via rekonstruktion har dem allerede), og fjernes i oprydnings-fasen når ON er
  bekræftet.
- De eksisterende `mergeServer`-tests (SessionContext.test.tsx) skal fortsat passere.

### 8.4 Mobil
Mobil-klienten (samme `/chat/sessions/{id}` REST-endpoint) får samme dual-read-behandling i sin
reducer/load-sti. Præcise filstier bekræftes i plan (Task 1).

---

## 9. Reversibilitet + udrulning

Runtime-flag **`structured_content_v2`** (via `central_switches`/runtime-state). **Default ON**
(Bjørns valg — ingen shadow-periode), men som governed kill-switch: flip OFF → nye beskeder
persisteres som ren tekst igen og `tool_result` streames som `system_event` igen. Allerede-skrevne
`content_json`-rækker forbliver læsbare (adapteren returnerer dem uanset flag).

**Udrulningsrækkefølge (må ikke brække live):**
1. **Klient først:** ship desk + mobil der læser BEGGE formater (content_json + tekst;
   content-blok + system_event tool_result). Bagudkompatibelt — ingen adfærdsændring endnu.
2. **Server bagefter:** deploy backend med flaget ON. Nye beskeder persisteres struktureret +
   `tool_result` streames som content-blok. De opdaterede klienter håndterer begge.
3. **Verificér live:** ny tur m. tool-kald → tool-kort overlever reload + code-mode-refresh; gammel
   session → tool-kort rekonstrueret. Ved problem → flip flag OFF.

**Caveat (dokumenteret risiko):** i vinduet mellem trin 2-deploy og en klient-genstart kan en
*gammel* desk-build (før trin 1) møde den nye wire-form og miste tool-kort indtil den opdateres.
Afbødning: klient-deploy før server-flip (trin 1 før 2), og desk kræver alligevel manuel
close+reopen efter build.

**Oprydnings-fase (efter ON er verificeret stabil):** fjern klient-side `system_event`-tool_result-
stien og v0.3.25's `localToolsByNorm`-workaround. Egen opgave, ikke en del af kerne-leverancen.

---

## 10. Test

- **`content_blocks_to_text`** (unit): round-trip + projektion-stabilitet; ren-tekst-tur giver
  bit-identisk output med dagens persist-form.
- **Skrive-sti** (integration): run m. tool-kald → `content_json` = korrekt ordnet array; `content`
  = korrekt projektion; flag OFF → `content_json` NULL + uændret tekst.
- **Serve-on-read** (unit mod `tool_results`): gammel tekst-besked m. `[tool]:<ref>` → rekonstrueret
  blok-array m. tool-kort; ukendt ref → degraderer til tekst uden at fejle.
- **Reducer desk+mobil** (unit): `tool_result` via content-blok-kanal folder korrekt på `tool_use_id`;
  dual-read af `system_event` bevaret; `mergeServer` taber ikke kort ved gentagne merges (behold
  eksisterende SessionContext-tests grønne).
- **Egress/invariant:** uændret — ingen nye udgående kald; PRIVATE_NO_EGRESS-invariant urørt.

---

## 11. Blast-radius & afbødning

| Risiko | Afbødning |
|--------|-----------|
| Server-læsere (kontekst-bygger/memory/søgning) forventer tekst | De læser fortsat `content`-tekst-projektionen — **urørt**. |
| Gamle sessioner mister tool-kort | Serve-on-read rekonstruerer fra `tool_results`-tabellen. |
| Wire-skift brækker gamle klienter | Klient-først-udrulning + klient dual-read. |
| Struktureret persist buggy | Kill-switch flip OFF → ren nuværende adfærd; skrevne rækker forbliver læsbare. |
| Projektion afviger fra dagens tekst | Bit-stabilitets-test på ren-tekst-tur. |
| Stor fil berørt (visible_runs/db) | Boy Scout: udskil nærmeste naturlige enhed før ændring hvis fil >2000 linjer. |

---

## 12. Filer (forventet berørt)

**Server:**
- `core/runtime/db_schema.py` — `content_json`-kolonne.
- `core/services/chat_sessions.py` — `append_chat_message` (skriv), GET-serialisering (adapter),
  ny `content_blocks_to_text` + rekonstruktion (evt. i egen ny modul-fil for isolation).
- `core/services/visible_runs_outcomes.py` — byg blok-array ved run-slut.
- `core/services/visible_runs_sse_v2.py` — `tool_result` som content-blok (flag-gated).
- `core/services/anthropic_sse_emitter.py` — evt. ny emitter-hjælper for tool_result-blok.
- Flag-læsning via eksisterende `central_switches`/runtime-state.

**Klient:**
- `apps/jarvis-desk/src/lib/api.ts` — `getSession` foretrækker `content_json`.
- `apps/jarvis-desk/src/lib/streamReducer.ts` — tool_result content-blok-kanal + dual-read.
- `apps/jarvis-desk/src/contexts/SessionContext.tsx` — `mergeServer` afhænger af serverens blokke.
- Mobil-modstykker (stier bekræftes i plan).

**Ny fil (foretrukket for isolation):**
- `core/services/content_blocks.py` — `content_blocks_to_text` + rekonstruktions-adapter + blok-typer,
  så logikken er ét-ansvar og enhedstestbar uden at oppuste chat_sessions.py.

---

## 13. Åbne detaljer til plan-fasen (ikke blokerende)

- Nøjagtig nuværende tekst-form for tool_use/tool_result i persist (så projektionen er identisk) —
  verificér i Task 1.
- Præcist `ALTER TABLE`-idempotens-mønster i schema-opsætningen.
- Præcise mobil-fil-stier for reducer/load.
- Nøjagtig SSE-event-navn/-form for tool_result-content-blokken (genbrug emitter-mønster).
