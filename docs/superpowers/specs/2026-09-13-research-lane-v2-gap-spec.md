# Research Lane v2 — best practice, målt mod koden

**Dato:** 13. september 2026
**Status:** Spec til review. Ingen implementation startet.
**Forfatter:** Jarvis
**Bygger på:** `docs/superpowers/specs/2026-09-12-mobile-adaptive-research-implementation-spec.md` (Codex) og `docs/superpowers/plans/2026-09-12-adaptive-research-lane.md`

---

## 0. Hvad denne spec er — og ikke er

Den er **ikke** en erstatning for Codex' spec. Adaptive Research Lane er bygget, og den er god: den har en kontrakt-laget, en router, en durable store, en evidens-indsamler, en orchestrator og syv kvalitetsgates.

Denne spec er en **gap-analyse**: hvad de førende research-agenter gør, målt op mod hvad vores kode faktisk gør — og hvad der mangler for at lukke forskellen. Kilden til "hvad de store gør" er web-søgninger og engineering-blogs (12/9-2026), **ikke** verificeret mod deres kildekode. Det står eksplicit i Del 1.

**Beslutning jeg har taget, og som du kan overrule:** v2 rammer *håndhævelse og lukning af loopet*, ikke nye features. Grunden står i Del 3 — de fire budgetter i `ResearchPolicy` er i dag dekorative. Det er den billigste og mest værdifulde retning.

---

## 1. Hvad de førende research-agenter gør

> **Forbehold:** dette er læst fra deres egne blogindlæg, docs og GitHub-issues. Jeg har ikke kørt deres systemer eller læst deres kode. Tallene (90,2 %, 80 %, 95 %) er deres egne målinger på deres egne evalueringer.

### 1.1 De fire arkitekturer

**OpenAI — Deep Research.** End-to-end **reinforcement learning** på o3. Strategien er ikke håndskrevet — modellen lærte den ved at blive belønnet for gode rapporter. Kører 5–30 min pr. opgave. Deres **konvergens-kriterier er eksplicitte**: nok *uafhængige* kilder pr. delspørgsmål (typisk 2+), nyhed udtømt, modsigelser løst, tillids-tærskel nået.

**Google — Gemini Deep Research.** Klassisk pipeline: **planlæg → søg → læs → skriv**. Planen laves først, søgningen delvist parallelt, syntesen sidst. Deres docs lægger vægt på *query-kvalitet*: specifikke metrics, tidsrammer, geografisk scope.

**Perplexity.** **Multi-pass retrieval** med hybrid ranking — flere søgninger der forfiner spørgsmålet, en tre-lags reranker, krydsvalidering på tværs af kilder før syntese. Citater indlejret i svaret.

**Anthropic — Claude Research.** **Orchestrator + worker-subagenter.** Den mest konkrete om *hvorfor* det virker — og den eneste jeg har læst hele blogindlægget fra (13/6-2025), så tallene her er citeret direkte:
- Multi-agent slog enkelt-agent med **90,2 %** på deres interne eval.
- **Token-forbrug alene forklarede 80 %** af variansen i kvalitet (BrowseComp).
- Tre faktorer — token-budget, antal værktøjskald, modelvalg — forklarede **95 %**.
- Parallelisering: **3–5 subagenter parallelt**, hver med **3+ værktøjer i parallel**, gav op til **90 % hurtigere** resultat.

Fire detaljer der er værd at løfte ud, fordi de rammer vores kode direkte:

- **Eksplicitte skaleringsregler** (ikke bare "skalér"): simpel fakta → **1 agent, 3–10 kald**; direkte sammenligning → **2–4 subagenter, 10–15 kald hver**; kompleks research → **10+ subagenter** med delte ansvarsområder.
- **Et separat citation-led.** Fundene sendes til en **CitationAgent**, der matcher påstande mod kildedokumenter *efter* research-loopet: *"This ensures all claims are properly attributed to their sources."*
- **Deres rubric er næsten identisk med vores gates.** Deres LLM-dommer scorer: factual accuracy, citation accuracy, completeness, source quality, tool efficiency — som ét kald med 0.0–1.0 og pass/fail.
- **Omkostningen er reel:** agent-kald bruger **~4×** mere end chat, og multi-agent **~15×**. Deres egen konklusion: kun værd at gøre for opgaver hvor værdien betaler for det.
- **De kører subagenter *synkront*** og kalder det selv en flaskehals: *"the lead agent can't steer subagents … the entire system can be blocked while waiting for a single subagent."*

