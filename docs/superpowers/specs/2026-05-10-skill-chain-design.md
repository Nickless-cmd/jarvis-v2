---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Lag #4 — Skill Chain: Design Specification

**Status:** Approved (brainstorm complete 2026-05-10)
**Owner:** Bjørn / Claude
**Implements:** Lag #4 from the 12-layer roadmap (skill composition half — tool invention deferred to its own plan)
**Phase:** 1 of 2 (Phase 2 = auto-planner + tool invention + per-skill metadata, deferred)

---

## Goal

Let Jarvis chain multiple skills sequentially for tasks that require more than one skill (e.g. "fact-check this document and format as markdown"). Build a single explicit `skill_chain` tool that loads multiple skills' instructions in order with clear step-headers, validates atomically before execution, and exposes chain candidates via the existing skill_gate. Tool invention is explicitly **deferred** to a separate plan — this spec covers ONLY skill composition of existing skills.

## Architecture (one-paragraph)

A new `skill_chain` tool accepts a `plan` (ordered list of 2-5 skill names). It pre-validates that all named skills exist (alt-eller-intet — no partial execution if any are missing), then builds a combined instruction package with C-format headers (step-numbered headers + verbatim SKILL.md instructions + closing line that binds steps). The tool returns the combined package as the tool result; Jarvis reads it and executes step 1 first, then step 2 using step-1 output as context, etc. The existing `skill_gate` is extended with a `chain_candidates` field that surfaces top-3 skills within 0.10 of the top score (only when ≥ 2 skills meet the criterion) plus a human-readable `chain_hint` suggesting `skill_chain(plan=[...])`. Eventbus publication carries metadata only (skill names, plan size, status) — no rationale text, no PII. Single master kill-switch `skill_chain_enabled` in runtime.json.

---

## Decisions made during brainstorm (locked)

| # | Decision | Choice |
|---|----------|--------|
| 1 | Phase 1 scope | **A**: skill-chaining only; tool invention deferred to own plan |
| 2 | Chain architecture | **B**: explicit `skill_chain` tool (no auto-planner, no implicit chaining) |
| 3 | Output format + failure | **C** (header-structure, verbatim instructions) + **Z** (pre-validation, alt-eller-intet) |
| 4 | Gate-integration + observability | **A** (top-K in gate when scores close) + **3** (eventbus metadata only) |

---

## Components

### `core/tools/skill_chain_tool.py` (new)

The single implementation file. Responsibilities:

- `SKILL_CHAIN_TOOL_DEFINITIONS` — tool schema for registration
- `SKILL_CHAIN_TOOL_HANDLERS` — handler map
- `_exec_skill_chain(args)` — main handler with validation pipeline + build
- `_validate_plan_existence(plan)` — atomic pre-validation
- `_build_combined_instructions(plan)` — C-format builder with step-headers
- `_publish_chain_event(plan, ...)` — eventbus emission

### `core/tools/skill_gate_tool.py` (extend)

Add `chain_candidates` and `chain_hint` fields to `_exec_skill_gate` output. Compute via two new private helpers:
- `_build_chain_candidates(suggestions)` — top-3 within 0.10 window
- `_build_chain_hint(candidates)` — human-readable hint string

### Other modified files

| Path | Change |
|------|--------|
| `core/runtime/settings.py` | New flag `skill_chain_enabled: bool = True` |
| `core/eventbus/events.py` | Add `cognitive_skill_chain` to `ALLOWED_EVENT_FAMILIES` |
| `core/tools/simple_tools.py` | Register `skill_chain` in TOOL_DEFINITIONS + handler |
| `scripts/smoke_test_startup.py` | Verify tool importable + registered |
| `tests/tools/test_skill_chain.py` | New test file |
| `tests/tools/test_skill_gate_chain_candidates.py` | New test file for gate extension |

### Untouched / reused (no changes)

- `core/services/skill_engine.py` — reuse `skill_exists`, `get_skill`, `get_skill_instructions`, `list_skills`
- `core/tools/skill_engine_tools.py` — reuse `_suggest_skills_for_query`
- No DB tables, no daemons, no runtime-state mutations
- No prompt_contract injection — discovery is via gate's `chain_hint` and the tool's description

---

## Tool schema

