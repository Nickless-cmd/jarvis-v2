---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Tool Invention Phase 1 Design

**Date:** 2026-05-12
**Status:** Draft — awaiting user review
**Roadmap item:** AGI track #9 — Tool Invention

## Goal

Close the most-pointed-at AGI gap: let Jarvis autonomously identify
when a new skill would help him, formulate what it should contain,
and install it after approval. This is a qualitative step from
"using tools" to "inventing tools" — and it has been explicitly
deferred from Lag #4 Creative Voice and skill_chain specs.

Phase 1 ships the minimum closed loop: a `propose_new_skill` tool
Jarvis calls when he notices the need; validation up front; approval
via the existing `propose_plan`-flow with a new `skill_data` payload;
automatic install via `create_skill()` when the plan is approved.

Phase 1.1 (separate) adds a daily nudge-scanner that detects repeated
tool-call sequences and surfaces them as awareness-block notifications,
acknowledging Jarvis' honest self-assessment that he will otherwise
forget the tool exists.

## Background

Existing infrastructure (already live):
- `skill_engine.py` — full skill system: `create_skill()`, `list_skills()`,
  `get_skill()`, `delete_skill()`, `search_skills()`, `reload_skills()`.
  Skills live as `SKILL.md` files in `SKILLS_ROOT` with optional
  scripts/templates/references subdirs.
- `plan_proposals.py` (Multi-step Planner Phase 1, deployed today) —
  propose/approve/dismiss/superseded lifecycle, auto-todo-conversion,
  cross-session plan resumption, status tracking with auto-completion.
- `skill_chain` Phase 1 — sequential skill execution.
- `dispatch_to_claude_code` — Jarvis can delegate code-writing.

**The hole Phase 1 closes:** `create_skill()` is unguarded — any caller
can write to disk. There is no trigger that lets Jarvis SAY "I need a
new skill", no approval gate, no formulation step from "I notice the
need" to "I have an installable SKILL.md". The infrastructure exists
in pieces; the loop is not closed.

## Brainstorm Decisions (Locked)

**Q1 — Trigger:** (c) Jarvis-initiated tool, with (a) light recurring-
pattern detector deferred to Phase 1.1. Jarvis was self-aware: *"Jeg
kender mig selv nok til at være ærlig: hvis jeg får et
propose_new_skill-værktøj, vil jeg nok glemme at bruge det i starten."*
We accept this honesty and design accordingly: minimal Phase 1, optional
nudge in Phase 1.1.

**Q2 — Approval flow:** (a) reuse `propose_plan` with a new
`skill_data` payload field. Hook in `resolve_plan` checks for
`skill_data` at approval time and calls `create_skill()`. Plan
auto-completes via existing Multi-step Planner Phase 1 logic.
Jarvis: *"Approval-flowet skal ikke vide noget om skills. Det skal
bare vide 'der er en plan med noget metadata'."*

**Q3 — Validation:** (a) at propose-time. Reject invalid name,
duplicate, empty instructions BEFORE the plan is created. Approval =
install must be an unbroken contract. New helper
`validate_skill_proposal()` runs the same checks as `create_skill()`
without writing to disk. On unexpected I/O error at install time
(disk full, permissions changed): log error + emit informational
event; no new `install_failed` plan status. Jarvis: *"Hvis I/O fejler
ved approval, er det en alvorlig systemfejl, ikke en proposal-status."*

## Architecture

### Files

**Modified:**
- `core/services/skill_engine.py` — add `validate_skill_proposal(name,
  description, instructions, use_when, tags) -> dict[str, Any]`.
- `core/services/plan_proposals.py` — `propose_plan` accepts new
  `skill_data: dict | None = None` kwarg and stores it on the plan
  record. `resolve_plan` hook checks `rec.get("skill_data")` at
  `decision="approved"` and calls `create_skill()` on it. Logs +
  emits informational event on I/O error.
- `core/tools/skill_engine_tools.py` — new tool definition + handler
  for `propose_new_skill`.
- `core/tools/simple_tools.py` — register `propose_new_skill` in
  `TOOL_DEFINITIONS` and `_TOOL_HANDLERS`.