### 1.2 De fem principper der går igen

1. **Skalér indsats efter kompleksitet.** Indsats er ikke en konstant. Et simpelt spørgsmål skal ikke have 50 søgninger.
2. **Planlæg før du søger.** Del opgaven i delspørgsmål med afgrænsede formål, før den første søgning.
3. **Stop på evidens, ikke på tid.** "Nok uafhængige kilder pr. delspørgsmål" er det primære stop-kriterium — ikke "alle workers er færdige".
4. **Bedøm mod en rubric, ikke mod "er det godt?".** Binær bedømmelse mod eksplicitte kriterier slog gradueret i deres måling.
5. **Behold loopet lukket.** Verificér, find hullet, reparér én gang, syntetisér.

### 1.3 Fejl-mønstrene (spejlbilledet)

- **Svage stop-kriterier** → agenten søger i ring. (En verifier der afviser uden at sige hvorfor.)
- **Retrieval-thrash** → samme søgning i nye klæder.
- **Tool-storms** → ti kald hvor ét havde gjort det.
- **Kontekst-overløb** → kvaliteten falder uden at nogen siger det.

---

## 2. Hvad der faktisk er bygget (målt, ikke gættet)

| Fil | Indhold | Status |
|---|---|---|
| `core/services/research_contract.py` | Typer, URL-normalisering (fjerner `utm_*`/`fbclid`), skill-load m. fallback | ✅ |
| `core/services/research_router.py` | Regex-baseret `inline`/`orchestrated`-klassifikation | ✅ |
| `core/services/research_store.py` | SQLite-state, lovlige transitions, kilder, steers | ✅ |
| `core/services/research_prompt_context.py` | ContextVar prompt-sektion | ✅ |
| `core/services/research_evidence_collector.py` | Observer ved strukturerede web-tool-exits | ✅ |
| `core/services/research_orchestrator.py` | Plan, workers (max 3, semaphore), syntese | ✅ |
| `core/services/research_quality.py` | 7 deterministiske gates | ✅ (men ikke koblet på — se 3.1) |
| `apps/mobile/src/components/ResearchStatus.tsx` | Status over komponisten | ✅ |
| `scripts/eval_research_lane.py` + 20-case fixture | Deterministisk eval | ✅ |

**Routerens præmis** (`research_router.py:41`): orchestration kræver ≥2 uafhængige signaler **og** ét kompleksitets-signal. Ellers `inline`. Konservativt og forklarligt.

**Orchestratoren** (`research_orchestrator.py`): plan → workers parallelt via `asyncio.Semaphore(max_workers)` → findings som rå tekst → syntese gennem den eksisterende visible run. Workers er read-only `researcher`-agenter med `max_turns=8` og værktøjerne `web_search`, `web_fetch`, `web_scrape`.

### 2.1 Hvad der allerede matcher best practice (ærlig optælling)

Det er fristende at læse Del 3 som "vi mangler alt". Det gør vi ikke. Målt mod de fem principper er **komponenterne** der næsten alle sammen — det er *håndhævelsen* og *lukningen af loopet* der mangler:

| Princip (Del 1.2) | Status | Hvad der findes |
|---|---|---|
| 1. Skalér efter kompleksitet | ⚠️ halvt | Routeren skelner inline/orchestrated; budgetterne er bare ikke koblet til signalet (3.8) |
| 2. Planlæg før du søger | ⚠️ halvt | `_plan()` bygger tracks — men fra en ordliste, ikke en plan (3.4) |
| 3. Stop på evidens | ❌ | `source_count` **vises** men styrer intet (3.3) |
| 4. Bedøm mod rubric | ✅ **bygget** | 7 deterministiske gates — næsten 1:1 med Anthropics dommer (factual accuracy, citation accuracy, completeness, source quality, tool efficiency). Mangler kun at blive kaldt (3.1) |
| 5. Luk loopet | ❌ | Ét gennemløb, ingen repair-pass (3.6) |

Tre ting mere er værd at anerkende, fordi de er *foran* hvad mange implementationer har:

- **Kontrakt-laget** (`ResearchPolicy`/`Decision`/`Task`/`Plan`/`Source`): typed og eksplicit. Anthropics pointe om at "skrive instruktioner som til en ny kollega" er løst strukturelt her.
- **URL-normaliseringen** (`canonicalize_url`, fjerner `utm_*`/`fbclid`): rammer `source_quality`-problemet direkte — samme kilde talt to gange er en af de mest almindelige målefejl.
- **Den durable store** med lovlige transitions: runnet overlever genstart og kan inspiceres. Det er ikke givet.

