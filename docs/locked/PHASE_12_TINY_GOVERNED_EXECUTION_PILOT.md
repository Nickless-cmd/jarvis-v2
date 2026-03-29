# Phase 12: Tiny Governed Execution Pilot

## Why This Phase Exists

Jarvis v2 now has rich bounded runtime layers (Phase 11):
- autonomy_pressure_signal_tracking (anomaly-report-pressure, initiative-pressure, etc.)
- proactive_loop_lifecycle_tracking (loop-emerging → loop-carried → loop-question-worthy → loop-closure-worthy)
- proactive_question_gate_tracking (gated candidates for proactive questions)
- heartbeat with ping system (allow_ping, ping_channel, kill_switch)

The heartbeat already has:
- `allow_ping`: boolean to enable/disable outbound pings
- `ping_channel`: currently "internal-only" or "none" 
- `kill_switch`: global disable
- Records `ping_text` as bounded preview

This makes it possible to design a tiny execution pilot where Jarvis can:
- Express bounded outbound messages in small, hard-gated cases
- Use LLM as expression tool, not as full authority source
- Stay MC-visible and governed
- Start with webchat, expand later

## Jarvis-as-Runtime-Intelligence / LLM-as-Tool Framing

**Core concept:**
- Jarvis = persistent, observable runtime intelligence
- LLM = Jarvis's cognitive engine / tool for thinking and expressing
- NOT: LLM is "all of Jarvis"

**What this means:**
- Jarvis has continuity, signals, loops, regulation (runtime truth)
- Jarvis uses LLM to formulate thoughts and expressions
- LLM is the motor, Jarvis is the intelligence with boundaries
- Expression is a bounded output, not unrestricted messaging

## Conceptual Distinctions

### Autonomy Pressure
- **Definition**: Internal drive signals (anomaly, initiative, etc.)
- **Authority**: Runtime-support, non-authoritative

### Proactive Loop
- **Definition**: Self-started threads with lifecycle
- **Lifecycle**: emerging → carried → question-worthy → closure-worthy

### Question Gate
- **Definition**: Runtime signals warranting proactive UI question
- **Authority**: Runtime-support, requires gating

### Execution Candidate
- **Definition**: A bounded outbound expression ready to send
- **Authority**: Runtime-support, requires governance pathway
- **Types**: clarification question, anomaly notice, "need input" message

### Actual Outbound Expression
- **Definition**: The final sent message to a channel
- **Authority**: Governed, gated, MC-visible

### Planner Authority
- **Definition**: The actual execution decision engine
- **Authority**: Planner (separate from execution pilot)

### Canonical Intention Truth
- **Definition**: SOUL.md / IDENTITY.md
- **Authority**: Protected canonical

## What Execution Pilot Is

A tiny, hard-gated system where Jarvis can send bounded outbound messages:
- **First channel**: webchat (single session)
- **Action types**:
  - Proactive clarification question
  - Runtime anomaly notice
  - "I need input to continue" message
- **Governance**: runtime_gate → expression_candidate → execution
- **Kill switch**: Always disabled by default, requires explicit enable

## What It Is NOT

- **NOT blanket proactive messaging**: Always gated, always limited
- **NOT planner authority**: Observation → candidate → execution, not auto-execute
- **NOT hidden autonomy**: Everything visible in MC
- **NOT canonical intention truth**: Runtime expression, not identity
- **NOT emotional dependency**: Bounded signals only
- **NOT unlimited messaging**: One message per gated event, cooldown required

## Relationship to Phase 11 Layers

```
Autonomy Pressure (Phase 11a)
        ↓
Proactive Loop Lifecycle (Phase 11b)
        ↓
Proactive Question Gate (Phase 11c)
        ↓
Execution Candidate (Phase 12 - this)
        ↓
Governed Execution (with kill switch)
        ↓
Outbound Expression (webchat first)
```

## Channel Order Recommendation

