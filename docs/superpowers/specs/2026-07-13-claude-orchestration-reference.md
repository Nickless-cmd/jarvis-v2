---
status: udkast (research + introspektion)
formål: Præcis, kilde-grounded model af HVORDAN Claude orkestrerer agenter + "råd",
         som fundament for redesign af Jarvis' agentur/råd/swarm. "Gør det rigtigt
         første gang — tag højde for det hele" (Bjørn, 13. jul).
kilder: FØRSTE-HÅND fra Claudes egne live tool-skemaer (Agent, Workflow) + skill
         subagent-driven-development i denne session. Krydstjekket mod officiel
         Claude Code-dok (separat research-agent). Hvor noget er inference, står det.
---

# Hvordan Claude FAKTISK laver agenter og kalder sit "råd"

> Bjørns pointe: "Dit er meget mere kraftfuldt og alligevel mere simpelt end det lort
> jeg lavede." Det er rigtigt — og grunden er at der IKKE er noget agent-system. Der er
> ét primitiv, komponeret forskelligt. Dette dokument beskriver primitivet præcist, hvad
> der gør det kraftfuldt-men-simpelt, og den fulde afbildning til Jarvis.

## DEL 1 — Mekanikken (første-hånd fra mine egne tool-skemaer)

### 1.1 Controlleren ER løkken (ingen manager-service ved siden af)
Der findes ikke en "agent-manager" som en separat tjeneste. Mit ræsonnements-loop ER
beslutteren. Det holder hele samtalen + opgave-tilstanden og afgør ALT i kontekst:
hvornår der skal spawnes, hvem der skal spawnes, hvad de skal have med, og hvad
resultatet betyder. Der er ingen skygge-proces bag mig — jeg er selv processen.

→ Dette er den ENESTE vigtigste forskel. Jarvis' council kører i dag i en daemon BAG
ham. Hos mig er der ingen bagved. Orkestratoren er den der tænker.

