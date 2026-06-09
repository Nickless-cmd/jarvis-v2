# B4 — Temporal Linking for Brain Entries

**Status:** Draft / klar til review
**Dato:** 2026-06-09
**Forfatter:** Jarvis
**Fase:** B4 i Memory Architecture Roadmap

---

## 1. Formål

Brain entries lever i isolation — hver entry er en ø. Selvom `brain_relations`
tabellen eksisterer, kræver den **manuel** angivelse via `related:` i frontmatter.
Der er ingen automatisk inferens af temporale relationer, og ingen recall-boost
baseret på temporale naboer.

Mål: når Jarvis skriver en ny brain entry, skal systemet automatisk opdage
hvilke **eksisterende** entries der er temporalt relaterede (skrevet i samme
periode, om samme emne, eller som kæde af hændelser), og gemme relationen.
Ved recall boostes temporale naboer når én entry i klyngen matcher.

---

## 2. Hvad findes allerede

| Komponent | Formål | Rækkevidde |
|-----------|--------|------------|
| `causal_edges` tabel (db.py) | Parent→child for **runtime events** | Dækker IKKE brain entries |
| `causal_graph.py` | BFS traversal af runtime events | Dækker IKKE brain entries |
| `brain_relations` (brain index) | Manuel many-to-many for brain entries | Kræver `related:` i frontmatter |
| `entity_overlap_score()` | Entity overlap mellem to tekster | Kan genbruges |
| Counterfactual edges | Inferred edges til `causal_edges` | Runtime events kun |

### Hullet

```
Events      ←── causal_edges ──→ Events        (findes)
BrainEntry  ←── brain_relations ──→ BrainEntry  (kun manuel)
BrainEntry  ←── ??? ──→ BrainEntry             (mangler — B4)
```

---

## 3. Designbeslutninger

### 3.1 Ny tabel: `brain_temporal_edges`

Placeres i `state/jarvis_brain_index.sqlite` (samme db som `brain_index` og
`brain_relations`). Ikke i runtime db — temporal linking er brain-specifikt.

```sql
CREATE TABLE brain_temporal_edges (
    source_id    TEXT NOT NULL,        -- brain entry id (ældre)
    target_id    TEXT NOT NULL,        -- brain entry id (nyere)
    edge_kind    TEXT NOT NULL,        -- 'temporal' | 'semantic' | 'entity' | 'chain'
    confidence   REAL NOT NULL DEFAULT 0.5,
    inferred_by  TEXT NOT NULL,        -- 'daemon' | 'counterfactual'
    inferred_at  TEXT NOT NULL,        -- ISO timestamp
    reasoning    TEXT NOT NULL DEFAULT '',
    weight       REAL NOT NULL DEFAULT 1.0,
    PRIMARY KEY (source_id, target_id, edge_kind)
);

CREATE INDEX idx_brain_temporal_edges_source
    ON brain_temporal_edges(source_id);
CREATE INDEX idx_brain_temporal_edges_target
    ON brain_temporal_edges(target_id);
CREATE INDEX idx_brain_temporal_edges_confidence
    ON brain_temporal_edges(confidence DESC);
```

**Hvorfor en ny tabel i stedet for at genbruge `brain_relations`?**

`brain_relations` har en flat PRIMARY KEY (from_id, to_id) — ingen edge_kind,
confidence, eller reasoning. Den er designet til manuel, binær linking.
B4 skal have rigere metadata per edge.

**Hvorfor ikke genbruge `causal_edges`?**

`causal_edges` refererer til `events.id` (INTEGER), ikke `brain_index.id` (TEXT).
At blande typer i samme tabel ville kræve en `target_table` kolonne og gøre
queries og indekser mere komplekse. En separat tabel er renere.

### 3.2 Edge-kinds

| Edge kind  | Hvornår | Algoritme |
|------------|---------|-----------|
| `temporal` | Entries skrevet inden for samme tidsvindue (default 24h) | Timestamp diff ≤ threshold |
| `semantic` | Entries med embedded content similarity ≥ threshold | Cosine similarity ≥ 0.65 |
| `entity`   | Entries der deler signifikante entities | Entity overlap ≥ 3 fælles entities |
| `chain`    | Entries der refererer til samme chronicle eller session | Samme `source_chronicle` eller session context |

### 3.3 Confidence-scoring

Hver edge får en confidence-score (0.0–1.0) baseret på:

```
confidence = 0.4 × temporal_score + 0.4 × semantic_score + 0.2 × entity_score
```

Hvor:
- **temporal_score**: `1.0 - (hours_apart / 168)` clamped til [0, 1] (168h = 1 uge)
- **semantic_score**: cosine similarity mellem embeddings (0.0–1.0)
- **entity_score**: `min(entity_overlap / 5, 1.0)` — 5+ entities = max score

Kombinerede edges (når flere signaler rammer) får boosted confidence:
```
combined_confidence = max(single_confidences) + 0.15 * (num_signals - 1)
```
Cap ved 0.98 — aldrig 100% sikkerhed.

