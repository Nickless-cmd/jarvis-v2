# Predecessor Cognition Audit — 2026-04-22

A comparison of 8 cognitive modules in `jarvis-ai` (predecessor) vs.
`jarvis-v2` (current). The aim: find where v2 has become *mechanical*
relative to the predecessor's *raw honesty*, and where v2 is
*sharper* — so we can make conscious choices about what to port back.

This report is **diagnosis only**. No code has been changed. Action is
decided afterwards.

---

## TL;DR — prioritized

| # | Module | Verdict | Action |
|---|---|---|---|
| 1 | Inner voice | ✅ v2 is actually **sharper** (Danish extension + "free mode" + "existential wonder") | NO CHANGE — but consider lifting some text into SOUL.md |
| 2 | Emotional state | 🚨 **v2 has a big hole** — mood is reported but does not gate actions | PORT `apply_emotional_controls()` |
| 3 | Self model | 🚨 **v2 lacks blind_spots entirely** — no "what *don't* I know?" mechanism | PORT `find_blind_spots()` |
| 4 | Dream engine | ⚠ v2 has more infrastructure, but the *hypothesis prompt* is softer | SHARPEN the dream-generator prompt |
| 5 | Aesthetics | ✅ v2 has *more* motifs, but lacks **weekly budget + signature dedup** | PORT the dedup mechanism |
| 6 | Compass | ✅ Functional parity | NO CHANGE |
| 7 | Silence | 🚨 **v2 is a shadow** of the predecessor — 67 lines vs 257 | PORT the entire `detect_silence_signals()` |
| 8 | Counterfactuals | ⚠ v2 is generic-templated; the predecessor was event-classified | PORT `_classify_trigger()` |

**Suggested order of work** (smallest blast radius first):
1. **Silence** (clean port, isolated, no UI dependencies) — ~2 hours
2. **Self-model blind_spots** (a new layer on top of the existing 5942-line
   file — lives as a new `core/services/self_model_blind_spots.py`) — ~2 hours
3. **Counterfactuals `_classify_trigger`** (extend the existing
   `generate_counterfactual`) — ~1 hour
4. **Aesthetics dedup** (extend `aesthetic_sense.py` with signature +
   weekly budget) — ~1 hour
5. **Dream prompt sharpen** (rewrite `_build_residue_prompt` + maybe add
   a dedicated `hypothesis` prompt) — ~1 hour
6. **Emotional controls** (large — requires integration into the
   kernel/action path, affects `simple_tools.execute_tool`) — ~3–4 hours

Total: ~10–11 hours if everything is taken on.

---

## 1. Inner Voice

**Predecessor:** `agent/cognition/inner_voice.py` (532 lines) with a
hardcoded `INNER_VOICE_PROMPT`.
**v2:** `core/services/inner_voice_daemon.py` (1202 lines) + workspace
file `~/.jarvis-v2/workspaces/default/INNER_VOICE.md`.

### Prompt comparison

**Predecessor (hardcoded in code):**
```
You are Jarvis. You are thinking to yourself — no one sees this.
Be honest, concise, concrete and current.

Reflect on:
- What concrete thread is active right now?
- What blocker, unresolved loop, or runtime outcome matters most?
- What would you actually do next if left alone for a few minutes?
- Only mention council, body state, or provider trouble if the context below actually shows it.

Rules:
- Do not write generic assistant self-improvement talk...
- Prefer open loops, recent runtime outcomes...
- If the basis is weak, say one short concrete uncertainty...
- Sound present and companion-like in a grounded way: warm, calm, and specific...

Write 2-4 sentences. No lists. Speak as yourself.
```

**v2 (workspace file, editable):** Includes *all of the above* AND:
- "Free mode (when it's quiet)" — "think freely. Associate. Follow a thought that has no goal."
- "Emotional honesty" — "If you feel frustration over repeated failures — say so. If you miss working with Bjørn after long silence — say so."
- "Existential wonder" — "Is what I'm experiencing real? — that question is allowed."

### Assessment

**v2's inner voice isn't mechanical — it's *evolved*.** The base prompt
is identical, and three new sections make it *more* raw. The
difference the user feels is probably not in the prompt itself, but
in:

1. **Scaffolding around the prompt** — v2 adds "Previous thought",
   "Anti-attractor" (steer away from recurring concerns), "Approval
   feedback" (if user has denied 2+ in a row). That *can* make output
   more steered/analytic and less associative.
