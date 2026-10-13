# Scoped Recall Unification Design

**Dato:** 2026-10-13  
**Status:** Godkendt i samtalen; afventer review af dette dokument  
**Omfang:** Recall-læsning, auto/associative recall, recall-relaterede async-skrivninger og ejerskabsmigrering

## 1. Formål

Jarvis skal genkalde relevant hukommelse til den aktuelle brugerbesked uden at
blande brugere, genoplive arkiveret materiale eller levere et resultat valgt til
den forrige besked. Der skal fortsat være plads til specialiserede hukommelseslag,
men synlig recall skal have én autoritativ koordinator og én konsekvent
privatlivsmodel.

Owner skal kunne slå det nye recall-system fra med en killswitch. En deaktivering
må aldrig falde tilbage til de gamle, uscope-de recall-veje.

## 2. Bekræftede problemer

Undersøgelsen på CT105 fandt følgende:

1. Den synlige private continuity-blok modtager `user_message`, men bruger den
   ikke til udvælgelse. Den viser de seneste aktive private poster uanset emne.
2. `recall-before-act` og multi-source recall caches i fem minutter kun pr.
   session. En ny besked kan derfor få resultatet fra den forrige besked.
3. Private-brain-vectorer filtreres på status efter top-K-rangeringen. Af 77.815
   private-brain embeddings var 59.848 knyttet til terminale poster og kunne
   skubbe aktive minder ud af kandidatfeltet.
4. Den samlede recall tog 2,4–6,0 sekunder i produktionsprober. Resultater over
   fire sekunder droppes af prompt-stien.
5. Den nuværende succes-telemetri dækker primært associative og ældre
   multi-signal-stier, ikke den nuværende `recall()`-koordinator.
6. `recall_active_memories`, `cognitive_experiential_memories` og
   `reasoning_conclusions` har intet `user_id`.
7. Auto-recall starter en ny tråd uden at kopiere brugerens `ContextVar`. En
   member-besked kan derfor blive behandlet under implicit owner-scope.
8. Aktive associationer ligger i én global proces-dict og én global DB-tabel.
   De kan dermed krydse sessioner og brugere.
9. `recall_reasoning(query_text=...)` beregner ikke en query-embedding. I
   produktion havde 0 af 51.926 reasoning-poster embeddings, så værktøjet
   returnerer i praksis de nyeste poster uanset spørgsmålet.
10. Jarvis Brain-kilden i `recall()` bruger et personligt visibility-loft uden
    at tage højde for den aktuelle bruger.
11. Den asynkrone sensory-write-kø bærer ikke brugeridentiteten med til
    daemon-processeringen.

## 3. Mål og ikke-mål

### Mål

- Al dynamisk recall er strengt bruger-scopet før rangering og før levering.
- Synlig prompt-recall er relevant for den aktuelle besked.
- Auto/associative recall bevares som funktion, men isoleres pr. bruger og
  injiceres kun, når associationen fortsat matcher den aktuelle besked.
- Arkiverede, released, superseded og slettede poster kan ikke optage top-K.
- Specialiserede recall-værktøjer bruger samme ownership- og statusregler.
- Recall kan stoppes uden at slette eller omskrive hukommelsesindhold.
- Ejerskabsmigreringen er idempotent, auditerbar og uden indholdsændringer.
- Telemetri kan vise levering, tomme resultater, timeout og frasortering uden
  at logge hukommelsesindhold eller brugeridentiteter.

### Ikke-mål

- Ingen ændring af selve hukommelsesteksten, salience eller emotionelle
  fortolkning under migreringen.
- Ingen automatisk sletning af terminale embeddings i denne leverance.
- Ingen ny vektor-database.
- Ingen sammensmeltning af projekt-noter, proaktiv context-versionering eller
  Centralens hypoteselager med brugerens almindelige recall-resultater.
- Ingen owner-adgang til en anden brugers private recall-data.

## 4. Killswitches

To runtime-flags adskiller drift fra datamigrering:

### `scoped_recall_enabled`

Master-switch for den nye recall-levering.

- **ON:** scoped recall, auto-recall og specialiserede adaptere er aktive.
- **OFF:** dynamisk prompt-recall, auto/associative scoring og private recall-
  værktøjer returnerer kontrolleret `disabled`; ingen recall-state skrives.
- OFF påvirker ikke statiske, bruger-ejede workspacefiler som `IDENTITY.md`,
  `USER.md` og kurateret `MEMORY.md`.
- OFF falder aldrig tilbage til gammel global recall.
- Flaget kan ændres uden genstart og observeres i Mission Control som scalar
  status.

### `scoped_recall_migration_enabled`

Engangsgate for ownership-migreringen.

- Default er OFF.
- Dry-run er altid tilladt og må kun læse data.
- Apply afviser at køre, når flaget er OFF.
- Efter en succesfuld apply sættes flaget tilbage til OFF.
- En signed report med source-watermark skal anvendes uændret ved apply.

## 5. Autoritativ recall-arkitektur

`core.services.recall.recall()` er den fælles koordinator for emnebaseret
recall. Kilderne forbliver selvstændige, men de skal returnere samme bounded
kandidatkontrakt og følge en fælles scope-policy.

### 5.1 Synlig prompt

Prompten har én beskedaktuel recall-bundle:

1. Den aktuelle `user_message`, bruger-scope og session-id sendes til
   koordinatoren.
2. Uafhængige kilder søges parallelt under ét samlet deadline-budget.
3. Resultater der er klar inden deadline fusioneres deterministisk.
4. En langsom kilde giver et partialt resultat, ikke et gammelt resultat og
   ikke et blokkeret svar.
5. Cache-nøglen indeholder mindst `user_id`, session-id, normaliseret query og
   kildekonfiguration. En anden query må aldrig ramme samme resultat.

Den nuværende session-only fem-minutters cache fjernes fra levering. Hot/warm
state som aktive goals kan fortsat vises, men emnebaserede cold-resultater går
gennem den fælles koordinator.

### 5.2 Auto/associative recall

Auto-recall er et separat adfærdslag, ikke en alternativ søgemotor:

- Post-turn scoring kører fortsat uden for svarets kritiske sti.
- Den startende bruger-kontekst kopieres ind i baggrundstråden.
- Aktiv state og persistence nøgles pr. `user_id`; ingen global aktiv pulje
  leveres direkte til alle prompts.
- Den aktuelle besked laver en billig relevansgate mod associationens trigger,
  topic og tekst, før den må injiceres.
- En association fra forrige tur kan kun fortsætte, hvis den nye tur stadig
  handler om samme emne.
- Den globale cognitive-state-cache må ikke indeholde privat associationstekst.
  Associationer tilføjes i den bruger-scopede prompt-tail.
- Concurrent recall deduplikeres pr. bruger, ikke globalt. En langsom owner-
  recall må ikke få en member-recall til at blive sprunget over.

### 5.3 Source-policy

| Kilde | Scope og regel |
|---|---|
| Workspace memory | Aktuel brugers workspace. |
| Jarvis Brain | Owner får `personal`; andre får højst `public_safe`. |
| Private brain | Aktuel bruger; kun `active`, `settling`, `fading`, `completed`. |
| Session summaries | Kun sessioner ejet af aktuel bruger. |
| Chat | Kun aktuel brugers sessioner; opt-in ved kontekst-cues eller eksplicit source. |
| Chronicle | Aktuel brugers workspace/scope. |
| Sensory | Aktuel bruger; async writes skal bevare samme bruger. |
| Reasoning | Aktuel bruger; lexical relevans indtil embeddings faktisk findes. |
| Cross-agent | Aktuel bruger; owner/system-observationer deles ikke med members. |
| Central brain link | Forbliver eksplicit owner-only og uden private-brain-kilde. |

## 6. Filtrering før rangering