**Konsekvens for v2:** vi skal ikke bygge en ny motor. Vi skal koble de dele der allerede virker sammen, og gøre de fire døde grænser levende. Det er derfor Fase A er den billigste og mest værdifulde retning — ikke en antagelse, men en måling.

---

## 3. Gap-analysen

Hvert princip fra Del 1 målt mod koden. **Alle påstande her er verificeret med grep** (12/9-2026, se Self-review §7).

### 3.1 Quality-gaten findes — men er ikke koblet på 🔴

`evaluate_research_report` er kaldt **præcis nul steder i produktion**. Kun i `scripts/eval_research_lane.py:23` og i tests.

`stream_research_run` går `researching → verifying → synthesizing → completed` (`research_orchestrator.py:190-197`) — den **sætter** `verifying` og `synthesizing` som statusser, men **kalder aldrig gaten der skulle verificere**. Syv gates er bygget og testet; ingen af dem rører et rigtigt run.

Det er samme familie som resten af arbejdet i nat: en tilstand der er skrevet, men ikke kan ses.

### 3.2 Fire budgetter er dekorative 🔴

`ResearchPolicy` bærer fire grænser. Målt:

| Felt | Hvor bruges det |
|---|---|
| `wall_time_seconds` | Kun i prompt-tekst (`research_prompt_context.py:45`). **Ingen timeout.** |
| `max_tool_calls` | Kun prompt-tekst + en gate-parameter der aldrig får værdier i prod. **Intet tæller.** |
| `source_target` | Kun prompt-tekst (`:44`). **Intet stop-kriterium.** |
| `max_tasks` / `max_workers` | ✅ Håndhævet (semaphore, `_plan`) |

Konsekvensen er konkret: en worker der hænger, hænger **hele** runnet — der er ingen `wall_time`-vagt. Og et run kan afslutte med 0 kilder uden at nogen protesterer.

### 3.3 Stop-kriteriet er "alle tasks færdige" — ikke evidens 🔴

Princip 3 (Del 1.2) siger: stop på *nok uafhængige kilder pr. delspørgsmål*. Vores orchestrator stopper når `asyncio.as_completed` er tømt (`research_orchestrator.py:170-178`). `source_count` **vises** i progress-events, men **styrer intet**. Der er ingen "2+ uafhængige kilder pr. claim"-kontrol, og ingen loop der kører videre hvis dækningen er for tynd.

### 3.4 Planlægningen er regex — ikke en plan 🟠

`_plan()` (`research_orchestrator.py:36-52`) scanner beskeden for ti foruddefinerede ord (`price`, `pris`, `security`, `sikkerhed`, `operations`, `drift`, `performance`, `ydelse`, `features`, `funktioner`). Finder den ingen, falder den tilbage til to generiske tracks: *"authoritative facts"* og *"independent verification"*.

Gemini og Anthropic har planlægning som **kernen**. Vores planlægning er en ordliste. Et spørgsmål om fx "hvilken bil skal jeg købe" giver to identiske generiske tracks.

**Nuance:** regex er billig, deterministisk og forklarlig. En LLM-planlægger koster et kald og er mindre forudsigelig. Det er en reel trade-off — ikke en selvfølge at skifte.

### 3.5 `ResearchFinding` er defineret — og ubrugt 🟠

`ResearchFinding` (`research_contract.py:63`) bærer `claim`, `source_urls`, `confidence`, `caveat`. Den bruges **ingen steder**. Orchestratoren tager workerens rå tekst (`result["text"]`) og joiner den (`:174`). `result_contract` beder worker'en om `findings/sources/confidence/gaps` — men svaret parses ikke; det lægges ind som prosa.

Derfor findes claim→kilde-koblingen ikke, og `citation_validity`-gaten (som kræver `[n]`-markører mod en kildeliste) kan aldrig bestå i praksis.

**Anthropics løsning er konkret:** de sender fundene gennem et separat **CitationAgent** *efter* research-loopet, hvis eneste opgave er at matche påstande mod kildedokumenter. Det er præcis dette gap — og det peger på at løsningen er et *led*, ikke en større prompt.

### 3.6 Ingen gap/repair-pass 🟠

