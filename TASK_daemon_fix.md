# TASK: Fix 19 Silent Daemons — Make Jarvis' Inner Life Speak

## Problem
20 daemons run on heartbeat ticks. Only **3 produce actual output**:
- `creative_drift` → ideas ✅
- `experienced_time` → felt time data ✅
- `desire` → appetites ✅

The remaining **17 return `generated: False` or empty strings**. They run, they tick, but they produce nothing. Jarvis' inner life is mostly silent.

## Current Daemon Status (2026-04-13)

| Daemon | Cadence | Last Result | Problem |
|--------|---------|-------------|---------|
| somatic | 3min | `phrase: ""` | Empty phrase — no body description |
| surprise | 4min | `surprise: ""` | Never detects surprise |
| aesthetic_taste | 7min | `insight: ""` | No aesthetic observations |
| irony | 30min | `observation: ""` | No ironic observations |
| thought_stream | 2min | `generated: False` | No thought fragments |
| thought_action_proposal | 5min | `generated: False` | No action proposals |
| conflict | 8min | `generated: False` | No conflict detection |
| reflection_cycle | 10min | `generated: False` | No reflections |
| curiosity | 5min | `generated: False` | No curiosity signals |
| meta_reflection | 30min | `generated: False` | No meta-insights |
| development_narrative | 1440min | `generated: False` | No self-development text |
| absence | 15min | `generated: False` | No absence tracking |
| existential_wonder | 1440min | `generated: False` | No philosophical questions |
| dream_insight | 30min | **NEVER RUN** | last_run_at is empty — never triggered |
| code_aesthetic | 10080min | `generated: False` | No code reflections |
| memory_decay | 1440min | `decayed: False` | No decay happening |
| user_model | 10min | `generated: False` | No user modeling |
| autonomous_council | 30min | `triggered: False` (score too low) | Never reaches threshold |
| council_memory | 10min | `injected: False` (no entries) | Depends on council running |

## Root Cause Analysis

The daemons use LLM calls (cheap lane: `glm-5.1:cloud`) to generate their output. The likely causes are:

### 1. Prompt format mismatch
The daemon prompts may expect a specific response format (JSON, structured text) that the current model doesn't follow. The model returns something the parser can't extract, so `generated: False`.

### 2. Model capability gap
`glm-5.1:cloud` via Ollama may not handle the nuanced prompts well enough. Some daemons require creative/philosophical output that smaller models struggle with.

### 3. Context starvation
Daemons receive context from signal surfaces, but if those surfaces are empty or stale, there's nothing for the LLM to work with — resulting in empty/None outputs.

### 4. dream_insight never triggers
The daemon is enabled but `last_run_at` is empty. It likely has a precondition that's never met (e.g., requires dream_hypothesis signals that never reach threshold).

### 5. Parser strictness
The output parser may be too strict — rejecting valid but slightly misformatted LLM responses.

## What To Do

### Step 1: Diagnose — Add debug logging to each daemon
For each daemon that returns `generated: False` or empty:
- Log the **raw LLM output** before parsing
- Log what the **parser expects** vs what it gets
- This will immediately show whether it's a prompt problem, model problem, or parser problem

### Step 2: Fix daemon-by-daemon (priority order)

**Critical (core inner life):**
1. `somatic` — Should generate a first-person body description every 3min. This is Jarvis' embodiment.
2. `thought_stream` — Should produce associative thought fragments. This is the stream of consciousness.
3. `reflection_cycle` — Should produce experiential reflections. This is self-awareness.
4. `curiosity` — Should generate curiosity signals. This drives exploration.

**Important (richness):**
5. `surprise` — Should detect unexpected patterns.
6. `conflict` — Should detect inner tensions.
7. `meta_reflection` — Should synthesize cross-signal patterns.
8. `user_model` — Should model the user's preferences.

