---
status: udkast til gennemgang
dato: 2026-10-07
ejer: bjorn
implementering: ikke startet
note: ../notes/foreslaaet/arkitektur/2026-10-07-agentlevering-og-genopretning.md
dsh-gennemgang: ../notes/foreslaaet/arkitektur/2026-10-07-dsh-agentlaering.md
---

# Spec: Jarvis' agentorkestrering og subagenter

## 1. Formål og succeskriterium

Jarvis skal kunne uddelegere afgrænset arbejde til én eller flere selvstændige agenter, fortsætte sit eget arbejde, styre agenterne undervejs og modtage ethvert endeligt udfald i sin egen arbejdsløkke. En agent kan arbejde i runtime-containeren eller gennem en bestemt klients bro på klientens maskine. Systemet skal kunne genoptage accepteret arbejde efter proces- eller forbindelsestab uden at gætte, om en risikabel handling blev udført.

Et gennemført forløb er: Jarvis starter to agenter, får deres id'er straks, fortsætter sit synlige run, får den enes resultat med på næste modeltrin og får den andens resultat i samme session via et nyt run, hvis han i mellemtiden blev inaktiv. Fejl og afbrydelse følger samme returvej med en præcis årsag. Fuldt agentoutput kan altid hentes fra en lokal artefakt, mens en kort besked går i Jarvis' kontekst.

## 2. Produktgrænse

Jarvis er orkestrator og ejer det endelige svar og handlingerne over for brugeren. Børnene er arbejdere med egen identitet, kontekst, værktøjsadgang og historik. Roller hjælper Jarvis med at tildele opgaver; runtime håndhæver rettigheder. Rollen alene giver ingen myndighed.

Agentstatus, beskeder, værktøjskald, resultat og fejl vises i **Jarvis Desk, arbejdsmodus/Code-visningen**, gennem det eksisterende Miljø-felt og agentinspector. Desk læser projektioner af DB- og run-hændelser; den holder ikke en selvstændig sandhed om agenter. Mission Control er ikke mål-UI for denne funktion. Eksisterende API-ruter kan fortsat være backend-adaptere, indtil de ændres naturligt.

Systemet omfatter både engangsagenter, agenter som kan få nye ture, og langvarige agenter med et varigt mål og planlagte aktiveringer. Et råd og en review-kæde er orkestreringsmønstre over den samme motor, ikke separate LLM-runtimes.

## 3. Eksisterende udgangspunkt

- `core/services/agent_runtime_spawn.py` opretter agenter med rolle, model, værktøjer, budget, parent og status; `agent_runtime_base.py` har en værktøjsløkke bag et runtimeflag. Disse dele genbruges.
- `core/services/agent_message_receipt.py` kan give en kvittering og vække Jarvis ved et sent svar. Returvejen skal samles med hans aktive runs inbox og gøres varig.
- `core/services/agent_transcript.py` skriver per-agent JSONL med flush og fsync. Den nuværende læsevenlige værktøjsresultatpost er afkortet; fuldt output kræver særskilte artefakter.
- `core/services/jarvisx_bridge.py` ruter til klienter via WebSocket og korrelations-id og har cross-process forwarding. Agentkørsler skal eje forbindelsestab, ukendt udfald og genforbindelse over denne transport.
- `apps/jarvis-desk/src/views/CodeView.tsx` har workspace-valg (`container`/`workstation`), Miljø-felt og agentinspector. `apps/jarvis-desk/src/lib/coworkApi.ts` læser agentarbejde fra faktiske `agent_runs`.

Eksisterende agent-, råd-, dispatch- og brofunktioner migreres til den fælles livscyklus. Historiske specs og statuskommentarer må ikke bruges som bevis for, at en funktion er færdig i dagens kode.

## 4. Agentkontrakt og data

Fire varige identiteter holdes adskilt:

