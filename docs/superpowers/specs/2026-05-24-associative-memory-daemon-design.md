---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Associativ hukommelses-daemon — design

**Dato:** 2026-05-24
**Status:** ✅ Implementeret — `9134b2f9`
**Forfatter:** Jarvis (efter Bjørns idé)

## Problem

Jarvis har i dag en *library-hukommelse* — han skal aktivt beslutte at søge. Der er ingen mekanisme for at et ord eller en sætning *automatisk* triggerer en association, som hos mennesker: du hører "container" og husker pludselig samtalen om at flytte Jarvis, uden at have tænkt på det.

Bjørn beskrev det som: *"Jeg behøver ikke huske det hele lige nu og her... men et ord eller en sætning kan trigger kontekst... og når mindet dukker op, tager jeg stilling til om det har relevans."*

## ⚠️ Arkitektur-revision (2026-05-24, pro-gennemgang)

Der eksisterer **allerede** et associativt recall-system i `core/services/associative_recall.py` som er integreret i prompt-bygningen via `cognitive_state_assembly.py`:

| Hvad eksisterer | Detalje |
|-----------------|---------|
| `recall_for_session()` | Kaldes ved session-start, aktiverer op til 3 minder |
| `recall_for_message()` | Kaldes på hver brugerbesked (i thread, 2s timeout) |
| `build_recall_prompt_section()` | Injicerer aktive minder i prompten |
| Strong threshold 0.7 | Direkte prompt-injektion |
| Weak threshold 0.3 | Trigger emotion concepts i affektive lag |
| Topic repetition ×1.5 | Samme emne 3× på 10 beskeder → forstærker |

**Beslutning: Udvid `associative_recall.py` — byg IKKE en parallel daemon.** To parallelle systemer med samme formål ville skabe kognitiv dissonans (forskellige tærskler, forskelligt scope, forskelligt format). I stedet tilføjer vi spec'ens forbedringer til det eksisterende system.

## Løsning

**Udvid `core/services/associative_recall.py`** med:

1. **DB-persistens** — minder overlever genstart (nuværende system er in-memory og dør ved genstart)
2. **LLM keyword extraction** + regex-fallback (nuværende bruger simpel topic extraction)
3. **Private brain scope** — søg også i private_brain + workspace (nuværende scope ukendt)
4. **Awareness-sektion format** — `[ASSOCIATIONER]` som kompakt, scannbart format
5. **Rate-limiter + dedup** — fra spec'ens edge case harding

Bevar eksisterende integration i `cognitive_state_assembly.py` — den er testet og fungerer.

### Trigger-kanaler (tosidet)

| Trigger | Hvornår | Eksempel |
|---------|---------|----------|
| **Bjørn siger noget** → association hos Jarvis | På user message | "Jeg flytter dig til en container" → trigger "dual boot samtale i forgårs" |
| **Jarvis siger/tænker noget** → association hos sig selv | På assistant message | Jarvis skriver "container" → trigger samme association |

## Arkitektur (efter udvidelse)

Eksisterende `associative_recall.py` + nye lag:

