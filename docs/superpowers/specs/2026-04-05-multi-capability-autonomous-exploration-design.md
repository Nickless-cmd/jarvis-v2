# Multi-Capability Autonomous Exploration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Jarvis capable of autonomous multi-file exploration in a single turn instead of asking permission for every read.

**Problem:** Five interacting constraints create a "ask-and-wait" loop where Jarvis never acts autonomously on read-only operations. Users must babysit every file read.

---

## Root Causes

| # | Cause | Location | Effect |
|---|-------|----------|--------|
| 1 | Only 1 capability executed per turn | `visible_runs.py:1284-1294` | Cannot explore freely |
| 2 | "No surrounding prose" with capability tags | `prompt_contract.py:1218` | Model chooses prose over action |
| 3 | User message must contain explicit path | `prompt_contract.py:1233,1241` | Blocks tool use unless user provides exact syntax |
| 4 | Self-deception guard blocks read action claims | `self_deception_guard.py:161-199` | Model afraid to claim it did anything |
| 5 | Second-pass forbids further exploration | `visible_runs.py:1494-1500` | No continuation after one capability |

---

## Change 1: Multi-Capability Execution

### Current flow

```
LLM pass 1 → parse tags → execute FIRST only → LLM pass 2 (prose only, no tools)
```

### New flow

```
LLM pass 1 → parse ALL tags → execute ALL sequentially → LLM pass 2 (grounded in all results)
```

### Design

**`_extract_capability_plan()`** (`visible_runs.py:1250-1303`):
- Add new key `"all_capabilities"`: a list of `{"capability_id": str, "arguments": dict}` for every known capability found in the response.
- `"selected_capability_id"` remains for backwards-compat, set to the first entry.
- Deduplication: skip duplicate capability IDs (same as current `seen` set behavior).
- Preserve `"multiple": len(all_capabilities) > 1` for observability.

**Execution loop** (`visible_runs.py:501-670`):
- Replace single-invocation with a `for` loop over `all_capabilities`.
- Each invocation calls `invoke_workspace_capability()` independently.
- Collect results into `capability_results: list[dict]`, each containing capability_id, status, execution_mode, result text, and detail.
- **Hard cap: 5 capabilities per turn.** If the LLM emits more than 5, execute the first 5 and note the rest as skipped in the trace.
- If any capability fails, continue executing the rest. Failures are recorded individually.

**Streaming:** No changes needed. `_CapabilityMarkupBuffer` already swallows all capability tags during streaming, regardless of count.

**Observability:** The execution trace already records `"capability_ids"` and `"multiple"`. Add `"capabilities_executed": int` and `"capabilities_skipped": int`.

---

## Change 2: Second-Pass Encourages Continuation

### Current second-pass prompt

```
Second-pass visible response task.
You have already completed one bounded capability invocation for the current user turn.
Respond to the user in ordinary prose only.
Do not emit any <capability-call ... /> tags.
Do not invoke another capability.
Do not describe hidden orchestration; just answer grounded in the result below.
```

### New second-pass prompt

```
Second-pass visible response task.
You executed {N} capabilities this turn. Results are below.

Respond to the user grounded in these results.
Do not emit any <capability-call ... /> tags in this response.

If the results fully answer the user's question, answer directly.
If you need more data to fully answer, tell the user what you would read next
so they can ask you to continue.
```

Key changes:
- Remove "Do not invoke another capability" (redundant with no-tags rule).
- Remove "Do not describe hidden orchestration" (it prevented useful transparency).
- Add explicit guidance to suggest next reads if results are insufficient.
- Include all N capability results, not just one.

### Result formatting

Each capability result is appended as:

```
--- Capability {i+1}: {capability_id} ---
Status: {status}
Execution mode: {execution_mode}
Result:
{result_text or detail}
```

---

## Change 3: Remove "No Surrounding Prose" Rule

### Current rule (`prompt_contract.py:1218`)

```
If you invoke a capability, emit exactly one capability-call line and no surrounding prose.
```

### New rule

```
When you invoke capabilities, emit the capability-call tags together.
You may include a brief sentence before or after the tags explaining what you are doing,
but keep it short — the capability results will speak for themselves.
```

### Location

`_visible_capability_truth_instruction()` in `prompt_contract.py`, line 1218. Replace the single line.

The parallel guidance in `_visible_capability_id_summary()` (lines 1311-1314) is unchanged — it already encourages multiple tags.

---

## Change 4: Relax Path Requirement for Read-Only Operations

### Current rules (`prompt_contract.py:1233,1241`)

