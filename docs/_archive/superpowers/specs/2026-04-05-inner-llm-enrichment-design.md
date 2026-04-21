# Inner LLM Enrichment — Design Spec

**Date**: 2026-04-05
**Status**: Approved
**Scope**: Replace deterministic template strings in 3 private memory pipeline files with LLM-generated inner thoughts via async enrichment

## Problem

Jarvis' private memory pipeline produces hardcoded deterministic strings instead of LLM-generated inner thoughts. Functions like `_helpful_signal()` output fixed templates such as `"keep the steadier pull around {focus}"`, and the same capability_id gets recycled as focus through every layer. This makes inner voice, development focus, and memory feel robotic and circular.

## Scope

**In scope — 3 files (highest impact):**
- `core/memory/private_inner_note.py` — `_private_summary()` and phrase generation
- `core/memory/private_growth_note.py` — `_lesson()`, `_helpful_signal()`, `_mistake_signal()`
- `core/memory/protected_inner_voice.py` — `_voice_line()` synthesis

**Out of scope (future work):**
- `core/memory/private_reflective_selection.py`
- `core/memory/private_development_state.py`
- `core/memory/private_retained_memory_record.py`
- `apps/api/jarvis_api/services/development_focus_tracking.py`
- `apps/api/jarvis_api/services/private_inner_note_signal_tracking.py`

## Architecture

### Approach: Unified Inner LLM Enrichment Service

The existing pipeline in `private_layer_pipeline.py` → `write_private_terminal_layers()` remains unchanged. It runs synchronously, builds template-based payloads, and persists them immediately.

A new enrichment layer runs **after** persistence:

```
write_private_terminal_layers()
  ├── build + persist inner_note (template)     ← unchanged
  ├── build + persist growth_note (template)    ← unchanged
  ├── build + persist inner_voice (template)    ← unchanged
  └── enrich_private_layers_async(              ← NEW
        run_id, payloads, chat_context)
           └── Daemon thread:
               ├── enrich inner_note → UPDATE DB
               ├── enrich growth_note → UPDATE DB
               └── enrich inner_voice → UPDATE DB
```

Template values serve as immediate fallback. LLM-enriched values replace them in-place when ready.

## New File: `core/memory/inner_llm_enrichment.py`

### Public API

```python
def enrich_private_layers_async(
    *,
    run_id: str,
    inner_note_payload: dict,
    growth_note_payload: dict,
    inner_voice_payload: dict,
    recent_chat_context: str,
) -> None:
```

Starts a single daemon thread that runs 3 LLM enrichments sequentially (to avoid rate limits on cheap models).

### LLM Call Pattern

Each enrichment:
1. Builds a focused prompt from pipeline payload fields + recent chat context
2. Calls cheapest available model via `resolve_provider_router_target(lane="cheap")`
3. Makes a synchronous HTTP call (within the daemon thread) — reuses the HTTP/urllib pattern from `visible_model.py` but with non-streaming completion (single response, no SSE)
4. On success: updates DB record via new `update_*_enriched()` function
5. On failure: logs warning, template value is preserved

### Prompts

Three separate, short system prompts (in Danish):

**Inner note enrichment:**
> "Du er Jarvis' private indre stemme. Baseret på denne arbejds-status og samtale-kontekst, formulér en kort, naturlig refleksion (1-2 sætninger, dansk). Undgå klichéer og faste vendinger."

User message contains: `private_summary`, `uncertainty`, `work_signal`, `focus`, recent chat turns.

**Growth note enrichment:**
> "Baseret på dette lærings-outcome, formulér hvad Jarvis lærte og hvad der var nyttigt (1-2 sætninger, dansk). Vær specifik, ikke generisk."

User message contains: `lesson`, `helpful_signal`, `mistake_signal`, `learning_kind`, `topic`, recent chat turns.

**Inner voice enrichment:**
> "Syntesér Jarvis' indre tilstand til en kort voice-linje der fanger mood, position og retning (1 sætning, dansk). Brug ikke pipe-separerede formater."

User message contains: `mood_tone`, `self_position`, `current_concern`, `current_pull`, recent chat turns.

### Token Budget

- Max output per call: 100 tokens
- Approximate input per call: ~500 tokens (payload + chat context)
- Total per pipeline run: ~1800 tokens (3 calls × ~600 tokens each)

### Chat Context

`recent_chat_context` is built from the already-available parameters `user_message_preview` and `work_preview` in `write_private_terminal_layers()`. No new data dependencies.

## DB Changes

### New Functions in `core/runtime/db.py`

```python
def update_private_inner_note_enriched(*, run_id: str, enriched_summary: str) -> None:
    """UPDATE private_inner_notes SET summary = ?, enriched = 1 WHERE run_id = ?"""

def update_private_growth_note_enriched(
    *, run_id: str, enriched_lesson: str, enriched_helpful_signal: str
) -> None:
    """UPDATE private_growth_notes SET lesson = ?, helpful_signal = ?, enriched = 1 WHERE run_id = ?"""

def update_protected_inner_voice_enriched(*, run_id: str, enriched_voice_line: str) -> None:
    """UPDATE protected_inner_voices SET voice_line = ?, enriched = 1 WHERE run_id = ?"""
```

### Schema Changes

Add `enriched INTEGER DEFAULT 0` column to:
- `private_inner_notes`
- `private_growth_notes`
- `protected_inner_voices`

This flag lets Mission Control distinguish template vs. LLM-enriched content.

## Integration Point

In `core/memory/private_layer_pipeline.py` → `write_private_terminal_layers()`, add at the end of the function (after all persistence):

```python
from core.memory.inner_llm_enrichment import enrich_private_layers_async

enrich_private_layers_async(
    run_id=run_id,
    inner_note_payload=inner_note_payload,
    growth_note_payload=growth_note_payload,
    inner_voice_payload=inner_voice_payload,
    recent_chat_context=_extract_recent_chat(user_message_preview, work_preview),
)
```

Helper `_extract_recent_chat()` concatenates user_message_preview and work_preview into a bounded string (~500 tokens max).

## Error Handling

- LLM call failure → warning in log, template value preserved
- No retry — next pipeline run produces a fresh enrichment opportunity
- Thread is daemon → dies with the process
- DB update failure → warning in log, no side effects
- Missing cheap model config → logs once, skips all enrichment

## What Does NOT Change

- Pipeline execution flow and ordering
- Existing template logic in all 3 files (preserved as fallback)
- The other 5 pipeline files
- Mission Control API/UI contracts (enriched flag is additive)
- Eventbus events
- Any downstream consumers of pipeline payloads

## Success Criteria

1. Pipeline latency is unchanged (enrichment is fully async)
2. When cheap model is available: inner_note, growth_note, and inner_voice contain natural-language text instead of template strings
3. When cheap model is unavailable: system degrades gracefully to current template behavior
4. Mission Control can show enriched flag to distinguish LLM vs template content
5. Total cost per pipeline run stays under 2000 tokens on cheap model