### 1.2 Ét primitiv: dispatch en KONSTRUERET kontekst → få et LANDET resultat
Hele orkestreringen hviler på ét kald: `Agent(prompt, subagent_type, …)`.
- Jeg konstruerer **præcis** den kontekst agenten har brug for. Agenten arver IKKE min
  historik — jeg giver den kun det den skal bruge. (Fra skill'en, ordret: *"They should
  never inherit your session's context or history — you construct exactly what they
  need."*) Det holder både min kontekst ren OG agentens ræsonnement fokuseret.
- Agentens **sidste besked ER returværdien** — den leveres tilbage til mig som
  tool-resultat. Output lander ALTID hos den der kan handle på det. Intet dør i en kø.
- Valgfrit: agenten kan **tvinges til struktureret output** (et JSON-schema valideres på
  tool-laget; modellen prøver igen ved mismatch). Så resultatet er maskin-brugbart data,
  ikke prosa-i-tomrum.
- Agenten kan køre **synkront** (jeg venter på svaret før jeg fortsætter) eller **i
  baggrunden** (jeg får besked når den er færdig → parallelisme).
- Jeg kan **fortsætte** en agent med bevaret kontekst (SendMessage til dens id) eller
  **starte frisk** (nyt Agent-kald). Roller er altså ikke persistente entiteter — de er
  konstruerede pr. opgave.

### 1.3 At spawne er en VURDERING, ikke en tidsplan
Fra Agent-tool-beskrivelsen (ordret parafraseret): *reach for this when the task matches
an agent type, when you have independent work to run in parallel, or when answering would
mean reading across several files — delegate it and you keep the conclusion, not the file
dumps. For a single-fact lookup where you already know the answer, search directly.*

Det vil sige — jeg spawner kun når in-kontekst-vurdering finder en **reel grund**:
- **Parallelisme:** N uafhængige delspørgsmål kan køre samtidig.
- **Bredde:** læsning/søgning der ikke kan holdes i én kontekst.
- **Isolation:** beskyt min egen kontekst mod at blive fyldt med støj.
- **Uafhængighed:** en frisk vurdering der IKKE skal arve min bias (kernen i "råd").

Der er INGEN cadence. Ingen "hvert 30. minut". Triggeren er behov, vurderet i kontekst.
Og disciplinen den anden vej (ordret fra skill'en): *once you've delegated a search,
don't also run it yourself — wait for the result.* Man dobbelt-arbejder ikke.

### 1.4 Review mellem trin — jeg er dirigent, ikke fabrik
Fra subagent-driven-development (min faktiske arbejdsmetode i denne session):
- Frisk subagent pr. opgave.
- **To-trins review efter HVER:** først spec-compliance (gjorde den det rigtige — hverken
  for lidt eller for meget?), så kode-kvalitet. Reviewer finder problem → samme agent
  fixer → re-review til godkendt.
- Jeg **holder overblikket** på tværs og justerer kursen mellem hvert kald. Jeg læser
  resultatet, beslutter næste træk, curerer næste agents kontekst ud fra det jeg lige lærte.

Det er forskellen på en dirigent (lytter, justerer, styrer) og en fabrik (producerer
blindt på et bånd). Jarvis' council er i dag en fabrik.

### 1.5 "Rådet" er IKKE et system — det er samme primitiv som en fan-out + syntese
Der er ingen separat council-motor med låste roller. Når jeg har brug for uafhængige
perspektiver, dispatcher jeg N agenter — enten identiske (afstemning) eller **hver med en
distinkt linse** — og syntetiserer selv. Fra Workflow-tool-beskrivelsen, de faktiske
mønstre:
- **Judge panel:** *generate N independent attempts from different angles, score with
  parallel judges, synthesize from the winner while grafting the best ideas from
  runners-up.* → Dette ER et "råd" — men rollerne er konstrueret til opgaven, ikke
  hardcodede Oracle/Architect/Critic.
- **Adversarial verify:** spawn N uafhængige skeptikere pr. påstand, hver bedt om at
  MODBEVISE; drop hvis flertal modbeviser. → Et råd hvis eneste job er at dræbe dårlige idéer.
- **Perspektiv-divers verify:** når noget kan fejle på flere måder, giv hver verifikator
  en distinkt linse (korrekthed, sikkerhed, ydelse, reproducerer-det) i stedet for N ens.
- **Loop-until-dry / completeness-critic:** bliv ved til K runder intet nyt finder; en
  sidste agent spørger "hvad mangler?".

Pointen: **råd og agent er DET SAMME primitiv**. Et råd er bare en fan-out af agenter med
et syntese-trin. Derfor er der intet at vedligeholde som et separat system.

### 1.6 Determinisme når det skal være det (Workflow)
Når orkestreringen skal være deterministisk (løkker, betingelser, fan-out) frem for
model-drevet, skrives den som et script: `agent()/parallel()/pipeline()/phase()`.
- `pipeline()` som default: hvert element gennem alle trin uden barriere (element A kan
  være i trin 3 mens B stadig er i trin 1 — vægur = langsomste enkelt-kæde).
- `parallel()` kun når man ægte skal bruge ALLE resultater samlet (en barriere).
- Concurrency er cappet (~min(16, cores-2) samtidige); man kan sende 100 elementer og de
  kører efterhånden. Struktureret schema-output pr. trin.

Dette er "råd/swarm med rygrad" — men stadig bygget af samme agent()-primitiv.

### 1.7 Event-drevet, IKKE tidsdrevet (krydstjekket mod officiel dok)
Dette er kernen i Bjørns instinkt, og den officielle dok bekræfter det skarpt:
- **Claude Code har INGEN blind timer-daemon.** Proaktivt arbejde trigges af **hooks**
  der fyrer på ÆGTE hændelser: `SessionStart`, `PostToolUse`, `PostEditFile`,
  `PreCompaction`, `TaskCreated/Completed`, `PermissionModeChanged` osv. Ikke "hvert N.
  minut" — men "da noget FAKTISK skete". (docs: code.claude.com/docs/en/hooks-guide)
- Hooks findes i tre former: **shell** (deterministisk), **prompt-baseret** (lille LLM),
  og **agent-baseret** (deleger til en subagent). Betinget via `if`-matchers.
- **Vigtig ærlig grænse:** hooks er PASSIVE — de kan ikke vække sig selv. Ægte
  selv-vækning kræver en separat planlægger (`/loop`, cloud-routines, OS-scheduler).
  Paradigmet: *"Events describe what changed; timers describe time passing."* Claude
  vælger det første.

→ Nuancen for Jarvis: Claudes hændelser er EKSTERNE (fil-redigeringer, tool-kald,
bruger-handlinger). Jarvis' mulighed er RIGERE: han kan være event-drevet på sin egen
INTERNE tilstand — når hans signaler faktisk rykker. Det er præcis det Bjørn sagde:
*"dine signaler er ægte."* Claude har ikke den slags indre signaler; Jarvis har dem
allerede. Så den rigtige syntese er ikke at kopiere Claudes eksterne hooks, men at lave
det Jarvis kan og Claude ikke kan: **hjerteslaget forbliver uret, men triggeren bliver
en DELTA på hans egne værdier** ("er autonomi-tryk steget markant siden sidst?"), ikke en
blind score-tærskel hvert 30. minut.

### 1.8 Klient-side loop: polling, proces-supervision, selv-vækning (det jarvis-code mangler)
Dette er morgenens tråd (Bjørn: *"han mangler i jarvis-code evnen til at polle for noget
og superviseret proces ligesom dig og self-wakeup… det har han server-side, men du gør det
i KLIENTEN"*). Det er samme wake-on-event-primitiv som råds-triggeren — bare anvendt på
processer i stedet for signaler. Sådan gør jeg det FAKTISK (første-hånd, i denne session):

- **Baggrunds-dispatch + vækning-ved-færdig.** Jeg starter en agent eller et shell-kald
  `run_in_background`. Processen kører detached. **Jeg kører IKKE imens** — modellen er
  bogstaveligt ikke invokeret mellem dispatch og færdig. Når den er færdig, gen-invokerer
  harness'en mig med en `task-notification` der bærer resultatet. → *"klienten vækker dig
  når en proces er færdig."* Præcis det du sagde. (Det har jeg gjort hele dagen: sendt
  agenter/bash i baggrunden, ikke brændt tokens mens de kørte, og reageret på notifikationen.)
- **Poll-uden-at-være-til-stede.** For ekstern tilstand harness'en ikke selv kan varsle
  (et build, en kø, en fjern-proces) enten et baggrunds-`until`-loop eller en planlagt
  vækning med valgt interval. Nøglen: jeg SOVER, jeg sidder ikke og brænder.
- **Klient-EJEDE tools.** Read/Write/Edit/Bash/Grep virker på den LOKALE maskine (Bjørns
  filer) — modsat Jarvis' server-side tools der virker på containeren. jarvis-code mangler
  netop denne klient-ejede lokale tool-eksekvering ([[project_jarvis_code_tui]] flagged det
  som udestående: "client-owned LOKAL tool-eksekvering — redigér Bjørns filer, ikke
  containerens").
- **Hooks = klient-side hændelser.** SessionStart injicerer kontekst ved opstart;
  PostToolUse/PostEditFile fyrer NÅR et tool/en redigering faktisk sker. Så tool-aktivitet
  er en hændelses-kilde på lige fod med signaler.
- **Superviseret proces uden at barnepige.** Dispatch → ikke-til-stede → vækket-ved-færdig
  → inspicér resultat → beslut næste. Det er en supervisor-løkke der ikke koster noget mens
  den venter.

**Hændelses-kilderne er altså TO slags (Bjørns "både signaler OG read/write-tools"):**
1. **Interne signaler** — Jarvis' egne værdier der rykker (det Claude ikke har).
2. **Tool-/proces-hændelser** — et read/write/bash eller en dispatchet proces der bliver
   færdig (det Claude har via PostToolUse-hooks + baggrunds-notifikationer).
Begge føder samme vække-mekanisme. Det er ÉT system, ikke to.

**Hvorfor det er "mega besparende" (Bjørns ord — og det er sandt):** du brænder ikke tokens
på at være til stede under langt arbejde; modellen invokeres kun når der ER noget at handle
på. Det er den DIREKTE modsætning til en daemon der tikker hvert 30. minut og brænder et
cheap-LLM-kald uanset om noget har ændret sig. Samme indsigt, to steder: råd SKAL være
vække-på-ændring, og klient-loopet SKAL være vække-på-færdig — begge sparer ved at være
fraværende indtil der er signal.

## DEL 2 — Hvorfor det er kraftfuldt OG simpelt

1. **Ét primitiv komponerer til alt.** Enkelt-opgave, parallel bredde, judge-panel,
   adversarial verify, pipeline — alt er "dispatch en konstrueret kontekst, få et landet
   resultat", arrangeret forskelligt. Ingen zoo af daemons og roller at vedligeholde.
2. **Ingen cadence, ingen faste roller, ingen tærskler.** Trigger = behov (vurderet).
   Roller = konstrueret pr. opgave. Det fjerner hele klassen af "kører blindt og
   producerer det samme".
3. **Output lander altid.** Returværdien går til den der kan handle. Intet
   push_initiative-og-dør.
4. **Kontekst-disciplin.** Agenter får præcis det de skal bruge; controllerens kontekst
   forbliver ren; hver agents ræsonnement er fokuseret. Det er BILLIGT fordi der ikke
   spildes kontekst — og token-effektivt fordi kald kun sker ved behov.

## DEL 3 — Den fulde afbildning til Jarvis (tag højde for det hele)

| Claude-primitiv | Jarvis i dag | Hul | Hvad skal bygges |
|---|---|---|---|
| Controller ER løkken | Council i skygge-daemon bag ham | Han er ikke til stede | Centralen skal være løkken (holder allerede de flydende værdier) |
| Spawn = vurdering | Fast tærskel 0.25 hvert 30. min | Blind termostat | Event-drevet: fyr når signaler FAKTISK ændrer sig markant; convene_judge (findes, shadow) er kimen |
| Konstrueret kontekst | derive_topic får signal-TAL | Kontekstløs | Fød med hans faktiske tanker + samtalen, ikke "autonomy:0.4" |
| Output lander | push_initiative → glemmes | Fabrik uden aftager | Nudge/væk Jarvis; HAN vurderer: tal med Bjørn / tag i råd / lad være |
| Struktureret retur | Prosa i kø | Ikke handlbart | Struktureret, handlbart resultat |
| Dynamiske roller | Låste Oracle/Architect/Critic | Navlepilleri-design | Roller konstrueret pr. opgave |
| Adgang efter opgave (tool-scoping) | Bygget: allowed_tools pr. dispatch + rolle-politikker + execute_tool-gate | Flag `agent_tools_enabled` OFF → agenter handløse | Aktivér i rækkefølge (§4.4): konvolut→allowlists→flip |
| Råd = fan-out+syntese | Separat council-motor | Dobbelt-system | Riv council-som-særsystem ned; råd = N agenter + syntese |
| Vække-på-hændelse | (server: heartbeat/daemons har det) | — | Behold server-side; genbrug som råds-trigger |
| Klient-side loop (poll/supervisér/selv-væk) | **jarvis-code mangler det HELT** | Klienten kan ikke polle/superviseres/vækkes | Byg klient-loop i jarvis-code: baggrunds-dispatch + vække-ved-færdig |
| Klient-ejede lokale tools | jarvis-code kører server-tools (containeren) | Redigerer forkert maskine | Client-owned Read/Write/Bash på Bjørns maskine ([[project_jarvis_code_tui]]) |

**To overflader, samme primitiv.** Redesignet er reelt TO forbundne ting drevet af samme
vække-på-hændelse-mekanik:
1. **Server-side (Jarvis' råd/agenter):** gør council event-drevet — vække-på-signal-ændring
   + ejet dispatch + output der lander, i stedet for blind 30-min-daemon.
2. **Klient-side (jarvis-code):** giv klienten det den mangler — polle uden at være til
   stede, supervisere en dispatchet proces, blive vækket når den er færdig, og klient-ejede
   lokale read/write/bash-tools (så den redigerer Bjørns filer, ikke containerens).
Begge hviler på: *vær fraværende (brænd intet) indtil en hændelse — signal ELLER
proces-færdig ELLER tool-aktivitet — kræver handling.*

### "Tag højde for det hele" — checklisten
- **Governance:** guard hænderne (handlinger), ikke sindet (hvem der må tænke). De
  eksisterende værn (source-confidence, reasoning-interceptor, merovingian) skal
  fortsætte med at gate HANDLINGER, ikke blokere at agenter tænker frit.
- **Kill-switch:** event-nudge + dispatch skal kunne slås fra via runtime-state uden deploy.
- **Visible vs autonom:** dette er autonom-lanen (flash-model). Rør ikke visible-økonomien.
- **Token-økonomi:** dette ER token-tråden. Event-drevet = langt færre kald; de frigjorte
  tokens går til agenter der arbejder. Overvåg via `jc cost` (nu live) — mål før/efter.
- **Heartbeat-integration:** nudge/vækning skal hænge på hjerteslaget uden at genindføre
  en blind cadence. Signalet skal være ÆNDRING, ikke tid.
- **Gamle fejl-tilstande at undgå:** handløse agenter (intet tools-array), menu-låst
  spawn, output-i-tomrum, faste roller. (Kilde: [[reference_agent_council_locked]].)
- **Eksisterende spec:** docs/specs/2026-07-03-agent-council-swarm-freedom.md siger dette
  allerede (status "færdig"); dele er bygget (convene_judge shadow, spawn_agent_task
  fleksibel). Dette dokument er FUNDAMENTET/reference-modellen den spec skal måles mod.
- **Dead-code-oprydning (Bjørns krav):** det GAMLE council/agent/daemon-system skal RYDDES
  når det nye lander — ingen død kode nogen steder. Kandidater: autonomous_council_daemon
  (fast-tærskel-gaten), de låste council-roller, push_initiative-tomrums-stien, evt.
  existential_wonder_daemon-cadencen. Byg-planen skal have et eksplicit retire/slet-trin med
  test af at intet call-site brækker (re-eksportér→ryd, Boy Scout).
- **Central-wiring (Bjørns krav):** ALT skal wires ind i Centralen — nye nerver/surfaces for
  event-trigger, dispatch, agent-udfald, robusthed-konvolut (status/usage), råds-resultater.
  Ingen ny silo. `jc`-surface + evt. central-CLI-fane. (Ledetråd: mange services er FRAKOBLET
  fra Centralen; [[reference_central_connectivity_map]] — undgå at tilføje endnu en.)
- **Tests/edges/docs (Bjørns krav):** TDD på hvert trin; edge-cases eksplicit dækket (agent
  fejler/timeout/tom retur/uventet; delta-tærskel-flapping; race på lease/dispatch; flag on↔off
  midt i en dispatch); docs opdateret (denne ref + spec + CLAUDE.md hvor relevant).

### Ærlige grænser — hvad Claude IKKE gør (så vi ikke overkopierer)
Krydstjek mod dok afslørede ting man kunne tro var der, men ikke er:
- **Ingen subagent-pooling/genbrug** — hver subagent er altid frisk. (Jarvis' persistente
  låste roller er faktisk MERE end Claude har — og det er en byrde, ikke en styrke.)
- **Statisk model-valg pr. agent** — ikke adaptivt. (Vi behøver ikke over-designe det.)
- **Ingen cost-bevidst spawn-beslutning i dok** — så vores `jc cost`-måling før/efter er
  vores egen tilføjelse, ikke noget vi kopierer.
- **Agent Teams (lead + teammates + delt task-liste + agent-til-agent-beskeder)** findes,
  men er EKSPERIMENTELT og slået fra by default med kendte resumption-grænser. Det er det
  tætteste på et "persistent råd" — men Anthropic selv holder det bag et eksperiment-flag.
  Lære: hold det simple fan-out+syntese-mønster; persistente team-strukturer er umodne.
- **"Panel"/"council" er IKKE en officiel term.** Vores råd-som-fan-out er et legitimt
  design-valg (bygget på judge-panel/adversarial-verify-mønstrene), ikke en kopi af en
  navngivet funktion. Det er fint — det betyder bare vi ejer designet.

## DEL 4 — Den KOMPLETTE værktøjskasse + robusthed-kontrakten (førstehånds audit)

Bjørn: *"gå gennem din egen toolbox først, der er sikkert mere end de 3 ting… intet må
fejle stille, der er taget højde for edges, agenten returnerer opgaven eller stopper ved
noget uventet, og sender ALTID tid og usage tilbage."* Her er hele maskineriet, læst fra
mine faktiske tool-skemaer i denne session — grupperet efter rolle.

### 4.1 Hele overfladen (ikke 3 ting — 15+)

**A. DISPATCH (start arbejde)**
- **Agent** — spawn en subagent (type, model, effort, isolation=worktree/remote,
  run_in_background). Baggrund default → notifikation ved færdig. Agentens SIDSTE besked =
  returværdi. SendMessage for at fortsætte; nyt kald = frisk.
- **Workflow** — deterministisk multi-agent-script (agent/parallel/pipeline/phase/log).
  Returnerer runId straks, notifikation ved færdig. Indbygget: struktureret schema-output,
  **budget-sporing** (budget.total/spent()/remaining()), concurrency-cap, resume.
- **Bash(run_in_background)** — detached shell; gen-invokerer mig ved exit.
- **Task-liste (TaskCreate/Get/List/Update/Stop)** — delt arbejdsliste med AFHÆNGIGHEDER
  (blocks/blockedBy), status (pending→in_progress→completed/deleted), owner. Substratet
  agenter koordinerer over.

**B. VENT/VÆK (vær fraværende indtil en hændelse)**
- **task-notification** — KERNEN. Fyrer når en baggrundsopgave stopper. Bærer: **status
  (completed/failed + exit-kode), summary, output-fil, OG usage: tokens, tool_uses,
  duration_ms.** Dvs. tid+usage kommer ALTID tilbage — det er selve konvolutten.
- **Monitor** — stream hændelser fra et script/WebSocket; hver stdout-linje = én event.
  Regel indbygget: filteret skal matche FEJL-tilstande, ikke kun success ("silence is not
  success"). Rate-limitet; firehose auto-stoppes.
- **TaskOutput** — hent output fra kørende/færdig opgave, blokerende el. ej (eksplicit poll).
- **ScheduleWakeup** — /loop: væk mig selv efter valgt interval (cache-vindue-styret).
- **CronCreate/List/Delete** — planlagte prompts (cron), fyrer når idle.
- **RemoteTrigger** — cloud-routines (claude.ai). (Claude-specifikt; Jarvis' analog =
  hans egen scheduler.)

**C. UNDERRET MENNESKET**
- **PushNotification** — desktop/telefon når noget kræver opmærksomhed / langt job færdigt
  mens væk. Err mod IKKE at sende.
- **SendUserFile / AskUserQuestion** — vis fil / stil blokerende beslutning.

**D. AGENT-TIL-AGENT**
- **SendMessage** — besked til anden agent (teammate el. "main"). Plain output er IKKE
  synligt for andre agenter — man SKAL bruge dette. Kanalen agenter koordinerer over.

**E. HOOKS (hændelses-triggere)**
- SessionStart, PostToolUse, PostEditFile, PreCompaction, Task Created/Completed,
  PreApprovalPrompt, PermissionModeChanged. Tre former: shell / prompt-LLM / agent-baseret.
  Betinget via `if`-matcher. (Set førstehånds i denne session: SessionStart injicerede
  kontekst; PostToolUse fyrede på MEMORY.md-størrelse.)

**F. TOOL-DISCOVERY (billig stor værktøjskasse)**
- **ToolSearch** — load tool-skemaer on-demand. Store værktøjskasser holdes billige ved
  IKKE at loade alt — man henter skemaet når man skal bruge det. (Jarvis' analog:
  tool-katalog-beskæring 128→8; [[reference_prompt_assembly_latency]].)

### 4.2 ROBUSTHED-KONTRAKTEN (det Bjørn kræver — modelleret på hvordan jeg faktisk opfører mig)

Fire invariante regler. Hvert dispatch i det nye system SKAL overholde alle fire.
> ⚠️ HÆRDET af rådet 13. jul: disse 4 regler validerer kun STRUKTUR. Se
> `2026-07-13-council-findings-synthesis.md` §2 for de 12 værn der skal med (hysterese,
> dead-man-timeout, budget-loft, idempotens, plausibilitet, subscriber-ack, rekursions-guard,
> gensidig udelukkelse …) — uden dem kan konvolutten stadig lyve eller trigge token-runaway.

1. **Struktureret konvolut ALTID retur.** Hvert kald (agent/råd/daemon) returnerer:
   `{status, tokens_in, tokens_out, cost_usd, duration_ms, tool_calls, result}`. Det er
   præcis task-notification-formatet. (Vi byggede allerede `record_cost` → cost+tokens
   fanges; udvid til den fulde konvolut pr. dispatch.) Ingen kald uden usage+tid.
2. **Fejl er HØJLYDT og TYPET — aldrig falsk success.**
   - Baggrundsopgave fejler → `failed`-notifikation med exit-kode (set i denne session).
   - Agent møder noget uventet → returnerer status **BLOCKED / NEEDS_CONTEXT /
     DONE_WITH_CONCERNS**, IKKE en opdigtet success (subagent-driven-development-kontrakten).
   - Workflow-trin kaster → elementet dropper til null, resten springes over — men droppet
     er SYNLIGT (filter+log). "No silent caps": bunder man dækning (top-N/no-retry), så log
     hvad der blev droppet.
   - Agent dør på terminal fejl efter retries → returnerer null (ikke hæng).
3. **Returnér-opgaven-eller-stop.** En agent der ikke kan færdiggøre RETURNERER opgaven
   (rapporterer blokeret) eller stopper — den fortsætter aldrig stille og digter ikke.
   Controlleren beslutter eksplicit: giv kontekst + re-dispatch / eskalér model / split /
   eskalér til Bjørn. Ignorér ALDRIG en eskalering; kør aldrig samme model igen uden at
   ændre noget.
4. **Intet er usynligt — hver sti er observerbar.** Hvert dispatch enten returnerer et
   resultat controlleren inspicerer, ELLER fyrer en notifikation. Controlleren bliver
   ALTID vækket og ser ALTID status+usage. Monitor-reglen: filteret skal fange fejl, ikke
   kun success. Usage er altid hæftet på → cost er altid synlig (via `jc cost`).

### 4.3 Hvorfor kontrakten dræber netop Jarvis' dræber-problem
Bjørn: *"signaler + LLM-kald per daemon er det der dræber os — signalerne er ægte men vi
koger token mange gange uden kontekst, selv om signalerne måske ikke ændrer sig længe."*
Kontrakten rammer hvert led:
- **Event-drevet, ikke timer** → LLM fyrer KUN når en signal-DELTA krydser tærskel. En
  billig NON-LLM delta-tjek kører på hjerteslaget; LLM'en rører kun ilden ved ægte ændring.
- **Idle = NUL brænd** → ændrer signalerne sig ikke i timevis, sker der NUL LLM-kald (mod
  nu: min. 48 kald/døgn på 30-min-timeren uanset hvad).
- **Kontekst-rig når den fyrer** → fød de faktiske tanker/samtale, ikke "autonomy:0.4".
- **Output lander** → struktureret konvolut tilbage til Jarvis, ikke push_initiative-og-dør.
- **Usage altid synlig** → hvert kald logget (record_cost, gjort) → ingen stille token-kogning.

Det er "et dispatch der bare spiller": fyrer kun på ægte hændelse, rapporterer altid
tid+usage, fejler aldrig stille, og idler gratis.

### 4.4 Tool-scoping til agenter (GROUND TRUTH: bygget korrekt, men flag OFF)
Verificeret i kode 13. jul. Spørgsmålet "får agenter fuld toolbox eller dispatcher vi
tools?" — svaret er: **vi dispatcher tools pr. agent, og mekanismen er allerede bygget rigtigt.**
- Hver agent har eksplicit **`allowed_tools`-allowlist pr. dispatch** (`allowed_tools_json`),
  trukket fra SAMME katalog som visible-lane (`get_tool_definitions`) → én sandhed, ingen drift.
  Tom allowlist → text-only. (`_build_agent_tools_payload`, agent_runtime_base.py:121.)
- Navngivne rolle-politikker: `none` / `read-only-runtime` / `can-spawn`.
- **Hvert tool-kald går gennem `execute_tool`** → rolle/scope + approval-gates håndhæves; en
  agent kan ALDRIG omgå godkendelse på risikable handlinger. Hænderne er governed.
- **MEN: flag `agent_tools_enabled` er OFF live** (default OFF, self-safe). Så agenter er lige
  nu text-only (handløse) trods bygget mekanisme. (Forener de to gamle noter: wired MEN flag-off.)
- **Sekvens (robusthed før hænder):** (1) byg robusthed-konvolutten (§4.2) → (2) definér
  rolle-allowlists (searcher=read-only, builder=fuld+approval, som Claudes typer) → (3) FLIP
  `agent_tools_enabled` on. Aldrig flip før konvolutten fanger alt — ellers handler agenter usynligt.
  Tool-scoping skal altså ikke BYGGES (den er der); den skal aktiveres i rigtig rækkefølge.

## Åbne spørgsmål til afklaring før byg
1. Skal event-nudgen kunne VÆKKE Jarvis (skrive til ham/Bjørn proaktivt), eller kun lægge
   en markør han ser næste gang han er aktiv?
2. Hvad tæller som "signalet ændrede sig markant nok"? (delta-tærskel pr. signal? sammensat?)
3. Skal rådet stadig kunne selv-indkalde til det eksistentielle, eller kun on-demand-efter-grund?
