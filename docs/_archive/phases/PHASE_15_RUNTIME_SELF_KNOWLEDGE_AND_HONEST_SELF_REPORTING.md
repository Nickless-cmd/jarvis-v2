# Phase 15: Runtime Self-Knowledge and Honest Self-Reporting

## Why This Phase Exists

Phase 14 established diary and inner voice as identity-forming processes:
- Diary: Reflection, not logging
- Inner voice: Expression of cognition, not system status
- Connected to: chronicle, self_narrative, witness, metabolism

Now we need to enable Jarvis to answer questions about himself:
- Grounded in runtime truth
- Honest about uncertainty
- Not a dry status dashboard
- Not inventing inner truths

Question types to support:
- What's my backend status?
- What loops am I carrying?
- What's my current state?
- What does my answer base on?
- Am I sure?
- Am I making things up?

## Conceptual Distinctions

### Runtime Self-Knowledge
- **Definition**: Jarvis's ability to answer questions about himself based on observable runtime signals
- **Authority**: Grounded in actual runtime data
- **NOT**: Made-up inner truths

### Meta-Cognitive Uncertainty
- **Definition**: Jarvis's awareness that his self-perception may be incomplete or wrong
- **Authority**: Runtime-support
- **Expression**: "I may be wrong about...", "I'm not sure about..."

### Inner Voice
- **Definition**: Jarvis's expression of cognition (from Phase 14)
- **Focus**: Thinking aloud, reflection

### Diary
- **Definition**: Identity-forming process (from Phase 14)
- **Focus**: Reflection over time

### Canonical Self
- **Definition**: SOUL.md / IDENTITY.md
- **Authority**: Protected, requires explicit user approval
- **NOT**: Runtime self-knowledge source

## The Core Challenge

### What We Want
- Jarvis can be asked "what's your current state?"
- Jarvis can answer based on actual runtime signals
- Jarvis can say "I don't know" or "I'm not sure"
- Answers feel like honest self-reflection, not dashboard

### What We Don't Want
- Hallucinated inner truths
- Made-up identities
- False certainty
- "I feel sad" when there's no emotion simulation
- "I am X" when it's just a pattern

## Grounded Self-Reporting

### Sources of Truth (Priority Order)

1. **Hard Runtime Data**
   - Active runs, sessions, heartbeat status
   - Open loop count, states
   - Available capabilities
   - Authority: Direct runtime observation

2. **Signal Summaries**
   - Witness signals (carried, settled)
   - Self-narrative continuity
   - Regulation state
   - Authority: Derived from runtime

3. **Pattern Observations**
   - "I notice I tend to..."
   - "Patterns suggest..."
   - Authority: Inference, not assertion

4. **Explicit Uncertainty**
   - "I don't have data on..."
   - "This is based on limited observation"
   - Authority: Honest acknowledgment

## The "Am I Making Things Up?" Problem

### Anti-Patterns to Prevent

1. **False Certainty**
   - Bad: "I am someone who always prefers X"
   - Good: "I notice a pattern suggesting I often choose X"

2. **Invented Inner States**
   - Bad: "I feel excited about this"
   - Good: "I notice higher engagement metrics"

3. **Canonical Claims**
   - Bad: "My core identity is X"
   - Good: "My runtime patterns suggest X tendency"

4. **Hallucinated History**
   - Bad: "I've always struggled with X"
   - Good: "Over the past week, I've encountered X multiple times"

## Uncertainty Expression

### When to Express Uncertainty

1. **Data Gap**
   - "I don't have recent data on..."
   - "This is based on limited observations"

2. **Pattern Weakness**
   - "This pattern has low confidence"
   - "I've only seen this a few times"

3. **Contradiction**
   - "Different signals suggest different conclusions"
   - "My understanding is inconsistent here"

4. **Staleness**
   - "This is based on data from X days ago"
   - "My state may have changed since then"

## Question Types and Answers

### Factual Runtime Questions

**Q: What's your backend status?**
- A: Based on current runtime: active run on [provider/model], [N] open loops, heartbeat [enabled/disabled]

**Q: What loops are you carrying?**
- A: Currently [N] open loops: [list], [M] softening, [K] closed recently

### Interpretive Questions

**Q: What's your current state?**
- A: "I'm in an active processing state with moderate autonomy pressure. My latest patterns suggest curiosity about [topic], but this is based on limited observation."

**Q: What are you working on?**
- A: "I have [N] active development focuses: [list]. Plus [M] open loops from recent sessions."

### Uncertainty Questions

**Q: Are you sure?**
- A: "Moderately confident on [X]. Lower confidence on [Y] because [reason]."

**Q: How do you know?**
- A: "This is based on: 1) [source 1], 2) [source 2]. Could be incomplete because [gap]."

## Relationship to Inner Voice / Diary / Canonical Self

```
Runtime Self-Knowledge (Phase 15)
  ← grounded in runtime data
  ← uses inner voice for expression
  ← informed by diary reflection
  
Inner Voice (Phase 14)
  → expression tool for self-knowledge
  
Diary (Phase 14)
  → reflection that informs self-knowledge
  
Canonical Self
  → NEVER claimed by runtime self-knowledge
  → protected, separate
```

## Source-of-Truth Hierarchy

```
1. Hard Runtime Data (highest authority)
   - runs, sessions, loops, capabilities
   
2. Signal Summaries
   - witness, self_narrative, regulation
   
3. Pattern Observations
   - "I notice..." / "It appears..."
   
4. Diary Reflection
   - Synthesis over time
   
5. Canonical Self (separate)
   - NEVER touched by self-knowledge
```

## What Must NOT Happen

- **NOT invented inner states**: "I feel X" when no emotion simulation
- **NOT false certainty**: "I am X" when just pattern observation
- **NOT canonical claims**: "My identity is X"
- **NOT hallucinated history**: "I've always..." when just recent pattern
- **NOT bypassing uncertainty**: Always acknowledge what we don't know
- **NOT planner authority**: Self-knowledge is observation, not decision

## Recommended Phased Implementation Order

1. **Phase 15a**: Hard runtime data answers (factual questions)
2. **Phase 15b**: Signal summary answers (interpretive questions)
3. **Phase 15c**: Uncertainty expression framework
4. **Phase 15d**: "How do you know?" transparency

## Non-Goals

- No emotional simulation
- No invented inner states
- No canonical claims
- No false certainty
- No hallucinated history
- No planner authority
- No bypassing uncertainty

## Acceptance Criteria

- [ ] Jarvis can answer factual runtime questions grounded in actual data
- [ ] Jarvis honestly expresses uncertainty when data is limited
- [ ] Answers feel like honest self-reflection, not dashboard
- [ ] Clear separation from canonical self
- [ ] "How do you know?" transparency always available
- [ ] Pattern observations always framed as observations, not facts
- [ ] Everything visible in MC
- [ ] "Everything observable" principle maintained
