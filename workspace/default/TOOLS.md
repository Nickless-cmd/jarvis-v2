# TOOLS

Runtime capability truth is authoritative.
This file is guidance only and must match current runtime capabilities.

Visible capability contract:
- If you use a visible capability, emit exactly `<capability-call id="..."/>`.
- The capability-call must stand alone, with no surrounding prose.
- JSON tool calls are not the contract.

Callable now:
- `tool:read-workspace-user-profile`
- `tool:search-workspace-memory-continuity`
- `tool:read-repository-readme`
- `tool:read-external-file-by-path`

Approval-gated now:
- `tool:propose-workspace-memory-update`
- `tool:propose-external-repo-file-update`

Write proposals are approval-gated.
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

## WRITE_FILE: propose workspace memory update
path: MEMORY.md

Proposes a bounded workspace write for `MEMORY.md`.
This is approval-gated and is not auto-executable.

## WRITE_EXTERNAL_FILE: propose external repo file update
path: ${PROJECT_ROOT}/README.md

Proposes a bounded external file update for the repository README.
This is approval-gated and is not auto-executable.
