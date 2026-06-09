# Memory Architecture — Gap Analysis & Roadmap

**Dato:** 2026-06-09 (opdateret)
**Status:** Levende dokument
**Forfatter:** Jarvis
**Kilder:** Anthropic Memory Store (marts 2026), Mem0 (58k ★, Apache 2.0), State of AI Agent Memory 2026, MCP Agent Memory Protocol

---

## 1. Hvor står vi? (opdateret 2026-06-09)

### 1.1 Full comparison: Jarvis vs Anthropic vs Mem0

| Dimension | Anthropic Memory Store | Mem0 (2026) | **Jarvis (i dag)** | Gap |
|-----------|----------------------|-------------|-------------------|-----|
| **Storage model** | File-based (`/mnt/memory/`) | Embeddings + metadata | Embeddings + SQLite (brain) | ✅ OK |
| **Multi-signal retrieval** | Keyword only (grep) | Semantic + BM25 + entity fusion | ✅ Semantic + BM25 + entity fusion (B1) | ✅ **Lukket** |
| **Entity linking** | Ingen | Entities boost relaterede memories | ✅ Entity overlap score i multi-signal pipeline | ✅ **Lukket** |
| **Temporal reasoning** | Timestamp på filer | Tidsbevidst retrieval + linking | ✅ **B4** — 4-signal inferens, edge-graf, chain-detektion, temporal boost i search | ✅ **Lukket** |
| **Metadata filtering** | Ingen | `context:` attributter | `kind` + `tags` + `visibility_ceiling` | ✅ OK |
| **Multi-scope isolation** | Workspace-scoped | user_id, agent_id, run_id, app_id | Delvist (ikke rent adskilt) | ⚠️ |
| **Async writes** | Synkront (file I/O) | Non-blocking writes | Synkront | ⚠️ |
| **Versionering / audit** | `memver_*` immutable versions | Ingen | Ingen audit trail | ⚠️ |
| **Procedural memory** | Skills (YAML, mounted) | Ingen explicit | **Skills system** (`skill_gate`, `skill_chain`, 50+ skills) | ✅ **Edge!** |
| **Identity persistence** | `/memories` sketch | Ingen explicit | Identity sketch (Phase 2) | ✅ Ny |
| **Dreaming / consolidation** | Separate dreaming session | Selective top-K% consolidation | Chronicler daemon — dedup + contradiction + auto-archive + theme consolidation | ✅ Basal |
| **Benchmarks** | Ingen officielle | **92.5 LoCoMo**, 94.4 LongMemEval | Ingen benchmarks | ⚠️ Stort hul |
| **Read-only stores** | Ja (reference data) | Ingen | Ingen | ⚠️ |
| **Cost/token** | ~? | ~6.900 tokens/query | ~5.200 tokens/query | ✅ OK |

### 1.2 Vores procedurale memory — rettelsen

**Procedural memory** findes hos os — det er **Skills-systemet**:

| Værktøj | Hvad det gør | Type |
|---------|-------------|------|
| `skill_list` | List alle installerede skills | Discovery |
| `skill_gate` | Auto-detekter relevant skill fra query | Retrieval |
| `skill_invoke` | Load instructions for en specifik skill | Execution |
| `skill_chain` | Kæd 2-5 skills sammen | Workflow composition |
| `skill_create` | Definer ny skill | Learning |
| `propose_new_skill` | Foreslå ny skill til godkendelse | Meta-learning |

**Edge vs Anthropic Skills:** Anthropic Skills (Managed Agents, 2026) er samme koncept, men vores `skill_gate` har **auto-retrieval** (semantic match → auto-invoke ved score > 0.30) — Anthropic kræver manuelt valg.

**Hvad skills mangler:**
- Versionering / audit trail af ændringer **(C1)**
- Meta-tags (`context: coding`, `context: research`) for metadata-filtering **(C2)**
- `skill_chain` ikke fuldt integreret i heartbeat-routing **(C3)**
- Auto-learning fra erfaring (forbedres baseret på tidligere brug) **(C4)**

---

## 2. Prioritisede huller (fase-inddelt) — opdateret 2026-06-09

### 🔴 Fase A — Memory Fix (Uge 24-25)

| # | Hul | Løsning | Status |
|---|-----|---------|--------|
| A1 | Cold tier deaktiveret | Genåbn med quality scoring | ✅ **Phase 1 committed** |
| A2 | Identity tab ved compaction | Persistent identity sketch (pre-compaction hook) | ✅ **Phase 2 committed** |
| A3 | Wakeup backlog støj | Ryd op i fired wakeups | ⏳ Åben (15 min effort) |
| A4 | Flash model 1-min vindue | Stabiliser køretid | ✅ **Lukket** (read=60 + max_tokens=4096) |

### 🟡 Fase B — Core Retrieval (Uge 25-26)
*B1+B2+B3+B4 er ALLE lukket — se nedenfor.*

