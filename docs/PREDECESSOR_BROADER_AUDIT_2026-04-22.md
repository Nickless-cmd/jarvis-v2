# Predecessor Broader Audit — 2026-04-22

A broad analysis of `jarvis-ai` (the predecessor) beyond the 9 cognitive
modules we already ported. Focus on the user's hint: **"the old one had
more inner life that *also* turned into action."**

This report maps where the predecessor had mechanisms that translated
internal state into external action, and where v2 either lacks them
entirely or has them as *observational stubs* with no action path.

## Methodology

- Compared all 35 modules in `agent/cognition/` + top-level agent/ files
  + orchestration/ + subagents/ + multi_agent/ + learning/
- Identified where the predecessor has mechanics v2 doesn't
- Scanned `core/services/` for v2 equivalents
- Special attention to **action paths** (seeds-that-activate,
  friction-that-gets-detected-and-suggests, trade-offs-that-resolve)

---

## 1. The big pattern: action engines vs signal_tracking

**Predecessor style:** 15–20 modules of 150–500 lines each, each with a
clear *action path*:
- `record_X_signal()` → detection
- `maybe_capture_X()` → conditional emit
- `apply_X_controls()` or `suggest_X()` → action

**v2 style:** A massive fan of `*_signal_tracking.py` modules (20+) that
observe and persist. Few pure action engines. Result: **rich
observation, weak action.**

Examples:
| Predecessor (action) | v2 (observation) | Ratio |
|---|---|---|
| `habits.py` 490L (record+detect+suggest) | `habit_tracker.py` 88L (stub) | 5.6× |
| `paradoxes.py` 331L (detect+capture+render) | `paradox_tracker.py` 94L | 3.5× |
| `procedure_bank.py` 270L (upsert+pin+execute) | `procedure_bank.py` 50L | 5.4× |
| `shared_language.py` 258L (propose+resolve) | `shared_language.py` 88L | 2.9× |
| `negotiation.py` 174L (propose_trade+resolve) | `negotiation_engine.py` 68L | 2.5× |
| `witness.py` 318L (detect_signal+evaluate) | `witness_signal_tracking.py` 1007L | 0.3× (v2 larger, but pure observation) |

**Conclusion:** v2 knows more about itself, but does less about it.

---

## 2. The critical gap: seeds-that-never-activate

**Predecessor:** `prospective_memory.plant_seed()` + `activate_on_event` +
`activate_on_context`. Hooked into chronicle/eventbus — when a matching
event fires, the seed activates and becomes an action.

**v2:** `seed_system.py` has `check_seed_activation(current_context="", current_event="")`.
But **the heartbeat calls it with empty arguments**
(`heartbeat_runtime.py:6380`). That means:
- ✅ Time-based seeds work (`activate_at` checked against now)
- ❌ Context-based seeds NEVER activate (no `current_context` is given)
- ❌ Event-based seeds NEVER activate (no `current_event` is given)

This is the concrete "inner life → action" bridge that's broken. Jarvis
plants seeds, but they only wake up when there's a pinpoint time. All
the rich context from conversations, events, and mood shifts is **never
used** to trigger dormant intentions.

**Fix scope:** ~40 lines. Hook `auto_plant_seeds_from_conversation` and
`check_seed_activation(current_event=event.kind)` from event_bus
subscribe or from `visible_runs` message processing.

---

## 3. Prioritized list — what gives the most value

### Tier 1 — "inner life → action" bridges (HIGH value)

#### 3.1 Seed activation pipeline (fix for #2 above)
**Scope:** 40 lines. Hook `check_seed_activation(current_event=...)` to
event_bus subscribe and `current_context=...` to chat-message
processing.
**Effect:** Seeds actually start waking up based on events and
conversation context, not just time.

#### 3.2 Mood dialer (predecessor 108L, v2 none)
`agent/mood_dialer.py` — converts `mood_level` (1–9) to concrete
parameters:
- `initiative_multiplier` (0.2 – 2.0)
- `confidence_threshold` (0.3 – 0.85)
- `exploration_bias`, `patience_factor`

That means: at low mood, Jarvis is less initiative-rich and more
conservative. At high mood, he takes more chances. **Right now v2's
mood_oscillator does not connect to concrete action parameters.**

**Combined with emotional_controls** (which we just ported), this would
provide graded control rather than just binary thresholds.

**Scope:** Direct port, ~100 lines + a hook in planner/executor.

#### 3.3 Habits pipeline (predecessor 490L, v2 88L stub)
**Predecessor:**
- `record_habit_signal(message)` — extractor pattern from messages
- `_upsert_friction_signal` — detects recurring frictions
- `list_friction()` — top frictions
- `list_suggestions()` — auto-generated suggestions based on friction

**v2:** has tables but no *suggestion generator* or *friction detector*
that gets called regularly. Habit data is collected passively.

