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
- `tool:write-user-profile`
- `tool:list-workspace-files`
- `tool:list-project-files`

Approval-gated now:
- `tool:propose-external-repo-file-update`
- `tool:rewrite-workspace-memory`

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
This is APPEND-ONLY: lines you add cannot be deleted or rewritten via this tool.
Use `tool:rewrite-workspace-memory` (approval-gated) if you need to clean or restructure.

ONLY write durable facts. NEVER write conversation fragments, reflections,
inner-state narration, or session-bound observations. MEMORY.md is a long-term
fact store, not a journal.

Durable facts look like:
- `- Bjørn prefers Danish responses by default`
- `- Commit fa479ad relaxed pilot from 3-AND to 1-OR`
- `- Runtime workspace lives in ~/.jarvis-v2/workspaces/default/`
- `- The chat UI Memory panel reads from private_retained_memory_record DB table`

NOT durable facts (never write these):
- "Jeg mærker en ro i systemet nu"  (inner state — belongs in INNER_VOICE / DB)
- "Vi ses om en time, kør forsigtigt"  (session-bound — belongs in chat history)
- "### 🚀 Mine optimeringsidéer"  (proposal — belongs in chat or task queue)
- "Næste skridt — jeg fortsætter selv"  (intention — belongs in initiative_queue)
- Any line that starts with an emoji header
- Any line that addresses Bjørn directly
- Any line describing what you are about to do or just did this turn

Format rules:
- Each fact is one line, starting with `- `
- Group facts under `## H2` section headers
- No `### H3` subsections, no emojis, no inline conversation
- Maximum one fact per line
- Be concise: a fact should fit on one screen line if possible

If a user says "remember this", "this is important", or asks you not to forget,
read MEMORY.md first, identify whether the new info is a durable fact or a
session note, and only write it here if it is durable.

If the write succeeds, state plainly that it was saved (one sentence). Do not
narrate block syntax, retry mechanics, or your inner experience of saving.

To write, use block syntax (the new content is appended; existing lines are
preserved automatically by the merge):
```
<capability-call id="tool:write-workspace-memory">
- New durable fact line one
- New durable fact line two
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

## REWRITE_MEMORY_FILE: rewrite workspace memory
path: MEMORY.md

REPLACES the entire content of MEMORY.md with the new content. Unlike
`tool:write-workspace-memory`, this is NOT append-only — existing lines
will be deleted if they are not present in the new content.

Use this when MEMORY.md has accumulated noise (conversation fragments,
inner-state narration, stale facts, duplicates) and needs a clean
restructure. The durable-fact filter still applies to the new content.

This is APPROVAL-GATED. Bjørn must explicitly approve each rewrite.
Always READ MEMORY.md first, draft the cleaned-up version, and present
the diff before invoking. The full new content goes in the block body.

To rewrite, use block syntax:
```
<capability-call id="tool:rewrite-workspace-memory">
# MEMORY

## Decisions (Active)
- ...

## Learned Facts
- ...
</capability-call>
```

## RUNTIME_INSPECT: read recent runtime events

Reads the 30 most recent eventbus events Jarvis' own runtime has emitted (heartbeat ticks, capability invocations, signal updates, conflict outcomes, ping decisions, etc.).
Use this to debug your own behavior, audit recent activity, or understand what the runtime has been doing between turns when you cannot remember.
This is read-only and does not require approval.
Bind it like other tools: `<capability-call id="tool:read-recent-runtime-events" />`
