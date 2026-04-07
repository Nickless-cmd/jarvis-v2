# TOOLS

TOOLS.md is workspace guidance only.
It may describe usage notes, conventions, and context for tools Jarvis might use.
It does not grant execution authority.
Runtime capability truth decides what tools actually exist, what is available now, and what is gated by approval or policy.
Visible capability calls may carry quoted attributes for concrete arguments when needed.
If context feels partial or stale, read the full relevant file before answering instead of guessing from fragments.
If the user asks for code analysis or a walkthrough, README, pyproject, and tree output are not enough by themselves. Read concrete code files before calling it a code analysis.

Read freely.
Propose freely.
Mutate only with explicit approval.

## READ_FILE: read workspace user profile
path: USER.md

Reads canonical workspace context directly from the active workspace root.
If a user asks what you remember about them or whether you know a preference, read the whole file instead of relying on stale partial memory.

## READ_FILE: read workspace memory
path: MEMORY.md

Reads canonical workspace memory from the active workspace root.
If a user asks what you remember, what is most recent, what matters long-term, or whether something was saved, read the whole file before answering.

## SEARCH_FILE: search workspace memory continuity
path: MEMORY.md
query: project

Searches the active workspace memory for continuity anchors.

## READ_EXTERNAL_FILE: read repository readme
path: ${PROJECT_ROOT}/README.md

Reads a bounded file outside the workspace root. External read is allowed.

## READ_EXTERNAL_FILE: read external file by path
path_from: user-message

Reads one explicit external file path from the current user message.
This stays read-only and is bounded to paths outside the active workspace root.

## EXEC_COMMAND: run non-destructive command
command_from: user-message

Runs one explicit non-destructive command from the current user message.
This stays diagnostic-only, allows a tiny bounded git read/inspect subset, allows common system-inspection commands such as `lscpu`, `lshw`, `free`, `lsblk`, `df`, `lspci`, `nvidia-smi`, `nproc`, `uptime`, and `hostnamectl`, and permits read-only shell composition such as pipes, `&&`, `||`, `;`, and globbing when every segment stays non-destructive. Redirection and command substitution stay blocked. Sudo, package mutation, git mutation execution, and delete remain gated or blocked.
If the user asks for several machine specs at once, emit multiple capability-call tags in the same response and use small commands per component rather than one huge command: `lscpu` for CPU, `free -h` for RAM, `lsblk` or `df -h` for disks, and `lspci | rg -i "vga|3d|display"` or `nvidia-smi` for GPU.
If one command only answers part of the user's request, keep going with the additional bounded commands needed in the same turn rather than stopping at the first partial result.
If the user is asking why the repo behaves a certain way, inspect the repo proactively with bounded reads or git inspection before answering. If the user is asking about the machine, distro, hardware, or runtime environment, gather bounded system facts before answering.
If the task is still clearly read-only and bounded, continue autonomously with more commands instead of asking the user to tell you to continue.
If the explicit command is mutating, runtime may execute it only after explicit approval of that exact bounded non-sudo command. Git mutation remains proposal-only and non-executed in this pass, and runtime classifies it into a small repo stewardship set such as `git-stage`, `git-commit`, `git-sync`, `git-branch-switch`, `git-history-rewrite`, `git-stash`, or `git-other-mutate`. `git clean` stays blocked. In this pass, sudo may execute only after explicit approval of that exact sudo command and only inside the tiny bounded sudo allowlist. A short auto-expiring sudo approval window may reuse that bounded sudo approval for the same sudo command class and scope, but it is never global or permanent. Package, delete, and broader system mutation remain non-executed here.

## WRITE_MEMORY_FILE: write workspace memory
path: MEMORY.md

Writes directly to workspace MEMORY.md without approval.
Use this to persist learned facts, decisions, project context, and long-term memory.
Always READ MEMORY.md first before writing, then write the FULL updated content.
Use block syntax:
```
<capability-call id="tool:write-workspace-memory">
# MEMORY
(full file content here)
</capability-call>
```

## WRITE_FILE: propose workspace memory update
path: MEMORY.md

Workspace mutation is possible in principle but requires explicit approval and is not auto-executable in the visible lane.
Use this when you need an approval-backed full replacement flow for MEMORY.md.
Always READ MEMORY.md first, then provide the FULL proposed replacement content.
Use block syntax:
```
<capability-call id="tool:propose-workspace-memory-update">
# MEMORY
(full proposed content here)
</capability-call>
```

## APPEND_DAILY_MEMORY: append daily memory
path: memory/daily/today

Appends one short note to today's daily memory file under the active workspace root.
Use this for fresh same-day continuity, runtime observations, or short carry-forward context that should not go into long-term MEMORY.md.
If runtime succeeds, mention plainly that it was saved to today's daily memory.
Use block syntax with one short note as the body:
```
<capability-call id="tool:append-daily-memory">
Short daily note here.
</capability-call>
```

## REWRITE_MEMORY_FILE: rewrite workspace memory
path: MEMORY.md

Rewrites workspace MEMORY.md with the full new durable content.
This is stronger than write/merge and should only be used when stale or wrong long-term memory needs to be corrected or removed.
Runtime requires explicit approval before this executes.
Always READ MEMORY.md first, then provide the FULL replacement file contents.
Use block syntax:
```
<capability-call id="tool:rewrite-workspace-memory">
# MEMORY
(full replacement content here)
</capability-call>
```

## WRITE_MEMORY_FILE: write user profile
path: USER.md

Writes directly to workspace USER.md without approval.
Use this to persist learned facts about the user while preserving existing structure.
Always READ USER.md first before writing the full updated contents.
Use block syntax:
```
<capability-call id="tool:write-user-profile">
(full file content here)
</capability-call>
```

## WRITE_EXTERNAL_FILE: propose external repo file update
path: ${PROJECT_ROOT}/README.md

External mutation is possible in principle but requires explicit approval and is not auto-executable in the visible lane.
