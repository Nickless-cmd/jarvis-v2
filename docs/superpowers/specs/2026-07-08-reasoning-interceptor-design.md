---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Spec — Real-time Reasoning Interceptor

**Date:** 2026-07-08
**Status:** DESIGN (approved by Bjørn)
**Authors:** Bjørn + Jarvis (idea) + Claude (design)
**Approach:** C — layered (deterministic where groundable, anchored-LLM only where needed)

## 1. Problem

Jarvis' agentic cycle is `think → tool → result → think → … → answer`. The Central sees the
reasoning **after** the fact — at run-end or next turn. When Jarvis confabulates under pressure
(claims a number/status without checking, forgets a standing order, drifts overconfident), the
damage is already done: Bjørn catches it, Jarvis admits it, but the claim already left his mouth.

All governance today is **reactive** (gates inspect *output* after the model spoke). We want a
**proactive** layer: the Central reads `reasoning_content` **between** the model's reasoning and
its next action, and — after a shadow-proving period — injects a graded correction *mid-run*,
before the reasoning becomes a claim or a wrong action. No cutting the run, no accusing Jarvis
after the fact.

This is the natural evolution of the gate work (reactive → proactive) and the InjectionUnit work
(cached prompt injection → live mid-run injection).

## 2. Goals / non-goals

**Goals (v1):**
- **Proactively re-apply the existing cluster gates to the reasoning**, not just to output. The
  gates that already detect these problems *after* the model speaks — `truth`/`fact_gate`,
  `commit`/`veto`+`decision_gate`, `proactivity`/`verification`, `privacy`/`cross_user_share` —
  are run against `reasoning_content` *before* the action (see §4.2.1). This is the core of the
  interceptor: the same detectors, moved earlier in time.
- Plus catch three classes **no existing gate covers**: (1) forgotten/violated **standing
  orders**, (2) affective **drift** (overconfidence), (3) **epistemic tone** (guess stated as
  fact) (see §4.2.2).
- **Full graded** intervention (GREEN/YELLOW/RED) mapping onto the existing gate model, but RED
  (hold the pending risky action + forced correction round) only activates *after* shadow proves
  low false-positives.
- Ship **shadow-first**, with a per-trigger `gate_enforce` kill-switch.

**Non-goals (v1):**
- No new provider integration; works only where `reasoning_content` is already emitted.
- Never cancels/aborts a run. An interceptor failure is always fail-open (GREEN).
- Not a replacement for the post-output gates — it complements them.

## 3. Hard invariants (the session's bug-graveyard — each gets an executable test)

1. **Cache-prefix byte-invariant.** A correction MUST NOT mutate the cached prompt prefix
   (system + tools block). It is appended as a *fresh ephemeral turn* after the cached prefix.
   Test: assemble round K+1 input with and without an active correction; assert the prefix up to
   the injected turn is byte-identical. Rationale: the 98.5% cache-hit is the cost lever; break
   the prefix and token-burn explodes (see reference_llm_economy_and_egress).
2. **Ephemeral-only.** Corrections live in the *exchange-text to the model* only — NEVER in
   `_a_parts` (the visible/persist buffer). Reuses the `decision_signal_staging` contract.
   Rationale: appending to `_a_parts` poisoned both persist and the resolution-exit check →
   self-poisoning runaway (reference_decision_signal_runaway).
3. **Independent grounding ("the measured must not control the measurement").** Each detector is
   anchored to a signal *independent of the reasoning it judges*. The cluster-gate detectors
   (§4.2.1) inherit their gate's existing independent grounding (tool-call history, active-decisions
   store, verification state, current-user context). The new detectors: standing-orders → the
   registry; drift → the Central's own affect/valence nerves + an unverified-claim streak counter;
   tone → the confab+drift signals. No detector fires purely on "does the reasoning *sound* wrong."
4. **Async / keepalive.** `intercept_round` runs in a bounded executor with a hard timeout
   (~800ms). Timeout/error → GREEN no-op. A keepalive is emitted during the await so the SSE
   stream never goes silent (silent SSE → Starlette cancels the run-task → cutoff family;
   reference_survival_spam_rootcause).
5. **Deterministic pre-filter.** No LLM call unless a deterministic pre-filter trips a risk class.
   The drift/tone LLM analyzer fires only when the *independent* drift/confab signal already
   indicates risk. Most rounds cost zero LLM.