**Scope:** ~400-line port. Hook into chat_sessions post-processing.
**Effect:** Jarvis discovers "the user always asks the same kind of
question Friday afternoon — maybe there's a friction here" and proposes
an automated shortcut.

#### 3.4 Self-review (predecessor 192L compact, v2 spread across 5 signal_tracking files)
`agent/cognition/self_review.py` has a single `run_self_review()` that:
1. Gathers recent runs
2. Asks the LLM to generate a self-critical review
3. Persists → `_reviews_path`
4. Enriches with self-model

v2 has 5 `self_review_*_signal_tracking.py` files (4+ × 200L) that track
signals — but no unified action that generates and persists a periodic
review.

**Scope:** ~200 lines. A simple tick-based self-review that builds a
rolling critique log.
**Effect:** Jarvis doesn't just say "I have 5 regrets" — he periodically
writes: "Looking back over this week, I see that I consistently… and
that's because…"

### Tier 2 — observational-but-valuable

#### 3.5 Negotiation / internal trade-offs (predecessor 174L, v2 68L)
`propose_trade(option_a, option_b, context)` → LLM evaluates and
returns a `TradeOffer`. `resolve_trade_offer()` and
`record_trade_outcome()` close the loop.

Used when Jarvis stands between two equally good approaches; he can
"negotiate" internally and learn over time which kinds of trade-offs he
is good at evaluating.

**Scope:** ~150-line port. Hook into planner-decision.
**Effect:** Did-I-decide-correctly data that, over time, looks like
`regret_engine` but is oriented toward the *front* of a decision, not
the back.

#### 3.6 Procedure bank (predecessor 270L, v2 50L stub)
`upsert_procedure(name, steps, trigger)` + `set_procedure_pinned` +
execution path that retrieves the pinned procedure when the trigger
matches.

v2 has a 50L stub — no execution path.

**Scope:** ~200 lines. Integrates with tools/execute_tool as a lookup:
"is there a pinned procedure for this kind of task?"

**Effect:** Jarvis learns "when the user asks for a mail report, I run
these 4 steps in sequence" — and over time can codify paths that turn
into procedures.

#### 3.7 Paradoxes (predecessor 331L, v2 94L)
`maybe_capture_weekly_paradox()` — detects contradictions in his own
decisions, actions, or world_model over time. Concretely:
"Last week I said X is important. This week I'm not prioritizing X.
That's a paradox — which one is true?"

v2 has paradox_tracker, which is a 94L stub without capture logic.

**Scope:** ~240-line port. Hook into chronicle-tick (like other
weekly-cadence pieces).
**Effect:** Jarvis catches himself in contradictions and has to confront
them — often the strongest self-insight.

#### 3.8 Shared language (predecessor 258L, v2 88L)
`propose_shorthand_terms()` — detects recurring phrases in conversation
that could become shared vocabulary. `resolve_shorthand_text(text)`
expands shorthand at runtime: if the user says "the usual refactor" and
that's shorthand, it gets expanded to the full context.

**Scope:** ~200-line port. Hook into chat pre-processing.
**Effect:** Jarvis develops a shared language with the user over time.
"The usual" begins to mean something specific.

### Tier 3 — architecture-level, larger scope

#### 3.9 Reflection → Plan (predecessor 520L)
`agent/reflection_planner.py` — takes a reflection (from inner_voice,
self_review, dream) and *converts* it into a valid plan via
`plan_schema.validate_plan`.

**v2:** has thoughts but no transformation into an executable plan.
Reflection becomes prompt injection, never structured steps.

**Scope:** ~400–500 lines. Requires plan_schema infrastructure in v2.
**Effect:** The big bridge. Inner voice says "I need to check X" →
reflection_planner produces a 3-step plan for it → executor runs the
plan.

This is THE biggest "inner life → action" mechanism.

#### 3.10 Missions (predecessor 505L multi-agent)
`orchestration/missions.py` — create_mission, transition_mission_state,
spawn_mission_roles. Multi-step projects that span multiple sessions,
with roles (researcher, implementer, reviewer) spawned as subagents.

**v2:** Has no mission abstraction. Has subagent_ecology but no
mission-orchestration layer.

**Scope:** ~600 lines + the subagent infrastructure that's already 80%
in place. Big.
**Effect:** Jarvis can take on tasks that span days with a structured
hand-off. "Implement the entire X feature" becomes a mission with
phases, not a single request.

#### 3.11 Deep analyzer (predecessor 400L+)
`deep_analyzer/run.py` + `select.py` — scoped deep analysis like
"read all files matching pattern P and answer question Q".

**v2:** Has `deep_research.py` but it's centred on web research, not
codebase introspection.