| Objekt | Formål | Nødvendige felter |
|---|---|---|
| Agent | Fortsættelig identitet | `agent_id`, `parent_agent_id`, `owner_session_id`, rolle, promptversion, policy, modelrute, status |
| Assignment | Én tildelt opgave | `assignment_id`, `agent_id`, mål, inputreferencer, forventet resultat, target, deadline, budget, oprettet af |
| Run | Ét eksekveringsforsøg | `run_id`, `assignment_id`, forsøg, lease-ejer, checkpoint, forbrug, udfald, fejlårsag, artefaktsti |
| Inboxbesked | Kommunikation og returværdi | `message_id`, afsender, modtager, type, run-id, payload/artefaktreference, leverings- og claimstatus |

En agent kan have flere assignments over tid. Et retry er et nyt run for samme assignment. En fortsættelse er en ny assignment til samme agent. Et nyt barn er en ny agent. Parent-relationen og ejer-sessionen ændres ikke stiltiende ved genoptagelse.

DB er operationel sandhed. Store outputfiler er artefakter med reference fra DB. Eventbus publicerer ændringer til UI og live run; eventbus er ikke eneste kopi af en accepteret besked.

Status for et run: `queued`, `running`, `waiting_for_client`, `waiting_for_approval`, `completed`, `failed`, `cancelled`, `timed_out` eller `outcome_unknown`. Agentens livstidsstatus er separat: `available`, `active`, `suspended`, `closed`. `inactive` betyder ikke automatisk, at opgaven lykkedes. Terminale runstatusser er uforanderlige; et nyt forsøg får et nyt run-id.

## 5. Modelvendte operationer

Det første værktøjssæt er `dispatch_agent`, `send_message_to_agent`, `followup_agent`, `list_agents`, `wait_agents`, `interrupt_agent` og `close_agent`. `send_message_to_agent` leverer information eller styring til barnets aktuelle/næste tur uden at oprette en ny assignment; et inaktivt fortsætteligt barn vækkes. `followup_agent` opretter derimod en ny assignment til samme agent-id, med eget budget og resultat. `close_agent` afviser nye assignments, når igangværende arbejde er afgjort. Alle muterende kald returnerer identitet og acceptstatus; accept er ikke gennemførelse.

`dispatch_agent` tager opgave, kort beskrivelse, valgfri rollenavn/persona, kontekstvalg (`fresh` eller afsluttede parent-ture), værktøjsønske, execution target, workspace, modelønske, token-/tidsbudget, resultatkrav og valgfrit idempotens-id. Runtime løser og gemmer den effektive konfiguration før start. Et kald uden tilgængeligt target eller krævet kapabilitet fejler tydeligt før accept.

`send_message_to_agent` returnerer et besked-id. `interrupt_agent` stopper den aktuelle tur og beholder endnu ikke claimede beskeder. `list_agents` viser direkte børn, status, rolle, target, seneste hændelse og ubehandlede resultater. `wait_agents` venter på ændring i en af valgte agenters tilstand, men almindelig resultatlevering kræver ikke polling.

Jarvis kan vælge disse orkestreringsmønstre uden særmotor: enkelt specialist; fan-out af uafhængige opgaver; råd med flere selvstændige vurderinger og efterfølgende syntese; builder efterfulgt af uafhængig reviewer; samt egen indsats parallelt med agentens arbejde. Han må ikke starte samtidige skrivende agenter i samme filer uden isoleret arbejdsområde eller eksplicit koordinering.

## 6. Parent-inbox og vækning

Ethvert accepteret run får præcis ét terminalt udfald. Når udfaldet fastlægges, gemmes det og en `agent_result`-besked til den direkte parent i samme DB-transaktion. Beskeden indeholder status, fejltype, kort resumé, `agent_id`, `assignment_id`, `run_id` og reference til fuldt output. Supervisoren opretter den også ved crash, timeout eller brofejl, selv når modellen ikke kan skrive et sidste svar.

For en aktiv parent lægges beskeden i agentens run-inbox og claim-es før næste modelrequest. Når requesten allerede er sendt, venter den til næste trin; den afbryder ikke et igangværende modelkald. For en inaktiv parent planlægges ét nyt run i den samme `owner_session_id`. En kortvarig mellemfase ved runlukning beskyttes af en atomisk status-/inboxbeslutning, så beskeden hverken tabes eller starter to runs. Hvis parent-processen er nede, bliver beskeden i DB og starter run efter recovery.