```
Dynamic external file read is allowed only when the user message already names
one explicit /absolute/or ~/path outside the workspace root.
```

```
Non-destructive exec is allowed only when the user message already includes
one explicit command in backticks or a command:/kommando: line.
```

### New rules

For file reads and directory listings:
```
Dynamic external file read and directory listing can use paths from:
(1) the user's current message,
(2) results from previous capability calls in this turn,
(3) well-known paths (PROJECT_ROOT, workspace root, home directory).
You do not need the user to spell out every path — if you know the path from context, use it.
```

For commands:
```
Non-destructive exec is allowed when the user's intent is clear.
You do not need the command in backticks — infer the appropriate read-only command from context.
```

### Safety

- Only read-only operations are relaxed. Write/mutation/sudo remains approval-gated.
- The runtime capability system already enforces read-only classification (`workspace_capabilities.py` approval policy). This change only affects the LLM's *willingness* to call the capability, not the runtime's *permission* to execute it.

---

## Change 5: Scope Self-Deception Guard to Writes/Mutations

### Rule 3: "Capabilities are approval-gated" (`self_deception_guard.py:189-199`)

**Current condition:** `has_gated and not has_active`

**Problem:** This fires even when callable read-only capabilities exist, because `has_active` checks a different signal than `has_callable`.

**Fix:** Add `has_callable` check from capability truth. Guard fires only when `has_gated and not has_callable` — i.e., when there are genuinely no callable capabilities at all.

**Implementation:**
- In `evaluate_self_deception_guard()`, extract callable count from `capability_truth`:
  ```python
  callable_count = len([
      c for c in (capability_truth or {}).get("runtime_capabilities", [])
      if c.get("available_now")
  ])
  has_callable = callable_count > 0
  ```
- Change condition from `has_gated and not has_active` to `has_gated and not has_callable`.

### Rule 1: "Do NOT claim you have executed" (`self_deception_guard.py:161-172`)

**Current text:**
```
Do NOT claim you have executed, performed, created, or completed external actions.
Internal continuation and quiet initiative are NOT execution evidence.
State only observed runtime facts.
```

**New text:**
```
Do NOT claim you have executed write or mutating actions unless runtime confirms.
Read-only capability results are factual — you may reference them directly.
Internal continuation and quiet initiative are NOT execution evidence for writes.
```

This scopes the guard to writes/mutations while letting Jarvis freely reference what it actually read.

---

## Files Modified

| File | Changes |
|------|---------|
| `apps/api/jarvis_api/services/visible_runs.py` | Multi-cap extraction, execution loop, second-pass prompt, result formatting |
| `apps/api/jarvis_api/services/prompt_contract.py` | Remove prose-ban (line 1218), relax path rules (lines 1233,1241) |
| `apps/api/jarvis_api/services/self_deception_guard.py` | Scope Rule 1 and Rule 3 to writes/mutations |
| `tests/test_visible_runs.py` | Tests for multi-cap extraction and execution |
| `tests/test_prompt_contract.py` | Tests for updated prompt rules |
| `tests/test_self_deception_guard.py` | Tests for scoped guard behavior |

---

## Testing Strategy

1. **Multi-cap extraction:** Test that `_extract_capability_plan` returns all capabilities, not just the first. Test dedup. Test cap at 5.
2. **Multi-cap execution:** Test that the execution loop runs all capabilities and collects all results. Test that failure in one doesn't block others.
3. **Second-pass prompt:** Test that the prompt includes all results and encourages continuation.
4. **Prose rule:** Test that the prompt no longer contains "no surrounding prose".
5. **Path rule:** Test that the prompt allows context-inferred paths.
6. **Self-deception guard:** Test that Rule 1 and Rule 3 don't fire when callable read-only capabilities exist.
7. **Streaming:** Verify `_CapabilityMarkupBuffer` still swallows all tags when multiple are present (should already work).
8. **Integration:** End-to-end test with LLM emitting 3 capability tags — verify all 3 execute and results appear in second-pass.

---

## Non-Goals

- **Recursive turn-chaining** (Tilgang B): Not implemented. Jarvis can suggest next reads, but the user initiates the next turn.
- **Write/mutation relaxation:** All write operations remain approval-gated. Only read-only operations are affected.
- **SOUL.md changes:** "Restraint" stays as a core value. The prompt changes are sufficient to counteract over-caution for reads without changing identity.
- **TOOLS.md truncation fix:** Already mitigated in previous session by putting rules in `_visible_capability_id_summary()`. No further changes needed.
