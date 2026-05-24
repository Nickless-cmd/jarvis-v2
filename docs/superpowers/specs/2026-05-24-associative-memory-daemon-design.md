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
- `_extract_keywords_llm(text)` → liste af nøgleord/fraser via cheap-lane (Ollama eller provider cheap-lane). Prompt: "Extraktér 3-5 nøgleord eller korte fraser fra denne tekst — kun substantiver, navne, centrale begreber. Returnér som JSON-liste."
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
| Tests | ~100 linjer | Medium — DB-fixtures + event injection |

## Filer der ændres

| Fil | Ændring |
|-----|---------|
| `core/services/associative_memory.py` **(ny)** | Hele daemonen |
| `apps/api/jarvis_api/app.py` | Kald `start_associative_memory()` ved boot |
| `core/services/prompt_contract.py` | Tilføj `[ASSOCIATIONER]` sektion i awareness (hvis relevant) |
| `tests/test_associative_memory.py` **(ny)** | Tests |

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