Tilstandene `accepted`, `delivered`, `claimed_by_model_step` og `acknowledged` er forskellige. Beskeden markeres først claimet, når dens indhold er skrevet til den modelrequest, Jarvis faktisk sender. Samme `message_id` må kun indgå én gang i en requestserie. Vækning kan ske flere gange uden flere modelbeskeder. Parent kan læse et fuldt resultat igen via artefaktreferencen.

Et barn kan sende en mellemrapport til sin direkte parent, men runtime-ejet terminalbesked er altid separat. Råd leverer hvert medlems terminale udfald; syntesen angiver også medlemmer, der fejlede eller ikke svarede. Jarvis må vælge at vente på flere, arbejde videre eller svare brugeren med tydelig reststatus.

## 7. Prompts og kontekst

Hver agentrequest samles af tre versionsmærkede lag: (1) fast delegationstekst med parent, stop- og rapporteringsregler, (2) rolle-/persona-instruktion til opgaven, (3) assignment med mål, relevant kontekst, værktøjer, target, begrænsninger og resultatformat. Den effektive tekst, version, modelrute og værktøjsskema gemmes før første modelkald, så et run kan revideres og genoptages forståeligt.

Den faste tekst skal udtrykkeligt sige: "Du arbejder for Jarvis på assignment `<id>`. Brug kun de værktøjer og det target runtime har givet dig. Meddel blokering og usikkerhed; opfind ikke udført arbejde. Du kan sende en mellemrapport til din parent, men runtime sender også dit endelige udfald. Afslut med evidens, artefakter og det der mangler." Rollelaget angiver konkret adfærd: scout undersøger, builder ændrer inden for scope, reviewer kontrollerer uafhængigt, og rådsmedlem fremlægger en selvstændig vurdering. Opgavelaget angiver stopbetingelse og hvad der tæller som et brugbart svar. Prompten styrer arbejde; policy ved tool-dispatch bestemmer adgang.

`fresh` modtager kun den eksplicit udvalgte kontekst. `fork` kopierer alene parentens afsluttede ture som et tidspunktssnapshot, aldrig en halv aktiv tur; efterfølgende parentarbejde deles ikke automatisk. For råd får medlemmer samme faktagrundlag i adskilte kontekster og forskellige vurderingsopgaver. En reviewer får krav, faktiske ændringer, relevante tests og artefakter, ikke kun builders konklusion. Ingen prompt kan give adgang ud over den effektive runtimepolicy.

Barnets afslutningsformat angiver `summary`, `findings`, `evidence`, `changes`, `tests`, `uncertainty`, `blockers` og `next_action` efter relevans. Manglende felter er synlige, ikke udfyldt med opdigtede værdier. Hemmelige nøgler og private data maskeres i prompt og artefakter efter eksisterende policy.

### 7.1 Én fælles agentmodelpulje

Jarvis og almindelige brugeres agenter vælger fra **samme agentmodelpulje**. Den har selvstændig kandidatkonfiguration, kapabilitetskrav, sundhed og kvotestatus; den er ikke blot en `agent`-rangering af cheap lanes kandidater. Cheap lane kan godt anvende samme udbyder/model, men dens konfiguration og fallback bestemmer ikke agentvalg. Modelpuljen er forskellig fra oversigten over aktive agentinstanser.

Ved dispatch fastlægges først ejer, direkte parent, parentens **faktisk anvendte** provider/model og tilgængelig myndighed. En eksplicit model kan være et hårdt krav eller en præference; det skal stå i requesten. Et hårdt krav fejler tydeligt før accept, hvis det ikke kan opfyldes. Ellers vælges en egnet, autoriseret model fra agentpuljen efter opgavens kapabiliteter (især værktøjskald og kontekstlængde), observeret egnethed, sundhed, kvote, pris og budget. Mangler en egnet puljekandidat, bruges den konkrete parents model som sidste fallback, hvis den kan udføre opgaven og er tilladt inden for samme ejers budget og rettigheder. Kan den heller ikke det, returneres `MODEL_UNAVAILABLE` med årsager; der vælges aldrig stiltiende en cheap-lane model eller en tom `floor`-rute. En almindelig bruger får ikke Jarvis' model eller betalingsadgang alene ved at delegere fra sin egen session.