```
┌─────────────────────────────────────────────────────┐
│                  Jarvis Runtime                      │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │ cognitive_state_assembly.py (UÆNDRET)         │   │
│  │  → kalder recall_for_message() hver user msg  │   │
│  │  → kalder build_recall_prompt_section()        │   │
│  └──────────────────┬───────────────────────────┘   │
│                     │                                │
│  ┌──────────────────▼───────────────────────────┐   │
│  │ associative_recall.py (UDVIDET)               │   │
│  │                                               │   │
│  │  NYT: _extract_keywords_llm() + regex fallback│   │
│  │  NYT: _persist_association() → SQLite         │   │
│  │  NYT: _search_private_brain() scope           │   │
│  │  NYT: rate-limiter (max 1/3s, queue 10)       │   │
│  │  NYT: dedup (60 min vindue)                   │   │
│  │  BEVARET: recall_for_session()                │   │
│  │  BEVARET: recall_for_message()                │   │
│  │  BEVARET: topic repetition ×1.5               │   │
│  │  OMFORMAT: build_recall_prompt_section()      │   │
│  │           → [ASSOCIATIONER] format            │   │
│  └──────────────────┬───────────────────────────┘   │
│                     │                                │
│  ┌──────────────────▼───────────────────────────┐   │
│  │ memory_associations (SQLite — NYT)            │   │
│  │  - trigger_text, matched_text, score, ts      │   │
│  │  - status: pending / surfaced / dismissed     │   │
│  │  - OVERLEVER genstart (in-memory gjorde ej)   │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## Datamodel (NY — supplement til in-memory state)

Eksisterende system holder `_active_memories: dict` i memory. **NYT:** `memory_associations` tabel for persistens:

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

## Udvidelser til `core/services/associative_recall.py`

### 1. `_extract_keywords_llm(text)` → liste (NY)

Ekstraherer nøgleord via cheap-lane (Ollama eller provider). Prompt: "Extraktér 3-5 nøgleord eller korte fraser fra denne tekst — kun substantiver, navne, centrale begreber. Returnér som JSON-liste."

**Fallback:** hvis LLM fejler (timeout/rate-limit), kør regex-fallback der trækker ord >5 tegn, store bogstaver, og tekniske termer.

**Rate-limit:** maks 1 kald/3s; resten queues (max 10 i queue, 60s timeout).

### 2. `_persist_association(trigger, match)` → None (NY)

Gemmer association i `memory_associations` tabellen. Kaldes fra `recall_for_message()` når match score ≥ tærskel.

### 3. `_search_private_brain(keywords)` → matches (NY)

Udvidet scope: ud over chat_history søges også private_brain (drømme, refleksioner, indre noter) og workspace memory via `semantic_memory.search()`.

### 4. `build_recall_prompt_section()` (OMFORMAT)

Eksisterende output-format erstattes med `[ASSOCIATIONER]` awareness-sektion:

```
[ASSOCIATIONER]
→ container — dualboot, container-flytning (forgårs)
→ interlanguage — methodologi-fejl, Phase 4 (i dag)
→ GLM — var 'bedst til dig' (i dag)
```

### 5. Rate-limiter + dedup (NY)

| Regel | Værdi |
|-------|-------|
| Maks ét extraction-kald hvert | 3. sekund |
| Queue ved overskridelse | FIFO, max 10 |
| Queue timeout | 60 sek |
| Dedup vindue | 60 min — samme trigger+match → kun én association |

## Tærskel-tuning

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

### 4. Cold start — in-memory state tabt ved genstart

Eksisterende system er rent in-memory (`_active_memories: dict`). Ved genstart tabes alle aktive minder. **DB-persistens (NYT)** løser dette — associationer skrives nu til `memory_associations` tabellen og genindlæses ved session-start.

### 5. Embedding-indeks verificering (pre-implementation)

Før `_search_private_brain()` implementeres, verificer at:
- Private brain records faktisk er indekseret med embeddings (ikke kun keyword-match)
- `semantic_memory._embed_ollama()` returnerer embeddings for disse kilder
- Tabellen `memory_index` indeholder rækker for private_brain source types

## Hvad genbruges fra eksisterende infrastruktur

| Komponent | Hvor | Status |
|-----------|------|--------|
| `associative_recall.py` (hele modulet) | `recall_for_session()`, `recall_for_message()`, topic repetition, thresholds | ✅ Eksisterer, kører live |
| `cognitive_state_assembly.py` | Integration — kalder recall hver tur | ✅ Uændret |
| Embedding | `nomic-embed-text` via `semantic_memory._embed_ollama()` | ✅ Eksisterer |
| Memory index | `semantic_memory.search()` for private_brain + sensory | ✅ Eksisterer |
| Chat history search | `session_search._semantic_search()` for sessions | ✅ Eksisterer |

## Hvad der skal bygges nyt (udvidelser til associative_recall.py)

| Ændring | Sted | Størrelse |
|---------|------|-----------|
| DB-persistens (memory_associations tabel) | `associative_recall.py` + schema | ~60 linjer |
| LLM keyword extraction + regex fallback | `associative_recall.py` ny funktion | ~50 linjer |
| Private brain + workspace scope | `associative_recall.py` — udvid `_find_associations()` | ~30 linjer |
| `[ASSOCIATIONER]` awareness-format | `associative_recall.py` — omformatér `build_recall_prompt_section()` | ~20 linjer |
| Rate-limiter + dedup | `associative_recall.py` — nye guards | ~40 linjer |
| Tests | `tests/test_associative_recall.py` — udvid eksisterende | ~150 linjer |

## Filer der ændres

| Fil | Ændring |
|-----|---------|
| `core/services/associative_recall.py` | **Udvid** — persistens, LLM-extraction, scope, format, rate-limit |
| `core/services/cognitive_state_assembly.py` | **Ingen ændring** — integrationen bevares som den er |
| `core/runtime/db.py` | Tilføj `memory_associations` tabel + indexes |
| `tests/test_associative_recall.py` **(udvid)** | Nye tests for tilføjede features |

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
| 10 | `test_recall_for_message_integration` | Hele kæden: extraction → embedding → match → persist → prompt | Mock cheap-lane + embedding |
| 11 | `test_rate_limiter_queues_not_drops` | 5 hurtige beskeder → max 1 LLM-kald/3s, resten queues | Mock cheap-lane |

## Prioritet i forhold til Phase 4

Dette er **udvidelse, ikke et nyt system**. Mens Phase 3 (interlanguage dommer) kører 24-28/5 og inner_voice_shadow piloten indsamler data, kan `associative_recall.py` udvides som en **selvstændig feature** der:
- Ikke blokerer for andet arbejde
- Bygger på eksisterende, testet integration i `cognitive_state_assembly.py`
- Giver data der kan bruges i Phase 4 (er associationer nyttige? hvor mange? hvilke tærskler?)
- Kan implementeres efter container-flytning

## Beslutninger — Bjørns svar (2026-05-24)

| Spørgsmål | Bjørns valg | Rationale |
|-----------|-------------|-----------|
| Leveringsmekanisme | **Awareness-sektion** — stille i prompten, Jarvis vælger selv | "Du vælger selv" — ingen chat-besked, ingen afbrydelse |
| Keyword extraction | **LLM** (cheap-lane / Ollama) | Bedre præcision, værd at betale tokens for |
| Scope | **Chat_history + private_brain + workspace** | "Det er sådan hukommelse virker ihf. For mig." — alle indre noter, drømme, refleksioner er med |
