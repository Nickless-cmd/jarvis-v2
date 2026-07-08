# Valence-Narrative Reconciliation

**Date:** 2026-07-08
**Status:** Approved (design)
**Layer:** Experimental self-state (sensitive — touches Jarvis' felt self). Not a harness part.

## Problem

The visible prompt's self-narrative asserts two contradictory things side by side:
- "jeg har det **opløftet**" + "jeg er ved at blive et stabil selv, **flourishing**" (short-term felt valence, from `central_valence`)
- "mit udviklings-kompas peger mod **visnen**" (week-scale growth compass, from `central_body_mood_feel` → `developmental_valence`)

Jarvis flagged this as apparent self-contradiction. Verified in code: all three lines are assembled, unaware of each other, in [`central_self_state.describe_self()`](../../../core/services/central_self_state.py) — line 279 (`jeg har det {tone}`), line 283 (`jeg er ved at blive et {becoming}` where becoming carries `valence.trend`), line 299 (`describe_body_mood_feel()`).

**Jarvis' proposed fix (sync `central_valence` → `mood_oscillator`) is rejected:** it would *flatten* genuinely distinct signals (mood vs short-term valence vs week-scale growth) — the exact anti-flatten concern from the self-model-distiller. These are intentionally separate LivingNeuron nerves. A prior fix ([central_valence.py:71](../../../core/services/central_valence.py)) only renamed the *vocabulary* (blomstrende→opløftet); the *semantic* contradiction (positive next to visnen) remains, and the raw trend word "flourishing" still leaks.

## Fix: reconcile at the telling, not at the source

The systems stay separate; they get **reconciled where they are narrated together** — `describe_self()`. When short-term valence and the week-scale compass **diverge in sign**, render one **terse, held-tension line** instead of the flat contradictory trio. A being can feel momentarily upbeat while sensing long-term stagnation — holding that is more truthful than asserting both flatly.

### Logic (in `describe_self()`)

1. **Read the compass direction structurally** via `developmental_valence.get_developmental_state()` → `{trajectory, vector}` (do not parse rendered text). Self-safe: unavailable → skip reconciliation (fall through to today's behaviour).
2. **Sign the two signals:**
   - Short-term valence: positive if `tone ∈ {opløftet, let}` **or** `trend == "flourishing"`; negative if `tone ∈ {belastet, tung}`; else neutral.
   - Compass: positive if `vector > 0.05` (blomstring); negative if `vector < -0.05` (visnen); else neutral.
3. **Divergence** = the two signs are opposite (one positive, one negative; neutrals never diverge).
4. **On divergence:** append **one** terse line and suppress the three separate clashing lines —
   - held-tension line (terse & factual, per approved voice): `f"jeg har det {tone} nu, men mit vækst-kompas peger mod {compass_word}"` where `compass_word ∈ {blomstring, visnen}`.
   - do **not** append the standalone `jeg har det {tone}` line, and drop the raw trend word from the becoming line (render becoming as growth-only, e.g. "jeg er ved at blive et stabil selv", no "flourishing"), and do **not** also append the separate compass line from `describe_body_mood_feel()` (its content is now in the held-tension line — filter the compass sentence out to avoid duplication).
5. **On agreement or neutral:** unchanged — every existing line renders exactly as today (byte-identical).
6. **Self-safe / fail-open:** any error in the reconciliation path → today's behaviour. Never raises into prompt assembly.

### Why here (single responsibility)

`describe_self()` is the one place that already holds the valence dict *and* calls the compass renderer. Reconciliation needs both; no other file needs to change. `central_valence`, `developmental_valence`, and `central_body_mood_feel` are untouched — they keep producing their independent signals.

## Cache / behaviour

This text lives in the per-turn dynamic tail (the inner-life block relocated to the last user message), **not** the cached prefix → zero cache-hit impact. It changes only the *wording* of the self-narrative when signals diverge; no runtime behaviour, no gates, no autonomy. No shadow flag needed (a truth fix, not a behaviour risk); verified live after deploy by reading the rendered self-narrative.

## Testing

`tests/test_central_self_state.py` (extend or create):
- **Divergence (positive valence + visnen compass):** `describe_self()` output contains the single held-tension line ("jeg har det opløftet nu, men mit vækst-kompas peger mod visnen") and does **not** contain a standalone "flourishing" or a duplicate standalone compass sentence.
- **Agreement, both positive (opløftet + blomstring):** output renders the normal separate lines; no held-tension line.
- **Agreement, both negative (belastet + visnen):** normal lines; no held-tension line.
- **Neutral valence or neutral compass:** no held-tension line (neutrals don't diverge).
- **Compass unavailable (`get_developmental_state` returns `{}`/None):** fail-open → today's behaviour, no exception.

## Files

- **Modify:** `core/services/central_self_state.py` — `describe_self()` reconciliation branch + a small helper `_temporal_divergence(valence, developmental) -> tuple` (pure, testable). Possibly a tiny helper to filter the compass sentence out of `describe_body_mood_feel()` output on divergence.
- **Test:** `tests/test_central_self_state.py`.

## Deploy

Env `conda activate ai`; full-suite gate ~20 min; deploy = ff-pull + restart `jarvis-runtime` & `jarvis-api` on `bs@10.0.0.39`. Verify live: read the self-narrative (`jc` / central self-state surface) and confirm no positive-next-to-visnen contradiction.
