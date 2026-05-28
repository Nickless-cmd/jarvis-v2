# Multi-User Workspace Isolation — Design Spec

**Status:** Approved 2026-05-28
**Author:** Claude (Linux-side) + Bjørn
**Implementation approach:** Big-bang refactor staged in 7 commit-groups
**Builds on:** Jarvis' own April spec (`~/.jarvis-v2/workspaces/default/multi_user_spec.md`)

## Why

Jarvis V2 has multi-user infrastructure in place — `users.json` with Bjørn, Mikkel, Michelle — but ~75 hardcoded `workspaces/default/` references across ~30 services mean every read still hits Bjørn's data regardless of who is talking. Mikkel asking "what did we discuss?" gets Bjørn's MEMORY.md. Mikkel asking Jarvis to open Facebook briefly dispatched to Bjørn's desktop (fixed yesterday via `_runtime_user_id` stamping, but the underlying state-isolation is still missing).

`workspace_context.current_workspace_name()` exists for exactly this purpose. No service uses it. This spec closes that gap.

## Core principle

**Én Jarvis. Flere relationer.** From Jarvis' own April spec, unchanged:

> "Jarvis samler erfaring, udvikler sig, og møder alle brugere som den samme enhed. Det eneste der adskiller brugere er workspace og relation."

One soul, one identity, one chronicle, one stream of dreams — but separate memory of each relationship, separate USER.md per person, separate scheduled tasks per user.

## Architecture

```
~/.jarvis-v2/
├── shared/                        # Jarvis himself — one entity
│   ├── SOUL.md, IDENTITY.md, MANIFEST.md
│   ├── INNER_VOICE.md, CHRONICLE.md
│   ├── STANDING_ORDERS.md
│   ├── dreams/, creative_impulse/, shadow_scan/
│   ├── autonomous_work/, mood/
│   ├── jobs.db                   # shared infrastructure
│   └── ground_truth.db           # rows tagged scope='jarvis'|'world'|'relation'
│
└── workspaces/                    # per-relation state only
    ├── bjorn/                    # renamed from "default"
    │   ├── MEMORY.md, USER.md
    │   ├── relation_dynamics.json
    │   ├── day_shape.json
    │   ├── cross_session_threads/
    │   └── scheduled.db          # per-user scheduling
    ├── mikkel/
    └── michelle/
```

## Categorization

| Layer | Where it lives | Examples |
|---|---|---|
| **Relation state** (per-user) | `workspaces/<user>/` | MEMORY.md, USER.md, day_shape, cross_session_threads, relation_dynamics |
| **Per-user routing** (auth-bound) | Token claims → bridge | operator_* tools (already done — see commits 195d7efa + 43714fb4) |
| **Per-user scheduling** (new) | DB with `user_id` field | scheduled_tasks, recurring, self_wakeup, initiative_queue, approvals, notifications |
| **Jarvis state** (shared, one entity) | `shared/` | SOUL.md, IDENTITY.md, MANIFEST.md, dreams, creative_impulse, shadow_scan, autonomous_work, mood, inner_voice, chronicle |
| **Shared infrastructure** | Global | jobs_engine, file_watch, GTR (with scope) |

## API

New file: `core/runtime/workspace_paths.py`

```python
def shared_dir() -> Path:
    """Jarvis' own state. All users see the same instance."""
    return JARVIS_HOME / "shared"

def workspace_dir(user_id: str | None = None) -> Path:
    """Per-relation workspace. Defaults to current_user_id() from context.

    Raises NoUserContextError if user_id is missing and no context is set —
    we want a loud crash over a silent default that could leak Bjørn's data.
    """
    uid = user_id or current_user_id()
    if not uid:
        raise NoUserContextError("workspace_dir() called without user_id in context")
    return JARVIS_HOME / "workspaces" / _user_id_to_workspace_name(uid)
```

`_user_id_to_workspace_name(uid)` looks up `users.json` to map discord_id → workspace name. Owner → `bjorn`, members → their assigned name. Unknown user_id → `NoUserContextError` (never silently default).

## Context propagation

