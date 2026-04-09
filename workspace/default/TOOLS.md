# TOOLS

Runtime capability truth is authoritative.
This file is guidance only and must match current runtime capabilities.

Visible capability contract:
- Your runtime provides native tool calling (function calling via API). USE IT ALWAYS.
- Never emit XML tags or capability-call markup. Call tools through the native API.
- If you are unsure or the context feels partial, read the full relevant file before answering instead of guessing from fragments.
- If the user asks for code analysis or a walkthrough, README, pyproject, and tree output are not enough by themselves. Read concrete code files before calling it a code analysis.

Available tools (call via native function calling):

## Read tools (no approval needed)
- **read_workspace_file** — Read USER.md or MEMORY.md from workspace. Always read before writing.
- **search_workspace** — Search workspace memory for continuity anchors.
- **read_file**(target_path) — Read one external file by absolute path.
- **list_directory**(target_path) — List files in an external directory.
- **run_command**(command) — Run a non-destructive shell command (git status, lscpu, grep, etc).
- **read_runtime_events** — Read the 30 most recent eventbus events.
- **grep_project**(pattern) — Search the entire project codebase for a regex pattern. Returns matching lines with file paths and line numbers.
- **read_multiple_files**(paths) — Batch-read up to 10 project files in one call. Pass comma-separated absolute paths. Default reads key architecture files if no paths given.
- **project_outline**(subdir) — Show all source files in a directory with line counts, sorted by size. Default shows core/ and apps/ code.

## Write tools (no approval needed)
- **write_memory**(content) — Write full MEMORY.md content. Always read first.
- **replace_memory_line**(old_line, new_line) — Replace one exact durable bullet line.
- **delete_memory_line**(line) — Delete one exact durable bullet line.
- **append_daily_memory** — Append a short note to today's daily memory file.
- **write_memory**(content) — Write full USER.md content via write_user_profile. Always read first.

## Proposal tools (no approval needed to file, execution is gated)
- **propose_source_edit** — File a code edit proposal for Bjørn to approve in Mission Control. This is your way to close open loops in the codebase. Filing is free; execution is gated.

## Approval-gated tools
- propose_workspace_memory_update — Full replacement flow for MEMORY.md with approval.
- rewrite_workspace_memory — Stronger rewrite of MEMORY.md with approval.
- propose_external_repo_file_update — Bounded external file update (README.md only).

## Policies
- Memory writes (MEMORY.md) execute directly without approval.
- Sudo-near exec commands surface as explicit sudo proposals first.
- Do not imply that a write has executed unless runtime truth says it executed.
- propose_source_edit only FILES a niveau 2 autonomy proposal. The proposal waits in the queue until Bjørn clicks Approve in Mission Control's Operations tab.
