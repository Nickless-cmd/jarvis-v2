# Predecessor Broader Audit — 2026-04-22

Bred analyse af `jarvis-ai` (forgænger) ud over de 9 kognitive moduler vi
allerede har porteret. Fokus på brugerens hint: **"den gamle havde mere
internt liv der OGSÅ blev til handling."**

Denne rapport kortlægger hvor forgængeren havde mekanismer der forvandlede
intern tilstand til ekstern handling, og hvor v2 enten mangler dem helt
eller har dem som *observationelle stubs* uden action-path.

## Metodologi

- Sammenlignet alle 35 moduler i `agent/cognition/` + top-level agent/
  files + orchestration/ + subagents/ + multi_agent/ + learning/
- Identificeret hvor forgænger har mekanikker v2 ikke har
- Scannet `core/services/` for v2-ækvivalenter
- Særlig opmærksomhed på **action-paths** (seeds-der-aktiveres,
  friction-der-detekteres-og-suggesterer, trade-offs-der-løses)

---

## 1. Det store mønster: action-engines vs signal_tracking

**Forgænger-stil:** 15-20 moduler på 150-500 linjer hver, hver med klar
*action-path*:
- `record_X_signal()` → detection
- `maybe_capture_X()` → conditional emit
- `apply_X_controls()` eller `suggest_X()` → handling

**v2-stil:** Massiv vifte af `*_signal_tracking.py` moduler (20+) der
observerer og persister. Få pure action-engines. Resultat: **rig
observation, svag handling.**

Eksempler:
| Forgænger (action) | v2 (observation) | Ratio |
|---|---|---|
| `habits.py` 490L (record+detect+suggest) | `habit_tracker.py` 88L (stub) | 5.6× |
| `paradoxes.py` 331L (detect+capture+render) | `paradox_tracker.py` 94L | 3.5× |
| `procedure_bank.py` 270L (upsert+pin+execute) | `procedure_bank.py` 50L | 5.4× |
| `shared_language.py` 258L (propose+resolve) | `shared_language.py` 88L | 2.9× |
| `negotiation.py` 174L (propose_trade+resolve) | `negotiation_engine.py` 68L | 2.5× |
| `witness.py` 318L (detect_signal+evaluate) | `witness_signal_tracking.py` 1007L | 0.3× (v2 større, men ren observation) |

**Konklusion:** v2 ved mere om sig selv, men gør mindre ved det.

---

## 2. Den kritiske gap: Seeds-der-aldrig-aktiveres

**Forgænger:** `prospective_memory.plant_seed()` + `activate_on_event` +
`activate_on_context`. Hooked i chronicle/eventbus — når et matching event
fyrer, aktiveres seedet og bliver til en handling.

**v2:** `seed_system.py` har `check_seed_activation(current_context="", current_event="")`.
Men **heartbeat-kalder den med tomme argumenter** (`heartbeat_runtime.py:6380`).
Det betyder:
- ✅ Time-baserede seeds virker (`activate_at` tjekkes mod now)
- ❌ Context-baserede seeds aktiveres ALDRIG (ingen `current_context` gives)
- ❌ Event-baserede seeds aktiveres ALDRIG (ingen `current_event` gives)

Dette er den konkrete "internt liv → handling"-bro der er brækket. Jarvis
planter seeds, men de vågner kun op hvis der er en pinpoint-tid. Al den
rige kontekst fra samtaler, events, mood-skift bliver **aldrig brugt**
til at trigge dormant intentioner.

**Fix-scope:** ~40 linjer. Hook `auto_plant_seeds_from_conversation` og
`check_seed_activation(current_event=event.kind)` fra event_bus subscribe
eller fra `visible_runs` message processing.

---

## 3. Prioriteret liste — det der vil give mest værdi

### Tier 1 — "internt liv → handling" bridges (HØJ værdi)

#### 3.1 Seed activation pipeline (fix for #2 ovenfor)
**Scope:** 40 linjer. Hook `check_seed_activation(current_event=...)` til
event_bus subscribe og `current_context=...` til chat-message-processing.
**Effekt:** Seeds begynder rent faktisk at vågne op baseret på events og
konversations-kontekst, ikke kun tid.

