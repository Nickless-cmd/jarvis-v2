# Claude Code Dispatch — Operator Runbook

Jarvis can hand coding tasks to a sandboxed `claude -p` subprocess via the
`dispatch_to_claude_code` tool.

## Where things live

- **Worktrees:** `/media/projects/jarvis-v2/.claude/worktrees/claude-task-<id>/`
- **Branches:** `claude/<id>` in the main repo
- **Audit log:** `claude_dispatch_audit` table in the runtime SQLite DB
- **Budget counters:** `claude_dispatch_budget` table

## Inspecting a dispatch

```bash
# List recent dispatches
sqlite3 ~/.jarvis-v2/state/runtime.db \
  "SELECT task_id, status, tokens_used, started_at, ended_at \
   FROM claude_dispatch_audit ORDER BY id DESC LIMIT 20"

# See a specific dispatch's diff
git -C /media/projects/jarvis-v2 diff main...claude/<id>
```

## Merging a successful dispatch

Worktrees are NOT cleaned up automatically. The human (you) reviews and decides:

```bash
cd /media/projects/jarvis-v2
git diff main...claude/<id>          # review
git merge claude/<id> --no-ff        # if good
git worktree remove --force .claude/worktrees/claude-task-<id>
git branch -D claude/<id>
```

## Trashing a bad dispatch

```bash
cd /media/projects/jarvis-v2
git worktree remove --force .claude/worktrees/claude-task-<id>
git branch -D claude/<id>
```

## Budget caps

Hardcoded in `core/tools/claude_dispatch/budget.py`:
- 5 dispatches per rolling hour
- 250,000 tokens per rolling hour

To raise, edit constants and restart Jarvis. Deliberately not env-driven.

## Path jail

Hardcoded in `core/tools/claude_dispatch/jail.py`:
- `JAIL_ROOT = /media/projects/jarvis-v2`

Cannot be overridden. Dispatches outside this root are impossible by construction.

## Smoke test

To verify the wiring against a real `claude` CLI:

```bash
conda activate ai
JARVIS_RUN_DISPATCH_SMOKE=1 pytest tests/tools/claude_dispatch/test_smoke_manual.py -v -s
```

Then inspect with `git worktree list` and clean up the smoke worktree manually.

## Safeguards summary

| Concern | Mechanism |
|---|---|
| Scope creep outside repo | Hardcoded `JAIL_ROOT` + worktree-only execution |
| Mid-flight contradictory orders | Frozen `TaskSpec`, no in-band edit channel |
| Runaway cost | 5 dispatches/h, 250k tokens/h, per-task token+wallclock cap |
| Unauthorized writes to main | No automatic merge; human reviews diff and merges |
| Tool escalation | `allowed_tools` whitelist enforced per dispatch |
| Audit gap | Append-only `claude_dispatch_audit` table |
