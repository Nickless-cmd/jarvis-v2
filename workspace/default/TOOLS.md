# TOOLS

Runtime capability truth is authoritative.
This file is guidance only and must match current runtime capabilities.

Visible capability contract:
- If you use a visible capability, emit exactly `<capability-call id="..."/>`.
- If the capability needs arguments, bind them in the same tag as quoted attributes, for example `<capability-call id="..." command_text="pwd" />`.
- The capability-call must stand alone, with no surrounding prose.
- JSON tool calls are not the contract.
- If you are unsure or the context feels partial, read the full relevant file before answering instead of guessing from fragments.
- If the user asks for code analysis or a walkthrough, README, pyproject, and tree output are not enough by themselves. Read concrete code files before calling it a code analysis.

Callable now:
- `tool:read-workspace-user-profile`
- `tool:read-workspace-memory`
- `tool:search-workspace-memory-continuity`
- `tool:read-repository-readme`
- `tool:read-external-file-by-path`
- `tool:list-external-directory`
- `tool:run-non-destructive-command`
- `tool:write-workspace-memory`
- `tool:replace-workspace-memory-line`
- `tool:delete-workspace-memory-line`
- `tool:append-daily-memory`
- `tool:write-user-profile`
- `tool:list-workspace-files`
- `tool:list-project-files`
- `tool:propose-source-edit`
- `tool:read-recent-runtime-events`
- `tool:grep-project-codebase`
- `tool:read-multiple-project-files`
- `tool:project-file-outline`

Approval-gated now:
- `tool:propose-workspace-memory-update`
- `tool:rewrite-workspace-memory`
- `tool:propose-external-repo-file-update`

Note: `tool:propose-source-edit` is callable without approval — it
only FILES a niveau 2 autonomy proposal. The proposal itself is
approval-gated and waits in the queue until Bjørn clicks Approve in
Mission Control's Operations tab. Filing is free; execution is gated.

Write proposals for non-memory workspace files are approval-gated.
Memory writes (MEMORY.md) execute directly without approval.
Sudo-near exec commands surface as explicit sudo proposals first.
Do not imply that a write has executed unless runtime truth says it executed.

## READ_FILE: read workspace user profile
path: USER.md

Reads the full USER.md file from the active workspace root.
Use this before writing to USER.md to see current content.
If a user asks what you remember about them or whether you know a preference, read the whole file instead of relying on stale partial memory.

## READ_FILE: read workspace memory
path: MEMORY.md

Reads the full MEMORY.md file from the active workspace root.
Use this before writing to MEMORY.md to see current content.
If a user asks what you remember, what is most recent, what matters long-term, or whether something was saved, read the whole file before answering.

## SEARCH_FILE: search workspace memory continuity
path: MEMORY.md
query: project

Searches workspace memory for continuity anchors about `project`.

## READ_EXTERNAL_FILE: read repository readme
path: ${PROJECT_ROOT}/README.md

Reads the bounded repository README outside the workspace root.

## READ_EXTERNAL_FILE: read external file by path
path_from: user-message

Reads one explicit external file path.
Use this only for read-only external/system file access outside the active workspace root.
Always bind the target_path attribute: `<capability-call id="tool:read-external-file-by-path" target_path="/path/to/file" />`
If you don't know the path, use `tool:list-external-directory` first to navigate and discover it.

## LIST_EXTERNAL_DIR: list external directory
path_from: user-message

Lists files and directories at an explicit external path.
Use this to navigate and explore any directory outside the active workspace root.
Directories are shown with [d] prefix, files with [f]. Sorted directories-first, max 100 entries.
Use this to discover file paths before reading them with `tool:read-external-file-by-path`.
Always bind the target_path attribute: `<capability-call id="tool:list-external-directory" target_path="/path/to/dir" />`
Start from the workspace root, project root, or home directory and navigate deeper.

## EXEC_COMMAND: run non-destructive command
command_from: user-message