- `core/runtime/settings.py` — add `tool_invention_enabled: bool = True`.

**Untouched / reused:**
- `core/services/agent_todos.py` — `create_from_plan` already
  handles plans with steps; skill-proposal plans have a single
  symbolic step ("Install skill 'X'") that auto-completes alongside
  the install. No changes needed.
- `core/services/prompt_contract.py` — pending_plan_section already
  shows skill-proposal plans alongside other plans (no new section
  required).
- `core/eventbus/events.py` — `cognitive_state` family covers new
  events (`cognitive_state.skill_proposed`,
  `cognitive_state.skill_installed`,
  `cognitive_state.skill_install_failed`).
- No new DB tables. No new event families. No new daemons.

### Data flow

```
Jarvis calls propose_new_skill(name, description, instructions, use_when, tags)
  → _exec_propose_new_skill(args)
       ├─ if not tool_invention_enabled: return error
       ├─ validate_skill_proposal(name, description, instructions, use_when, tags)
       │     ├─ same checks as create_skill (regex, fields, no-dupe)
       │     ├─ does NOT write to disk
       │     └─ return {"status": "ok"} or {"status": "error", "error": ...}
       ├─ if validation error: return it to Jarvis
       └─ plan_proposals.propose_plan(
              session_id=args.session_id,
              title=f"Ny skill: {name}",
              why=description,
              steps=[f"Install skill '{name}' (auto on approval)"],
              skill_data={"name": ..., "description": ..., "instructions": ...,
                          "use_when": ..., "tags": ...},
          )
       └─ emit cognitive_state.skill_proposed {plan_id, name}

User approves (via approve_plan tool or MC):
  → resolve_plan(plan_id, decision="approved")
       ├─ status → approved
       ├─ existing Phase 1 auto-create-todos runs (single step)
       └─ NEW: if rec.get("skill_data"):
            try:
                skill_engine.create_skill(**rec["skill_data"])
                emit cognitive_state.skill_installed
                # plan will auto-complete when todo is marked done; the
                # install completion can mark the todo too via
                # update_todo_status to chain into auto-completion.
            except Exception as e:
                logger.error("skill install failed for plan %s: %s", plan_id, e)
                emit cognitive_state.skill_install_failed
                # plan stays "approved" but uncompleted; user sees warning
```

### Tool definition (Ollama-compatible)

```python
{
    "type": "function",
    "function": {
        "name": "propose_new_skill",
        "description": (
            "Foreslå en ny skill du selv mener du har brug for. Værktøjet "
            "validerer at navn+content er installerbart, lægger forslaget "
            "som en plan der venter på godkendelse. Når brugeren godkender, "
            "installeres skillen automatisk via skill_engine.create_skill()."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "lowercase, alphanumeric + - + _ (matches ^[a-z0-9][a-z0-9_-]*$)",
                },
                "description": {
                    "type": "string",
                    "description": "én sætning om hvad skillen gør",
                },
                "instructions": {
                    "type": "string",
                    "description": "SKILL.md body (markdown). Skal være konkret nok til at en frisk session kan følge den.",
                },
                "use_when": {
                    "type": "string",
                    "description": "trigger-beskrivelse: hvornår skal denne skill påberåbes? Default = description.",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "valgfrie tags til søgbarhed",
                },
            },
            "required": ["name", "description", "instructions"],
        },
    },
}
```

### Validation helper

`skill_engine.validate_skill_proposal()` — same regex/fields/dupe-check
as `create_skill()`, but returns without writing. Implementation
extracts the existing validation logic into a shared function that
both `create_skill()` and `validate_skill_proposal()` call. No
behavior change for existing `create_skill()` callers.

## Phase 1 sub-deliveries

### Phase 1.1 of Phase 1 — Validation + plan-payload
- Add `tool_invention_enabled` setting flag
- Add `validate_skill_proposal()` to skill_engine
- Extend `propose_plan` to accept `skill_data` kwarg
- Add `propose_new_skill` tool + handler
- Register in `simple_tools.py`

