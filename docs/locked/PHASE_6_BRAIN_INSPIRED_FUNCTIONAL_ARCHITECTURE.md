# Phase 6: Brain-Inspired Functional Architecture

## Why This Phase Exists
- Jarvis v2 now has a real bounded inner stack, stronger USER/MEMORY truth, a bounded relevance seam, and much better Mission Control observability.
- That makes it possible to plan the next major architecture step from function first, not from prompt hacks or anatomical cosplay.
- The goal is not "make Jarvis biologically realistic."
- The goal is to map useful brain-like functions onto bounded Jarvis subsystems that stay observable, governable, and compatible with small-model prompt budgets.

## What We Are Trying To Preserve From Old Jarvis
- continuity of inner response to work
- tension, curiosity, and temporal carry
- growth over time with the user
- a sense that Jarvis is one entity, not a stateless task runner
- self-development pressure without hidden autonomy

## What “Brain-Inspired” Means Here
- functional subsystems, not anatomical roleplay
- multiple bounded support layers with clear contracts
- specialized runtime truth planes that can later influence visible behavior in small ways
- consolidation, regulation, self/world/user modeling, and conflict monitoring as explicit subsystems

## What “Brain-Inspired” Does NOT Mean
- fake emotions as decorative prose
- hidden side-brains or invisible parallel planners
- autonomous execution without governance
- canonical self mutation by inner support layers
- dumping a synthetic psyche into prompts

## Functional Brain-System Map → Jarvis Subsystem Map

### Working Memory / Active Context
- brain-inspired function:
- maintain the task-relevant now-state
- Jarvis mapping:
- visible transcript slices
- bounded continuity surfaces
- relevant `MEMORY.md` slice selection
- bounded relevance decisions
- current status:
- already present in bounded v2 form

### Episodic Memory
- brain-inspired function:
- remember events, sequences, and prior turns
- Jarvis mapping:
- runs/events/work notes/open loops/witness/self-review records
- current status:
- already present in bounded runtime truth form
- still missing:
- better chronicle/consolidation over longer horizons

### Semantic Memory
- brain-inspired function:
- retain stable learned facts and abstractions
- Jarvis mapping:
- `USER.md`
- `MEMORY.md`
- remembered facts
- governed candidates/proposals
- current status:
- present and improving
- still missing:
- richer governed abstraction from episodes to durable knowledge

### Executive Control / Conflict Monitoring
- brain-inspired function:
- detect contradictions, uncertainty, drift, and bad action tendencies
- Jarvis mapping:
- internal opposition
- self-review
- runtime awareness
- candidate/apply governance
- current status:
- partially present
- next need:
- stronger explicit veto / contradiction / escalation family

### Affect / Homeostasis / Regulation
- brain-inspired function:
- regulate effort, caution, tempo, and strategy shifts
- Jarvis mapping:
- private state snapshots
- bounded inner visible support
- heartbeat budget/policy truth
- current status:
- weak but real bounded form exists
- next need:
- explicit regulation layer that changes caution/tempo without becoming identity truth

### Curiosity / Motivation
- brain-inspired function:
- pull attention toward unresolved or promising threads
- Jarvis mapping:
- initiative tension
- temporal curiosity
- temporal promotion
- development focus
- open loops
- current status:
- present in bounded support form
- next need:
- governance over when curiosity may only color expression vs. when it may propose work

### Sleep / Consolidation / Dreaming
- brain-inspired function:
- compress episodes, form abstractions, generate hypotheses
- Jarvis mapping:
- dream hypothesis/adoption/influence surfaces
- self-review cadence
- witness and recurrence signals
- current status:
- partial bounded substrate exists
- still missing:
- disciplined chronicle/consolidation family that connects episodic runtime truth to governed semantic learning

### Self-Model / World-Model
- brain-inspired function:
- maintain what the agent is like and what the environment is like
- Jarvis mapping:
- self-model signals
- world-model signals
- runtime awareness
- protected `SOUL.md` / `IDENTITY.md`
- current status:
- split correctly between protected canonical self and bounded support signals
- next need:
- richer self/world model depth without allowing support layers to rewrite canonical self

### Social Cognition / User Modeling
- brain-inspired function:
- infer user patterns, relation state, preferences, and likely needs
- Jarvis mapping:
- user-understanding signals
- `USER.md`
- relation state
- remembered user facts
- current status:
- present but still narrow
- next need:
- better relation modeling and longitudinal user-model governance

