---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Tool Router — Per-Turn Tool Selection

**Date:** 2026-05-06
**Status:** Approved (Bjørn) — ready for implementation plan
**Owner:** Claude Code

## Problem

The visible-chat lane currently sends **all 293 tool definitions** to the
provider on every turn. Measured payload (provider=ollama, model=glm-5.1:cloud,
empty session):

| Source | Tokens | % |
|---|---|---|
| System prompt | 6,201 | 14.2% |
| Transcript history | 0 | 0.0% |
| **Tool definitions** | **37,593** | **85.8%** |
| User message | 8 | 0.0% |
| **Total** | **43,802** | 100% |

Tool definitions dominate the prompt by a factor of ~6× over the system
prompt. They are the actual cause of high token cost, latency, and the
"27K input tokens" observation Jarvis reported in conversation. This is
the largest single optimization target in the system.

## Goal

Build a **ToolRouter** that selects a relevant subset (target ~60-100 tools)
of the catalog per turn while preserving capability coverage through:

1. A static **always-core** set of frequently-used tools
2. **Embedding-based dynamic selection** of additional context-relevant tools
3. A **`load_more_tools`** safety hatch when the router misses something
4. **Fallback to full list** when the router is uncertain

Constraints:

- Must not silently disable Jarvis from reaching tools he needs
- Must be reversible (killswitch) without restart
- Must produce rich observability data so we can calibrate adaptively
- Must not affect heartbeat lane or background daemons
- Must add < 200ms to a visible turn

## Non-goals

- Compressing individual tool definition schemas (separate work)
- Removing or deprecating tools (separate audit)
- Refactoring the static text in prompt_contract.py (separate work, ~500 tok savings, deferred)

## Decisions (from brainstorming Q&A)

| # | Decision | Choice |
|---|---|---|
| 1 | Failure mode when selection misses | `load_more_tools` escape hatch + fallback to full when uncertain |
| 2 | Aggressiveness | Adaptive — start conservative, tighten threshold based on `load_more` rate |
| 3 | Selection mechanism | Hybrid: tags (always-core) + embedding (dynamic) |
| 4 | Always-core size | Broad safety net (~60-80 tools, derived from 7-day usage) |
| 5 | Lanes affected | Visible + autonomous only; heartbeat & daemons untouched |
| 6 | Tag source | Hybrid: LLM-generated baseline + manual overrides |
| 7 | Observability | Rich (events + DB tables + MC widget) |
| 8 | `load_more_tools` invocation | Hybrid: by-name primarily, by NL-query as backup; always-on tool catalog (~6K tok) lets Jarvis see what exists |
| 9 | Implementation order | Big-bang — `load_more_tools` + fallback are sufficient safety nets |

## Architecture

A new `ToolRouter` layer sits between `_build_visible_input` and the
provider call. It returns a `ToolSelection` indicating which tool
definitions to send for the current turn.

```
visible_runs.py
  user_message
      │
      ▼
  _build_visible_input         (unchanged; system prompt now includes [TOOL_CATALOG])
      │
      ▼
  ToolRouter.select_tools(user_message, session_id, lane)
      ├── always_core ← top_used_from_db(limit=70) ∪ pinned_set
      ├── embedding_picks ← top_k(cosine(embed(user_message), tool_embeddings))
      ├── confidence ← score(msg_clarity, top_similarity, recent_load_more_rate)
      ├── if confidence < threshold: fallback to full 293
      └── return ToolSelection(selected_names, ...)
      │
      ▼
  stream_visible_followup(tools = [defs for selected_names])
```

### New data structures

| Path | Purpose |
|---|---|
| `state/tool_tags.json` | Auto-generated tags per tool (LLM bootstrap output) |
| `state/tool_tags.overrides.json` | Manual tag overrides; takes precedence |
| `state/tool_tags.pinned.json` | Tools pinned to always-core regardless of usage |
| `state/tool_embeddings.sqlite` | `tool_embeddings(name, embedding BLOB, computed_at)` |
| `events` table | New family `tool_router.*` events |
| `tool_router_decisions` table | Per-turn decision log |
| `tool_router_load_more` table | `load_more_tools` invocation log |