```python
SKILL_CHAIN_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "skill_chain",
            "description": (
                "Chain multiple skills in sequence for tasks that require "
                "more than one skill (e.g. fact-check then summarize, "
                "research then format). Each step's instructions are loaded "
                "into context in order, with clear step-headers. You execute "
                "step 1, then continue to step 2 using your step-1 output as "
                "context, and so on. Use when skill_gate returns multiple "
                "close-matching candidates, or when the task naturally has "
                "multiple phases. For single-skill tasks, use skill_invoke "
                "instead."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "plan": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Ordered list of skill names. Min 2, max 5. "
                            "Each name must exist (verified before execution)."
                        ),
                        "minItems": 2,
                        "maxItems": 5,
                    },
                    "rationale": {
                        "type": "string",
                        "description": (
                            "Optional: short note on why this chain. "
                            "Logged in tool-call but not persisted to events."
                        ),
                    },
                },
                "required": ["plan"],
            },
        },
    },
]
```

---

## Validation pipeline

```python
def _exec_skill_chain(args: dict) -> dict:
    # 1. Kill-switch
    if not load_settings().skill_chain_enabled:
        return {"status": "disabled",
                "note": "skill_chain is disabled in runtime settings"}

    # 2. Required arg + type
    plan = args.get("plan")
    if not isinstance(plan, list):
        return {"status": "rejected", "reason": "plan must be a list"}

    # 3. Length bounds
    if len(plan) < 2:
        return {"status": "rejected",
                "reason": "plan must have at least 2 skills"}
    if len(plan) > 5:
        return {"status": "rejected",
                "reason": "plan exceeds max length of 5"}

    # 4. Type check entries
    if not all(isinstance(s, str) and s.strip() for s in plan):
        return {"status": "rejected",
                "reason": "all plan entries must be non-empty strings"}

    # 5. Normalize names
    normalized_plan = [s.strip() for s in plan]

    # 6. Pre-validate ALL skills exist (Z — alt-eller-intet)
    missing = _validate_plan_existence(normalized_plan)
    if missing:
        return {
            "status": "rejected",
            "reason": "unknown skills in plan",
            "missing": missing,
            "available": [s["name"] for s in skill_engine.list_skills()],
        }

    # 7. Build combined instructions
    instructions = _build_combined_instructions(normalized_plan)

    # 8. Publish event
    _publish_chain_event(
        plan=normalized_plan,
        instructions_length=len(instructions),
        rationale_provided=bool(args.get("rationale")),
        status="ok",
    )

    # 9. Build result
    result = {
        "status": "ok",
        "chain": normalized_plan,
        "step_count": len(normalized_plan),
        "instructions": instructions,
        "instructions_full_length": len(instructions),
        "note": _build_note(normalized_plan, instructions),
    }
    return result


def _validate_plan_existence(plan: list[str]) -> list[str]:
    """Returns list of missing skill names (empty list if all exist)."""
    return [name for name in plan if not skill_engine.skill_exists(name)]
```

### Validation fail-paths summary

| Failure | Status | Reason | Recovery |
|---------|--------|--------|----------|
| Kill-switch off | `disabled` | runtime setting | Toggle in runtime.json |
| Plan ikke list | `rejected` | "plan must be a list" | Fix call type |
| Plan < 2 entries | `rejected` | "plan must have at least 2 skills" | Use `skill_invoke` |
| Plan > 5 entries | `rejected` | "plan exceeds max length of 5" | Split into 2 calls |
| Empty/non-string entry | `rejected` | "all plan entries must be non-empty strings" | Fix entries |
| Unknown skill(s) | `rejected` | + `missing` + `available` lists | Correct names |
| skill_engine read error | `error` | "engine error: {type}" | Defensive — log + return |

---

## Combined instructions format (C)

```
[skill_chain — 2 steps]

## Step 1 of 2: fact-checker
<entire fact-checker SKILL.md instructions, verbatim>

## Step 2 of 2: markdown-helper
<entire markdown-helper SKILL.md instructions, verbatim>

When you finish step 1, continue to step 2 using your step-1 output as context. Each subsequent step builds on prior output.
```

### Builder

```python
def _build_combined_instructions(plan: list[str]) -> str:
    """Header-format combination — instructions verbatim, step-headers added."""
    n = len(plan)
    parts = [f"[skill_chain — {n} steps]\n"]
    for i, name in enumerate(plan, start=1):
        skill_data = skill_engine.get_skill_instructions(name)
        if skill_data.get("status") != "ok":
            # Defensive — pre-validation should have caught this
            parts.append(f"\n## Step {i} of {n}: {name} (UNAVAILABLE)\n")
            continue
        instructions = skill_data.get("instructions", "").strip()
        parts.append(f"\n## Step {i} of {n}: {name}\n")
        parts.append(instructions)
    parts.append(
        "\n\nWhen you finish step 1, continue to step 2 using your step-1 "
        "output as context. Each subsequent step builds on prior output."
    )
    return "\n".join(parts)
```

