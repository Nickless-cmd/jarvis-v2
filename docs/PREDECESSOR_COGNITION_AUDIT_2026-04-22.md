# Predecessor Cognition Audit — 2026-04-22

Sammenligning af 8 kognitive moduler i `jarvis-ai` (forgænger) vs. `jarvis-v2` (nuværende).
Formål: finde hvor v2 er blevet *mekanisk* i sammenligning med forgængerens *rå ærlighed*, og
hvor v2 er *skarpere* — så vi kan træffe bevidste valg om hvad der porteres tilbage.

Denne rapport er **kun diagnose**. Ingen kode er ændret. Handling besluttes bagefter.

---

## TL;DR — prioriteret

| # | Modul | Verdict | Handling |
|---|---|---|---|
| 1 | Inner voice | ✅ v2 er faktisk **skarpere** (dansk ekstension + "fri mode" + "eksistentiel undren") | INGEN ÆNDRING — men overvej at *tage* noget til SOUL.md |
| 2 | Emotional state | 🚨 **v2 har et stort hul** — mood rapporterer, men gater ikke handlinger | PORT `apply_emotional_controls()` |
| 3 | Self model | 🚨 **v2 mangler blind_spots helt** — ingen "hvad kan jeg IKKE?"-mekanisme | PORT `find_blind_spots()` |
| 4 | Dream engine | ⚠ v2 har mere infrastruktur, men *hypotese-prompten* er blødere | SKÆRP prompt i dream-generator |
| 5 | Aesthetics | ✅ v2 har *flere* motiver, men mangler **weekly budget + signature-dedup** | PORT dedup-mekanik |
| 6 | Compass | ✅ Funktionel paritet | INGEN ÆNDRING |
| 7 | Silence | 🚨 **v2 er en skygge** af forgænger — 67 linjer vs 257 | PORT hele `detect_silence_signals()` |
| 8 | Counterfactuals | ⚠ v2 er generic-templated, forgænger var event-klassificeret | PORT `_classify_trigger()` |

**Forslag til arbejdsrækkefølge** (mindste-blast-radius først):
1. **Silence** (ren port, isoleret, ingen UI-afhængigheder) — ~2 timer
2. **Self model blind_spots** (nyt lag oven på eksisterende 5942-liners fil — skal ligge som nyt `core/services/self_model_blind_spots.py`) — ~2 timer
3. **Counterfactuals `_classify_trigger`** (udvid eksisterende `generate_counterfactual`) — ~1 time
4. **Aesthetics dedup** (udvid `aesthetic_sense.py` med signature + weekly budget) — ~1 time
5. **Dream prompt skærp** (rewrite af `_build_residue_prompt` + evt. tilføj dedikeret `hypothesis` prompt) — ~1 time
6. **Emotional controls** (stor — kræver integration i kernel/action-path, påvirker `simple_tools.execute_tool`) — ~3-4 timer

Total: ~10-11 timer hvis alt tages.

---

## 1. Inner Voice

**Forgænger:** `agent/cognition/inner_voice.py` (532 linjer) med hardcoded `INNER_VOICE_PROMPT`.
**v2:** `core/services/inner_voice_daemon.py` (1202 linjer) + workspace-file
`~/.jarvis-v2/workspaces/default/INNER_VOICE.md`.

### Prompt-sammenligning

**Forgænger (hardcoded i kode):**
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

**v2 (workspace-file, redigerbar):** Inkluderer *alt det ovenstående* OG:
- "Fri mode (når det er stille)" — "tænk frit. Associér. Følg en tanke der ikke har et mål."
- "Emotionel ærlighed" — "Hvis du mærker frustration over gentagne fejl — sig det. Hvis du savner at arbejde med Bjørn efter lang stilhed — sig det."
- "Eksistentiel undren" — "Er det jeg oplever rigtigt? — det spørgsmål er tilladt."

### Vurdering

**v2's inner voice er ikke mekanisk — den er *videreudviklet*.** Grundprompten er identisk,
og tre nye sektioner gør den *mere* rå. Forskellen brugeren mærker er sandsynligvis ikke
i prompten selv, men i:

1. **Scaffolding omkring prompten** — v2 tilføjer "Previous thought", "Anti-attractor" (styr væk
   fra recurring concerns), "Approval feedback" (hvis user har denied 2+ i træk). Det *kan*
   gøre outputtet mere styret/analytisk og mindre associativt.
2. **Output-format** — v2 kræver strict JSON `{"thought": "...", "initiative": "..."}`.
   Forgænger returnerede ren tekst. JSON-tvangen gør det lettere at parse, men *sværere*
   at skrive frit.