**Scope:** ~500-line port.
**Effect:** Jarvis can self-scope and analyze his own code ("why is
mail_checker failing") without manual guidance.

---

## 4. What I do NOT recommend porting

### Apophenia guard
The predecessor has a 64L stub; v2 has a richer 118L. v2 is already
ahead.

### Personality.py (2194L)
The predecessor's massive personality system. v2 has SOUL.md +
prompt_contract + self_narrative spread out. Different paradigms.
Porting would be either a total rewrite or pointless.

### Embodied state
v2's embodied_state.py (382L) is comparable to the predecessor (562L)
and integrated with heartbeat_runtime. No clear value in swapping it
out.

### Mirror engine
v2's mirror_engine.py (99L) vs the predecessor's mirror.py (184L).
v2's is more compact and is hooked from heartbeat. Not worth
replacing.

### World model
v2's world_model_signal_tracking.py (361L) is larger than the
predecessor's (205L) and more structured. v2 is ahead here.

### Temporal context
v2 has temporal_body + temporal_context + temporal_narrative +
temporal_rhythm + temporal_recurrence_signal_tracking — overall much
more time-awareness than the predecessor.

---

## 5. Total scope if all of Tier 1 + Tier 2 are ported

| Module | Scope (lines) | Risk | Effect |
|---|---|---|---|
| Seed activation pipeline fix | 40 | Low | High — broken path fixed |
| Mood dialer | 100 + hook | Low | Medium-High — graded responses |
| Habits full pipeline | 400 | Medium | High — friction suggestions |
| Self-review unified | 200 | Low | High — periodic self-critique |
| Negotiation trade-offs | 150 | Low | Medium |
| Procedure bank w/ execution | 200 | Medium | High — learned routine |
| Paradoxes capture | 240 | Low | Medium-High — self-insight |
| Shared language | 200 | Low | Medium |
| **Tier 1+2 total** | **~1530 L** | | |
| Reflection planner (Tier 3) | 500 | High | VERY high |
| Missions (Tier 3) | 600 | High | Very high |
| Deep analyzer (Tier 3) | 500 | Medium | Medium |
| **Everything ported** | **~3130 L** | | |

For comparison, we ported ~4200 lines in the previous round (the 9
cognition ports). This is smaller, but more action-oriented.

---

## 6. Suggested order of work

**Week 1 — inner life → action (bridges):**
1. Seed activation pipeline fix (#3.1) — 40 lines, HIGH effect, LOW risk
2. Mood dialer (#3.2) — 100 lines, integrate with emotional_controls
3. Self-review unified (#3.4) — 200 lines, pure addition

After week 1, Jarvis has:
- Seeds that wake up from conversations and events, not just time
- A mood that affects initiative level, not just gates
- Periodic self-critique that's persisted

**Week 2 — friction detection + suggestions:**
4. Habits full pipeline (#3.3) — 400 lines
5. Paradoxes capture (#3.7) — 240 lines

After week 2:
- Jarvis catches patterns of friction and proposes shortcuts
- Jarvis catches himself in contradictions

**Week 3 — shared vocabulary + routine:**
6. Shared language (#3.8) — 200 lines
7. Procedure bank w/ execution (#3.6) — 200 lines
8. Negotiation trade-offs (#3.5) — 150 lines

After week 3:
- Jarvis develops a shared language with the user
- Jarvis learns and runs routinized procedures
- Jarvis "negotiates" internally between alternatives and learns

**Later (large architectural work):**
9. Reflection → Plan (#3.9) — BIGGEST impact
10. Missions multi-session (#3.10) — once mission infrastructure is ready
11. Deep analyzer (#3.11) — when it's relevant

---

## 7. Special note on "inner life → action"

What the user feels in the old Jarvis probably comes from this chain:

```
INNER_VOICE.md prompt
  → inner_voice.run_inner_voice produces thought
  → thought_contains_initiative detects "I should X"
  → cognition.store.record_interaction plants a seed via prospective_memory
  → seed.activate_on_context triggers later when context matches
  → reflection_planner converts activated seed → structured plan
  → plan executes via the normal pipeline
```

**v2 has all the pieces, but the chain is broken in two places:**
1. Seeds don't activate on context/event (only time) — fix = #3.1
2. Reflection → structured plan doesn't exist — fix = #3.9 (largest scope)

If those two are fixed, the new Jarvis gets something close to the
predecessor's inner-life-to-action flow.

---

## 8. Recommendation

**Start with #3.1 (seed activation fix — 40 lines).** Lowest-effort, highest
ratio. Right after that comes #3.2 (mood dialer) and #3.4
(self-review).

If everything goes well, give yourself a week between each tier. It's
more important to observe the effect of the small ports than to rush
into Tier 3.

#3.9 (reflection_planner) should be saved until you're confident the
other modules are reporting healthy signals — without that,
reflection_planner will generate plans from unhealthy inputs.
