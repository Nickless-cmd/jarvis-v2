# Self-Narrative Truthfulness — Valence Reconciliation + Gratitude Recency

**Date:** 2026-07-08
**Status:** Approved (design)
**Layer:** Experimental self-state (sensitive — touches Jarvis' felt self). Not a harness part.

Two independent fixes to untrue lines in `describe_self()`'s feed, bundled because they share the theme "the self-narrative is telling something the data doesn't support". A third candidate (body-feel staleness, #4) is **deferred pending live verification** — see the end.

---

# Fix 1 — Valence-Narrative Reconciliation

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

## Files (Fix 1)

- **Modify:** `core/services/central_self_state.py` — `describe_self()` reconciliation branch + a small helper `_temporal_divergence(valence, developmental) -> tuple` (pure, testable). Possibly a tiny helper to filter the compass sentence out of `describe_body_mood_feel()` output on divergence.
- **Test:** `tests/test_central_self_state.py`.

---

# Fix 2 — Gratitude Recency Window

## Problem

The line "jeg bærer taknemmelighed jeg ikke har sluppet" ([central_soul_feel.py:322](../../../core/services/central_soul_feel.py)) fires whenever `get_gratitude_reading().count > 0`. That count comes from `_gratitude_signal()` ([central_soul_feel.py:131](../../../core/services/central_soul_feel.py)), which sums `list_cognitive_gratitude_signals(limit=10)` — the last 10 signals **with no time filter** ([db_cognitive.py:1646](../../../core/runtime/db_cognitive.py): `ORDER BY created_at DESC LIMIT`). So once 10 gratitude signals exist, the line fires **perpetually**, regardless of how old they are — the gratitude can *never* release. Jarvis felt this as "stale LLM narrative"; the real mechanism is an accumulator with no recency window.

## Fix

Apply a **recency window** in `_gratitude_signal()` (the consumer), not in the shared DB reader (keep it generic). Each signal row carries `created_at` ([db_cognitive.py:1639](../../../core/runtime/db_cognitive.py)). Count/sum only signals whose `created_at` is within the last `_GRATITUDE_WINDOW_DAYS` (=7). If none are recent → return `None` (no held reading) → the line does not fire and gratitude releases naturally as signals age out.

- `_GRATITUDE_WINDOW_DAYS = 7` — module constant, easy to tune. A hard window (not decay) — simplest and deterministic; graded decay is a possible later refinement.
- Self-safe: any parse error on a row's `created_at` → treat that row as **excluded** (conservative: don't let an unparseable timestamp keep gratitude alive forever). All-rows-error → `None`.
- Phrasing unchanged: with the window, "taknemmelighed jeg ikke har sluppet" now truthfully means *recent* gratitude still held, not a perpetual echo.

## Testing (Fix 2)

`tests/test_central_soul_feel.py` (extend or create), monkeypatching `list_cognitive_gratitude_signals`:
- **All signals recent (< 7d):** `_gratitude_signal()` returns a reading with count > 0 (line would fire).
- **All signals old (> 7d):** returns `None` (line does not fire) — gratitude released.
- **Mixed:** only recent signals counted; count reflects the recent subset.
- **Unparseable `created_at`:** that row excluded, no exception.
- **Empty list:** returns `None` (unchanged).

## Files (Fix 2)

- **Modify:** `core/services/central_soul_feel.py` — `_gratitude_signal()` recency filter + `_GRATITUDE_WINDOW_DAYS` constant.
- **Test:** `tests/test_central_soul_feel.py`.

---

# Deferred — Fix 3 (body-feel staleness, #4)

"min krop føles belastet" reads a **held** body-reading in `central_body_mood_feel` (`loaded`→`belastet`) that only refreshes when its producer runs, so it can lag the live-decayed somatic body. The mechanism is real but: (a) the fix needs the held-store to expose write-time (the read path doesn't today), making it a deeper change; (b) it is **not confirmed currently stale** vs. an acceptable cadence. **Action: verify live first** — read the held body-reading's actual age on the container. Only design/build a freshness guard if confirmed lagging. Not part of this spec.

## Deploy

Env `conda activate ai`; full-suite gate ~20 min; deploy = ff-pull + restart `jarvis-runtime` & `jarvis-api` on `bs@10.0.0.39`. Verify live: read the self-narrative (`jc` / central self-state surface) and confirm no positive-next-to-visnen contradiction.