### Phase 1.2 of Phase 1 — Install hook + events
- Extend `resolve_plan` to detect `skill_data` and call `create_skill()`
- Emit eventbus events
- Verify auto-completion path works (single-step plan completes on
  todo-completion which fires after install)

## Success criteria

1. **Validation rejects bad proposals at propose-time.** Duplicate
   name, invalid regex, empty instructions all return error from
   `propose_new_skill` without plan creation.
2. **Valid proposals create a plan with `skill_data`.** State_store
   shows plan with skill_data payload + status awaiting_approval.
3. **Approval triggers install.** When user approves, `create_skill()`
   runs; SKILL.md exists on disk; `list_skills()` includes it.
4. **Event emitted on install:**
   `cognitive_state.skill_installed` fires with `plan_id`
   and `name`.
5. **Kill-switch works:** `tool_invention_enabled=False` →
   `propose_new_skill` returns error immediately.
6. **Backwards compat:**
   - `propose_plan(...)` calls without `skill_data` work unchanged.
   - Existing 109 plans + new plans from Multi-step Planner Phase 1
     unaffected.
   - `create_skill()` callers (none currently in the wild, but defense
     in depth) unaffected — validation helper is additive.
   - All existing tests pass.
7. **Dismissed proposals do not install.** When user dismisses, plan
   marked dismissed; no `create_skill()` call.
8. **I/O failure logged but not catastrophic.** If `create_skill()`
   raises at install time, logged + event emitted, plan stays
   approved but uncompleted. No crash.

## Risks & mitigations

- **Jarvis proposes bad skills.** SKILL.md vague, instructions wrong,
  description misleading. *Mitigation:* approval-gate is the human-in-
  the-loop check. 30-day review reads installed skills.
- **Jarvis forgets the tool exists.** Self-acknowledged. *Mitigation:*
  Phase 1.1 nudge-scanner planned.
- **Race condition on duplicate names.** Two `propose_new_skill`
  calls simultaneously with same name. *Mitigation:* validate-then-
  write race is fundamental in any file-based system; if both pass
  validation at the same instant, the second `create_skill()` at
  install-time will fail on exists-check; install-failure logged.
- **Bad skills are hard to remove.** *Mitigation:* `skill_engine.
  delete_skill()` exists; user can call via MC or future tool.
  Phase 2 could add `propose_skill_retirement` flow.
- **Skill could shadow a built-in tool.** A skill named the same as
  a tool could confuse the skill_chain system. *Mitigation:*
  validation includes a check against existing tool names (added in
  this Phase 1).
- **No proof the skill actually works.** Validation is
  syntactic/structural only; we don't execute it. *Mitigation:*
  Phase 2 could add sandboxed dry-run. For Phase 1, the gap is
  acceptable — installed skills get reviewed by reading SKILL.md.
- **Naming collisions over time as Jarvis proposes more.** Phase 1
  doesn't track proposal history beyond plan_proposals. *Mitigation:*
  Phase 2 could add a `skill_proposal_history` view in MC.

## Out of scope (Phase 1.1 / Phase 2 / deferred)

- **Phase 1.1:** Daily nudge-scanner (recurring-pattern detector,
  surfaces in awareness-block as "you've run X+Y+Z 5 times today —
  consider propose_new_skill"). Separate brainstorm round once we
  have Phase 1 data.
- **Phase 2:**
  - Skill retirement flow (propose_skill_deletion with approval)
  - Skill refinement (modify existing skill via similar flow)
  - Sandboxed skill execution / dry-run validation
  - Skill version management
  - Cross-Jarvis-instance skill sharing
  - Multi-step skill proposals (skill with scripts/templates)

## 30-day review

Schedule eval at 2026-06-12:
- Count proposed skills (zero is meaningful data — Jarvis forgot)
- Count approved + installed
- Count dismissed
- Read installed skills' SKILL.md content — kvalitet?
- Bjørns subjektive vurdering: virker værktøjet? Er forslagene gode?
- Verify event log for install/install_failed events
- Decide: keep, tune, deprecate, or proceed to Phase 1.1 nudge-scanner
- If install_failed events appeared: investigate root cause