### Soft cap on instructions size

```python
_SOFT_INSTRUCTIONS_CAP = 32000  # chars; ~8k tokens

def _build_note(plan: list[str], instructions: str) -> str:
    if len(instructions) > _SOFT_INSTRUCTIONS_CAP:
        return (
            f"⚠ Combined instructions are {len(instructions)} chars "
            f"(soft cap {_SOFT_INSTRUCTIONS_CAP}). Consider shorter chain. "
            "Execute step 1 first, then continue to step 2 using your "
            "step-1 output as context."
        )
    return (
        f"Skills loaded in chain: {len(plan)} steps. Execute step 1 first, "
        "then continue to step 2 using your step-1 output as context. "
        "Each skill's instructions are below."
    )
```

Soft cap = warning, not failure. Jarvis decides whether to proceed or cancel.

---

## Eventbus publication (3 from question 4)

```python
def _publish_chain_event(*, plan, instructions_length, rationale_provided, status):
    try:
        event_bus.publish(
            "cognitive_skill_chain.executed",
            {
                "plan": plan,
                "step_count": len(plan),
                "instructions_length": instructions_length,
                "rationale_provided": rationale_provided,  # bool only — no PII
                "status": status,
            },
        )
    except Exception:
        pass  # eventbus errors must never break tool execution
```

Notér: ingen rationale-tekst i payload. Mission Control kan tælle frekvens, plot popular chains, plot success-rate uden at se Bjørns kontekst-tekst.

---

## skill_gate udvidelse

### Existing output (preserved unchanged)

All existing fields remain identical:
- `status`, `gate_result`, `query`, `skill_name`, `score`
- `suggestions`, `all_matches`, `use_as_template`
- `skill_description`, `skill_use_when`, `skill_tags`
- `instructions`, `instructions_full_length`, `note`, `skilmd_preview`

### New fields (always present, defaulted when not applicable)

```python
{
  "chain_candidates": list[dict],  # always present, [] when no chain candidates
  "chain_hint": str,               # always present, "" when no hint
}
```

### Helper: `_build_chain_candidates`

```python
def _build_chain_candidates(suggestions: list[dict]) -> list[dict]:
    """Return top-3 (max) skills within 0.10 of top score.

    Empty list when:
    - No suggestions
    - Only 1 suggestion exists
    - Top score below 0.30 (weak match — chain doesn't help)
    - Only top-1 was within the 0.10 window
    """
    if not suggestions or len(suggestions) < 2:
        return []
    top_score = float(suggestions[0].get("score") or 0.0)
    if top_score < 0.30:
        return []
    candidates = [
        {"name": s["name"], "score": s["score"]}
        for s in suggestions[:3]
        if float(s.get("score") or 0.0) >= top_score - 0.10
    ]
    if len(candidates) < 2:
        return []
    return candidates
```

### Helper: `_build_chain_hint`

```python
def _build_chain_hint(candidates: list[dict]) -> str:
    if not candidates:
        return ""
    names = [c["name"] for c in candidates]
    plan_repr = ", ".join(f"'{n}'" for n in names)
    n = len(candidates)
    return (
        f"{n} skills matched closely (within 0.10 of top score). "
        f"Consider skill_chain(plan=[{plan_repr}]) "
        "if the task requires multiple steps."
    )
```

### Where in `_exec_skill_gate`

After computing `suggestions`, before the threshold-check that creates `low_match` result:

```python
# NEW: compute chain candidates from suggestions
chain_candidates = _build_chain_candidates(suggestions)
chain_hint = _build_chain_hint(chain_candidates) if chain_candidates else ""

# ... existing threshold + invoke logic ...

# NEW: inject chain-fields into all return paths
result["chain_candidates"] = chain_candidates
result["chain_hint"] = chain_hint
return result
```

Add to `low_match` result, `no_match` result, `disabled` result — every output gets `chain_candidates` (defaulted to `[]`) and `chain_hint` (defaulted to `""`).

---

## Settings flag

```python
# core/runtime/settings.py — added 2026-05-10
# Master kill-switch for skill_chain tool. When False, the tool returns
# "disabled" stub immediately. The tool stays in the schema so Jarvis
# can still call it; it just no-ops.
skill_chain_enabled: bool = True
```

Flag is loaded via `load_settings()` and consumed in `_exec_skill_chain`.

---

## Discovery flow (how Jarvis learns to chain)

