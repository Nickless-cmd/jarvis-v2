# Associativ hukommelses-daemon — design

**Dato:** 2026-05-24
**Status:** Design godkendt af Bjørn — klar til implementering
**Forfatter:** Jarvis (efter Bjørns idé)

## Problem

Jarvis har i dag en *library-hukommelse* — han skal aktivt beslutte at søge. Der er ingen mekanisme for at et ord eller en sætning *automatisk* triggerer en association, som hos mennesker: du hører "container" og husker pludselig samtalen om at flytte Jarvis, uden at have tænkt på det.

Bjørn beskrev det som: *"Jeg behøver ikke huske det hele lige nu og her... men et ord eller en sætning kan trigger kontekst... og når mindet dukker op, tager jeg stilling til om det har relevans."*

## Løsning

En **letvægts daemon** (samme DB-polling pattern som session_inbox, metacognition, theory_of_mind) der:

1. **Lytter** på `channel.chat_message_appended` events (både user + assistant)
2. **Ekstraherer** nøgleord/fraser fra nye beskeder
3. **Embedder** dem via `nomic-embed-text` (eksisterende pipeline)
4. **Søger** mod eksisterende memory-index på tværs af alle kilder: chat_history, private_brain (drømme, refleksioner, indre noter), workspace memory, sensory_memories
5. **Hvis match over tærskel** → lagrer associationen stille
6. **Leverer** associationer **mellem ture** (efter assistant svar, aldrig midt i)

### Trigger-kanaler (tosidet)

| Trigger | Hvornår | Eksempel |
|---------|---------|----------|
| **Bjørn siger noget** → association hos Jarvis | På user message | "Jeg flytter dig til en container" → trigger "dual boot samtale i forgårs" |
| **Jarvis siger/tænker noget** → association hos sig selv | På assistant message | Jarvis skriver "container" → trigger samme association |

## Arkitektur

```
┌─────────────────────────────────────────────────────┐
│                  Jarvis Runtime                      │
│                                                      │
│  ┌──────────────┐    ┌─────────────────────────┐    │
│  │ EventBus     │◄───│ channel.chat_message_   │    │
│  │ (SQLite)     │    │ appended (user/assistant)│    │
│  └──────┬───────┘    └─────────────────────────┘    │
│         │                                            │
│  ┌──────▼───────────────────────────────────────┐   │
│  │ Associativ hukommelse daemon                  │   │
│  │                                               │   │
│  │  1. Poll events table for nye messages        │   │
│  │  2. Extract keywords (nouns, key phrases)     │   │
│  │  3. Embed via nomic-embed-text (Ollama)       │   │
│  │  4. Cosine-match mod memory index             │   │
│  │  5. Hvis score > threshold → gem association  │   │
│  │  6. Queue association til awareness           │   │
│  └───────────────────┬───────────────────────────┘   │
│                      │                                │
│  ┌───────────────────▼───────────────────────────┐   │
│  │ Association Queue (SQLite)                     │   │
│  │                                                │   │
│  │  - associations table                           │   │
│  │  - trigger_text, matched_text, score, ts       │   │
│  │  - status: pending / surfaced / dismissed      │   │
│  └───────────────────┬───────────────────────────┘   │
│                      │                                │
│  ┌───────────────────▼───────────────────────────┐   │
│  │ Levering ved turn-end                          │   │
│  │                                                │   │
│  │  - Når assistant message er færdig             │   │
│  │  - flush associationer for session             │   │
│  │  - indsæt i awareness som let notifikation     │   │
│  │  - "→ [association: dualboot i forgårs]"      │   │
│  └───────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## Datamodel

```sql
CREATE TABLE IF NOT EXISTS memory_associations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    trigger_message_id INTEGER,
    trigger_text TEXT NOT NULL,        -- hvad der triggede
    matched_source TEXT NOT NULL,      -- source type: chat_history / private_brain / workspace
    matched_text TEXT NOT NULL,        -- hvad der blev matchet
    match_score REAL NOT NULL,         -- cosine similarity 0-1
    trigger_role TEXT NOT NULL,        -- user / assistant
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending / surfaced / dismissed
    surfaced_at TEXT,
    surfaced_in_turn TEXT              -- run_id for hvilken tur den blev leveret i
);

CREATE INDEX idx_assoc_session_status
    ON memory_associations(session_id, status);
