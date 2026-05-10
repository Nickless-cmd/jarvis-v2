# Skill Chain Phase 1 — Day 1 baseline

**Date:** 2026-05-10
**Deployed:** 04e598c8e068d8661d7a78ca731e9142f881f81d (jarvis-runtime + jarvis-api restart)

## Initial state

- skill_chain registered in TOOL_DEFINITIONS: **True**
- Total tools registered: **320**
- skill_chain_enabled flag: **True**
- No daemon — pure synchronous tool

## Force-call results

### Happy path (chain of 2 existing skills)

```python
_exec_skill_chain({'plan': ['fact-checker', 'markdown-helper'], 'rationale': 'test'})
# status: ok, chain: ['fact-checker', 'markdown-helper']
# instructions_full_length: 8763
# First 250 chars:
#   [skill_chain — 2 steps]
#   ## Step 1 of 2: fact-checker
#   # Fact Checker
#   Verify factual claims in documents and propose corrections backed by authoritative sources.
#   ## When to use
#   ...
```

C-format builder works correctly. Step 1 header followed by verbatim
fact-checker SKILL.md content. Step 2 follows with markdown-helper.
Closing line at the end (not shown in 250-char preview).

### Rejection paths

**Unknown skill:**
```python
_exec_skill_chain({'plan': ['fact-checker', 'fake-skill-foo']})
# {'status': 'rejected', 'reason': 'unknown skills in plan',
#  'missing': ['fake-skill-foo'],
#  'available': ['deep-research', 'excel-automation', 'fact-checker',
#                'markdown-helper', 'prompt-optimizer', 'web-scraper',
#                'youtube-downloader']}
```

Atomic pre-validation works — Jarvis sees exactly what's missing AND
the full list of valid alternatives.

**Single skill:**
```python
_exec_skill_chain({'plan': ['fact-checker']})
# {'status': 'rejected', 'reason': 'plan must have at least 2 skills'}
```

### Gate chain_candidates (live test)

| Query | Top | Score | Chain candidates |
|-------|-----|-------|------------------|
| `"fact-check this article and write report"` | fact-checker | 0.336 | [] (gap too wide) |
| `"undersøg det her emne, fakta-tjek påstandene, og skriv som markdown"` | markdown-helper | 0.476 | **3** (markdown-helper, fact-checker, deep-research) |
| `"research markedet og lav en rapport"` | deep-research | 0.514 | **3** (deep-research, fact-checker, prompt-optimizer) |

Multi-intent Danish queries successfully fire chain_candidates with
3 close matches. The gate correctly identifies when a task spans
multiple skill domains.

## Plug-in site verification

- **simple_tools.py registration** — verified, 320 tools total
- **skill_chain tool** — happy + reject paths verified live
- **skill_gate chain_candidates** — verified populated for multi-intent queries
- **skill_gate chain_hint** — populated when chain_candidates non-empty

## Open observations

- First spontaneous skill_chain call (when does Jarvis use it?): **pending observation**
- Common chain plans observed: **pending observation**
- chain_hint visibility in real visible-lane runs: **pending observation**
- Pre-validation rejection-rate (typos in real Jarvis usage): **pending**
- Plan-size distribution (2 vs 3 vs 5): **pending**
