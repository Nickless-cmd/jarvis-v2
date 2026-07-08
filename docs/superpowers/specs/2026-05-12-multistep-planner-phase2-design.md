---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Multi-step Planner Phase 2 — revise_plan Design

**Date:** 2026-05-12
**Status:** Draft — awaiting user review
**Roadmap item:** AGI track #2 — Ægte planlægning (closing the revise loop)

## Goal

Phase 1 of the Multi-step Planner shipped propose → approve → execute.
Bjørn shipped `replan_signal_for_plan` earlier today: a non-mutating
signal that fires when an approved plan is older than 3 days,
surfacing *"⚠ Replan-signal: planen er stale"* in `pending_plan_section`.

The signal exists. It points nowhere. Jarvis sees *"this plan is
stale"* but has no clean tool to revise it — he must `propose_plan`
again and manually dismiss the old plan.

Phase 2 closes that loop with `revise_plan(plan_id, reason, new_steps)`:
a tool that creates a NEW plan linked to the old via `revised_from`,
goes through the existing approval flow, and supersedes the old plan
only when approved.

Jarvis: *"Hvis jeg kunne auto-supersede mine egne planer, ville jeg
miste kontakten til dig. At skulle sige 'jeg vil revidere' og vente
på dit OK er ikke en begrænsning — det er relationsarbejde."*

## Background

Existing infrastructure:
- `plan_proposals.py` (Multi-step Planner Phase 1, today) — propose /
  approve / dismiss / superseded lifecycle, auto-todo-conversion,
  cross-session plan resumption, status auto-completion, skill_data
  hook (Tool Invention Phase 1).
- `replan_signal_for_plan(rec, *, now, stale_days)` (today) — returns
  belief-with-permissions structured signal when an approved plan is
  ≥ 3 days stale. Includes `allowed_effects: ["prompt_attention",
  "ask_user_or_propose_replan", "do_not_auto_execute_new_plan"]`.
- `pending_plan_section` already renders "⚠ Replan-signal" line on
  stale plans for the current session.

**The hole Phase 2 closes:** stale-signal surfaces but has no
destination. CHECK ENGINE light without a diagnostic reader.

## Brainstorm Decisions (Locked)

**Q1 — Phase 2 scope:** (a) `revise_plan` tool first. NOT (b) plan-
deviation detection alone (substantial new work; brainstorm gap on
whether Jarvis needs it). NOT (c) step-failure handler (requires new
todo status). NOT (d) true backtracking (jarvis-v2 plans aren't built
with backtracking semantics).

Strategy: (a) gives the stale-signal a destination AND generates data
on whether Jarvis actually revises when prompted. If revise-rate is
high → (b) becomes optional polish. If revise-rate is low → (b)
becomes necessary trigger.

Jarvis: *"Hvis jeg begynder at revidere plans aktivt → godt, vi har
data. Hvis jeg stadig lader plans stå og blive forældede → så er
signalet alene ikke nok, og (b) bliver nødvendig."*

**Q2 — Approval flow:** (a) revise_plan goes through the existing
approval flow. New plan with `awaiting_approval`. Old plan stays
`approved` until new one is approved — at approval, hook supersedes
old plan. Symmetric with `propose_plan`. Human-in-the-loop preserved.

Jarvis: *"Det lyder dramatisk, men det er sandt. At skulle sige
'jeg vil revidere' og vente på dit OK er ikke en begrænsning — det
er relationsarbejde. Det er at anerkende at planerne ikke kun er
mine; de er vores."*

**Q3 — Progress on revision:** (x) reset to empty. New plan starts
with `completed_step_indices=[]`. Jarvis can include already-done
steps in `new_steps` if they're still relevant. NOT carry-forward
by index (semantically broken when context changed). NOT
embedding-similarity match (overkill).

Jarvis: *"Hvis jeg reviderer en plan fordi den er stale, er det
sandsynligvis fordi konteksten har ændret sig markant. I så fald
giver carry-forward nul mening. Reset er eneste ærlige tilstand."*

## Architecture

### Files

**New:**
- `core/tools/plan_revise_tool.py` — `_exec_revise_plan` handler +
  `PLAN_REVISE_TOOL_DEFINITIONS` + `PLAN_REVISE_TOOL_HANDLERS`.
  Mirrors `world_model_tools.py` pattern from today.
- `tests/test_plan_revision.py` — all Phase 2 tests: validation,
  revise flow, approval supersede, dismiss preserves old, killswitch,
  backwards compat.