### New services

| File | Responsibility |
|---|---|
| `core/services/tool_router.py` | The selector itself — `select_tools()`, confidence scoring, fallback logic |
| `core/services/tool_tagger.py` | One-shot LLM tag bootstrap; `get_tags(name)` with override layers |
| `core/services/tool_catalog.py` | Compact name + 1-line catalog string for system prompt |
| `core/services/tool_router_runtime.py` | Nightly daemon: recompute always-core ranking, adjust threshold, refresh embeddings |

### New tool

`load_more_tools(names: list[str] | None, query: str | None)` — implemented
as a "magic" tool whose execution mutates the next round's
`tool_definitions` in the agentic loop.

### Wiring

- `visible_runs.py`: invoke `select_tools` between `_build_visible_input`
  and `stream_visible_followup`. Pass `selection.selected_names` resolved to
  full tool definitions instead of the unfiltered `_get_tool_defs()`.
- `prompt_contract.py`: add a `[TOOL_CATALOG]` section that always renders
  the compact catalog (~6K tok). Inserted after operational sections.
- `app.py`: register new MC route `tool_router_router`.
- `runtime.py`: start `tool_router_runtime` daemon during lifespan startup
  (when `runtime_services_enabled`).
- `events.py`: add `tool_router` to `ALLOWED_EVENT_FAMILIES`.
- `runtime/db.py`: add migrations for the two new tables.
- `runtime/settings.py`: add `tool_router_enabled: bool = True` (killswitch),
  `tool_router_threshold: float = 0.55`, `tool_router_always_core_size: int = 70`,
  `tool_router_k_embeddings: int = 30`.

## Components

### `tool_catalog.py` — always-on tool overview

Produces a compact textual list of all 293 tools as a `[TOOL_CATALOG]`
section in the system prompt. Format:

```
TOOL CATALOG (use load_more_tools to fetch full schema):
- read_file: read file contents from a path
- grep: regex search across files
- bash: run shell command (sandboxed)
- pollinations_image: generate image from prompt
... (293 entries)
```

Cost: ~6K tokens, static unless tools change. Computed at startup,
invalidated when `get_tool_definitions()` output hash changes.

### `tool_tagger.py` — taxonomy maintenance

Two functions:

- `bootstrap_tags()` — runs once. Calls a cheap-lane LLM with the entire
  tool catalog and asks it to suggest 1-3 domain tags per tool from a fixed
  set: `memory, code, system, web, social, audio, video, image, identity,
  scheduling, hardware, dev, planning, search`. Writes
  `state/tool_tags.json`. Re-run when new tools are added.
- `get_tags(tool_name) -> list[str]` — reads from `tool_tags.json` with
  `tool_tags.overrides.json` taking precedence and `tool_tags.pinned.json`
  also surfaced for the always-core ranking.

Not regenerated per turn. Static until tools change or a manual override
is committed.

### `tool_router.py` — the core selector

Per call: `select_tools(user_message, session_id, lane) -> ToolSelection`.

```python
@dataclass
class ToolSelection:
    selected_names: list[str]      # tools to send with full schema
    always_core: list[str]         # of selected, which were always-core
    embedding_picks: list[str]     # of selected, which came from embedding
    confidence: float              # 0.0..1.0
    fallback_used: bool            # True if confidence too low → full list
    reason: str                    # human-readable explanation
    elapsed_ms: int
```

Algorithm:

1. **Always-core** — top 60-80 tools by 7-day call count from
   `tool_call_log` ∪ pinned set from `tool_tags.pinned.json`. Cached
   in-memory, refreshed nightly.
2. **Embedding-match** — embed user_message, find top-K cosine similarity
   to `tool_embeddings`. Filter out tools already in always-core.
3. **Confidence score** — see formula below.
4. **Threshold gate** — if `confidence < threshold`: return all 293 with
   `fallback_used=True`.
5. **Otherwise:** return always-core ∪ embedding-picks (capped at 100 total).

Confidence formula (v1):

