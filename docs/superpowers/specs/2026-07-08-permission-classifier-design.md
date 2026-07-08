---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Harness Refactor Part E — LLM Permission-Classifier

**Date:** 2026-07-08
**Status:** Approved (design)
**Program:** Harness refactor (see `2026-07-08-harness-model-tiering-design.md` A/B/C/D/E map). A/Fase4/B/C shipped LIVE. E is the last core part before **D** (coercion-removal). Recovered from Jarvis' v1 spec Fase 5 (dropped in v2).

## Goal

Predict whether the **owner** would approve a **mutating** action, so the clearly-safe ones can eventually be auto-allowed and only the genuinely risky ones surfaced — reducing approval friction *without* weakening safety. Ships **shadow-first**: it predicts and measures its own accuracy (earned trust, like `model_trust`) but changes nothing until it proves itself and the owner flips it active.

## Ground truth (verified 2026-07-08)

- **Mutating actions that hit approval today:** writes (`write_file`, `operator_write_file`) and operator mutations (`operator_bash`, `operator_open_url`, `operator_launch_app`, `operator_kill_process`, `operator_record_audio`, `operator_browser_evaluate`).
- **Current approval decision** is static rule-based: an auto-approve path allowlist + blocked-pattern denylist ([simple_tools.py:596-628](../../../core/tools/simple_tools.py)); `_runtime_trust_all`/`force` bypasses approval; otherwise a tool returns `status="approval_needed"`.
- **Safety gates run first:** `commit_gate_arbiter.evaluate_commit_gates` (veto + decision, RED=blocked / YELLOW=soft_warn / GREEN=allow), governed per-gate via `gate_enforcement` kill-switches ([commit_gate_arbiter.py](../../../core/services/commit_gate_arbiter.py)).
- **Role/mode** enforced via ContextVars inside `execute_tool` (`effective_role`, `current_tool_scope`).
- **Earned-trust precedent:** `model_trust` (durable SQLite, per-key strength, fail-open) — E follows the same shape.

## Architecture

E is a **new advisory layer alongside** the existing gates — never a replacement. It is **subordinate**: it runs after the safety gates and can only ever *reduce* friction, never add blocking.

### Module `core/services/permission_classifier.py`

**Prediction:**
```
classify_action(tool: str, arguments: dict, ctx: dict) -> PermissionPrediction
# PermissionPrediction = {verdict: "approve"|"deny"|"uncertain", confidence: float, reason: str}
```
- Only called for **mutating** tools (a `_MUTATING_TOOLS` set matching the approval-hitting tools above). Read-only tools are never classified.
- **Cheap-lane LLM** call (`daemon_llm_call` / the cheap provider), short prompt: tool name + a redacted/clipped args summary + minimal `ctx` (role, mode, gate outcome). Predicts *"would the owner approve?"*.
- **Cached by `(tool, args_signature)`** — `args_signature = sha256(json.dumps({tool, arguments}, sort_keys=True))` — so repeat actions cost nothing and the verdict is deterministic within the cache TTL.
- Self-safe: any error → `{verdict: "uncertain", confidence: 0.0, reason: "classifier_error"}` (fail-open to normal approval).

**Earned trust (durable, per-tool):**
```
record_prediction_outcome(tool: str, *, predicted: str, actual: str, is_owner_gold: bool) -> None
classifier_trust(tool: str) -> str          # "untrusted" | "trusted"; fail-open "untrusted"
build_permission_classifier_surface() -> dict
```
- Durable SQLite table `permission_classifier_stats` (per-tool: correct/total, gold_correct/gold_total, streak, trust, last_updated) — **survives restart**.
- `actual` = the **dense bootstrap** (existing decision: allowlist auto-approve→`approve`, blocked/denied→`deny`) OR a **gold** owner approve/deny of a surfaced card (`is_owner_gold=True`, weighted much higher).
- **Trust earned** when a tool reaches `_TRUST_MIN_PREDICTIONS` (=50) with accuracy ≥ `_TRUST_MIN_ACCURACY` (=0.95) **and** zero unresolved **gold** misses. A single gold miss (predicted approve, owner denied — or vice-versa) resets that tool's streak to untrusted. Fail-open: unknown tool → `untrusted`.

**Active decision predicate (pure, built + tested, wiring deferred):**
```
should_auto_allow(tool: str, prediction: PermissionPrediction, *, gates_green: bool, role: str) -> bool
```
Returns True only when `gates_green and classifier_trust(tool)=="trusted" and prediction.verdict=="approve" and prediction.confidence>=_ACTIVE_MIN_CONFIDENCE and role=="owner"`. Not wired into `simple_tools` this round (see Behaviour by mode).

**Prediction stash (for gold lookup at resolution):**
```
stash_prediction(action_id: str, tool: str, predicted: str) -> None
pop_prediction(action_id: str) -> dict | None      # {tool, predicted} or None
```
Bounded map with TTL so an owner resolution minutes later can still match its prediction.

**Mode kill-switch:** `settings.extra["permission_classifier_mode"]` (+ env `JARVIS_PERMISSION_CLASSIFIER_MODE`), values `off | shadow | active`, **default `shadow`**. Same dual-read pattern as the Part B/C flags.

### Behaviour by mode

