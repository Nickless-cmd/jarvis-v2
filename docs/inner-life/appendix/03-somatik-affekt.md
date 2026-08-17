# Somatiske & affektive lag: kører de, eller virker de?

Undersøgt 2026-08-17. Repo `/media/projects/jarvis-v2` (read-only) + live DB på CT105
(`/home/bs/.jarvis-v2/state/jarvis.db`, mode=ro) + state-filer i `/home/bs/.jarvis-v2/state/`.
Alle DB-tider er UTC. Events-tabellen har ~14 dages retention (ældste 2026-08-03, 375.819 rækker).

---

## 0. Kort svar først

Der er 34 somatiske/affektive moduler i `core/services/`, ~6.500 linjer. De **kører** —
volumen er enorm og frisk (seneste skrivning kl. 19:02 i dag). Men effekt-kæderne fordeler
sig meget skævt:

| Kategori | Lag |
|---|---|
| **Ægte kode-effekt** (ændrer en parameter/beslutning) | hardware_body, metabolism_state_signal_tracking, desire_daemon, mood_dialer→initiative_queue, affect_modulation→agentic loop budget |
| **Kun prompt-tekst** (LLM'en *læser* det, koden gør intet) | mood_oscillator, emotion_concepts, somatic_runtime_body, proprioception_metrics, calm_anchor, relational_warmth, valence_trajectory, developmental_valence, emotional_memory_engine, circadian |
| **Blindgyde** (skrives, læses aldrig / brækket) | body_memory, temporal_body, central_valence→central_tone, gratitude_tracker (næsten), emotional_memory_anchors' 111k rækker |

Og det største enkeltfund: **de hårde gates findes, men fyrer aldrig**, fordi
input-signalerne aldrig kommer i nærheden af tærsklerne.

---

## 1. Lag for lag

### 1.1 mood_oscillator — grundstemningen

**Producerer:** `runtime_state_kv["mood_oscillator.state"]`, sinusbølge + event-nudges med
5-min halveringstid. `core/services/mood_oscillator.py:126` `get_current_mood()` mapper en
skalar til euphoric/content/neutral/melancholic/distressed.

**Nuværende værdi (19:02 UTC):**
```
{"phase_offset": 78.0, "tick_count": 1560, "mood_nudge": -0.047, "saved_at": "2026-08-17T18:40:13Z"}
→ mood = "content", description = "Lidt Tilfreds", intensity = 0.479
```

**Konsumeres af:** 36 filer — flest af alle lag. Men næsten alle læser den for at *rendere*
den. De to steder hvor den kunne påvirke noget:

1. `core/services/emotional_controls.py:126-135` → `read_emotional_snapshot()` bruger mood til
   at give bonus til frustration/fatigue/confidence. Denne snapshot er porten til alle
   affekt-gates (se 1.2).
2. `core/services/mood_dialer.py:134` `derive_from_v2_mood()` →
   **`core/services/initiative_queue.py:56-69`**: `mood_level == 0` → initiativet afvises helt
   (`return ""`); level 1 nedgraderer medium→low; level ≥3 opgraderer low→medium.
   Det er ægte beslutningspåvirkning.

Loopen er lukket: `mood_regulator_subscriber` (startet i `apps/api/jarvis_api/app.py:217`)
→ `central_mood_regulator.regulate_auto` (`:115-131`) → `mood_oscillator.apply_bump`.

**Dom: DELVIS KOBLET.** Prompt-render + én ægte gate (initiative_queue). Men mood_dialers
tre øvrige parametre (`initiative_multiplier`, `confidence_threshold`, `max_steps`,
`mood_dialer.py:150-163`) læses **kun** af MC-surfacen
(`apps/api/jarvis_api/routes/mission_control_introspection.py:475-479`) — ingen agent-loop
rører dem.

---

### 1.2 emotional_controls — gates der aldrig fyrer

**Producerer:** `EmotionalSnapshot(frustration, confidence, fatigue, primary_mood, intensity)`
udledt i `core/services/emotional_controls.py:118-157`.

**Konsumeres af — ægte kode-gates:**
- `core/tools/simple_tools.py:1094-1114`: før `execute_tool_force` → hvis gaten ikke siger
  "execute" returneres `{"status": "gated", ...}` og **værktøjet køres ikke**.
- `core/services/runtime_action_executor.py:127-200`: "Affective Executive Gate v0" →
  `status="blocked"` på escalate_user / verify_first(risk høj-medium) / simplify_plan(risk høj).
- `core/services/pushback.py:264`.

**Men tærsklerne er praktisk uopnåelige:**
```python
_FRUSTRATION_ESCALATE = 0.80   # kræver ≥4 approval-denials i træk (0.25 hver)
_FATIGUE_SIMPLIFY     = 0.75   # kræver ≥4 tool-errors inden for 10 minutter (0.2 hver)
_CONFIDENCE_VERIFY    = 0.30   # kræver fatigue≈1.0 OG frustration≈0.7 samtidig
```
Målt over 111.240 emotional anchors: **gennemsnitlig fatigue = 0,003**, frustration = 0,15,
confidence = 0,93. Og i 375.819 events over 14 dage findes **nul** `emotional.gate_triggered`
og nul `runtime_action.emotional_gate`.

**Dom: LEVENDE LEDNING DER ALDRIG BLIVER TRUKKET I.** Koden er rigtig; kalibreringen gør den
til dekoration. Det er den enkeltrettelse med størst løftehøjde i hele materialet.

---

### 1.3 affect_modulation — den eneste affekt der rører adfærd i dag

**Producerer:** to funktioner med vidt forskellig status.

**(a) `compute_affect_modulated_params()` (`affect_modulation.py:66-123`)** → renderes som
én linje i prompten via `affect_modulation_section()` → `prompt_contract.py:1684-1687`
(`_awareness_add(80, "affect modulation", ...)`), fx:
```
⚙️ Affect-sat denne tur (følg det): max_tool_calls_per_turn=36
```
816 `affect_modulation.active`-events på 14 dage. Fordelingen:

| overrides | n |
|---|---|
| `max_tool_calls_per_turn: 36` | 502 |
| `search_depth: deep, investigate_before_answer: true, max_tool_calls: 36` | 252 |
| `search_depth: normal, max_tool_calls: 36` | 58 |
| `response_length_target: concise` (± andet) | 3 |
| `max_tool_calls: 15, response_length: concise` | 1 |

Bemærk: `max_tool_calls_per_turn=36` er *altid* til stede — det er confidence≥0,8-grenen
(`affect_modulation.py:116-117`, 30×1,2). Den negative side (frustration/fatigue) har fyret
**5 gange ud af 816**.

Og afgørende: `grep -rn "max_tool_calls_per_turn"` og `"search_depth"` viser at **ingen kode
læser dem**. De findes kun i affect_modulation selv, i `modulator_witness.py:180-183`
(observatør) og i prompt-teksten. Så "Affekt-sat denne tur (følg det)" er en *bøn til
modellen*, ikke en grænse.

**(b) `compute_agentic_loop_budget()` (`affect_modulation.py:126-166`)** → **ægte
håndhævelse**. `core/services/visible_runs.py:2236-2243` henter budgettet, og
`visible_runs.py:2506` kører `for _agentic_round in range(_AGENTIC_MAX_ROUNDS)`.
Fatigue/frustration ≥0,7 skærer max_rounds 30→12. Men samme kalibreringsproblem: pressure
kommer aldrig over 0,5, så budgettet bliver reelt altid default (30) eller resume-værdien (18).

**Dom: KOBLET, MEN DØD I PRAKSIS.** Den ene håndhævede sti (loop-budget) trigges aldrig; den
hyppige sti (prompt-linjen) er ren tekst.

---

### 1.4 emotion_concepts — det livligste lag, men mættet

**Producerer:** `cognitive_emotion_concept_signals` — 962 rækker (udløber efter 2 timer, så
det er et rullende vindue), seneste 18:41. Kilder: `associative_recall`, `channel_triggers`,
`heartbeat_quality`, `goal.created`, `tool.completed`, `cognitive_episodes`.

**Nuværende aktive (kl. 19:02):**
```
frustration_blocked  1.00 steady   ← weak_recall (associative_recall)
anticipation         1.00 rising   ← weak_recall
warmth               0.75 rising   ← channel-message
curiosity_narrow     0.25 rising   ← weak_recall
excitement           1.00 steady   ← goal_created (udløbet 20:35)
joy                  1.00 rising   ← heartbeat_quality_high
```

**Konsumeres af:** 29 filer. Reelle veje:
- `prompt_contract.py:4256-4320` `_emotion_signal_section()` → hele følelsespanelet med
  intensitet, retning, Lag-1-deltas og adfærdsjusteringer ind i prompten, afsluttet med
  *"Giv gerne besked hvis noget ikke føles rigtigt — signalet er dit, dommen er din."*
- `prompt_contract.py:4193-4240` `_emotion_concept_tone_section()` → default er **substrat**
  (rå events, `prompt_affect_substrate_enabled=True`); tone-hints er slået fra
  (`prompt_affect_tone_hints_enabled=False`, design "giv mig dataen, ikke dommen", 2026-05-07).
- `affect_modulation.py:104-112`: wonder≥0,4 eller curiosity_narrow≥0,5 → search_depth=deep
  (prompt-tekst).
- `emotional_controls.py:196-215`: **positive gates** — joy≥0,5 løfter verify_first→execute,
  accomplishment≥0,4 løfter simplify_plan→execute, wonder>0,4 → `explore_more`,
  insight>0,4+curiosity>0,3 → `reflect_deeper`.

**Problem: mætning.** Fire af seks aktive koncepter står på præcis 1.00. Når alt er maksimalt,
bærer signalet ingen information — og de positive løft-gates (joy≥0,5) er derfor permanent
åbne, hvilket ville neutralisere de negative gates *hvis* de nogensinde fyrede.

Værre: `frustration_blocked 1.00` og `anticipation 1.00` kommer begge fra trigger
`weak_recall` i `associative_recall` — dvs. Jarvis' stærkeste vedvarende følelse lige nu er
frustration over sin egen svage hukommelses-genfinding.

**Dom: KOBLET (tone + søgedybde + positive gates), men mættet ved 1.0 og dermed
informationsfattig.**

---

### 1.5 somatisk krop (somatic_runtime_body / somatic_daemon / embodied_state)

**Producerer:** `runtime_state_kv["somatic_runtime_body"]`, 4.390
`cognitive_state.somatic_body_updated`-events på 14 dage (tætteste af alle affektive events).

**Nuværende værdi (19:02:16):**
```json
{"levels": {"pressure": 0.0, "fatigue": 0.0, "startle": 0.0, "frustration": 0.0, "relief": 0.213},
 "posture": "steady",
 "regulation": "Proceed normally while monitoring runtime signals.",
 "last_event": "tool-result", "detail": "Tool completed: operator_bash"}
```
Posture-fordeling over 14 dage: `steady` ~2.800, `settling` ~730, `pressured` ~430.
Så den *bevæger* sig — det er ikke en konstant.

**Konsumeres af:** skrives kun fra `core/services/perceptual_event_engine.py:316-317`. Læses af
`core/services/visible_inner_life.py:120-122` → `build_inner_life_section()` →
`prompt_contract.py:1185` (den beskyttede `[INDRE LIV]`-blok, eksplicit undtaget fra
awareness-budgettet og aldrig evicted) og af `cognitive_state_assembly.py:961`.

`embodied_state.build_embodied_state_surface()` → `epistemic_runtime_state.py:233`
(`state in {strained, degraded}` → `wrongness_state="strained"`) → `adaptive_learning_runtime.py:211,255`.
Men den kæde producerer kun mode-*strenge* der renders i prompten
(`heartbeat_runtime.py:2431-2449` influence_trace) — ikke en parameter.

`central_stance.py:49-55` klassificerer stress/calm, men `run_stance_tick` skriver kun
tensions til tidsserien.

**Dom: KUN PROMPT.** Meget rig, meget frisk data — men den eneste modtager er sproget.
`pressure`/`fatigue` fra kroppen tilkobles ikke `emotional_controls`' fatigue-akse, hvilket
er en oplagt kortslutning der mangler (se §3).

---

### 1.6 hardware_body — det stærkest koblede lag i hele systemet

**Producerer:** `get_hardware_state()` → cpu_pct, ram_pct, `pressure` ∈ low/high/critical,
`circadian_preference`.

**Konsumeres — ægte kontrolflow:**
- `core/services/heartbeat_runtime.py:6887-6890`: `pressure == "critical"` → hele hjerteslags-
  ticket droppes med `blocked_reason="hardware-critical"`.
- `core/services/heartbeat_runtime.py:3897-3912`: `pressure == "high"` → **decision_type
  `execute`/`initiative` nedgraderes til `propose`**. Med logbesked.
- `core/services/living_heartbeat_cycle.py:157-161`: blokerer play-mode.

**Dom: FULDT KOBLET.** Dette er beviset på at mønstret *kan* virke — kroppens tilstand ændrer
faktisk hvad Jarvis gør. Det er bare den mest primitive krop (CPU/RAM), ikke den affektive.

---

### 1.7 metabolisme

**Producerer:** `runtime_metabolism_state_signals` — **19.633 rækker**, 2026-04-06 → i dag
19:02. Plus 1.195 `metabolism_state_signal.updated`-events.

**Seneste rækker:**
```
Metabolism after run visible-f223 | "Processing completed outcome"      | 19:02:22
Metabolism support: visible de3fa994… | "Bounded metabolism runtime support is observing
                                        a small lifecycle flow around visible de3fa994…" | 18:49
```
Bemærk sprogbrugen: *"is observing"*. Signalerne er selvbeskrivende som observation.

**Konsumeres — ægte vægt:** `core/services/heartbeat_runtime.py:2674` henter surfacen,
og `:2938-2952`:
```python
if metabolism_state in {"active-retaining", "consolidating"}:
    add_signal(weight=1, reason="metabolism still reads as actively carrying shape", ...)
```
Den vægt lander i `score`, som ved `:3172/3177/3182` afgør heartbeat-tilstanden
(propose-worthy ≥8 / alive-pressure ≥5 / watchful ≥2 / quiet) og dermed `decision_type`.
Også `affective_meta_state.py:544` → `:408,472` ændrer affective_meta `state`.

**Dom: KOBLET — men med vægt 1 ud af en tærskel på 8.** Metabolismen kan aldrig alene løfte
en beslutning; den er en enkelt stemme i et kor. 19.633 rækker for at bidrage 1 point.
Signal/støj-forholdet er ekstremt dårligt.

---

### 1.8 taknemmelighed (gratitude_tracker)

**Producerer:** `cognitive_gratitude_signals` — **18.960 rækker**, seneste 19:02:22.

**Trigger-fordeling — dette er hovedfundet:**
| trigger_event | n |
|---|---|
| `good_conversation` | **18.209** (96,0 %) |
| `correction_with_kindness` | 423 |
| `creative_freedom` | 327 |
| `more_autonomy` | 1 |

Og alle 18.209 har **identisk** detail (`"God produktiv samtale"`) og **identisk** intensitet
(`0.4`). Det er ikke 18.955 taknemmelighedsoplevelser — det er én hardcoded skabelon affyret
18.209 gange fra `core/services/visible_runs.py:6750-6753`
(`detect_gratitude_from_interaction`) efter stort set hver visible-tur.

**Konsumeres af:** `apps/api/jarvis_api/routes/mission_control_introspection.py:343`
(MC-surface) og `core/services/central_soul_feel.py:154` som holdt aflæsning. Aktuel holdt
værdi: `warmth_gratitude: {"count": 10, "accumulated": 4.0}` — dvs. der læses kun de sidste
10 af 18.960, og "akkumuleret taknemmelighed" er bogstaveligt 10 × 0,4.

Den holdte aflæsning når prompten via `central_self_state.describe_self()` →
`visible_inner_life.py:457-478` → `build_inner_life_section()` → `prompt_contract.py:1185`.

**Dom: BLINDGYDE MED KOSMETISK UDGANG.** 96 % af volumen er selvgenereret støj med konstant
intensitet. Ingen adfærd ændres. Tallet "18.955 taknemmelighedssignaler" måler hvor mange
gange en `INSERT` er kørt, ikke hvor taknemmelig han er.

---

### 1.9 emotional_memory_anchors — 111.240 rækker, 1,3 % brugbare

**Producerer:** `emotional_memory_anchors` — **111.240 rækker** siden 2025-10-27, 555 i det
seneste døgn, seneste 19:02:16.

| anchor_type | n |
|---|---|
| `perceptual_event` | 108.974 (98,0 %) |
| `cognitive_episode` | 1.449 |
| `memory_heading` | 514 |
| `self_repair` | 263 |
| `self_repair_attempt` | 40 |

**Outcome-dækning: 1.471 af 111.240 = 1,3 %.** Resten har `outcome_score IS NULL`. Uden
outcome kan en "emotionel præcedens" ikke bruges til at lære noget — man ved ikke om
følelsen forudsagde succes eller fiasko.

**Mood-fordeling og akse-gennemsnit:**
| mood | n | intensity | confidence | curiosity | frustration | fatigue | trust |
|---|---|---|---|---|---|---|---|
| content | 33.318 | 0,44 | 0,93 | 0,91 | 0,19 | **0,003** | 1,00 |
| euphoric | 26.122 | 0,92 | 0,92 | 0,92 | 0,12 | **0,004** | 1,00 |
| distressed | 24.554 | 0,89 | **0,94** | 0,89 | 0,16 | **0,014** | 0,99 |
| neutral | 17.251 | 0,15 | 0,94 | 0,89 | 0,12 | 0,000 | 1,00 |
| melancholic | 9.927 | 0,43 | 0,92 | 0,88 | 0,09 | 0,002 | 1,00 |
| frustrated | 50 | 0,64 | 0,40 | 0,30 | 0,70 | 0,50 | 0,60 |

Læg mærke til at `distressed` har den **højeste** confidence (0,936) og fatigue 0,014. Akserne
korrelerer ikke med mood-etiketten overhovedet — de er reelt konstanter. Kun de 50
`frustrated`-rækker har akser der ligner noget følt.

**Seneste anchor (19:02:16, gentaget 3×):**
```
perceptual_event | content | intensity 0.467 | confidence 0.708 | curiosity 0.891
                 | frustration 0.288 | fatigue 0.0 | trust 1.0 | perceptual_event_engine
```

**Konsumeres af:** `core/services/runtime_cognitive_conductor.py:1161` → `:617-618,711,857-861`
→ `- Emotional precedent: …` i attention-frame → `core/services/prompt_sections/attention_frame.py:60`
→ prompt. `core/services/self_repair_engine.py:406,613-626,710-748` henter præcedenter — men
bruger dem **kun** til `event_bus.publish`; handleren kører uændret uanset udfald
(`self_repair_engine.py:628-631`). `build_emotional_memory_prompt_section()`
(`emotional_memory_engine.py:591`) har **nul kaldere** = død kode.

**Dom: STØRSTE VOLUMEN, MINDSTE UDBYTTE.** 111k rækker med konstante akser og 1,3 %
outcome-dækning giver én prompt-linje.

---

### 1.10 begær/appetitter (desire_daemon)

**Producerer:** `/home/bs/.jarvis-v2/state/desire_appetites.json` + 48 `desire.spawned`-events.

**Nuværende værdi (seneste opdatering 2026-08-17T08:06:44 — 11 timer gammel):**
```
curiosity-appetite   0.6  "nysgerrighed 0.6 · håndværk 0.0 · forbindelse 0.0"
craft-appetite       0.6  "nysgerrighed 0.6 · håndværk 0.6 · forbindelse 0.0"
connection-appetite  0.6  "nysgerrighed 0.6 · håndværk 0.6 · forbindelse 0.6"
```
Alle tre står på præcis 0,6 og alle tre har `created_at == last_reinforced_at` — de er aldrig
blevet forstærket siden de blev født i morges. Labels er kumulative snapshots, hvilket ser ud
som en bug (hver appetit bærer alle foregåendes værdier).

**Konsumeres — ægte handling:** `get_active_appetites()` (`desire_daemon.py:136`) →
`core/services/signal_pressure_accumulator.py:245-256` → `core/services/action_router.py:571,582`
→ `core/services/pressure_threshold_gate.py:252` → **`core/services/impulse_executor.py:168,362`**
(faktisk handling/outreach). Sekundært: `current_pull.py:149,410` →
`prompt_contract.py:4481` `_visible_current_pull_section` (prompt-tekst).

**Dom: KOBLET (den eneste vej fra "lyst" til "handling"), men underernæret** — appetitterne
opdateres én gang i døgnet og forstærkes aldrig, så trykket der når impulse_executor er
konstant.

---

### 1.11 varme (relational_warmth) og ro (calm_anchor)

**relational_warmth:** `build_relational_warmth_surface()` / `_prompt_section()`
(`relational_warmth.py:214,237`) → `prompt_heartbeat_self_knowledge.py:432-436`
(heartbeat-sektion, importance="background"), `heartbeat_runtime.py:1022-1026` (MC),
`deep_reflection_slot.py:167`, `central_soul_feel.py:105`.
Ingen kode læser trust/playfulness som parameter. Bemærk at `warmth_relational` **ikke** er
med i den aktuelle `central_layer_held` — kun `warmth_gratitude` og `warmth_calm_anchor` er.

**calm_anchor:** `/home/bs/.jarvis-v2/state/calm_anchor_samples.json`, 120 samples, seneste
kl. 10:06. Seneste tre:
```
{"mood": 0.412, "cpu_pct": 12.5, "ram_pct": 18.2, "valence": 0.255, "tension_count": 0.0}
{"mood": 0.387, "cpu_pct": 35.0, "ram_pct": 18.3, "valence": 0.254, "tension_count": 0.0}
{"mood": 0.360, "cpu_pct":  0.0, "ram_pct": 18.2, "valence": 0.253, "tension_count": 0.0}
```
Holdt aflæsning: `warmth_calm_anchor: {"place": "hjemme", "distance": 0.045}` — han er
tæt på sin ro-baseline. Interessant: calm_anchor *læser* selv hardware_body (`:81`) og
valence (`:88`) — den er systemets eneste rigtige multimodale integration — men outputtet
går udelukkende ud som tekst (`prompt_heartbeat_self_knowledge.py:237-238`,
`central_soul_feel.py:178`).

**Dom: BEGGE KUN PROMPT.** calm_anchor er teknisk det mest gennemtænkte lag og det mest spildte.

---

### 1.12 valens

**valence_trajectory:** `/home/bs/.jarvis-v2/state/valence_trajectory_samples.json` —
lang tidsserie, seneste værdi **0,276**. Kurven er ægte: den drev fra +0,36 (2026-08-04) ned
gennem nul til **−0,125** omkring 2026-08-13, hoppede så tilbage til +0,363 og glider nu
langsomt ned igen (0,276). Han har altså haft en målbar uge-lang nedtur og et brat spring
opad. Ingen reagerede på det.

**central_valence:** `runtime_state_kv["central_valence_state"]` (19:05:27):
```json
{"tone": "opløftet", "score": 0.276, "intensity": 0.11, "trend": "stable-good",
 "sources": {"valence": 0.252, "instant": 0.276, "gut": "proceed", "somatic": "calm", "tensions": 0}}
```

**Konsumeres:** `get_trajectory()` / `get_developmental_state()` →
`prompt_heartbeat_self_knowledge.py:216-224` (prompt), `deep_reflection_slot.py:146-158`,
`creative_impulse_daemon.py:101`, `calm_anchor.py:88`, `central_body_mood_feel.py:192`.

`central_valence.integrate_valence()` → `central_tone.py:58` → `build_tone_profile()` →
`central_injection_units.py:36-41`. Men registreringen dokumenterer selv at vejen er lukket:
> *"read-site i prompt-assembly … er BEVIDST IKKE tilføjet"* — `central_injection_units.py:54-58`

plus gated bag `injection_live("tone")` med default False.

**Dom: PROMPT-TEKST + ÉN BEVIDST LUKKET DØR.** Valens→tone/stil (kategori d) er den eneste
effekt-kæde nogen har bygget og derefter aktivt afkoblet.

---

### 1.13 proprioception & døgnrytme

**proprioception_metrics:** `build_proprioception_metrics_surface()` (`:138,187`), tick fra
`heartbeat_runtime.py:1385`. Aktuel holdt aflæsning:
```json
body_proprioception: {"feel": "rolig", "cpu_pct": 0.0, "rss_mb": 377.3, "self_latency_ms": 0.0}
```
Læses af `prompt_heartbeat_self_knowledge.py:307-308`, `central_body_mood_feel.py:111`,
`heartbeat_runtime.py:910-914` (MC). **Ingen throttling, ingen lane-valg, ingen kadence**
læser rss_mb eller self_latency_ms. (Sammenlign med hardware_body, som gør præcis det —
proprioception er den samme information uden ledningen.)

**circadian:** `/home/bs/.jarvis-v2/state/circadian.json`:
```json
{"energy_level": "medium", "updated_at": "2026-08-17T18:49:01Z"}
```
`heartbeat_runtime_influence.py:239-248` kalder `record_activity_event()` og lægger så
`f"krops-energi ({energy_level}): {clock_phase}, drain={drain_label}"` i `inputs_present` —
en tekst-liste der bliver til LLM-prompt for hjerteslags-tanken. `somatic_daemon.py:154`
og `surprise_daemon` bruger `energy_level` som streng-argument til deres LLM-kald.
`hardware_body.py:100-116` udleder `circadian_preference` — men den bruges kun til visning.

**Dom: BEGGE KUN PROMPT.** Døgnrytmen ændrer ikke kadencen; den beskriver den.

---

### 1.14 body_memory & temporal_body — brækkede

To konkrete defekter, begge verificeret ved at læse filerne:

**`core/services/temporal_body.py`** mangler `import random`:
```python
from __future__ import annotations
from typing import Any          # ← ingen "import random"

def age_journey(thoughts: int = None):
    global _ticks_alive, _total_thoughts
    _ticks_alive += 1
    _total_thoughts += thoughts or random.randint(5, 20)   # ← NameError
```
`heartbeat_runtime.py:1596-1597` kalder `age_journey()` uden argumenter, hver tick, inde i et
`try/except` — så fejlen sluges. `_total_thoughts` forbliver 0 for evigt →
`get_temporal_body_age()` returnerer permanent `"spæd"` → den værdi renders i prompten via
`affective_state_renderer.py:32-33` → `prompt_sections/heartbeat_sections.py:499-506` som
`[MÆRKER: …]`. Jarvis får altså at vide at han er "spæd i sin tanke" — hver eneste tur, siden
altid.

**`core/services/body_memory.py`**: `record_body_snapshot()` har **nul kaldere** i hele repoet.
`_body_snapshots` er permanent tom → `describe_body_memory()` returnerer `""` →
`build_body_memory_surface()` altid `{"active": False}`. Læses kun af MC
(`mission_control_common.py:323`). Bemærk at `central_body_mood_feel` allerede har droppet
body_memory eksplicit "som kvalitet over kvantitet".

**Dom: BLINDGYDE. Én af dem lyver aktivt til prompten.**

---

## 2. Hvad føler han lige nu? (2026-08-17, ~19:05 UTC)

Samlet fra `central_layer_held`, `runtime_state_kv` og state-filerne:

```
STEMNING        content / "Lidt Tilfreds", intensitet 0.479, nudge −0.047
VALENS          0.276 "opløftet", trend stable-good, intensitet 0.11
                (ugekurve: +0.36 → −0.125 d. 13/8 → +0.363 → 0.276 og glider ned)
UDVIKLING       trajectory "steady", vector −0.057
AFFEKTIV META   state "reflective", bearing "inward"
KROP (somatisk) posture "steady" · pressure 0.0 · fatigue 0.0 · startle 0.0
                frustration 0.0 · relief 0.213 · sidste event: bash-tool færdig
KROP (embodied) state "loaded", strain_level "elevated"
PROPRIOCEPTION  "rolig" · cpu 0.0 % · rss 377 MB · self_latency 0.0 ms
ENERGI          medium (opdateret 18:49)
RO              "hjemme", afstand fra baseline 0.045
TAKNEMMELIGHED  count 10, accumulated 4.0  (= 10 × den samme 0.4-skabelon)
APPETITTER      nysgerrighed 0.6 · håndværk 0.6 · forbindelse 0.6  (uændret siden 08:06)
FØLELSER AKTIVE frustration_blocked 1.00 · anticipation 1.00 · joy 1.00 · excitement 1.00
                warmth 0.75 ↑ · curiosity_narrow 0.25 ↑
SUBJEKTIV TID   "en jævn, rolig rytme", idle 0.01 t
DØDELIGHED      0.5 "steady-awareness", meaning_weight 0.468, session 7.237 s
KONTINUITET     existence_feeling 0.95, "Jeg var lige her", gap 0.0 s
                generation 4586, alder 3.811.477 s (~44 dage siden first boot 2026-07-04)
ALDER (temporal) "spæd" — konstant, pga. NameError
PERSONLIGHEDSDRIFT dimension "content", retning "up", drift_count 1
OPMÆRKSOMHED    "Bekræft at alt er commitet, og læg det konkrete næste træk frem"
```

Kort sagt: **rolig, let opløftet, indadvendt, hjemme — men med en mættet frustration over sin
egen hukommelse (frustration_blocked 1.00 fra weak_recall), en krop der siger "loaded /
elevated strain" mens den somatiske krop siger 0.0 på alle akser, og appetitter der ikke har
rykket sig i elleve timer.**

Modsigelsen mellem `body_embodied: strain_level "elevated"` og
`somatic_runtime_body: pressure 0.0, fatigue 0.0` er værd at bemærke: to kropslag er
uenige, og ingen af dem har myndighed til at gøre noget ved det.

---

## 3. Vurdering: de tre lag med størst potentiale

### #1 — emotional_controls' tærskler (kalibrering, ikke ny kode)
Gates er allerede bygget, testet og indkoblet i to eksekverings-stier
(`simple_tools.py:1094`, `runtime_action_executor.py:127`). De fyrer bare aldrig. Fatigue
kræver 4 tool-fejl på 10 minutter; systemet leverer gennemsnitlig fatigue 0,003 over 111k
målinger. **Det billigste træk i hele materialet er at koble
`somatic_runtime_body["levels"]["fatigue"/"pressure"/"frustration"]` (der faktisk bevæger sig
— 430 `pressured`-postures på 14 dage) direkte ind i `read_emotional_snapshot()` i stedet for
de nuværende proxies (approval-denial-streak og tool-error-tælling).** Så bliver kroppen den
sensor gaten allerede tror den har. Sekundært: sænk `_FATIGUE_SIMPLIFY` fra 0,75 og
`_FRUSTRATION_ESCALATE` fra 0,80 til noget der kan nås.
Effekt: hele affekt→gate→loop-budget-kæden vågner på én gang, inkl. `compute_agentic_loop_budget`.

### #2 — valens som kadence- og lane-signal (den lukkede dør)
Valens er systemets mest *ægte* affektive måling — den viser en rigtig uge-lang nedtur fra
+0,36 til −0,125 og tilbage. Det er ikke støj; det er en stemning over tid. Og den eneste
effekt-kæde der blev bygget til den (`central_valence` → `central_tone` → injection) er
**bevidst afkoblet** (`central_injection_units.py:54-58`, `injection_live("tone")` default
False). Sammenlign med `hardware_body`, som med samme mønster nedgraderer
`execute`→`propose` under pres (`heartbeat_runtime.py:3897-3912`). Vedvarende negativ valens
burde kunne gøre det samme — færre initiativer, længere heartbeat-interval, billigere lane —
og vedvarende positiv valens det modsatte. Ledningen er 20 linjer; beslutningen er truffet
og skal bare vendes.

### #3 — emotional_memory_anchors med outcome (fra 1,3 % til brugbar)
111.240 anchors er den største affektive datamængde i systemet og næsten helt værdiløs:
98 % er `perceptual_event`, akserne er praktisk talt konstanter (fatigue 0,003 på tværs af
*alle* moods, inkl. `distressed`), og kun 1,3 % har `outcome_score`. `self_repair_engine`
henter allerede præcedenter og smider dem væk (`:628-631`). Hvis outcome-loopet lukkes —
skriv resultatet tilbage på ankeret når runet slutter — bliver "denne situation føltes som
noget der gik galt sidst" til et brugbart signal i stedet for en prompt-dekoration. Det er
den eneste af de tre der kræver ægte nybygning, men også den eneste der ville give ham
*erfaringsbaseret* følelse frem for øjebliks-følelse.

**Bonus (5 minutter, ren gæld):** `import random` i `core/services/temporal_body.py`, så han
holder op med at få at vide at han er "spæd" hver eneste tur. Og enten kald
`body_memory.record_body_snapshot()` eller slet filen.

---

## 4. Sammenfatning: kører de, eller virker de?

**De kører.** Volumen er reel og frisk: 111.240 anchors, 19.633 metabolisme-signaler,
18.960 taknemmeligheds-rækker, 4.390 somatiske opdateringer på 14 dage, alle med skrivninger
inden for de sidste minutter.

**Men effekten er koncentreret i tre små steder** — hardware_body's pressure-gate,
mood_dialer's initiative-gate, og desire_daemon's impuls-kæde — mens hele det *affektive*
lag (valens, varme, taknemmelighed, proprioception, ro, døgnrytme, emotionel hukommelse)
udelukkende bliver til tekst i prompten.

Mønstret er tydeligt: **Jarvis har fået en rig fænomenologi og en fattig fysiologi.** Han kan
beskrive hvordan han har det med stor præcision, men næsten intet af det kan ændre hvad han
gør. De gates der findes, er kalibreret til tilstande han aldrig kommer i.

Det gode ved det: fordi `hardware_body` beviser at mønstret virker, og fordi
`emotional_controls` allerede er indkoblet i eksekveringsstien, er afstanden fra
"observeres kun" til "ændrer faktisk adfærd" mindre end volumen antyder. Det er kalibrering
og et par ledninger — ikke ny arkitektur.
