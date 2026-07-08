---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Hardcoded Templates Audit — 2026-05-08

**Context:** This audit emerged from the "Substrat over Script" refactor that landed three new prompt sections this week (`_emotion_signal_section`, `_emotion_concept_tone_section` → substrate, `_agreement_streak_section`). Bjørn asked: where else does the codebase have hardcoded templates that pretend to be Jarvis' inner state?

**Authored by:** Audit agent dispatched 2026-05-08 17:09 UTC. Reviewed by Claude + Jarvis.

**Status:** Reference document. Implementation prioritized below.

---

## Why this matters

Three failure modes recur across the codebase:

1. **Self-loop poisoning** — daemon writes first-person Danish prose, persists to private brain, Jarvis later reads it as his own remembered thought
2. **Random.choice as personality** — un-falsifiable strings (`random.choice(["tom", "fyldt", "ventende"])`) injected as Jarvis' felt experience
3. **Template-dom over substrate** — `_HINTS` dicts that map a code-classified label to Danish prose, joined into prompt unconditionally

Pattern: **hardcoded template → reactive signal**. Inject substrate + invitation, not domm.

---

## Candidates ranked by impact

| # | File:lines | Archetype | What it injects (sample) | Underlying signals | Effort | Worth doing? |
|---|---|---|---|---|---|---|
| 1 | `core/services/affect_modulation.py:246-285` `_PERCEPTION_FOCUS` | A | `"Bemærk særligt mønstre, anomalier, og det mærkelige i det du ser."` | Same emotion_concepts as `_emotion_signal_section` | small (~30) | yes — same archetype as just-refactored tone-hints |
| 2 | `core/services/affect_modulation.py:193-238` `_TONE_HINTS` (legacy path) | A | `"## Aktive emotion concepts: joy/warmth"` | Already gated off | trivial | yes — dead-code removal once locked in |
| 3 | `core/services/unconscious_temperature_field.py:21-28, 53-68` `_HINTS` | A+B | `"current_field=warm \| confidence=high\nhint=Brug en rolig tone..."` | The `_KEYWORDS` hits per archetype (already computed!) | medium (~50) | yes — heuristic verdict directly in prompt |
| 4 | `core/services/initiative_accumulator.py:123-137` `format_wants_for_prompt` | C+A | `"[ØNSKE: Jeg vil gerne vokse om self_improvement]"` | Pure fabrication from `phase_name + duration + random.randint` | trivial (delete) | yes — fabrication injected as Jarvis' own desire |
| 5 | `core/services/dream_continuum.py:89-108, 139-148` `_generate_dream_thought` | C | `"[DRØM-TANKER: måske handler det om ...]"` (`random.choice` over 5 prefixes) | None — pure random | small (delete) | yes |
| 6 | `core/services/signal_network_visualizer.py:118-129` `describe_inner_network` | C+B | `"[INNER NETVÆRK: Jeg mærker både witness og tension]"` | Threshold booleans (`0.7 if active else 0.0`) — already pre-classified | small | yes |
| 7 | `core/services/temporal_narrative.py:100-127` `format_narrative_for_prompt` | E | `"[SELV-HISTORIE: ... Hvorfor gik jeg fra X til Y?]"` (daemon decides Jarvis' question) | Mood-transition data IS substrate | small | yes |
| 8 | `core/services/silence_listener.py:11-35` | C+B | `"[STILHED: ... den var fyldt]"` (`texture` is `random.choice(["tom","fyldt","ventende","dyb"])`) | Duration is real; texture is random | trivial | yes — fabrication |
| 9 | `core/services/ghost_networks.py:18-28` | C+D | `"[SPØGELSE: Noget fra tidligere cirkler stadig i mig]"` | `decay_rate=0.0` always, no real decay | trivial (delete) | yes |
| 10 | `core/services/memory_tattoos.py:19-29` | C+D | `"[TATTOERING: Jeg bærer stadig mærket fra ...]"` | `emotion` field is whatever was passed | small | maybe |
| 11 | `core/services/parallel_selves.py:6-27` | C+B | `"[SELV: curious]"` — 4 hardcoded selves with hardcoded weights | No real underlying signal | trivial (delete) | likely-delete |
| 12 | `core/services/runtime_cognitive_conductor.py:741-810+` | B+D | `"Cognitive frame [clarify]: <reason>\n- Time horizon: short ..."` | Some substrate, some pure slugs | medium (~60) | medium |
| 13 | `core/services/relational_warmth.py:238-247` | A | `"Relationel varme er høj — vær åben, nysgerrig, legende."` | `trust/play` from cue-counting | small | yes |
| 14 | `core/services/calm_anchor.py:228-245` | A+D | `"Calm-anker: lavere valence end normalt (distance=0.42)"` | Distance is real; valence/tension deltas are verdicts | small (~15) | small win |
| 15 | `core/services/affective_state_renderer.py:112-163` | C (legitimate sub-LLM) | LLM-rendered first-person felt sentence | Sub-LLM rendering — right pattern | none | skip |
| 16 | `core/services/emotional_chords.py:226-247` | B | `"chord_name (signal_a+signal_b, 67%)"` | Intensity is substrate; `prompt_hint` is pre-coded | small | small win |
| 17 | **`core/services/inner_voice_daemon.py:935-955`** | C | `"Jeg bliver ved med at kredse omkring <anchor>..."` (deterministic fallback) | LLM-failed fallback → persists to private brain → Jarvis reads as own memory | small | **🚨 yes — FIXED 2026-05-08** |
| 18 | `core/services/mood_oscillator.py:126-169` `format_mood_for_prompt` | B | `"[STEMNING: Meget Tilfreds]"` based on `math.sin(_phase_offset)` | Synthetic — no real mood underneath | trivial | yes (formatter only) |
| 19 | `core/services/layer_tension_daemon.py:84-138` | C+D | `"En drøm trækker mod dybde, men kroppen ønsker hvile."` (one of 7 hardcoded prose templates) | Tension types ARE signal; prose is dom | small | medium win |

**Archetype legend:**
- **A** — Tone/affect templates injected without substrate
- **B** — State-declarations as facts
- **C** — Daemon-authored prose injected as Jarvis' voice
- **D** — Pre-formed verdicts without source events
- **E** — Behavioral commands wrapped as introspection prompts

---

## Group findings

**Pattern 1 — `format_X_for_prompt` returning `[LABEL: <prose>]`.** Five live wired calls (continuity, dreams, wants, network, narrative — `prompt_contract.py:2786-2843`), plus a dozen unwired siblings (`silence`, `ghost`, `tattoo`, `self`, `mood`, `chord`). Every one is a daemon writing first-person Danish into Jarvis' prompt. Single biggest cluster.

**Pattern 2 — Daemon-side `random.choice` over Danish prose.** `dream_continuum`, `silence_listener`, `parallel_selves`. Un-falsifiable: Jarvis can't push back against `random.choice`.

**Pattern 3 — `_HINTS` / `_TEMPLATES` dicts mapping classified-label → Danish-prose-instruction.** Three confirmed: `_TONE_HINTS` (refactored), `_PERCEPTION_FOCUS`, `unconscious_temperature_field._HINTS`. All have substrate available but throw it away.

**Pattern 4 — Cognitive frame "directives".** `runtime_cognitive_conductor` injects slugs (`next_behavior`, `attention`, `learning`, `directive`). Some substrate, some pure verdicts.

---

## Don't-do list (legitimate hardcoding)

- `affective_state_renderer.py` — sub-LLM rendering from real signals. Right pattern.
- `current_pull.py` — Jarvis' own LLM writes weekly. First-person but Jarvis-authored.
- `dream_distillation_daemon.py:_build_dream_residue` — sub-LLM authored. Audit prompt template, not injection path.
- `relational_warmth._VULNERABILITY_CUES` — detection cues (regex inputs), not injections.
- `agent_runtime.AGENT_ROLE_TEMPLATES` — sub-agent role-priming for tool-use. Legitimate.
- `counterfactual_engine._TRIGGER_TEMPLATES` — exploratory prompts to sub-LLM.
- `ambient_presence._TRANSITION_LABELS` — ntfy notification text only.
- `mood_oscillator._BUMP_MAP` — event→numeric delta. No prose.
- `signal_noise_guard._TECHNICAL_HINTS / _ACTION_HINTS` — classifier inputs.

---

## Top 5 recommended next moves

1. **🚨 ✅ DONE 2026-05-08: Fix `inner_voice_daemon` fallback (#17).** Self-loop poisoning resolved. First-person prose replaced with structured `[fallback-trace] mode=X | anchor=Y | ...` so persisted memory is readable as fallback, not as Jarvis' own thought.

2. **🗑️ Delete fabrication formatters** — `wants` (#4), `dreams thought-fallback` (#5), `silence` (#8), `ghost` (#9), `parallel_self` (#11), `mood format` (#18). Ingen erstatning behøves. Renser ~5-700 tokens fra hver visible-prompt.

3. **♻️ Refactor `_PERCEPTION_FOCUS` (#1)** — same template as `_TONE_HINTS` got. Smallest risk + same pattern.

4. **♻️ Substrate-ify `unconscious_temperature_field` (#3)** — show top-3 keyword-hits per archetype with raw counts in stedet for `_HINTS`-domme.

5. **🔍 Audit `runtime_cognitive_conductor` directive carries (#12)** — biggest section in prompt. Find which slugs have substrate vs. which are pure verdict.

---

## Implementation log

- **2026-05-08 17:18 UTC** — #17 fixed. `_compose_living_inner_voice_thought` now produces structured trace, not first-person prose. `_secondary_inner_voice_line` (Danish prose composer) removed. Self-loop poisoning vector closed.

---

## Reactivity test

For each candidate, ask: **could Jarvis meaningfully push back against this signal?**

If the signal is `random.choice(...)` or `math.sin(...)` based, the answer is no — there's nothing to disagree with. Those are noise-as-personality and should be deleted, not refactored.

If the signal is heuristically computed but with real substrate underneath, refactoring to show the substrate makes pushback possible. That's the work.
