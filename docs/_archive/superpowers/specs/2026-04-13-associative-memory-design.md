# Associative Memory Design

## Overview

Dormant associative memory for Jarvis — memories triggered by semantic content, emotional state, and repetition patterns rather than always loaded into context. Mirrors how human episodic memory works: mostly dormant, surfaced by contextual resonance.

## Architecture

Two units with clear responsibilities:

### `apps/api/jarvis_api/services/experiential_memory.py` (extended)

Adds two methods to the existing service:

- `score_memories_by_relevance(candidates, context_text, emotional_state)` — sends up to 20 candidate memories to the local/cheap LLM lane with a relevance-scoring prompt. Returns `{memory_id: float}` dict with scores 0.0–1.0. Falls back to empty dict if LLM is unavailable.
- `reinforce_memory(memory_id)` — increments `reinforcement_count` and resets `decay_score` toward 1.0 for a memory that has been re-surfaced, slowing its future decay.

Existing `get_relevant_experiential_memories()` is preserved and used as the candidate-pool query (recency × importance ordering).

### `apps/api/jarvis_api/services/associative_recall.py` (new, ~200 lines)

Coordinator that decides when and what to surface.

Public API:
- `recall_for_session(session_context: dict) -> list[dict]` — called once at session start, returns up to 3 memories
- `recall_for_message(message_text: str, emotional_state: dict) -> list[dict]` — called per user message, returns up to 2 memories
- `build_recall_prompt_section() -> str` — formats currently active memories for system-prompt injection
- `apply_weak_recall_to_emotions(memories: list[dict]) -> None` — triggers appropriate emotion concepts from weak-scoring memories
- `clear_session_recall() -> None` — resets active memory state at session end

Internal state: in-memory dict `_active_memories: dict[str, dict]` keyed by `memory_id`, max 5 entries.

## Data Flow

### Session-Start Recall

1. Query DB: top-20 memories ordered by `importance * decay_score DESC`
2. Build context string from session metadata: channel, time-of-day, current bearing
3. LLM call (local/cheap lane, 15s timeout): score each candidate 0.0–1.0 for relevance to context
4. Score ≥ 0.7 → add to `_active_memories` (max 3 at session start)
5. Score 0.3–0.7 → `apply_weak_recall_to_emotions()` → trigger matching emotion concept at proportional intensity
6. Fallback if LLM unavailable: top-3 by `importance * decay_score` without scoring

### Per-Message Recall

1. Build signal string: message text + active emotion concepts + `current_bearing`
2. Candidate pool: top-10 from DB *excluding* already-active session memories
3. Apply repetition multiplier: if same `topic` appears in ≥ 3 consecutive messages, multiply LLM scores for that topic by ×1.5 (post-LLM, capped at 1.0)
4. LLM call with signal string (15s timeout)
5. Score ≥ 0.7 → add to `_active_memories` (max 2 added per message, max 5 total in session); if already at cap, new memory replaces weakest active
6. Score 0.3–0.7 → `apply_weak_recall_to_emotions()`
7. If an already-active memory matches again → call `reinforce_memory(memory_id)`

### Prompt Injection

`build_recall_prompt_section()` is called from `cognitive_state_assembly.py` and returns a formatted block:

```
Associative memories (triggered by current context):
- [narrative snippet, max 80 chars] (topic: deployment, strength: 0.82)
- [narrative snippet, max 80 chars] (topic: debugging, strength: 0.71)
```

Injected only when `_active_memories` is non-empty.

## Trigger Signals

Three signals combine to build the LLM scoring prompt:

1. **Semantic content** — message text or session context description
2. **Emotional state** — current emotion concepts (name + intensity) and emotional baseline axes
3. **Repetition pattern** — topic frequency counter across recent messages (maintained in `associative_recall.py`)

All three are included in the LLM prompt. The LLM is instructed to weight them holistically.

## Scoring Thresholds

| Score | Action |
|-------|--------|
| ≥ 0.7 | Inject as text in system prompt |
| 0.3–0.69 | Trigger emotion concept at proportional intensity, no text injection |
| < 0.3 | Ignored |

## Edge Cases and Error Handling

- **LLM unavailable:** Recency-based top-3 fallback, no exception propagated. Recall is never blocking.
- **No memories in DB:** `recall_for_session()` returns empty list silently. No LLM call made.
- **Cap enforcement:** Max 5 active memories in session. New high-scoring memory displaces weakest active.
- **Repetition detection:** Topic frequency counter resets every 10 messages to prevent stale amplification.
- **15s LLM timeout:** If exceeded, recency fallback is used for that call.
- **Session end:** `clear_session_recall()` clears `_active_memories`. No cross-session persistence of active state.
- **Stale memories:** `decay_score` is maintained by existing experiential memory system. Low decay_score memories appear lower in candidate pool naturally.

## Integration Points

- **`cognitive_state_assembly.py`** — calls `build_recall_prompt_section()` and includes output in assembled prompt
- **`app.py`** — calls `clear_session_recall()` on session end (or not needed if per-request state)
- **`experiential_memory.py`** — extended with `score_memories_by_relevance()` and `reinforce_memory()`
- **`emotion_concepts.py`** — `apply_weak_recall_to_emotions()` calls `trigger_emotion_concept()`

## Out of Scope

- Vector/embedding search (no infrastructure, LLM scoring used instead)
- Cross-session active memory persistence
- Writing new memories (handled by existing experiential memory pipeline)
- Forgetting/eviction from DB (handled by existing decay system)
