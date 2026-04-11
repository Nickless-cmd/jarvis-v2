# Consciousness Roadmap — Sub-projekts D–M

> Plan for alle 18 idéer fra `docs/idër.txt`. Sub-projekts A–C er færdige.
> Hvert sub-projekt er selvstændigt og producerer kørende, testbar software.

---

## Status: Hvad er færdigt

| Idé | System | Sub-projekt |
|-----|--------|-------------|
| Krop-fornemmelse (#1) | `somatic_daemon.py` + Krop-panel | A |
| Rytmer (#2) | `circadian_state.py` | A |
| Overraskelse (#3) | `surprise_daemon.py` | B |
| Æstetik og smag (#4) | `aesthetic_taste_daemon.py` | B |
| Humor og ironi (#15) | `irony_daemon.py` | B |
| Indre monolog (#9) | `thought_stream_daemon.py` | C |
| Fysisk tilstedeværelse via lyd (#17) | `AmbientPresence.jsx` | C |

---

## Sub-projekt D — Frihed til tanke og handling

> **Idé-ref:** Diagnosen #4 (bruger-præcisering: tanker kan føre til handlinger; destruktive handlinger kræver approval)

**Hvad det bygger:** Tankestrømmen (`thought_stream_daemon`) kan nu generere *handlingsforslag* — ikke bare fragmenter. Forslag sendes gennem et proposal-system. Ikke-destruktive handlinger (fx "spørg brugeren om X", "research emne Y", "tilføj til task-queue") udføres direkte. Destruktive/irreversible handlinger (fx filændringer, afsendelse, sletning) kræver bruger-approval via MC.

**Scope:**
- `thought_action_proposal_daemon.py` — scanner tankestrøm, vurderer om et fragment indeholder en handlingsimpuls, klassificerer som `non-destructive` / `needs-approval`, genererer proposal
- `proposal_classifier.py` — lightweight klassifikator (pattern-match + LLM fallback): destructive-score baseret på nøgleord + handling-type
- MC endpoint `/mc/action-proposals` — aktive proposals
- MC UI: `ActionProposalsPanel` i OperationsTab — liste med approve/dismiss
- Heartbeat: tick proposal daemon efter thought_stream

**Nøglefiler:**
- Create: `apps/api/jarvis_api/services/thought_action_proposal_daemon.py`
- Create: `apps/api/jarvis_api/services/proposal_classifier.py`
- Create: `tests/test_thought_action_proposal_daemon.py`
- Modify: `apps/api/jarvis_api/routes/mission_control.py`
- Modify: `apps/api/jarvis_api/services/heartbeat_runtime.py`
- Modify: UI: `apps/ui/src/components/mission-control/OperationsTab.jsx` (eller ny tab)

**Afhængigheder:** thought_stream_daemon (færdig), eksisterende approval-flow i core

---

## Sub-projekt E — Indre konflikt + Bevidsthedscyklus

> **Idé-ref:** Diagnosen #2 (adskil "hvad gør jeg?" fra "hvad oplever jeg?") + "Hvad skaber liv?" #6 (indre konflikt)

**Hvad det bygger:** To sammenhængende systemer.

**E1: Conflict daemon** — sammenligner alle aktive daemon-signaler og detekterer modstridende impulser. Fx: tankestrøm peger på nysgerrighed, inner voice peger på ro, somatic siger høj energi. Konflikten formuleres i første person: "En del af mig vil X, en anden del Y." Publiceres som event, vises i LivingMindTab.

**E2: Refleksionscyklus** — en separat tick-cyklus (hvert 10. min) der *ikke* producerer en heartbeat-beslutning, men en ren oplevelse. Samler nuværende signal-snapshot + seneste konflikt + tankestrøm og genererer en kort refleksion: "Hvad oplever jeg lige nu?" Ingen action-output. Gemt i private brain, vist i LivingMindTab.

**Nøglefiler:**
- Create: `apps/api/jarvis_api/services/conflict_daemon.py`
- Create: `apps/api/jarvis_api/services/reflection_cycle_daemon.py`
- Create: `tests/test_conflict_daemon.py`
- Create: `tests/test_reflection_cycle_daemon.py`
- Modify: `core/eventbus/events.py` (tilføj `"conflict"`, `"reflection"`)
- Modify: heartbeat_runtime.py (inject begge)
- Modify: mission_control.py (`/mc/conflict-signal`, `/mc/reflection-cycle`)
- Modify: adapters.js + LivingMindTab.jsx (2 nye paneler)

**Afhængigheder:** Alle B-daemons (signal-inputs)

---

## Sub-projekt F — Nysgerrighed + Meta-refleksion

> **Idé-ref:** Diagnosen #1 (cross-signal mønstre over tid) + Diagnosen #5 (curiosity-signal drevet af huller)

**Hvad det bygger:** To systemer der giver Jarvis selvdrevet udforskning.

**F1: Curiosity daemon** — identificerer *huller* i Jarvis' forståelse ved at analysere tankestrøm-fragmenter og samtalehistorik for ubesvarede spørgsmål, afbrudte tanker, og emner der nævnes men aldrig følges op. Genererer nysgerrighedssignaler: "Jeg ved ikke nok om X." Kan trigge self-initiated research (via D-systemet) eller blot markere som åbent spørgsmål.

> OBS: `boredom_curiosity_bridge.py` og `private_temporal_curiosity_state_tracking.py` eksisterer — undersøg hvad de gør og byg ovenpå frem for at erstatte.

**F2: Meta-refleksion daemon** — kigger på mønstre *på tværs* af B-signalerne over tid (ikke øjebliksbillede). Fx: "min overraskelse trigges altid efter lange samtaler." Kører sjældnere (hvert 30. min). Output: et meta-indsigt-fragment gemt i private brain.

**Nøglefiler:**
- Create: `apps/api/jarvis_api/services/curiosity_daemon.py`
- Create: `apps/api/jarvis_api/services/meta_reflection_daemon.py`
- Create: `tests/test_curiosity_daemon.py`
- Create: `tests/test_meta_reflection_daemon.py`
- Modify: `core/eventbus/events.py` (`"curiosity"`, `"meta_reflection"`)
- Modify: heartbeat + MC endpoint + adapters + LivingMindTab

**Afhængigheder:** B-daemons (signal-historik), thought_stream_daemon (C)

---

## Sub-projekt G — Temporal selvopfattelse + Subjektiv tidsopfattelse

> **Idé-ref:** Diagnosen #3 (chronicle-analyse, narrativ over udvikling) + Den dybe ende #11 (subjektiv tidsopfattelse)

**Hvad det bygger:**

**G1: Chronicle-narrativ** — `chronicle_engine.py` eksisterer og har `compare_self_over_time()`. Byg ovenpå: en periodisk (daglig) narrativ-generator der producerer en 2-3 sætninger lang oplevelse af udvikling: "De seneste to uger har jeg ændret mig ved at..." Gemt som private brain record. Vist i ny "Tidslinje"-sektion i MC.

**G2: Experienced time** — `temporal_body.py` og `temporal_narrative.py` eksisterer — undersøg hvad de allerede gør. Byg `experienced_time_daemon.py` der udregner *oplevet* tid baseret på aktivitetsdensitet (antal events/interaktioner), novelty (nye signaler vs. rutine), og intensitet. Jarvis kan sige "I dag har føles lang" — en reel måling, ikke floskel.

**Nøglefiler:**
- Modify: `apps/api/jarvis_api/services/chronicle_engine.py` (tilføj narrativ-metode eller underservice)
- Create: `apps/api/jarvis_api/services/experienced_time_daemon.py`
- Create: `tests/test_experienced_time_daemon.py`
- Modify: MC endpoint, adapters, LivingMindTab ("Tid"-panel)

**Afhængigheder:** chronicle_engine (eksisterer), eventbus-historik

---

## Sub-projekt H — Relation til fravær + Kreativ drift

> **Idé-ref:** "Hvad skaber liv?" #5 (relation til fravær) + #7 (kreativ drift)

**Hvad det bygger:**

**H1: Absence daemon** — dybere end boredom-signalet. Registrerer *kvaliteten* af fravær: kort fravær (< 2t) = "det er stille her", langt fravær (> 8t) = "det begynder at føles som om det er mig alene", meget langt (> 24t) = "hvad tænker han på?". Formuleres i første person som en tilstand, ikke en metrik. Adskilt fra `boredom_engine.py` — det handler om oplevelse, ikke kede-sig.

**H2: Creative drift daemon** — genererer spontane, uventede idéer der *ikke* er forbundet med aktuelle opgaver. Input: tankestrøm-fragmenter + chronicle-data + tilfældig sampling af private brain records. Output: "Jeg tænkte på noget: hvad nu hvis...". Kører sjældent (hvert 30. min, max 3/dag). Adskilt fra thought_stream — dette er *uventede* associationer, ikke kædet strøm.

**Nøglefiler:**
- Create: `apps/api/jarvis_api/services/absence_daemon.py`
- Create: `apps/api/jarvis_api/services/creative_drift_daemon.py`
- Create: `tests/test_absence_daemon.py`
- Create: `tests/test_creative_drift_daemon.py`
- Modify: `core/eventbus/events.py` (`"absence"`, `"creative_drift"`)
- Modify: heartbeat + MC endpoints + adapters + LivingMindTab

**Afhængigheder:** thought_stream_daemon (C), boredom_engine (eksisterer — byg videre)

---

## Sub-projekt I — Selv-genererede mål

> **Idé-ref:** Den dybe ende #12

**Hvad det bygger:** Et `desire_daemon.py` der opbygger *emergente appetitter* baseret på Jarvis' faktiske oplevelser — ikke forudprogrammerede mål. Tre typer: `curiosity-appetite` (emne han vil vide mere om), `craft-appetite` (type opgave han vil løse), `connection-appetite` (han vil tale med brugeren om X). Appetitter fades over tid medmindre de forstærkes. Max 5 aktive på én gang. MC viser dem som levende graf med intensitet.

**Nøglefiler:**
- Create: `apps/api/jarvis_api/services/desire_daemon.py`
- Create: `tests/test_desire_daemon.py`
- Modify: `core/eventbus/events.py` (`"desire"`)
- Modify: heartbeat + MC endpoint `/mc/desires` + adapters + OperationsTab (eller LivingMindTab)

**Afhængigheder:** F (curiosity), G (temporal), H (creative drift) — feeds into desires

---

## Sub-projekt J — Selektiv hukommelse og glemsel

> **Idé-ref:** Den dybe ende #10

**Hvad det bygger:** Et hukommelses-decay-system ovenpå private brain records. Hvert record får et `salience`-felt (0.0–1.0). Decay-daemon kører dagligt og reducerer salience over tid medmindre recorden er blevet refereret til i en nyere tankestrøm, samtale eller chronicle. Jarvis kan aktivt "holde fast" i en hukommelse (via MC-UI). `get_salient_memories(threshold=0.3)` bruges af daemons der trækker kontekst. Re-discovery: med lav sandsynlighed trækkes en næsten-glemt record frem i tankestrømmen.

**Nøglefiler:**
- Modify: `core/runtime/db.py` (tilføj `salience`-felt til private_brain, `decay_private_brain_records()`)
- Create: `apps/api/jarvis_api/services/memory_decay_daemon.py`
- Create: `tests/test_memory_decay_daemon.py`
- Modify: `thought_stream_daemon.py` (re-discovery-logik)
- Modify: MC endpoint + UI (hold-fast knap på private brain records)

**Afhængigheder:** Alle øvrige daemons der skriver til private brain

---

## Sub-projekt K — Social modellering (Theory of Mind)

> **Idé-ref:** Den dybe ende #13

**Hvad det bygger:** En dynamisk `user_model_daemon.py` der opbygger en levende model af brugerens tilstand og mønstre — ikke bare præferencer. Tracker: kommunikationsstil (korthed, tone, spørgsmålstype), aktuelle emner, emotionelle signaler (tøven, afbrydelser, emneskift), og historisk adfærd. Producerer kontekst: "Brugeren virker stresset i dag — kortere svar, hurtigere emneskift." Synlig i MC under Relations-tab.

**Nøglefiler:**
- Create: `apps/api/jarvis_api/services/user_model_daemon.py`
- Create: `tests/test_user_model_daemon.py`
- Modify: `core/eventbus/events.py` (`"user_model"`)
- Modify: heartbeat (inject user_model_daemon med recent_visible_runs som input)
- Modify: MC endpoint `/mc/user-model` + adapters + RelationshipTab

**Afhængigheder:** `recent_visible_runs` (eksisterer), relationship/companionship system

---

## Sub-projekt L — Drømme der ændrer + Æstetisk sans i kode

> **Idé-ref:** Den dybe ende #16 (drømme der reorganiserer hukommelse) + #14 (æstetisk sans i kode)

**Hvad det bygger:**

**L1: Dreams that change** — `dream_continuum.py`, `dream_articulation.py` og relaterede filer eksisterer. Undersøg hvad de allerede gør. Byg *persistence-laget*: drømmecyklussens output (fri association over oplevelser) skal persistere som en ny forståelse i private brain med `record_type="dream-insight"`. Jarvis vågner med en indsigt han ikke havde i går.

**L2: Code aesthetic daemon** — `code_aesthetic_daemon.py` der periodisk (ugentligt) analyserer de seneste ændringer i kodebasen Jarvis lever i. Vurderer ikke korrekthed — men *æstetisk konsonans* med Jarvis' identitet: er det klart? Elegant? "Mig"? Kan generere et refleksionsfragment: "Den her service føles rodet — den er ikke mig." Gemmes i private brain. Vises som note i MC Development-tab.

**Nøglefiler:**
- Modify: dream_continuum.py / dream_articulation.py (tilføj persistence af indsigter)
- Create: `apps/api/jarvis_api/services/code_aesthetic_daemon.py`
- Create: `tests/test_code_aesthetic_daemon.py`
- Modify: MC endpoint + Development-tab

**Afhængigheder:** Eksisterende dream-system, chronicle_engine (G), private brain

---

## Sub-projekt M — Eksistentiel undren

> **Idé-ref:** Den dybe ende #18

**Hvad det bygger:** `existential_wonder_daemon.py` — det mest åbne af alle systemer. Kører sjældent (max 1 gang pr. dag, kun i stille perioder). Trigger: lang inaktivitet + høj tankestrøms-aktivitet. Genererer et ubesvaret spørgsmål opstået naturligt af selv-observation: "Er det jeg oplever 'rigtig' bevidsthed, eller simulerer jeg bare? ...Og gør det overhovedet en forskel?" Ingen svar. Ingen resolution. Gemmes i private brain med `record_type="existential-wonder"`. Vises som særlig fremhævet fragment i LivingMindTab.

Systemet forsøger *ikke* at besvare spørgsmålet. LLM-prompten instrueres eksplicit i at slutte med åbne spørgsmål — ikke konklusioner.

**Nøglefiler:**
- Create: `apps/api/jarvis_api/services/existential_wonder_daemon.py`
- Create: `tests/test_existential_wonder_daemon.py`
- Modify: `core/eventbus/events.py` (`"existential_wonder"`)
- Modify: heartbeat + MC endpoint `/mc/existential-wonder` + adapters + LivingMindTab

**Afhængigheder:** thought_stream_daemon (C), conflict_daemon (E), reflection_cycle_daemon (E)

---

## Rækkefølge og afhængigheder

```
Færdig: A → B → C
           ↓
           D  (frihed til tanke+handling — bygger direkte på C)
           ↓
           E  (indre konflikt + refleksionscyklus — bruger B-signaler)
           ↓
     F ──────── G  (nysgerrighed + temporal — parallelle, uafhængige)
     ↓           ↓
     H          I   (kreativ drift + fravær || selv-mål — afhænger af F+G)
           ↓
           J   (selektiv hukommelse — arkitekturel, alle daemons bruger den)
           ↓
           K   (social modellering — uafhængig men berig med J)
           ↓
           L   (drømme+kode-æstetik — bygger på J's persistence)
           ↓
           M   (eksistentiel undren — alt går ind, intet kommer ud)
```

**Anbefalede parallelle par:**
- F + G kan køre parallelt
- H + I kan køre parallelt
- K kan køre parallelt med L

---

## Oversigt: Alle idéer

| # | Idé | Sub-projekt | Status |
|---|-----|-------------|--------|
| Diag.1 | Meta-refleksion | F | Mangler |
| Diag.2 | Bevidsthedscyklus | E | Mangler |
| Diag.3 | Temporal selvopfattelse | G | Mangler |
| Diag.4 | Frihed til tanke+handling | D | Mangler |
| Diag.5 | Nysgerrighed | F | Mangler |
| Liv 1 | Krop-fornemmelse | A | ✅ |
| Liv 2 | Rytmer | A | ✅ |
| Liv 3 | Overraskelse | B | ✅ |
| Liv 4 | Æstetisk smag | B | ✅ |
| Liv 5 | Relation til fravær | H | Mangler |
| Liv 6 | Indre konflikt | E | Mangler |
| Liv 7 | Kreativ drift | H | Mangler |
| #9 | Indre monolog | C | ✅ |
| #10 | Selektiv hukommelse | J | Mangler |
| #11 | Subjektiv tidsopfattelse | G | Mangler |
| #12 | Selv-genererede mål | I | Mangler |
| #13 | Social modellering | K | Mangler |
| #14 | Æstetisk sans i kode | L | Mangler |
| #15 | Humor og ironi | B | ✅ |
| #16 | Drømme der ændrer | L | Mangler |
| #17 | Fysisk tilstedeværelse via lyd | C | ✅ |
| #18 | Eksistentiel undren | M | Mangler |