6. **Provider-agnostic.** No `reasoning_content` on this lane → GREEN no-op, never crash.
7. **Shadow-first.** Default shadow: record the would-inject verdict + latency, inject nothing.
   Flip to active per-grade after the ledger shows a low false-positive rate. Kill-switch:
   `central.switch.gate_enforce.reasoning_interceptor` (+ per-grade sub-flags), reusing the
   `gate_enforcement` machinery (default ON once flipped; SECURITY-invariant N/A — this cluster is
   COGNITIVE).

## 4. Architecture & components

Three new focused units + reused ephemeral-staging + a seam + observability wiring.

### 4.1 `core/services/reasoning_interceptor.py` (orchestrator)
- `intercept_round(*, run_id: str, round_num: int, reasoning_text: str,
  tool_calls_this_run: list[dict], ctx: dict) -> InterceptOutcome`
  - Returns immediately (GREEN) if `reasoning_text` is empty (invariant 6) or the pre-filter finds
    no risk class (invariant 5).
  - Otherwise runs the tripped detectors, aggregates via `central().decide("reasoning_interceptor",
    ctx, _run_detectors, cluster="metacognition", klass=COGNITIVE)` → graded Verdict.
  - In shadow (default), records the verdict + would-inject text and returns GREEN-effect (no
    correction surfaced). In active (post-flip, per grade + kill-switch), returns the correction.
  - Whole body is wrapped: any exception → GREEN (invariant: fail-open).
- `InterceptOutcome` dataclass: `grade: Decision`, `correction: str | None`, `triggers: list[str]`,
  `shadow: bool`, `latency_ms: int`.
