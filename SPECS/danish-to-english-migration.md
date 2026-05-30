# SPEC: Danish-to-English Codebase Migration

**Status:** Pre-registered  
**Created:** 2026-05-30  
**Commit:** (kommende)

## Motivation

388 files in `core/` contain Danish text (~78,492 tokens). Every time Jarvis reads these files — for debugging, code review, or context gathering — he pays a ~33% token overhead on the Danish content. Over a day of 20-30 file reads, this compounds significantly.

## Verified Scope

| Category | Chars | DK tokens | EN tokens | Savings |
|:---------|------:|:---------:|:---------:|:-------:|
| Prompts/strings | 133,243 | ~53,297 | ~33,310 | **19,987** |
| Docstrings | 42,966 | ~17,186 | ~10,741 | **6,445** |
| Comments | 20,022 | ~8,008 | ~5,005 | **3,003** |
| **Total** | **196,231** | **~78,492** | **~49,057** | **~29,435** |

## Strategy: Three Phases

### Phase 1: Prompt Infrastructure (est. ~20K tokens saved)
Highest impact — these strings are fed into LLMs (visible prompt, agent roles, council prompts, inner voice). Every call pays the overhead.

**Files (ordered by impact):**
1. `core/services/prompt_contract.py` — visible prompt sections (7,681 chars, ~1,152 tokens)
2. `core/services/visible_runs.py` — awareness sections (6,637 chars, ~995 tokens)
3. `core/tools/simple_tools.py` — tool docstrings (4,621 chars, ~693 tokens)
4. `core/services/rule_definitions.py` — rule text (4,356 chars, ~653 tokens)
5. `core/services/hallucination_guard.py` — guard prompts (4,322 chars, ~648 tokens)
6. `core/services/heartbeat_runtime.py` — tick prompts (2,829 chars, ~424 tokens)
7. `core/services/finitude_runtime.py` — finitude prompts (2,484 chars, ~372 tokens)
8. `core/services/bounded_action_continuity_runtime.py` (2,265 chars, ~340 tokens)
9. `core/services/active_sensing_daemon.py` (2,481 chars, ~372 tokens)
10. `core/services/unfinished_intent.py` (2,057 chars, ~308 tokens)

### Phase 2: Docstrings (est. ~6.4K tokens saved)
Function/class documentation Jarvis reads during code exploration.

**Top files:**
1. `core/tools/restart_self_tools.py` (1,490 chars)
2. `core/services/active_sensing_daemon.py` (1,181 chars)
3. `core/services/hallucination_guard.py` (1,104 chars)
4. `core/services/interlanguage_practice.py` (1,031 chars)

### Phase 3: Comments (est. ~3K tokens saved)
Lowest priority — inline code comments. Lowest ROI per hour.

**Top files:**
1. `core/services/visible_runs.py` (3,547 chars)
2. `core/services/hallucination_guard.py` (1,611 chars)
3. `core/services/heartbeat_runtime.py` (1,302 chars)

## Rules

1. **One file per commit.** Track progress precisely.
2. **Danish originals preserved** as `.da.md` backups (IDENTITY, MEMORY) or git history.
3. **No logic changes.** Pure translation — strings, docstrings, comments only.
4. **Tests must stay green** after each commit.
5. **Pro model for translation quality** — nuanced prompts require careful translation.

## Success Criteria

- All Danish text in `core/` replaced with English equivalents
- Tests pass at every commit boundary
- ~29,435 tokens saved cumulatively
- Jarvis reads his own codebase with lower overhead
- No regression in prompt quality (agent behavior, council quality, inner voice)