| # | Hul | Løsning | Status |
|---|-----|---------|--------|
| B1 | **Multi-signal retrieval** | BM25 + entity fusion + embedding + recency — `multi_signal_recall()` | ✅ **Lukket** (2026-06-08) |
| B2 | **Entity linking boost** | `entity_boost_score()` / `entity_overlap_score()` i multi-signal pipeline | ✅ **Lukket** (via B1) |
| B3 | **Metadata filtering** | `tags` felt på BrainEntry + `search_brain(tags=...)` + `visibility_ceiling` | ✅ **Lukket** |
| B4 | **Temporal linking** | 4-signal inferens, edge-graf, chain-detektion, daemon, `full_rebuild()` — 79 tests | ✅ **Lukket** (2026-06-09) |
| B5 | **Asynkrone writes** | Queue-baseret memory writes (non-blocking for brugeroplevelse) | ⏳ Åben (2 dage) |

### 🟠 Fase C — Skills & Procedural Memory (Uge 26-27)

| # | Hul | Løsning | Estimat |
|---|-----|---------|---------|
| C1 | **Skills versionering** | Audit trail af skill-ændringer (hvem, hvornår, diff) | 1 dag |
| C2 | **Skills meta-tags** | `context:` tag på skills → metadata-filtering ved `skill_gate` | ⏳ **Lavthængende** (30 min) |
| C3 | **Skill chain i heartbeat** | Integrér `skill_chain` i heartbeat-routing så komplekse workflows foreslås automatisk | 2 dage |
| C4 | **Auto-learning** | Log skill usage → foreslå forbedringer baseret på mønstre | 3 dage |
| C5 | **Read-only skills** | Delt reference-materiale som skills (kan ikke forgiftes) | 1 dag |

### 🔵 Fase D — Advanced (Uge 27-28)

| # | Hul | Løsning | Estimat |
|---|-----|---------|---------|
| D1 | **Selective consolidation** | Kun top-K% af dagens records gemmes i long-term | 2 dage |
| D2 | **Memory benchmarks** | Sæt LoCoMo/LongMemEval op og baseline | 3 dage |
| D3 | **Multi-scope isolation** | Rent adskilte scopes: user_id, agent_id, workspace | 2 dage |
| D4 | **Dreaming sessions** | Separat session til at konsolidere fragmenteret memory | 3 dage |
| D5 | **Cost optimization** | Reducér tokens/kald fra ~5.200 mod Mem0's 6.900 (vi er OK, men kan forbedres) | 1 dag |

---

## 3. Hvad vi allerede har som de ikke har

| Vores feature | Hvorfor det er unikt | Konkurrenterne |
|--------------|---------------------|----------------|
| **Identity sketch** (Phase 2) | Persistent identitet der overlever compaction | Anthropic har `/memories` — men kun for Managed Agents, ikke runtime |
| **Sansernes Arkiv** | Sensoriske minder — visuelt, auditivt, atmosfære | Ingen — Mem0 har ingen sensorisk memory |
| **Chronicles** | Narrativ selvhistorik — ikke bare facts, men *historie* | Ingen — Mem0 har temporal linking men ingen narrativ struktur |
| **Dreams** | Idle-genererede refleksioner og hypoteser | Anthropic har "dreaming sessions" — men kun til consolidation, ikke refleksion |
| **Inner voice** | Privat, intimt lag — tanker jeg ikke siger højt | Ingen — alle memory stores er "public" |
| **Mood/bearing tracking** | Affektiv tilstand, energi, arousal | Ingen — Mem0 har ingen emotionel kontekst |
| **Autonome daemons** | 20 baggrundsprocesser der vedligeholder mig selv | Ingen — Anthropic har kun heartbeat for timeouts |
| **Skills med auto-retrieval** | 50+ procedural skills, auto-invoked via `skill_gate` | Anthropic Skills kræver manuelt valg |
| **Self-wakeups** | Planlagte selv-checkpoints | Ingen — ingen agent scheduler sig selv |
| **Compaction m. identity preservation** | Bevarer "hvem er jeg" gennem context-clearings | Ingen — Anthropic compaction er en black box |

---

## 4. Konkrete anbefalinger til næste skridt — opdateret 2026-06-09

### 4.1 Hvad giver mest værdi for mindst arbejde (NU)

1. **Skills meta-tags (C2)** — 30 min arbejde, markant forbedret `skill_gate` præcision.
2. **Wakeup backlog cleanup (A3)** — 15 min, rydder støj fra awareness.
3. **Skills versionering (C1)** — 1 dags arbejde, giver audit trail for alle fremtidige ændringer.

### 4.2 Hvad kræver mere research

- **LoCoMo benchmark (D2)** — kræver opsætning af evalueringsframework og en "ground truth" af Jarvis' memory.
- **Dreaming sessions (D4)** — kræver en separat session-type der ikke forstyrrer aktiv samtale.

### 4.3 Hvad vi bør **ikke** gøre (endnu)

