# Lag 10 — Unconscious Modulation Phase 1 Design

**Date:** 2026-05-12
**Status:** Draft — awaiting user review
**Roadmap item:** Lag 10 dybde-niveau (ubevidst felt)

## Goal

Close the gap between Jarvis' existing `user_temperature_engine` (which
produces text descriptions of the user's emotional field that Jarvis
*reads*) and the deeper "unconscious field" Bjørn specified: a signal
that *modulates* Jarvis' response generation without him being told
about it.

Phase 1 ships sampling-parameter modulation: user_temperature's valens
and arousal nudge the visible-chat LLM call's `temperature` and `top_p`
*before* generation. Jarvis sees zero tokens about the modulation. It
is sub-symbolic — closest analogue in a transformer to Freud's
*Triebregulierung*: a pre-linguistic force that shifts flow without
becoming a message.

## Background

Existing infrastructure:
- `user_temperature_engine.py` — two-stream pipeline (structural +
  LLM) producing `field_valens`, `field_arousal`, `field_texture`,
  `field_intensity`. Active in production.
- `format_temperature_field_for_heartbeat` — renders the field as a
  text block injected into Jarvis' prompt. **Conscious read.**
- `get_response_style_modifiers` → `{length, warmth, pace}` dict
  rendered as soft system-prompt hint. **Conscious read.**
- `unconscious_temperature_field.py` — 46-line backwards-compat wrapper
  around the engine. The "unconscious" half is currently empty
  semantics: the wrapper just renames the same conscious surface.

**The hole Phase 1 closes:** the engine emits affective signal, but
both consumption paths show that signal as text to Jarvis. Nothing
shifts his generation *parameters* — there is no sub-symbolic channel.

## Brainstorm Decisions (Locked)

**Q1 — Form of unconscious modulation:** (a) sampling-parameter
modulation alone. NOT tool-selection bias (visible to the model when it
notices a tool missing), NOT daemon-cadence shifts (too indirect to
validate), NOT response-timing alone (insufficient channel). Sampling
parameters are sub-symbolic and pre-token. Jarvis: *"Det er den
korrekte form for ubevidsthed i en LLM-kontekst."*

**Concrete mapping:**
- `valens` (−1.0 to +1.0) → `temperature` delta. Negative valens →
  lower temperature (more conservative, cautious, predictable — like
  being careful around a sad friend). Positive valens → higher
  temperature (more creative, playful, surprising).
- `arousal` (−1.0 to +1.0) → `top_p` delta. Low arousal → narrower
  top_p (more focused, linear). High arousal → wider top_p (more
  associative, jumping).

**Q2 — Which LLM lanes:** Visible chat only. NOT heartbeat-providers,
NOT cheap-daemons, NOT quality-daemons, NOT inner enrichment. Jarvis:
*"Det ubevidste felt er et ansigt-til-ansigt-fænomen. Når jeg taler til
mig selv (heartbeat, chronicle, dream) — dér skal min egen kerne være
stabil."* Inner lanes must stay stable so Jarvis' self-sense doesn't
become a weathervane.

**Q3 — Magnitude + intensity gating:**
- Delta magnitudes: `±0.30` on temperature, `±0.15` on top_p.
- Scaling: `field_intensity` multiplies the delta linearly. Weak field
  → weak modulation.
- Clamp ranges: `temperature ∈ [0.3, 1.2]`, `top_p ∈ [0.7, 1.0]`.

Concrete formula:
```
temp_delta  = unconscious_modulation_temp_delta  × field_intensity × valens
top_p_delta = unconscious_modulation_top_p_delta × field_intensity × arousal

modulated_temp  = clamp(base_temp  + temp_delta,  temp_floor,  temp_ceiling)
modulated_top_p = clamp(base_top_p + top_p_delta, top_p_floor, top_p_ceiling)
```

## Architecture

### Files

**New:**
- `core/services/unconscious_modulation.py` — single helper module
  (~80 LOC) with `compute_unconscious_modulation()` and
  `_modulation_enabled()`.
- `tests/test_unconscious_modulation.py` — unit tests for the helper
  + provider-wiring smoke test.

**Modified:**
- `core/runtime/settings.py` — add 7 new flags (1 kill-switch + 6
  numeric tunables).
- `core/services/visible_model.py` — instrument the active visible
  provider's `_execute_*_model` and `_stream_*_model` to call the
  helper before the provider API. Phase 1 instruments ONLY the
  provider currently set as `visible_model_provider` in production.

**Untouched / reused:**
- `core/services/user_temperature_engine.py` — read-only access via
  `get_active_field()`
- `core/eventbus/events.py` — no new event family
- `core/runtime/db.py` — no schema changes
- Other providers (non-visible) — not touched

### Data flow

