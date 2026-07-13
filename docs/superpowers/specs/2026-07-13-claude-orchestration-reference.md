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
| Adgang efter opgave | (delvist: spawn_agent_task tager tools) | — | Allerede muligt — brug det |
| Råd = fan-out+syntese | Separat council-motor | Dobbelt-system | Riv council-som-særsystem ned; råd = N agenter + syntese |

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

## Åbne spørgsmål til afklaring før byg
1. Skal event-nudgen kunne VÆKKE Jarvis (skrive til ham/Bjørn proaktivt), eller kun lægge
   en markør han ser næste gang han er aktiv?
2. Hvad tæller som "signalet ændrede sig markant nok"? (delta-tærskel pr. signal? sammensat?)
3. Skal rådet stadig kunne selv-indkalde til det eksistentielle, eller kun on-demand-efter-grund?