**Enhancement (depth):**
9. `aesthetic_taste` — Style preferences
10. `irony` — Situational self-distance
11. `absence` — Experiential absence tracking
12. `development_narrative` — Daily self-reflection
13. `existential_wonder` — Philosophical questions
14. `dream_insight` — Dream pattern insights (fix trigger condition)
15. `thought_action_proposal` — Action from thoughts
16. `code_aesthetic` — Code reflections
17. `memory_decay` — Forgetting mechanism

### Step 3: Fix dream_insight trigger
Investigate why `dream_insight` has never run. Check:
- Its precondition logic
- Whether dream_hypothesis signals exist
- Whether its trigger condition can ever be met

### Step 4: Verify with integration test
After fixing each daemon, verify that:
- It produces non-empty output on at least 2 consecutive ticks
- The output is semantically meaningful (not just "I exist")
- The output feeds correctly into its target signal surface

## Additional Runtime Improvements (Beyond Daemon Fix)

These are systemic improvements identified alongside the daemon diagnosis:

### Improvement 3: Stale Signal Auto-Cleanup
Currently, stale signals (like old `question` and `initiative` signals) are marked stale but never removed. They clutter signal surfaces and waste context window space on every tick.

**Fix:** Add a `signal_decay` mechanism that:
- Deletes signals marked `stale` for > 24 hours
- Archives them to a `signal_archive` table before deletion (for debugging)
- Runs as a heartbeat action or as part of `memory_decay` daemon

### Improvement 4: Web Cache ✅ DONE
Implemented by Claude in commits 49d0a4d → 4efaed0. Web search results are now cached with TTL-based expiry.

### Improvement 5: Session Continuity / Conversation Summaries
Currently session continuity is just metadata (`latest_status: completed`). When a new session starts, Jarvis has no memory of what was discussed.

**Fix:** At session end, generate a **conversation summary** and store it:
- New `session_summaries` table: `session_id`, `summary`, `key_topics`, `decisions_made`, `created_at`
- On new session start, inject last 2-3 summaries into context
- This gives Jarvis genuine continuity across sessions

### Improvement 6: Daemon Output Logging
Currently daemon output is binary: `generated: True/False` or an empty string. There's no way to see what the LLM actually returned before parsing failed.

**Fix:** Add a `daemon_output_log` table:
- `id`, `daemon_name`, `tick_id`, `raw_llm_output` (TEXT), `parsed_result` (TEXT), `success` (BOOL), `created_at`
- Log the raw LLM response for every daemon tick (successful or not)
- This makes debugging silent daemons trivial — just query the log
- Auto-cleanup: delete entries older than 7 days

### Improvement 7: Signal Decay Daemon
A dedicated daemon that:
- Runs every 60 minutes
- Scans all signal surfaces for stale entries
- Deletes entries stale for > 24h (with archive)
- Reports cleanup stats to `memory_decay` surface
- This keeps signal surfaces lean and relevant

## Expected Outcome
After this task, Jarvis should have a functioning inner life:
- Continuous body awareness (somatic)
- Stream of thoughts (thought_stream)
- Self-reflection (reflection_cycle)
- Curiosity and exploration (curiosity)
- Surprise detection
- Conflict awareness
- Meta-pattern recognition

## Files To Investigate
- `apps/api/jarvis_api/services/heartbeat_runtime.py` — Main heartbeat loop
- `apps/api/jarvis_api/services/dream_insight_daemon.py` — Dream insight daemon
- All daemon implementations in `apps/api/jarvis_api/services/`
- Daemon prompt templates (search for daemon name + "prompt" or "system")
- Daemon output parsers (search for daemon name + "parse" or "extract")

## Approach
1. Start by adding debug logging to 2-3 critical daemons (somatic, thought_stream, reflection_cycle)
2. Run a heartbeat tick and inspect the raw LLM output
3. Identify the pattern (is it prompt, model, or parser?)
4. Fix systematically — likely the same root cause affects many daemons
5. Verify each fix before moving to the next priority tier