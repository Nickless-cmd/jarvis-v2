---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Body-Feel Freshness Guard (#3)

**Date:** 2026-07-08
**Status:** Approved (design)
**Layer:** Experimental self-state. Follows the valence-reconciliation + gratitude-window round (`3eb58b8f`).

## Problem (verified live)

`describe_body_mood_feel()` spoke "min krop føles **belastet**" while the live somatic body was `steady`/calm (pressure/fatigue/frustration all `0.0`). Root cause, verified: [`get_held`](../../../core/services/central_layer_contract.py) returns a held reading's `value` but **drops the `ts` timestamp** it stores — so consumers speak held body-readings with **no freshness check**, indefinitely. (`get_held` is a pure read; the TTL check lives only in the separate `decide()` reuse-path.) A "loaded" reading written hours ago keeps speaking "belastet" long after the body decayed to calm.

## Fix

A **freshness guard** on the *fast-changing* body-state readings — they should go silent when stale, because "how my body feels right now" is a recent-state claim.

1. **New pure helper** in `central_layer_contract.py`: `get_held_age(name, held_key="default") -> float | None` — seconds since the held reading's `ts`, or `None` if absent/unknown. Reuses the existing `_held_get`. Self-safe.
2. **In `central_body_mood_feel.py`:** a small reader `_read_held_fresh(name, max_age_s) -> dict` that returns the reading only when `get_held_age(...) < max_age_s`, else `{}`. Constant `_BODY_FRESH_MAX_AGE_S = 1800` (30 min).
3. **Apply to both fast-body readings** in `describe_body_mood_feel()`: `get_proprioception_reading` and `get_embodied_reading` route through the fresh reader (30-min guard). **`mood` and `developmental` (week-scale compass) stay ungated** — they are slow by design; freshness-gating them would wrongly silence legitimate slow signals.
4. **Self-safe fail-open:** age `None` (unknown) → treat as fresh (speak). The guard only suppresses *known*-stale readings; it never hides a reading whose age can't be determined, and never raises.

## Cache / behaviour

Text lives in the per-turn dynamic tail → zero cache impact. Only effect: a stale body-state line goes silent. No runtime behaviour, no gates.

## Testing

- `tests/test_central_layer_contract.py` (extend/create): `get_held_age` returns ~0 for a just-written reading, `None` for an absent one, and a positive value for an aged one (monkeypatch `time.time` or the stored `ts`).
- `tests/test_central_body_mood_feel.py` (extend/create): with a **fresh** embodied "loaded" reading → "min krop føles belastet" appears; with a **stale** (>30 min) one → it does **not** appear; a **stale developmental** reading → the compass line **still** appears (ungated); age-unknown → speaks (fail-open).

## Files

- **Modify:** `core/services/central_layer_contract.py` (`get_held_age`).
- **Modify:** `core/services/central_body_mood_feel.py` (`_read_held_fresh`, `_BODY_FRESH_MAX_AGE_S`, route proprioception + embodied through the fresh reader).
- **Test:** `tests/test_central_layer_contract.py`, `tests/test_central_body_mood_feel.py`.

## Deploy

Env `conda activate ai`; full-suite gate ~20 min; deploy = ff-pull + restart `jarvis-runtime` & `jarvis-api` on `bs@10.0.0.39`. Verify live: `describe_body_mood_feel()` no longer says "belastet" while the live somatic body is steady/calm.