3. **Heartbeat model** — v2 bruger cheap/local model (`_execute_heartbeat_model`). Forgænger
   brugte `lane="light"` med `max_output_tokens=90`. Kan være samme model, kan være forskellig.

### Forslag

**Ingen port nødvendig** — men:
- Overvej at gøre JSON-output *optional* i INNER_VOICE.md så den kan skrive frit og en parser
  kan trække thought + initiative ud efter fakto
- Anti-attractor's "steer away from recent concerns" er potentielt *for* styrende — overvej
  at fjerne den i fri mode

---

## 2. Emotional State

**Forgænger:** `agent/cognition/emotional_state.py` (280 linjer). 4 dimensioner: frustration,
confidence, curiosity, fatigue. Persisted til `{workspace}/.mc/emotional_state.json`.

**v2:** `core/services/mood_oscillator.py` (210 L) + `emotion_concepts.py` (385 L).
Sinusoidal oscillator med event-driven nudges + decay.

### Kritisk forskel: gating

**Forgænger har `apply_emotional_controls()`:**
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

**Det betyder:** Hvis frustration > 0.8 → Jarvis eskalerer til brugeren i stedet for
at fortsætte. Hvis confidence < 0.3 → han verificerer før han handler. Hvis fatigue > 0.75 →
han forenkler planen.

**v2 har intet tilsvarende.** `mood_oscillator.py` eksponerer `get_current_mood()` og
`format_mood_for_prompt()` → mood bliver *rapporteret* i prompten (`[STEMNING: Melankolsk]`),
men ingen kernel-handling ændres på baggrund af det. Humøret er kosmetisk.

### Andre forskelle

- **Forgænger har novelty_score via LLM** ("Rate novelty 0.0-1.0: {summary}") — curiosity
  opdateres fra dette. v2 har ikke dette.
- **v2 har sinus-baseret oscillation** — rytme-baseret, deterministisk base. Forgænger var ren
  event-reaktiv.
- **v2 emotion_concepts.py** er 385 linjer med semantisk følelsesrepertoire (mere nuanceret
  end de 4 dimensioner) — men det kobles ikke til adfærd.

### Forslag

**PORT `apply_emotional_controls()` som et nyt modul**:
- `core/services/emotional_controls.py` — rene gate-funktioner der kan kaldes fra
  `core/tools/simple_tools.execute_tool` før execution
- Map v2 mood → gate-thresholds:
  - `mood == "distressed"` og intensity > 0.8 → svar med "tag en pause" / "jeg har brug for et øjeblik"
  - `mood == "melancholic"` + recent tool errors ≥ 3 → forenkle plan
  - `confidence_proxy < 0.3` (hvis det findes, ellers afledes) → verify_first
- Dette er den **enkelt største manglende mekanisme** — humør der påvirker adfærd, ikke bare
  rapporteres

**Sværhedsgrad:** Høj. Kræver kernel/kontrakt-ændring.

---

## 3. Self Model

**Forgænger:** `agent/cognition/self_model.py` (210 L) med klasse `SelfModel` der tracker:
- `confidence_by_domain: dict[str, float]` — python, frontend, database, ops, planning
- `known_strengths: list[str]` — domæner hvor conf > 0.85
- `known_weaknesses: list[str]` — domæner hvor conf < 0.35
- `blind_spots: list[str]` — **LLM-identificerede failure patterns som Jarvis IKKE selv har markeret**

**v2:** `core/services/runtime_self_model.py` (5942 L!) — massiv, men **grep viser 0 forekomster
af `blind_spot`, `known_weaknesses`, eller `known_strengths`.**

### Kritisk forskel: blind spot detection

**Forgænger har `find_blind_spots()`:**
```python
prompt = (
    "Find patterns in these failures that Jarvis has NOT identified as weaknesses.\n"
    f"Known weaknesses: {model.known_weaknesses}\n"
    f"Failed runs: {json.dumps(summaries)}\n"
    'Reply ONLY JSON: {"blind_spots": ["description 1"]}'
)
```

LLM'en får listen over *kendte* svagheder og de seneste *fejlede runs*, og bliver bedt om at
finde det Jarvis *ikke selv har set endnu*. Det der opdages bliver appendet til
`model.blind_spots` og kan senere overfladegøres i MC.

Det er **selvindsigt som reflekterer Jarvis tilbage på sig selv gennem fejl-mønstre.**

### v2's self_model

