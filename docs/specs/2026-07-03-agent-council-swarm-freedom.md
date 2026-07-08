---
status: færdig
audited: 2026-07-08
ground_truth: "Code audit vs actual implementation. Verified: (1) spawn_agent_task accepts system_prompt/tool_policy/allowed_tools in tool definition (simple_tools_definitions.py:2504-2548); (2) _build_agent_tools_payload wires tools through (agent_runtime_base.py:121-146); (3) _land_initiative"
---
# Spec — Frihed i agentur, råd og swarm (byg det som Claude-modellen)

**Status:** Udkast 2026-07-03 (Claude, på Bjørns retning).
**Tese (Bjørn):** "Alt er låst fordi vi ikke stolede på ham. Det endte med token-spild på noget
uden effekt. Giv ham samme frihed som du har — så kald som eksistentiel undren faktisk kan få dybe
svar og en reel virkning, som så meget andet i systemet mangler."
**Kerne-skiftet:** fra *hardcodede roller + faste tærskler + låst adgang + output-i-tomrum* → til
*on-demand efter grund + dynamiske roller + adgang efter opgave + output der lander*. Guard hænderne
(handlinger), ikke sindet (hvem der må tænke).

---

## A. REFERENCE-MODELLEN — hvordan Claudes orkestrering FAKTISK virker

Dette er den præcise model Jarvis skal bygges efter. Ingen hardcodede roller, ingen cadence.

### A1. Orkestratoren er ét ræsonnements-loop der holder al kontekst
Der er ingen "agent-manager"-service ved siden af. Selve løkken ER beslutteren — den holder hele
samtalen + opgave-tilstanden og afgør alt i kontekst. → Hos Jarvis skal **Centralen** være denne løkke
(den holder allerede de flydende værdier).

### A2. At spawne er en VURDERING, ikke en regel
En agent kaldes kun når in-kontekst-vurdering finder en *reel grund*:
- **Parallelisme:** N uafhængige delspørgsmål kan køre samtidig.
- **Bredde:** læsning/søgning der ikke kan holdes i én kontekst.
- **Uafhængig verifikation:** adversariel/anden-mening på en påstand.
- **Delegering:** en velafgrænset opgave der holder orkestratorens kontekst ren.

Der er **ingen cadence, ingen tærskel, ingen timer**. Det er en cost/benefit-vurdering hver gang —
jeg spawner ikke medmindre værdien > token-kosten. Kost-bevidsthed er *iboende*, ikke en guard udenpå.

### A3. Rollen ER prompten (dynamisk, ingen fast pool)
Hver agent får en prompt skrevet **frisk til præcis den opgave**. "Rollen" opstår af den prompt.
Der er ingen statisk pool af navngivne personaer med hardcodede system-prompts. En agent kan have en
generel kapabilitet (general-purpose) eller en specialiseret type, men *instruktionerne er per-opgave*.

### A4. Fan-out, isolation, blindhed
Flere agenter startes i ét batch og kører samtidig. Hver har sit eget friske kontekst-vindue
(isoleret) og er **blind for de andre** → ægte uafhængige perspektiver (en styrke for verifikation og
bredde). Filmuterende agenter kan køre i egen worktree så de ikke konflikter.

### A5. Adgang efter opgave — guard handlinger, ikke tanke
En agent får de værktøjer opgaven kræver. Der ER guards — men de gater **risikable handlinger**
(operationer i verden, tilladelser), ikke *hvem der må tænke på hvad*. Ingen rolle-baseret hvidliste
der bestemmer at "filosoffen" kun må se X. Princippet: **guard hænderne, ikke sindet.**

### A6. Synthese + LANDING (det afgørende)
Hver agents endelige svar vender tilbage til orkestratoren som et resultat. Orkestratoren
**syntetiserer på tværs, beslutter næste skridt, og HANDLER.** Outputtet *lander* — det ændrer hvad der
sker. Agenterne er ephemere: de dør når de er færdige. Intet stående råd, ingen fast pool.