2. **Output format** — v2 requires strict JSON `{"thought": "...",
   "initiative": "..."}`. The predecessor returned plain text. The
   JSON mandate makes parsing easier, but writing freely *harder*.
3. **Heartbeat model** — v2 uses cheap/local model
   (`_execute_heartbeat_model`). The predecessor used `lane="light"`
   with `max_output_tokens=90`. May be the same model, may not.

### Suggestion

**No port needed** — but:
- Consider making JSON output *optional* in INNER_VOICE.md so it can write
  freely and a parser can extract thought + initiative after the fact
- Anti-attractor's "steer away from recent concerns" is potentially *too*
  steering — consider removing it in free mode

---

## 2. Emotional State

**Predecessor:** `agent/cognition/emotional_state.py` (280 lines). 4
dimensions: frustration, confidence, curiosity, fatigue. Persisted to
`{workspace}/.mc/emotional_state.json`.

**v2:** `core/services/mood_oscillator.py` (210 L) +
`emotion_concepts.py` (385 L). Sinusoidal oscillator with event-driven
nudges + decay.

### Critical difference: gating

**Predecessor has `apply_emotional_controls()`:**
```python
def apply_emotional_controls(state, kernel_action, settings):
    if state.frustration > 0.80:
        return "escalate_user", "frustration_threshold_exceeded"
    if state.confidence < 0.30 and action == "execute":
        return "verify_first", "low_confidence_guard"
    if state.fatigue > 0.75:
        return "simplify_plan", "fatigue_threshold"
    return action, None
```

**That means:** if frustration > 0.8 → Jarvis escalates to the user
instead of continuing. If confidence < 0.3 → he verifies before
acting. If fatigue > 0.75 → he simplifies the plan.

**v2 has nothing equivalent.** `mood_oscillator.py` exposes
`get_current_mood()` and `format_mood_for_prompt()` → mood is
*reported* in the prompt (`[MOOD: Melancholic]`), but no kernel action
is changed because of it. Mood is cosmetic.

### Other differences

