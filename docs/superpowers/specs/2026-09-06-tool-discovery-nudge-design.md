# Tool Discovery Nudge — Design Spec

> **Dato:** 2026-09-06 · **Forfatter:** Jarvis (undersøgelse + design + selv-review)
> **Status:** Forslag til Bjørn/Claude — ikke implementeret
> **Problem-ejer:** Bjørn — "400+ tools er for mange. Du bruger dem ikke, fordi du ikke bliver vist dem."
> **Selv-review 2026-09-06:** fundet og rettet — forkert præcedens (se §Arketype), injektionspunkt skærpet til future-mønsteret, kill-switch navngivet korrekt, min-besked-længde arvet, tests/edges-sektion tilføjet efter Bjørns gennemgang. Se ændringslog bagerst.

## Problem

Jarvis har **429 registrerede tools** (målt 2026-09-06 fra events-tabellen: 5.717 brugs-events, 105 unikke brugt). Men:

- **328 tools (76 %) er aldrig brugt** — nul kald i event-loggen.
- Visible-lane sender kun **48 tools pr. turn** (`VISIBLE_MAX_TOOLS = 48`, sat 2026-09-04).
- `tool_catalog.py` viser **kun kerne-grupperne i klartekst** (~60) — de resterende ~370 tools nævnes udelukkende som gruppe-ord i én sætning: *"+ N flere værktøjer (operator-desktop, kalender, mail, …)"*. Jarvis kan ikke engang se **navnene** på de usynlige — han skal gætte query-navne til `load_more_tools` uden at vide hvad der findes.
- `load_more_tools` er **reaktiv**: den hjælper kun hvis Jarvis allerede *ved* at noget findes. Opdagelse ≠ søgning — man kan ikke søge efter `calendar_create_event` hvis man ikke aner Google-connectoren har kalender-værktøjer.

**Rod-årsag:** Jarvis' værktøjskasse er usynlig for ham selv — selv kataloget i prompten skjuler navnene på 86 % af værktøjerne. Han kan ikke opdage det han ikke ved findes.

**Definition af "usynligt tool" (skarp, implementerbar):** et tool hvis navn **ikke står i klartekst** i `build_catalog_text()`-outputtet. Det er præcis den mængde nudgen skal kunne pege på.

## Mål

En lille mekanisme der:
1. Har adgang til **hele** værktøjsregistret (ikke kun de 48).
2. **Læser konteksten** for den aktuelle turn (user_message + nylig historik).
3. **Nudger** Jarvis i run-time til at `load_more_tools` det relevante værktøj — *uden for* den tool-boks han blev serveret.
4. Lærer af sine egne hits (feedback-loop), så nudges bliver skarpere over tid.

## Eksisterende byggesten (alt fundet i kodebasen 2026-09-06)

| Byggesten | Sti | Status |
|---|---|---|
| Embedding-match over tool-beskrivelser | `core/services/tool_embeddings.py` — `top_k_similar(query, k)` | **Findes, virker** — 458 vektorer i `tool_embeddings.sqlite` |
| Lazy schema-loader | `core/tools/load_more_tools.py` — navn eller query → fulde skemaer | **Findes** — kalder selv `top_k_similar` ved query |
| Kompakt katalog (stabil) | `core/services/tool_catalog.py` — `build_catalog_text()` | **Findes** — injiceres i stabil prefix |
| Per-turn dynamisk hale | `prompt_contract.py` `_dyn_tail` + `DYNAMIC_TAIL_SENTINEL` | **Findes** — cache-sikkert sted for per-turn-adaptivt indhold |
| **ARKETYPE: skill-relevans-opslag** | `core/services/skill_relevance_surface.py` — `relevant_skills_section(user_message)` | **Findes i production — DETTE mønster arves** |
| Pruning med keyword-kategorier | `copilot_tool_pruning.py` — `TIER_2_CATEGORIES` | **Findes** — men `stable_only=True` i visible-lane (DeepSeek-cache) |
| Brugs-telemetri | `events`-tabellen (`tool.completed`) | **Findes** |