```python
def score(user_message: str, top_sim: float, load_more_rate_7d: float) -> float:
    msg_clarity = clarity_signal(user_message)               # 0..1
    similarity_strength = min(top_sim / 0.7, 1.0)            # 0..1
    adaptive_floor = max(0.3, 0.6 - load_more_rate_7d * 2.0)
    return (msg_clarity * 0.4 + similarity_strength * 0.6) * adaptive_floor
```

`clarity_signal` rewards: ≥3 words, not pure affirmation ("ja"/"ok"),
contains question word or verb, not only emoji.

### `tool_router_runtime.py` — nightly daemon

- Reads `tool_call_log` for last 7 days, recomputes always-core ranking
- Recomputes embeddings if any tool's hash changed
- Adjusts adaptive threshold based on `load_more_rate_7d`:
  - `> 0.15` → threshold += 0.05
  - `< 0.05` → threshold -= 0.03
  - bounds: `[0.30, 0.85]`
- Promotes top-missed tools (frequent in `load_more_tools` calls) into
  always-core ranking with a usage-count boost
- Publishes `tool_router.daemon_run` event with summary

### `load_more_tools` tool

```python
def load_more_tools(
    names: list[str] | None = None,
    query: str | None = None,
) -> dict:
    """Fetch full tool schemas Jarvis didn't get this turn.

    Either provide explicit names, or a natural-language query and we'll
    embedding-match for you. Returned tools are added to the agentic
    loop's tool_definitions for the *next* round.
    """
```

Implemented as a "magic" tool — its execution mutates the agentic loop's
per-round extra-tools list. Returns a receipt dict listing which tools
were added. Always present in the selection (always-core).

### MC widget

Lives on Cheap Balancer tab (alongside other infrastructure widgets) or
gets a new tab if space is tight.

- 4 MetricCards: `Save-rate (avg tokens)`, `Selection-rate %`,
  `load_more rate %`, `Fallback rate %`
- Confidence histogram (10 buckets)
- Top-missed tools list
- ScrollPanel: 20 newest decisions

Endpoint: `/mc/tool-router-state` returning the JSON shape documented
in section 5 of the brainstorm.

## Data flow per turn

1. User sends message → `start_visible_run`
2. `_build_visible_input` builds system prompt (now with `[TOOL_CATALOG]`)
3. `tool_router.select_tools(user_message, session_id, "visible")`
   - Compute always-core, embedding picks, confidence
   - Publish `tool_router.decision` event
   - Insert `tool_router_decisions` row
   - Return `ToolSelection`
4. `tool_definitions = [get_definition(n) for n in selection.selected_names]`
5. `stream_visible_followup(base_messages, tool_definitions)`
6. If Jarvis calls `load_more_tools`:
   - Tool execution mutates `_round_extra_tools`
   - Publish `tool_router.load_more_fired` event
   - Insert `tool_router_load_more` row
   - Next round's tool_definitions includes the additions
7. After turn completes: `tool_call_log` updated; nightly daemon picks up
   the data on next run

## Error handling & fallback

| Failure | Detection | Response |
|---|---|---|
| `tool_tags.json` missing/corrupt | Read fails | Log warning, use auto-derived from description |
| `tool_embeddings.sqlite` missing/corrupt | Query fails | Compute on-the-fly this turn, schedule rebuild |
| Embedding model unavailable | Provider error | Fallback: always-core + tag-based keyword match |
| `select_tools()` raises | Try/except wrapper | Return `ToolSelection(fallback_used=True, reason="router-error: <type>")` |
| Always-core empty (fresh install) | Empty result | Use hardcoded bootstrap set of 25 essentials until daemon populates |
| `load_more_tools` unknown name | Validation | Return error to Jarvis: "tool 'X' not found. Available: ..." |
| `load_more_tools` empty matches | Empty result | Return 5 nearest with note "no strong matches, here are closest" |
| Nightly daemon fails | Exception logging | Always-core list freezes until next successful run |

### Hard guarantees

1. **Selection is never blocking** — `select_tools()` has `timeout=200ms`.
   Exceeded → automatic fallback.
2. **Fallback is always functional** — `get_tool_definitions()` (the
   current full 293-list) is the source of truth. If anything is wrong,
   send the full list.
