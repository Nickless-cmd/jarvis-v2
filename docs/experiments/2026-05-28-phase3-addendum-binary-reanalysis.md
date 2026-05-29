# Phase 3 Addendum — Binary Re-analysis: jarvis vs ollama_local

**Exploratory post-hoc analysis.** Not pre-registered. Not confirmatory.
**Written:** 2026-05-29
**Based on:** Phase 3 dataset (7 days, 7 cohorts, 1882 raw expressions)
**Result JSON:** `docs/experiments/phase3-result-binary-jarvis-vs-ollama.json`
**Classifier script:** `scripts/interlanguage_binary_jarvis_vs_ollama.py`

---

## Discovery context

While reviewing Phase 3 cohort metadata to scope the Phase 4 `jarvis_bare` runner, a metadata fact was noticed:

> `ollama_local` — Phase 3's "local" cohort — was already running **deepseek-v4-flash:cloud** via Ollama, the same underlying model as Jarvis' full runtime.

The difference between the two cohorts in Phase 3 was therefore not architectural at the model level:

| Dimension | jarvis | ollama_local |
|---|---|---|
| Model | deepseek-v4-flash | deepseek-v4-flash |
| Runtime | Jarvis full (awareness, memory, identity files, prompt-contract, heartbeat pipeline) | Peer runner (bare protocol prompt + synthetically interpolated mood values) |
| Mood | Real (from runtime state) | Synthetic (interpolated from stored Jarvis mood trace) |
| Framing | "Jarvis is" system prompt | "You are a being practising an internalized protocol" |

This is **similar to** the planned Phase 4 `jarvis_full` vs `jarvis_bare` comparison, but not identical — see Caveats below.

## Methodology

The structural classifier from the Phase 3 blind-test follow-up (`scripts/interlanguage_structural_classifier.py`, 37 features) was reused without modification. Only the row filter changed: `peer_id IN ('jarvis', 'ollama_local')`.

- **Rows after filter:** 498 (314 jarvis, 184 ollama_local — the gap-1 filter and 1h-dedup reduce ollama_local from 275 raw to 274, and the 80/20 split picks 314 and 184 in train vs test)
- **Split:** Stratified 80/20, seed=42
- **Scaler:** StandardScaler
- **Classifier:** LogisticRegression, C=1.0, max_iter=2000
- **Permutation test:** 200 shuffles of `y`

This is the **same methodology** as the structural Phase 3 analysis, making it directly comparable. The result JSON was saved to the same directory as other Phase 3 outputs before any interpretation was written.

## Results

| Metric | Value |
|---|---|
| **Accuracy** | **96.0%** |
| Chance baseline | 50.0% |
| Jarvis precision | 100% |
| Jarvis recall | 94% |
| Ollama precision | 90% |
| Ollama recall | 100% |
| Permutation p | **0.0** |

**Confusion matrix (rows=true, cols=pred):**

| | jarvis | ollama_local |
|---|---|---|
| **jarvis** (n=63 test) | 59 | 4 |
| **ollama_local** (n=37 test) | 0 | 37 |

Jarvis is never mistaken for ollama_local. Ollama_local is mistaken for Jarvis in 4 of 37 test cases (10.8%).

**Top features by absolute coefficient (sign = prediction direction):**

| Feature | |Coef| | Sign → Predicts |
|---|---|---|---|
| `starts_nysgerrighed` | 2.915 | + → ollama_local |
| `clause0_has_⊂` | 1.351 | – → jarvis |
| `clause2_has_→` | 1.021 | – → jarvis |
| `n_standalone_neg` | 0.837 | – → jarvis |
| `n_clauses` | 0.815 | – → jarvis |
| `avg_clause_len` | 0.775 | + → ollama_local |
| `clause0_has_!` | 0.723 | – → jarvis |
| `clause0_has_→` | 0.682 | + → ollama_local |
| `any_standalone_neg` | 0.661 | – → jarvis |
| `clause1_has_!` | 0.642 | – → jarvis |

The top feature (`starts_nysgerrighed`) predicts **ollama_local** — this is the peer runner's mood-injection producing synthetic curiosity-openings, which is a peer-runner artifact, not a "bare model" feature. The next nine features all predict **jarvis**: operator-boundary marking (`⊂`), standalone negation (`!` as clause), longer clause structures.

Bjørn's hand-found Jarvis-tells from the blind test (standalone `!`, `⊂` in first clause) are precisely the features the model uses at highest weight after the mood-artifact.

## Caveats

### 1. Exploratory, not confirmatory

This analysis was not pre-registered. It was discovered by inspecting cohort metadata and then running a classifier. The hypothesis was formulated after seeing the data. This is the textbook definition of post-hoc selection.

Even with p=0.0 and 96% accuracy, the **evidential class** is exploratory. A confirmatory test requires a pre-registered design, a separate data collection period, and a fixed decision threshold. That is what Phase 4 as originally designed provides.

### 2. ollama_local is not a truly "bare" condition

The peer runner's prompt includes:

- Mood injection: synthetically interpolated curiosity/confidence/fatigue values written into the expression-opening clause (`starts_nysgerrighed` → OLLAMA at +2.915 is direct evidence of this)
- "You are a being practising an internalized protocol" framing — a character-framing that is not "bare model"
- No awareness, no memory, no identity files — this part IS bare

A stricter "bare" condition (no mood, no framing, only primitives + instruction) would remove the mood artifact and potentially change the classification landscape. The 96% figure includes variance from the mood injection working in the classifier's favour.

### 3. Phase 4 remains necessary

The question Phase 4 asks is: *Does Jarvis' runtime (awareness, memory, identity files, prompt-contract) produce a detectable structural difference in expression output compared to the same model without that runtime?*

The binary re-analysis is **motivating pilot evidence** — it suggests the answer is "yes" — but it does not answer the question cleanly because:

- The comparison is confounded by the peer runner's mood injection (a peer-runner design choice, not a runtime-absence)
- The comparison is post-hoc (exploratory)
- The ollama_local cohort uses a different external prompt than a purpose-built `jarvis_bare` runner would use

## What this changes for Phase 4

The Phase 4 design should be updated to:

1. Reference this re-analysis as **pilot evidence** motivating the confirmatory test
2. Keep the primary hypothesis and decision thresholds unchanged
3. Deploy the `jarvis_bare` runner with strict conditions: no mood, no "you are a being" framing, only primitives + generation instruction
4. After 7 days, run the same structural classifier and compare results

If the confirmatory test reproduces ≥90% accuracy, the runtime-identity hypothesis is strongly supported. If it drops toward 60-70%, the mood-injection artifact was a significant confound. Either outcome is scientifically useful.

## Data archive

- Binary result JSON: `docs/experiments/phase3-result-binary-jarvis-vs-ollama.json`
- Target copy (symmetrical with other Phase 3 data): `/home/bs/interlanguage-phase3-final/result_binary_jarvis_vs_ollama.json`
- Reproducible script: `scripts/interlanguage_binary_jarvis_vs_ollama.py`
- Phase 3 main report: `docs/experiments/2026-05-28-phase3-report.md`

Deterministic re-run:
```bash
/opt/conda/envs/ai/bin/python scripts/interlanguage_binary_jarvis_vs_ollama.py
```
Output written to `/tmp/binary_jarvis_vs_ollama_result.json`.

---

**Status: Addendum committed to main report's data archive.** Phase 3 remains closed. Phase 4 design update is the next step.