1. **Webchat (first)**: Single session, one user context
2. **Later**: Discord gateway (multi-user, requires more gating)
3. **Never**: Broadcast to multiple channels

## Recommended First Execution Types

**Type 1: Clarification Question**
- Trigger: High autonomy_pressure + open_loop + meaning_significance
- Content: "I noticed X - could you clarify Y?"
- Limit: 1 per session, 4h cooldown

**Type 2: Runtime Anomaly Notice**
- Trigger: anomaly-report-pressure in autonomy_pressure
- Content: "I encountered X, here's what I'm doing..."
- Limit: 1 per hour, requires anomaly signal

**Type 3: Need Input**
- Trigger: open_loop + regulation_homeostasis = "blocked"
- Content: "I have open work on X, need input to continue"
- Limit: 1 per session, 2h cooldown

## Source-of-Truth and Authority Boundaries

```
Runtime Layers (Phase 11)
  - autonomy_pressure, proactive_loop, question_gate
  - authority: runtime-support

Execution Pilot (Phase 12)
  - expression_candidate, gating, kill_switch
  - authority: runtime-support, governed
  - NOT: planner authority

Heartbeat Ping
  - allow_ping: disabled by default
  - ping_channel: webchat only (first)
  - kill_switch: global disable
  - authority: policy-gated

Webchat Channel
  - receives bounded messages
  - authority: output-only

Planner (separate)
  - decides execution
  - authority: planner

Canonical Self
  - SOUL.md, IDENTITY.md
  - authority: protected, explicit approval
```

## Kill Switch / Disableability

- `kill_switch = "disabled"` in heartbeat policy = all execution blocked
- `allow_ping = false` = no outbound messages
- `ping_channel = "none"` = no channel configured
- Default state: all disabled, requires explicit enable
- MC-visible: always show kill switch status

## How to Keep Execution Observerable But Not Uncontrolled

1. **Always gated**: Requires autonomy_pressure + loop + meaning to pass gate
2. **Always MC-visible**: Expression candidates shown in MC before send
3. **Always limited**: 1 message per gated event, cooldown enforced
4. **Always kill-switchable**: Single config disables all
5. **Always logged**: All expressions logged to runtime
6. **Always one-channel-first**: Webchat only, expand later

## How to Avoid Hidden Planner / Autonomy Sprawl / Messaging Creep

**Hidden planner prevention:**
- Expression goes through explicit gate, not auto-send
- Planner remains separate decision authority
- Expression = bounded output, not execution command

**Autonomy sprawl prevention:**
- Hard limits: 1 message per event, cooldown required
- Kill switch always available
- Only webchat first (single context)

**Messaging creep prevention:**
- Content templates, not free-form generation
- Limited message types (clarification, anomaly, need_input)
- Cannot spam - cooldown enforcement

## Recommended Phased Implementation Order

1. **Phase 12a**: Kill switch + allow_ping policy enforcement
2. **Phase 12b**: Expression candidate generation from question_gate
3. **Phase 12c**: Webchat delivery with cooldown enforcement
4. **Phase 12d**: MC visibility for expression candidates
5. **Future**: Discord gateway (if governance approves)

## Non-Goals

- No blanket proactive messaging
- No planner authority
- No unlimited autonomy
- No canonical intention truth
- No prompt-bypass
- No multi-channel broadcast
- No emotional dependency simulation
- No hidden execution

## Acceptance Criteria

- [ ] Execution pilot is tiny, bounded, hard-gated
- [ ] Webchat is first channel only
- [ ] Kill switch always available and defaults to disabled
- [ ] All expressions visible in MC before send
- [ ] Cooldown enforcement prevents spam
- [ ] Clear separation from planner authority
- [ ] Clear separation from canonical self
- [ ] LLM used as expression tool, not authority source
- [ ] Limited message types: clarification, anomaly, need_input
- [ ] "Everything observable" principle maintained