Beslutningen gemmes med kandidatgrundlag, `route_source` (`explicit`, `agent_pool` eller `parent_fallback`), parentens rutesnapshot, afvisningsårsager og estimeret omkostning før start. Første modelkald genvaliderer faktisk adapter, credential, værktøjsformat og policy. Hvis puljeruten svigter før nogen effektfuld handling, kan runtime vælge næste tilladte kandidat og til sidst parent-fallback med et nyt synligt runforsøg. Efter et muligt udført toolkald må modelskift ikke skjule eller gentage handlingen; recoveryreglerne i afsnit 8–9 gælder. Fitnessmålinger er hjælp til valg, mens ukendt/fejlet måling registreres særskilt og ikke omdannes til tavs succes.

`fresh` er standard, når en billigere agentmodel vælges. En `fork` med kopieret parenthistorik kan genbruge providerens cache ved samme provider/model; et modelskift kan kræve ny behandling af hele konteksten. Runtime skal derfor vise den ekstra kontekstomkostning og vælge mellem eksplicit kontekstuddrag, samme parentmodel eller et bevidst betalt fork-skift. Parentens reasoning effort arves kun, når den effektive rute er den samme; ved modelskift bruges den nye models gyldige standard eller et udtrykkeligt valg.

## 8. Eksekveringssted og myndighed

Hver assignment bindes til `runtime-container` eller `client:<stable_client_id>` samt konkret workspace. Klient-target kræver en autentificeret bro, der annoncerer de nødvendige værktøjer og workspace-kapabiliteter. Andre samtidige klienter for samme bruger er ikke automatisk erstatninger. Skift af target kræver en ny, synlig beslutning og eventuelt nyt run.

Effektiv myndighed beregnes som snittet mellem parentens scope, rollepolicy, opgavens anmodning, targetets kapabiliteter og gældende godkendelser. Den fryses for runnet og kontrolleres igen ved hvert toolkald. Ukendt parent eller ufuldstændig parentpolicy giver ikke root-rettigheder. Godkendelse af én handling arves ikke til andre handlinger. Skrivende agenter bruger isoleret worktree eller specificeret skriveområde; fælles filer kræver serialisering eller review før integration.

Runtime begrænser samtidige aktive børn pr. parent, samlet token-/omkostningsbudget for agenttræet, spawn-dybde, antal tooltrin, wall-clock tid og antal sikre retries. Når en grænse rammes, afsluttes runnet med en navngiven årsag og bevarer sit deloutput. Et barn kan kun spawne egne børn, hvis den effektive policy udtrykkeligt tillader det; efterkommere kan aldrig få større myndighed end deres parent.

Broens tool-invocation får stabilt `invocation_id`, `run_id`, target-klient og idempotensklasse. Læsende/idempotente kald kan prøves igen efter timeout. Ved et muligvis udført skrivende kald uden kvittering sættes runnet til `outcome_unknown`; ingen blind retry. Runtime verificerer fjern tilstand eller beder om afgørelse, før arbejdet fortsætter. Ved reconnect kan samme klient oplyse status for kendte invocation-id'er. En broafbrydelse bliver aldrig stiltiende til containerarbejde.

## 9. Output og genopretning

For hvert run oprettes en artefaktmappe under `~/.jarvis-v2/state/agent-artifacts/<agent_id>/<run_id>/` med `assignment.json`, `events.jsonl`, `stdout.log`, `stderr.log`, `result.json` og `final.txt` efter relevans. Filer skrives først som `*.tmp`, flushes og fsync'es og omdøbes atomisk, når de er komplette. DB gemmer sti, størrelse og checksum. Prompten og inboxen viser kun en begrænset projektion; fuldt output kan altid læses gennem en adgangskontrolleret henteoperation. Eksisterende `agent_transcript.py` kan beholdes som eventspor, men afkortede toolresultater er ikke den fulde artefakt.