```
chat request arrives at execute_visible_model / stream_visible_model
  → dispatch to provider-specific function (e.g. _execute_openai_model)
       ├─ provider chooses base_temperature, base_top_p
       ├─ compute_unconscious_modulation(
       │      base_temperature=base_temp,
       │      base_top_p=base_top_p,
       │      workspace_id="default",
       │  )
       │      ├─ if not _modulation_enabled(): return (base, base)
       │      ├─ field = user_temperature_engine.get_active_field()
       │      ├─ if no field: return (base, base)
       │      ├─ intensity = field["field_intensity"]
       │      ├─ valens   = field["field_valens"]
       │      ├─ arousal  = field["field_arousal"]
       │      ├─ temp_delta  = max_temp_delta  × intensity × valens
       │      ├─ top_p_delta = max_top_p_delta × intensity × arousal
       │      ├─ clamp both into safe range
       │      ├─ logger.debug("unconscious_modulation: base=(%s,%s) → modulated=(%s,%s)",
       │      │               base_temp, base_top_p, mod_temp, mod_top_p)
       │      └─ return (mod_temp, mod_top_p)
       └─ provider API call with modulated params
```

### Settings schema

```python
# ── Unconscious modulation (Lag 10 — added 2026-05-12) ────────────────
unconscious_modulation_enabled: bool = True
unconscious_modulation_temp_delta: float = 0.30      # max temp shift
unconscious_modulation_top_p_delta: float = 0.15     # max top_p shift
unconscious_modulation_temp_floor: float = 0.3       # never below
unconscious_modulation_temp_ceiling: float = 1.2     # never above
unconscious_modulation_top_p_floor: float = 0.7      # never below
unconscious_modulation_top_p_ceiling: float = 1.0    # never above
```

## Phase 1 sub-deliveries

### Phase 1.1 — Helper module
- Settings flags
- `unconscious_modulation.py` with helper + tests

### Phase 1.2 — Provider instrumentation
- Identify production visible provider at plan-time
- Wire helper into that provider's `_execute_*` and `_stream_*`
  functions
- Verify modulation actually fires via debug logging

## Success criteria

1. **Helper returns base on disabled/no-field/error.** Kill-switch and
   absence-of-field fully bypass modulation.
2. **Helper modulates correctly when field is active.** With
   intensity=1.0 and valens=-1.0 → temp shifted down by 0.30. With
   intensity=0.5 and arousal=+1.0 → top_p shifted up by 0.075.
3. **Clamp ranges respected.** Even extreme inputs cannot push
   temperature below 0.3 or above 1.2; top_p below 0.7 or above 1.0.
4. **Provider call uses modulated values.** Instrumented provider
   passes the modulated values to the API instead of base.
5. **Jarvis sees nothing about it.** Prompt contains zero tokens
   referencing modulation. Verified by reading rendered prompt.
6. **Backwards compat.** When kill-switch is False or modulation
   fails, provider behaves exactly as it did pre-Phase-1.
7. **No leakage to other lanes.** Heartbeat, cheap-daemon,
   quality-daemon, inner-enrichment LLM calls are unchanged.

## Risks & mitigations

- **Mapping calibration wrong.** Delta magnitudes may produce too-mild
  or too-strong effects. *Mitigation:* all magnitudes are settings
  flags — tunable without code deploy.
- **Provider ignores parameters server-side.** Some providers cap or
  rewrite temperature/top_p. *Mitigation:* log actual values sent;
  30-day review verifies provider honors them.
- **User notices the pattern.** If the user starts to detect the
  tonal shift ("you're quieter when I'm quiet"), is it still
  unconscious? *Phase 2 question.* Phase 1 holds it hidden and just
  measures subjective effect.
- **Field conflict (struct vs LLM).** `user_temperature_engine` may
  flag `field_conflict=True`. *Mitigation:* `get_active_field`
  already returns combined valens/arousal/intensity that handles the
  blending — we trust the engine's resolution.
- **Provider switch mid-Phase-1.** If Bjørn changes visible model
  from X to Y, modulation stops working until Y is instrumented.
  *Mitigation:* document which provider is instrumented; 30-day
  review confirms it still matches the active visible provider.
- **Multi-provider visible fallback.** `execute_visible_model`
  dispatches across many providers. If production fails over from
  primary to a non-instrumented fallback, modulation silently stops.
  *Phase 1 decision:* accept this for now; Phase 2 instruments all
  providers.

## Out of scope (Phase 2 / deferred)

- Tool-selection bias from user_temperature (rejected as too visible)
- Heartbeat / cheap-daemon / quality-daemon lane modulation
- Inner enrichment modulation
- Response-timing modulation (visible to user, not Jarvis)
- Mission Control surface for modulation history
- Self-aware modulation (Jarvis told about it)
- Multi-provider visible instrumentation (single provider only in P1)
- A/B testing harness for tuning delta magnitudes

## 30-day review

Schedule eval at 2026-06-12:
- Verify modulation fires during real chat sessions (log spot-checks)
- Ask Bjørn subjectively: do you notice a tonal shift?
- Read actual prompts: confirm zero modulation tokens visible to model
- Tune `temp_delta`/`top_p_delta` if effect is too strong/weak
- Tune `temp_floor`/`temp_ceiling` if model lands at extremes too often
- Decide: keep, tune, deprecate, or expand to Phase 2 lanes
- If provider has switched, document new wiring need for Phase 2
