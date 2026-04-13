# LLM Prompt Caching Design

## Goal

Reduce LLM calls between Jarvis and providers (Ollama, Groq) without losing any output quality. Three layered caching mechanisms that work together.

## Architecture

Three independent layers, each reducing waste at a different level:

- **Layer A — Daemon response cache:** Hash-based LLM response caching in `daemon_llm_call()`. Identical prompts within TTL window return cached responses without calling the LLM.
- **Layer B — Tick-scoped signal & identity cache:** Per-heartbeat-tick in-memory cache for `build_identity_preamble()` and signal surface reads. Eliminates ~40+ redundant DB reads per tick.
- **Layer C — Ollama KV-cache-friendly call ordering:** Reorder daemon execution in heartbeat_runtime so daemons with similar prompt prefixes run consecutively, maximizing Ollama's internal KV cache reuse.

```
Heartbeat tick starts
  -> start_tick()                    [Layer B: tick cache activated]
  -> Daemon group 1 runs             [Layer C: sorted for Ollama KV]
    -> daemon_llm_call() checks cache [Layer A]
      -> Cache hit: return cached, no LLM call
      -> Cache miss: call LLM, store in cache
  -> Daemon group 2 runs...
  -> end_tick()                      [Layer B: tick cache cleared]
```

## Layer A: Daemon Response Cache

### Location

Extend `daemon_llm_call()` in `apps/api/jarvis_api/services/daemon_llm.py`. No new file needed.

### Cache structure

Module-level dict:

```python
_response_cache: dict[str, tuple[str, float]] = {}
# key: SHA256(prompt), value: (response_text, expires_at_timestamp)
```

### TTL per daemon type

Determined by `daemon_name` parameter already passed to `daemon_llm_call()`:

| Category | Daemons | TTL |
|----------|---------|-----|
| Fast (2-3 min cadence) | somatic, thought_stream | 90s |
| Medium (5-10 min cadence) | curiosity, conflict, reflection_cycle, user_model | 180s |
| Slow (30min+ cadence) | meta_reflection, irony, aesthetic_taste, development_narrative, existential_wonder, code_aesthetic | 600s |
| No cache | session_summary (one-shot) | 0 |

Default TTL for unknown daemon names: 120s.

### Cache rules

- Only cache successful (non-empty) LLM responses. Never cache fallback strings.
- Cache key is SHA256 of the full prompt text. Changed context = different hash = automatic cache miss.
- In-memory only. Lost on server restart (acceptable — daemons regenerate on next tick).
- No max-size limit needed — ~20 entries max at any time, each under 500 bytes.

### Integration point

Inside `daemon_llm_call()`, before attempting cheap lane:

```python
def daemon_llm_call(prompt, *, max_len=200, fallback="", daemon_name=""):
    cache_key = hashlib.sha256(prompt.encode()).hexdigest()
    cached = _check_cache(cache_key)
    if cached is not None:
        # Log cache hit for observability
        return cached

    # ... existing cheap lane + heartbeat model logic ...

    if text:  # only cache successful responses
        _store_cache(cache_key, final, daemon_name)

    return final
```

## Layer B: Tick-Scoped Signal & Identity Cache

### Location

New file: `apps/api/jarvis_api/services/tick_cache.py`

### API

```python
def start_tick() -> None:
    """Call at beginning of heartbeat tick. Resets cache."""

def end_tick() -> None:
    """Call at end of heartbeat tick. Clears cache."""

def get(key: str) -> object | None:
    """Return cached value or None."""

def set(key: str, value: object) -> None:
    """Store value for this tick."""
```

Module-level `_cache: dict[str, object] | None = None`. When `_cache is None`, caching is inactive (safe fallthrough for non-heartbeat callers).

### Integration points

1. **heartbeat_runtime.py** — call `start_tick()` at beginning of `_execute_heartbeat_tick()`, `end_tick()` at the end (in a finally block).

2. **identity_composer.py** — wrap `build_identity_preamble()`:
   ```python
   cached = tick_cache.get("identity_preamble")
   if cached is not None:
       return cached
   # ... build preamble ...
   tick_cache.set("identity_preamble", result)
   return result
   ```

3. **Signal surface reads** — the most-read surfaces during daemon ticks: `body_state`, `thought_stream` (latest_fragment), `inner_voice_mode`, `energy_level`. Each surface-building function checks tick_cache before DB query.

### Scope

Only cache values that are read multiple times per tick. Do not cache one-shot reads. Target surfaces:
- `build_identity_preamble()` — called 12+ times per tick
- `energy_level` / `body_state` — read by somatic, reflection, conflict, surprise, thought_stream
- `inner_voice_mode` — read by thought_stream, conflict, reflection
- `latest_fragment` — read by curiosity, thought_action_proposal, meta_reflection, conflict

## Layer C: Ollama KV-Cache-Friendly Call Ordering

### Location

Only change: reorder daemon execution blocks in `heartbeat_runtime.py`.

### Grouping

Daemons sorted by prompt prefix similarity:

1. **Hardware/energy context group:** somatic, surprise, conflict
2. **Thought-stream context group:** thought_stream, curiosity, thought_action_proposal, reflection_cycle
3. **Cross-signal snapshot group:** meta_reflection, user_model
4. **Rare cadence group (24h+):** development_narrative, existential_wonder, code_aesthetic, irony, aesthetic_taste
5. **Non-LLM daemons (order irrelevant):** experienced_time, absence, memory_decay, signal_decay, dream_insight, council_memory, autonomous_council, desire, creative_drift

### Rationale

Ollama holds KV cache for the last prompt. Consecutive calls with the same `build_identity_preamble()` prefix plus similar context structure let Ollama skip re-evaluating the shared prefix. Within each group, the prompt prefix is near-identical.

## What We Do NOT Cache

- Visible chat responses (user-facing, must always be fresh)
- Heartbeat decision model calls (unique context each tick)
- Session summary generation (one-shot per run end)
- Fallback/empty daemon responses (would mask real output)

## Observability

- `daemon_llm_call()` logs cache hits to `daemon_output_log` with `provider="cache"` so hits are visible in Mission Control
- `tick_cache` exposes `get_tick_cache_stats() -> dict` with hit/miss counts per tick for debugging

## Testing

- Layer A: Unit tests mocking `daemon_llm_call` — verify cache hit returns same value, cache miss calls LLM, TTL expiry works, changed prompt = cache miss
- Layer B: Unit tests for `tick_cache` — start/end lifecycle, get/set semantics, None when inactive
- Layer C: No tests needed — just execution order change

## Success Criteria

- 60-80% reduction in daemon LLM calls per heartbeat cycle (measurable via daemon_output_log provider="cache" entries)
- Zero change in daemon output quality (same prompts produce same cached responses)
- No increase in heartbeat tick duration