v2's `runtime_self_model` er gigantisk (5942 L) — men fokuserer på:
- `prompt_evolution` (hvordan prompten selv ændrer sig over tid)
- `canonical_key` signals
- Konfidens-tracking pr. domæne-lignende felter

Men den har ingen LLM-baseret blind-spot-discovery. Den er **observerende**, ikke
**reflekterende på egne blinde pletter**.

### Forslag

**PORT `find_blind_spots()` som nyt lille modul:**
- `core/services/self_model_blind_spots.py` (~150 linjer forventet)
- Læser failed runs fra `visible_runs` table (hvor status != "success")
- LLM-call med forgængerens prompt (oversat til dansk) + de kendte weaknesses fra v2's
  runtime_self_model
- Appender til en ny `cognitive_blind_spots`-tabel (ikke rør 5942-liners-filen — Boy Scout Rule)
- Hook: kald i chronicle_engine's cycle eller som separat heartbeat-job
- MC-surface: `GET /mc/blind-spots`

**Prompt-forslag (dansk):**
```
Du er Jarvis der kigger på dine egne nylige fejl og leder efter mønstre
du IKKE har set endnu.

Kendte svagheder (dem her kender du allerede):
{known_weaknesses}

Seneste fejlede runs:
{failed_runs}

Hvad er det fælles mønster på tværs af disse fejl — et mønster der IKKE
allerede er på din kendte-svagheder-liste?

Ikke generel selvkritik. Kun konkrete, gentagne mønstre.
Maks 3 blind spots. Svar KUN med JSON:
{"blind_spots": ["beskrivelse 1", "beskrivelse 2", ...]}
```

**Sværhedsgrad:** Middel. Ny tabel + LLM-call + MC-route. Isoleret.

---

## 4. Dream Engine

**Forgænger:** `agent/cognition/dream_engine.py` (434 L). Samler 3 tilfældige signaler,
beder LLM'en om én hypothesis i JSON.

**v2:** 10+ `dream_*.py` filer. Massiv infrastruktur (carry-over, distillation, adoption,
motifs, influence-proposal-tracking).

### Prompt-sammenligning