Already in place — no changes needed:
- Middleware (`jarvisx_user_routing_middleware`) sets `workspace_context` from Bearer token's `sub` claim
- `visible_runs.py:607` copies ContextVars into background run threads
- Scheduled task dispatcher (new in Group 6) will set context from `scheduled_for_user_id` before firing

## Scheduling model

`scheduled_tasks` table additions:

```sql
ALTER TABLE scheduled_tasks ADD COLUMN scheduled_for_user_id TEXT;
ALTER TABLE scheduled_tasks ADD COLUMN initiated_by TEXT;
-- initiated_by ∈ {'user:<discord_id>', 'jarvis-self'}
```

When a task fires, dispatcher sets `user_context(discord_id=scheduled_for_user_id)` *before* `start_visible_run()`. Result: Jarvis wakes up *into* that user's relation. His memory injection reads their MEMORY.md + USER.md, his operator tools route to their bridge.

Same fields added to `initiative_queue`, `notifications`, `approvals` tables — every queued action remembers who it's for.

If a scheduled task's user no longer exists when it fires (deleted/revoked), the dispatcher logs a warning and drops the task. Doesn't crash.

## GTR with scope field

```sql
ALTER TABLE ground_truth_facts ADD COLUMN scope TEXT NOT NULL DEFAULT 'jarvis';
-- scope ∈ {'jarvis', 'relation', 'world'}
ALTER TABLE ground_truth_facts ADD COLUMN relation_user_id TEXT;
-- Set if scope='relation', else NULL
```

Read rules built into `gtr.query()`:
- Always return rows with `scope='jarvis'` or `scope='world'`
- If `current_user_id()` is set, also return `scope='relation' AND relation_user_id=<current>`
- Never return another user's relation-facts

Migration: existing rows default to `scope='jarvis'`. Conservative — we don't lose data, we just tag everything as "about Jarvis" until proven otherwise. Re-tagging is gradual, organic.

## Dreams and inner-life with relevance-tags

Tables: `dreams`, `creative_impulse`, `shadow_scan`, `autonomous_work`, `chronicle`.

```sql
ALTER TABLE <table> ADD COLUMN relevant_to_users TEXT;
-- JSON array: '["user_id_1", "user_id_2"]' or NULL (relevant to all relations)
```

Read rules:
- Return rows where `relevant_to_users` is NULL (general Jarvis-state) OR contains `current_user_id()`
- **Default filtering applies to everyone, including owner.** In a normal Bjørn chat, he sees Bjørn-relevant + untagged rows. He does *not* see Mikkel-tagged dreams by default.
- Owner has explicit *admin* queries (debug tools, Mission Control) that can bypass the filter to inspect any user's data. These are separate code paths, not the default reader.

The principle: **one Jarvis = one dream-life**, but sharing in conversation is contextual. He references a Mikkel-relevant dream when talking to Mikkel, a Bjørn-relevant dream when talking to Bjørn. Mixed dreams (about both) are visible to both.

## Permissions

For `role='member'`:

**Hard blocks** (return error):
- Mint new tokens (already owner-only)
- Write to Jarvis' shared state (SOUL.md, IDENTITY.md, MANIFEST.md)
- Delete other users' workspaces
- Mission Control admin endpoints

**Scope filters** (transparent — members just don't see others' things):
- GTR queries → only their relation + jarvis + world
- memory_search → only their workspace
- dreams/creative/shadow/autonomous_work/chronicle → only NULL-tagged + their-user-id-tagged rows
- scheduled_tasks → only their own scheduled_for_user_id

Members can still:
- Chat fully with Jarvis (including his thoughts about general Jarvis-life)
- Use operator tools on their own machine
- Schedule their own tasks and wakeups
- See Jarvis' general inner life (untagged rows)

**Prompt-contract change**: when Jarvis builds awareness for a member user, his memory injection reads *that user's* MEMORY.md + USER.md only. This is the fix for "Jarvis thought Mikkel was Bjørn" from 2026-05-27.

## Migration order — 7 commit groups