3. **No permanent state mutation before success** — embedding rebuild
   writes to `.tmp` and atomic-renames only on completion.
4. **`load_more_tools` is always callable** — it's in always-core and
   included in fallback list.

### Observability when failures fire

Each fallback reason is published as `tool_router.fallback_fired` event
with a `reason` field. The MC widget shows fallback-rate over time —
sudden spikes indicate something broke underneath.

## Observability (rich)

### Events

New family `tool_router` (added to `ALLOWED_EVENT_FAMILIES`):

```
tool_router.decision         — one per visible/autonomous turn
tool_router.load_more_fired  — when Jarvis calls load_more_tools
tool_router.fallback_fired   — when selection bails to full list
tool_router.daemon_run       — nightly recompute statistics
```

`tool_router.decision` payload example:

```json
{
  "run_id": "...", "session_id": "...", "lane": "visible",
  "user_message_preview": "hvor mange tokens bruger vi nu?",
  "selected_count": 73, "fallback_used": false,
  "always_core_count": 65, "embedding_picks_count": 8,
  "confidence": 0.74, "threshold": 0.55,
  "elapsed_ms": 24,
  "would_have_sent_full": 293,
  "tokens_saved_estimate": 28140
}
```

### DB tables

```sql
CREATE TABLE tool_router_decisions (
  id INTEGER PRIMARY KEY,
  run_id TEXT, session_id TEXT, lane TEXT,
  user_message_preview TEXT,
  selected_names_json TEXT,
  always_core_names_json TEXT,
  embedding_picks_json TEXT,
  confidence REAL, threshold REAL,
  fallback_used INTEGER, fallback_reason TEXT,
  elapsed_ms INTEGER,
  tokens_saved_estimate INTEGER,
  created_at TEXT
);
CREATE INDEX idx_tool_router_decisions_created_at
  ON tool_router_decisions(created_at);

CREATE TABLE tool_router_load_more (
  id INTEGER PRIMARY KEY,
  run_id TEXT, decision_id INTEGER,
  requested_names_json TEXT, requested_query TEXT,
  resolved_names_json TEXT,
  round_index INTEGER,
  created_at TEXT
);
CREATE INDEX idx_tool_router_load_more_created_at
  ON tool_router_load_more(created_at);
```

### MC endpoint shape

`GET /mc/tool-router-state` returns:

```json
{
  "enabled": true,
  "config": {"threshold": 0.55, "always_core_size": 70, "k_embeddings": 30},
  "totals": {
    "decisions_today": 142, "decisions_7d": 1023,
    "fallback_rate_7d": 0.08, "load_more_rate_7d": 0.04,
    "avg_tokens_saved_7d": 27200, "avg_elapsed_ms": 18
  },
  "top_missed_tools_7d": [
    {"name": "pollinations_image", "count": 12},
    {"name": "discord_channel", "count": 7}
  ],
  "confidence_histogram": [...10 buckets...],
  "recent_decisions": [...20 newest...]
}
```

### Adaptive feedback loop

The nightly daemon reads observability data and adjusts:

- **`always_core` ranking**: tools sorted by call count over last 7 days.
  Top 70 plus pinned set form the always-core list.
- **Threshold adjustment**: hysteresis as documented above.
- **Top-missed promotion**: tools frequently appearing in
  `load_more_tools(names=...)` get a boost in always-core ranking — they
  are evidently more important than their raw call count suggests.

Daemon-run results are written as `tool_router.daemon_run` events so we
can trace parameter shifts over time.

## Testing

### Unit tests (`tests/services/test_tool_router.py`)

- `select_tools` returns always-core on empty user_message
- Confidence function is monotonic in `top_sim`
- Embedding cache hits/misses behave correctly
- `load_more_tools` with unknown name returns error
- `load_more_tools` with query hits the embedding router
- Timeout (>200ms) → fallback
- Corrupt `tool_tags.json` → continues with auto-derived

### Integration tests (`tests/integration/test_tool_router_runtime.py`)

- Full turn through `_build_visible_input` → `select_tools` →
  `stream_visible_followup` with mocked provider
- Verify `tool_router.decision` event publishes with correct payload
- Verify `tool_router_decisions` row writes
- Verify `load_more_tools` mutates next-round tool_definitions

