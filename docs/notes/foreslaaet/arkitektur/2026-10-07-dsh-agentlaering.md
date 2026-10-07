---
status: foreslået
dato: 2026-10-07
ejer: bjorn
spec: ../../../specs/2026-10-07-agentorkestrering-og-subagenter.md
---

# DSH-gennemgang før Jarvis' agentmotor

Status: foreslaaet

## Problem

Denne gennemgang bygger på den lokale checkout af `deepseek-harness` i `~/Skrivebord/deepseek-harness`, især `packages/subagent/subagent/README.md`, `packages/subagent/tool-subagent/README.md`, spawn-/fork-backendernes README og modelvalgsprøverne. Den beskriver DSH's nuværende kontrakter; den er ikke en påstand om, at samme kode kan flyttes direkte til Jarvis.

Jarvis har allerede flere agentveje, men de udgør ikke endnu den fejlsikre, samlede livscyklus i spec'en. Agentpuljen ligger allerede i cheap-lane/provider-infrastrukturen; den rummer premium-modeller til agentarbejde. DSH er et konkret sammenligningsgrundlag for at vælge, hvad der skal genbruges som mønster, og hvad der skal bygges stærkere.

## Beslutning

Vi tager disse kontrakter med i designet:

1. **Tre adskilte lag.** Service ejer agentlivscyklus og parentrelation, provider ejer eksekvering, og modelværktøjet er en tynd dispatchflade. En provider annoncerer kapabiliteter; ugyldig persona, modeloverride, kontekstform eller fortsættelse afvises før child publiceres. Jarvis bør anvende samme preflight mod runtime-container og klientbro.
2. **Accept og afslutning er forskellige hændelser.** Et fortsætteligt barn får et stabilt id ved accepteret start. Det kan modtage nye beskeder og afbrydes, mens parent fortsætter. Afslutning giver en separat runtime-ejet besked, også hvis barnet ikke selv får skrevet et sidste svar. Agentkataloget kan læses uden at starte alle børn igen.
3. **Kontekst og roller er eksplicitte.** Spawn har tom samtale og kræver selvstændig opgavetekst. Fork ser alene afsluttede parent-ture. Persona og tool-filter kan gives pr. værktøjsinstans; tool-filter håndhæves ved værktøjskald. Jarvis skal versionere den effektive prompt og håndhæve værktøjer i runtime.
4. **Begrænsninger ved optagelse.** DSH har dybdegrænse (standard 1) og kapacitet for aktive fortsættelige børn (standard 8). Fuld kapacitet afviser start eller cold resume frem for at lade en parent vente på en plads, den selv optager. Jarvis skal også begrænse budget, tid, samtidige klientjobs og retries.
5. **Modelarv er en standard, ikke en lov.** Fresh spawn arver som udgangspunkt parentens provider/model, men request og værktøjskonfiguration kan override efter kapabilitetskontrol. DSH's leverede fork-værktøjer skjuler modelvalg for at bevare mulig cachegenbrug af kopieret historik. Agentmodelruter autoriseres pr. session og valideres mod den aktive adapter før child oprettes. Ved ruteskift nulstilles rutespecifik reasoning effort.
6. **Ejerskab har en skarp grænse.** Provider rydder op ved fejl før child publiceres; efter accepteret/publiceret start skal ejeren kunne se, stoppe og hente barnet. Jarvis skal gøre denne grænse transaktionel med DB, artefaktreference og idempotensnøgle.

### Huller vi skal lukke i Jarvis

DSH dokumenterer selv begrænsninger: child-til-parent kræver en live parent, der er ingen varig parent-mailbox, processens Activation og kapacitet er lokale, og en accepteret men endnu ikke logget besked kan tabes ved crash. En wake-gap efter afbrydelse kan lade en opfølgning stå i kø indtil næste vækning. ACP-børn er engangsarbejde uden samme lokale trace-/fortsættelseskontrakt. Jarvis' krav om bro, genstart og altid synligt udfald kræver derfor **varig inbox/outbox, leases på tværs af processer, genafspilning af accepterede beskeder og eksplicit ukendt udfald for fjern skrivehandling**. DSH's levering kan inspirere flowet, men opfylder ikke alene disse garantier.

## Forskellen til Jarvis' kode i dag

