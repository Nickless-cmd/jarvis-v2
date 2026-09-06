# CC-Style Prompt Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Jarvis' visible lane behave more like Claude Code: small stable prompt, context/tool expansion only when needed, bounded historical tool results, and cache-stable DeepSeek payloads.

**Architecture:** Keep identity and safety in the stable prefix. Move volatile or optional context behind deterministic gates. Replace the always-send-all-tools behavior with a small base tool pool plus lazy schema loading. All transcript reduction must be append-only or keyed by discrete compaction/lifecycle floors so DeepSeek prompt caching is not broken by sliding-window churn.

**Tech Stack:** Python 3.11, pytest, existing `core.services.prompt_contract`, `core.services.visible_followup_lean`, `core.context.tool_result_lifecycle`, `core.tools.simple_tools_definitions`, and visible model adapter paths.

**Spec:** `/home/bs/Videoklip/agent-01-compact.md`, `/home/bs/Videoklip/agent-03-prompt-skills.md`, `/home/bs/Videoklip/agent-04-cache-cost.md`, and the measured payload from `scripts/measure_prompt_payload.py`.

## Global Constraints

- Do not move dynamic content before the stable prefix.
- Do not introduce recency-relative transcript rendering that changes old bytes each turn.
- Preserve identity, safety, tool-output hygiene, and anti-fabrication rules.
- New feature gates must default conservatively unless the task explicitly activates a previously built, tested mechanism.
- Every behavior change gets a failing test first, then implementation, then targeted tests, then a commit via `scripts/commit_with_attribution.py`.
- Files over the Boy Scout threshold must be split before adding substantial logic.

---

### Task 1: Activate Lean Agentic Prompt Safely

**Files:**
- Modify: `core/services/visible_followup_lean.py`
- Modify: `core/runtime/settings.py`
- Test: `tests/test_lean_agentic_prompt.py`

**Interfaces:**
- Consumes: `build_lean_base_messages(base_messages) -> tuple[list[dict], dict]`
- Produces: default-on runtime behavior for `agentic_lean_prompt_enabled()`

- [ ] **Step 1: Write failing tests** asserting the default is enabled, env/config can still disable it, and the transform preserves the anti-lie row.
- [ ] **Step 2: Run the targeted test and verify RED.**
- [ ] **Step 3: Change `agentic_lean_prompt_enabled()` default to true, with env false still winning.**
- [ ] **Step 4: Run `tests/test_lean_agentic_prompt.py`.**
- [ ] **Step 5: Commit.**

### Task 2: Activate Tool Result Lifecycle

**Files:**
- Modify: `core/runtime/settings.py`
- Test: `tests/context/test_tool_result_lifecycle.py`
- Test: `tests/services/test_visible_runs_lifecycle.py`

**Interfaces:**
- Consumes: `tool_result_lifecycle_enabled` setting
- Produces: old tool results render as cold stubs after compaction/lifecycle advancement

- [ ] **Step 1: Write failing tests** for default enabled and explicit config false override.
- [ ] **Step 2: Run targeted tests and verify RED.**
- [ ] **Step 3: Flip the default to enabled while preserving config override.**
- [ ] **Step 4: Run lifecycle/transcript tests.**
- [ ] **Step 5: Commit.**

### Task 3: Add Intent-Based Lean Tool Pool

**Files:**
- Create: `core/tools/tool_pool_filter.py`
- Modify: `core/tools/simple_tools.py` or `core/tools/simple_tools_definitions.py`
- Modify: `scripts/measure_prompt_payload.py`
- Test: `tests/test_visible_tool_pool_filter.py`

**Interfaces:**
- Produces: `select_visible_tool_definitions(tool_defs, user_message, mode="auto") -> tuple[list[dict], dict]`

- [ ] **Step 1: Write failing tests** showing a simple greeting gets a small core pool, a coding request gets code tools, and DeepSeek cache order is deterministic.
- [ ] **Step 2: Verify RED.**
- [ ] **Step 3: Implement deterministic category matching and stable alphabetical ordering inside categories.**
- [ ] **Step 4: Wire visible lane tool definition selection through the filter.**
- [ ] **Step 5: Run prompt payload measurement and targeted tests.**
- [ ] **Step 6: Commit.**

### Task 4: Add Lazy Tool Schema Loader

**Files:**
- Modify: `core/tools/tool_pool_filter.py`
- Modify: `core/tools/simple_tools_definitions.py`
- Test: `tests/test_visible_tool_pool_filter.py`

**Interfaces:**
- Produces: a visible tool such as `load_tool_schemas` that can expose full schemas for omitted tools by name/category.

- [ ] **Step 1: Write failing tests** that omitted tools are discoverable through a loader/index without sending every schema in the initial payload.
- [ ] **Step 2: Verify RED.**
- [ ] **Step 3: Add the loader tool definition and handler using existing tool-definition data.**
- [ ] **Step 4: Ensure the loader is always in the core visible pool.**
- [ ] **Step 5: Run targeted tests and payload measurement.**
- [ ] **Step 6: Commit.**

### Task 5: Make Prompt Relevance Live for Non-Frozen Tail Sections

**Files:**
- Modify: `core/services/central_prompt_composer.py`
- Modify: `core/services/prompt_contract.py`
- Test: `tests/test_central_prompt_composer.py`
- Test: `tests/test_prompt_contract.py`

**Interfaces:**
- Consumes: `should_include(turn_type, section)`
- Produces: deterministic default dropping only for explicitly non-frozen, low-value dynamic tail sections

- [ ] **Step 1: Write failing tests** that identity/security sections are never dropped, while known noisy tail sections can be omitted for simple greetings.
- [ ] **Step 2: Verify RED.**
- [ ] **Step 3: Add default safe relevance weights and a live-by-default path only for tail sections.**
- [ ] **Step 4: Assert the stable prefix hash is unchanged for equivalent inputs.**
- [ ] **Step 5: Run targeted prompt tests.**
- [ ] **Step 6: Commit.**

### Task 6: Add Time-Based Microcompact

**Files:**
- Create: `core/context/microcompact.py`
- Modify: `core/services/prompt_sections/transcript_sections.py`
- Test: `tests/context/test_microcompact.py`
- Test: `tests/test_chat_context_usage.py`

**Interfaces:**
- Produces: `apply_time_based_microcompact(messages, now, gap_minutes=60, keep_recent=5) -> tuple[list[dict], dict]`

- [ ] **Step 1: Write failing tests** for clearing old historical tool results after a >60 minute assistant gap while keeping the newest 5 and leaving non-tool messages untouched.
- [ ] **Step 2: Verify RED.**
- [ ] **Step 3: Implement pure microcompact transform.**
- [ ] **Step 4: Wire it before transcript rendering only when cache TTL is already expired.**
- [ ] **Step 5: Run microcompact/transcript tests and payload measurement.**
- [ ] **Step 6: Commit.**

### Final Verification

- [ ] Run `python -m compileall core apps/api scripts`.
- [ ] Run targeted prompt/tool/context tests.
- [ ] Run `python scripts/measure_prompt_payload.py --json` and compare tool/system/transcript totals.
- [ ] Inspect DeepSeek cache-sensitive ordering: stable prefix first, dynamic tail last, deterministic tool order.