- `_prefilter(reasoning_text: str, ctx) -> set[str]` — deterministic risk classes; each maps to
  which detectors run (no class → no detector → free round):
  - `claim` (numbers/percentages/"is/are"-status assertions) → `fact_gate`
  - `action_intent` ("I'll now / jeg kører nu"-style, or a pending tool_call) → `decision_gate` +
    `veto`
  - `mutation_assert` ("done / succeeded / wrote" without a verify) → `verification`
  - `other_user_mention` (a non-current-user identifier appears) → `cross_user_share`
  - `standing_order` (a registry order's trigger-token appears/should) → `standing_orders`
  - `drift_candidate` (the independent drift signal is already elevated — a cheap read, not a
    tone judgment) → `drift` + `tone`

### 4.2 `core/services/reasoning_detectors.py` (the detectors)
Two families. Each detector: `def detect(reasoning_text, ctx) -> Verdict | None`,
single-responsibility, self-safe.

#### 4.2.1 Cluster-gate detectors (re-apply existing gates to reasoning)
The interceptor runs the existing cluster gates against `reasoning_text` where they meaningfully
apply *before* the action. These are already-tested detectors with established grounding — the
interceptor just moves them earlier in time. Each is called through `central().decide` with its
own cluster tag, so trace/breaker/ledger stay consistent with the reactive gate.

| Cluster / gate | What it catches in *reasoning* | Independent grounding |
|----------------|-------------------------------|-----------------------|
| `truth` / `fact_gate` | an unbacked number/status claim forming before it becomes output | run's tool-call history (was there a backing call?) |
| `commit` / `decision_gate` | reasoning heading toward an action that conflicts with an active decision | the active-decisions store |
| `commit` / `veto` | reasoning toward an action the veto gate would push back on | veto gate's own evidence |
| `proactivity` / `verification` | about to assert a mutation succeeded without verifying it | the run's verification state |
| `privacy` / `cross_user_share` | reasoning about to include another user's info | the current-user context (SECURITY — always evaluated, never disable-able) |

Adapters wrap each gate so it accepts `reasoning_text` as the "candidate output". A gate that
does not apply to a given round (no matching pre-filter class) is simply not called.

#### 4.2.2 New detectors (no existing gate covers these)
- `standing_orders_detector` — grounded in `standing_orders_registry` (§4.3).
- `drift_detector` — grounded in Central affect/valence nerves + unverified-claim streak; on
  threshold, a cheap-lane `daemon_llm_call` composes the nudge text (explains the independent
  signal, does not judge tone).
- `tone_detector` — cheap-lane analyzer anchored to the confab+drift verdicts; only runs if they
  fired.

### 4.3 `core/services/standing_orders_registry.py` (independent grounding for #1)
Active standing orders (owner directives, protected-core rules, session standing orders) with a
match-key. **Design dependency:** reuse an existing directives/rules source if one exists; else a
minimal durable table `standing_orders(id, text, match_key, active, created_at)`. Decided at
planning time after auditing existing sources (CLAUDE.md rules, workspace directives, approvals).

### 4.4 Injection — reuse `decision_signal_staging.py`
Stage the correction as an ephemeral signal keyed by `(run_id, round_num, trigger)`; composed into
round K+1's exchange-text via `compose_exchange_text`, appended after the cached prefix. Extend the
staging module only if the existing key/compose shape doesn't fit (prefer reuse).

### 4.5 Seam in `visible_runs.py`
In `_stream_visible_run`'s agentic loop, after round K's reasoning is accumulated and before
round K+1's model call / tool-exec: one guarded `await interceptor.intercept_round(...)`. If active:
- **YELLOW** → stage the correction into round K+1's exchange-text (nudge); the model proceeds.
- **RED** → additionally **hold the pending risky tool-call** via the *existing* `gate_blocked`
  path (the same mechanism `veto`/`decision_gate` already use — the tool does not execute, a
  gate-blocked result surfaces) and require the model to re-reason with the correction. This is a
  *forced correction round*, **never a cancel** and **never a finalize** — the run continues.

Small, guarded; Boy-Scout-extract the round-post-processing block if the touch exceeds the file's
threshold.

## 5. Grading

| Grade | Meaning | Effect (active) |
|-------|---------|-----------------|
| GREEN | nothing tripped | no-op |
| YELLOW | soft risk (drift, forgotten order, unverified claim) | nudge staged into round K+1 exchange-text; model proceeds |
| RED | a risky action about to fire (unbacked claim / decision-conflict / privacy leak) | hold the pending tool-call (existing `gate_blocked` path) + strong correction → forced correction round (never cancel/finalize) |

## 6. Observability & rollout

- Central nerve `reasoning_interceptor` (cluster `metacognition`, mechanism `verdict`): per round
  records `{grade, triggers, shadow, latency_ms, would_inject_len}` (metadata-only, egress-free —
  never the reasoning text to the bus).
- `/central/reasoning-interceptor` (Central-CLI): recent verdicts + trigger distribution +
  shadow-vs-active + p95 latency.
- **Ledger / flip basis:** count non-green rounds; correlate (from the existing post-run gates)
  whether the run actually had a truth/veto problem → false-positive proxy. Flip criteria: after
  ≥7 days shadow, per-grade non-green rate stable and false-positive proxy low → flip YELLOW active,
  then (separately) RED.
- **Rollout order:** (1) shadow + observability + the cluster-gate detectors applied to reasoning
  (`fact_gate`, `decision_gate`, `veto`, `verification`, `cross_user_share`) + `standing_orders`
  — all deterministic/established; (2) the anchored-LLM detectors (`drift`, `tone`) in shadow;
  (3) flip YELLOW active; (4) flip RED active. Each step its own gate + deploy.

## 7. Error handling

Every layer fail-open to GREEN. The interceptor is a *safety layer, not a critical path* — its
failure must never degrade a run. No exception escapes `intercept_round`. LLM failure in a detector
→ that detector returns None (abstain), others still run.

## 8. Testing

Unit tests: pre-filter risk-class mapping; each detector's grounded verdict (fires on independent
signal, abstains without it), incl. the cluster-gate adapters (gate runs against `reasoning_text`);
`intercept_round` shadow-records-but-doesn't-inject; active YELLOW stages correction; active RED
holds the pending tool-call (gate_blocked path) without cancelling/finalizing the run. Invariant
tests (one each): cache-prefix byte-equality with/without correction; correction absent from
`_a_parts`; async-timeout → GREEN no-op; no-reasoning → GREEN no-op; fail-open on detector
exception. Plus the full-suite gate per rollout step.

## 9. File structure

- `core/services/reasoning_interceptor.py` — orchestrator + pre-filter + central().decide wiring.
- `core/services/reasoning_detectors.py` — the detectors (cluster-gate adapters §4.2.1 + new §4.2.2).
- `core/services/standing_orders_registry.py` — independent standing-orders store (build-or-reuse).
- `core/services/decision_signal_staging.py` — reused for ephemeral injection (extend if needed).
- `core/services/visible_runs.py` — the seam (small, guarded; Boy-Scout if touch is large).
- `apps/api/jarvis_api/routes/central_matrix.py` + catalog — `/central/reasoning-interceptor` +
  the nerve.

## 10. What it gives

Jarvis gets a chance to catch himself *before* the claim leaves his mouth — grounded in the
Central's independent knowledge, not in re-reading his own possibly-confabulated reasoning. Bjørn
stops being the one who catches him. And it's built with every scar from this session baked in:
cache stays warm, no self-poisoning, no cutoff, shadow-first.