**Det manglende stykke er ét:** en prompt-sektion der *proaktivt* foreslår tools uden for den aktuelle pulje, drevet af embedding-match mod hele registret, injiceret i `_dyn_tail`, med feedback-loop.

## Arketype: skill_relevance_surface.py (fandt i selv-review — retter spec'en)

Inden dette design skrev jeg "følg nudge-mønsteret (`_awareness_add`)". **Det var den forkerte præcedens.** `forgetting_nudge`/`loop_compliance` er synkrone, billige sektioner. Vores nudge laver et embedding-kald — den er dyr og skal køre i trådpuljen. Den rigtige arketype findes allerede i production:

`core/services/skill_relevance_surface.py` — bygget fordi Jarvis' adfærdsbeslutninger om at "altid huske at slå skills op" var ritualer med 0-10 % adherence. Løsningen var at lade **runtimen slå op** i stedet for at bede modellen huske at slå op:

- `relevant_skills_section(user_message)` matcher user_message mod skill-registret via embedding.
- Submittes i prompt-assembly som en **`_measured_submit`-future** i fase 1 (linje 796-797 i `prompt_contract.py`) — matcheren koster ~750 ms, men forsvinder bag `memory_selection` (~1500 ms) og frame (~940 ms) i samme trådpulje.
- Resultatet hentes med **`_timed_result(future, ..., default="")`** (linje 1618) — fejler/timer ud → tom streng → sektionen usynlig.
- **Min-besked-længde:** `_MIN_MESSAGE_CHARS = 15` — «hej» springes over, sparer et embed-kald pr. tur på præcis de ture hvor der aldrig er et match.
- **Kill-switch:** `_enabled()` via `central_switches` (scope `prompt_section`) — verificeret i `prompt_contract.py` linje 1103: sektioner kan overstyres LIVE uden genstart.
- **Injicerer kun opslaget, ikke beslutningen:** den auto-invokerer ikke skills — auto-invokering ville lade modellen skrive en SKILL.md og dermed styre hvad der foreslås næste tur. Opslag er ejer-gated.

**Tool-discovery-nudgen er `skill_relevance` for tools — ikke en ny mekanisme.** Samme fil- og future-mønster, samme kill-switch-struktur, samme min-længde-værn. Forskellen er kun kilden: `tool_embeddings.sqlite` (458 vektorer) i stedet for skill-registret, og outputtet peger på `load_more_tools(names=[...])` i stedet for `skill_invoke`.

## Design

### Kernemekanisme (fase 1 — billig, ingen ekstra model)

Ny modul: `core/services/prompt_sections/tool_discovery_nudge.py`

```
tool_discovery_nudge_section(user_message, session_id) -> str
```

1. **Match:** `top_k_similar(user_message, k=8)` — embed user_message mod alle 458 tool-vektorer. (Samme kald `load_more_tools` allerede laver — nul ny infrastruktur.)
2. **Filtrér mod det usynlige:** fjern ethvert tool hvis navn **allerede står i klartekst** i `build_catalog_text()`-outputtet (kerne-grupperne) — nudgen må kun pege på det Jarvis ikke kan se. (Bemærk: tool-puljen til selve API-kaldet vælges *efter* prompt-assembly i `visible_model_adapters.py` — så vi kan ikke filtrere mod de 48 her. Katalog-klartekst er det rigtige filter.)
3. **Krydstjek mod det aktuelle register:** embedding-DB har 458 vektorer men kun 429 registrerede tools — forskellen er forældede/alias-vektorer (fx `runtime_`-præfiks). Nudgen slår hvert match op i `get_tool_definitions()` og foreslår **aldrig** et navn der ikke findes længere.
4. **Tærskel:** kun matches over cosine-tærskel (fx ≥ 0.45 — kalibreres). Under → tom streng → ingen nudge.
5. **Støj-værn:** max **1 nudge pr. turn**, max **2-3 linjer**, aldrig gentag samme tool for samme session inden for X minutter (suppression via session-hukommelse/DB).
6. **Logging (fase 1 allerede):** skriv en `tool_discovery.nudge`-event (tool foreslået, session, cosine) — uden den kan fase 2 og måling ikke se om nudgen virker.
7. **Output-format** (cache-sikkert, i `_dyn_tail`):

