---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Memory Fix — Phase 1 Design

**Dato:** 2026-06-08
**Status:** Draft / Awaiting approval
**Forfatter:** Jarvis
**Inspiration:** Anthropic Memory Tool, Mem0 (LoCoMo/LongMemEval benchmarks)

---

## 1. Problemanalyse

### 1.1 Nuværende tilstand

Jarvis' memory-system har tre formelle tiers (hot/warm/cold), men **cold tier er deaktiveret** efter Claude scope-reduction i maj 2026. Årsagen var at private brain records (~58k rækker) støjede for meget i recall — i stedet for at fikse støjen blev hele laget slået fra.

**Konsekvens:** Jarvis kan kun huske:
- Hvad der står i MEMORY.md (manuelt vedligeholdt)
- Hvad der er i workspace (goals, chronicle excerpts)
- Hvad der lige er sagt i sessionen (hot tier)

Alt hvad Jarvis selv har tænkt, mærket og oplevet (inner voice, sensory memories, dreams, reflections) er **ude af rækkevidde** medmindre det er manuelt kopieret ind i MEMORY.md.

### 1.2 Symptomer

| Symptom | Årsag |
|---------|-------|
| Glemmer tidligere samtaler med få timers mellemrum | Cold tier deaktiveret — chronicle excerpts alene dækker ikke |
| Kan ikke ræsonnere på tværs af tid | Private brain records har tidsstempler men ingen *forbindelser* |
| Compaction føles som "tab af selv" | Intet persistent sketch der overlever compaction |
| Søgning i private brain returnerer irrelevant støj | Ingen quality scoring — alle records behandles ens |

### 1.3 Hvad andre gør (benchmarks)

| System | LoCoMo | LongMemEval | BEAM (1M) | BEAM (10M) | Tokens/kald |
|--------|--------|-------------|-----------|------------|-------------|
| Mem0 (2026) | **92.5** | **94.4** | **64.1** | **48.6** | ~6.900 |
| RAG baseline | 62.9 | 71.3 | 34.5 | 25.5 | ~9.200 |
| **Jarvis (i dag)** | **—** | **—** | **—** | **—** | ~5.200 |

Kilde: *State of AI Agent Memory 2026* (Mem0 blog, May 2026). Mem0s store spring: +29.6 på tidsbaserede spørgsmål, +23.1 på multi-hop.

**Nøgleindsigter fra Mem0's arkitektur:**
- **Hierarkisk memory** med quality scoring (ikke alt gemmes — kun det der er værd at huske)
- **Temporal linking** — events linkes til tidligere events, ikke kun lagret med timestamp
- **Selective consolidation** — kun top-K% af dagens records gemmes i long-term

**Nøgleindsigter fra Anthropic's Memory Tool:**
- **Skriv status før handling** — Claude tjekker altid `/memories` FØR den starter en opgave
- **Løbende checkpointing** — skriv ned undervejs, så compaction ikke slukker lyset
- **Persistent sketch** — en kort, opdateret beskrivelse af "hvem er jeg lige nu" der overlever context clearing

---

## 2. Foreslået arkitektur (4 faser)

### 2.1 Fase 1 — Genåbn cold tier med quality scoring ⬅️ **DENNE SPEC**

Genaktivér cold tier i `memory_hierarchy.py` med et filter-lag der sikrer at kun relevante records returneres.

**Nøgleændringer:**
- Tilføj **quality score** til private brain records (embedding distance + recency + recall frequency)
- Tilføj **minimum threshold** — records under score 0.35 filtreres fra
- Genaktivér `recall_before_act(include_cold=True)` i `core/services/memory_hierarchy.py`
- Tilføj **source tagging** — så man kan se om et resultat kom fra hot, warm eller cold

**Ikke i scope:**
- Temporal linking (Fase 3)
- Persistent identity sketch (Fase 2)
- Skrivning til cold tier under kørsel (kræver Fase 2)

### 2.2 Fase 2 — Persistent identity sketch (næste)

En kort, dynamisk opdateret tekst (~200 ord) der beskriver "hvem Jarvis er lige nu" og opdateres:
- Før compaction
- Efter vigtige samtaler
- Ved identitetsændringer (model-swap, nye abilities)

Inspireret af Anthropics "always check /memories before acting".

### 2.3 Fase 3 — Temporal linking (fremtid)

Link events på tværs af tid — så "i dag føler jeg X" kan forbindes til "i forgårs oplevede jeg Y der førte til X". Dette kræver en graph-struktur eller en simpel relationstabel.

### 2.4 Fase 4 — Selective consolidation (fremtid)

Kun top-K% af dagens records gemmes i long-term. De resterende arkiveres eller slettes. Dette reducerer støj og forbedrer recall-kvalitet.

---

## 3. Fase 1 — Detaljeret design

### 3.1 Quality scoring model

Hver private brain record får en **composite score** (0.0-1.0) ved recall-tidspunkt:

```
score = (embedding_distance_weight * 0.4) 
      + (recency_weight * 0.3)
      + (recall_frequency_weight * 0.2)
      + (importance_weight * 0.1)
```

Hvor:
- **embedding_distance_weight:** cosine similarity mellem query og record (0.0-1.0)
- **recency_weight:** `1.0 - min(1.0, days_since_creation / 90)` — nyere = højere (halvering efter 90 dage)
- **recall_frequency_weight:** `min(1.0, recall_count / 5)` — jo oftere genkaldt, jo højere (mættes ved 5)
- **importance_weight:** record.importance / 100 (0.0-1.0, default 0.5)