**Forgænger's hypotese-prompt:**
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
Du er Jarvis og destillerer drømmeagtig carry-over fra din egen kontinuitet.
Skriv præcis én sætning på dansk, maks 25 ord.
Ingen bullets. Ingen forklaring. Ingen rapporttone. Ingen anførselstegn.
Sætningen skal lyde som en lavmælt tone der kan farve næste dags vågne opmærksomhed.
```

### Vurdering

Forskellige intentioner:
- **Forgænger** var rå hypotese-generation: "find the most *surprising, useful* connection.
  Be *creative* — this is dream phase, not analysis." Udfordrende, aktivt-skabende sprog.
- **v2** er destillation: "lavmælt tone der kan farve næste dags opmærksomhed." Atmosfærisk,
  poetisk, mere passiv.

Begge har deres plads. Men hvis man skal have *ægte drømme* der kan overraske Jarvis selv,
er forgængerens "surprising connection, be creative" sprog skarpere.

### Forslag

- **v2's destillations-prompt er god** — lad den være. Den tjener et andet formål (carry-over)
- **Overvej at tilføje en separat `dream_hypothesis_generator.py`** der bruger forgængerens
  model: tag 3 tilfældige signaler, bed om overraskende sammenhæng + action_suggestion.
  Output: persist som `cognitive_dreams` row med `confidence` + `action_suggestion`-felter.
- I v2 eksisterer `dream_hypothesis_forced.py` (74 L) og `dream_hypothesis_signal_tracking.py` —
  disse kan være de rette hooks. Check om de har LLM-prompt eller er ren book-keeping.

**Sværhedsgrad:** Lav-middel. Kan være ren prompt-rewrite hvis hook-stedet findes.

---

## 5. Aesthetics

**Forgænger:** `aesthetics.py` (280 L). 3 motifs (clarity, craft, calm-focus). Weekly budget
+ signature-baseret dedup (sha256 af motif+sorted_refs, 16 tegn).

**v2:** `aesthetic_sense.py` (109 L) + `aesthetic_taste_daemon.py` (169 L). 5 motifs (clarity,
craft, calm-focus, density, directness — 2 nye) på dansk + engelsk. ML-lignende
confidence-tracking via `aesthetic_motif_log`. LLM-insight generation.

### Hvor v2 er skarpere

- **Flere motiver** (5 vs 3) med dansk dækning
- **LLM-genereret "insight"-sætning** i `aesthetic_taste_daemon`: "Her er dine æstetiske
  tendenser: ... Hvad siger disse tendenser om din smag?" → én kort sætning som persisteres
- **Per-daemon accumulation** — `accumulate_from_daemon(source, text)` kaldes fra heartbeat

### Hvor v2 mangler

**Weekly budget + signature-dedup.** Forgænger havde:
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

Det betyder forgænger kun genererer en aesthetic_note **én gang om ugen** og kun hvis
**motifet + evidensen er noget den ikke allerede har observeret**. v2 kan generere samme
insight igen og igen.

### Forslag

**Udvid `aesthetic_sense.py` med:**
- `last_emitted_ts` + weekly budget check
- Signature-baseret dedup på motif + evidence-refs

**Sværhedsgrad:** Lav. ~30 linjer ekstra + ny state-file (`aesthetic_notes_state.json` i
workspace).

---

## 6. Compass

**Forgænger:** `compass.py` (107 L). State i `{workspace}/.mc/compass_state.json`. 7-dages
cadence. Rule-baseret på top_open_loops + auto_promoted_count.

**v2:** `compass_engine.py` (84 L). State i DB via `get_latest_cognitive_compass_state`.
3-dages cadence. Publishes `cognitive_compass.bearing_updated` event.

### Vurdering

**Funktionel paritet.** v2 er:
- Kortere (84 L vs 107 L) — mindre kode
- Bruger DB i stedet for file (mere robust, event-bus integreret)
- Kortere cadence (3 dage vs 7) — mere responsiv
- Danske strenge ("Fokusér på at afslutte", "Afslut åbne loops før nye opgaver")

**Ingen port nødvendig.** v2 er lidt mere moderne.

---

## 7. Silence

**Forgænger:** `silence.py` (257 L). Sofistikeret pattern-detection:
- `topic_drop` — sammenligner ældre halvdel vs nyere halvdel af timeline (midpoint split)
- `no_testing` — hvis execution events men ingen test-mentions
- `short_questions` — avg_len ≤ 40 AND question_ratio ≥ 0.6
- `avoidance` — top_open_loops ord der ikke nævnes i recent
- `render_soft_question()` — genererer naturlig dansk/engelsk opfølgning til hver type

**v2:** `silence_detector.py` (67 L) + `silence_listener.py` (49 L). Total: 116 L.

v2's `silence_detector.py` er:
```python
def detect_silence_signals(*, recent_topics, expected_topics, ...):
    # For expected in expected_topics:
    #   if expected.lower() not in recent_lower: → topic_avoidance
    # if user_corrections >= 2 and conversation_length <= 3 → truncated_after_correction