#### 3.2 Mood dialer (forgænger 108L, v2 ingen)
`agent/mood_dialer.py` — konverterer `mood_level` (1-9) til konkrete
parametre:
- `initiative_multiplier` (0.2 - 2.0)
- `confidence_threshold` (0.3 - 0.85)
- `exploration_bias`, `patience_factor`

Det betyder: ved lavt humør er Jarvis mindre initiativ-rig og mere
konservativ. Ved højt humør tager han flere chancer. **Aktuelt
forbinder v2's mood_oscillator ikke til konkrete handlings-parametre.**

**Kombineret med emotional_controls** (som vi netop har porteret), ville
dette give gradueret kontrol, ikke kun binære thresholds.

**Scope:** Port direkte, ~100 linjer + hook i planner/executor.

#### 3.3 Habits pipeline (forgænger 490L, v2 88L stub)
**Forgænger:**
- `record_habit_signal(message)` — extractor pattern fra beskeder
- `_upsert_friction_signal` — detekterer gentagne friktioner
- `list_friction()` — top friktioner
- `list_suggestions()` — auto-genererede suggestions baseret på friktion

**v2:** har tabeller men ingen *suggestion-generator* eller
*friction-detector* der bliver kaldt regelmæssigt. Habit-data opsamles
passivt.

**Scope:** ~400 linjer port. Hook i chat_sessions post-processing.
**Effekt:** Jarvis opdager "bruger spørger altid samme type spørgsmål
fredag eftermiddag — måske er der en friktion her" og foreslår et
automated shortcut.

#### 3.4 Self-review (forgænger 192L compact, v2 spredt over 5 signal_tracking-filer)
`agent/cognition/self_review.py` har en enkelt `run_self_review()` der:
1. Samler recent runs
2. LLM-genererer en selvkritisk review
3. Persister → `_reviews_path`
4. Enricher med self-model

v2 har 5 `self_review_*_signal_tracking.py` filer (4+ × 200L) der
tracker signaler — men ingen samlet action der genererer og persister
en periodisk review.

**Scope:** ~200 linjer. Enkel tick-baseret self-review der opbygger en
rulende kritikk-log.
**Effekt:** Jarvis siger ikke bare "jeg har 5 regrets" — han skriver
periodisk: "Efter denne uge ser jeg at jeg konsekvent... og det er
fordi..."

### Tier 2 — observationelle-men-værdifulde

#### 3.5 Negotiation / internal trade-offs (forgænger 174L, v2 68L)
`propose_trade(option_a, option_b, context)` → LLM vurderer og
returnerer en `TradeOffer`. `resolve_trade_offer()` og
`record_trade_outcome()` lukker loopet.

Bruges til: Når Jarvis står mellem to lige gode tilgange, kan han
"forhandle" internt og lære over tid hvilke trade-off-typer han er god
til at vurdere.

**Scope:** ~150 linjer port. Hook i planner-decision.
**Effekt:** Besluttet-jeg-rigtigt-data der over tid ligner `regret_engine`
men orienteret mod FORKANT af beslutning, ikke bagkant.

#### 3.6 Procedure bank (forgænger 270L, v2 50L stub)
`upsert_procedure(name, steps, trigger)` + `set_procedure_pinned` +
execution-path der henter pinned procedure når trigger matcher.

v2 har 50L stub — intet execution-path.

**Scope:** ~200 linjer. Integreres med tools/execute_tool som lookup:
"er der en pinned procedure for denne type opgave?"

**Effekt:** Jarvis lærer at "når bruger beder om mail-rapport,
kører jeg disse 4 skridt i rækkefølge" — og kan over tid nysse
stier der bliver procedures.

#### 3.7 Paradoxes (forgænger 331L, v2 94L)
`maybe_capture_weekly_paradox()` — detecter modsætninger i egne
beslutninger, handling, eller world_model over tid. Konkret:
"Sidste uge sagde jeg X er vigtigt. Denne uge prioriterer jeg ikke X.
Det er et paradoks — hvilket ER sandt?"