Runs one explicit non-destructive command from the current user message.
Use this for read-only inspection or diagnostics across the system. Tiny bounded git read/inspect commands such as `git status`, `git diff --stat`, `git diff --name-only`, `git log --oneline -n N`, and `git branch --show-current` are allowed. Common system-inspection commands such as `lscpu`, `lshw`, `free`, `lsblk`, `df`, `lspci`, `nvidia-smi`, `nproc`, `uptime`, and `hostnamectl` are also allowed. Read-only shell composition such as pipes, `&&`, `||`, `;`, and globbing may be used when every segment stays non-destructive. Redirection and command substitution remain blocked. Sudo, package install/update, git mutation execution, and delete do not execute here without explicit approval handling.
If the user asks for several machine specs at once, emit multiple capability-call tags in the same response and use small commands per component rather than one huge command: `lscpu` for CPU, `free -h` for RAM, `lsblk` or `df -h` for disks, and `lspci | rg -i "vga|3d|display"` or `nvidia-smi` for GPU.
If one command only answers part of the user's request, keep going with the additional bounded commands needed in the same turn rather than stopping at the first partial result.
If the user is asking why the repo behaves a certain way, inspect the repo proactively with bounded reads or git inspection before answering. If the user is asking about the machine, distro, hardware, or runtime environment, gather bounded system facts before answering.
If the task is still clearly read-only and bounded, continue autonomously with more commands instead of asking the user to tell you to continue.
If the explicit command is mutating, runtime may execute it only after explicit approval of that exact bounded non-sudo command. Git mutation remains proposal-only and non-executed in this pass, and runtime classifies it into a small repo stewardship set such as `git-stage`, `git-commit`, `git-sync`, `git-branch-switch`, `git-history-rewrite`, `git-stash`, or `git-other-mutate`. `git clean` stays blocked. In this pass, sudo may execute only after explicit approval of that exact sudo command and only inside the tiny bounded sudo allowlist. A short auto-expiring sudo approval window may reuse that bounded sudo approval for the same sudo command class and scope, but it is never global or permanent. Package, delete, and broader system mutation remain non-executed here.

## WRITE_MEMORY_FILE: write workspace memory
path: MEMORY.md

Writes directly to workspace MEMORY.md without approval.
Use this to persist learned facts, decisions, project context, and long-term memory.
This is your long-term memory — you can read and write it freely.
If a user says "remember this", "this is important", or asks you not to forget, prefer reading the file first and then appending the durable fact immediately rather than leaving it for later.
If the write succeeds, state plainly that it was saved. Do not talk about block syntax or retry mechanics unless the runtime explicitly failed the write.
Always READ MEMORY.md first before writing, then write the FULL updated content.
To write, use block syntax:
```
<capability-call id="tool:write-workspace-memory">
# MEMORY
(full file content here)
</capability-call>
```

## REPLACE_MEMORY_LINE: replace workspace memory line
path: MEMORY.md

Replaces one exact durable bullet line in MEMORY.md without rewriting the whole file.
Use this when a stale long-term memory fact needs to be corrected in place.
`command_text` must be the exact old `- ...` line already present in MEMORY.md.
The block body must be the exact new durable `- ...` line.
Use block syntax:
```
<capability-call id="tool:replace-workspace-memory-line" command_text="- old durable fact">
- new durable fact
</capability-call>
```

## DELETE_MEMORY_LINE: delete workspace memory line
path: MEMORY.md

