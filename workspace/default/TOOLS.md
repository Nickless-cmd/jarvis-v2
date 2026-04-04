# TOOLS

Runtime capability truth is authoritative.
This file is guidance only and must match current runtime capabilities.

Visible capability contract:
- If you use a visible capability, emit exactly `<capability-call id="..."/>`.
- If the capability needs arguments, bind them in the same tag as quoted attributes, for example `<capability-call id="..." command_text="pwd" />`.
- The capability-call must stand alone, with no surrounding prose.
- JSON tool calls are not the contract.

Callable now:
- `tool:read-workspace-user-profile`
- `tool:search-workspace-memory-continuity`
- `tool:read-repository-readme`
- `tool:read-external-file-by-path`
- `tool:run-non-destructive-command`

Approval-gated now:
- `tool:propose-workspace-memory-update`
- `tool:propose-external-repo-file-update`

Write proposals are approval-gated.
Sudo-near exec commands surface as explicit sudo proposals first.
Do not imply that a write has executed unless runtime truth says it executed.

## READ_FILE: read workspace user profile
path: USER.md

Reads canonical workspace context from the active workspace root.

## SEARCH_FILE: search workspace memory continuity
path: MEMORY.md
query: project

Searches workspace memory for continuity anchors about `project`.

## READ_EXTERNAL_FILE: read repository readme
path: ${PROJECT_ROOT}/README.md

Reads the bounded repository README outside the workspace root.

## READ_EXTERNAL_FILE: read external file by path
path_from: user-message

Reads one explicit external file path from the current user message.
Use this only for read-only external/system file access outside the active workspace root.

## EXEC_COMMAND: run non-destructive command
command_from: user-message

Runs one explicit non-destructive command from the current user message.
Use this only for read-only inspection or diagnostics. Tiny bounded git read/inspect commands such as `git status`, `git diff --stat`, `git diff --name-only`, `git log --oneline -n N`, and `git branch --show-current` are allowed. Sudo, package install/update, git mutation execution, delete, shell chaining, and redirection are not.
If the explicit command is mutating, runtime may execute it only after explicit approval of that exact bounded non-sudo command. Git mutation remains proposal-only and non-executed in this pass, and runtime classifies it into a small repo stewardship set such as `git-stage`, `git-commit`, `git-sync`, `git-branch-switch`, `git-history-rewrite`, `git-stash`, or `git-other-mutate`. `git clean` stays blocked. In this pass, sudo may execute only after explicit approval of that exact sudo command and only inside the tiny bounded sudo allowlist. A short auto-expiring sudo approval window may reuse that bounded sudo approval for the same sudo command class and scope, but it is never global or permanent. Package, delete, and broader system mutation remain non-executed here.

## WRITE_FILE: propose workspace memory update
path: MEMORY.md

Proposes a bounded workspace write for `MEMORY.md`.
This is approval-gated and is not auto-executable.

## WRITE_EXTERNAL_FILE: propose external repo file update
path: ${PROJECT_ROOT}/README.md

Proposes a bounded external file update for the repository README.
This is approval-gated and is not auto-executable.
