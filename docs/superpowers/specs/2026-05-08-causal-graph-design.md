# Causal Graph Layer — Design Spec

**Dato:** 2026-05-08
**Status:** Approved by Bjørn 2026-05-08
**Forfatter:** Brainstormet med Claude
**Motivation:** Jarvis AGI-rapport 2026-05-07, prioritet #1 (neuro-symbolic). Lukker hullet "causally grounded retrieval" som Pengfei Du-survey identificerede som ét af 10 åbne udfordringer for autonome LLM-agenter.

---

## 1. Mål

Etablere et causal graph-lag oven på den eksisterende `events`-tabel (389k rows) der gør Jarvis i stand til at besvare spørgsmål som:

- *"Hvorfor fejlede X?"* — backward-traversal til root cause
- *"Hvad førte X til?"* — forward-traversal til downstream effekter
- *"Hvis X ikke var sket, hvilke events ville være prunet?"* — counterfactuals beriget med ægte kausal-data

Subsystemet er **advisory** (suggestions, ikke binding gates) og **decoupled** (eksisterende events fortsætter uændret; ingen call-sites tvinges til migrering).

---

## 2. Storage

Ny tabel `causal_edges`:

```sql
CREATE TABLE causal_edges (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  child_event_id   INTEGER NOT NULL,
  parent_event_id  INTEGER NOT NULL,
  edge_kind        TEXT NOT NULL,    -- 'triggered'|'enabled'|'blocked'|'caused'
  confidence       REAL NOT NULL,    -- [0.0, 1.0]
  source           TEXT NOT NULL,    -- 'explicit'|'inferred-kind'|'inferred-id'|'inferred-temporal'
  created_at       TEXT NOT NULL,
  reasoning        TEXT NOT NULL DEFAULT '',
  UNIQUE(child_event_id, parent_event_id, edge_kind)
);
CREATE INDEX idx_ce_child ON causal_edges(child_event_id);
CREATE INDEX idx_ce_parent ON causal_edges(parent_event_id);
```

**Beslutninger:**
- Separat tabel (ikke kolonne på `events`) → flere causes pr. event mulige, idempotent inferens, ingen migration på 389k rows
- `UNIQUE(child, parent, edge_kind)` forhindrer duplikat-edges; inference UPDATER row hvis bedre evidens dukker op
- `confidence` + `source` giver query-API filtrering ("vis kun ≥0.7") og observability for inference-kvalitet
- `reasoning` er kort streng der forklarer hvorfor edge'en blev trukket (debugging)

---

## 3. Eksplicit edges — instrumentering

`event_bus.publish()` udvides:

```python
event_bus.publish(
    "tool.error",
    {"tool": "bash_run", "error": "..."},
    caused_by=parent_event_id,   # int eller list[int]
    edge_kind="triggered",        # default 'triggered' når caused_by er sat
)
```

Implementering:
- `publish()` skriver event som før, henter `lastrowid`
- Hvis `caused_by` sat → INSERT i `causal_edges` med `source='explicit'`, `confidence=1.0`
- `caused_by` accepterer int eller list (flere parents → multiple edges)
- Backwards compat: ingen kald uden `caused_by` påvirkes

**Initial instrumentering (curated kerne-set):**
- `tool_router` (tool-result → next-action)
- `decision_engine` (decision → review)
- `self_review_unified` (review → conclusion)
- `counterfactual_engine` (trigger → counterfactual)
- `contradiction_engine` (decision + review → contradiction)
- `agentic_round` i `visible_runs` (round-N → round-N+1)

Resten kommer organisk når kode rører de paths.

---

## 4. Inferens-daemon

`core/services/causal_inference_daemon.py`. Tick hver 15 min, scanner kun events fra inference-allowlist.

### 4.1 Allowlist (v1)