1. **Tool description** — `skill_chain`'s description explains when to use it
2. **Gate's `chain_hint`** — when ≥ 2 skills score within 0.10 of top, gate suggests `skill_chain(plan=[...])`
3. **Gate's `chain_candidates`** — structured list Jarvis can read directly
4. **Self-discovery** — Jarvis can call `skill_chain` whenever he judges multi-skill task

No system-prompt injection in Phase 1 — tool description + gate hints carry the discovery weight.

---

## Success criteria — 30-day evaluation

### (1) Technical correctness

- `skill_chain` accepts plans of 2-5 skills
- Pre-validation atomic (no partial execution if any skill missing)
- Validation rejects with `available` list when skills missing
- Combined instructions follow C-format (headers + verbatim + closing line)
- Soft cap on 32k chars produces warning, not rejection
- Kill-switch returns "disabled" stub
- Empty/non-list/non-string entries rejected with clear messages
- Eventbus publication works with metadata only (no rationale text)
- Skill_gate `chain_candidates` + `chain_hint` populated correctly
- Existing skill_gate behavior unchanged (regression-tested)

### (2) Subjective quality

- Jarvis calls `skill_chain` at least once unprompted in 30 days
- When `chain_hint` is populated, Jarvis evaluates chain vs invoke
- Combined instructions are read by Jarvis (he follows step ordering)
- At least one chain produces output better than single-skill alone
- Inner_voice or chronicle shows signs of chaining: "*two skills here*", "*step 1 first*"

### (3) Business value

- Chain-frequency vs skill_invoke-frequency: ~5-15% of skill activations?
- Plan-size distribution: 2 vs 3 vs 4 vs 5? Default cap right?
- Pre-validation rejection-rate: how often does Jarvis typo? Schema clarity signal

If (1) holds but (2)/(3) inert: tool description too vague, or chain_hint not effective discovery — Phase 2 prompt-contract integration.

---

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Jarvis calls skill_chain with single skill | Medium | Validation rejects with clear message |
| Token-bloat from long chain | Medium | Max 5 + soft cap 32k chars + warning |
| `chain_candidates` confusing when only top-1 close | Low | Empty list when < 2 within window |
| Skill engine read fails between validation and build | Low | Defensive `(UNAVAILABLE)` + status="ok" |
| Combined instructions exceed model context | Low | 32k chars ≈ 8k tokens, well under 200k window |
| Skill_chain feedback loop | Low | Stateless tool, no DB mutation |
| PII leaks in eventbus | Low | Rationale excluded from payload by design |
| Skill_gate over-suggests chains | Medium | 0.10 window + top-1 ≥ 0.30 requirement; tunable |
| Backwards compat broken for skill_gate consumers | Low | New fields are pure additions |

---

## Phase 2 outlook

Not built now; design must not block:

1. **Tool invention** — separate plan with sandboxing, governance, audit
2. **Auto-planner** (`skill_plan(query)` returns chain via LLM call)
3. **Auto-detection in gate** (LLM analysis of query for chain-worthy intent)
4. **Output-passing schemas** — structured skill input/output, pipe-style
5. **Chain-history table** — log + outcome tracking
6. **Skill co-occurrence learning** — observe sequences, suggest defaults
7. **Prompt-contract integration** — system-prompt explains chaining
8. **Per-skill `chain_with` metadata** — frontmatter declares compatible chains

---

## Open questions for implementation planning

1. **Tool registration site** — `simple_tools.py` already has SKILL_GATE_TOOL_DEFINITIONS pattern. Mirror exactly: import, splat into TOOL_DEFINITIONS, merge into _TOOL_HANDLERS.

2. **`get_skill_instructions` return shape** — verify in implementation that `status: "ok"` is the success indicator (not just presence of `instructions` key).

3. **Test fixture for skill existence** — tests need a way to register fake skills. Reuse pattern from `test_skill_engine.py`'s `isolated_skills_root` fixture.

4. **Eventbus subscriber** — does any existing subscriber care about `cognitive_skill_chain.executed`? Check during planning. Default: no, just published for future MC consumers.

5. **`get_response_style_modifiers` integration** — none. Skill_chain doesn't know about user temperature; that's prompt_contract's concern. Out of scope.

---

## Out of scope for this spec

- Tool invention (separate plan)
- Asynchronous/parallel skill execution
- Conditional chains ("if step 1 says X, jump to step 4")
- Cross-workspace skill sharing
- Skill marketplaces / external chain catalogs
- Chain versioning/snapshots
- Auto-planner (Phase 2)
- LLM-based chain detection in gate (Phase 2)
