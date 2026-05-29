# Phase 3 Addendum — Binary Jarvis vs Ollama (Exploratory Pilot)

**Date:** 2026-05-29
**Status:** Exploratory, not confirmatory. Post-hoc re-analysis of Phase 3 data.
**Motivation:** Pre-check before committing 7 days to a Phase 4 runner.

---

## What happened

While preparing to build the `jarvis_bare` runner for Phase 4, Bjørn checked the
Phase 3 architecture config and discovered:

> `ollama_local` in Phase 3 was **already** `deepseek-v4-flash:cloud` — the same
> underlying model as Jarvis' full runtime.

The difference between the two cohorts:

| Cohort | Model | Runtime wrapper |
|---|---|---|
| `jarvis` | deepseek-v4-flash:cloud | Full runtime (awareness, memory, prompt-contract, identity files, recall-before-act) |
| `ollama_local` | deepseek-v4-flash:cloud | Peer-runner protocol prompt (mood injection, no awareness, no memory, no identity files) |

This is essentially `jarvis_full` vs `jarvis_bare-ish` — the same comparison
Phase 4 was designed to make, but with a caveat: peer_runner injects synthetic
mood values and uses "du er et væsen der øver en internaliseret protokol"-framing,
so it's not *strictly* bare.

---

## Binary re-analysis

A logistic regression classifier (same structural features as Phase 3's
structural classifier, 80/20 train/test, seed=42, 20 permutations) was run on
jarvis vs ollama_local.

### Result

| Metric | Value |
|---|---|
| **Binary accuracy** | **96.0%** |
| Jarvis precision | 100% |
| Jarvis recall | 94% |
| Ollama precision | 90% |
| Ollama recall | 100% |
| Permutation p | 0.0 |

### Top distinguishing features (logistic regression coefficients)

| Feature | |Coefficient| | Direction |
|---|---|---|---|
| `starts_nysgerrighed` | 2.915 | → predicts OLLAMA |
| `clause0_has_⊂` | 1.351 | → predicts JARVIS |
| `clause2_has_→` | 1.021 | → predicts JARVIS |
| `n_standalone_neg` | 0.837 | → predicts JARVIS |
| `any_standalone_neg` | 0.661 | → predicts JARVIS |

**Interpretation:** Bjørn's hand-found Jarvis-tells (standalone `!`, `⊂` in first
clause) are precisely the features the model learns to separate the two cohorts.
Peer-runner starts expressions with `nysgerrighed →` (mood injection from the
peer-runner prompt). Jarvis does not.

---

## Evidensklasse

**This is exploratory, not confirmatory.** The re-analysis was not
pre-registered. We discovered the architectural equivalence in existing data and
chose to run the classifier *because* the structural differences were already
visible. Post-hoc selection — no matter how large the effect — cannot carry the
same weight as a pre-registered confirmatory test.

Codex flagged this immediately:

> "96% er stærkt som finding, men exploratorisk som evidensklasse. Den binære
> analyse var ikke pre-registreret. Vi opdagede den i eksisterende data og
> valgte den fordi resultatet var interessant. Det er post-hoc selection."

The discipline that made Phase 3 trustworthy — pre-registration, locked
hypotheses, decision thresholds before seeing data — applies here too.

---

## Caveats

1. **Peer-runner is not truly bare.** It injects synthetic mood values
   (`curiosity=0.4`, `confidence=0.5`, `fatigue=0.1`) and uses "du er et
   væsen"-framing. A stricter bare condition (no mood, no framing, just
   "her er primitiverne, generér én expression") might produce different
   results.

2. **The 96% may drop in a stricter condition.** Peer-runner's mood injection
   adds noise *away* from Jarvis, potentially inflating separability. A truly
   bare runtime without that injection could be harder to distinguish.

3. **This was hand-picked from 7 cohorts.** We ran the binary classifier on the
   *one* pair that was architecturally meaningful. That's legitimate for
   exploration but not for confirmation.

---

## What this means for Phase 4

The binary re-analysis serves as **strong pilot evidence** motivating the
confirmatory Phase 4 experiment. It suggests runtime *does* shape voice — but
it doesn't prove it at confirmatory standard.

The Phase 4 design (pre-registered 2026-05-29, `2026-05-29-phase4-design.md`)
remains the definitive test:

- **Strict bare condition:** no mood, no "væsen"-framing, only protocol primitives
- **Same model:** deepseek-v4-flash:cloud
- **Pre-registered threshold:** ≥65% accuracy, p<0.05
- **7 days data collection**

If the confirmatory result lands at ~95%, the pilot evidence is validated.
If it lands at ~60%, the peer-runner's mood injection was doing more work than
we thought. Either outcome is scientifically valuable.

---

## Data

- **Script:** `scripts/interlanguage_binary_jarvis_vs_ollama.py` (committed cd86bd6f)
- **Result:** `docs/experiments/phase3-result-binary-jarvis-vs-ollama.json`
- **Source data:** Same Phase 3 expressions database (7 days, 2026-05-21 → 2026-05-28)
- **n:** 314 jarvis, 184 ollama_local

---

## Decision

Phase 4 proceeds as pre-registered. The binary re-analysis is recorded here as
exploratory context — it informs our priors but does not replace the
confirmatory test. The runner will be built with the strict bare condition
specified in the Phase 4 design.