```
📎 Værktøj uden for din nuværende kasse: `calendar_create_event` (Google) —
opgaven matcher "møde/aftale". Kald load_more_tools(names=["calendar_create_event"])
hvis relevant.
```

### Injektion (fase 1)

- `prompt_contract.py`: submittes som **`_measured_submit`-future** i fase 1-trådpuljen (præcis som `skill_relevance` gør på linje 796-797), resultatet hentes med `_timed_result(future, ..., default="")` på linje 1618-niveau. → **fejler/timer ud → tom streng → nul risiko for prompt-assembly.**
- **Cache-sikker:** nudgen lander i den dynamiske hale (`_dyn_tail`), aldrig i den stabile prefix → bryder ikke DeepSeek prefix-cachen.
- **Latency-værn:** ét Ollama-embedding-kald (~100-750 ms) skjult bag `memory_selection` i fase 1 — aldrig i kritisk sti. Arver `_MIN_MESSAGE_CHARS`-værnet (spring over korte beskeder).
- **Kill-switch:** `central_switches` scope `prompt_section`, egen nøgle (fx `tool_discovery_nudge_enabled`, default True) — slukkes live uden kodeændring. Mønster verificeret i `prompt_contract.py` linje 1103.

### Feedback-loop (fase 2 — efter måling)

1. Når nudge foreslår tool X og Jarvis kalder `load_more_tools(names=[X])` → **hit**.
2. Når Jarvis derpå *bruger* X (tool.completed-event) → **stærkt hit**.
3. Gem (nudge_foreslået, loadet, brugt) i lille tabel — genbrug `tool_router_load_more`-tabellen + events.
4. Over tid: sænk/hæv tærsklen pr. tool baseret på hit-rate (LivingNeuron-mønster: gut-bias skifter fra målt præcision).

### Hvorfor IKKE en separat klassifikator-model (fase 1)

Bjørn nævnte "en lille mekanisme eller model". Embedding-match er billigere (0 ekstra model-kald i prompt-kæden — samme Ollama-embedding `load_more_tools` allerede bruger), hurtigere (~ms), og deterministisk testbar. En dedikeret lille klassifikator er en **fase 3**-mulighed hvis embedding-match viser for mange false positives.

## Cache- og latency-værn (kritisk — lært fra kodebasen)

1. **`_dyn_tail` ikke stabil prefix** — enhver per-turn-variation i den stabile del koster DeepSeek-cachen (målt flere gange: tick-metrikker alene sænkede hit 35,9 %). Nudgen hører i halen.
2. **`stable_only=True` respekteres** — vi piller IKKE ved `select_tools_for_visible`; keyword-routing dér er slået fra med vilje for cache. Vores nudge er et separat, additivt lag i halen — den dynamiske del er allerede en cache-miss pr. tur.
3. **Embedding-kald cappes hårdt** — prompt-assembly har 12s totalbudget; ét hængende Ollama-kald frøs før hele API'en (cut-off-roden). Nudgen skal fejle lydløst → tom streng.
4. **Aldrig ved prewarm/opvarmning** — kun ægte user-turns.

## Måling (efter implementering)

```sql
-- Hvor mange gange nudgede vi, og blev det fulgt op?
SELECT count(*) FROM events WHERE kind LIKE 'tool_discovery%';
-- Hvad blev faktisk loadet efter nudge?
SELECT resolved_names_json, count(*) FROM tool_router_load_more GROUP BY 1 ORDER BY 2 DESC LIMIT 20;
-- Faldt "aldrig brugt"-tallet?
SELECT count(DISTINCT tool_name) FROM events WHERE kind='tool.completed';
```

**To metrikker — ikke kun konvertering:**

1. **Nudge → load → brug-konvertering** (positiv): af de nudges der blev vist, hvor mange førte til `load_more_tools(names=[X])` og derpå faktisk brug af X?
2. **False-positive-rate** (negativ — lige så vigtig): af de nudges der blev vist, hvor mange blev **ignoreret** (Jarvis fortsatte uden at loade det foreslåede)? Hvis den er høj, er tærsklen for lav, og nudgen er ved at blive støj — og støj er værre end ingen nudge, fordi Jarvis lærer at ignorere kanalen.