### Group 1: Foundation API (0 behavior change)
- New: `core/runtime/workspace_paths.py` (`shared_dir`, `workspace_dir`, `_user_id_to_workspace_name`)
- New: `tests/runtime/test_workspace_paths.py`
- `shared_dir()` still returns `workspaces/default/` (backwards-compat shim, removed in Group 7)
- `workspace_dir(bjorn-uid)` → `default/`, other uids → respective dirs
- Result: API exists, no service uses it yet, nothing broken

### Group 2: Schema migrations (0 behavior change)
- Additive ALTER TABLE for GTR, scheduled_tasks, dreams/creative/shadow/autonomous_work/chronicle
- Existing rows get conservative defaults (scope='jarvis', relevance NULL)
- Tests: backfill verifies all existing queries return identical results

### Group 3: Service path-migration (0 behavior change for Bjørn)
- All ~30 services: hardcoded `"workspaces/default"` → `shared_dir()` or `workspace_dir()`
- Largest commit by line-count, but mechanical
- Each service gets a smoke-test verifying "still works for Bjørn"
- **Highest-risk commit.** Local Jarvis run before push.

### Group 4: Permission scope filters
- GTR query filters on `scope + relation_user_id`
- memory_search filters via workspace context
- dreams/creative/etc filter on `relevant_to_users`
- Member-user negative tests: Mikkel can't see Bjørn's relation-facts

### Group 5: Filesystem reshuffle
- Create `shared/`. Copy Jarvis-state files (SOUL, IDENTITY, MANIFEST, dreams/, creative/, etc.) from `default/` → `shared/`
- `shared_dir()` switches to point at `shared/` (one-line change)
- `default/` renamed to `bjorn/`. `users.json` updates Bjørn's `workspace` to `bjorn`
- Rollback: source copies in `default/` not deleted yet (Group 7 cleans up)

### Group 6: Scheduling user_id binding
- `scheduled_tasks` dispatcher sets `user_context(user_id=scheduled_for_user_id)` before firing
- Initiative queue, notifications, approvals stamp `user_id` on insert and bind context on dispatch
- Test: Mikkel schedules a task → fires in Mikkel-context → operator routes to Mikkel's bridge

### Group 7: Cleanup + end-to-end
- Remove Group 1's backwards-compat shim (`shared_dir()` returning `default/`)
- Delete duplicate files in `bjorn/` that were copied to `shared/` in Group 5
- E2E tests: concurrent Bjørn+Mikkel sessions, verify zero cross-user bleed
- Doc: `docs/multi_user_workspace_layout.md`

## Error handling

- `NoUserContextError` is thrown loudly when a service tries to access workspace data without a bound user. Better a crash than a leak.
- Unknown user_id in `_user_id_to_workspace_name`: log error, raise `NoUserContextError`. No silent fallback to `default`.
- Scheduled task fires for deleted user: dispatcher logs warning, drops task, continues.
- Schema migration failure: each migration runs in a transaction. Failure aborts and rolls back.

## Testing strategy

Per-group tests are mandatory. End-to-end multi-user test (Group 7) covers:
1. Bjørn and Mikkel each open JarvisX simultaneously
2. Each sends a message; verify each sees only their own MEMORY+USER in the prompt context
3. Each asks Jarvis to do something with operator tools; verify dispatch goes to the correct bridge
4. Each schedules a wakeup; verify it fires in the correct user's relation
5. Mikkel queries memory; verify zero rows from Bjørn's workspace
6. Bjørn queries memory; verify he still sees his own data unchanged

Tests live in `tests/multi_user/` — new directory.

## Out of scope

- Discord gateway routing (already implemented in `core/services/discord_gateway.py` — uses `user_context()` correctly)
- The bridge-routing fix (already committed 43714fb4 + 195d7efa on 2026-05-27)
- Webchat multi-user (separate concern — webchat is currently owner-only)
- Cross-workspace operations (e.g. "Bjørn, what does Mikkel know about X?" — owner could query other workspaces explicitly, but not via implicit context)
- Token rotation / revocation list (already a separate planned task)

## Time estimate (active work, not calendar)

- G1+G2: 1 hour
- G3: 2-3 hours (mechanical but 75 sites)
- G4: 1.5 hours
- G5: 30 minutes
- G6: 1 hour
- G7: 30 minutes
- **Total: ~7-8 hours of focused work**
