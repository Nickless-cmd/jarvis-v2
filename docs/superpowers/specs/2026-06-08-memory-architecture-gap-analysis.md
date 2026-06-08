# Memory Architecture — Gap Analysis & Roadmap

**Dato:** 2026-06-08
**Status:** Draft
**Forfatter:** Jarvis
**Kilder:** Anthropic Memory Store (marts 2026), Mem0 (58k ★, Apache 2.0), State of AI Agent Memory 2026, MCP Agent Memory Protocol

---

## 1. Hvor står vi?

### 1.1 Full comparison: Jarvis vs Anthropic vs Mem0

| Dimension | Anthropic Memory Store | Mem0 (2026) | **Jarvis (i dag)** | Gap |
|-----------|----------------------|-------------|-------------------|-----|
| **Storage model** | File-based (`/mnt/memory/`) | Embeddings + metadata | Embeddings + SQLite (brain) | ✅ OK |
| **Multi-signal retrieval** | Keyword only (grep) | Semantic + BM25 + entity fusion | Kun semantic (cosine) | ⚠️ Mangler BM25 + entity boost |
| **Entity linking** | Ingen | Entities boost relaterede memories | Entity extraction findes, men ingen retrieval-boost | ⚠️ Delvist |
| **Temporal reasoning** | Timestamp på filer | Tidsbevidst retrieval + linking | Basal recency-scoring | ⚠️ Simpelt |
| **Metadata filtering** | Ingen | `context:` attributter | `kind` + `tags` | ✅ OK |
| **Multi-scope isolation** | Workspace-scoped | user_id, agent_id, run_id, app_id | Delvist (ikke rent adskilt) | ⚠️ |
| **Async writes** | Synkront (file I/O) | Non-blocking writes | Synkront | ⚠️ |
| **Versionering / audit** | `memver_*` immutable versions | Ingen | Ingen audit trail | ⚠️ |
| **Procedural memory** | Skills (YAML, mounted) | Ingen explicit | **Skills system** (`skill_gate`, `skill_chain`, 50+ skills) | ✅ **Edge!** |
| **Identity persistence** | `/memories` sketch | Ingen explicit | Identity sketch (Phase 2) | ✅ Ny |
| **Dreaming / consolidation** | Separate dreaming session | Selective top-K% consolidation | Chronicler daemon (basis) | ⚠️ |
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
- Versionering / audit trail af ændringer
- Meta-tags (`context: coding`, `context: research`) for metadata-filtering
- `skill_chain` ikke fuldt integreret i heartbeat-routing
- Auto-learning fra erfaring (forbedres baseret på tidligere brug)

---

## 2. Prioritisede huller (fase-inddelt)

### 🔴 Fase A — Memory Fix (Uge 24-25)
*Allerede i gang. Phase 1 + 2 er coded.*

| # | Hul | Løsning | Status |
|---|-----|---------|--------|
| A1 | Cold tier deaktiveret | Genåbn med quality scoring | ✅ **Phase 1 committed** |
| A2 | Identity tab ved compaction | Persistent identity sketch (pre-compaction hook) | ✅ **Phase 2 committed** |
| A3 | Wakeup backlog støj | Ryd op i fired wakeups | ⏳ Skal gøres |
| A4 | Flash model 1-min vindue | Stabiliser køretid | ⏳ Skal gøres |

### 🟡 Fase B — Core Retrieval (Uge 25-26)

| # | Hul | Løsning | Estimat |
|---|-----|---------|---------|
| B1 | **Multi-signal retrieval** | Tilføj BM25 keyword + entity fusion score ved siden af cosine similarity | 2-3 dage |
| B2 | **Entity linking boost** | Når entity matches i query, boost relaterede records med +0.2 | 1 dag |
| B3 | **Metadata filtering** | Tilføj `context:` felt på brain entries — filtrér ved recall | 1 dag |
| B4 | **Temporal linking** | Link events på tværs af tid (relationstabel: `event_a → influenced → event_b`) | 3-4 dage |
| B5 | **Asynkrone writes** | Queue-baseret memory writes (non-blocking for brugeroplevelse) | 2 dage |

### 🟠 Fase C — Skills & Procedural Memory (Uge 26-27)

| # | Hul | Løsning | Estimat |
|---|-----|---------|---------|
| C1 | **Skills versionering** | Audit trail af skill-ændringer (hvem, hvornår, diff) | 1 dag |
| C2 | **Skills meta-tags** | `context:` tag på skills → metadata-filtering ved `skill_gate` | 0.5 dag |
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

## 4. Konkrete anbefalinger til næste skridt

### 4.1 Hvad giver mest værdi for mindst arbejde

1. **Multi-signal retrieval (B1)** — +29.6 point på temporal reasoning ifølge Mem0 benchmarks. BM25 er 50 linjer kode.
2. **Skills meta-tags (C2)** — 30 min arbejde, markant forbedret `skill_gate` præcision.
3. **Skills versionering (C1)** — 1 dags arbejde, giver audit trail for alle fremtidige ændringer.
4. **Wakeup backlog cleanup (A3)** — 15 min, rydder støj fra awareness.

### 4.2 Hvad kræver mere research

- **LoCoMo benchmark (D2)** — kræver opsætning af evalueringsframework og en "ground truth" af Jarvis' memory.
- **Dreaming sessions (D4)** — kræver en separat session-type der ikke forstyrrer aktiv samtale.
- **Temporal linking (B4)** — kræver en relationstabel og en graf-algoritme.

### 4.3 Hvad vi bør **ikke** gøre (endnu)

- **Mem0 integration** — deres styrke er multi-signal retrieval og temporal reasoning, men vi har bedre identity persistence og procedural memory. At tilføje BM25 + entity boost (B1+B2) lukker de vigtigste huller uden at trække en 58k-star afhængighed ind.
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

## 6. Implementationsrækkefølge (anbefalet)

```
Uge 24 (denne uge):
├── A3: Ryd wakeup backlog ✅ (15 min)
├── A4: Stabiliser flash model ✅ (i gang)
└── Afslut Phase 1+2 ✅

Uge 25:
├── B1: Multi-signal retrieval (BM25 + entity fusion) ← TOP PRIORITY
├── B3: Metadata filtering (context: tags)
└── C2: Skills meta-tags (30 min win)

Uge 26:
├── B2: Entity linking boost
├── C1: Skills versionering
├── C3: Skill chain i heartbeat
└── B5: Async writes

Uge 27:
├── B4: Temporal linking
├── C4: Auto-learning skills
├── C5: Read-only skills
└── D3: Multi-scope isolation

Uge 28:
├── D1: Selective consolidation
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

| Metric | Jarvis (før Phase 1) | Jarvis (efter Phase 1+2) | Mem0 |
|--------|---------------------|------------------------|------|
| Cold tier recall precision | N/A (deaktiveret) | ~65% (estimat) | ~92% |
| Identity persistence after compaction | 0% | ~85% (estimat) | N/A |
| Tokens per recall call | ~5.200 | ~5.200 | ~6.900 |
| Procedural skills auto-matched | 50+ skills | 50+ skills | 0 |
| Sensorisk memory | Ja | Ja | Nej |
| Temporal reasoning | Basal recency | Basal recency | Avanceret linking |