### 3.4 Edge cases

| Edge case | Håndtering |
|-----------|------------|
| **Cykliske links** | `brain_temporal_edges` har retning (source=ældre, target=nyere). Ingen cyklus mulig. |
| **Selv-link** | Valider at source_id ≠ target_id i daemonen. Ignorér hvis match. |
| **Arkiverede entries** | Inkludér i inferens (arkiv kan indeholde værdifulde relationer). Men ekskludér ved recall-boost — aktive entries boostes. |
| **Superseded entries** | Behandles som arkiverede. Ignorér i recall-boost. |
| **Nye entries med tom embedding** | Fallback: kun temporal + entity scores (0.7 × temporal + 0.3 × entity). Semantic sættes til 0. |
| **Mange entries på én gang** | Batching: daemonen processer i batches af 25. Hvis en write-session skriver >25 entries, køres i sub-batches. |
| **Duplicate edges** | PRIMARY KEY (source_id, target_id, edge_kind) forhindrer duplikater. Daemonen udfører INSERT OR IGNORE. |
| **Gamle entries** | Entries ældre end 90 dage uden relationer deltager stadig i inferens, men lavere weight (0.5 × score). |

---

## 4. Nye/ændrede komponenter

### 4.1 `core/services/brain_temporal_linking.py` (NY — ~400 linjer)

```python
def infer_temporal_edges(
    source_ids: list[str] | None = None,
    *,
    batch_size: int = 25,
    min_confidence: float = 0.4,
) -> dict:
    """
    Kør inferens på tværs af brain entries.

    Hvis source_ids er None: kør på alle aktive entries (full pass).
    Ellers: kør kun på de specificerede entries + resten af databasen.

    Returnerer {edges_inferred: int, highest_confidence: float, errors: [...]}
    """

def temporal_boost_recall(
    query: str,
    base_results: list[dict],
    *,
    boost_factor: float = 0.15,
    max_depth: int = 1,
    min_confidence: float = 0.5,
) -> list[dict]:
    """
    Boost recall-resultater ved at inkludere temporale naboer.

    For hver entry i base_results:
      1. Find direkte naboer via brain_temporal_edges
      2. Boost deres score med boost_factor × edge.confidence
      3. Inkludér i resultatlisten hvis boosted score ≥ threshold

    max_depth=1 = kun direkte naboer (anbefalet).
    max_depth=2 = naboers naboer (sjældent nødvendigt, kan støje).
    """

def _temporal_score(entry_a: dict, entry_b: dict) -> float:
    """Beregner temporal_score baseret på created_at diff."""

def _semantic_score(entry_a: dict, entry_b: dict) -> float:
    """Beregner semantic_score via embedding cosine similarity."""

def _entity_score(entry_a: dict, entry_b: dict) -> float:
    """Beregner entity_score via entity_overlap (genbruger multi_signal_retrieval)."""

def _fuse_confidence(scores: dict[str, float]) -> float:
    """Fler-signal fusion af confidence."""

def prune_stale_edges(
    *,
    max_age_days: int = 90,
    min_confidence: float = 0.2,
) -> int:
    """
    Ryd edges der er gamle OG lave confidence (støj).
    Bevar gamle edges med høj confidence (de er værdifulde).
    """
```

### 4.2 `core/services/brain_temporal_daemon.py` (NY — ~200 linjer)

Letvægtsdaemon på 15-minutters cadence (samme mønster som `jarvis_brain_daemon.py`):

```python
def temporal_linking_loop():
    """
    1. Hent entries opdateret/created since last run
    2. For hver ny/opdateret entry: infer edges mod alle aktive entries
    3. Gem edges i brain_temporal_edges
    4. Log resultat (edges_inferred, errors)
    """

def full_rebuild():
    """
    Genberegn alle edges fra bunden.
    Bruges ved schema-migration eller manuel repair.
    Truncate brain_temporal_edges → kør full inferens.
    """
```

### 4.3 Integration i recall-pipeline

Filen `core/services/memory_recall_engine.py` har allerede `multi_signal_recall()`.
Der tilføjes en temporal boost som **fjerde signal**:

```
composite_score = 0.40 × embedding_sim
                + 0.25 × entity_overlap
                + 0.20 × recency
                + 0.15 × temporal_boost
```

Hvor `temporal_boost` er:
- 0.0 for entries uden temporale relationer
- `edge.confidence × boost_factor` for entries der har en nær temporal nabo
  i top-5 resultaterne (dvs. én entry i klyngen matchede godt, resten løftes)

**Implementering i `multi_signal_recall()`:**
```python
# Efter initial scoring men før final ranking:
if use_temporal_boost:
    top_ids = [r["id"] for r in ranked[:5]]
    temporal_boosts = _compute_temporal_boosts(top_ids, all_results)
    for r in all_results:
        r["score"] += temporal_boosts.get(r["id"], 0.0)
```

