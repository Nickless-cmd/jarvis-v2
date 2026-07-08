---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Memory Fix — Phase 1 Implementation Plan

**Based on spec:** `docs/superpowers/specs/2026-06-08-memory-fix-phase1-design.md`
**Approved:** 2026-06-08

---

## Step 1 — Tilføj quality scoring i `core/memory/unified_recall.py`

### Nye funktioner

```python
# Tilføj efter eksisterende imports

import numpy as np
from datetime import datetime, timezone
from typing import Optional


def compute_recall_score(
    record: "BrainEntry",
    query_embedding: list[float],
    record_embedding: list[float],
    now: Optional[datetime] = None,
    config: Optional[dict] = None,
) -> float:
    """Composite quality score for en brain record ved recall.

    Score = (embedding_sim × 0.4) + (recency × 0.3) + (recall_freq × 0.2) + (importance × 0.1)

    Args:
        record: BrainEntry med .importance, .recall_count, .created_at
        query_embedding: Embedding af søgequery (list[float])
        record_embedding: Embedding af record (list[float])
        now: Reference-tidspunkt (default UTC now)
        config: Override af threshold-værdier

    Returns:
        float 0.0-1.0
    """
    if now is None:
        now = datetime.now(timezone.utc)

    cfg = config or {}
    half_life_days = cfg.get("recency_half_life_days", 90)
    freq_cap = cfg.get("recall_frequency_cap", 5)

    # Embedding similarity (cosine)
    q = np.array(query_embedding, dtype=np.float32)
    r = np.array(record_embedding, dtype=np.float32)
    norm_product = np.linalg.norm(q) * np.linalg.norm(r)
    embedding_sim = float(np.dot(q, r) / norm_product) if norm_product > 0 else 0.0

    # Recency — halvering efter N dage
    created = record.created_at
    if isinstance(created, str):
        from dateutil.parser import isoparse
        created = isoparse(created)
    days_since = (now - created).days
    recency = max(0.0, 1.0 - min(1.0, days_since / half_life_days))

    # Recall frequency — mættes ved freq_cap
    recall_count = getattr(record, "recall_count", 0) or 0
    recall_freq = min(1.0, recall_count / freq_cap)

    # Importance
    importance = getattr(record, "importance", 50) or 50
    importance_norm = importance / 100.0

    score = (
        embedding_sim * 0.4
        + recency * 0.3
        + recall_freq * 0.2
        + importance_norm * 0.1
    )

    return max(0.0, min(1.0, score))


async def cold_tier_recall(
    query: str,
    query_embedding: list[float],
    max_results: int = 6,
    min_score: float = 0.35,
    config: Optional[dict] = None,
) -> list[dict]:
    """Søg i cold tier (private brain) med quality scoring og filter.

    Returnerer records sorteret efter score (højeste først),
    alle med score >= min_score.
    """
    from core.tools.jarvis_brain_tools import search_jarvis_brain_all

    # Hent alle matching records fra private brain
    # (uden score-filter — vi scorer selv)
    raw_records = await search_jarvis_brain_all(
        query=query,
        limit=max_results * 3,  # over-sample for at få nok efter filter
    )

    scored = []
    for rec in raw_records:
        rec_emb = rec.get("embedding", [])
        if not rec_emb:
            continue  # spring records uden embedding over

        score = compute_recall_score(
            record=rec,
            query_embedding=query_embedding,
            record_embedding=rec_emb,
            config=config,
        )
        if score >= min_score:
            scored.append({
                **rec,
                "_score": score,
                "_source": "cold",
            })

    scored.sort(key=lambda r: r["_score"], reverse=True)
    return scored[:max_results]
```

### Edge case-håndtering i funktionerne

- **Record uden embedding:** Springes stille over (kan ikke scores)
- **Query embedding = 0-vektor:** Embedding_sim = 0.0, resten af scoren bestemmer
- **Record uden created_at:** Recency = 0.5 (neutral)
- **Record uden importance:** Importance = 0.5 (default)
- **Alle records under threshold:** Returner tom liste
- **recall_count overflow:** Capped internt af `min(1.0, N / freq_cap)` — integer overflow kan ikke ske i Python

### Tests

```python
# tests/test_memory_quality_score.py

def test_compute_recall_score_perfect_match():
    """Ens identiske embeddings + ny record + høj importance = ~0.95-1.0"""
    ...

def test_compute_recall_score_zero_embedding():
    """0-vektor embedding giver embedding_sim=0 — resten af scoren bestemmer"""
    ...

def test_compute_recall_score_old_record():
    """Record fra 2 år siden → recency ~0.0 — kun freq+importance holder den i live"""
    ...

def test_compute_recall_score_threshold_filter():
    """Records under 0.35 ekskluderes fra resultater"""
    ...
```

---

## Step 2 — Opdater BrainEntry med recall_count

### I `core/services/jarvis_brain.py`

Tilføj felt på BrainEntry dataclass:

```python
@dataclass
class BrainEntry:
    # ... eksisterende felter ...
    recall_count: int = 0
```