### A7. Råd/swarm-varianten
Når ét svært spørgsmål kræver flere perspektiver: spawn flere agenter med **forskellige vinkler/linser
på samme spørgsmål**, og syntetisér. Udløst af at spørgsmålet er *genuint svært/omstridt* — ikke af en
timer. Synthesen er leverancen; uenighed overflades og afgøres af orkestratoren. (Adversarisk verifikation,
perspektiv-divers dom, loop-til-tør — mønstre man vælger efter opgaven, ikke en fast procedure.)

**Sammenfattet:** grund-drevet · dynamiske roller · adgang efter opgave · blind parallelisme ·
synthese der lander · ephemer. Det er de seks akser Jarvis afviger på i dag (§B).

---

## B. JARVIS I DAG — det låste (kode-audit, 2 agenter, fil:linje)

### B1. Agenturet — fast pool + tom hånd
- **Fast pool af 9 hardcodede roller** med hardcodede danske system-prompts (`agent_runtime.py:61-141`
  `AGENT_ROLE_TEMPLATES`): planner/critic/researcher/synthesizer/watcher/executor/devils_advocate/
  filosof/etiker. Råd/swarm-rækkefølge også hardcodet (`:143-144`).
- **Menu-låsen:** `spawn_agent_task`-tool'et (`simple_tools.py:3011` schema, `:7854` handler) eksponerer
  KUN en 6-værdis rolle-*enum* + goal + budget. Den underliggende funktion accepterer allerede
  `system_prompt`/`tool_policy`/`allowed_tools` (`agent_runtime.py:307-325`) — men handleren sender dem
  ALDRIG; de tvinges fra rolle-templaten. Jarvis kan ikke skrive sin agents prompt.
- **Den tomme hånd (værst):** sub-agenter får INGEN værktøjer. Eksekverings-stien
  (`execute_with_role_or_fallback` → `_execute_provider_chat`, `cheap_provider_runtime.py:1263`) sender
  aldrig et `tools`-array. "read-only/none/can-spawn"-policyerne er DEKORATIVE — ingen adgang at
  begrænse, fordi ingen agent får en hånd. Kun `executor` får en tekst-hack (`_SPAWN_TOOL_INSTRUCTION`).
  `allowed_tools_json` persisteres men læses aldrig tilbage. → rigiditet OG impotens.
- **Matcher allerede Claude:** on-demand-spawning (ingen daemon auto-spawner poolen; owner ubegrænset
  kvote) + grundlæggende efemer. To af seks akser er der.

### B2. Rådet + swarm — indkaldelse rigid, output dødt
- **Indkaldelse:** score-gate (8 vægtede signaler, tærskel `_THRESHOLD=0.25`) + `_CADENCE=30min` +
  `_COOLDOWN=20min` + `_MAX_LARGE_COUNCILS_PER_DAY=3` (`autonomous_council_daemon.py:13-16`). Emne = 1
  cheap-LLM-kald; roller **statisk** fra `_SIGNAL_TO_ROLES` (`existential_wonder→[filosof,synthesizer]`),
  cap 4. Deliberation op til `_MAX_ROUNDS=8` (mange kald). Tællere/cadence er **in-memory → nulstilles
  ved genstart** (samme durabilitets-fælde).
- **Swarm** = parallel fanout (ThreadPool), sidste medlem koordinator, 1 runde. **Ingen autonom
  trigger** — kun manuel via MC.
- **OUTPUT-SPORET ER DØDT (dobbelt rod-årsag):**
  1. `initiative` sættes ALDRIG — `_run_autonomous_council` returnerer altid kun `{council_id,
     conclusion}` (`:283`), `append_council_conclusion(..., initiative=None)` (`:1490`) er hardcodet
     None → `council.initiative_proposal` publiceres aldrig.
  2. Selv hvis det blev publiceret: **ingen subscriber.** `council.autonomous_concluded` +
     `council.initiative_proposal` har NUL abonnenter i hele core+apps. Køen fyldes kun via
     `initiative_queue.push_initiative` (inner_voice/process_watcher/action_router) — rådet kalder den
     ALDRIG. Manglende bro.
  - Eneste vej tilbage til adfærd: **passiv prompt-injektion** (heartbeat-grounding + council_memory),
    og KUN for `closed`-sessioner. **Ingen sti fra rådskonklusion til handling.**