```
tool.completed, tool.error, tool.invoked, tool.force_invoked,
decision.created, decision.deduped, decision.revoked,
behavioral_decision_review.kept|partial|broken,
self_review.completed, conflict.detected, conflict.resolved,
counterfactual.detected, counterfactual.regret,
emergence.pattern_candidate_*, contradiction.detected,
runtime.executive_action_outcome_recorded, runtime.cheap_lane_provider_failed,
channel.message_inbound, memory.seed_triggered, memory.seed_fulfilled,
identity.drift_detected, heartbeat.conflict_resolved
```

### 4.2 Three-tier matching (per child event, stop ved første match)

| Tier | Strategy | Confidence | Source-tag |
|---|---|---|---|
| 1 | **Kind-rule** — hardcoded ~30 par (`tool.invoked → tool.completed/error`, `decision.created → behavioral_decision_review.*`), kræver shared_id eller ≤30s | 0.9 | `inferred-kind` |
| 2 | **Shared-ID** — match på `tool_call_id` / `run_id` / `decision_id` / `session_id` i payload, ≤60s | 0.8 | `inferred-id` |
| 3 | **Temporal-only fallback** — samme `session_id` ≤30s, ingen anden match | 0.4 | `inferred-temporal` |

### 4.3 Drift, idempotens, cap

- UNIQUE-constraint på (child, parent, edge_kind) forhindrer dubletter
- Hvis daemon finder bedre evidens (fx tier-1 efter en tier-3 først blev skrevet), UPDATER eksisterende row til højere confidence + ny source
- Cap: max 500 nye edges/tick
- Backfill: første kørsel scanner sidste 7 dage retroaktivt, chunks á 1000 events, sleep 100ms mellem chunks

---

## 5. Query API

`core/services/causal_graph.py`:

```python
def query_causal_chain(
    *, event_id: int,
    direction: str = "backward",  # 'backward'|'forward'
    max_depth: int = 5,
    min_confidence: float = 0.5,
) -> dict:
    """
    Returns:
      {
        "root_event": {id, kind, payload, created_at},
        "chain": [
          {"depth": 1, "event": {...}, "edge": {kind, confidence, source}},
          {"depth": 2, "event": {...}, "edge": {...}},
          ...
        ],
        "truncated": bool,        # True hvis hit max_depth uden at nå root
        "total_nodes": int,
      }
    """

def query_causal_neighbors(
    *, event_id: int,
    direction: str = "both",
    min_confidence: float = 0.5,
) -> dict:
    """Direkte naboer (depth=1) — hurtigere for explore-style."""
```

**Detaljer:**
- BFS-traversal med `visited`-set så cycles afsluttes pænt
- `min_confidence` filtrerer lav-konfidens inference-edges hvis caller ønsker skarp graf
- Cap: total nodes ved 100 (returnerer `truncated=True` hvis ramt)
- "backward" = parent-edges op (hvad caused dette?)
- "forward" = child-edges ned (hvad caused dette så?)

**Convenience helpers:**
- `get_root_causes(event_id)` — backward indtil events uden parents, returnér alle
- `get_immediate_cause(event_id)` — depth=1, top-confidence

---

## 6. Counterfactuals two-way integration

### 6.1 Forward-konsumption (counterfactuals → causal graph)

`counterfactual_engine.run()` udvides: når den genererer "hvad hvis trigger-event T ikke var sket?", kalder den `query_causal_chain(event_id=T.id, direction="forward", max_depth=3)`. Resultatet bruges til at:

- Identificere downstream-events der ville være prunet i hypotesen
- Berige `counterfactual.what_if` med konkret kausalkæde fra real data: *"hvis T ikke var sket, ville A, B og C heller ikke være sket"*
- Erstatte Phase 1's tomme placeholder-kausalitet med ægte graf-data

### 6.2 Backward-publication (causal graph ← counterfactual events)

Når `counterfactual_engine` emitterer `counterfactual.detected` event, sker det med eksplicit `caused_by=trigger_event_id`. Edge får `edge_kind="caused"`, `source="explicit"`. Det gør counterfactuals selv query'bare i grafen — *"hvilke counterfactuals stammer fra `tool.error`-mønstre?"*.

### 6.3 V1-begrænsning