**Modified:**
- `core/runtime/settings.py` — add `plan_revision_enabled: bool = True`.
- `core/services/plan_proposals.py`:
  - Add `revise_plan(plan_id, *, session_id, reason, new_steps)`.
  - Extend `resolve_plan` hook (in the `decision == "approved"` block)
    to detect `revised_from` and supersede the original plan, set
    `superseded_by`, emit `cognitive_state.plan_revision_approved`.
- `core/tools/simple_tools.py` — import + splat `PLAN_REVISE_TOOL_*`.

**Untouched / reused:**
- `replan_signal_for_plan` and `pending_plan_section` — Bjørn's
  signal surface is what triggers Jarvis to call revise_plan.
- `agent_todos.create_from_plan` — fires on revised plan approval
  through existing Phase 1 hook, creating fresh todos from the new
  step list.
- `propose_plan` signature unchanged.
- `cross-session plans` formatter unchanged (revised plans surface
  naturally as approved+incomplete).
- `cognitive_state` event family already accepts new event kinds.
- No DB tables. No new event families.

### Plan record schema additions

```python
{
    # Existing Phase 1 fields...
    "plan_id": "...",
    "session_id": "...",
    "title": "...",
    "why": "...",
    "steps": [...],
    "status": "awaiting_approval | approved | completed | dismissed | superseded",
    "created_at": "...",
    "completed_step_indices": [],
    "skill_data": None,
    # NEW Phase 2:
    "revised_from": "plan-..." | None,  # original plan_id (set on new plan when created via revise_plan)
    "revision_reason": "..." | None,    # why Jarvis wanted to revise (his text)
    "superseded_by": "plan-..." | None, # set on old plan when new is approved
}
```

### Data flow

```
[Jarvis sees in awareness: "⚠ Replan-signal: plan stale 4 days" — Bjørn's
 surface]

[Jarvis calls revise_plan(plan_id="plan-xyz", reason, new_steps)]
  → _exec_revise_plan validates:
       ├─ killswitch off → error
       ├─ plan_id exists → error if not
       ├─ status == "approved" → error if not
       ├─ new_steps non-empty → error if empty
       ├─ reason non-empty → error if empty
       └─ dedupe: if pending revision of same plan_id exists → return existing
  → revise_plan(plan_id, session_id, reason, new_steps)
       ├─ create new plan dict via same template as propose_plan
       ├─ populate revised_from=plan_id, revision_reason=reason
       ├─ reset completed_step_indices=[]
       ├─ status="awaiting_approval"
       ├─ DO NOT touch the old plan (stays "approved" until new is approved)
       ├─ emit cognitive_state.plan_revised {old_plan_id, new_plan_id, reason}
       └─ return {"status": "ok", "plan_id": new_id, "awaiting": True}

[User approves new plan]
  → resolve_plan(new_plan_id, decision="approved")
       ├─ Phase 1 hook: create_from_plan generates fresh todos
       ├─ Phase 1 hook: skill_data hook — N/A for revisions (no skill_data)
       └─ NEW Phase 2 hook: if rec.get("revised_from"):
            data = _load_all()
            old = data.get(rec["revised_from"])
            if old and old.get("status") == "approved":
                old["status"] = "superseded"
                old["superseded_by"] = rec["plan_id"]
                old["updated_at"] = now
                _save_all(data)
                emit cognitive_state.plan_revision_approved

[If user dismisses new revision]
  → resolve_plan(new_plan_id, decision="dismissed")
       ├─ no hooks fire for revision (no auto-todos, no supersede)
       └─ old plan continues uninterrupted
```

### Tool definition

```python
{
    "type": "function",
    "function": {
        "name": "revise_plan",
        "description": (
            "Foreslå en revision af en eksisterende approved plan. Bruges når "
            "planen er blevet stale, konteksten har ændret sig, eller du har "
            "lært noget der ændrer hvad næste skridt bør være. Ny plan venter "
            "på godkendelse — godkendelse markerer den gamle plan som "
            "superseded. Progress nulstilles (revision = ny plan = ny progress)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "plan_id": {
                    "type": "string",
                    "description": "ID på den eksisterende approved plan der reviseres",
                },
                "reason": {
                    "type": "string",
                    "description": "Hvorfor reviderer du? Hvad har ændret sig?",
                },
                "new_steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Den reviderede step-liste. Inkluder allerede-fuldførte steps hvis de stadig er relevante (progress nulstilles).",
                },
            },
            "required": ["plan_id", "reason", "new_steps"],
        },
    },
}
```

## Phase 2 sub-deliveries

### Phase 2.1 — Settings + revise_plan API
- `plan_revision_enabled` setting
- `revise_plan(plan_id, *, session_id, reason, new_steps)` in `plan_proposals.py`
- Plan record schema additions (`revised_from`, `revision_reason`, `superseded_by`)