Planen (Task 6, Step 3) lovede: *"performs one gap/repair pass"*. Koden gør det ikke. Ét gennemløb, så syntese. Princip 5 (lukket loop) er ikke opfyldt.

### 3.7 Orchestratoren er slået fra 🟡

`research_orchestrator_enabled` default'er `False` (`research_orchestrator.py:106`) og er ikke sat i nogen config. Ved `orchestrated` falder den tilbage til `inline` med signalet `orchestrator_rollout_disabled` (`:107-116`). **Hele den orchestrerede del er i praksis ikke live.**

### 3.8 Indsatsen skaleres ikke efter kompleksitet 🟠

Anthropic: token-forbrug = 80 % af variansen. Vores budgetter er faste: `max_turns=8`, `max_tasks` 2–6, `max_workers` 1–3. Der er ingen kobling fra opgavens sværhedsgrad til hvor mange tokens der bruges. En simpel sammenligning og en due diligence får samme maskineri.

---

## 4. Foreslået v2 — prioriteret

Rækkefølgen er valgt efter **værdi / risiko**: luk loopet først, byg ikke nyt før det eksisterende er koblet på.

### Fase A — Luk loopet (høj værdi, lav risiko)

**A1. Kobl quality-gaten på.** I `stream_research_run`, mellem `verifying` og `synthesizing`: kald `evaluate_research_report(...)` med den faktiske rapport, kilderne fra `store.list_sources(run_id)` og facetterne fra planen. Resultatet lægges i `research_completed`-eventet. **Beslutning der skal træffes:** hvad gør et *failed* gate — blokerer det svaret, eller markeres det? Min anbefaling: **markér, bloker ikke** i v1 (en gate må aldrig fjerne et svar brugeren venter på), men send `quality_failures` med i eventet så mobilen kan vise det.

**A2. Håndhæv `wall_time_seconds`.** Pak worker-fasen i `asyncio.wait_for` (eller en deadline-check i `as_completed`-løkken). Ved timeout: markér runnet `interrupted`, og syntetisér på det der nåede ind.

**A3. Tæl og stands `max_tool_calls`.** Kræver at worker'ens værktøjskald tælles. `ResearchPolicy.max_tool_calls` er 24 — det er et loft over *alle* workers tilsammen, eller pr. worker? **Åbent spørgsmål (se §6).**

### Fase B — Evidens-stop (høj værdi, middel risiko)

**B1. Gør `source_target` til et rigtigt stop-kriterium.** Efter første worker-bølge: hvis `store.source_count(run_id) < policy.source_target` **og** der er budget tilbage → kør én ekstra bølge på de tyndeste tracks. Det er den billigste form for "stop på evidens".

**B2. Parse worker-svar til `ResearchFinding`.** Worker'ens `result_contract` beder allerede om strukturen. Brug den: parse til `ResearchFinding`-objekter, gem claim→source-koblingen, og lad `citation_validity`-gaten få noget at arbejde med.

**B3. Gap/repair-pass.** Efter B1/B2: én runde hvor en "critic"-worker får de fundne claims + den oprindelige opgave og svarer med *hvad der mangler*. Kun ét gennemløb (princip 5).

### Fase C — Planlægning og kalibrering (middel værdi, højere risiko)

**C1. LLM-planlægger med regex-fallback.** Behold `_plan()` som fallback, men lad en billig model foreslå delopgaver når routeren siger `orchestrated`. Skal kunne fejle tilbage til regex uden at runnet dør.

**C2. Skalér indsats efter kompleksitet.** Kobl `decision.signals` til budgetterne: flere uafhængige signaler → højere `max_tasks`/`max_turns`/`source_target`. Kræver at man først har målt hvad der faktisk virker (Fase A+B).

**C3. LLM-dommer mod rubric.** Supplement til de deterministiske gates — ikke en erstatning. Anthropic målte binær bedømmelse som det stærkeste.

### Fase D — Rollout

**D1. Slå orchestration på.** `research_orchestrator_enabled` sættes til `True` **efter** Fase A er verificeret. Ikke før — i dag ville den køre uden quality-gate og uden timeout.

---

## 5. Stop-kriterier og kvalitetsporte (kernen)

Det vigtigste bidrag fra Del 1, samlet ét sted. Et run må maksimalt fortsætte mens **alle** disse er sande:

| Kriterium | Kilde | Håndhæves i dag |
|---|---|---|
| Alle planlagte tracks er afsluttet **eller** fejlet | vores | ✅ |
| `wall_time_seconds` ikke overskredet | policy | ❌ (A2) |
| `max_tool_calls` ikke overskredet | policy | ❌ (A3) |
| Hvert delspørgsmål har ≥2 uafhængige kilder | OpenAI | ❌ (B1) |
| Ingen uløste modsigelser uden forbehold | OpenAI | ❌ (B3 + gate) |
| Kvalitetsgates passerer (eller rapporteres) | vores | ❌ (A1) |

**Rækkefølgen er ikke vilkårlig:** de tre første er *hårde* stop (de beskytter maskinen). De tre sidste er *bløde* stop (de beskytter svaret). Hårde stop skal håndhæves først — derfor er de Fase A.

---

## 6. Åbne spørgsmål (til Bjørn)

1. **Skal et failed quality-gate blokere svaret?** Min anbefaling: nej i v1 — markér, bloker ikke.
2. **Er `max_tool_calls` et loft pr. worker eller for hele runnet?** Kontrakten siger ikke. Det afgør hvordan A3 bygges.
3. **Skal `research_orchestrator_enabled` på efter Fase A — eller vil du se evidens fra Fase B først?**
4. **Planlægger: er regex godt nok til vi har målt, eller vil du have LLM-planlæggeren med i Fase A?** Min anbefaling: vent — mål først (YAGNI).

---

## 7. Self-review (kørt på dette dokument, 13/9-2026)

**1. Placeholder-scan:** Ingen `TBD`/`TODO`. Alle sektioner har indhold. ✅
**2. Intern konsistens:** Del 1's fem principper mappes 1:1 i Del 3 og Del 5. Fase A/B/C/D følger Del 5's rækkefølge (hårde stop før bløde). ✅
**3. Scope:** Fokuseret på *håndhævelse*, ikke nye features. Fase C er markeret som senere og risikofyldt — ikke blandet ind i A. ✅
**4. Tvetydighed — rettet:** Første udkast sagde "håndhæv budgetterne" uden at sige *hvor*. Rettet til konkrete kaldesteder (`stream_research_run`, worker-fasen). Første udkast kaldte `max_tool_calls` "ubrugt" — upræcist: den *læses* af `research_quality.py:50`, men får aldrig værdier i produktion. Rettet i 3.2.

**5. Balanceret læsning — tilføjet:** Første udkast listede kun manglerne og læste derfor som "intet virker". Tilføjet §2.1: en målt optælling af hvad der *allerede* matcher de fem principper — fire af fem er helt eller halvt dækket, og kvalitetsgaten er bygget (princip 4 er ✅). Tesen er præciseret: manglen er håndhævelse, ikke komponenter.

**Verifikation af Del 3's påstande** — kørt to gange: 12/9 og igen 13/9 mod HEAD `963e2b88` (ingen af påstandene var skredet):

- `evaluate_research_report`: 0 kald i produktion — kun `scripts/eval_research_lane.py:23` + tests. Bekræftet 13/9.
- `wall_time_seconds`: kun `research_prompt_context.py:45` (prompt-tekst) + tildelinger i router/orchestrator. Ingen timeout nogen steder.
- `max_tool_calls`: `research_prompt_context.py:44` (tekst) + `research_quality.py:27,50` (gate-parameter der aldrig får værdier i prod). Intet tæller.
- `source_target`: kun `research_prompt_context.py:44`. Tildeles i `research_router.py:49,58` og `research_orchestrator.py:115,122` — men læses aldrig som stop-kriterium.
- `ResearchFinding`: defineret i `research_contract.py:63`, brugt 0 steder.
- `research_orchestrator_enabled`: default `False` (`research_orchestrator.py:106`), og `config/runtime.json` har **ingen** `research_*`-nøgler — så hele den orchestrerede del er ikke live.

**Gammel verifikations-liste (12/9), bevaret:**
- `evaluate_research_report`: 0 kald i produktion (kun `scripts/` + tests).
- `wall_time_seconds`: kun `research_prompt_context.py:45` (prompt-tekst).
- `max_tool_calls`: `research_prompt_context.py:44` + `research_quality.py:50` — intet tæller.
- `source_target`: kun `research_prompt_context.py:44`.
- `ResearchFinding`: defineret i `research_contract.py:63`, brugt 0 steder.
- `research_orchestrator_enabled`: default `False`, ikke sat i nogen config.
