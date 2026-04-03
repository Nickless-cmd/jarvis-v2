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
This stays diagnostic-only and blocks sudo, package mutation, git mutation, delete, shell chaining, and redirection.
If the explicit command is mutating or sudo-near, runtime may carry it only as an approval-gated proposal and not as executed work.

## WRITE_FILE: propose workspace memory update
path: MEMORY.md

Workspace mutation is possible in principle but requires explicit approval and is not auto-executable in the visible lane.

## WRITE_EXTERNAL_FILE: propose external repo file update
path: ${PROJECT_ROOT}/README.md

External mutation is possible in principle but requires explicit approval and is not auto-executable in the visible lane.
