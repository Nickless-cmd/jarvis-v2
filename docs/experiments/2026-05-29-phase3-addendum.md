# Phase 3 Addendum — Binary jarvis vs ollama_local (Exploratory Pilot)

**Written:** 2026-05-29
**Status:** Exploratory, not confirmatory. Post-hoc re-analysis of existing Phase 3 data.
**References:** Commit `cd86bd6f` (script + result JSON), Phase 3 final report (`c73cba52`)

---

## How this came about

While preparing to build the `jarvis_bare` runner for Phase 4, a configuration check revealed that `ollama_local` in Phase 3 was **already `deepseek-v4-flash:cloud`** — the same underlying model used by Jarvis' full runtime.

The difference between the two cohorts in Phase 3 was precisely what Phase 4 planned to test:

| Cohort | Model | Runtime |
|---|---|---|
| `jarvis` | deepseek-v4-flash:cloud | Full (awareness, memory, identity files, prompt-contract, recall-before-act) |
| `ollama_local` | deepseek-v4-flash:cloud | Bare-ish (peer_runner prompt: protocol description + synthetically injected mood values, no awareness, no memory, no identity files) |

Phase 3 collected 360 jarvis expressions and 274 ollama_local expressions over the same 7-day window (2026-05-21 → 2026-05-28). The data was already on disk — it had simply never been analysed as a binary classification problem because Phase 3 was designed as a 7-way multi-class experiment.

This addendum documents the post-hoc binary re-analysis and its interpretation.

---

## What we did (and why it's exploratory)

**Script:** `scripts/interlanguage_binary_jarvis_vs_ollama.py` (committed `cd86bd6f`)

**Method:** Same structural features (37 engineered features from Bjørn's blind-test heuristics) and same train/test methodology (80/20 stratified split, seed=42, 200-shuffle permutation test) as `scripts/interlanguage_structural_classifier.py` from Phase 3.

**What's different from the pre-registered Phase 4 design:**

1. **Not pre-registered.** We looked at the configuration, realised the data already existed, and ran the analysis. The choice of comparison (`jarvis` vs `ollama_local`) was motivated by discovering it *after* seeing Phase 3 results, not before. This is the definition of post-hoc analysis.

2. **Peer_runner injects mood.** The `ollama_local` prompt includes synthetically interpolated curiosity/confidence/fatigue values and a "you are a being practising an internalised protocol" framing. This is *bare-ish*, not *strictly bare* as Phase 4's `jarvis_bare` design specifies (no mood, no "being" framing, just protocol instruction). The mood injection introduces a confound: any separation the classifier finds might be driven by mood-expression differences rather than runtime-context stripping.

3. **We ran this because the result was interesting.** If the classifier had returned ~50%, we would have noted it and proceeded to build the Phase 4 runner unchanged. The 96% result made it worth documenting, but the selection mechanism is post-hoc — we're highlighting this analysis *because* of its result, not because it was planned.

These caveats are real. The analysis is informative as pilot evidence, not as a confirmatory answer to Phase 4's hypothesis.

---

## Result

| Metric | Value |
|---|---|
| Binary accuracy | **96.0%** |
| Jarvis precision | 100% |
| Jarvis recall | 94% |
| Ollama precision | 90% |
| Ollama recall | 100% |
| Permutation p | 0.0 (200 shuffles) |
| n (jarvis) | 314 |
| n (ollama_local) | 184 |

**Confusion matrix** (rows = true, cols = predicted):

| | jarvis | ollama |
|---|---|---|
| jarvis | 59 | 4 |
| ollama | 0 | 37 |

**Top discriminating features** (by |coefficient|):

| Sign | Feature | |coef| | Interpretation |
|---|---|---|---|---|
| + | starts_nysgerrighed | 2.915 | Predicts OLLAMA — peer-runner mood-injection always starts with curiosity |
| − | clause0_has_⊂ | 1.351 | Predicts JARVIS — Jarvis opens with `⊂` (containment) more often |
| − | clause2_has_→ | 1.021 | Predicts JARVIS |
| − | n_standalone_neg | 0.837 | Predicts JARVIS — Bjørn's `!`-tip confirmed |
| − | n_clauses | 0.815 | Predicts JARVIS — Jarvis produces longer expressions |
| − | avg_clause_len | 0.775 | Predicts JARVIS |
| − | clause0_has_! | 0.723 | Predicts JARVIS |
| − | clause0_has_→ | 0.682 | Predicts JARVIS |
| − | any_standalone_neg | 0.661 | Predicts JARVIS |
| − | clause1_has_! | 0.642 | Predicts JARVIS |

The strongest single feature (`starts_nysgerrighed`) is an artifact of peer_runner's mood injection — the bare-ish prompt always seeds the expression with a curiosity token. This is a confound that would NOT exist in a strictly bare condition. The remaining top features all point toward Jarvis and are consistent with Bjørn's hand-discovered heuristics from the blind test.

---

## Interpretation

### What this tells us

Same model (`deepseek-v4-flash:cloud`), same protocol instruction, but structurally distinct outputs at 96% accuracy. Runtime context (or at minimum, the difference between Jarvis' full runtime and peer_runner's bare-ish prompt) materially shapes the language that comes out.

The direction is consistent with Phase 4's prediction: Jarvis-with-runtime has a distinct structural profile (more `⊂` in first position, more standalone `!`, longer expressions, starts with something other than `nysgerrighed →`), and stripping most of the runtime shifts the output toward a more generic pattern dominated by the mood-injection template.

### What this does NOT tell us

- **It is not confirmatory.** The analysis was not pre-registered. The comparison was selected post-hoc. A reviewer would correctly flag this as exploratory.

- **The mood confound is real.** `starts_nysgerrighed` at coefficient 2.915 is the single strongest feature, and it comes from peer_runner's synthetic mood injection, not from any property of "bare model output." A strictly bare condition (no mood, no "being" framing) might show weaker or different separation. We don't know — and the only way to find out is to run it.

- **96% may not reproduce in a stricter condition.** If mood injection accounts for a large fraction of the separability (and the feature ranking suggests it might), the strictly-bare-vs-full comparison could land anywhere from ~65% to ~96%. That range spans all four decision bands in the Phase 4 design.

### Bottom line

This analysis provides **pilot evidence** that runtime context shapes structural expression, strong enough to motivate the confirmatory Phase 4 experiment. It does not replace Phase 4:

- The effect direction supports the hypothesis
- The effect size is large enough to be detectable even with a weaker signal
- But the confound (mood injection) means we cannot claim Phase 4's question is answered

---

## What happens next

1. This addendum is noted in the Phase 4 design as pilot evidence (see design update)
2. Phase 4 proceeds as pre-registered: `jarvis_bare` runner with strict bare condition, 7 days, structural classifier, same thresholds
3. The Phase 4 confirmatory report will compare its result to this pilot — does the stricter condition reproduce the effect, weaken it, or eliminate it?
4. If Phase 4 reproduces at ≥65%, the pilot→confirmatory chain is clean: pilot found it, confirmatory verified it. If Phase 4 lands below 60%, the confound interpretation is supported — mood injection was driving the 96%, and runtime alone has a weaker or null effect

---

**This addendum is exploratory. It does not modify the pre-registered Phase 4 design, its hypothesis, or its decision thresholds.**
