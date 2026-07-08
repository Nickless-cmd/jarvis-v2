---
status: færdig
audited: 2026-07-08
ground_truth: "Verified against live code: (1) workspace_paths.py module exists with shared_dir(), workspace_dir(), NoUserContextError matching claims exactly; (2) database schema has scheduled_for_user_id, initiated_by, relevant_to_users columns on declared tables (schema audit via db_schema.p"
---
# Multi-User Workspace Layout

One-page reference for what lives where in `~/.jarvis-v2/`. See spec
`docs/superpowers/specs/2026-05-28-multi-user-workspace-isolation-design.md`
for design rationale.

## Layout

```
~/.jarvis-v2/
├── shared/                # Jarvis-state (one entity, all users see same)
│   ├── SOUL.md, IDENTITY.md, MANIFEST.md
│   ├── INNER_VOICE.md, CHRONICLE.md, STANDING_ORDERS.md
│   ├── dreams/, runtime/, journal/, letters/
│   └── (etc.)
│
├── workspaces/            # Per-relation state
│   ├── bjorn/             # MEMORY.md, USER.md, day_shape, threads
│   ├── mikkel/
│   └── michelle/
│
└── config/
    └── users.json         # discord_id → workspace name + role
```

## API

In services, always resolve paths via the helper:

```python
from core.runtime.workspace_paths import shared_dir, workspace_dir

shared_dir()      # → ~/.jarvis-v2/shared
workspace_dir()   # → ~/.jarvis-v2/workspaces/<current user's name>
workspace_dir(user_id="...")  # explicit override
```

If `workspace_dir()` is called without a `user_id` and no context is set, it raises `NoUserContextError`. This is deliberate — we want a loud crash over a silent leak.

## When to use which

- **Per-relation state** (MEMORY.md, USER.md, day_shape, threads): `workspace_dir()`
- **Jarvis' own state** (SOUL, IDENTITY, dreams, creative impulses, jobs queue): `shared_dir()`
- **Per-user queued work** (scheduled_tasks, initiatives, approvals): DB row with `scheduled_for_user_id`. Dispatcher binds workspace_context via `core.services.scheduled_task_runner.fire_scheduled_task` before firing.

## Permissions

`role='member'` (Mikkel, Michelle):
- Can chat, use operator tools on their own machine, schedule their own tasks
- Cannot mint tokens or write to shared/ SOUL.md, IDENTITY.md, MANIFEST.md
- Read-filtered: see Jarvis-state + their own relation, never other users'

`role='owner'` (Bjørn):
- Can do everything, can mint tokens, can write shared/
- Normal session sees Jarvis-state + Bjørn-relation only (same filter)
- Admin paths (Mission Control, debug tools) can bypass filter for observability

## Database tags

Three columns added in the multi-user refactor:

- `scheduled_for_user_id` (on scheduled_tasks, runtime_initiatives, capability_approval_requests, tool_intent_approval_requests) — who the queued action is for
- `initiated_by` (same tables) — `user:<discord_id>` or `jarvis-self`
- `relevant_to_users` (on cognitive_chronicle_entries, dream tables, runtime_initiatives) — JSON array of discord_ids who should see this row. NULL = visible to all relations.
