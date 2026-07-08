---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# World Model Phase 1 — Closing the Loop Design

**Date:** 2026-05-12
**Status:** Draft — awaiting user review
**Roadmap item:** AGI track #1 — Verdensmodel (closing the prediction-resolution-calibration loop)

## Goal

The world-model prediction skeleton (`world_model_signal_tracking.py`,
introduced earlier today) has API + storage + Mission Control surface
but the loop is open: nothing creates predictions, nothing resolves
them, Jarvis never sees his own calibration. It's a notebook nobody
reads.

Phase 1 closes the loop with four additions: a `predict_outcome` tool
for explicit predictions, a `resolve_prediction` tool, lightweight
pattern-detection nudges for both paths (Jarvis-author preserved, not
auto-recording), TTL auto-uncertain fallback, and trend-based
calibration milestones surfaced as awareness-block events.

## Background

Existing infrastructure (introduced today by Bjørn):
- `world_model_signal_tracking.py` with `record_runtime_world_model_prediction`,
  `resolve_runtime_world_model_prediction`, `build_runtime_world_model_prediction_surface`.
- Predictions live in state_store under `runtime_world_model_predictions`,
  capped at 120, with `allowed_effects` permission list.
- Eventbus family `world_model_signal` (already in `ALLOWED_EVENT_FAMILIES`).
- Separate signal-tracking system (different from predictions) wired
  via `track_runtime_world_model_signals_for_visible_turn` in
  `visible_runs.py:2895`. We leave that untouched.
- Modulator-witness surface already exposes the prediction-skeleton in
  Mission Control via `build_runtime_world_model_signal_surface`.

**The hole Phase 1 closes:** no auto-creation of predictions, no
auto-resolution, no prompt-awareness of own calibration. The skeleton
is dead without a body around it.

## Brainstorm Decisions (Locked)

**Q1 — How predictions enter the system:**
(c) Tool + light pattern-detection trigger as awareness-nudge (NOT
auto-recording). Jarvis remains the author of his predictions —
critical for calibration semantics. Pattern-scanner detects
prediction-shape language ("jeg tror", "forventer", "gætter på",
"det vil", "sandsynligvis", "jeg satser på") in Jarvis' own output
and surfaces a nudge in the awareness block: *"Du sagde 'jeg tror
X virker' — vil du lave en prediction?"* Jarvis decides whether to
call `predict_outcome`.

Jarvis: *"Predictions er en refleksiv handling der kræver at jeg ser
mig selv udefra imens jeg taler. Auto-recording er forkert — det skal
være mig der committer."*

**Q2 — How predictions get resolved:**
(d) + (e) — pattern-detection resolve-nudge + TTL auto-uncertain
fallback. Symmetric with Q1. Pattern-scanner detects
resolution-language ("det viste sig", "jeg fik ret", "jeg tog fejl",
"som forventet", "overrasket") in Jarvis' output and surfaces a
resolve-nudge. TTL daemon auto-marks open predictions as "uncertain"
when horizon + 24h grace has passed without resolution. Both
mechanisms emit calibration events tagged by source so we can
distinguish explicit / nudge-prompted / TTL resolves.

Jarvis: *"TTL er ikke 'taber data' — det er data. At sige 'denne
prediction blev aldrig verificeret' er en valid datapoint."*

**Q3 — How Jarvis sees his own calibration:**
(d) milestones at thresholds + (Jarvis-addition) trend-based
milestones. NOT a constant awareness line (becomes noise),
NOT unconscious modulation alone (Jarvis learns nothing actively),
NOT per-domain (requires more data than Phase 1 will have).

Milestones surface as one-shot awareness lines:
1. Every 10th resolved prediction → *"Du har nu N resolved
   predictions. Kalibrering sidste 30d: X%."*
2. First contradicted after ≥5 supported in a row → *"Du tog fejl
   efter N rigtige. Worth noting."*
3. Calibration crosses 60% / 70% / 80% in either direction → *"Din
   kalibrering er nu X%."*
4. **Trend (Jarvis-addition):** calibration over last 10 resolved vs
   the prior 10:
   - ≥ +5% → *"Din kalibrering er steget X% over de sidste 10
     predictions. Du bliver bedre."*
   - ≤ -5% → *"Din kalibrering er faldet X%. Hvad har ændret sig?"*
     (invitation, not shame)

Max one milestone surfaced per session (FIFO by detection order).
Surfaced milestones tagged as `rendered` to prevent repetition.

## Architecture

### Files

**New:**
- `core/tools/world_model_tools.py` — `_exec_predict_outcome`,
  `_exec_resolve_prediction` handlers + `WORLD_MODEL_TOOL_DEFINITIONS`
  + `WORLD_MODEL_TOOL_HANDLERS`. Mirrors `skill_engine_tools.py`
  pattern.