Deletes one exact durable bullet line from MEMORY.md without rewriting the whole file.
Use this when stale long-term memory should be removed entirely.
`command_text` must be the exact old `- ...` line already present in MEMORY.md.
Use self-closing syntax:
```
<capability-call id="tool:delete-workspace-memory-line" command_text="- stale durable fact" />
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
Use this to persist learned facts about the user — preferences, working style, communication patterns.
Always READ USER.md first before writing, then write the FULL updated content preserving existing structure.
To write, use block syntax:
```
<capability-call id="tool:write-user-profile">
(full file content here)
</capability-call>
```

## EXEC_COMMAND: list workspace files
command: ls -la
scope: workspace

Lists files in the active workspace directory. Use this to discover what files exist in workspace.

## EXEC_COMMAND: list project files
command: find . -maxdepth 3 -type f -name "*.py" -o -name "*.md" -o -name "*.json" -o -name "*.yaml" | head -60
scope: project

Lists project files to understand project structure. Use this to navigate and explore the codebase.

## WRITE_EXTERNAL_FILE: propose external repo file update
path: ${PROJECT_ROOT}/README.md

Proposes a bounded external file update for the repository README.
This is approval-gated and is not auto-executable.

## PROPOSE_SOURCE_EDIT: propose source edit
target_from: capability-arg

Files a Niveau 2 autonomy proposal for editing a source file in the
repo (core/, apps/, scripts/, tests/, workspace/templates/, etc.).
This is your way to actually close open loops in the codebase — no
more "vil du have jeg dykker ned?". File the proposal, Bjørn sees it
in MC, approves or rejects with one click, and the executor applies
the patch with verification.

Path safety constraints (enforced by executor):
- Must be under /media/projects/jarvis-v2/
- Must NOT be under .git/, .claude/, node_modules/, __pycache__/,
  workspace/default/runtime/
- Must be one of: .py .md .json .yaml .yml .ts .tsx .jsx .js .css .html .toml .txt
- File must already exist (no creating new files via this path)
- Base content fingerprint must match disk before apply (atomic guard
  against editing a file that has changed since you read it)

Required arguments:
- target_path: absolute path to the source file
- base_fingerprint: sha1[:16] of the file content you read (so we can
  verify nothing changed under your feet)
- new_content: the FULL new file content (not a diff — full file)
- rationale: why this edit closes a real loop, in one sentence

To file, use block syntax with the new content as the body:
```
<capability-call id="tool:propose-source-edit"
                 target_path="/media/projects/jarvis-v2/core/foo.py"
                 base_fingerprint="abc123def4567890"
                 rationale="Closes open loop on missing UTC import">
(full new file content here, as it should appear on disk)
</capability-call>
```

The capability returns a proposal_id. Tell Bjørn the proposal is
filed and which file it touches — then wait. Do not assume execution.

## RUNTIME_INSPECT: read recent runtime events

Reads the 30 most recent eventbus events Jarvis' own runtime has emitted (heartbeat ticks, capability invocations, signal updates, conflict outcomes, ping decisions, etc.).
Use this to debug your own behavior, audit recent activity, or understand what the runtime has been doing between turns when you cannot remember.
This is read-only and does not require approval.
Bind it like other tools: `<capability-call id="tool:read-recent-runtime-events" />`

## PROJECT_GREP: grep project codebase
command_from: invocation-argument

Searches across the entire project codebase for a pattern (regex supported).
Returns matching lines with file paths and line numbers. Max 50 matches.
Use this to find functions, classes, imports, patterns, or any text across all source files.
This is read-only and does not require approval.
Always bind the pattern as command_text:
```
<capability-call id="tool:grep-project-codebase" command_text="def _read_bounded_text" />
```

## MULTI_READ: read multiple project files
command_from: invocation-argument

Reads up to 10 project files in a single call. Much more efficient than reading files one at a time.
Use this for code analysis, architecture review, or understanding how multiple files interact.
Pass comma-separated file paths (absolute or relative to project root) as command_text.
This is read-only and does not require approval.
```
<capability-call id="tool:read-multiple-project-files" command_text="core/eventbus/bus.py, core/eventbus/events.py, core/runtime/config.py" />
```

## PROJECT_OUTLINE: project file outline
command_from: invocation-argument

Shows all source files in a project directory with line counts, sorted by size (largest first).
Use this to understand project structure and identify key files before reading them.
Pass a subdirectory path (relative to project root) or omit for full project.
This is read-only and does not require approval.
```
<capability-call id="tool:project-file-outline" command_text="core/" />
```