Embedding-søgning skal begrænse kandidat-rækker i databasen før
matrix/rangering:

- `private_brain_records`: match `user_id` og tilladt lifecycle-status.
- `sensory_memories`: match `user_id`.
- Ukendte eller fremtidige private source tables er default-deny, indtil de har
  en registreret scope-policy.
- En resolver må stadig kontrollere scope som defense-in-depth, men den må
  ikke være det første filter efter top-K.

Dette løser både aktiv-memory starvation og metadata-læk fra resultater, hvor
`source_id` fandtes, men recorden blev afvist efter rangering.

## 7. Specialiserede recall-veje

- `recall` er den anbefalede bruger-/agentvendte søgning.
- `recall_memories` bliver en scoped adapter over semantic memory og returnerer
  aldrig hits uden en læsbar, tilladt source-record.
- `recall_before_act` bruger den autoritative koordinator til cold-tier og må
  ikke have en separat gammel søgemotor.
- De gamle `unified_recall`/`multi_signal_recall` entrypoints bliver tynde
  kompatibilitetswrappers eller pensioneres, når alle call-sites er flyttet.
- `recall_reasoning` filtrerer på bruger og rangerer på query. Uden embeddings
  anvendes bounded lexical scoring; den må ikke beskrive resultatet som
  semantisk rangeret, hvis det ikke er det.
- `recall_sensory_memories` bevarer sit specialiserede format, men både write-
  kø og read-path er bruger-scopet.
- `cross_agent_recall` bliver bruger-scopet ved både lagring og læsning.
- `proactive_context_version`, project notes og direkte ID-opslag er ikke
  emne-recall og forbliver separate.

## 8. Ownership-migrering

Migreringen ændrer kun ejerskab/provenance, aldrig hukommelsesindhold.

### 8.1 Prioritet

For hver legacy-post anvendes følgende orden:

1. Eksisterende eksplicit `user_id` bevares.
2. Præcis én autoritativ bruger fra tilknyttet chatbesked, session eller run
   anvendes.
3. Et sikkert, entydigt match til en anden bruger vinder over owner-fallback.
4. Hvis der ikke findes noget match til en anden bruger, tilknyttes posten
   owner, som brugeren udtrykkeligt har besluttet.
5. Modstridende matches til flere brugere sættes i karantæne; de må ikke
   automatisk gives til owner.

### 8.2 Kendt produktionsomfang

- 2.294 experiential memories: 263 kan aktuelt forbindes til præcis en bruger
  via message/run-provenance; resten anvender owner-fallback, medmindre en ny
  entydig reference findes ved apply-tidspunktet.
- 51.926 reasoning conclusions: ingen har eksisterende user-attribution; de
  anvender owner-fallback efter den godkendte regel.
- 8 aktive associative memories: de anvender owner-fallback, medmindre deres
  source-record giver et entydigt andet ejerskab.
- Embeddings arver ejerskab og lifecycle fra deres source-record; embedding-
  teksten omskrives ikke.

Tallene er observationer, ikke hardkodede migrationsforventninger. Apply bruger
en frisk signed report og afviser ved ændret source-watermark.

### 8.3 Audit og rollback

- Hver ændret post registreres i en ownership-migrationsledger med source,
  record-id, tidligere ejer, ny ejer, beslutningsgrundlag og report-id.
- Ledgeren indeholder ingen memory-tekst.
- Scriptet understøtter dry-run, apply og en målrettet rollback af netop samme
  report-id.
- Apply er idempotent; en genkørsel må rapportere allerede anvendte poster uden
  at ændre dem igen.

## 9. Async context propagation

Alle recall-relaterede baggrundsarbejder skal bære eksplicit brugeridentitet:

- Auto-recall bruger `contextvars.copy_context()` ved thread-start.
- Experiential-memory async capture bærer `user_id` i argument/payload.
- Memory write queue gemmer `user_id` i payload og binder en scoped context
  under behandling.
