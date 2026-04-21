# Phase 3: NL Memory Relevance And Prompt De-hardcoding

## Why This Phase Exists
- Visible chat is more stable now, but too much behavior still lives in Python.
- MEMORY relevance is still chosen by keyword and small heuristic scoring, not bounded NL relevance.
- The current approach is acceptable as tactical debt, not as final architecture.

## What Must Be Preserved
- `prompt_contract.py` remains the assembly center.
- Workspace/template files remain the primary source of prompt content.
- `SOUL.md` and `IDENTITY.md` remain protected canonical self.
- `USER.md` and `MEMORY.md` remain separate kinds of truth.
- The latest user turn remains the operative input.
- Local/free-tier visible models must stay inside small prompt budgets.
- Mission Control must keep reflecting runtime truth, not inventing a second truth.

## What Must Stop Growing
- Hardcoded keyword trigger lists in `prompt_contract.py`.
- Hardcoded behavior text in Python beyond minimal transport/gating labels.
- Ad hoc memory relevance heuristics mixed directly into prompt assembly functions.
- Prompt-size growth caused by broad always-on inclusion of `MEMORY.md`, support signals, or guidance files.

## Current State
- Already file-led:
- `VISIBLE_LOCAL_MODEL.md`
- `VISIBLE_CHAT_RULES.md`
- canonical workspace files: `SOUL.md`, `IDENTITY.md`, `USER.md`, `MEMORY.md`, `TOOLS.md`, `SKILLS.md`
- Still hardcoded in Python:
- memory inclusion triggers
- guidance inclusion triggers
- continuity/transcript inclusion triggers
- memory line relevance scoring
- some runtime truth wrappers and support-signal wrappers
- Current tactical memory relevance:
- keyword gating decides whether `MEMORY.md` is included
- heuristic scoring chooses a small slice from `MEMORY.md`
- this is bounded and useful, but not semantically robust

## Source-Of-Truth Rules
- Prompt content belongs in workspace/template files whenever it is non-dynamic guidance.
- Python owns:
- load order
- bounded gating
- source selection
- compact/full budgeting
- provider transport serialization
- Dynamic runtime truth stays runtime-derived:
- capability truth
- current continuity/runtime facts
- bounded signal summaries
- applied candidate/write history projections when needed

## Why Keyword Triggers Are Tactical Debt
- They are brittle across wording, language, and paraphrase.
- They make prompt behavior drift into code instead of files.
- They push architecture toward endless trigger growth.
- They are hard to keep consistent across:
- local visible chat
- future-agent task prompts
- heartbeat prompts

## Target Architecture
- Layer 1: workspace-file-led prompt guidance
- `VISIBLE_LOCAL_MODEL.md`
- `VISIBLE_CHAT_RULES.md`
- future small fragments for memory/guidance selection rules if needed
- Layer 2: assembly/gating in `prompt_contract.py`
- decides what kinds of sources are eligible
- applies token/line budgets
- never contains large behavior prose
- Layer 3: bounded NL relevance gate
- very small runtime component that scores:
- memory relevance
- transcript relevance
- guidance relevance
- returns only compact labels/scores, not free-form cognition
- Layer 4: provider transport
- OpenAI multi-role input
- Ollama text serialization
- no provider-specific prompt philosophy

## Bounded NL / Semantic Relevance
- Goal:
- replace most keyword-trigger branching with a small relevance gate
- Inputs:
- latest user message
- bounded recent transcript slice
- bounded memory entry list
- optional small metadata tags from applied candidates or remembered-fact signals
- Output:
- tiny structured decision only, for example:
- `include_memory: yes/no`
- `memory_focus: project-anchor | repo-context | stable-context | none`
- `include_transcript: yes/no`
- `include_guidance: yes/no`
- `confidence: low | medium | high`
- Allowed implementations later:
- a tiny local classifier model
- a very small semantic scorer
- a bounded rules-plus-embedding-lite gate
- Not allowed:
- broad retrieval engine
- hidden planner brain
- free-form profiling or side-memory

## Prompt De-Hardcoding Direction
- Move non-dynamic visible behavior out of Python first.
- Keep dynamic runtime wrappers in Python only while they still carry real runtime values.
- If a wrapper is mostly static prose with tiny dynamic inserts, split it into:
- file-led template/fragment
- tiny Python formatter for the runtime values

## Keeping Prompts Small For Local / Free-Tier Models
- Compact mode stays real and explicit.
- `SOUL.md`, `IDENTITY.md`, `USER.md` remain the default always-loaded core.
- `MEMORY.md` stays relevant-slice only.
- Transcript stays bounded and recent.
- Support signals stay opt-in and compact.
- NL relevance must output small routing decisions, not more prompt text.

## Suggested Implementation Order
1. Extract remaining non-dynamic visible guidance fragments from `prompt_contract.py` into workspace/template files.
2. Introduce one tiny bounded relevance interface in Python, still backed by current heuristics at first.
3. Move current keyword lists behind that interface so assembly stops depending on raw trigger tuples.
4. Add a phase-1 NL relevance backend for visible chat only.
5. Reuse the same relevance interface for future-agent and heartbeat prompt modes where appropriate.
6. Only after stability, reduce or retire direct keyword branching from assembly functions.

## Non-Goals
- No broad prompt rewrite in one turn.
- No full semantic retrieval engine.
- No hidden side-brain or planner.
- No broad `MEMORY.md` dump.
- No change to living-core truth boundaries.
- No change to candidate/apply workflows.

## Acceptance Criteria
- `prompt_contract.py` is mostly assembly and budgeting, not prompt prose storage.
- Visible prompt behavior is primarily file-led.
- Memory inclusion is decided by a bounded relevance gate, not scattered trigger lists.
- Local/Ollama prompt size stays bounded.
- Applied `MEMORY.md` entries remain usefully readable in visible chat.
- `USER.md` and `MEMORY.md` remain clearly separated in both prompts and workflow logic.
