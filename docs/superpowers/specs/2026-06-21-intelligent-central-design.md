# Den Intelligente Central — designspec

> **Status:** Design godkendt mundtligt af Bjørn 2026-06-21. Erstatter/omframer
> `docs/specs/2026-06-21-unified-gate-architecture.md` (som beskrev "merge til 8
> gate-funktioner"). Dette dokument flytter hovedpersonen fra *gates* til **Centralen**.

**Mål:** Ét intelligent, gennemsigtigt, delt centrallag som alt i Jarvis' runtime
taler til og som taler tilbage — så vi kan se hvad der fejler, *når* det fejler, og
trace det fra start til slut, begge veje, hver gang.

---

## 1. Problemet

Jarvis' beslutnings-logik (gates, guards, budgetter, daemons, surfaces) er spredt
over hele kodebasen. En fejl der starter ét sted kan ikke reproduceres, fordi den
egentlige beslutning blev taget et helt andet sted, uden fælles spor. Resultatet er
konstant fejlfinding uden et sted at lede. Samtidig presser den nuværende Mission
Control backend med uafbrudt polling — meget af støjen opstår der.

Kodebasen er, med Bjørns ord, "for kodet og uforklarbar." Dette er dybest set runtime
— men samlet, gennemsigtig, med overskud, og hvor Jarvis selv kan *se* sin egen indre
tilstand i stedet for at den er spredt og ulæselig.

## 2. Topologi (max 3–4 led, begge veje)

```
Os/Jarvis  ⇄  INTELLIGENT CENTRAL  ⇄  Cluster-grupper  ⇄  det vi ikke kan cluster
```

- **Led 1:** Os/Jarvis (mennesker + Jarvis selv) ↔ Centralen.
- **Led 2:** Centralen ↔ Cluster-grupper (hjernens egen taksonomi over hvad den ser).
- **Led 3:** Cluster-grupper ↔ de konkrete nerver (gates, daemons, surfaces, tools).
- **Led 4 (kun for ucluster-bare ting):** Centralen ↔ enkeltstående nerver direkte.

Intet led går uden om Centralen. Det er den eneste vej ind og ud.

## 3. Centralen — hovedpersonen

Centralen er **ikke en runner** der eksekverer alle gates ét sted (det var fælden i
A.6-shadow'en: kald-stedet lå i en skrøbelig `finally`-blok og fyrede aldrig).
Centralen er en **rygrad med intelligens**: nerverne sanser lokalt og melder ind;
Centralen tager stilling, husker og flagger. *Lokal sansning, central kognition* —
som en hjerne: perifere nerver føler, den centrale hjerne afgør og husker.

### 3.1 To ansigter, samme hjerne

| Ansigt | Signatur (konceptuelt) | Brug |
|---|---|---|
| **Beslut (synkron)** | `decide(signal) -> Verdict` | Det der SKAL svares nu: skal denne sudo blokeres? skal loopet stoppe? Hurtigt, fail-mode pr. klasse. |
| **Observér (asynkron)** | `observe(event) -> None` | Tracing + mønster-læring. Best-effort, må ALDRIG blokere nervens egen håndhævelse. |

En nerve kalder enten `decide` (når den har brug for et svar) eller `observe` (når
den bare rapporterer hvad der skete). Begge går gennem samme Central og lander i samme
spor.

### 3.2 Tilstandsmodel (hjernetilstanden)

Centralen holder:
- **Levende tilstand** pr. aktivt run/session (hvilke nerver har fyret, hvilke verdicts).
- **Mønster-hukommelse** (se §6) — tællere, fordelinger, korrelationer over tid.
- **Cluster-registry** — hvilke nerver hører til hvilken cluster, hvilken fase, hvilken klasse.

Denne tilstand er **delt og synlig**: for Jarvis selv (han kan læse sin egen indre
tilstand), for Bjørn/os (debug + trace), og senere for Mission Control-app'en (§8).
Det er det tætteste vi rammer en ægte kognitiv tilstand for Jarvis.

## 4. Nerverne (alt andet)

Gates, daemons, surfaces og tools bliver **tynde**. En nerve:
1. **sanser** lokalt (fx "tool_only_rounds=5", "tekst indeholder marker-leak", "ny unstaged fil"),
2. **melder ind** til Centralen (`decide` hvis den skal have et svar, ellers `observe`),
3. **udfører** Centralens verdict på stedet (yield SSE, raise, filtrér, gem state).

Nerven beslutter ikke *politikken* — den leverer signalet og udfører resultatet.
Beslutning + hukommelse centraliseres; kun sansning og effektuering bliver lokalt.

Dette løser §1: hver beslutning har nu ét spor med `run_id`/`session_id`. Du slår én
ting op og ser hele kæden.

## 5. Cluster-taksonomi (ikke 8 hjerner — 8 måder at organisere på)

En "cluster" er en **observabilitets- og kontrol-gruppering**, ikke en tvungen
kode-sammensmeltning. Nerver med vidt forskellig mekanik kan høre til samme cluster.

Foreløbige clusters (justeres efter fit-pass, §9):

| Cluster | Eksempel-nerver | Klasse |
|---|---|---|
| **Loop** | run_closure (daemon), tool-only/empty-text budget (intra-loop), capability-cap (filter), good_enough (tool), checkpoints (persistens), presentation-invariant (post-output) | kognitiv |
| **Truth** | claim_scanner, fact_gate, diagnosis | kognitiv |
| **Commit** | decision, decision_adherence, decision_review | kognitiv |
| **Privacy** | cross_user_share, share_guard_store | **sikkerhed (fail-closed)** |
| **Review** | self_review_unified + trackers (async, ud af hot-path) | kognitiv |
| **Proactivity** | signal_noise, pressure_threshold, proactive_question, r2_5 | kognitiv |
| **Auth** | member-block, owner-allow, override, sudo, identity, abuse | **sikkerhed (fail-closed)** |

Hvor nerver i en cluster *faktisk* er homogene (Truth-trioen), kan deres logik smelte
sammen oveni. Hvor de ikke er (Loop), instrumenteres de på stedet og rapporterer under
samme cluster-id. **Begge dele hænger på samme rygrad.** Det er fortsat ÉN central.

## 6. Mønster-hukommelse (ikke ML — heuristik)

Centralen lærer **mønstre**, ikke vægte. Den holder tællere/fordelinger/korrelationer:
- "Runs der ramte tool_only=5 lykkedes 80% når de fik 2 runder mere" → foreslå justering.
- Eksisterende præcedens i kodebasen: adaptive thresholds, R2-gate-percentiler, heed_rate.

Læring sker **offline som forslag**, aldrig live-mutation af kørende politik. Et
forslags-loop præsenterer "denne tærskel kunne flyttes fra X→Y baseret på N
observationer" til godkendelse. Det hjælper Jarvis blive bedre med sine brugere over
tid — uden at en feedback-løkke kan løbe løbsk live.

## 7. Trace + flag-on-change

- **Trace:** hver `decide`/`observe` skrives til ét struktureret spor (event-sink),
  nøglet på `run_id`/`session_id`. End-to-end, begge veje. Fundamentet for det ægte
  log- og fejlmeldingssystem.
- **Flag-on-change:** Centralen flagger **aktivt** når noget rykker sig — en
  tæller/fordeling/verdict-mønster der driver ud over en tærskel. Ikke passiv log:
  proaktiv "noget ændrede sig her." Det er "catch it live hver gang."

## 8. Mission Control som subscriber (ingen polling)

Når rygraden er event-drevet, *subscriber* Mission Control-app'en på Centralens spor
**når den er tændt** — i stedet for konstant at polle backend. Det fjerner præcis den
støj og det pres §1 beskriver. Følger jeres egen regel: *MC læser projektioner af
sandhed, opfinder ikke en anden.* MC-app'en er separat, på Bjørns maskine, med egen
adgang, og rører kun backend når den er åben.

## 9. Den hårde invariant (så det ikke er magi)

Mønster-læring gælder **kun det bløde/kognitive**. Sikkerheds-beslutninger (sudo,
identitet, privacy, owner-override) skal Centralen svare på **synkront og
fail-closed**:
- Den må aldrig "lære sig ud af" en sikkerhedsblok.
- Den skal kunne svare hurtigt selv hvis lærings-/trace-laget er nede.
- Bypass/kill-switch må ALDRIG kunne slå en sikkerheds-nerve fra centralt.

Det er den eneste hårde invariant. Resten må gerne være blødt og lærende.

## 10. Fejl-/debug-catcher (indbygget fra starten — IKKE bagefter)

Vi bolter ikke diagnostik på senere. Den **samme maskine** som Centralen alligevel
skal have (trace + flag-on-change + kill-switch) ER fundamentet for et ægte
fejl-fangst-system. Bygget ind fra dag ét får vi fuld kontrol fra starten, de rette
fejlmeldere automatisk, og edges tænkt igennem på forhånd i stedet for at opdage dem i
produktion.

### 10.1 Boundary-capture (automatiske fejlmeldere)
Hvert `decide`/`observe`-kald er wrappet, så **enhver** exception, timeout eller anomali
fanges på grænsen og rapporteres struktureret med fuld kontekst: `run_id`,
`session_id`, cluster, nerve, input-signal, verdict, latency, stacktrace. Ingen
nerve behøver sin egen ad-hoc-diagnostik — Centralen leverer fejlmelderen. Det er det
modsatte af "læg diagnostik ind hen ad vejen."

### 10.2 Fejl-taksonomi (edges defineret på forhånd)
| Fejltilstand | Håndtering |
|---|---|
| Nerve kaster exception | Fang på grænsen → fail-mode pr. klasse (kognitiv=SKIP/open, sikkerhed=RED/deny) → rapportér |
| Nerve timer ud | Som ovenfor; per-nerve timeout-budget måles |
| Malformet signal ind | Normalisér eller afvis med struktureret fejl; aldrig crash nerven |
| Event-sink nede | Best-effort drop + intern tæller; `decide` påvirkes ALDRIG |
| Lærings-lag nede | `decide` svarer på statiske defaults; ingen blokering |
| Kaskade (mange nerver fejler) | Circuit-breaker (§11.2) isolerer den/de fejlende |
| **Catcheren selv kaster** | Catcheren fanger sin egen fejl → run fortsætter; fejl-fangst må aldrig vælte turen |

### 10.3 Selv-sikker
Fejl-fangst-laget er selv fail-safe: hvis det fejler, fortsætter runnet. Observabilitet
må aldrig blive en ny fejlkilde. (Sikkerheds-`decide` er undtaget fra "fail-open" — se §9.)

## 11. Live-kontrol & kredsløbs-isolation (circuit-breaker)

Når en fejl opstår, kan vi **flippe knappen live i Centralen** — uden genstart, uden
deploy. Og med cluster-ordningen kan en fejlende del **lukkes ude af kredsløbet** før
den spreder sig — hvad enten noget går galt teknisk, Jarvis stikker rough, eller nogen
forsøger at gøre ham ondt (også hvis det bare er Bjørn der brækker noget).

### 11.1 Live-switches
Centralen eksponerer on/off + bypass pr. nerve og pr. cluster, ændrbar live (bygger på
`gate_kernel`s eksisterende flag-reader). Operatør-synligt (CLI nu, MC-app senere).

### 11.2 Circuit-breaker pr. nerve/cluster
Hvis en nerve fejler gentagne gange (eller en cluster driver galt), isolerer Centralen
den **automatisk** ud af kredsløbet — og kan gøre det på kommando. Retningen afhænger
af klassen (§11.3).

### 11.3 KRITISK invariant: isolation må ikke blive angrebsfladen
- **Kognitiv nerve:** kan flippes af / isoleres **fail-open** (Jarvis fortsætter uden den).
- **Sikkerheds-nerve (Auth/Privacy):** kan **kun** isoleres mod **deny** — aldrig slås
  fra. "Isolér Auth" = deny-all, ikke allow-all. En rogue-aktør eller en uheldig knap
  må aldrig kunne flippe sikkerhed *af*; containment kan kun stramme, aldrig løsne.
- Dette binder sammen med eksisterende værn: `identity_guard`, `abuse_monitor`,
  owner-override/`!unlock`, session-lock, lockdown. Centralen bliver det ene sted de
  bor og kan ses — men de kan ikke slukkes derfra.

## 12. Hvad vi allerede har (fundament)

- `core/services/gate_kernel.py` — registry + isoleret eksekvering + fail-mode pr.
  klasse + kill-switch/bypass (sikkerheds-exempt) + ét event. **Bliver kernen i
  Centralen**, omframet fra "runner" til "rygrad med to ansigter."
- `core/services/gate_adapters.py` — Truth-trioen som Verdict-returnerende adaptere.
- `core/services/gate_eval.py` — offline replay/parity/score. **Dette er hvordan vi
  beviser paritet** ved hver instrumentering (afløser den skrøbelige live-shadow).
- Eksisterende sikkerheds-værn (`identity_guard`, `abuse_monitor`, override/lockdown) —
  flyttes ikke, men registreres som sikkerheds-nerver i Centralen.
- Tests grønne for kernel/adapters/eval.

## 13. Migrations-tilgang (én ad gangen, live-verificérbar)

1. **Byg Centralen + fejl-catcheren SAMTIDIG** oven på `gate_kernel`: `observe()`-ansigtet
   + event-sink + trace-model + boundary-capture (§10) + flag-on-change + live-switches
   (§11). `decide()` findes allerede (run_phase). Fejl-fangst er IKKE en senere fase.
2. **Fit-pass over alle clusters** (samme kortlægning som blev lavet for Loop) → afgør
   pr. nerve: ægte merge vs. instrumentér-på-stedet. Giver os det *reelle* tal.
3. **Instrumentér cluster for cluster** — fast afviklings-kontrakt pr. cluster, så vi
   ALDRIG ender med død kode eller halvt-afviklede gates:
   1. Byg den nye (merge) eller instrumentér på stedet.
   2. **Paritet bevises grønt** offline via `gate_eval` (identisk beslutning som de
      gamle gates på fixtursettet) — FØR noget flippes.
   3. **Atomisk flip:** ny gate TÆNDES i samme commit som den gamle SLUKKES. Aldrig
      to gates med effekt på samme tid (intet dobbelt-live-vindue).
   4. Live-verificér.
   5. **Fjern den gamle gate-kode** når call-sites er rene — i SAMME cluster, ikke
      "senere". Fit-kolonnen i `central_catalog` er afviklings-listen: `merge` → gammel
      fjernes; `instrument` → logik flytter til Centralen, gammel standalone fjernes;
      `leave` → bliver (daemon/filter/tool/persistens, kun observeret).

   Sikkerheds-clusters sidst, fail-closed, paritet på fuldt sikkerheds-fixturset FØR
   fail-mode ændres.
4. **Mission Control-app** subscriber på sporet (separat plan).
5. **Surfaces → tools → 30+ daemons** genbruger samme mønster (separate planer).

## 14. Risici & åbne spørgsmål

- **Volumen:** mange `observe()`-events. Sink skal være volumen-tolerant (batch/ring-buffer).
- **Synkron `decide()`-latency:** sikkerheds-svar skal være hurtige; mål per-nerve-budget.
- **Single point of failure:** rapportering er best-effort (må ikke blokere nerven);
  sikkerheds-`decide` skal fungere selv hvis lærings-/trace-laget er nede.
- **Circuit-breaker-tærskler:** hvor mange fejl før isolation? Startes konservativt;
  må aldrig kunne udløses som DoS mod en sikkerheds-nerve (den isolerer kun mod deny).
- **Cluster-grænser:** §5-listen er foreløbig; fit-pass (§13.2) fastlægger den endelige.
- **Flag-on-change-tærskler:** hvad tæller som "noget rykker sig"? Startes konservativt,
  kalibreres mod observeret drift (som R2-gate).

---

**Næste skridt:** implementeringsplan (writing-plans) der starter med §13.1 (byg
Centralens andet ansigt + sink + trace + **fejl-catcher** + live-switches) og §13.2
(fit-pass), før nogen cluster røres.