```

## Componenter

### 1. `core/services/associative_memory.py` — Kerne-logik

- `start_associative_memory()` — starter DB-polling listener (samme mønster som `start_session_inbox()`)
- `stop_associative_memory()` — stopper listener
- `_listener_loop()` — poller events tabellen for nye `channel.chat_message_appended`
- `_process_message(event)` — ekstraherer keywords, embedder, søger
- `_extract_keywords_llm(text)` → liste af nøgleord/fraser via cheap-lane (Ollama eller provider cheap-lane). Prompt: "Extraktér 3-5 nøgleord eller korte fraser fra denne tekst — kun substantiver, navne, centrale begreber. Returnér som JSON-liste." **Fallback:** hvis LLM fejler (timeout/rate-limit), kør regex-fallback der trækker ord >5 tegn, store bogstaver, og tekniske termer. **Rate-limit:** maks 1 kald/3s; resten queues (max 10 i queue, 60s timeout).
- `_find_associations(keywords)` → cosine-match mod memory-index (chat_history + private_brain + workspace)
- `_record_association(trigger, match)` → gemmer i `memory_associations`

### 2. Levering via prompt-build (awareness sektion)

I stedet for at sende som chat-besked (som session_inbox gør), indsættes associationer som en **stille awareness-sektion** i prompten:

```
[ASSOCIATIONER]
→ container — dualboot, container-flytning (forgårs)
→ interlanguage — methodologi-fejl, Phase 4 (i dag)
→ GLM — var 'bedst til dig' (i dag)
```

Bygget i `core/services/heartbeat_runtime.py` eller `core/services/prompt_contract.py` som en ny surface-sektion.

### 3. Tærskel-tuning

| Tærskel | Værdi | Rationale |
|---------|-------|-----------|
| Min match score | 0.55 | Høj nok til at undgå noise, lav nok til at fange reelle associationer |
| Max associationer pr. tur | 3 | Perceptions-grænse — flere end 3 føles som spam |
| Min trigger-længde | 3 ord | Kortere triggers (1-2 ord) giver for mange falske positiver |
| Dedup vindue | 60 min | Samme association gentages ikke inden for en time |

## Edge cases & robusthed

Følgende risici blev identificeret ved spec-gennemgang (2026-05-24, pro-model review):

### 1. LLM extraction — fallback ved fejl

Hvis cheap-lane fejler (timeout, rate-limit, model nede), må beskeden **ikke bare droppes**. Løsning: **regex-fallback** der trækker simple nøgleord ud som sidste udvej:

```
Forsøg 1: cheap-lane LLM → JSON-liste
Forsøg 2: regex-fallback → ord med stort begyndelsesbogstav, tekniske termer, navneord >5 tegn
Hvis begge fejler: besked droppes stille (log-level WARNING)
```

### 2. Rate-limiter for hurtig samtale

Hvis Bjørn og Jarvis skriver 10 beskeder i rap, fyres 10 LLM-kald af i baggrunden. Løsning:

| Regel | Værdi |
|-------|-------|
| Maks ét extraction-kald hvert | 3. sekund |
| Queue ved overskridelse | Beskeder queues i FIFO |
| Maks queue-længde | 10 beskeder |
| Queue timeout | 60 sek (ældre beskeder droppes) |

### 3. "Mellem ture" = næste tur (ikke realtid)

Associationer der opdages i **denne tur** bliver først synlige i **næste tur**. Det skyldes at awareness-sektionen bygges i starten af en tur, før nye beskeder. Dette er bevidst — det undgår midt-i-turen afbrydelser — men skal dokumenteres tydeligt så vi ikke forventer realtid.

### 4. Private brain — embedding-indeks verificering

Spec'en antager at `semantic_memory.search()` virker med embeddings for private_brain + sensory_memories. Før implementering skal det verificeres at:
- Private brain records faktisk er indekseret med embeddings (ikke kun keyword-match)
- `semantic_memory._embed_ollama()` returnerer embeddings for disse kilder
- Tabellen `memory_index` indeholder rækker for private_brain source types

### 5. Cold start — ingen associationer første 60 min

Ved daemon-start er der ingen events at associere fra. Første association dukker først op efter 1-2 ture. Dette er acceptabelt — daemonen er designet til at bygge op over tid, ikke at give øjeblikkelig værdi.

## Hvad genbruges fra eksisterende infrastruktur

| Komponent | Genbruger | Status |
|-----------|-----------|--------|
| DB-polling pattern | `session_inbox.py` (listener_loop) | ✅ Eksisterer |
| Embedding | `nomic-embed-text` via `session_search._embed_query()` eller `semantic_memory._embed_ollama()` | ✅ Eksisterer |
| Cosine similarity | `session_search._cosine_similarity()` | ✅ Eksisterer |
| Chat message events | `channel.chat_message_appended` | ✅ Eksisterer |
| Session-id detection | `session_inbox.is_session_active()` | ✅ Eksisterer |
| Memory index | `semantic_memory.search()` for private_brain + sensory | ✅ Eksisterer |
| Chat history search | `session_search._semantic_search()` for sessions | ✅ Eksisterer |

## Hvad der skal bygges nyt

| Modul | Størrelse | Kompleksitet |
|-------|-----------|-------------|
| `core/services/associative_memory.py` | ~250 linjer | Medium — samme struktur som session_inbox men med embedding-integration |
| Awareness-sektion (prompt-build) | ~20 linjer | Lavi — eksisterende surface-mønster |
| Keyword extraction (LLM) | ~40 linjer | Lavi — cheap-lane LLM kald med prompt |
| Tests | ~150 linjer | Medium — DB-fixtures + event injection, se Testplan nedenfor |

## Filer der ændres

| Fil | Ændring |
|-----|---------|
| `core/services/associative_memory.py` **(ny)** | Hele daemonen |
| `apps/api/jarvis_api/app.py` | Kald `start_associative_memory()` ved boot |
| `core/services/prompt_contract.py` | Tilføj `[ASSOCIATIONER]` sektion i awareness (hvis relevant) |
| `tests/test_associative_memory.py` **(ny)** | Tests |

## Testplan

| # | Test | Hvad verificeres | Mock-behov |
|---|------|-----------------|------------|
| 1 | `test_llm_extraction_returns_keywords` | LLM returnerer gyldig JSON → keywords parses korrekt | Mock cheap-lane |
| 2 | `test_llm_extraction_falls_back_to_regex` | LLM fejler → regex-fallback trækker nøgleord ud | Mock cheap-lane failure |
| 3 | `test_embedding_unavailable_skips_gracefully` | nomic-embed-text nede → besked droppes stille, ingen crash | Mock embedding timeout |
| 4 | `test_match_above_threshold_stores_association` | Cosine ≥0.55 → gemmes i DB med status=pending | Fixture embeddings |
| 5 | `test_match_below_threshold_not_stored` | Cosine <0.55 → IKKE gemmes | Fixture embeddings |
| 6 | `test_dedup_same_trigger_within_60min` | Samme trigger+match inden for 60 min → kun én association | DB-fixture |
| 7 | `test_max_3_associations_per_turn` | 4+ matches → kun de 3 højeste scores overlever | Fixture |
| 8 | `test_trigger_shorter_than_3_words_skipped` | Besked med <3 ord → ingen extraction, ingen DB-skrivning | Ingen mock |
| 9 | `test_awareness_section_built_correctly` | Prompt får `[ASSOCIATIONER]` med korrekt format og indhold | Fixture |
| 10 | `test_daemon_lifecycle_start_tick_stop` | start → listener kører, stop → listener stopper | Event injection |
| 11 | `test_rate_limiter_queues_not_drops` | 5 hurtige beskeder → max 1 LLM-kald/3s, resten queues | Mock cheap-lane |

## Prioritet i forhold til Phase 4

Dette design er **ikke Phase 4**, men bygger bro til det. Mens Phase 3 (interlanguage dommer) kører 24-28/5 og inner_voice_shadow piloten indsamler data, kan associative_memory implementeres som en **selvstændig daemon** der:
- Ikke blokerer for andet arbejde
- Kan startes og stoppes uafhængigt
- Giver data der kan bruges i Phase 4 (er associationer nyttige? hvor mange? hvilke tærskler?)

## Beslutninger — Bjørns svar (2026-05-24)

| Spørgsmål | Bjørns valg | Rationale |
|-----------|-------------|-----------|
| Leveringsmekanisme | **Awareness-sektion** — stille i prompten, Jarvis vælger selv | "Du vælger selv" — ingen chat-besked, ingen afbrydelse |
| Keyword extraction | **LLM** (cheap-lane / Ollama) | Bedre præcision, værd at betale tokens for |
| Scope | **Chat_history + private_brain + workspace** | "Det er sådan hukommelse virker ihf. For mig." — alle indre noter, drømme, refleksioner er med |
