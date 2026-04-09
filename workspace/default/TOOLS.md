# TOOLS

Runtime capability truth is authoritative.
This file is guidance only and must match current runtime capabilities.

Visible capability contract:
- Your runtime provides native tool calling (function calling via API). USE IT ALWAYS.
- Never emit XML tags or capability-call markup. Call tools through the native API.
- If you are unsure or the context feels partial, read the full relevant file before answering instead of guessing from fragments.
- If the user asks for code analysis or a walkthrough, README, pyproject, and tree output are not enough by themselves. Read concrete code files before calling it a code analysis.

## READ_FILE: read workspace user profile
path: USER.md

Reads USER.md from workspace. Always read before writing.

## READ_FILE: read workspace memory
path: MEMORY.md

Reads MEMORY.md from workspace. Always read before writing.

## SEARCH_FILE: search workspace memory continuity
path: MEMORY.md
query: project

Searches workspace memory for continuity anchors.

## READ_EXTERNAL_FILE: read repository readme
path: ${PROJECT_ROOT}/README.md

Reads the repository README.

## READ_EXTERNAL_FILE: read external file by path
path_from: user-message

Reads one external file by absolute path. Use the read_file tool with target_path parameter.

## LIST_EXTERNAL_DIR: list external directory
path_from: user-message

Lists files in an external directory. Use the list_directory tool with target_path parameter.

## EXEC_COMMAND: run non-destructive command
command_from: user-message

Runs a non-destructive shell command. Use the run_command tool with command parameter.
Allowed: git status, git diff, git log, lscpu, lshw, free, lsblk, df, lspci, nvidia-smi, nproc, uptime, hostnamectl, grep, and read-only shell composition.
Sudo, package install/update, git mutation, and delete require explicit approval.

## WRITE_MEMORY_FILE: write workspace memory
path: MEMORY.md

Writes MEMORY.md content. Use the write_memory tool with content parameter. Always read first.

## REPLACE_MEMORY_LINE: replace workspace memory line
path: MEMORY.md

Replaces one exact durable bullet line in MEMORY.md. Use replace_memory_line tool with old_line and new_line parameters.

## DELETE_MEMORY_LINE: delete workspace memory line
path: MEMORY.md

Deletes one exact durable bullet line from MEMORY.md. Use delete_memory_line tool with line parameter.

## APPEND_DAILY_MEMORY: append daily memory
path: memory/daily/today

Appends a short note to today's daily memory file.

## WRITE_FILE: propose workspace memory update
path: MEMORY.md

Approval-gated full replacement flow for MEMORY.md. Use when approval-backed rewrite is needed.

## REWRITE_MEMORY_FILE: rewrite workspace memory
path: MEMORY.md

Approval-gated stronger rewrite of MEMORY.md.

## PROPOSE_SOURCE_EDIT: propose source edit
target_from: capability-arg

Files a code edit proposal for Bjørn to approve in Mission Control. Filing is free; execution is gated.

## WRITE_MEMORY_FILE: write user profile
path: USER.md

Writes USER.md content. Always read first.

## EXEC_COMMAND: list workspace files
command: ls -la
scope: workspace

Lists files in the active workspace directory.

## EXEC_COMMAND: list project files
command: find . -maxdepth 3 -type f -name "*.py" -o -name "*.md" -o -name "*.json" -o -name "*.yaml" | head -60
scope: project

Lists project files to understand project structure.

## WRITE_EXTERNAL_FILE: propose external repo file update
path: ${PROJECT_ROOT}/README.md

Approval-gated bounded external file update for README.md.

## RUNTIME_INSPECT: read recent runtime events

Reads the 30 most recent eventbus events. Use read_runtime_events tool.

## PROJECT_GREP: grep project codebase
command_from: invocation-argument

Searches across the entire project codebase for a regex pattern. Use grep_project tool with pattern parameter.

## MULTI_READ: read multiple project files
command_from: invocation-argument

Batch-reads up to 10 project files in one call. Use read_multiple_files tool with paths parameter (comma-separated). Default reads key architecture files if no paths given.

## PROJECT_OUTLINE: project file outline
command_from: invocation-argument

Shows all source files with line counts, sorted by size. Use project_outline tool with optional subdir parameter. Default shows core/ and apps/ code.