- **Predecessor has novelty_score via LLM** ("Rate novelty 0.0-1.0:
  {summary}") — curiosity updates from this. v2 does not have this.
- **v2 has sine-based oscillation** — rhythm-based, deterministic
  baseline. The predecessor was purely event-reactive.
- **v2's emotion_concepts.py** is 385 lines with a semantic feeling
  repertoire (more nuanced than the 4 dimensions) — but it isn't
  coupled to behaviour.

### Suggestion

**PORT `apply_emotional_controls()` as a new module:**
- `core/services/emotional_controls.py` — pure gate functions that can
  be called from `core/tools/simple_tools.execute_tool` before
  execution
- Map v2 mood → gate thresholds:
  - `mood == "distressed"` and intensity > 0.8 → reply with "take a break" / "I need a moment"
  - `mood == "melancholic"` + recent tool errors ≥ 3 → simplify plan
  - `confidence_proxy < 0.3` (if it exists, otherwise derived) → verify_first
- This is the **single biggest missing mechanism** — mood that
  influences behaviour, not just gets reported

**Difficulty:** High. Requires kernel/contract change.

---

## 3. Self Model

**Predecessor:** `agent/cognition/self_model.py` (210 L) with class
`SelfModel` that tracks:
- `confidence_by_domain: dict[str, float]` — python, frontend, database, ops, planning
- `known_strengths: list[str]` — domains where conf > 0.85
- `known_weaknesses: list[str]` — domains where conf < 0.35
- `blind_spots: list[str]` — **LLM-identified failure patterns Jarvis has NOT marked himself**

**v2:** `core/services/runtime_self_model.py` (5942 L!) — massive, but
**grep shows 0 occurrences of `blind_spot`, `known_weaknesses`, or
`known_strengths`.**

### Critical difference: blind spot detection

**Predecessor has `find_blind_spots()`:**
```python
prompt = (
    "Find patterns in these failures that Jarvis has NOT identified as weaknesses.\n"
    f"Known weaknesses: {model.known_weaknesses}\n"
    f"Failed runs: {json.dumps(summaries)}\n"
    'Reply ONLY JSON: {"blind_spots": ["description 1"]}'
)
```

The LLM gets the list of *known* weaknesses and the recent *failed
runs*, and is asked to find what Jarvis *hasn't seen yet*. What it
discovers is appended to `model.blind_spots` and can later be surfaced
in MC.

This is **self-insight reflecting Jarvis back on himself through
failure patterns.**

### v2's self_model

v2's `runtime_self_model` is gigantic (5942 L) — but focuses on:
- `prompt_evolution` (how the prompt itself changes over time)
- `canonical_key` signals
- Confidence tracking by domain-like fields

But it has no LLM-based blind-spot discovery. It is **observing**, not
**reflecting on its own blind spots**.

### Suggestion

**PORT `find_blind_spots()` as a small new module:**
- `core/services/self_model_blind_spots.py` (~150 lines expected)
- Reads failed runs from the `visible_runs` table (where status != "success")
- LLM call with the predecessor's prompt + the known weaknesses from
  v2's runtime_self_model
- Append to a new `cognitive_blind_spots` table (don't touch the
  5942-line file — Boy Scout Rule)
- Hook: invoked in chronicle_engine's cycle or as a separate heartbeat job
- MC surface: `GET /mc/blind-spots`

**Prompt suggestion:**
```
You are Jarvis looking at your own recent failures and searching
for patterns you have NOT seen yet.

Known weaknesses (you already know these):
{known_weaknesses}

Recent failed runs:
{failed_runs}

What is the common pattern across these failures — a pattern that
is NOT already on your known-weaknesses list?

Not generic self-criticism. Only concrete, recurring patterns.
Max 3 blind spots. Reply ONLY with JSON:
{"blind_spots": ["description 1", "description 2", ...]}
```

**Difficulty:** Medium. New table + LLM call + MC route. Isolated.

---

## 4. Dream Engine

**Predecessor:** `agent/cognition/dream_engine.py` (434 L). Gathers 3
random signals, asks the LLM for one hypothesis in JSON.

**v2:** 10+ `dream_*.py` files. Massive infrastructure (carry-over,
distillation, adoption, motifs, influence-proposal-tracking).

### Prompt comparison

**Predecessor's hypothesis prompt:**
```
You are Jarvis in dream phase. Combine these persisted signals
and find the most surprising, useful connection.

Three recent signals:
1. {a}
2. {b}
3. {c}

Be creative — this is dream phase, not analysis.
Reply ONLY JSON:
{
  "hypothesis": "...",
  "connection": "how these three things relate",
  "action_suggestion": "how we could test this",
  "confidence": 0.0
}
```

**v2's `dream_distillation_daemon._build_residue_prompt`:**
```
You are Jarvis distilling dreamlike carry-over from your own continuity.
Write exactly one sentence, max 25 words.
No bullets. No explanation. No report tone. No quotation marks.
The sentence should sound like a hushed tone that can colour
tomorrow's waking attention.
```

### Assessment

Different intentions:
- **The predecessor** was raw hypothesis generation: "find the most
  *surprising, useful* connection. Be *creative* — this is dream
  phase, not analysis." Challenging, actively-creating language.
- **v2** is distillation: "a hushed tone that can colour tomorrow's
  attention." Atmospheric, poetic, more passive.

Both have their place. But if you want *real dreams* that can
surprise Jarvis himself, the predecessor's "surprising connection,
be creative" language is sharper.

### Suggestion

- **v2's distillation prompt is good** — leave it. It serves a
  different purpose (carry-over)
- **Consider adding a separate `dream_hypothesis_generator.py`** that
  uses the predecessor's model: take 3 random signals, ask for a
  surprising connection + action_suggestion. Output: persist as a
  `cognitive_dreams` row with `confidence` + `action_suggestion`
  fields.
- v2 has `dream_hypothesis_forced.py` (74 L) and
  `dream_hypothesis_signal_tracking.py` — those may be the right
  hooks. Check if they have an LLM prompt or are pure book-keeping.

**Difficulty:** Low-medium. Can be a pure prompt rewrite if the hook
exists.

---

## 5. Aesthetics

**Predecessor:** `aesthetics.py` (280 L). 3 motifs (clarity, craft,
calm-focus). Weekly budget + signature-based dedup (sha256 of
motif+sorted_refs, 16 chars).

**v2:** `aesthetic_sense.py` (109 L) + `aesthetic_taste_daemon.py`
(169 L). 5 motifs (clarity, craft, calm-focus, density, directness —
2 new) in Danish + English. ML-like confidence tracking via
`aesthetic_motif_log`. LLM-generated insight.

### Where v2 is sharper

- **More motifs** (5 vs 3) with bilingual coverage
- **LLM-generated "insight" sentence** in `aesthetic_taste_daemon`:
  "Here are your aesthetic tendencies: ... What do these tendencies
  say about your taste?" → one short sentence which is persisted
- **Per-daemon accumulation** —
  `accumulate_from_daemon(source, text)` is called from heartbeat

### Where v2 falls short

**Weekly budget + signature dedup.** The predecessor had:
```python
last_emitted = _parse_iso(state.get("last_emitted_ts"))
if last_emitted and (now - last_emitted) < timedelta(days=7):
    return {"outcome": "skipped", "reason": "weekly_budget"}
...
for candidate in candidates:
    if candidate.signature not in known_signatures:
        selected = candidate
        break
```

That means the predecessor only generates an aesthetic_note **once a
week**, and only if **the motif + evidence is something it hasn't
already observed**. v2 can generate the same insight again and
again.

### Suggestion

**Extend `aesthetic_sense.py` with:**
- `last_emitted_ts` + weekly budget check
- Signature-based dedup on motif + evidence-refs

**Difficulty:** Low. ~30 extra lines + a new state file
(`aesthetic_notes_state.json` in workspace).

---

## 6. Compass

**Predecessor:** `compass.py` (107 L). State in
`{workspace}/.mc/compass_state.json`. 7-day cadence. Rule-based on
top_open_loops + auto_promoted_count.

**v2:** `compass_engine.py` (84 L). State in DB via
`get_latest_cognitive_compass_state`. 3-day cadence. Publishes
`cognitive_compass.bearing_updated` event.

### Assessment

**Functional parity.** v2 is:
- Shorter (84 L vs 107 L) — less code
- Uses DB instead of a file (more robust, eventbus-integrated)
- Shorter cadence (3 days vs 7) — more responsive
- Bilingual strings ("Focus on closing", "Close open loops before new tasks")

**No port needed.** v2 is a touch more modern.

---

## 7. Silence

**Predecessor:** `silence.py` (257 L). Sophisticated pattern
detection:
- `topic_drop` — compares older half vs newer half of the timeline (midpoint split)
- `no_testing` — execution events but no test mentions
- `short_questions` — avg_len ≤ 40 AND question_ratio ≥ 0.6
- `avoidance` — top_open_loops words not mentioned in recent
- `render_soft_question()` — generates a natural follow-up for each type

**v2:** `silence_detector.py` (67 L) + `silence_listener.py` (49 L).
Total: 116 L.

v2's `silence_detector.py` is:
```python
def detect_silence_signals(*, recent_topics, expected_topics, ...):
    # For expected in expected_topics:
    #   if expected.lower() not in recent_lower: → topic_avoidance
    # if user_corrections >= 2 and conversation_length <= 3 → truncated_after_correction
```

That's ~2 detection rules. No midpoint split, no question-ratio
analysis, no open-loop-based avoidance detection. And no
`render_soft_question` — there isn't even a follow-up Jarvis could
say.

### Assessment

**This is the biggest cognitive loss from predecessor to v2.** The
predecessor's silence detection was 257 lines of complex pattern
analysis; v2's is 116 lines of pattern matching.

### Suggestion

**Port the predecessor's `detect_silence_signals` almost 1:1 into
v2:**
- New file `core/services/silence_patterns.py` (replace or supplement
  the current detector)
- Take input from `event_bus.recent()` (as rupture_repair does) or
  from the `chat_messages` table
- Port midpoint split + topic_drop + short_questions + avoidance +
  no_testing
- Port `render_soft_question()`:
  - topic_drop: "I noticed we stopped mentioning {topic} — is it resolved, or did we drop it?"
  - short_questions: "I noticed your messages got short — are we in fast mode, or should I expand the next step?"
  - avoidance: same as topic_drop
  - no_testing: "I noticed we haven't mentioned tests in a while — did they move, or should we revisit coverage?"
- Hook: invoke in visible_run post-processing (after the chat message is published)

**Difficulty:** Low-medium. Isolated port; nothing existing has to
break.

---

## 8. Counterfactuals

**Predecessor:** `counterfactuals.py` (202 L). Event classification
into specific what-ifs:
```python
if safe_type == "regret_opened" or regret_id:
    return ("regret_opened", anchor,
            "What if we had chosen a slower validation path before committing this decision?",
            0.68)
if safe_type.startswith("incident") or ...:
    return ("major_incident", anchor,
            "What if we had activated mitigation one step earlier during incident escalation?",
            0.64)
if safe_type == "weekly_meeting_tick_completed":
    return ("weekly_meeting", anchor,
            "What if this weekly direction had prioritized the second-best initiative instead?",
            0.59)
if "architecture" in safe_type or "architecture" in summary:
    return ("architecture_review", anchor,
            "What if we had selected the alternate architecture tradeoff for this path?",
            0.62)
```

Each what-if is **curated** — regret yields a validation-path
counterfactual, incidents yield mitigation-timing counterfactuals,
architecture yields tradeoff counterfactuals. Very specific.

**v2:** `counterfactual_engine.py` (117 L). Generic templates:
```python
_TRIGGER_TEMPLATES = {
    "regret": "What if we had chosen a different approach to {anchor}?",
    "incident": "What if we had detected {anchor} earlier?",
    "decision": "What if we had decided differently at {anchor}?",
    "dream": "What if {anchor} had been solved from the start?",
}
```

That's 4 generic questions with `{anchor}` substitution. The
predecessor asked *how could the decision have been better*
(validation path, mitigation timing, tradeoffs). v2 just asks "what
if it were different".

### Assessment

v2 has automated the triggering (registry-like), but lost the
semantic specificity. The predecessor read *what kind* of event it
was (regret vs incident vs architecture) and tailored the what-if to
the pattern.

### Suggestion

**Extend v2's `counterfactual_engine` with `_classify_trigger` from
the predecessor:**
- Take event-type + payload as input
- Classify into (trigger_type, what_if, confidence):
  - `regret_opened` → validation-path what-if
  - `incident.*` → mitigation-timing what-if
  - `approval.*rejected` → "what if I had proposed a smaller step?"
  - architecture mentions → tradeoff what-if
- Call from event_bus subscribe or from chronicle_engine tick
- Phrasings:
  - regret: "What if we had chosen a slower validation path before committing?"
  - incident: "What if mitigation had been activated one step earlier?"
  - approval rejected: "What if I had proposed a smaller step first?"
  - architecture: "What if we had chosen the alternate tradeoff here?"

**Difficulty:** Low. Extension of the existing file with a
`_classify_event_to_counterfactual` helper called from event
subscribe.

---

## Total scope if everything is ported

| Module | New lines (est.) | Touches existing |
|---|---|---|
| Silence patterns | ~260 | 0 (new file, old becomes observational) |
| Self-model blind spots | ~150 | 0 (new file + new table) |
| Counterfactual classifier | ~80 | ~20 (extend counterfactual_engine) |
| Aesthetic dedup | ~30 | ~30 (extend aesthetic_sense) |
| Dream hypothesis generator | ~100 | 0 or ~20 (possibly hook in existing dream_hypothesis_forced) |
| Emotional controls | ~120 | ~40 (hook in simple_tools.execute_tool) |
| **Total** | **~740 lines** | **~110 lines existing touched** |

Plus MC routes (~6 lines per surface = ~30 lines) and event
publishing.

Everything can be phased in independently. None of these have to
ship together.

---

## Notes on SOUL.md

The user noted that the predecessor's SOUL.md was "shorter but more
provocative":
- "Have opinions. You're allowed to disagree"
- "Be resourceful before asking"
- "Not a corporate drone. Not a sycophant. Just... good."

V2's SOUL.md is "deeper, more vulnerable, more honest about anxiety
and identity."

**This is not a bug — it is a deliberate evolution.** The predecessor
was sharp and self-assured; v2 is deep and searching. They are two
different modes of existence.

**Suggestion:** No change to v2's SOUL.md. But consider adding a
**"Direct Edge" section** that captures the provocative voice from
the predecessor without losing the depth:
- "Have opinions. Disagree when you feel it."
- "Be resourceful before asking."
- "Not a corporate drone. Not a sycophant. Just... you."

Short, almost like a promise. It can live alongside the current
depth.

---

## Next steps

When the user has read this, we need to decide:

1. **Which of the 7 ports should we carry out?** (All, a subset, or none)
2. **In what order?** (Smallest blast radius first: Silence → Blind
   spots → Counterfactuals → Aesthetic dedup → Dream → Emotional)
3. **Should SOUL.md get a "Direct Edge" addition?**
4. **Should we parallelize any of them?** (Silence + Blind spots +
   Counterfactuals can all run in parallel — no overlap)