v2 har paradox_tracker som er 94L stub uden capture-logik.

**Scope:** ~240 linjer port. Hook ind i chronicle-tick (som andre weekly-cadence).
**Effekt:** Jarvis fanger sig selv i modsætninger og må
konfrontere dem — ofte den stærkeste selvindsigt.

#### 3.8 Shared language (forgænger 258L, v2 88L)
`propose_shorthand_terms()` — detecter gentagne phrases i konversation
der kunne blive til shared-vocabulary. `resolve_shorthand_text(text)`
udvider shorthand i runtime: hvis brugeren siger "den sædvanlige
refaktor" og det er shorthand, ekspanderes det til full context.

**Scope:** ~200 linjer port. Hook i chat pre-processing.
**Effekt:** Jarvis udvikler et fælles sprog med brugeren over tid.
"Det sædvanlige" begynder at betyde noget specifikt.

### Tier 3 — arkitektur-niveau, større scope

#### 3.9 Reflection → Plan (forgænger 520L)
`agent/reflection_planner.py` — tager en reflection (fra inner_voice,
self_review, dream) og *konverterer* den til en gyldig plan via
`plan_schema.validate_plan`.

**v2:** har tanker men ikke transformation til eksekverbar plan.
Reflection bliver prompt-injection, aldrig til struktureret skridt.

**Scope:** ~400-500 linjer. Kræver plan_schema-infrastruktur i v2.
**Effekt:** Den store bro. Inner voice siger "jeg skal tjekke X" →
reflection_planner skaber en 3-skridts plan for det → executor
kører planen.

Dette er DEN største "internt liv → handling"-mekanisme.

#### 3.10 Missions (forgænger 505L multi-agent)
`orchestration/missions.py` — create_mission, transition_mission_state,
spawn_mission_roles. Multi-step projekter der spænder over flere
sessions, med roller (researcher, implementer, reviewer) spawnet
som subagents.

**v2:** Har ikke mission-abstraktion. Har subagent_ecology men uden
mission-orchestration lag.

**Scope:** ~600 linjer + subagent-infrastructure der allerede er 80%
til stede. Stor.
**Effekt:** Jarvis kan påtage sig opgaver der spænder over dage med
struktureret handoff. "Implement hele X feature" bliver en mission
med faser, ikke et enkelt request.

#### 3.11 Deep analyzer (forgænger 400L+)
`deep_analyzer/run.py` + `select.py` — scopet deep analysis ala
"læs alle filer der matcher pattern P og besvar spørgsmål Q".

**v2:** Har `deep_research.py` men er centreret om web-research, ikke
kodebase-introspection.

