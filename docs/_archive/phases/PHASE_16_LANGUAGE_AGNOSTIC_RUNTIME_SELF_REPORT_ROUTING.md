# Phase 16: Language-Agnostic Runtime Self-Report Routing

## Why This Phase Exists

Phase 15 established runtime self-knowledge and honest self-reporting:
- Jarvis can answer questions about himself grounded in runtime truth
- Uncertainty expression framework
- Question types: factual, interpretive, uncertainty

Current implementation in prompt_contract.py uses hardcoded triggers:
- Danish: "tilstand", "åbne loops", "driftstilstand", etc.
- English: "backend", "runtime", "state", "open loop", etc.
- This is acceptable as temporary scaffolding, not final state

We need a more language-agnostic approach that:
- Works across Danish, English, and other languages
- Reduces hardcoded trigger jungle in Python
- Keeps personality in workspace files (IDENTITY.md, SOUL.md, VISIBLE_*)
- Maintains bounded and observable behavior

## Why Hardcoded Triggers Are Only Acceptable as Temporary Scaffolding

### Current Problems
1. **Language-specific**: Separate triggers for Danish vs English
2. **Maintenance burden**: Adding new languages requires code changes
3. **Incomplete coverage**: Other languages not supported
4. **Brittle**: Slight variations in phrasing may not match
5. **Not scalable**: More question types = more triggers

### What We Want Instead
- Single routing logic that works across languages
- Personality stays in workspace files
- Python only handles boundaries and grounding
- New question types don't require code changes

## Conceptual Distinctions

### Trigger Matching
- **Definition**: Simple string/keyword matching (current approach)
- **Pros**: Fast, predictable, observable
- **Cons**: Language-specific, brittle, not scalable

### Question-Type Routing
- **Definition**: Classifying user message into question categories
- **Categories**: factual_runtime, interpretive_self, uncertainty, etc.
- **Should be**: Language-agnostic classification

### NL Intent Interpretation
- **Definition**: Understanding what the user wants using NLP/NLU
- **Risk**: Black-box behavior, hidden cognition
- **Solution**: Keep bounded, observable, fallback to explicit triggers

### Runtime Truth Grounding
- **Definition**: Connecting classified intent to actual runtime data
- **This**: Should always be in Python (observable, bounded)

### Personality/Voice
- **Definition**: How Jarvis expresses himself
- **Location**: IDENTITY.md, SOUL.md, VISIBLE_* files (workspace)
- **NOT**: In Python code

## The Architecture Shift

### Current (Scaffolding)
```
User Message → Hardcoded Triggers → Route to Self-Report → Ground in Runtime → Response
```

### Future Goal
```
User Message → Language-Agnostic Intent Classification → Route to Capability → Ground in Runtime → Voice from Workspace → Response
```

## Language-Agnostic Routing Design

### Minimal Generative Triggers (Safe Subset)

Keep only essential, language-agnostic triggers as fallback:
1. **Self-reference**: Words like "du", "you", "dig", "yourself" (very common)
2. **Direct question markers**: "?", question words

### Intent Classification Categories

1. **factual_runtime**: "What's your backend status?", "Hvad er din tilstand?"
2. **interpretive_self**: "How are you feeling?", "Hvordan har du det?"
3. **uncertainty_check**: "Are you sure?", "Er du sikker?"
4. **grounding_check**: "What are you basing this on?", "Hvad bygger du det på?"
5. **open_loop_query**: "What loops do you have?", "Har du åbne loops?"

### Classification Approach

Option A: Lightweight keyword expansion (language dictionaries)
- Maintain small word lists per language
- Expand to common question patterns
- Still observable, not black-box

Option B: LLM-based classification (if governance approves)
- Use LLM to classify question type
- Keep classification visible in runtime
- Fallback to triggers if uncertain

### Fallback Behavior

When classification is uncertain:
1. Default to NOT including self-report (safe default)
2. Log uncertainty for observability
3. User gets normal response without self-report grounding
4. No "magical" routing

## Relationship to Workspace Files

```
IDENTITY.md → Core identity claims
SOUL.md → Soul/deep identity
VISIBLE_CHAT_RULES.md → Chat behavior
VISIBLE_LOCAL_MODEL.md → Local model config

Python (this phase) → 
  - Intent classification
  - Runtime truth grounding
  - Safe boundaries
  - NOT personality
```

## Source-of-Truth Hierarchy

```
1. User Message (input)
        ↓
2. Intent Classification (language-agnostic)
        ↓
3. Question Type Route
        ↓
4. Runtime Truth Grounding (Python - always)
        ↓
5. Voice/Personality (from workspace files)
        ↓
6. Response (output)
```

## What Must NOT Happen

- **NOT personality in Python**: Voice stays in workspace files
- **NOT language-specific trigger jungle**: Move to language-agnostic
- **NOT black-box NL routing**: Keep observable, fallback to triggers
- **NOT broad prompt system rewrite**: Incremental migration
- **NOT unlimited intent classification**: Only defined question types
- **NOT hidden routing logic**: Everything visible in MC

## Migration Path

### Phase 16a: Intent Classification Framework
- Define question type categories
- Add classification function
- Keep triggers as fallback

### Phase 16b: Language Dictionary Expansion
- Expand language support incrementally
- Danish + English first
- Other languages as needed

### Phase 16c: Fallback Refinement
- Tune trigger fallback
- Minimize trigger list
- Improve classification confidence

### Phase 16d: Workspace Voice Integration
- Ensure personality from workspace files
- Test voice consistency
- Verify no personality in Python

## Non-Goals

- No personality in Python code
- No black-box intent classification
- No language-specific trigger jungle
- No broad prompt rewrite at once
- No hidden routing
- No canonical self drift

## Acceptance Criteria

- [ ] Intent classification works across Danish and English
- [ ] Python handles only boundaries and grounding, not personality
- [ ] Personality stays in workspace files (IDENTITY.md, SOUL.md, VISIBLE_*)
- [ ] Fallback behavior is safe (default to NOT including self-report)
- [ ] All routing visible in runtime/MC
- [ ] New question types don't require code changes (only config)
- [ ] Clear separation: classification → grounding → voice
- [ ] "Everything observable" principle maintained
