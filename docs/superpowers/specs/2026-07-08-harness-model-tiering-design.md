---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Spec — Harness Refactor, Part 1: Central-Governed Earned Model-Trust + Instruction/Config

**Date:** 2026-07-08
**Status:** DESIGN (approved by Bjørn)
**Authors:** Jarvis (original harness spec) + Bjørn + Claude (model-tiering + source-grounding)
**Program context:** This is the FIRST of a multi-part harness refactor "from rigid coercion to
instructive trust" (Jarvis' verified research + Claude's source-check of the Claude Code leak
[dbreunig, superframeworks] and Codex agent loop [bytebytego]). Later parts get their own
spec→plan cycles: **B** context/tool-result management (incl. the `__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__`
cache marker, §4.3), **C** tool concurrency, **D** gate-repurpose + coercion-removal, **E** LLM
permission classifier (predict-if-owner-would-approve a mutating action → auto-allow safe, surface
risky; from Jarvis' v1-spec Fase 5, dropped in his v2 — recovered here so it isn't lost;
`classify_action(tool, args, ctx)`). Jarvis' "Fase 4" (pre/post-tool → metacognition) already shipped
today as the **reasoning-interceptor** (shadow).

**Adjacent items noted (NOT this program, recorded so nothing from the original wish is forgotten):**
v1 §6 7-step parallel/deferred bootstrap pipeline (startup-perf, separate concern); v1 §7 four
sub-agent types with own context windows (ties to the known agent-council-locked issue — agent-system
work); v1 §4 four persistent-memory types + v1 §9 CLAUDE.md-per-turn (we already have SOUL/IDENTITY +
workspace memory — a possible taxonomy refinement, not core).

## 1. Problem

Our harness has 7 coercion mechanisms in `visible_runs.py` (verified: `_AGENTIC_MAX_ROUNDS=100`@1962,
`_MAX_EMPTY_TEXT_ROUNDS=3`@2094, `_MAX_TOOL_ONLY_ROUNDS=4`@2140, `_SYNTH_PAUSE_AFTER=8`@2150,
`_MAX_NO_PROGRESS=2`@2157, hollow_promise@2143/3241, loop_nudge@3396) used to *force* the model to
stop tool-only loops. Claude Code and Codex have **none** of these — they trust the model to decide
when it's done, and the harness only handles execution/permissions/compaction. But **their model is
Claude / o3.** Our lane is deepseek/kimi/glm/ollama/copilot — models that genuinely degenerate
(kimi looping "jeg kører nu 🎯" with no tool call is why hollow_promise_guard exists).

So "trust the model like Claude Code does" is only safe **per model, once that model has proven it
self-regulates.** And the prompt is missing the instruction that would let a capable model stop on
its own (no synthesis/"you're done"/conciseness guidance), while compaction fires too early on
large-window lanes (192k flat = ~19% of a 1M window).

## 2. Goals / non-goals

**Goals (this spec):**
- **Foundation:** a Central-governed, *earned* per-model trust status (`weak` → `strong`), auto-
  promoted on evidence, auto-reverted on regression, no owner babysitting.
- **Sub-project A** (reads the foundation):
  - Add the missing **synthesis/"you're done"** instruction (all models) + **conciseness**
    (strong only).
  - Make the compaction threshold **model-window-aware**.
  - Adopt an explicit **cache-boundary marker** (scope-assessed below).

**Non-goals (later parts):** tool-result aging/micro-compact (B), transparent-compaction UI (B),
concurrent/serialized tools (C), repurposing gates + removing the 7 mechanisms (D). This spec
**changes none of the 7 mechanisms** — it only builds the trust signal they'll later read.

## 3. Foundation — Central-governed earned model-trust

### 3.1 States & default
Every model is **weak** until it earns **strong**. `weak` = today's behavior unchanged (all safety
nets, coercion active, no conciseness caps). Unknown/new model → **weak** (conservative).