**Schema-migration:** Ingen nødvendig — `recall_count` har default 0. SQLite kolonnen kan være nil (behandles som 0).

### I `core/tools/jarvis_brain_tools.py`

**Opdater `search_jarvis_brain`** — returner score i resultatet:

```python
async def search_jarvis_brain(
    query: str,
    limit: int = 5,
    min_score: float = 0.35,
) -> list[dict]:
    """Søg med quality scoring."""
    entries = await _search_brain_raw(query, limit=limit * 3)
    query_emb = await compute_embedding(query)
    
    scored = []
    for entry in entries:
        score = compute_recall_score(
            record=entry,
            query_embedding=query_emb,
            record_embedding=entry.get("embedding", []),
        )
        if score >= min_score:
            scored.append({**entry, "_score": score})
    
    scored.sort(key=lambda r: r["_score"], reverse=True)
    return scored[:limit]
```

**Opdater `read_brain_entry`** — inkrementér recall_count:

```python
async def read_brain_entry(entry_id: str) -> dict | None:
    """Læs en entry og inkrementér recall_count."""
    entry = await _get_entry_by_id(entry_id)
    if entry:
        await _increment_recall_count(entry_id)
    return entry
```

Tilføj hjælpefunktion:

```python
async def _increment_recall_count(entry_id: str) -> None:
    """Increment recall_count for en brain entry."""
    from core.db import db
    await db.execute(
        "UPDATE brain_entries SET recall_count = COALESCE(recall_count, 0) + 1 WHERE id = ?",
        (entry_id,),
    )
```

---

## Step 3 — Genaktivér cold tier i `core/services/memory_hierarchy.py`

### Find `recall_before_act` funktionen og opdater:

```python
async def recall_before_act(
    *,
    query: str = "",
    include_cold: bool = True,  # Ændret default fra False til True
    cold_max: int = 6,
    min_cold_score: float = 0.35,
) -> dict[str, Any]:
    """Compose hot+warm+(optional cold) tier snapshot before an action."""
    
    result = {
        "hot": _get_hot_tier(),
        "warm": await _get_warm_tier(),
        "cold": [],
    }
    
    if include_cold:
        cold = await cold_tier_recall(
            query=query,
            max_results=cold_max,
            min_score=min_cold_score,
        )
        result["cold"] = cold
    
    return result
```

**Source tagging:** Hver returneret record i `result["cold"]` har `_source: "cold"` — dette tillader downstream at prioritere hot > warm > cold.

---

## Step 4 — Tilføj runtime.json konfig

### I `~/.jarvis-v2/config/runtime.json`:

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

**Feature toggle:** Sæt `enabled: false` for at deaktivere cold tier uden kodeændring.

---

## Step 5 — Integration tests

```python
# tests/test_memory_hierarchy.py

async def test_recall_before_act_cold_tier_enabled():
    """recall_before_act returnerer cold tier når include_cold=True"""
    result = await recall_before_act(query="hvad sagde vi om hukommelse", include_cold=True)
    assert "cold" in result
    assert isinstance(result["cold"], list)
    

async def test_recall_before_act_cold_tier_disabled():
    """recall_before_act returnerer tom cold når include_cold=False"""
    result = await recall_before_act(query="test", include_cold=False)
    assert result["cold"] == []


async def test_cold_tier_quality_order():
    """Records sorteres efter score (højeste først)"""
    result = await cold_tier_recall(query="test", ...)
    if len(result) >= 2:
        assert result[0]["_score"] >= result[1]["_score"]


async def test_cold_tier_below_threshold():
    """Records under min_score returneres ikke"""
    result = await cold_tier_recall(query="meget obskurt emne", min_score=0.9)
    assert len(result) == 0
```

---

## Step 6 — Rollback procedure

Hvis noget går galt:

```bash
# Mulighed 1: Slå fra via runtime.json
sed -i 's/"enabled": true/"enabled": false/' ~/.jarvis-v2/config/runtime.json
systemctl restart jarvis-api

# Mulighed 2: Git revert
git revert HEAD --no-edit
systemctl restart jarvis-api
```

---

## Commit-strategi

Per din policy: **éen commit per fil** (traceable progress):

| Commit | Fil(er) | Besked |
|--------|---------|--------|
| 1 | `core/memory/unified_recall.py` | `memory-fix: tilføj compute_recall_score + cold_tier_recall` |
| 2 | `core/services/jarvis_brain.py` | `memory-fix: tilføj recall_count felt på BrainEntry` |
| 3 | `core/tools/jarvis_brain_tools.py` | `memory-fix: opdater search/read med scoring + recall_count` |
| 4 | `core/services/memory_hierarchy.py` | `memory-fix: genaktivér cold tier i recall_before_act` |
| 5 | `~/.jarvis-v2/config/runtime.json` | `memory-fix: tilføj cold_tier konfig` |

Tests: Commit 1-4 hver har deres tilhørende tests i commit-beskeden, men selve test-filerne committes i en separat commit.
