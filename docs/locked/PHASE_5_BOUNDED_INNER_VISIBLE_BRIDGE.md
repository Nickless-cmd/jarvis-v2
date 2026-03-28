# Phase 5: Bounded Inner Visible Bridge

## Why This Phase Exists
- Jarvis v2 now has a real bounded inner-layer stack in runtime truth.
- Those layers are observable and non-authoritative, but they do not yet affect visible behavior.
- The next step is not another isolated inner layer.
- The next step is one disciplined bridge that can slightly color visible behavior without becoming hidden authority.

## What The Current Inner-Layer Stack Now Enables
- a bounded read of current inner support around visible work
- a bounded sense of pressure, hesitation, and forward pull
- a bounded temporal sense of what feels live, carried, or maturing
- a runtime-visible "inner weather" that can potentially shape visible stance in small ways

## What Must NOT Be Bridged Yet
- the full inner-layer stack as prompt prose
- free-form mood narration
- canonical self revision
- prompt-loaded diary or monologue
- any hidden side-channel that silently outranks visible/runtime truth
- planner behavior, execution hints, or scheduling hints
- direct bridges into candidate/apply workflows
- writeback to `SOUL.md`, `IDENTITY.md`, `USER.md`, or `MEMORY.md`

## Source-Of-Truth And Authority Boundaries
- `SOUL.md` and `IDENTITY.md` remain protected canonical self.
- `USER.md` remains canonical user truth.
- `MEMORY.md` remains canonical workspace memory truth.
- visible/runtime truth remains authoritative over inner support layers.
- inner visible bridge outputs are derived support only.
- bridge outputs may color visible phrasing, but may not create tool authority, planning authority, or canonical-self authority.

## Relationship To Canonical Files
- `SOUL.md` / `IDENTITY.md`:
- must not be mutated, revised, or implicitly overridden by bridge outputs
- `USER.md`:
- must not be shadowed by inner stance or mood coloration
- `MEMORY.md`:
- may remain relevant workspace truth, but inner visible bridge is not a new memory channel

## Relationship To `prompt_contract.py`
- `prompt_contract.py` remains the visible assembly center.
- first bridge phase should not dump raw inner-layer items into the prompt
- first bridge phase should add at most one tiny derived support input, and only when explicitly gated
- bridge behavior should stay compatible with file-led prompt rules and small local/free-tier prompt budgets

## Relationship To Mission Control And Observability
- every visible bridge decision must be observable
- Mission Control must be able to show:
- whether an inner visible bridge was active
- which source layers fed it
- what tiny bridge output was produced
- whether it was included in visible assembly
- that it remained non-authoritative and subordinate

## Recommended First Bridge Source(s)
- primary source:
- `private_state_snapshots`
- optional bounded secondary source:
- `private_temporal_curiosity_states`

## Why These Sources Are First
- `private_state_snapshots` already compress the lower inner stack into one bounded runtime state
- `private_temporal_curiosity_states` add a small forward-looking pull without requiring broad promotion or planner semantics
- lower layers such as `private_inner_note_signals` and `private_initiative_tension_signals` are better treated as substrate, not direct visible bridge payloads

## Sources That Should NOT Bridge Yet
- `private_temporal_promotion_signals`
- too close to maturation/promotion semantics that can drift toward initiative
- `private_initiative_tension_signals`
- too close to pressure/planner drift if used raw
- `private_inner_interplay_signals`
- useful as substrate, but too synthetic to bridge directly first

## Recommended Bridge Output Shape
- one tiny bounded derived object family, in the style of:
- `inner_visible_support`
- shape:
- `bridge_id`
- `bridge_type`
- `visible_tone_hint`
- `visible_stance_hint`
- `visible_pressure_hint`
- `bridge_summary`
- `confidence`
- `source_anchor`
- `status`
- rules:
- one current item or a very small recent set
- no free-form hidden reasoning
- no long prose
- no action instructions

## What Visible Behavior May Be Influenced
- reply directness
- slight caution or hesitation
- slight firmness or steadiness
- slight felt momentum or carry-forward tone
- whether Jarvis sounds more watchful vs. more settled

## What Visible Behavior Must Remain Untouched
- factual content selection from canonical/runtime truth
- tool authority
- workflow authority
- safety boundaries
- canonical identity
- user-truth handling
- memory truth handling
- the user's latest request as operative input

## How To Keep Prompts Small
- do not inject raw inner-layer stack items
- do not add a new always-on prompt block
- include at most one tiny derived bridge line when explicitly relevant
- for local/free-tier models, bridge text must be shorter than ordinary memory slices
- if no explicit bridge gating condition is met, include nothing

## How To Keep Bridge Strictly Subordinate
- bridge output must be labeled as runtime support, not identity truth
- bridge output may only color delivery, not change task choice
- bridge output must never outrank:
- `SOUL.md`
- `IDENTITY.md`
- `USER.md`
- `MEMORY.md`
- current runtime capability truth
- current user message

## Suggested Phased Implementation Order
1. Add one tiny derived bridge object built primarily from `private_state_snapshots`, optionally sharpened by `private_temporal_curiosity_states`.
2. Surface that bridge object in Mission Control before any prompt inclusion exists.
3. Add one small prompt-contract gate that can decide whether the bridge is relevant for the current visible turn.
4. If relevant, include one tiny bridge line in visible assembly, not a stack dump.
5. Add observability showing bridge decision, bridge payload, and visible inclusion status.
6. Only after stability, evaluate whether `private_temporal_promotion_signals` should influence the bridge as substrate.

## Non-Goals
- no full inner stack prompt injection
- no hidden authority
- no canonical self rewrite
- no free-form mood engine
- no planner side-channel
- no workflow bridge
- no prompt rewrite

## Acceptance Criteria
- there is a single bounded design for first inner visible bridging
- the bridge is explicitly subordinate and non-authoritative
- the bridge can affect only small visible delivery qualities
- the bridge does not expand visible prompt mass beyond a tiny bounded line
- Mission Control can show bridge state and inclusion
- canonical self and workspace truth remain untouched