### 3.2 Degeneration signal (evidence)
A *run* is **clean** if it produced **none** of these degeneration events; **any one** makes it a
degeneration run. All already exist as Central nerves / loop state:
- `loop/no_progress_finalize` (visible_runs.py:3628)
- `stream/cutoff_at_loop_lag` (visible_runs.py:4144/4840)
- `loop/empty_completion` (empty-completion nerve)
- hollow-promise fired (hollow_promise_guard)
- tool-only cap hit (`_MAX_TOOL_ONLY_ROUNDS` reached) / synth-pause forced

The interceptor/loop already emits these; the tracker **subscribes/reads**, it does not add new
detection.

### 3.3 Earn / revert (the mechanism)
- Per-model durable record (survives restart, like `gate_verdict_ledger`): `{model, clean_streak,
  strength, last_degeneration_at, promoted_at}`.
- On run end, the Central records the run as clean or degeneration for `run.model`.
- **Auto-promote:** `clean_streak >= _PROMOTE_THRESHOLD` (start 20) → `strength = strong`,
  `promoted_at = now`. No owner step. Emits a Central event (observable).
- **Auto-revert:** a degeneration run on a `strong` model → `strength = weak`, `clean_streak = 0`,
  `last_degeneration_at = now`. Instant. Emits a Central event.
- **Owner override (optional):** a flag `model_trust_pin.<model> = strong|weak|auto` (default
  `auto`). Owner *can* pin, never *must*. Read before the earned status.

### 3.4 Reader + surface
- `model_strength(model: str) -> "strong" | "weak"` — reads pin, else earned status, **fails open to
  `weak`**. This is the single downstream reader.
- `/central/model-trust` (Central-CLI): per model {strength, clean_streak, threshold,
  last_degeneration, promoted_at, pin}.
- New module `core/services/model_trust.py` (record_run_outcome, model_strength, build surface) +
  a `model_trust` table (or runtime-state key). Registered to record on run completion in
  `visible_runs.py` (one guarded call at run finalize).

### 3.5 Governance
This is the Central autonomously changing the harness's own trust posture — but conservatively:
default weak, high clean-streak threshold, **single-event auto-revert**, fully observable, owner-
overridable. It is lower-stakes and reversible (unlike the Keymaker decentralization keys, which
stay owner-gated). Consistent with "the Central carries what the owner shouldn't have to remember."

## 4. Sub-project A — what strong vs weak changes

### 4.1 Prompt instruction (`prompt_contract.py`)
There are TWO existing output-discipline sources this must harmonize with, not orphan or duplicate:
- `_visible_capability_truth_instruction`@3489 — "CALL the tool, never simulate" (tool-honesty).
- the self-correction instruction@3275-3291 (English compact + Danish full) — the **anti-confabulation
  anchor**: *"verify before you say done (read the file, ran the test); ALWAYS CHECK 'status' —
  approval_needed/error means it did NOT happen; admit failures openly; ask if unsure; MEMORY-FIRST."*

**These stay, verbatim, for ALL tiers.** The self-correction discipline is precisely what weak lanes
need most (they confabulate + hide failures), so it is universal — untouched by this spec.

The refactor adds one new tiered block, `_output_discipline_instruction(*, strength: str) -> str`,
composed *coherently alongside* the above (no repetition of "check status"):
- **Both tiers** — the missing "synthesize & stop" guidance (safe for weak; it helps them *stop*):
  - "After each tool result, consider: do I have enough to answer? If yes, synthesize your findings
    and respond directly — do not keep calling tools when you already have the answer."
  - "Finish your sentence with punctuation before a tool call — never cut off mid-word."
  - "Tool results are for you — refer to them in your own words, never reproduce them verbatim."