### Daemon tests (`tests/services/test_tool_router_runtime.py`)

- Bootstrap-tagger generates 1-3 tags per tool
- Always-core ranking sorts correctly from mock call-log
- Adaptive threshold-adjustment hits bounds correctly
- Embedding rebuild atomic-renames correctly

### Smoke test

Add to existing `scripts/smoke_test_startup.py`:

- Verify `tool_router.py` initializes with no tools (graceful)
- Verify `/mc/tool-router-state` endpoint returns 200

### Manual validation set

20 sample user messages covering:

- Short greetings ("hej") → most aggressive selection
- Memory questions ("hvad sagde vi i går?") → memory tools in selection
- Code work ("læs visible_runs.py") → code tools
- Ambiguous ("hmm") → fallback to full
- Multi-domain ("vis mig din tilstand og lav et billede") → broad selection
- Empty/junk → fallback

Run before deploy, save outputs as regression baseline.

## Rollout

### Pre-deploy

1. Bootstrap tags via cheap-lane LLM, manual review of top 50 most-used tools
2. Compute embeddings, verify cache is correct
3. Run manual validation set, compare against baseline

### Deploy (big-bang)

1. Merge to main, restart `jarvis-runtime` and `jarvis-api`
2. Initial threshold: `0.55` (conservative — fallback if uncertain)
3. Watch `/mc/tool-router-state` first hour — fallback rate should land
   between 10-30%
4. Watch `load_more_tools` rate first day — should be < 10%

### Killswitch

Settings flag `tool_router_enabled: bool = True`. If set to `False`,
`select_tools` always returns `ToolSelection(fallback_used=True,
selected=all_tools())`. Flippable from MC or directly in `runtime.json`
without restart (settings reload every 30s).

### First-week observation

Daily checks:

- Save-rate avg (target: 20-30K/turn)
- Fallback rate (target: < 25%)
- Top-missed tools (should *fall* over time as always-core self-adjusts)
- Jarvis adherence rate (must not drop materially — if it falls, kill
  switch and analyze)

## Open questions

1. **Which embedding model?** Recommendation: local Ollama
   (`nomic-embed-text` or `mxbai-embed-large`). Rationale: no network
   call, stable, cheap. Verify deployment on Ollama host before
   implementation.
2. **Confidence threshold tuning ranges in production?** v1 starts at
   `0.55` with ±0.03/0.05 nightly adjustments, bounds `[0.30, 0.85]`.
   Numbers may be retuned after first week's data.
3. **Tools used <1×/week but critical?** `tool_tags.pinned.json` lets
   you explicitly pin tools to always-core regardless of usage. Built as
   part of the manual-override layer.

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Selection misses a critical tool, Jarvis fails silently | `load_more_tools` is in always-core; tool catalog is always visible |
| Embedding model latency adds to turn time | 200ms timeout; cached embeddings; can swap to keyword-only fallback |
| Adaptive threshold oscillates | Hysteresis + bounds; nightly cadence (not per-turn) |
| Tool tags become stale as tools evolve | `bootstrap_tags()` rerun on tool-set changes; manual overrides persist |
| First-day chaos with selection | Killswitch + conservative initial threshold + first-hour monitoring |
| Token savings smaller than estimated | Measurement script (`scripts/measure_prompt_payload.py`) gives ground truth before/after |

## Success criteria

- Average tokens-per-turn drops from ~43K to ≤ 20K (target: ~50% reduction)
- `load_more_tools` rate stays < 10% over 14 days
- Fallback rate stays < 25% over 14 days
- Jarvis adherence rate does not decrease materially vs. 14-day baseline
- No silent capability loss — every `load_more_tools` call resolves
  successfully or returns an explanatory error
- Router latency p95 < 100ms; never blocks a turn

## Out of scope (deferred)

- Compressing individual tool definition schemas (separate effort)
- Auditing and removing unused tools (separate audit)
- Refactoring `prompt_contract.py` static text into signals
  (~500 tok savings, deferred until tool router proves the bigger win)
- Per-tool descriptions optimization (downstream of compression work)