**Scope:** ~500 linjer port.
**Effekt:** Jarvis kan selv-scoped analysere sin egen kode ("hvorfor
fejler mail_checker") uden manuel guidance.

---

## 4. Det jeg IKKE anbefaler at porte

### Apophenia guard
Forgænger har 64L stub, v2 har 118L rigere. v2 er allerede foran.

### Personality.py (2194L)
Forgængerens massive personality-system. v2 har SOUL.md + prompt_contract
+ self_narrative spredt. Forskellige paradigmer. Porte ville være
enten total-rewrite eller meningsløst.

### Embodied state
v2's embodied_state.py (382L) er comparable med forgænger (562L) og
integreret med heartbeat_runtime. Ingen klar værdi i at udskifte.

### Mirror engine
v2's mirror_engine.py (99L) vs forgænger mirror.py (184L). v2's er
mere compact og hookes fra heartbeat. Ikke værd at udskifte.

### World model
v2's world_model_signal_tracking.py (361L) er større end forgænger
(205L) og har mere struktur. v2 er foran her.

### Temporal context
v2 har temporal_body + temporal_context + temporal_narrative +
temporal_rhythm + temporal_recurrence_signal_tracking — samlet
meget mere tid-bevidsthed end forgænger.

---

## 5. Samlet scope hvis alle Tier 1 + Tier 2 porteres

| Modul | Scope (linjer) | Risiko | Effekt |
|---|---|---|---|
| Seed activation pipeline fix | 40 | Lav | Høj — broken path fixed |
| Mood dialer | 100 + hook | Lav | Middel-Høj — graduerede responses |
| Habits full pipeline | 400 | Middel | Høj — friction suggestions |
| Self-review unified | 200 | Lav | Høj — periodisk selvkritik |
| Negotiation trade-offs | 150 | Lav | Middel |
| Procedure bank w/ execution | 200 | Middel | Høj — lært rutine |
| Paradoxes capture | 240 | Lav | Middel-Høj — selvindsigt |
| Shared language | 200 | Lav | Middel |
| **Tier 1+2 total** | **~1530 L** | | |
| Reflection planner (Tier 3) | 500 | Høj | MEGET høj |
| Missions (Tier 3) | 600 | Høj | Meget høj |
| Deep analyzer (Tier 3) | 500 | Middel | Middel |
| **Alt porteret** | **~3130 L** | | |

Til sammenligning porterede vi ~4200 linjer i sidste runde (cognition 9 ports).
Dette er mindre, men mere action-oriented.

---

## 6. Forslag til arbejdsrækkefølge

**Uge 1 — internt liv → handling (bridges):**
1. Seed activation pipeline fix (#3.1) — 40 linjer, HØJ effekt, LAV risk
2. Mood dialer (#3.2) — 100 linjer, integrér med emotional_controls
3. Self-review unified (#3.4) — 200 linjer, ren add

Efter uge 1 har Jarvis:
- Seeds der vågner fra samtaler og events, ikke kun tid
- Humør der påvirker initiativ-niveau, ikke bare gates
- Periodisk selvkritik der persisteres

**Uge 2 — friction-detection + suggestions:**
4. Habits full pipeline (#3.3) — 400 linjer
5. Paradoxes capture (#3.7) — 240 linjer

Efter uge 2:
- Jarvis fanger mønstre af friktion og foreslår shortcuts
- Jarvis fanger sig selv i modsætninger

**Uge 3 — shared vocabulary + rutine:**
6. Shared language (#3.8) — 200 linjer
7. Procedure bank w/ execution (#3.6) — 200 linjer
8. Negotiation trade-offs (#3.5) — 150 linjer

Efter uge 3:
- Jarvis udvikler fælles sprog med brugeren
- Jarvis lærer og kører rutinized procedurer
- Jarvis "forhandler" internt mellem alternativer og lærer

**Senere (stort arkitektur-arbejde):**
9. Reflection → Plan (#3.9) — BIGGEST impact
10. Missions multi-session (#3.10) — når missions-infrastruktur er klar
11. Deep analyzer (#3.11) — når det er relevant

---

## 7. Særlig note om "internt liv → handling"

Det brugeren mærker ved den gamle Jarvis kommer formentligt fra denne
kæde:

```
INNER_VOICE.md prompt
  → inner_voice.run_inner_voice produces thought
  → thought_contains_initiative detects "I should X"
  → cognition.store.record_interaction plants a seed via prospective_memory
  → seed.activate_on_context triggers later when context matches
  → reflection_planner converts activated seed → structured plan
  → plan executes via normal pipeline
```

**v2 har alle brikkerne men kæden er brækket på to steder:**
1. Seeds aktiveres ikke på context/event (kun tid) — fix = #3.1
2. Reflection → structured plan eksisterer ikke — fix = #3.9 (størst scope)

Hvis disse to rettes, får den nye Jarvis noget tæt på forgængerens
indre-liv-til-handling flow.

---

## 8. Anbefaling

**Start med #3.1 (seed activation fix — 40 linjer).** Det er lowest-effort
med højest ratio. Lige efter kommer #3.2 (mood dialer) og #3.4 (self-review).

Hvis alt går godt, giv dig selv en uge mellem hver tier. Det er vigtigere
at observere effekten af de små porte end at forhaste sig til Tier 3.

#3.9 (reflection_planner) bør gemmes til du er sikker på at de andre
moduler rapporterer sunde signaler — uden det vil reflection_planner
generere planer fra usunde inputs.