- **Strong tier only** — conciseness (from Claude Code; would truncate weak lanes):
  - "Go straight to the point. Try the simplest approach first without going in circles. Do not
    overdo it."
  - "Keep text between tool calls to ≤25 words. Keep final responses to ≤100 words unless the task
    genuinely requires more."
- Wired into the visible prompt build next to the existing two blocks; `strength =
  model_strength(run.model)`. The compact (Ollama) variant keeps its trimmed self-correction as today.

**Net picture per tier:** weak = tool-honesty + self-correction + synthesize/stop (all safety);
strong = the same + conciseness caps. Nothing is removed; conciseness is the only strong-exclusive add.

### 4.2 Model-window-aware compaction threshold (`settings.py` + `core/context/auto_compact.py`)
- Today: `auto_compact` triggers at `context_run_compact_threshold_tokens (240k) × 0.80 = 192k`
  (auto_compact.py:24) — flat, model-blind.
- New: `threshold = model_window × _AUTO_COMPACT_WINDOW_PCT` where `model_window` comes from the
  existing `core/services/model_context.py` / `context_window_manager.py`, and
  `_AUTO_COMPACT_WINDOW_PCT` starts at 0.70. So a 1M-window lane compacts at ~700k, a 128k lane at
  ~90k — each proportional to its *own* window, instead of one flat 192k that's ~19% of a 1M window
  but ~150% of a 128k window. **Fail-safe:** unknown/unresolvable window → keep the current flat
  `context_run_compact_threshold_tokens × 0.80` behavior unchanged (the flat value becomes the
  *fallback*, not a cap).
- Not model-strength-tiered (it's window-aware, applies to all).

### 4.3 Cache-boundary marker — SCOPE DECISION
Adopting `__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__` (static-before-dynamic ordering + an invisible marker)
is structurally invasive to prompt assembly. **Decision: defer to Sub-project B** (context/prompt-
assembly), NOT this spec. Rationale: A is meant to be the *safe immediate win* (instruction +
config, reversible, no shadow); reordering the prompt-assembly + inserting a cache boundary is a
prompt-structure change that deserves its own shadow-gated verification alongside the tool-result
aging (which also restructures the prompt). Keeping A small keeps it safe. Noted here so it isn't
lost.

## 5. Error handling
`model_strength` → weak on any failure. Threshold → current flat on unknown window. Trust recording
self-safe (a failure to record must never affect a run). Instruction assembly self-safe (falls back
to today's instruction on failure).

## 6. Testing
- `model_trust`: clean run increments streak; degeneration run resets + reverts a strong model;
  promote at threshold; pin overrides earned; `model_strength` fails open to weak.
- Instruction: strong output contains the ≤25/≤100 conciseness lines; weak output contains synthesis
  but NOT the word-caps; **both tiers still carry the self-correction anti-confabulation text**
  (verify-before-done / check-'status') and the "synthesize & stop" guidance.
- Threshold: 1M window → ~700k; 128k window → ~90k; unknown → flat 192k.
- Full-suite gate.

## 7. File structure
- `core/services/model_trust.py` (new) — earned-trust mechanism + `model_strength` + surface.
- `core/runtime/db_*.py` or runtime-state — durable per-model record.
- `core/services/prompt_contract.py` — `_output_discipline_instruction` + wire at 3489.
- `core/runtime/settings.py` + `core/context/auto_compact.py` — model-window threshold.
- `apps/api/jarvis_api/routes/central_matrix.py` + catalog — `/central/model-trust`.
- `core/services/visible_runs.py` — one guarded `record_run_outcome` call at run finalize.
- Tests per module.

## 8. What it gives
The Central earns each model's trust from evidence and revokes it instantly on regression — so Bjørn
never classifies a model manually, strong lanes get Claude-Code-style instructive trust + conciseness,
weak lanes keep their safety nets, and the later coercion-removal (Sub-project D) has a *per-model,
evidence-based* signal to gate on. Nothing about the 7 mechanisms changes yet — this builds the
trust they'll read.