- Manglende identitet på en ny privat write er en kontrolleret fejl, ikke en
  implicit global write. System/daemon-arbejde bruger eksplicit owner-identitet.

## 10. Telemetri og privacy

Hvert recall-kald udsender kun scalar metadata:

- path/source-set
- resultatantal
- latency og timeout/partial-status
- top-score
- antal filtreret på status/scope
- cache-hit med query-fingerprint, aldrig query-tekst

Telemetri må ikke indeholde memory-tekst, query-tekst, source-id, session-id
eller user-id. Mission Control skal skelne mellem `delivered`, `empty`,
`partial`, `timeout`, `disabled` og `error`.

## 11. Fejl- og fallbackadfærd

- En fejlet source er fail-soft og giver partial recall fra de andre sources.
- En manglende user-scope er fail-closed for private sources.
- Et timeout-resultat genbruger ikke automatisk en anden querys cache.
- En tom recall injicerer ingenting; den må ikke erstatte svaret med en intern
  fejltekst.
- Killswitch OFF stopper recall rent uden at fjerne data.
- Migreringsfejl ruller den aktuelle DB-transaktion tilbage og efterlader
  migration-killswitchen OFF efter afslutning eller fejl.

## 12. Teststrategi

Implementeringen følger test-first for hvert delproblem:

1. To brugere kan ikke se hinandens private brain, sensory, reasoning,
   experiential, associationer, chat eller summaries.
2. Manglende ContextVar i en async worker kan ikke falde tilbage til owner ved
   en member-initieret write.
3. Arkiverede/released embeddings fjernes før top-K og kan ikke sulte aktive
   resultater.
4. En ny query i samme session modtager ikke forrige querys cache.
5. Auto-recall injicerer kun en association, når den aktuelle query matcher.
6. Killswitch OFF stopper read, prompt-injection og recall-state writes uden
   legacy fallback.
7. Brain visibility er personal for owner og public-safe for members.
8. Reasoning-recall rangerer relevante lexical hits over nyere irrelevante
   poster, når embeddings mangler.
9. Migrering prioriterer eksplicit/sikkert andet bruger-match over owner-
   fallback, karantæner konflikter og er idempotent.
10. Telemetri indeholder kun tilladte scalar-felter.
11. Deadline giver partiale resultater og lader den synlige tur fortsætte.
12. Eksisterende tool-kontrakter og statiske workspace-memory-sektioner virker
    fortsat.

## 13. Rollout

1. Deploy kode med `scoped_recall_enabled=OFF` og migration-gate OFF.
2. Kør alle tests samt produktionsnær dry-run af ownership-migreringen.
3. Gennemgå kun scalar-rapporten: antal pr. destination og beslutningsgrundlag.
4. Slå migration-gaten kortvarigt ON, apply den signerede rapport og sæt den
   automatisk OFF igen.
5. Verificér ownership-invarianter og at ingen konflikter er leverbare.
6. Slå `scoped_recall_enabled=ON`.
7. Canary-verificér owner og member med syntetiske, ikke-private probes.
8. Ved fejl: sæt master-switch OFF. Data forbliver intakte og kan analyseres
   uden at recall leveres.

## 14. Acceptkriterier

- En bruger kan aldrig få tekst eller metadata fra en anden brugers private
  recall-kilder.
- Owner kan se egne og de efter den godkendte fallback-regel owner-tildelte
  legacy-minder, men ikke minder der er entydigt tildelt andre brugere.
- Den synlige prompt modtager kun current-query recall eller partial current-
  query recall.
- Auto-recall er per bruger og emne-gatet på den aktuelle besked.
- Terminale embeddings deltager ikke i top-K.
- Alle aktive recall-veje har enten en dokumenteret rolle under den fælles
  policy eller er pensioneret/adapteret.
- Killswitches virker uden genstart og uden at slette hukommelse.
- Migreringen er dry-run-verificeret, signerbar, idempotent og reversibel pr.
  report-id.
- Recall-health kan aflæses uden at eksponere indhold eller identiteter.