Counterfactuals kan kun query graf på events der ER blevet edge-tracket. Backfill fanger sidste 7 dage; ældre counterfactual-triggers får tom forward-traversal og falder pænt tilbage til Phase 1-stil placeholder.

---

## 7. Tool-surface + prompt-injection

### 7.1 Tool: `query_why`

```python
@tool("query_why")
def query_why(
    event_id: int | None = None,
    event_kind: str | None = None,  # alternativ: seneste event af kind
    max_depth: int = 5,
    min_confidence: float = 0.5,
) -> dict:
    """Returnér kausal-kæde. Hvis event_id mangler, bruger seneste event af event_kind."""
```

Format: kæde fra `query_causal_chain()` + human-readable summary pr. trin.

### 7.2 Prompt-injection: `prompt_sections/causal_alerts.py`

Awareness-sektion (priority 30) scanner sidste 30 min for kritiske failure-events:
- `tool.error` med severity≥medium
- `behavioral_decision_review.broken`
- `runtime.cheap_lane_provider_failed`
- `identity.drift_detected`
- `executive_contradiction.detected`

For hver: `query_causal_chain(depth=3, min_confidence=0.7)`, formatterer top-1 chain som:

```
🔗 Kausalkæde — recent failure:
  ROOT: channel.message_inbound (08:14:23) "Bjørn: prøv noget med GridBot"
    ↳ tool.invoked: bash_run (08:14:25)
    ↳ tool.error: ImportError (08:14:27) ← kæden stoppede her
```

Cap: max 2 chains pr. tur. Returner "" hvis ingen kritiske failures.

---

## 8. Error handling

| Fejl | Strategi |
|---|---|
| Inferens-daemon crasher mid-tick | `logger.warning` + skip cycle. Næste tick tager backlog op. |
| Cyklisk graf (A→B→A) | BFS `visited`-set; cycle log warning + truncér |
| Event-payload missing forventet field | Tier 2 (shared-id) skipper, falder til tier 3 (temporal) |
| 389k events: backfill OOM | Chunker á 1000 events, sleep 100ms, cap 7 dage retroaktivt |
| `query_causal_chain` på event uden edges | Returnér tomt svar `{root_event, chain: [], total_nodes: 1}`, ingen exception |
| Counterfactuals query'er graf der mangler edges | Falder tilbage til Phase 1 placeholder uden fejl |

---

## 9. Tests (`tests/test_causal_graph.py`)

1. Schema migration idempotent på fresh + eksisterende DB
2. Eksplicit edge insert via `event_bus.publish(..., caused_by=X)` skriver row med source='explicit', confidence=1.0
3. Inference tier-1 (kind-rule): `tool.invoked` + `tool.completed` shared tool_call_id → 0.9, `inferred-kind`
4. Inference tier-2 (shared-id): events med shared run_id uden kind-rule match → 0.8, `inferred-id`
5. Inference tier-3 (temporal): events samme session_id ≤30s, intet andet match → 0.4
6. Idempotens: daemon kørt 2x producerer ikke duplikat-edges (UNIQUE)
7. Confidence upgrade: tier-3 edge først, tier-1 finder samme par senere → row UPDATE til 0.9
8. Backward chain: `query_causal_chain(direction='backward')` traverser parent-edges korrekt
9. Cycle handling: A→B→A graf afsluttes pænt med `truncated=True`
10. Counterfactual integration: Phase 1-style trigger producerer counterfactual med beriget what_if-data fra causal graph forward-query

---

## 10. Faseplan

**Phase 1 (denne spec):** Storage + eksplicit edges + inferens-daemon + query API + counterfactuals two-way + tool + awareness-injection.

**Phase 2 (senere, ikke i scope):** Forward-graph LLM-summary i prompt ("dette mønster er gentaget 5x i sidste uge → her er de typiske kausal-stier"). Kræver counterfactuals Phase 2.

**Phase 3 (senere):** Cross-session causal patterns — ægte "temporal substrate" per Shapira et al.