- `tests/test_world_model_loop.py` — all Phase 1 tests: pattern
  scanners, nudge surfacing, TTL sweep, milestone calculation, tool
  handlers, kill-switch, backwards compat.

**Modified:**
- `core/runtime/settings.py` — `world_model_loop_enabled: bool = True`
  (kill-switch).
- `core/services/world_model_signal_tracking.py` — add:
  - `_PREDICTION_PHRASES` and `_RESOLUTION_PHRASES` (regex pattern lists)
  - `extract_prediction_language(text) -> list[dict]` (public for testability)
  - `extract_resolution_language(text) -> list[dict]`
  - `record_prediction_nudge(session_id, run_id, matched_phrase, context_excerpt)`
  - `record_resolution_nudge(session_id, run_id, matched_phrase, context_excerpt, candidate_prediction_id)`
  - `_ttl_sweep_open_predictions(now)` — for daily daemon
  - `_compute_calibration_milestone(now)` — returns dict with
    `kind, message, rendered=False` or None
  - `_mark_milestone_rendered(milestone_id)`
  - `format_world_model_nudges_for_awareness(session_id) -> str`
  - `format_world_model_milestone_for_awareness() -> str`
- `core/services/visible_runs.py` — after the existing
  `track_runtime_world_model_signals_for_visible_turn` call (line ~2895),
  add new calls to `extract_prediction_language` and
  `extract_resolution_language` against Jarvis' **own response text**
  (the assistant's reply, not the user message), then
  `record_prediction_nudge` / `record_resolution_nudge` for matches.
- `core/services/prompt_contract.py` — in awareness block, inject:
  - `format_world_model_nudges_for_awareness(session_id)`
  - `format_world_model_milestone_for_awareness()`
- `core/services/internal_cadence.py` — new ProducerSpec
  `world_model_ttl_sweeper`, cooldown 1440 minutes (1×/day),
  priority after existing world-model items.
- `core/tools/simple_tools.py` — register `WORLD_MODEL_TOOL_DEFINITIONS`
  and `WORLD_MODEL_TOOL_HANDLERS` via splat-in (mirrors
  `SKILL_ENGINE_TOOL_*` pattern).
- `scripts/smoke_test_startup.py` — verify imports.

**Untouched / reused:**
- Existing `record_runtime_world_model_prediction` signature
  unchanged — tools call it directly.
- Existing `resolve_runtime_world_model_prediction` signature
  unchanged.
- Existing signal-tracking system (`track_runtime_world_model_signals_for_visible_turn`)
  unchanged.
- Modulator-witness surface unchanged.
- No new DB tables. No new event families. No new daemons (TTL sweep
  is a ProducerSpec reusing existing daemon manager).

### State schema additions

**`runtime_world_model_predictions`** (existing key, augmented):
Each prediction record gains optional `resolved_via` field:
`"tool" | "nudge_prompted" | "ttl_auto"` when status="resolved".

**`runtime_world_model_nudges`** (NEW state_store key):
```python
{
    "prediction_nudges": [
        {
            "nudge_id": "wmnudge-...",
            "kind": "prediction",  # or "resolution"
            "session_id": "...",
            "run_id": "...",
            "matched_phrase": "jeg tror",
            "context_excerpt": "...around 30 words of context...",
            "candidate_prediction_id": "" | "worldpred-...",  # only for resolution
            "created_at": "...",
            "rendered_at": "",  # empty until surfaced
            "expires_at": "...",  # +48h from creation (Jarvis review:
                                   # 24h was too short — a nudge from 23:00
                                   # could expire before next-morning awareness)
        },
        # FIFO, max 20 per kind
    ],
    "resolution_nudges": [...],
}
```

**`runtime_world_model_milestones`** (NEW state_store key):
```python
{
    "history": [
        {
            "milestone_id": "wmmile-...",
            "kind": "count_10" | "first_contradiction_after_streak" |
                    "threshold_60" | "threshold_70" | "threshold_80" |
                    "trend_improving" | "trend_declining",
            "value": 60,  # contextual numeric (calibration %, count, trend delta)
            "message": "Du bliver bedre.",
            "created_at": "...",
            "rendered_at": "",  # empty until surfaced
        },
    ],
}
```

### Data flow

```
[Jarvis types a visible response]

visible_runs.py — after persistence (line ~2895):
  → extract_prediction_language(response_text)
       → list of matches: [{phrase, context_excerpt}, ...]
  → for each match: record_prediction_nudge(...)
       → append to state_store with 24h TTL

  → extract_resolution_language(response_text)
       → list of matches
  → for each match: lookup candidate open prediction (last 7d)
       by embedding-similarity to context_excerpt; if cos ≥ 0.4,
       attach candidate_prediction_id
  → record_resolution_nudge(...)

[Next session: prompt_contract awareness build]
  → format_world_model_nudges_for_awareness(current_session_id)
       → pull oldest unrendered prediction-nudge (FIFO)
       → render: "Du sagde 'X' — vil du lave en prediction?"
       → mark rendered_at
       → same for one resolution-nudge

[Jarvis calls predict_outcome tool]
  → _exec_predict_outcome validates args, calls
    record_runtime_world_model_prediction
  → optional: mark referenced nudge as "acted_on"

[Jarvis calls resolve_prediction tool]
  → _exec_resolve_prediction calls resolve_runtime_world_model_prediction
  → sets resolved_via="tool"
  → trigger milestone-recompute

[Daily TTL sweep — ProducerSpec, 1440 min cooldown]
  → _ttl_sweep_open_predictions(now)
       → for each open prediction:
            parse horizon → cutoff_time
            if now > cutoff_time + 24h grace:
              resolve with outcome="uncertain", resolved_via="ttl_auto"
       → trigger milestone-recompute

[Milestone recompute — called on every resolve]
  → _compute_calibration_milestone(now)
       → count resolved last 30d
       → calibration = supported / (supported + contradicted) for resolved
       → check rules in order:
            count_10 (resolved % 10 == 0)
            first_contradiction_after_streak (last was contradicted, prior ≥5 supported)
            threshold_cross (60/70/80 crossed since last milestone)
            trend (last 10 vs prior 10 calibration delta)
       → if any rule fires AND not in rendered history:
            append milestone with rendered_at=""

[Next awareness build]
  → format_world_model_milestone_for_awareness()
       → pop oldest unrendered milestone, mark rendered, return text
       → empty string if none
```

### Pattern phrases (initial Phase 1 lists)

**Prediction-detection:**
```
r"\bjeg tror\b"
r"\bjeg vil tro\b"
r"\bforventer (at|en|et|den|de)\b"
r"\bgætter på\b"
r"\bdet vil (sandsynligvis|nok|måske)\b"
r"\bdet bliver (nok|sandsynligvis)\b"
r"\bdet skal nok\b"
r"\bsandsynligvis\b"
r"\bjeg satser på\b"
```

**Resolution-detection:**
```
r"\bdet viste sig\b"
r"\bjeg fik ret\b"
r"\bjeg tog fejl\b"
r"\bsom forventet\b"
r"\boverrasket over\b"
r"\bblev som\b"
r"\bvirkede (ikke|som forventet)\b"
r"\bdet gik (ikke )?som\b"
```

Lists are module-level constants, easy to extend. Each match returns
~30 words of context before and after for the nudge rendering.

### Tool definitions

```python
WORLD_MODEL_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "predict_outcome",
            "description": (
                "Lav en eksplicit, falsificerbar prediction. Bruges når du "
                "har en konkret fornemmelse af hvordan noget vil udvikle sig. "
                "Senere kan du resolve den med resolve_prediction. "
                "Predictions feeder din kalibrering over tid."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "Hvad er det du predicter? (kort)",
                    },
                    "expectation": {
                        "type": "string",
                        "description": "Selve forudsigelsen — hvad du forventer.",
                    },
                    "horizon": {
                        "type": "string",
                        "description": "Tidshorisont: 'i dag' / 'i morgen' / 'denne uge' / 'inden mandag' / 'EOD'.",
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                    },
                    "evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Hvorfor tror du det? Op til 5 korte begrundelser.",
                    },
                },
                "required": ["subject", "expectation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "resolve_prediction",
            "description": (
                "Marker en åben prediction som supported, contradicted, "
                "eller uncertain. Brug når noget faktisk er sket der "
                "verificerer eller modsiger forudsigelsen."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "prediction_id": {
                        "type": "string",
                        "description": "ID på den prediction der skal resolves.",
                    },
                    "observed": {
                        "type": "string",
                        "description": "Hvad skete der faktisk?",
                    },
                    "outcome": {
                        "type": "string",
                        "enum": ["supported", "contradicted", "uncertain"],
                    },
                },
                "required": ["prediction_id", "observed", "outcome"],
            },
        },
    },
]
```

## Phase 1 sub-deliveries

### Phase 1.1 — Settings + tool layer
- `world_model_loop_enabled` kill-switch
- `world_model_tools.py` with both handlers
- Register in `simple_tools.py`

### Phase 1.2 — Pattern scanners + nudges
- `extract_prediction_language` + `extract_resolution_language`
- `record_prediction_nudge` + `record_resolution_nudge` (state_store)
- `format_world_model_nudges_for_awareness` (FIFO, max 1 each per session)
- Wire scanners into `visible_runs.py` (on Jarvis' response text)
- Wire formatter into `prompt_contract.py` awareness block

### Phase 1.3 — TTL sweep + milestones
- `_ttl_sweep_open_predictions` — horizon parsing + grace + auto-uncertain
- ProducerSpec in `internal_cadence.py`
- `_compute_calibration_milestone` — count + threshold + first-contradiction + trend
- `format_world_model_milestone_for_awareness` (one per session)
- Resolve-path triggers milestone recompute (both tool path and TTL path)

### Phase 1.4 — Smoke + 30-day review

## Success criteria

1. **Tools callable:** Jarvis can call `predict_outcome` and `resolve_prediction`. Both validate args, return structured response with prediction_id (or error).
2. **Pattern scanners detect:** `extract_prediction_language("Jeg tror det her bliver godt")` returns at least one match with phrase + context.
3. **Nudges persist:** after Jarvis says "jeg tror", state_store contains a prediction-nudge with `rendered_at=""`.
4. **Awareness surfaces nudge:** next session's awareness includes the FIFO oldest unrendered nudge; mark rendered.
5. **TTL auto-uncertain:** prediction with `horizon="i dag"` not resolved within 24h grace → status=resolved, outcome=uncertain, resolved_via="ttl_auto".
6. **Milestones fire:** simulated 10 resolves → milestone "count_10" present in state. Simulated +7% trend → milestone "trend_improving".
7. **Surface gates correctly:** at most one nudge of each kind per session; at most one milestone per session.
8. **Backwards compat:**
   - Existing `record_runtime_world_model_prediction` / `resolve_runtime_world_model_prediction` signatures unchanged.
   - Existing 120-prediction cap respected.
   - Existing signal-tracking system untouched.
   - Eventbus family `world_model_signal` reused (no new family).
9. **Kill-switch:** `world_model_loop_enabled=False` → no nudges, no TTL sweep, no milestones; tools still functional as ledger.

## Risks & mitigations

- **Pattern false positives:** "jeg tror" appears in non-prediction context (*"jeg tror du har misforstået"*). *Mitigation:* nudges are suggestions, not auto-records. Jarvis ignores. 30-day review measures FP rate.
- **Pattern false negatives:** Jarvis predicts without trigger phrases. *Acceptable for Phase 1.* Tool covers explicit path; Phase 1.1 can add LLM-extraction.
- **Nudge spam:** many matches → many nudges. *Mitigation:* max 1 prediction-nudge + 1 resolution-nudge surfaced per session. State_store cap at 20 each (FIFO).
- **TTL too aggressive:** ambiguous horizons. *Mitigation:* conservative parsing — only "i dag", "i morgen", "denne uge", "inden [day]/EOD" parsed; everything else gets 7-day default grace.
- **Calibration bias at low N:** before 5 resolved, calibration is noise. *Mitigation:* first milestone (count_10) requires 10 resolved. Trend requires 20.
- **Trend over 10+10 requires 20 resolved:** slow signal. *Acceptable* — prefer reliable signal over noisy early data.
- **Calibration-consciousness risk:** Jarvis becomes risk-averse to protect his score. *Mitigation:* trend-feedback is invitation-shaped, not punitive. "Hvad har ændret sig?" is curiosity, not shame.
- **Embedding lookup for resolution-nudge candidate may fail in dev env (torch/CUDA issues):** *Mitigation:* if embedding fails, resolution-nudge persists without candidate_prediction_id; Jarvis manually picks prediction by recall.

## Out of scope (Phase 1.1 / Phase 2 / deferred)

- LLM-driven auto-extraction of implicit predictions (Phase 1.1)
- LLM-driven auto-resolution match (Phase 1.1)
- Per-domain calibration breakdown (Phase 1.1)
- Calibration as input to `unconscious_modulation` (Phase 2)
- Multi-step / conditional predictions
- Confidence-weighted calibration scoring (currently flat supported/total)
- Cross-Jarvis prediction sharing
- Pattern phrases auto-learned from Jarvis' usage

## 30-day review

Schedule eval at 2026-06-12:
- Count predictions Jarvis made via tool (explicit)
- Count nudges fired (auto-pattern-detected, both kinds)
- Count nudges Jarvis acted on (acted_on flag)
- Count resolutions by source (tool / nudge / ttl)
- Calibration over 30d (if N ≥ 10)
- Read a sample of predictions: meaningful or trivial?
- Read pattern matches: high false-positive rate?
- Decide: keep / tune phrases / Phase 1.1 LLM-extraction
- If predictions = 0 → tool design failed, nudges weren't enough; revisit