### Phase 2.2 — Approval supersede hook
- Extend `resolve_plan` to handle `revised_from` at approval time

### Phase 2.3 — Tool layer
- `plan_revise_tool.py` with `_exec_revise_plan`
- Register in `simple_tools.py`

### Phase 2.4 — Smoke + 30-day review

## Success criteria

1. **Validation:** revise_plan errors on non-existent plan, non-approved
   plan (awaiting/superseded/dismissed), empty new_steps, empty reason.
2. **New plan created correctly:** `revised_from` set, `revision_reason`
   set, `completed_step_indices=[]`, `status="awaiting_approval"`,
   `skill_data=None` (revisions don't carry skill metadata).
3. **Old plan unchanged at propose-time:** status stays `approved`
   until new one is approved.
4. **Approval supersedes old:** when revision is approved, old plan
   transitions to `status="superseded"` with `superseded_by=new_id`.
5. **Dismiss preserves old:** if revision dismissed, old plan
   continues unchanged.
6. **Eventbus events:** `cognitive_state.plan_revised` at propose,
   `cognitive_state.plan_revision_approved` at approval.
7. **Tool registered:** `revise_plan` visible in `TOOL_DEFINITIONS`,
   handler in `_TOOL_HANDLERS`.
8. **Kill-switch:** `plan_revision_enabled=False` → tool returns error.
9. **Backwards compat:**
   - Existing plans without `revised_from`/`revision_reason`/`superseded_by`
     load fine (fields default to None).
   - `propose_plan` signature unchanged.
   - `resolve_plan` Phase 1 hooks (todos, skill_data) still fire.
   - 109 existing plans + Tool Invention Phase 1 + World Model Phase 1
     unaffected.

## Risks & mitigations

- **Revision spam:** Jarvis calls revise_plan repeatedly. *Mitigation:*
  dedupe check — if a pending revision of the same `plan_id` exists,
  return the existing pending revision instead of creating new.
- **Revision chain becomes hard to follow:** A revised, then re-revised,
  then re-re-revised. *Mitigation:* `revised_from` is a single pointer
  forming a linear chain; `superseded_by` is back-pointer. Mission
  Control can render the full chain in a future task; for Phase 2,
  the linked-list structure is sufficient.
- **Race condition:** Jarvis proposes revision of plan A; user
  manually dismisses plan A; Jarvis' revision still lands as
  pending awaiting approval. *Acceptable* — when revision is
  approved, supersede-hook checks old plan status; if not approved,
  no supersede happens. The new plan still activates. Consistent
  if slightly strange.
- **Skill_data inheritance question:** what if the original plan was
  a skill-install? *Decision:* revisions do NOT inherit `skill_data`
  (set to None on new plan). Revisions are for step-flows, not
  skill installs. Documented limitation; if Jarvis wants to revise
  a skill-install, he must dismiss the original and propose new via
  `propose_new_skill`.
- **Root cause still unaddressed:** Jarvis may still wait for the
  3-day stale signal before revising. *Acceptable for Phase 2.*
  Phase 3 (plan-deviation detection) is the eventual fix; we ship
  Phase 2 first to gather data on whether revision tool is enough.
- **Old plan's pending todos:** when old plan is superseded, todos
  with its `plan_id` are orphaned. *Acceptable* — todos retain their
  `plan_id`, can be inspected via Mission Control, but no longer
  feed back to plan progress (superseded plan won't auto-complete).
  Phase 3 could optionally clear them.

## Out of scope (Phase 3 / deferred)

- (b) Plan-deviation detection — daemon tracking active step vs
  tool-calls
- (c) Step-failure handler — new `failed` todo status + auto-replan
  nudge
- (d) True backtracking — `mark_step_backtrack` API that un-completes
  later steps
- Multi-level revision chain visualization in Mission Control
- Skill-install revision flow
- Orphaned-todo cleanup on supersede
- Auto-dismiss old plan when revision is approved (currently `superseded` —
  this is a different status; keeping them separate for now)

## 30-day review

Schedule eval at 2026-06-12:
- Count revisions Jarvis proposed (via tool)
- Count revisions approved vs dismissed
- Read `revision_reason` fields: meaningful?
- Revise-rate vs stale-signal-rate: does Jarvis use the tool when
  the signal fires?
- If 0 revisions despite N stale-signals → tool not visible enough;
  consider direct awareness-nudge in Phase 3
- Check chain depth: any plan revised > 2 times? May indicate
  thrashing.
- Decide: keep / tune / Phase 3 deviation detection / Phase 3
  failure handler