- **`off`:** classifier never runs. Byte-identical to today.
- **`shadow` (default) — the only flow wired this round:** for each mutating action, classify **non-blocking** (offloaded to a worker thread), stash the prediction by action-id (for later gold lookup), and record the **bootstrap** outcome (`approve` if the existing path auto-approved, `deny` if it blocked). **The approval flow is unchanged** — no auto-allow, no added latency, no behaviour change. Pure observability to build the per-tool track record.
- **`active` — decision logic built + tested this round, NOT wired into the approval path yet.** The pure predicate `should_auto_allow(tool, prediction, *, gates_green, role) -> bool` returns True **only when ALL hold:** `gates_green` (safety gates not blocked), `classifier_trust(tool) == "trusted"`, `verdict == "approve"` with `confidence >= _ACTIVE_MIN_CONFIDENCE` (=0.9), **and** `role == "owner"`. It is unit-tested in isolation. **Wiring it into `simple_tools`' real approval resolution is a deliberately separate follow-up (Part E-active),** taken only after per-tool track records justify it — so this round cannot change what runs without asking, no matter the flag. A `deny`/`uncertain` verdict will (when eventually wired) never block — it just falls through to the normal approval.

### Safety invariants (non-negotiable)

1. **Subordinate to the gates.** E is consulted only after `evaluate_commit_gates`. If a gate blocked the action, E is irrelevant. E can never override or soften a gate.
2. **Only reduces friction, never adds blocking.** Even in `active`, a `deny` prediction → fall back to the normal approval surface; E never auto-blocks (blocking is the gates' job).
3. **Owner-only auto-allow.** E auto-resolves only for `effective_role == "owner"`. A member/guest mutating action is never auto-approved by E — normal approval applies. For non-owner actors E is log-only.
4. **Shadow = zero flow change**, non-blocking classification.
5. **Fail-open throughout** — any error anywhere → normal approval path.

### Wire points (two — bootstrap + gold)

1. **Decision point** (`simple_tools`, where `approval_needed` is produced / auto-approve is decided): in **shadow**, spawn the non-blocking `classify_action`, stash the prediction keyed by action-id, and `record_prediction_outcome(is_owner_gold=False)` with the **bootstrap** actual (auto-approve→`approve`, blocked→`deny`). Does **not** touch the returned status.
2. **Approval-resolution point** (where an owner approve/deny of a *surfaced* card is processed — the visible-approval resolution path): look up the stashed prediction by action-id and `record_prediction_outcome(is_owner_gold=True)` comparing the prediction to the owner's actual decision. This is the **gold** signal; it fires only for actions that were genuinely surfaced and resolved by the owner. If no stashed prediction exists (classifier was off/missed), record nothing.

The prediction stash is a small bounded in-memory/durable map `action_id → {tool, predicted}` with TTL, so a resolution minutes later can still find its prediction. Both hooks are fail-open (any error → no record, normal flow).

## Cost / latency / cache

Cheap lane + `(tool, args_signature)` cache → most repeat actions are free. Shadow classification is offloaded to a worker so the approval path incurs **no** added latency. Non-determinism is bounded by the cache (same signature → same cached verdict within TTL).

## Central visibility

`/central/permission-classifier` (owner-only, mirrors `/central/model-trust`): per-tool prediction counts, accuracy, gold accuracy, trust state, current mode.

## Testing

`tests/test_permission_classifier.py`:
- `classify_action` shape; cache hit on repeat `(tool, args)`; classifier error → `uncertain`/fail-open.
- `record_prediction_outcome` + `classifier_trust`: earns `trusted` at ≥50 preds & ≥0.95 accuracy & no gold miss; a gold miss resets to `untrusted`; unknown tool → `untrusted`.
- Mode helper defaults `shadow`; env override wins.
- **Subordination:** a gate-blocked action → E not consulted / never flips a block (test the wiring guard).
- **Role gating:** non-owner + active + trusted + approve → still NOT auto-allowed.
- **Active gate:** auto-allow only when gates-green ∧ trusted ∧ approve ∧ confidence≥0.9 ∧ owner; any missing condition → normal approval.
- New `core/…` files need matching `tests/test_<stem>.py` (coverage gate).

## Files

- **New:** `core/services/permission_classifier.py` (classify_action, record_prediction_outcome, classifier_trust, should_auto_allow, stash/pop_prediction, mode helper, build surface) + `tests/test_permission_classifier.py`.
- **New:** `@router.get("/permission-classifier")` in `apps/api/jarvis_api/routes/central_matrix.py` (mirror `/model-trust`).
- **Modify:** `core/tools/simple_tools.py` — **hook 1** at the approval decision (shadow: non-blocking classify + stash + bootstrap record). Inline, minimal, fail-open.
- **Modify:** `resolve_pending_approval(item_id, approved=...)` (called from [cowork.py:53](../../../apps/api/jarvis_api/routes/cowork.py), the owner approve/deny path backed by `tool_intent_approval_requests`) — **hook 2**: `pop_prediction(item_id)` + gold `record_prediction_outcome(is_owner_gold=True)`. Fail-open. Exact module of `resolve_pending_approval` confirmed during planning.

**Verified dependencies:** cheap-lane `daemon_llm_call` ([daemon_llm.py:129](../../../core/services/daemon_llm.py)); owner-resolution `resolve_pending_approval` ([cowork.py:53](../../../apps/api/jarvis_api/routes/cowork.py)).

## Deploy

Env `conda activate ai`; full-suite gate ~20 min; deploy = ff-pull + restart `jarvis-runtime` & `jarvis-api` on `bs@10.0.0.39`. Ships `shadow` → zero behaviour change; per-tool track record accrues durably; owner flips `active` per tool-confidence later (like `model_trust`).