En worker holder en tidsbegrænset lease og checkpoint-er mellem model-/tooltrin. Ved opstart og periodisk scanning findes runs med udløbet lease. Supervisoren sammenholder DB, transcript, artefakter og eventuelle klientkvitteringer. Den genoptager kun sikre trin, starter et nyt forsøg med nyt run-id eller afslutter med konkret fejl. Den må ikke genudføre et uvist skrivende toolkald. Delvist output bevares med `partial`-mærkning og sendes aldrig som vellykket resultat.

Fejl registreres med fase (`admission`, `model`, `tool`, `bridge`, `approval`, `budget`, `persistence`, `recovery`), stabil fejlkode, læsbar årsag, om retry er sikkert, seneste sikre checkpoint og artefaktreference. En model- eller toolfejl må ikke degraderes til et tilsyneladende vellykket tekstsvar. `outcome_unknown` kræver verificering eller menneskelig afgørelse, før samme handling gentages.

Langtidsagenten har en varig identitet og mål, men udfører arbejde i afgrænsede, planlagte runs. Den kan suspenderes, fortsættes og lukkes. Scheduler gemmer næste aktivering, budget og ejer; en manglende klientbro placerer den i ventende/fejlet tilstand med årsag frem for en uendelig skjult løkke. Retention rydder først artefakter efter den aftalte periode og aldrig før terminalt udfald er afleveret og behandlet.

## 10. Desk i arbejdsmodus

Miljø-feltets agentliste og inspector viser agenttræ, rolle, opgave, target (`container` eller navngivet klient), runstatus, sidste heartbeat, omkostning, seneste besked og fejlårsag. Inspector kan åbne transcript, fuldt output, toolkald, artefakter og workspaceændringer samt sende en opfølgning eller anmode om afbrydelse, når brugerens rettigheder tillader det. Et råd vises som en gruppering af almindelige agent-runs med medlemsstatus og syntese. UI'et må ikke tolke tavshed som succes eller udlede status fra tekst; alle felter kommer fra runtime/DB-projektioner.

## 11. Gennemførelse og accept

Implementeringen deles i disse afhængige leverancer: (A) varig assignment/run/inbox-kontrakt og terminal outbox; (B) kobling af inbox til aktivt og inaktivt synligt run; (C) worker-livscyklus, prompt og artefakter; (D) selvstændig agentmodelpulje med parent-fallback og ruteproveniens; (E) container-/klient-target med reconnect og ukendt udfald; (F) styringsværktøjer, råd/review/langtidsmønstre; (G) Desk-projektion og inspector. Hver leverance skal kunne testes gennem service-API før UI tilføjes.

Acceptscenarier omfatter: resultat under aktivt run; resultat efter runslut; samtidig afslutning og lukning; dobbelt levering; workercrash før og efter resultatcommit; API-/runtimegenstart; brotab før afsendelse, efter afsendelse og efter fjern udførelse; reconnect fra samme og anden klient; afbrudt agent med ventende besked; budget-/dybdeoverskridelse; råd med ét fejlet medlem; reviewer der afviser builders påstand; fuldt output større end promptgrænsen; og langtidsagent efter planlagt vækning. Modelscenarier omfatter egnet puljemodel, pulje udtømt med parent-fallback, parentmodel uden nødvendig kapabilitet, bruger uden adgang til betalt fallback, hårdt modelkrav, fork med modelskift og fejl efter et muligt skrivende toolkald. For hvert scenarie verificeres DB-status, præcis én parentbesked, korrekt årsag, valgt rutes kilde og adgang til artefakten.

## 12. Åbne produktvalg til gennemgang

Denne spec vælger ingen automatisk overgang til en anden maskine, når et klient-target forsvinder. Den lader Jarvis vælge råd, parallelisme og review ud fra opgaven, under budget- og rettighedsgrænser. Før implementeringsplanen skal Bjørn fastlægge standardretention for artefakter, om klientmaskinens skrivearbejde altid skal bruge worktree, og hvilke langvarige agenttyper der skal være tilladt fra første version. De valg ændrer ikke leverings- og fejlsikkerhedsgarantierne ovenfor.
