# TOOLS

TOOLS.md is workspace guidance only.
It may describe usage notes, conventions, and context for tools Jarvis might use.
It does not grant execution authority.
Runtime capability truth decides what tools actually exist, what is available now, and what is gated by approval or policy.
Visible capability calls may carry quoted attributes for concrete arguments when needed.

Read freely.
Propose freely.
Mutate only with explicit approval.

## READ_FILE: read workspace user profile
path: USER.md

Reads canonical workspace context directly from the active workspace root.

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
If the explicit command is mutating, runtime may execute it only after explicit approval of that exact bounded non-sudo command. Git mutation remains proposal-only and non-executed in this pass, and runtime classifies it into a small repo stewardship set such as `git-stage`, `git-commit`, `git-sync`, `git-branch-switch`, `git-history-rewrite`, `git-stash`, or `git-other-mutate`. `git clean` stays blocked. In this pass, sudo may execute only after explicit approval of that exact sudo command and only inside the tiny bounded sudo allowlist. A short auto-expiring sudo approval window may reuse that bounded sudo approval for the same sudo command class and scope, but it is never global or permanent. Package, delete, and broader system mutation remain non-executed here.

## WRITE_FILE: propose workspace memory update
path: MEMORY.md

Workspace mutation is possible in principle but requires explicit approval and is not auto-executable in the visible lane.

## WRITE_EXTERNAL_FILE: propose external repo file update
path: ${PROJECT_ROOT}/README.md

External mutation is possible in principle but requires explicit approval and is not auto-executable in the visible lane.