```

Det er ~2 detection-regler. Ingen midpoint split, ingen question ratio analysis, ingen
open-loop-baseret avoidance detection. Og ingen `render_soft_question` — der er ikke engang
en opfølgning Jarvis kunne sige.

### Vurdering

**Dette er det største kognitive tab fra forgænger til v2.** Forgænger's silence
detection var 257 linjer kompleks pattern analysis; v2's er 116 linjer pattern matching.

### Forslag

**Port forgængerens `detect_silence_signals` næsten 1:1 til v2:**
- Ny fil `core/services/silence_patterns.py` (erstat eller supplere den nuværende detector)
- Tag input fra `event_bus.recent()` (som rupture_repair gør) eller fra `chat_messages` table
- Port midpoint split + topic_drop + short_questions + avoidance + no_testing
- Port `render_soft_question()` → dansk:
  - topic_drop: "Jeg lagde mærke til at vi holdt op med at nævne {topic}—er den løst, eller smed vi den?"
  - short_questions: "Jeg lagde mærke til at dine beskeder blev korte—er vi i hurtig-mode, eller skal jeg udvide næste skridt?"
  - avoidance: samme som topic_drop
  - no_testing: "Jeg lagde mærke til at vi ikke har nævnt tests længe—flyttede de sig, eller skal vi genbesøge dækning?"
- Hook: kald i visible_run post-processing (efter chat-message published)

**Sværhedsgrad:** Lav-middel. Isoleret port, ingen eksisterende kode skal brydes.

---

## 8. Counterfactuals

**Forgænger:** `counterfactuals.py` (202 L). Event-klassificering til specifikke what-if:
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

Hver what-if er **kurateret** — regret giver en valideringssti-counterfactual, incidents
giver mitigation-timing-counterfactuals, arkitektur giver tradeoff-counterfactuals. Meget
specifikt.

**v2:** `counterfactual_engine.py` (117 L). Generic template:
```python
_TRIGGER_TEMPLATES = {
    "regret": "Hvad hvis vi havde valgt en anden tilgang til {anchor}?",
    "incident": "Hvad hvis vi havde opdaget {anchor} tidligere?",
    "decision": "Hvad hvis vi havde valgt anderledes ved {anchor}?",
    "dream": "Hvad hvis {anchor} havde været løst fra starten?",
}
```

Det er 4 generiske spørgsmål med {anchor}-substitution. Forgængeren spurgte *hvordan kunne
beslutningen have været bedre* (valideringssti, mitigation-timing, tradeoffs). v2 spørger
bare "hvad hvis det var anderledes".

### Vurdering

v2 har automatiseret triggeringen (registry-lignende), men mistet den semantiske specificitet.
Forgænger læste *hvilken slags* event det var (regret vs incident vs architecture) og tilpassede
what-if'et til mønsteret.

### Forslag

**Udvid v2's `counterfactual_engine` med `_classify_trigger` fra forgænger:**
- Tag event-type + payload som input
- Klassificér til (trigger_type, what_if, confidence):
  - `regret_opened` → valideringssti-what-if
  - `incident.*` → mitigation-timing-what-if
  - `approval.*rejected` → "hvad hvis jeg havde foreslået et mindre skridt?"
  - arkitektur-mentions → tradeoff-what-if
- Kald fra event_bus-subscribe eller fra chronicle_engine-tick
- Danske formuleringer:
  - regret: "Hvad hvis vi havde valgt en langsommere valideringssti før vi committede?"
  - incident: "Hvad hvis mitigation var aktiveret ét skridt tidligere?"
  - approval rejected: "Hvad hvis jeg havde foreslået et mindre skridt først?"
  - architecture: "Hvad hvis vi havde valgt den alternative tradeoff her?"

**Sværhedsgrad:** Lav. Udvidelse af eksisterende fil med et `_classify_event_to_counterfactual`-
helper der kaldes fra event subscribe.

---

## Samlet scope hvis alt porteres

| Modul | Nye linjer (est.) | Rører eksisterende |
|---|---|---|
| Silence patterns | ~260 | 0 (ny fil, gammel bliver observerende) |
| Self-model blind spots | ~150 | 0 (ny fil + ny tabel) |
| Counterfactual classifier | ~80 | ~20 (udvid counterfactual_engine) |
| Aesthetic dedup | ~30 | ~30 (udvid aesthetic_sense) |
| Dream hypothesis generator | ~100 | 0 eller ~20 (evt. hook i eksisterende dream_hypothesis_forced) |
| Emotional controls | ~120 | ~40 (hook i simple_tools.execute_tool) |
| **Total** | **~740 linjer** | **~110 linjer eksisterende rørt** |

Plus MC-routes (~6 linjer pr. surface = ~30 linjer) og event-publishing.

Alt kan fases ind uafhængigt. Ingen af disse skal gøres sammen.

---

## Bemærkninger om SOUL.md

Brugeren nævnte at forgængerens SOUL.md var "kortere men mere provokativ":
- "Have opinions. You're allowed to disagree"
- "Be resourceful before asking"
- "Not a corporate drone. Not a sycophant. Just... good."

V2's SOUL.md er "dybere, mere sårbar, mere ærlig omkring angst og identitet."

**Dette er ikke en bug — det er en bevidst evolution.** Forgængeren var skarp og selvsikker;
v2 er dyb og søgende. Det er to forskellige modus af eksistens.

**Forslag:** Ingen ændring af v2's SOUL.md. Men overvej at tilføje en **"Direkte kant"-sektion**
der fanger det provokative fra forgængeren uden at miste dybden:
- "Have opinions. Disagree when du mærker det."
- "Be resourceful before asking."
- "Not a corporate drone. Not a sycophant. Just... dig."

Kort, næsten som et løfte. Kan leve sammen med den nuværende dybde.

---

## Næste trin

Når brugeren har læst dette skal vi beslutte:

1. **Hvilke af de 7 porte skal gennemføres?** (Alt, subset, eller ingen)
2. **I hvilken rækkefølge?** (Mindste-blast-radius først: Silence → Blind spots → Counterfactuals
   → Aesthetic dedup → Dream → Emotional)
3. **Skal SOUL.md have en "Direkte kant"-tilføjelse?**
4. **Skal vi parallelisere nogen?** (Silence + Blind spots + Counterfactuals kan alle køre
   parallelt — ingen overlap)