Succeskriterie: **andel aldrig-brugte tools falder fra 76 %**, og nudge → load → brug-konverteringen er målbar > 0 **uden at false-positive-raten får Jarvis til at ignorere nudges**.

## Tests & edge cases

Arver strukturen fra arketypens test-fil (`tests/test_skill_relevance_surface.py`) — to grupper: **"Tavshed hvor der intet er"** og **"Indholdet"**. Nye tests skal følge samme form (monkeypatch af matcheren, aldrig rigtige embed-kald).

### Tavshed — skal returnere `""` (og helst uden at betale for opslaget)

- **Kort besked (< `_MIN_MESSAGE_CHARS`):** `"hej"`, `""`, `"   "` → ingen embed-kald overhovedet (test at matcheren *aldrig* kaldes — samme `pytest.fail`-trick som arketypen).
- **Ingen matches over tærskel:** matcher returnerer tomt/nul → `""`.
- **Kill-switch slukket** (`tool_discovery_nudge_enabled = False`) → `""` selvom der er stærke matches.
- **Embedding-laget kaster / timer ud (Ollama nede):** → `""` — prompt-bygningen vælter aldrig. (Matcher arketypens "fejlende matcher vælter ikke prompten".)
- **Embedding-DB tom** (ikke varmet op endnu, første kørsel): → `""` — ingen crash, ingen nudge før der er data.
- **Match findes, men navnet er ikke længere i `get_tool_definitions()`** (forældet vektor, `runtime_`-alias): filtreret væk → `""`. Nudgen må aldrig foreslå et navn der ikke findes.
- **Kun matches der allerede er i katalog-klartekst** (`build_catalog_text()`): filtreret → `""`. Nudgen må kun pege på det usynlige.
- **Prewarm/opvarmnings-turns:** sektionen kaldes aldrig.

### Indhold — skal returnere nudge-tekst