- `core/services/agent_pool_router.py` kalder `central_route` med `lane="agent"`, og `central_route._scored_candidates()` henter kandidater fra `_configured_cheap_candidates()`. Det er foreneligt med, at agentpuljen er en logisk kandidatgruppe i den eksisterende providerinfrastruktur; det beviser ikke endnu den krævede premium-først-rækkefølge eller ejerafhængige fallback.
- Premium-adgang er i dag også bundet til opgavetype: `agent_runtime_spawn._scout_maa_betale()` åbner for visse researcher/scout-roller, mens `agent_loop.py` åbner for udvalgte kode-skrive-typer. Den ønskede fælles premium-agentpulje for agentarbejde kræver en samlet, ejerbevidst policy i stedet for disse forskellige lokale porte.
- `core/services/agent_runtime_spawn.py` prøver rollekonfiguration og agentrouter, men falder til sidst tilbage til `cheap_lane_status_surface().selected_target` uden ejerafgørelse. Den skriver også `lane="cheap"` i agentregisteret. Det gør ruteproveniens og den tilsigtede fallback uklar.
- `central_route.route()` kan levere cheap-lanens floor eller en degraderet tom modelrute. Agentstart skal i stedet afvise en ubrugelig rute tydeligt og aflevere `MODEL_UNAVAILABLE`.
- `route_agent_task()` får ikke ejer/session som input. Agentvalg skal kende den autentificerede ejer og træets budget. Samme premium-agentpulje må betjene Jarvis' og andre brugeres agenter, men kun Bjørns opgaver må falde tilbage til Bjørns DeepSeek API; andre brugeres fallback er cheap lane. Nuværende `apps/api/jarvis_api/routes/agent_loop.py` har desuden en sidste hårdkodet DeepSeek-default, som kræver en ejerbeskyttet grænse før modelkald.
- Fitnessvagten i `agent_pool_router.py` fanger alle undtagelser og fortsætter. Ukendt fitness kan være tilladt, men må logges som ukendt; en målt uegnet model eller en ødelagt fitnesskontrol må ikke skjules i en succesrute.

### Første implementeringsskive

Behold den eksisterende providerinfrastruktur, men gør premium-agentpuljens kandidatgruppe og prioritet eksplicit. Byg en ren beslutningsfunktion, der returnerer en fuldt valideret rute, autentificeret ejer, `route_source` og afvisningsårsager. Prøv alle egnede puljekandidater før fallback: DeepSeek API for Bjørns opgaver, cheap lane for andre brugeres opgaver. Et eksplicit hårdt modelkrav må ikke omgås, og DeepSeek-adgang kontrolleres igen ved providerkaldet. Gem beslutningen før modellen eller et værktøj kaldes. Test to ejere, tom og delvist fejlet pulje, værktøjsinkompatibilitet, budgetafslag, fork med ændret rute og forsøg på at vælge DeepSeek via et barn eller en API-default. Derefter kobles funktionen til den varige assignment-/run-kontrakt i spec'en.

## Overvejede alternativer

- **Flytte agentpuljen ud i en helt ny konfiguration:** giver stærk fysisk adskillelse, men duplikerer den eksisterende providerinfrastruktur og er ikke nødvendig for at håndhæve puljens prioritet og ejergrænse.
- **Altid arve parentens model som DSH's standard:** er enkelt og gør fork-cache mulig, men bryder rækkefølgen premium-agentpulje før ejerens fallback.
- **Altid bruge billigste model:** sparer penge, men ignorerer observeret værktøjsegnethed og kvalitetskrav; Jarvis har allerede kodekommentarer om modeller, der finder på toolresultater.
- **Stiltiende skifte til enhver ledig model:** skjuler budget- og adgangsbrud og gør fejl svære at efterprøve. Kun puljen og den pågældende ejers tilladte fallback indgår i beslutningen.
- **Kopiere DSH's process-lokale inbox:** giver hurtigt in-process arbejde, men opfylder ikke krav om genstart, klientbro og levering til en inaktiv parent.

## Konsekvenser

Agentpuljens premium-kandidater skal kunne identificeres og rangeres særskilt inden for den nuværende providerinfrastruktur. Ejeridentitet skal følge hele agenttræet, og DeepSeek-spærren skal ligge også ved providerinvocation. Preflight, fallback og hvert afslag skal være synligt i run- og omkostningssporet. En billig agent er kun en gevinst, hvis kvalitet, værktøjsformat og genbehandlet fork-kontekst regnes med. DSH's aktuelle begrænsninger viser, at varig inbox/outbox og tværproces-leases fortsat skal bygges i Jarvis; gennemgangen er ikke et bevis for, at den eksisterende Jarvis-kode allerede leverer garantierne.