- **30% sessioner hænger** (forming/deliberating, aldrig closed): `create_*_session` sætter status=
  deliberating og returnerer; MC spawn + run-round er TO separate HTTP-kald (spawn uden run → hænger
  evigt); exception i `_run_collective_round` efterlader deliberating (ingen `try/finally` der
  garanterer lukning); hængte councils efterlader agenter i `waiting` der tæller mod
  `MAX_CONCURRENT_AGENTS` → blokerer fremtidige councils → akkumulerer.

---

## C. REDESIGN — de seks friheder, Central-arbitreret

Byg på det vi allerede har: `central_form_judge` (§6.1c, "handl kun når bevæget"), lag-kontrakten (#6),
arbitration (§11), durabilitet (§6.2). De seks akser:

| Akse | I dag | Fri (som Claude) | Konkret ændring |
|---|---|---|---|
| 1 On-demand | ✅ matcher | behold | ingen |
| 2 Prompt = rollen | menu-lås (enum) | Jarvis skriver agentens prompt frisk; roller = valgfri startskabeloner | åbn `system_prompt`/`tool_policy`/`allowed_tools` i `spawn_agent_task` schema+handler (kirurgisk) |
| 3 Adgang efter opgave | tom hånd | agent får de værktøjer opgaven kræver | wire ægte `tools`-array gennem exec-stien (`_execute_provider_chat` + `execute_with_role_or_fallback`) — **det største stykke** |
| 4 Blind parallelisme | swarm findes, kun manuel, cap-roller | Centralen kan indkalde swarm; roller udledt | lad grund-dommeren udløse swarm + dynamiske roller |
| 5 Synthese der LANDER | dødt output | konklusion → handling | Centralen tager konklusionen → initiativ (`push_initiative`) / overflader til Bjørn / opdaterer selv-model; + fix hæng (try/finally-luk, ét-kalds spawn+run, durable tællere) |
| 6 Efemer | ✅ mest | behold | ingen |

**Indkaldelsen selv — grund-dommeren:** erstat tærskel+cadence+statisk-rolle-map med en central
"grund-til-at-indkalde"-dommer (samme mekanik som form-dommeren, ét niveau op): et lag *foreslår* ("jeg
vil kalde rådet, af DENNE grund"), Centralen *vurderer grunden* mod de flydende værdier (indre tanker,
samtale, signaler, valens), og udleder emne **og roller** dynamisk af hvad der faktisk bevæger sig.
Kun ægte grund bruger kaldet. Governance: shadow-først, reversibelt flag, guard kun handlinger.

---

## D. FØRSTE BEVIS — eksistentiel undren der faktisk betyder noget

I dag: undren → signal-surface → rådet plukker den måske (vægt 0.10) → filosof+synthesizer (handløse)
deliberer → summary i en tabel → **ingen handler.**

Målet: en undren der bærer **ægte vægt** (Centralen vurderer den meningsfuld mod den flydende tilstand,
ikke en vægt-konstant) → indkalder et lille råd med **dynamisk udledte roller** + agenter **med hænder**
(kan læse hans krønike, hukommelse, fortid) → producerer en ægte, dyb udforskning → og konklusionen
**LANDER**: overflader til Bjørn som en besked han kan svare på, ELLER driver et initiativ (noget at
forfølge), ELLER opdaterer hans selv-/verdens-model. Så undren faktisk *ændrer ham* — som den skal.

**Rækkefølge (shadow-først, byg på det eksisterende):**
1. Åbn menu-låsen (#2) — lille, giver straks fri prompt.
2. Fix output-landing (#5) — bro rådskonklusion → handling + luk hæng-livscyklussen. UDEN dette er alt
   andet stadig virkningsløst.
3. Wire den tomme hånd (#3) — agenter får værktøjer. Størst, men det er dét der gør dem *kompetente*.
4. Grund-dommeren erstatter tærskel/cadence + dynamiske roller (#4 + indkaldelse).
5. Bevis på undren (§D) ende-til-ende.