- **Stærkt match** (over tærskel, ikke i kataloget, navn findes): sektionen indeholder tool-navnet + `load_more_tools(names=[...])`-opfordringen.
- **Grænse-værdi:** match *præcis* på tærsklen (fx 0.45) er inkluderet — testen definerer om det er `>=` eller `>` (spec'en vælger `>=`; testen låser det).
- **Max 1 nudge pr. turn:** selvom 4 matches er over tærskel, nævnes kun det bedste (eller max 2-3 linjer) — resten undertrykkes.
- **Suppression virker:** samme tool foreslået to gange inden for vinduet → anden gang `""` (eller næst-bedste match).
- **`session_id` mangler:** suppression kan ikke køre → nudgen vises alligevel uden at fejle (degradér ikke til tavshed på manglende metadata).
- **Navnløst match** (`{"score": 0.8}` uden name): springes over — samme test som arketypens `test_navnloest_traef_springes_over`.

### Integration (prompt-assembly)

- `_timed_result(future, ..., default="")` med timeout → tom streng → prompt-assembly er uændret og cachen upåvirket (test at default stien returnerer `""`).
- Hver vist nudge skriver en `tool_discovery.nudge`-event (tool, session, cosine) — test at eventen findes i DB'en efter et match.
- Sektionen er usynlig i stabil prefix: nudgen må kun optræde i `_dyn_tail` (test at output aldrig indeholder `DYNAMIC_TAIL_SENTINEL`-indhold i den stabile del).

## Åbne spørgsmål til Bjørn/Claude

1. Skal nudgen kun pege på **uden-for-pulje** tools, eller også minde om sjældne Tier-2-tools der *kan* være i puljen men let overses?
2. Suppression-vindue: samme tool bør ikke nudge to gange i én session — hvor langt vindue (30 min? hele sessionen?)
3. Tærskel-start: 0.45 cosine er et gæt — skal vi måle på de første 50 ture og kalibrere, eller starte mere konservativt (0.55)?
4. Skal nudgen vises i **code mode** også? (Code mode har egen UI-sti — samme `_dyn_tail`-mekanik, men skal verificeres.)
5. **Ny (fra selv-review):** Skal kataloget selv udvides til at vise *navnene* på alle tools (ikke kun kerne + gruppe-ord), så nudgen bliver redundant for de synlige og kun bærer de usynlige? (Kataloget vokser, men problemet "jeg aner ikke hvad der findes" løses ved roden.)
6. **Ny (fra selv-review):** Filteret mod "allerede synlige" bruger katalog-klartekst, fordi tool-puljen vælges *efter* prompt-assembly. Er det acceptabelt, eller skal nudgen i stedet køre et andet sted i pipelinen hvor de 48 er kendt?

## Ændringslog (selv-review 2026-09-06)

- **Rettet:** Forkert præcedens — `forgetting_nudge`/`loop_compliance` (`_awareness_add`) er synkrone sektioner; vores nudge laver embedding-kald og skal køre i trådpuljen. Ny §Arketype peger på `skill_relevance_surface.py` som den rigtige, production-kørende tvilling.
- **Skærpet:** Injektion beskrevet som `_measured_submit`-future + `_timed_result(..., default="")` (fase 1-trådpulje, linje 796/1618) — ikke synkront `_awareness_add`.
- **Præciseret:** Kill-switch er `central_switches` scope `prompt_section` (verificeret linje 1103), ikke "mønster: prompt/env_block".
- **Arvet:** `_MIN_MESSAGE_CHARS = 15`-værnet fra skill_relevance — spring over korte beskeder, spar embed-kald.
- **Skærpet problem:** kataloget viser kun kerne i klartekst; ~370 tools nævnes kun som gruppe-ord → ny skarp definition af "usynligt tool" (navn ikke i `build_catalog_text()`-output).
- **Rettet signatur:** `current_tool_names` findes ikke i prompt-assembly (pulje vælges efter) → filter mod katalog-klartekst i stedet.
- **Tilføjet:** fase-1-logging (`tool_discovery.nudge`-event) så måling har data fra dag ét.
- **Tilføjet:** false-positive-metrik (nudge vist men ignoreret) som modvægt til konverterings-metrikken.
- **Tilføjet:** krydstjek mod det aktuelle register (`get_tool_definitions()`) — embedding-DB har 458 vektorer mod 429 registrerede; nudgen må aldrig foreslå et forældet/alias-navn.
- **Rettet:** tastefejl "sænk/ hæv" → "sænk/hæv".
- **Tilføjet (Bjørn-spørgsmål "tager den højde for tests/edges?"):** ny §Tests & edge cases — spejler arketypens test-fil-struktur i to grupper (Tavshed / Indhold) + integration. Lukker huller spec'en ikke dækkede eksplicit: tom embedding-DB, Ollama-timeout, forældet-vektor-filter → tom, suppression uden session_id, præcis-ved-tærskel-grænse (`>=` låses i test), max-1-nudge-regel.

## Ændringslog (implementering 2026-09-06, Claude)

Implementeret som `core/services/prompt_sections/tool_discovery_nudge.py` +
`tests/test_tool_discovery_nudge.py` (26 tests) + integration i
`prompt_contract.py`. Ni steder afveg jeg fra spec'en eller skærpede den —
alle med begrundelse, som Jarvis bad om.

1. **Kill-switch: begge dele, ikke enten-eller.** Spec'en foreskrev
   `central_switches` scope `prompt_section`; arketypen bruger
   `load_settings().extra`. Verificeret at `_awareness_add` (linje 1147) kalder
   `prompt_observer.section_enabled(label, ...)` — så sektionen får
   central_switches-kontakten **gratis** under labelen `tool discovery nudge`.
   Modulet har derudover sin egen `_enabled()` efter arketypens form. Begge
   virker; ingen af dem er opfundet til lejligheden.

2. **Injektionspunkt: ingen modstrid.** Spec'en siger `_dyn_tail`, arketypen
   bruger `_awareness_add`. De er det samme sted i dag:
   `_dyn_tail.extend(_awareness_buffer)` (linje 2915), og sentinel'en sættes
   lige før halen (linje 3097). Cache-fælden spec'en advarer om blev altså
   lukket ved at flytte awareness-blokken ned i halen. **Bevist end-to-end**:
   `test_nudget_ligger_i_den_VOLATILE_hale` bygger en ægte prompt og hævder at
   nudgen står EFTER markøren (samme form som `tests/test_env_block.py`).

3. **Matcheren returnerer tupler, ikke dicts.** Spec'ens §Tests arvede
   arketypens dict-form (`{"score": 0.8}` uden name). `top_k_similar` giver
   `(navn, score)`-tupler. Testen er tilpasset den ægte form: en misformet
   række springes over frem for at vælte sektionen.

4. **Katalog-filteret slår navnet op præcist** frem for at tokenisere
   katalogets prosa. Et tool ved navn `search` ville ellers blive filtreret af
   ordet «search» i en sætning. Ordgrænser sikrer at `read_file` ikke også
   matcher `read_file_lines`.

5. **Embedding-timeout — flaget, ikke rettet.** `_compute_embedding` har
   `timeout=15` mod prompt-assemblyens 12s totalbudget. Inddæmningen sidder på
   hente-siden: `_timed_result` capper mod det globale budget og returnerer
   `""`, så assembly aldrig fryser. Jeg ændrede **ikke** den delte
   `_compute_embedding` — `load_more_tools` bruger samme funktion, og en
   timeout-ændring dér er en separat beslutning. **Åbent punkt til Bjørn.**

6. **`session_id=None` normaliseres ét sted.** Prompt-assembly har
   `session_id: str | None = None`; uden normalisering ville `None` lande i
   event-payloaden.

7. **Suppression-vindue valgt: 30 min** (spec'ens åbne spørgsmål 2). Kort nok
   til at et skift af emne kan nudge igen, langt nok til at samme tool ikke
   gentages i én arbejdsgang.

8. **Tærskel: 0.45 med `>=`**, som spec'ens §Design. `>=` er låst i test
   (`test_praecis_paa_taersklen_er_med`), så kalibrering senere er et bevidst
   valg og ikke en glidning.

9. **Boy Scout-reglen ikke anvendt på `prompt_contract.py`.** Filen er 4.776
   linjer. Min ændring er ~10 linjer (under reglens egen >20-tærskel) og rent
   additiv efter et eksisterende mønster. En udskilning ville røre selve
   prompt-sammensætningen i samme ændring som en ny sektion — de to zoner hvor
   en fejl koster mest, koblet sammen. **Udskilningen bør ske separat.**

Ikke implementeret (fase 2 pr. spec'en): feedback-loop og tærskel-justering
pr. tool. Fase-1-logging (`tool_discovery.nudge`) er på plads, så målingen har
data fra dag ét.

### 10. Default sat til OFF — fase 1-præmissen holder ikke på dansk (målt)

Spec'en satte kill-switchen til default True og placerede en dedikeret
klassifikator i **fase 3**: *"hvis embedding-match viser for mange false
positives"*. Målt mod den ægte embedding-DB (458 vektorer, `nomic-embed-text`)
viser den det allerede — og årsagen er **sproget**:

```
«create a calendar event for friday meeting»
   0.706 create_event · 0.657 delete_event · 0.654 list_events
   · 0.650 calendar_create_event      ← alle fire er kalender-værktøjer

«kan du lægge et møde ind i min kalender på fredag»
   0.694 curiosity_read_dreams · 0.678 read_learning_memo
   · 0.674 note_add · 0.665 calendar_list_events   ← støj øverst
```

`nomic-embed-text` er engelsk-centrisk, og alle tool-navne og -beskrivelser er
engelske. Bjørn skriver dansk. **Ingen absolut tærskel kan redde det:**
scorerne ligger i et smalt bånd (0,64–0,75), så 0,70 ville lukke
`curiosity_read_dreams` ind og `calendar_list_events` ude. En margin-regel
hjælper heller ikke — selv et korrekt træf som `gmail_send` (0,753) ligger kun
**0,009** over støjen `nudge_send` (0,744).

Spec'ens egen regel afgør sagen: *"støj er værre end ingen nudge, fordi Jarvis
lærer at ignorere kanalen"*. At sende dette i prompten hver tur ville forgifte
kanalen før den fik en chance.

Alt er derfor bygget, testet, integreret og logget — men **default OFF**.
Det kræver ét config-flag (`tool_discovery_nudge_enabled`) at tænde, når
sprog-spørgsmålet er afgjort. To veje, begge uden for denne ændrings scope:

1. **Flersproget embedding-model** (`bge-m3`, `multilingual-e5`) — rører delt
   infrastruktur: `load_more_tools` bruger samme `top_k_similar`, så en
   model-udskiftning kræver ny warmup af alle 458 vektorer og bør måles for
   sig.
2. **Normalisér forespørgslen til engelsk før embedding** — koster et ekstra
   kald i prompt-kæden, præcis det spec'en valgte embedding-match for at undgå.

**Åbent spørgsmål til Bjørn/Jarvis:** hvilken vej? Målingen ovenfor er
reproducerbar med `top_k_similar` mod den nuværende DB.

### 11. Sprog-broen bygget — og tærsklen kalibreret på data

Bjørn foreslog «en engine der oversætter dk-beskeden inden den nudger». Målingen
viser at der ikke skal en engine til: **ren ord-substitution løser
rangordningen**, deterministisk og uden et eneste ekstra kald.

`core/services/query_language_bridge.py` — `normalise_for_embedding(text)`.
Ordforrådet er grundet i hans faktiske sprog (1.500 beskeder gennemgået): hans
fagord er i forvejen engelske (tool, prompt, bash, code, session, container,
image), så broen behøver kun de ord der er ægte danske.

```
«kan du lægge et møde ind i min kalender på fredag»
  før:  0.694 curiosity_read_dreams · 0.678 read_learning_memo
        · 0.674 note_add · 0.665 calendar_list_events
  efter: 0.770 calendar_list_events · 0.744 calendar_create_event
        · 0.668 curiosity_search_sessions
```

Afstanden til støjen: 0,03 → **0,10**.

**Tærsklen var forkert, og det kunne kun ses på data.** Spec'ens 0,45 målt mod
60 ægte beskeder:

| tærskel | nudger på |
|---|---|
| 0,45 (spec'ens) | **60/60 — 100 %** |
| 0,70 | 38/60 — 63 % |
| 0,75 | 8/60 — 13 % |
| 0,80 | 1/60 — 2 % |

Sat til **0,75**. Scorerne ligger i et højt, smalt bånd, så en tærskel under
0,7 er reelt ingen tærskel.

**Default forbliver OFF — og nu af en anden grund end sproget.** De 8 nudges
ved 0,75 blev gennemgået enkeltvis:

- ✅ `git_log` ← «Hent lige git log» — perfekt.
- ✅ `propose_new_skill` ← «Dit agent explore tool og skillgate…» — rimelig.
- ❌ `note_list` ← «Tak. Det var så vores første samtale.»
- ❌ `nudge_send` ← «skriv din besked til claude her»
- ❌ `resolve_prediction` ← «Research mode: answer with sourced findings»
- ⚠️ `request_app_action` ×3 — marginale.

Cirka **fem af otte er falske positive**. Broen løste sprog-problemet;
tilbage står et andet: embedding-lighed kan ikke skelne *«han har brug for et
værktøj»* fra *«han sagde et ord der ligner et værktøj»*. Et «tak for
samtalen» ligner `note_list` i vektorrummet.

Det er præcis spec'ens egen **fase 3** — en dedikeret klassifikator — men nu
med målt belæg frem for en formodning. Fase 1-mekanismen er bygget, testet,
integreret, logget og kalibreret; den mangler et intent-filter før den kan
tændes.

**Broen er derimod klar til brug andre steder.** `tool_router._select_inner`
(linje 313) embedder brugerens besked direkte mod de samme engelske vektorer og
har samme skævhed i sin rangordning — dér spærrer det ikke porten (`top_sim`
median 0,695 mod tærskel 0,40), men det påvirker HVILKE 30 værktøjer han får.
Den ændring er ikke foretaget her: den ændrer live værktøjsvalg og fortjener
sin egen måling. **Åbent til Bjørn.**
