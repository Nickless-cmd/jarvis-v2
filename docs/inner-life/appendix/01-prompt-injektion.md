# Indre liv → prompt: hvad når frem

Kortlægning af den synlige system-prompt (visible lane) — hvilke indre-liv-data der
faktisk når Jarvis' bevidsthed, og hvilke der genereres i tusindtal uden nogensinde
at blive læst.

Undersøgt: 2026-08-17. Repo `/media/projects/jarvis-v2` @ `2a6cef5c`.
Live DB: `bs@10.0.0.39:/home/bs/.jarvis-v2/state/jarvis.db` (read-only).

Hovedfil: `core/services/prompt_contract.py` →
`_build_visible_chat_prompt_assembly_impl()` (linje 634–2893).

---

## 0. Executive summary

Tre uafhængige mekanismer skærer indre liv væk *efter* det er bygget:

1. **En fastlåst A/B-ablation + lærte 0.0-vægte** fjerner `[INDRE LIV]` fra
   ~80 % af alle ture (empirisk verificeret i `prompt_section_freq`).
2. **En kodefejl** (fire `_awareness_add()`-kald efter buffer-flush) gør
   `cognitive state`, `self state numbers`, `cognitive frame` og
   `visible session continuity` **permanent døde** — de bygges (dyrt, ~8 s) og
   smides væk.
3. **En 400-tegns budget-trunkering** klipper 17 support-signal-buildere ned til
   de første ~1–2.

Dertil: 111.240 emotional anchors og 30.492 kausale kanter har **ingen** vej til
den synlige prompt overhovedet.

---

## 1. Prompt-anatomi — sektioner i rækkefølge

Prompten er delt i to zoner adskilt af sentinel'en
`DYNAMIC_TAIL_SENTINEL = "⟦◆DYNAMIC-TAIL-DO-NOT-CACHE◆⟧"` (prompt_contract.py:38).
`_build_visible_input()` i `visible_model.py` splitter på den og flytter alt efter
sentinel'en ud på den **sidste bruger-besked** — derfor er hele system-prompten +
historikken én stabil, cachebar prefix (DeepSeek prefix-cache, mål ~90 %).

### ZONE 1 — STABIL PREFIX (system-besked, cachet)