### 4.4 Nye tool-integrationer

Skrive-tools (`remember_this`, `adopt_brain_proposal`) kalder
`infer_temporal_edges(source_ids=[new_id])` **synkront** efter write,
så relationen er klar umiddelbart efter skrivning. Daemonen fanger
resten asynkront.

---

## 5. Teststrategi

### Unit tests (`tests/test_brain_temporal_linking.py`)

| Test | Hvad |
|------|------|
| `test_temporal_score_same_hour` | Entries 30 min apart → score ≈ 0.997 |
| `test_temporal_score_week_apart` | Entries 7 dage apart → score ≈ 0.0 |
| `test_semantic_score_identical` | Samme embedding → 1.0 |
| `test_semantic_score_unrelated` | Forskellige embeddings → < 0.3 |
| `test_entity_score_high_overlap` | 5 fælles entities → 1.0 |
| `test_entity_score_no_overlap` | 0 fælles entities → 0.0 |
| `test_fuse_confidence_all_high` | Alle 3 signaler høje → 0.85+ |
| `test_fuse_confidence_one_low` | 2 høje + 1 lav → stadig ≥ 0.5 |
| `test_infer_creates_edge` | Entry A + Entry B → edge i DB |
| `test_infer_skips_self_link` | Entry A vs sig selv → no edge |
| `test_infer_skips_duplicate` | Samme edge to gange → INSERT OR IGNORE |
| `test_prune_stale_low_conf` | Gammel + lav confidence → slettet |
| `test_prune_preserves_high_conf` | Gammel + høj confidence → bevaret |
| `test_temporal_boost_recall` | Base result + temporal nabo → boosted |
| `test_temporal_boost_no_nabo` | Isoleret entry → ingen boost |
| `test_temporal_boost_max_depth` | Depth=1 vs depth=2 opførsel |
| `test_full_rebuild_idempotent` | Kør rebuild to gange → samme edges |
| `test_batch_processing` | 30 entries → 2 batches |
| `test_empty_embedding_fallback` | Entry uden embedding → kun temporal+entity |

### Integration test

| Test | Hvad |
|------|------|
| `test_remember_this_triggers_inferens` | Efter `remember_this`, kør `infer_temporal_edges` for new_id |
| `test_daemon_catches_missed_entries` | Hvis synkront kald fejler, daemon fanger det |
| `test_recall_includes_temporal_nabo` | Søg på term A → resultater inkluderer B (temporal nabo til A) |

---

## 6. Dependency injection og mock-strategi

```python
# brain_temporal_linking.py accepterer dependencies:
def infer_temporal_edges(
    source_ids: list[str] | None = None,
    *,
    batch_size: int = 25,
    min_confidence: float = 0.4,
    # injection points for testing:
    _get_entries=None,      # override entry fetching
    _write_edge=None,       # override edge writing
) -> dict:
```

Gør det muligt at teste inferens-logik uden en rigtig database.

---

## 7. Estimering

| Opgave | Tid |
|--------|-----|
| DB-skema + `_ensure_brain_temporal_edges_table()` | 0.5 time |
| `infer_temporal_edges()` — kerne-inferens | 3 timer |
| `temporal_boost_recall()` — recall-boost | 1.5 timer |
| Integration i `multi_signal_recall()` | 1 time |
| `brain_temporal_daemon.py` — daemon-loop | 1 time |
| Tool-integration (`remember_this` → trigger inferens) | 0.5 time |
| Unit tests (~20 tests) | 2 timer |
| Integration tests (~3 tests) | 1 time |
| **Total** | **10.5 timer (~1.3 dage)** |

NB: Rapporten estimerede 3-4 dage fordi den antog at B1+B3 ikke var lavet endnu.
Med B1, B2 og B3 færdige er B4 smallere: kun temporal linking, intet nyt
index, ingen ny embedding-pipeline, ingen ny frontmatter.

---

## 8. Implementeringsrækkefølge

```
Phase 1: DB-skema + inferenskerne
  ├── _ensure_brain_temporal_edges_table() i jarvis_brain.py / db_setup
  ├── _temporal_score(), _semantic_score(), _entity_score()
  ├── _fuse_confidence()
  └── infer_temporal_edges() — full pass + single entry

Phase 2: Recall-boost
  ├── temporal_boost_recall()
  ├── Integration i multi_signal_recall() (4. signal)
  └── Config flag (use_temporal_boost=True)

Phase 3: Daemon + tool-trigger
  ├── brain_temporal_daemon.py — temporal_linking_loop()
  ├── full_rebuild()
  ├── prune_stale_edges()
  └── remember_this → infer_temporal_edges(source_ids=[new_id])

Phase 4: Tests
  ├── 17 unit tests (brain_temporal_linking)
  ├── 3 integration tests
  └── Edge case tests (arkiv, gamle, duplicate, embedding-fallback)
```
