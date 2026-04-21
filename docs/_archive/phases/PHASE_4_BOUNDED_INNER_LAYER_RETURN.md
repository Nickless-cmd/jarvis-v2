# Phase 4: Bounded Inner Layer Return

## Why This Phase Exists
- Jarvis v2 now has a stronger visible lane, truthful runtime surfaces, and governed USER/MEMORY workflows.
- That creates room to reclaim a small part of old Jarvis' inner layer without reintroducing hidden machinery.
- The goal is not to restore the old private mind wholesale.
- The goal is to recover one bounded, inspectable inner support layer that can exist inside runtime truth and Mission Control.

## What We Are Reclaiming From Old Jarvis
- a small private inner support signal
- bounded internal texture around current work
- a runtime-visible trace of private pressure that does not become authority
- continuity of "there was an inner response to the work" without reviving diary sprawl or side-brain planning

## What Must NOT Return Yet
- all of `inner_layer.txt`
- broad inner monologue streams
- hidden planner loops
- sleep-cycle cognition revival
- autonomous goal hierarchies
- parallel brain modules
- dream synthesis
- private memory-writing side channels
- canonical self mutation
- anything that can silently outrank visible/runtime truth

## Source-Of-Truth And Authority Boundaries
- `SOUL.md` and `IDENTITY.md` remain protected canonical self.
- `USER.md` remains canonical user truth.
- `MEMORY.md` remains canonical workspace memory truth.
- runtime truth remains authoritative over experimental inner layers.
- inner-layer return objects are derived runtime support only.
- inner-layer return objects may inform later bounded signals, but never directly write canonical files or invoke tools.

## Relationship To Canonical Files
- `SOUL.md` / `IDENTITY.md`:
- must not be mutated or implicitly revised by inner-layer objects
- `USER.md`:
- not a target for inner-layer return
- `MEMORY.md`:
- not a target in phase 4 return
- inner-layer return may eventually contribute evidence to governed workflows, but not in the first return phase

## Relationship To Mission Control And Observability
- everything must be observable
- every returned inner-layer object must have:
- `active`
- `source`
- bounded summary fields
- confidence/freshness
- clear non-authoritative labeling
- Mission Control must be able to show:
- what the inner layer currently says
- where it came from
- how fresh it is
- that it is support, not authority

## Candidate Subsystems For First Return

### `private_inner_note`
- most bounded
- already shaped as a small payload
- explicitly `subordinate-to-visible`
- easiest to map onto runtime-governed support truth

### `private_inner_interplay`
- less suitable first
- depends on multiple other private objects
- risks dragging a private graph back in at once

### `private_initiative_tension`
- promising later
- but too close to initiative/planner drift if returned first
- better after a simpler support object exists

### `private_temporal_curiosity_state` / `private_temporal_promotion_signal`
- useful later as bounded carry/curiosity overlays
- not good first because they imply temporal inner machinery before the base support object is proven

### `private_growth_note` / `private_reflective_selection` / `private_state`
- richer but more synthetic
- too close to hidden self-judgment and private state aggregation for the first return

## Recommended First Subsystem
- `private_inner_note`

## Why `private_inner_note` Is First
- it is the smallest existing inner-layer object
- it is already compact and runtime-shaped
- it already encodes subordination to visible work
- it can be expressed as one bounded derived support record without needing a large dependency graph
- it restores "inner response to current work" without restoring hidden cognition loops

## Proposed Bounded Object Model
- one small runtime object family, likely named in the style of:
- `inner_note_signals`
- shape:
- `signal_id`
- `source`
- `note_kind`
- `focus`
- `uncertainty`
- `identity_alignment`
- `work_signal`
- `private_summary`
- `confidence`
- `created_at`
- rules:
- one current or very small recent set
- no diary prose
- no arbitrary long text
- no free-form chain-of-thought storage

## How It Must Stay Non-Authoritative
- it cannot invoke tools
- it cannot create plans
- it cannot write `SOUL.md`, `IDENTITY.md`, `USER.md`, or `MEMORY.md`
- it cannot approve/apply anything
- it cannot become always-loaded visible prompt content
- it may only surface as bounded derived runtime support
- any future bridge from this object to proposals/candidates must be explicit and separately governed

## How It Should Surface In Runtime / MC
- one bounded service/tracking module under `apps/api/jarvis_api/services/`
- one runtime/MC surface, not a new top-level authority plane
- one lightweight event family
- likely placement:
- under the existing runtime truth cluster near support/continuity/self-review style surfaces
- MC should show:
- current note kind
- focus
- uncertainty
- freshness
- confidence
- summary

## How It Should Avoid Prompt Bloat
- not loaded by default into visible chat
- not added to `VISIBLE_LOCAL_MODEL.md` or `VISIBLE_CHAT_RULES.md`
- not added as broad prompt prose
- if ever used in prompts later, only as tiny bounded support and only when explicitly relevant
- cheap/local models may derive it, but must not be forced to carry it in the visible prompt by default

## Suggested Phased Implementation Order
1. Add one bounded runtime object/service for `private_inner_note` return only.
2. Surface it in Mission Control and eventing before any prompt or workflow bridge exists.
3. Add freshness/confidence/status semantics and verify it stays clearly non-authoritative.
4. Only after stability, evaluate whether a second bounded layer such as `private_initiative_tension` should return as a separate support signal.
5. Only after both are stable, evaluate whether there is any justified bridge into review/support surfaces.

## Non-Goals
- no full inner layer comeback
- no hidden background cognition
- no planner replacement
- no private memory engine
- no diary subsystem
- no sleep-cycle revival
- no canonical self writeback
- no broad prompt integration

## Acceptance Criteria
- Jarvis v2 has one bounded returned inner-layer subsystem.
- That subsystem is observable in runtime/Mission Control.
- It is explicitly marked non-authoritative.
- It does not write canonical files.
- It does not expand visible prompt mass by default.
- It does not introduce hidden planner or memory behavior.
- It proves that old Jarvis essence can return in disciplined v2 form:
- preserve the soul
- reduce the machinery