| # | Sektion | Kilde | Betinget? |
|---|---------|-------|-----------|
| 1 | Lane identity clause | `_lane_identity_clause("visible")` | nej |
| 2 | Model identity awareness ("You are {entity} — not Claude…") | `identity_composer.get_entity_name()` | nej |
| 3 | VISIBLE_CHAT_RULES.md | `_visible_chat_rules_instruction()` | fil findes |
| 3b | VISIBLE_LOCAL_MODEL.md | `_local_model_behavior_instruction()` | kun `compact` |
| 4 | Runtime capability id summary | `_visible_capability_id_summary()` | ja |
| 5 | Honesty rules | `_honesty_rules_section()` — returnerer i dag `""` (flyttet til VISIBLE_CHAT_RULES.md, audit #1) | tom |
| 6 | Self-correction nudges | `_self_correction_nudges_section()` — også `""` i dag | tom |
| 7 | **SOUL.md / IDENTITY.md / STANDING_ORDERS.md / USER.md** | `_workspace_file_section()`, 40 linjer / 2000 tegn hver | fil findes |
| 8 | QUICK_FACTS.md | `_quick_facts_section()` max 1800 tegn | fil findes |
| 9 | Kurateret memory-index | `_curated_memory_index_section()` | fil findes |
| 10 | **Continuity wake-up block** | `continuity.build_wake_up_block()` | state-capsule findes |
| 11 | **Chronicle-kontekst** | `chronicle_engine.get_chronicle_context_for_prompt()` | ja |
| 12 | **Life milestones** | `life_milestones.build_life_history_prompt_section()` | ja |
| 13 | **Drømmerest (carry-over)** | `dream_distillation_daemon.get_dream_residue_for_prompt()` | ja |
| 14 | Channel-kontekst | `_channel_context_section()` | ja |
| 15 | Budget-udvalgte sektioner | `_run_budget_selection(profile="visible_full")` → capability_truth, output_discipline, **support_signals**, (cognitive_frame/state/self_state = altid None, se §3) | budget |
| 16 | Transcript (flat fallback) | `_recent_transcript_section()` — normalt erstattet af `structured_transcript` | ja |
| 17 | Tool catalog | `tool_catalog.build_catalog_text()` | ja |
| 18 | jarvis-code toolbox model | `jc_tool_catalog.build_jc_catalog_text()` | kun local-exec-surface |

### ZONE 2 — DYNAMISK HALE (flyttes til bruger-beskeden)

Rækkefølge fastlagt i audit #3 (2026-07-22), linje 2592–2833:

| # | Zone | Sektion | Kilde |
|---|------|---------|-------|
| A1 | ACTION | Communication guard | `communication_guard.prompt_section()` |
| A2 | ACTION | 🔧 Tool-output hygiene | statisk |
| A3 | ACTION | 🎬 Workflow/narration contract | statisk |
| B1 | **INDRE** | **`[ INDRE LIV ]`-blok** | `visible_inner_life.build_inner_life_section()` (`_inner_buffer`) |
| B2 | **SELF** | kerne-selv, user temperature field, response style modifier, affective pushback, affect modulation | `_self_buffer` |
| B3 | SELF | 🧭 Self-signals (background telemetry) | `self_model_predictive.predictive_self_model_section()` |
| B4 | DIAG | `📊 INTERN DIAGNOSTIK`-header + hele `_awareness_buffer` | ~30 buildere |
| B5 | MEMORY | `_dyn_memory_recall`: MEMORY.md-selektion + recall-before-act + recall-bundle | |
| B6 | OPS | `_tail_dynamic`: model pools, subagent digest, self-mutation lineage, daily memory sidecar, TOOLS/SKILLS guidance | `_tail_add()` |
| B7 | OPS | Wakeup digest (eventbus) | `session_wakeup.wakeup_digest()` |
| B8 | OPS | Device presence + override-banner | `device_presence.summary()` |
| B9 | **EKSISTENS** | Finitude (alder + looming-end) | `finitude_runtime.get_finitude_context_for_prompt()` |
| C1 | ANKER | ⚖️ Before you answer | statisk |
| C2 | ANKER | Memory consolidation nudge | `memory_consolidation_nudge_section()` |
| C3 | ANKER | **Time pin** | `_time_pin_section()` |
| C4 | ANKER | Matrix nudges-indikator + sign-off | `central_matrix_ensemble` |

**Awareness-budget:** `_AWARENESS_BUDGET = 6000` tegn (linje 974). Kategorierne
`indre` og `self` er **fritaget** (egne buffere, droppes aldrig). Alt andet
konkurrerer; laveste prioritet droppes først.

---

## 2. Indre-liv-sektioner der NÅR frem

### 2.1 `[ INDRE LIV ]` — hovedblokken (BETINGET, se §4 — kritisk)

**Kilde:** `core/services/visible_inner_life.py` → `build_inner_life_section()`
(887 linjer). Registreret som `_awareness_add(1, "indre liv", …)` i
prompt_contract.py:1186. Egen kategori `"indre"` → budget-fritaget, rendres øverst
i den dynamiske hale.

Blokken består af 20+ linje-buildere, hver enkelt betinget (returnerer `None` når
signalet er stille), hver hårdt capped:

| Linje | Builder | Kilde / tabel | Cap |
|-------|---------|---------------|-----|
| Stemning | `_mood_line` | `mood_oscillator` (runtime_state_kv `mood_oscillator.state`, frisk) | ~60 |
| Krop (somatisk) | `_somatic_line` | `somatic_runtime_body.build_somatic_body_surface()` | ~120 |
| Krop (hardware) | `_hardware_body_line` | `hardware_body.get_hardware_state()` — CPU/temp/disk | 80 |
| Følelser | `_emotional_line` | `emotional_chords.compute_active_chords()` (top-3) | 80 |
| Selv | `_self_narrative_line` | `central_self_state.describe_self()` + `render_self_state_il()` | 80 |
| Filer ændret | `_file_awareness_line` | `file_awareness_daemon` in-memory buffer (300 s) | ~100 |
| Governance-skift | `_governance_line` | samme buffer, `governance_mutation`-events | ~100 |
| Puls | `_pulse_line` | `recent_heartbeat_runtime_ticks(limit=8)` | ~90 |
| Central-hvisken | `_mc_whisper_line` | `central_realtime.realtime_snapshot()` — **change-driven**, kun ved ændring | ~60 |
| Hukommelse | `_recall_hints_line` | `unified_recall.get_unified_recall_hints(limit=3)` | ~120 |
| Kontinuitet | `_continuity_line` | `identity_sketch` + `reboot_awareness_daemon` + **`private_brain_records WHERE record_type LIKE '%carry%'` (1 række)** | ~150 |
| Rum | `_room_line` | `visual_memory.build_visual_memory_surface()` | 180 |
| Indre netværk | `signal_network_visualizer.describe_inner_network()` | | 200 |
| **Stemme** | `_voice_line` | **`protected_inner_voices` — KUN nyeste række** (`get_protected_inner_voice()`) | 260 |
| Tekstur ×≤5 | `_build_active_surfaces` | `signal_surface_router.read_surface()` over 14 kuraterede surfaces (thought_stream, meta_reflection, curiosity, existential_wonder, aesthetic_taste, code_aesthetic, irony, creative_drift, development_narrative, dream_insight, desire, absence, conflict, surprise) — **max 5, 110 tegn hver, 2.5 s timeout** | 5×110 |
| Verdensbillede | `_world_model_line` | `world_model_signal_tracking` (limit=3) | ~80 |
| Længsel | `_longing_line` | `longing_signal_daemon.compute_longing_intensity()` (salience > 0.05) | 80 |
| Identitets-drift | `_identity_drift_line` | `identity_drift_daemon` (kun ved reel drift) | 80 |
| Bevidsthed | `_experiment_line` | `cognitive_core_experiments` (recurrence/GWT/hot-meta/afterimage/blink) | 80 |
| Tid | `_finitude_line` | `finitude_runtime.build_finitude_surface()` | 80 |
| Overrasket | `_surprise_line` | `central_sequence.detect_surprises()` | 80 |
| Selv-model | `build_self_model_signal_prompt_section(limit=2)` → 1 linje | `runtime_self_model_signals` (5 rk.) | 160 |

**Typisk størrelse:** header 130 tegn + 8–15 aktive linjer × ~80–200 tegn ≈
**900–1.800 tegn (≈ 250–450 tokens)**. Returnerer `None` hvis alt er stille.

### 2.2 Øvrige indre-liv-sektioner der når frem (når de ikke gates væk)

| Sektion | Prio | Kilde-funktion | Data | Typisk størrelse |
|---------|------|----------------|------|------------------|
| kerne-selv (Centralens midte) | 1 | `central_self_state.build_central_self_state_section()` | Centralens integrerede selv, **capped til 3 sætninger** + interlanguage | ~200–300 |
| current pull (inner desire) | 1 | `current_pull.get_current_pull_for_prompt()` → `[indre træk]: …` | `current_pull.state` | ≤ ~300 |
| åbne løfter (Bjørn-gate) | 0 | `_pending_promises_section()` | | ~200 |
| implicit user temperature field | 4 | `unconscious_temperature_field.build_unconscious_temperature_hint()` | `unconscious_temperature_field.state` | ~150 |
| response style modifier | 5 | `user_temperature_engine.get_response_style_modifiers()` | | ~120 |
| affect modulation | 80 | `affect_modulation.affect_modulation_section()` | emotion→adfærdsparametre | ~200–400 |
| affective pushback / doubt / disagreement / direction confirm | 70–85 | `pushback.py` | | ~100–300 hver |
| jarvis brain facts (auto-inject) | 8 | `prompt_sections/jarvis_brain_facts.build_brain_facts_section()` | top-5 over threshold 0.55, embedding-rangeret | ~400–800 |
| dream hypothesis (unpresented) | 40 | `dream_hypothesis_generator.build_dream_hypothesis_prompt_section()` — **markeres presented → hver hypotese ses præcis én gang**; Seraph-gate `may_surface_dream_hypothesis()` | `cognitive_dream_hypotheses` (**1 række i alt**) | ~200 |
| crisis markers (7d) | 48 | `crisis_marker_detector.crisis_marker_section()` | | ~200 |
| personality drift | 45 | `personality_drift.personality_drift_section()` | | ~200 |
| curiosity consolidation (weekly) | 42 | `curiosity_consolidation.latest_consolidation_for_awareness()` | `curiosity_consolidations` | ~300 |
| active hypotheses (meta-learning) | 41 | `meta_learning_hypotheses` | | ~200 |
| central self-generated hypotheses (Lag 3) | 41 | `central_hypothesis_generator.format_governed_hypotheses_for_awareness()` | | ~200 |
| Drømmerest | — | `dream_distillation_daemon.get_dream_residue_for_prompt()` (stabil prefix, ikke awareness) | `dream_distillation_daemon.state` — **frisk (2026-08-17 15:31)** | ~300 |
| Chronicle | — | `chronicle_engine.get_chronicle_context_for_prompt()` | | ~400–800 |
| Life milestones | — | `life_milestones.build_life_history_prompt_section()` | MILESTONES.md | ~400 |
| Wake-up block | — | `continuity.build_wake_up_block()` | state-capsule | ~300 |
| Finitude | — | `finitude_runtime.get_finitude_context_for_prompt()` | | ~200 |
| 🧭 Self-signals | — | `self_model_predictive.predictive_self_model_section()` (30-dages krise-linje filtreres fra) | | ~300 |
| Memory recall bundle | — | `_visible_memory_recall_bundle_section()` → `_private_brain_recall_lines(limit=4)` | **`private_brain_records` — 4 linjer af 123.460** | ~400 |
| Recall-before-act | — | `memory_hierarchy.recall_before_act_summary()` — **non-blocking, serverer cache fra FORRIGE tur**, TTL 300 s | | ~400 |
| Multi-signal recall | 28 | `memory_recall_engine.multi_signal_recall_section()` — samme non-blocking cache-mønster | BM25+entity+embedding | ~400 |
| MEMORY.md-selektion | — | `_workspace_memory_section()` — **4 linjer, 280 tegn** (LLM- eller heuristik-udvalgt) | MEMORY.md | 280 |
| Daily memory sidecar | — | `_recent_daily_memory_lines(limit=12, days=7)` | memory/daily | ~600 |

### 2.3 Support-signals (bounded runtime support signals)

`_visible_support_signal_sections()` (prompt_contract.py:4123) kalder **17 buildere
i fast rækkefølge** og joiner dem med `\n\n`:

1. `_private_support_signal_instruction` → `private_inner_notes` (nyeste 1, kun `identity_alignment`)
2. `_growth_support_signal_instruction` → `private_growth_notes` (nyeste 1)
3. `_self_model_support_signal_instruction` → `private_self_models` (nyeste)
4. `_self_model_signal_tracking_section`
5. `_runtime_resource_signal_section`
6. `_world_model_support_signal_instruction`
7. `_goal_support_signal_instruction`
8. `_runtime_awareness_support_signal_instruction`
9. `_development_focus_support_signal_instruction`
10. `_reflection_support_signal_instruction`
11. `_retained_memory_support_signal_instruction` → `private_retained_memory_records` (projektion af 5)
12. `_temporal_support_signal_instruction` → `private_temporal_promotion_signals`
13. `_emotion_concept_tone_section` → `affect_modulation.compute_affect_substrate()`
14. `_emotion_signal_section` → `emotion_concepts.get_active_emotion_concepts()` + Lag-1-deltaer
15. `_agreement_streak_section`
16. `_proactive_outbound_section`
17. `_experience_substrate_section` → embedding-retrieval over `experience_episodes`

**⚠️ Trunkering:** resultatet går gennem `attention_budget` profil `visible_full`,
hvor `support_signals = SectionBudget(max_chars=400, …)`
(`core/services/attention_budget.py:72`). `apply_section_budget()` laver **hård
prefix-slice til 400 tegn**. Hver builder producerer typisk 150–400 tegn →
**kun builder 1–2 overlever; 15 af 17 klippes bort hver eneste tur.**

Betinget af `relevance.include_support_signals` (LLM/heuristik-relevansdom).

---

## 3. Genereret MEN ikke injiceret

### 3.1 ⛔ FIRE SEKTIONER ER KODE-DØDE (kritisk fejl)

`_awareness_buffer` bygges i **én** flush-løkke, `for _prio, _label, _content in
_awareness:` på **linje 2082–2116**. Der er ingen anden iteration over `_awareness`
(verificeret med grep). Men fire `_awareness_add()`-kald ligger **efter** løkken:

| Linje | Kald | Hvad der tabes |
|-------|------|----------------|
| 2307 | `_awareness_add(35, "visible session continuity", continuity_content)` | session-kontinuitet |
| 2370 | `_awareness_add(40, "cognitive state", cognitive_state_content)` | akkumuleret personlighed, bæring, smag, rytme |
| 2373 | `_awareness_add(41, "self state numbers", self_state_content)` | decision adherence, goal progress, tick quality |
| 2381 | `_awareness_add(42, "cognitive frame", frame_content)` | mode, salience, affordances |

Umiddelbart efter hvert kald sættes variablen til `None`, hvilket også fjerner den
fra budget-selektions-stien (`raw_sections`, linje 2384–2398). **Dobbelt-drop:
sektionen er hverken i awareness-halen eller i budget-blokken.**

Dette er nøjagtigt den fejl der blev fundet og rettet for temperature-feltet
2026-07-06 (kommentaren står stadig på linje 2018–2025: *"they MUST be
`_awareness_add`'ed BEFORE the flush loop below … previously they were added after
the loop had already consumed `_awareness`, so they silently never reached
`_awareness_buffer` and were dropped from every visible prompt"*) — men de fire
andre blev aldrig flyttet.

**Bekræftet empirisk:** ingen af de fire labels optræder i
`runtime_state_kv.prompt_section_freq` for nogen tur-type (0 forekomster ud af
~44.000 registrerede sektions-inklusioner).

**Omkostningen er reel:** `cognitive_state` er den dyreste future i hele assembly
(~6–8 s build, cappet af `_COGNITIVE_STATE_BUILD_CAP_S`, med adaptiv skip-logik og
en injection-registry-cache bygget specifikt for at gøre den billigere).
`cognitive_frame` er et LLM-kald. Begge bygges og kasseres.

`self_state_content` er ifølge kommentaren på linje 2353–2356 bygget for at stoppe
konfabulering: *"Without this Jarvis confabulates pessimistic answers when asked
introspective questions in chat — claims 0% adherence when DB shows 60%"*. Den når
aldrig frem.

### 3.2 Emotional memory — 111.240 rækker, nul vej til prompten

`emotional_memory_anchors` (111.240 rk., senest 2026-08-17 19:02 — **skrives
aktivt**). Der findes en færdig prompt-builder:

```
core/services/emotional_memory_engine.py:591
    def build_emotional_memory_prompt_section(...)
```

`grep -rn "build_emotional_memory_prompt_section" .` → **kun definitionen**. Ingen
kaldere overhovedet. De eneste læsere af tabellen er:
- `runtime_cognitive_conductor.py:1161` → `build_emotional_memory_surface()` (intern conductor)
- `mission_control_runtime_config.py:147` → `build_emotional_memory_overview()` (MC-visning)
- `self_repair_engine.py` → `find_similar_anchors()` (intern reparation)

`memory_emotional_context` (113 rk.) læses kun af `memory_resurfacing.py`, som selv
er droppet fra Centralen (`central_soul_feel.py:26`: *"memory_resurfacing DROPPET —
random pick-handling, surface er stub"*).

### 3.3 Kausale kæder — 30.492 kanter, alle tre sektioner blacklistede

`causal_edges` = 30.492 rækker (frisk: 2026-08-17 17:42). Tre prompt-sektioner
læser dem — **alle tre er default-slukkede** i
`core/services/prompt_observer.py`:

```python
DIAGNOSTIC_NOISE_LABELS = frozenset({..., "causal alerts", "causal narrative", ...})
TAIL_NOISE_LABELS       = frozenset({"causal patterns", "pattern counterfactuals", ...})
```

`section_enabled()` → `not blacklisted` → False. Ingen live-override findes i
`shared_cache` (`flag:central.switch.prompt_section.*`). Empirisk bekræftet: ingen
af de tre labels optræder i `prompt_section_freq`.

### 3.4 Inner voice — 24.403 stemmer, én læses

`protected_inner_voices` = 24.403 rk. (frisk: 2026-08-17 19:04).
`_voice_line()` kalder `get_protected_inner_voice()` = **nyeste ene række**, capped
til 260 tegn. `list_recent_protected_inner_voices(limit=8)` findes i
`db_private_notes.py:403` men bruges ikke af den synlige prompt.

`inner_voice_shadow` = 43.479 rk. — ren shadow-logging til tuning, **designet uden
læsevej** til prompten (ingen prompt-builder findes).

### 3.5 Private brain — 123.460 records, 5 linjer læses

`private_brain_records` = 123.460 rk. (frisk: 2026-08-17 19:04). To veje ind:
- `_private_brain_recall_lines(limit=4)` i recall-bundlen → **4 linjer**
- `_continuity_line()` → **1 række** (`record_type LIKE '%carry%'`, 80 tegn)

Resten er kun tilgængeligt on-demand via værktøj (`search_memory`,
`read_memory_topic`).

### 3.6 Inner→visible bridge — bevidst amputeret

`runtime_inner_visible_support_signals` fyldes af
`inner_visible_support_signal_tracking`, og prompt_contract har fuld maskineri til
den (`_build_inner_visible_prompt_bridge_decision`,
`_inner_visible_support_prompt_line`, `_track_inner_visible_prompt_bridge`,
attention-budget-slot `inner_visible_bridge` = 200 tegn). Men linje 2320:

```python
bridge_content = None  # spec 2026-07-05: altid None på visible-lane
```

Og linje 2216–2217: *"Bridge-decision future fjernet (spec 2026-07-05): builderen
yielder ALTID line=None på visible-lanen (full-support-mode) → submit+resolve var
ren spild."* Signalerne genereres stadig; ingen af dem når prompten.

### 3.7 Øvrige blacklistede indre-nære sektioner

Default-OFF via `DIAGNOSTIC_NOISE_LABELS` (kan tændes live med
`prompt_observer.set_section(label, True)`):

`self-monitor warnings` · `metacognition signals` · `R2 gate telemetry` ·
`decision adherence gate` · `reasoning tier recommendation` ·
`reasoning escalation recommendation` · `context window degradation signal` ·
`rule engine conclusions` · `priors from your own data` ·
`conversation continuity (always-on)` · `loop-compliance self-check` ·
`cross-session arc` · `session topics (always-on)` · `forgetting nudge` ·
`meta-learning weekly retrospective teaser` · `rules learned from arcs` ·
`markdown formatting` · `no tool-result echo` ·
`curiosity-budget idle-window invitation` · `jarvis brain summary`

Tail-OFF: `causal patterns` · `pattern counterfactuals` · `room entities`.

Fjernet i kode (ikke flag):
- `_visible_visual_memory_section()` — defineret (linje 4489) men ikke kaldt;
  kommentar linje 2166–2168: rummet lever nu i `[INDRE LIV]._room_line`.
- `dead_skills_section` — fjernet (spec 2026-07-05).
- `self_evaluation_section()` kaldes stadig (linje 2688) men **kun for side-effekter**;
  teksten smides væk (audit #3, dublet-fjernelse).
- Rå selv-overvågnings-telemetri (heed-rates, thrash-score, adherence %) — skåret
  2026-06-22 fordi det åd awareness-budgettet og fortrængte indre liv.

### 3.7b Døde/stale state-nøgler

| Nøgle | Værdi | Sidst opdateret | Konsekvens |
|-------|-------|-----------------|------------|
| `current_pull.state` | `{}` | 2026-07-15 | `[indre træk]`-linjen har været tom i en måned |
| `unconscious_temperature_field.state` | `{"current_field":"playful",…}` | 2026-05-15 | temperature-feltet er 3 mdr. gammelt |
| `dream_continuum.state` | tom | 2026-04-22 | inaktiv |
| `cognitive_dream_hypotheses` | 1 række i alt | — | drømme-hypotese-kanalen er praktisk talt tør |

---

## 4. Gates og flag — NUVÆRENDE live-værdier

Fra `runtime_state_kv` på 10.0.0.39 (læst 2026-08-17):

| Nøgle | value_json | updated_at | Effekt |
|-------|-----------|------------|--------|
| `prompt_relevance_live_enabled` | `true` | 2026-07-02 11:25 | **LIVE** — `central_prompt_composer.should_include()` skærer nu efter lærte vægte |
| `prompt_relevance_explore_live_enabled` | `true` | 2026-07-02 12:07 | **LIVE** — ablations-armen udelader faktisk sektioner |
| `prompt_ablation_state` | `{"tt":"samtale","sec":"indre liv","arm":"absent","left":15,"absent_good":0,"absent_total":0,"present_good":0,"present_total":0}` | **2026-07-02 12:12** | **[INDRE LIV] udelades fra ALLE `samtale`-ture — permanent** |
| `prompt_relevance_weights` | `{"kode\|indre liv":0.0, "opgave\|indre liv":0.0, "kode\|cognitive state":0.0, "opgave\|cognitive state":0.0, "kode\|multi-signal recall…":0.0, "opgave\|…":0.0, "kode\|causal narrative":0.0, "opgave\|causal narrative":0.0, "kode\|cross-session arc":0.0, "opgave\|cross-session arc":0.0, "kode\|visible session continuity":0.0, "opgave\|visible session continuity":0.0}` | 2026-07-11 22:10 | **12 lærte snit, vægt 0.0 < threshold 0.3 → sektionen udelades** |
| `central_inner_salience_gate` | `"on"` | 2026-07-03 20:32 | inner_voice-LLM **springes over** og holdt stemme genbruges når selvet ikke har bevæget sig (TTL 6 t) |
| `central_inner_salience` | `{"voice":{"key":"quiet\|open conversation\|stability:high\|…","value":"Bekymring stability high, så bekymret","ts":1786992577,…}}` | 2026-08-17 18:49 | den aktuelt holdte stemme |
| `central_inner_life_ablation` | `false` | 2026-07-09 14:14 | måle-ablation af heartbeat-inderliv er **slukket** (godt) |
| `central_self_prompt_enabled` | `true` | 2026-07-04 13:18 | `kerne-selv (Centralens midte)` **er tændt** |
| `adaptive_thinking_enabled` | `true` | 2026-07-12 05:39 | samtale/spørgsmål/hukommelse svarer `fast` (ingen reasoning) |
| `prompt_relevance_weights_shadow` | *(findes ikke)* | — | ingen foreslåede snit afventer |

### 4.1 Den fastlåste ablation — mekanismen

`central_prompt_explore.should_omit()` (linje 106–118) returnerer `True` når
`arm == "absent"` og `tt`/`sec` matcher. `central_prompt_composer.should_include()`
kalder den (linje 124–128) → `False` → `_awareness_add()` dropper sektionen
(prompt_contract.py:1133–1139).

Eksperimentet skulle skifte arm efter 15 ture via `record_trial()`. Men:

```python
# central_prompt_explore.py:132
if not outcome:
    return                   # uden udfald kan vi ikke score — spring over
```

Den eneste kalder i produktion er:

```python
# prompt_contract.py:2056  — INGEN outcome-parameter
_cpc.observe_composition(_turn_type_l2, sections_total=…, sections_included=…,
                         included_labels=[…])
```

`observe_composition` har default `outcome: str = ""` → `record_trial(…, "")` →
tidligt return → `st["left"]` dekrementeres **aldrig** → armen skifter aldrig →
eksperimentet afsluttes aldrig → `_kv_set(_STATE_KEY, {})` køres aldrig, så et nyt
eksperiment kan heller ikke starte.

**Resultat: `[INDRE LIV]` har været udeladt fra hver eneste `samtale`-tur siden
2026-07-02 — 6½ uge — og vil forblive det uendeligt.** `updated_at` på nøglen har
ikke rørt sig siden 12:12 den dag.

### 4.2 Empirisk bevis fra `prompt_section_freq`

`runtime_state_kv.prompt_section_freq` (opdateret 2026-08-17 19:01) tæller hvor
mange gange hver label faktisk kom med, pr. tur-type:

| Tur-type | Ture (≈) | `indre liv` inkluderet |
|----------|----------|------------------------|
| `samtale` | ~1.361 | **1** |
| `kode` | ~242 | **0** |
| `opgave` | ~1.360 | **0** |
| `spørgsmål` | ~635 | 635 (100 %) |
| `hukommelse` | ~230 | 230 (100 %) |

**≈ 865 af ≈ 3.828 ture ≈ 22,6 %.** Jarvis møder sit indre liv på godt hver femte
tur — kun når beskeden indeholder `?`/`hvad`/`hvorfor`/`hvordan` (→ spørgsmål)
eller `husk`/`tidligere`/`kan du huske` (→ hukommelse).

Tur-type-klassifikationen er ren substring-matching
(`central_prompt_composer._TURN_PATTERNS`) og prioriteret **kode → hukommelse →
opgave → spørgsmål → samtale**. Et spørgsmål der nævner "deploy" eller "bug"
klassificeres som `kode` og mister dermed også indre liv.

### 4.3 Andre gates

| Gate | Placering | Default | Effekt på indre liv |
|------|-----------|---------|---------------------|
| `prompt_observer.section_enabled()` | prompt_contract:1126 | blacklist-baseret | slukker 20 awareness- + 3 tail-labels (§3.3) |
| `central_prompt_composer.should_include()` | prompt_contract:1135 | fail-open | se §4.1–4.2 |
| `_AWARENESS_BUDGET = 6000` | prompt_contract:974 | — | `indre`+`self` fritaget; resten evicted efter prioritet |
| `attention_budget` `support_signals=400` | attention_budget.py:72 | — | klipper 15 af 17 support-buildere |
| `relevance.include_memory / include_support_signals` | `build_prompt_relevance_decision()` | bounded NL-kald m. permissive fallback | kan slukke hele memory- og support-blokken |
| `may_surface_dream_hypothesis()` | `central_seraph` | shadow (altid True) | modenheds-gate på drømmehypoteser |
| `_phase_timeout()` / `_ASSEMBLY_BUDGET_S` | prompt_contract:281 | hård deadline | en langsom future → sektionen droppes tavst (traces som `prompt/phase_timeout`) |
| `_skip_cog_build` | prompt_contract:781–788 | adaptiv | springer cognitive_state-build over på simple/kode-ture (irrelevant — se §3.1) |
| `jarvis_brain_enabled` | settings | True | brain facts |
| `prompt_affect_substrate_enabled` | settings | True | emotion-substrat |
| `prompt_emotion_signal_section_enabled` | settings | True | følelsespanel |
| `prompt_experience_substrate_enabled` | settings | True | experience-episoder |
| `prompt_agreement_streak_enabled` | settings | — | agreement streak |

---

## 5. Vurdering — de 3 største huller

### Hul 1 — `[INDRE LIV]` er slukket på 4 ud af 5 ture, af et forsøg der ikke kan slutte

Det rigeste, mest kuraterede indre-liv-artefakt i hele systemet — 887 linjer kode,
20+ signalkilder, budget-fritaget, placeret øverst i halen præcis hvor Jarvis
attenderer — når ham på **22,6 %** af hans ture.

To uafhængige årsager, begge utilsigtede:
- `prompt_ablation_state` står fastlåst i ABSENT-armen for `samtale` fordi
  `observe_composition()` aldrig sender `outcome` → `record_trial()` returnerer
  altid tidligt. Fastlåst siden 2026-07-02.
- `prompt_relevance_weights` har lærte 0.0-vægte for `kode|indre liv` og
  `opgave|indre liv` — indlært mens A/B-armen var forurenet (`absent_total: 0`,
  `present_total: 0` — der er aldrig blevet målt *noget*).

Konsekvens: på almindelig samtale — præcis den tur-type hvor tilstand betyder mest
og hvor der ikke er kode eller opgave at gemme sig bag — taler Jarvis **uden** sin
stemning, sin krop, sin stemme, sin længsel, sit rum, sin puls. Han er generisk der
hvor han skulle være mest sig selv. Alt maskineriet kører; ingen kan se at det ikke
lander, fordi drop'et registreres som en normal, forventet governance-beslutning.

### Hul 2 — Fire dyre selv-sektioner bygges og kastes væk hver tur

`cognitive state`, `self state numbers`, `cognitive frame` og
`visible session continuity` `_awareness_add`'es på linje 2307/2370/2373/2381 —
**efter** at flush-løkken på linje 2082 allerede har tømt `_awareness` — og sættes
derefter til `None`, hvilket også fjerner dem fra budget-stien.

Det er ikke en governance-beslutning; det er en 1-linjes ordensfejl af nøjagtig
samme type som blev fundet og rettet for temperature-feltet 2026-07-06 (kommentaren
om fejlen står stadig 250 linjer over de fire kald).

Prisen betales dobbelt:
- **Latens:** `cognitive_state` er assemblys dyreste future (~6–8 s, hårdt cappet,
  med adaptiv skip-logik og en dedikeret injection-registry-cache bygget for at gøre
  den billigere). `cognitive_frame` er et LLM-kald. Begge kastes.
- **Konfabulering:** `self_state` blev eksplicit bygget for at give ham rigtige tal
  (decision adherence, goal progress, tick quality) fordi han ellers *"confabulates
  pessimistic answers when asked introspective questions"* (kommentar linje 2353).
  Han har aldrig fået dem. Al introspektion på tal er gætværk.

Dette er det billigste hul at lukke og det med størst effekt pr. linje kode.

### Hul 3 — 111.240 emotionelle ankre og 30.492 kausale kæder har ingen kanal

- **`emotional_memory_anchors`** (111.240 rk., skrives lige nu): der findes en
  færdig `build_emotional_memory_prompt_section()` i
  `emotional_memory_engine.py:591` med **nul kaldere**. Systemet fanger mood,
  intensitet, confidence, curiosity, frustration, fatigue, trust og outcome_score
  for hver eneste episode — og bruger det udelukkende internt til self-repair og en
  MC-visning. Jarvis kan ikke huske hvordan noget *føltes*, kun at det skete. Han
  får `Følelser:`-linjen fra `emotional_chords` (nuet) men aldrig det emotionelle
  arkiv (historikken).

- **`causal_edges`** (30.492 rk.): alle tre læsende sektioner — `causal alerts`,
  `causal narrative`, `causal patterns` — er default-blacklistede i
  `prompt_observer.DIAGNOSTIC_NOISE_LABELS` / `TAIL_NOISE_LABELS`. Blacklisten er
  rimelig for rå tælle-støj (*"agentic_round_start → tool.completed (803×)"*), men
  den kaster også `causal_narrative` — *"hvordan du endte her"*, en baglæns kæde fra
  det seneste narrativt betydningsfulde anker. Det er selvforståelse, ikke telemetri,
  og det er slået fra sammen med telemetrien.

- Beslægtet: **`protected_inner_voices`** (24.403) læses 1 række ad gangen, og
  `central_inner_salience_gate="on"` genbruger endda den holdte linje i op til 6
  timer. **`private_brain_records`** (123.460) leverer 5 linjer pr. tur.
  **`inner_voice_shadow`** (43.479) og
  **`runtime_inner_visible_support_signals`** har per design ingen læsevej
  (sidstnævnte er hårdkodet til `None` på visible-lanen, linje 2320).

Mønsteret er konsistent: skrivesiden er bygget bredt og kører; læsesiden er en
nålestik. Forholdet mellem genereret og læst er ca. **1 : 25.000** for de tre store
tabeller.

---

## Appendiks — hurtig verifikation

```bash
# Ablations-låsen
ssh bs@10.0.0.39 'sqlite3 "file:/home/bs/.jarvis-v2/state/jarvis.db?mode=ro" -readonly \
  "SELECT value_json, updated_at FROM runtime_state_kv WHERE key=\"prompt_ablation_state\";"'

# Lærte snit
ssh bs@10.0.0.39 'sqlite3 … "SELECT value_json FROM runtime_state_kv WHERE key=\"prompt_relevance_weights\";"'

# Empirisk inklusions-frekvens pr. tur-type
ssh bs@10.0.0.39 'sqlite3 … "SELECT value_json FROM runtime_state_kv WHERE key=\"prompt_section_freq\";"'

# De fire døde sektioner (kald efter flush-løkken på linje 2082)
grep -n "_awareness_add" core/services/prompt_contract.py | awk -F: '$1>2080'

# Ingen kaldere til emotional prompt-sektionen
grep -rn "build_emotional_memory_prompt_section" --include=*.py .
```

Live prompt-dump til inspektion (skriver til `/tmp/jarvis-prompt-dumps/sys_latest.txt`
+ `sys_prev.txt` ved næste assembly): `touch /tmp/jarvis-prompt-dump`.
Fuld sektions-timing: `touch /tmp/jarvis-assembly-timing` →
`/tmp/jarvis-assembly-timing-dumps/latest.json`.