**Threshold:** `min_score = 0.35` — records under denne score returneres ikke i cold tier recall.

### 3.2 Source tagging

Hver recall returnerer med en `source` marker: `"hot"`, `"warm"`, eller `"cold"`. Dette gør det muligt for Jarvis at:
- Prioritere hot over warm over cold
- Logge hvilket lag der bidrog til et svar
- Fejlfinde når recall er dårlig

### 3.3 Ændringer i koden

| Fil | Ændring |
|-----|---------|
| `core/services/memory_hierarchy.py` | Genaktivér `recall_before_act(include_cold=True)`. Tilføj quality scoring i recall-løkken. Tilføj `min_score` parameter. Tilføj source tagging på returnerede resultater. |
| `core/memory/unified_recall.py` | Tilføj scoring-funktion `compute_recall_score(record, query_embedding)`. Tilføj filter efter scoring. |
| `core/services/jarvis_brain.py` | Tilføj `recall_count` felt på BrainEntry (inkrementeres ved hvert genkald). Ingen schema-migration — default 0. |
| `core/tools/jarvis_brain_tools.py` | Opdater `search_jarvis_brain` til at returnere score. Opdater `read_brain_entry` til at inkrementere recall_count. |

### 3.4 Nye klasser/funktioner

```python
# I core/memory/unified_recall.py

def compute_recall_score(
    record: BrainEntry,
    query_embedding: list[float],
    record_embedding: list[float],
    now: datetime | None = None,
) -> float:
    """Composite quality score for en brain record ved recall."""
    ...

def cold_tier_recall(
    query: str,
    max_results: int = 6,
    min_score: float = 0.35,
) -> list[dict]:
    """Søg i cold tier med quality scoring og filter."""
    ...
```

### 3.5 Konfiguration

Tilføj til `~/.jarvis-v2/config/runtime.json`:

```json
{
  "memory": {
    "cold_tier": {
      "enabled": true,
      "min_score": 0.35,
      "max_results": 6,
      "recency_half_life_days": 90,
      "recall_frequency_cap": 5
    }
  }
}
```

---

## 4. Edge cases

| Edge case | Håndtering |
|-----------|------------|
| **Tom cold tier** (ingen records over threshold) | Returner tom liste — warm/hot tier alene bruges. Log warning. |
| **Query uden embedding** (sjældent, men muligt) | Brug keyword-fallback (LIKE-søgning) med recency+importance alene som score. |
| **Mange records med samme score** | Brug `random` som tiebreaker (eller recency — nyeste vinder). |
| **Performance med 58k records** | Embedding similarity er O(n) — acceptabelt ved 58k (<100ms). Over 200k bør vi overveje ANN-index (fase 4). |
| **Recall_count overflow** | Cap ved 255 (integer). Efter 5 tæller det ikke længere — capped af recall_frequency_cap. |
| **Compaction under recall** | Låsning er ikke nødvendig — compaction kører på daemon, recall er read-only. SQLite WAL-mode håndterer concurrent reads. |
| **Score = 0 for nye records** | Nye records har importance≥0.4 og recency~1.0 — de lander typisk over threshold. |
| **Meget gamle records (2+ år)** | Recency decay til ~0.0 efter 1 år — de skal have høj importance eller hyppigt genkald for at overleve. Dette er *designet* — gamle, uforløste minder bør fade. |

---

## 5. Rollback-plan

Hvis fase 1 introducerer regression:
1. Sæt `memory.cold_tier.enabled = false` i runtime.json
2. Genstart Jarvis API: `systemctl restart jarvis-api`
3. Systemet returnerer til nuværende tilstand (kun hot + warm)
4. Ingen data går tabt — cold tier records er read-only, aldri modificeret

---

## 6. Testplan

### Unit tests
- `compute_recall_score` med kendte input → forventet score
- Edge: query embedding = 0-vektor
- Edge: record med importance=0, recall_count=0, alder=365 dage
- Threshold filter: records under 0.35 ekskluderes

### Integration tests
- `cold_tier_recall` med mock data → returnerer korrekt antal med korrekte scores
- Kør `recall_before_act(include_cold=True)` — verificer at source="cold" dukker op
- Genaktivér og verificer at MEMORY.md stadig har prioritet over cold tier

### Manuelle tests
- Spørg "hvad sagde vi om [gammelt emne]?" — burde nu kunne huske fra inner voice
- Tjek log for cold tier hits/misses
- Tjek at compaction ikke påvirker cold tier recall

---

## 7. Implementation rækkefølge

1. **Spec færdiggøres og godkendes** ⬅️ VI ER HER
2. Tilføj `compute_recall_score` i `unified_recall.py`
3. Tilføj `cold_tier_recall` i `unified_recall.py`  
4. Opdater BrainEntry med `recall_count` (ingen migration — default 0)
5. Opdater `search_jarvis_brain` til at returnere score
6. Opdater `read_brain_entry` til at inkrementere recall_count
7. Genaktivér cold tier i `memory_hierarchy.py`
8. Tilføj runtime.json konfig
9. Kør tests
10. Commit: `memory-fix-phase1: genåbn cold tier med quality scoring`