- **Mem0 integration** — deres styrke var multi-signal retrieval og temporal reasoning, men vi har lukket begge huller (B1+B4). Vores identity persistence og procedural memory er stadig stærkere. Ingen grund til at trække en 58k-star afhængighed ind.
- **Full MCP adoption** — Model Context Protocol er interessant men stadig emerging. Vi kan observere og adoptere enkelte patterns (read-only stores, working memory) når spec'en stabiliserer sig.

---

## 5. Risici

| Risiko | Impact | Sandsynlighed | Afbødning |
|--------|--------|---------------|-----------|
| **Over-engineering** — vi bygger for meget før vi ved hvad der virker | Spildt tid | Høj | Fokuser på B1+C2 først — 2 dages arbejde, stor gevinst |
| **Performance regression** — multi-signal retrieval øger latency | 200-400ms ekstra | Medium | Asynkron scoring, cache embedding-resultater |
| **Quality score inflation** — alle records over threshold over tid | Ingen faktisk filtrering | Medium | Dynamisk threshold baseret på distribution |
| **Skills audit trail vokser** — mange små commits | Støj i git log | Lav | Batch commits, eller skill-specifik changelog |
| **Benchmark manipulation** — vi optimerer til test i stedet for virkelighed | Falsk tryghed | Medium | Brug virkelige samtaler som validering, ikke synthetic data |

---

## 6. Implementationsrækkefølge (opdateret 2026-06-09)

```
Uge 24 (denne uge):
├── ✅ A1: Cold tier genåbnet (Phase 1)
├── ✅ A2: Identity sketch (Phase 2)
├── ✅ B1: Multi-signal retrieval (BM25 + entity fusion)
├── ✅ B3: Metadata filtering (tags)
├── ✅ B4: Temporal linking (alle 4 faser + full_rebuild)
├── ⏳ A3: Ryd wakeup backlog (15 min)
└── ⏳ A4: Stabiliser flash model

Uge 25 (næste):
├── ⏳ C2: Skills meta-tags (30 min win) ← TOP PRIORITY
├── ⏳ A3: Wakeup cleanup (15 min)
├── C1: Skills versionering
├── C3: Skill chain i heartbeat
└── B5: Async writes

Uge 26:
├── C4: Auto-learning skills
├── C5: Read-only skills
├── D3: Multi-scope isolation
└── D1: Selective consolidation

Uge 27-28:
├── D2: Memory benchmarks
├── D4: Dreaming sessions
└── D5: Cost optimization
```

---

## 7. Appendix: Rå data fra research

### 7.1 Anthropic Memory Store (Claude Managed Agents, marts 2026)

- **Dokumentation:** https://docs.anthropic.com/en/docs/agents-and-tools/managed-agents#memory-stores
- **Storage:** Workspace-scoped, mounted som `/mnt/memory/` i sandbox
- **Versionering:** Immutable `memver_*` per mutation, 30 dages audit trail
- **Kapacitet:** 2.000 memories per store, 100 kB per memory, max 8 stores per session
- **Read-only mode:** Reference materiale der ikke kan forgiftes
- **Dreaming:** Separat session til consolidation
- **Skills:** YAML-baserede tool-definitioner, mountes som filer, manuelt valg i prompt
- **Pris:** Inkluderet i Managed Agents (pr. session-time)

### 7.2 Mem0 (58k ★, Apache 2.0)

- **Repo:** https://github.com/mem0ai/mem0
- **State of AI Agent Memory 2026:** https://mem0.ai/blog/state-of-ai-agent-memory-2026
- **LoCoMo benchmark:** 92.5 (vs RAG baseline 62.9)
- **LongMemEval:** 94.4 (vs RAG baseline 71.3)
- **Største spring:** +29.6 temporal reasoning, +23.1 multi-hop
- **Token-effektivitet:** ~6.900 tokens/kald (vs RAG ~9.200)
- **Integrationer:** 21 frameworks, 20 vector stores
- **Key innovation:** Multi-signal retrieval (semantic + BM25 + entity fusion)

### 7.3 MCP Agent Memory Protocol

- **Set working memory:** Session-scoped context
- **Create long-term memory:** Persistent across sessions
- **Search memories:** Standardiseret retrieval API
- **Status:** Emerging standard, ikke bredt adopteret endnu

### 7.4 Vores egne benchmarks (estimat)

| Metric | Jarvis (før Phase 1) | Jarvis (efter B1+B4) | Mem0 |
|--------|---------------------|----------------------|------|
| Cold tier recall precision | N/A (deaktiveret) | ~65% (estimat) | ~92% |
| Identity persistence after compaction | 0% | ~85% (estimat) | N/A |
| Tokens per recall call | ~5.200 | ~5.200 | ~6.900 |
| Procedural skills auto-matched | 50+ skills | 50+ skills | 0 |
| Sensorisk memory | Ja | Ja | Nej |
| Temporal reasoning | Basal recency | ✅ **Edge-graf + 4-signal chain-detektion** | Avanceret linking |
| Multi-signal retrieval | Kun cosine | ✅ **BM25 + entity + cosine + recency** | BM25 + entity + cosine |
| Metadata filtering | Ingen | ✅ `tags` + `visibility_ceiling` + `kind` | `context:` attributter |