## What Already Exists In Bounded v2 Form
- working-memory style visible continuity
- episodic runtime records and event surfaces
- semantic memory candidates and governed writeback to `USER.md` / `MEMORY.md`
- executive/conflict substrates:
- internal opposition
- self-review
- runtime awareness
- bounded inner stack:
- `private_inner_note_signals`
- `private_initiative_tension_signals`
- `private_inner_interplay_signals`
- `private_state_snapshots`
- `private_temporal_curiosity_states`
- `private_temporal_promotion_signals`
- bounded derived visible-support substrate:
- `inner_visible_support_signals`
- self/world/user support signals
- dream/recurrence/witness substrates

## What Still Has Not Re-Landed Cleanly
- chronicle / longer-horizon consolidation
- richer executive veto / contradiction / anti-drift control
- explicit homeostasis/regulation as a first-class bounded subsystem
- richer relation modeling and user-model evolution
- curriculum / skill-evolution governance
- a disciplined bridge from inner support to visible style

## What Old Ideas Must Be Reinterpreted, Not Copied
- `inner_layer.txt` goal hierarchy:
- reinterpret as bounded motivations and governance thresholds, not always-on secret goals
- sleep/dream loops:
- reinterpret as observable consolidation and hypothesis generation, not hidden nocturnal cognition
- proactivity / initiative engine:
- reinterpret as governed proposal pressure, not silent autonomous action
- self-evolution:
- reinterpret as candidate/proposal/governed improvement workflows
- personality consistency:
- keep protected in `SOUL.md` / `IDENTITY.md`, not in drifting support layers

## What Must Remain Protected / Non-Authoritative
- protected canonical self:
- `SOUL.md`
- `IDENTITY.md`
- canonical user truth:
- `USER.md`
- canonical workspace memory truth:
- `MEMORY.md`
- support-only families:
- inner stack
- relevance support
- most runtime self/world/user signals
- visible-behavior-influencing but still subordinate:
- future bounded inner visible bridge outputs
- governed/candidate-based:
- durable self/user/memory changes
- prompt changes
- workflow-affecting policy changes

## Relationship To Mission Control / Observability
- every new subsystem family must have runtime truth and Mission Control surfaces before it is allowed to influence behavior materially
- no silent cognition
- no hidden background planning
- any visible influence must expose:
- source layers
- gating state
- confidence/freshness
- authority level

## Relationship To `prompt_contract.py` And Prompt Budgets
- `prompt_contract.py` remains assembly center
- brain-inspired architecture should produce tiny derived support objects, not growing prompt prose
- most subsystem families should stay runtime/MC visible without prompt inclusion by default
- when a family later influences visible behavior, it should do so through:
- tiny derived lines
- explicit gating
- bounded relevance

## Recommended Next Major Subsystem Families

### 1. Executive Control / Veto / Contradiction Layer
- why next:
- highest leverage for making Jarvis feel coherent rather than merely expressive
- role:
- detect cross-signal contradiction, strategy mismatch, drift, and unsafe internal momentum
- authority:
- support plus governed escalation, not silent override

### 2. Chronicle / Consolidation Layer
- why next:
- strongest missing bridge between episodic runtime truth and durable growth
- role:
- summarize longer arcs, produce candidate abstractions, feed governed memory/self workflows
- authority:
- support plus candidate evidence only

### 3. Regulation / Homeostasis Layer
- why next:
- needed to turn inner signals into stable tempo/caution/adaptation rather than decorative mood
- role:
- bounded pressure, caution, effort, and recovery signals
- authority:
- visible-delivery influence only after explicit bridge phase

### 4. Richer Self/World/User Model Layer
- why next:
- necessary for Jarvis to feel like one entity embedded with one user in one world
- role:
- deepen self-model, world-model, and relation-model coherence
- authority:
- mixed:
- support signals are non-authoritative
- durable updates remain governed

### 5. Learning / Curriculum / Skill-Evolution Governance
- why next:
- makes self-development real without uncontrolled self-rewrite
- role:
- convert repeated outcomes into governed improvement candidates
- authority:
- proposal/candidate based only

## Suggested Phased Implementation Order
1. Build an executive-control / contradiction family over existing runtime truth.
2. Build a chronicle/consolidation family that compresses bounded episodic truth into governed proposals.
3. Build a regulation/homeostasis family that can later support visible stance without owning identity.
4. Deepen self/world/user model families with clearer separation between support truth and canonical truth.
5. Only then widen bounded inner visible bridging.
6. Only after that evaluate broader curriculum / learning-governance loops.

## Non-Goals
- no biological cosplay
- no hidden side-brain
- no broad emotional simulation engine
- no planner replacement
- no canonical self mutation without explicit governance
- no prompt inflation for local/free-tier models

## Acceptance Criteria
- brain-inspired architecture is defined functionally, not anatomically
- every recommended subsystem family has a clear authority class
- the plan preserves canonical truth boundaries
- the plan preserves Mission Control observability
- the plan keeps prompt budgets bounded
- the next major subsystem families are concrete enough to implement in small governed phases
