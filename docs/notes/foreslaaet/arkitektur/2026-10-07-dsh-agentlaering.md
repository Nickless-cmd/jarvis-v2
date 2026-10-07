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

Jarvis har allerede flere agentveje, men de udgør ikke endnu den fejlsikre, samlede livscyklus i spec'en. Især er en `agent`-rute i den nuværende kode stadig baseret på cheap lanes kandidater. DSH er et konkret sammenligningsgrundlag for at vælge, hvad der skal genbruges som mønster, og hvad der skal bygges stærkere.

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

- `core/services/agent_pool_router.py` kalder `central_route` med `lane="agent"`, men `central_route._scored_candidates()` henter stadig kandidater fra `_configured_cheap_candidates()`. En særskilt rangering er altså ikke endnu en særskilt agentmodelpulje.
- `core/services/agent_runtime_spawn.py` prøver rollekonfiguration og agentrouter, men falder til sidst tilbage til `cheap_lane_status_surface().selected_target`. Den skriver også `lane="cheap"` i agentregisteret. Det strider mod den ønskede modelpolitik og gør ruteproveniens uklar.
- `central_route.route()` kan levere cheap-lanens floor eller en degraderet tom modelrute. Agentstart skal i stedet afvise en ubrugelig rute tydeligt og aflevere `MODEL_UNAVAILABLE`.
- `route_agent_task()` får ikke ejer/session som input. Agentvalg og fallback skal kende ejeren, den konkrete parents senest faktisk anvendte model, adgang til betalte ruter samt træets budget. Det er især vigtigt for agenter startet af almindelige brugere.
- Fitnessvagten i `agent_pool_router.py` fanger alle undtagelser og fortsætter. Ukendt fitness kan være tilladt, men må logges som ukendt; en målt uegnet model eller en ødelagt fitnesskontrol må ikke skjules i en succesrute.

### Første implementeringsskive

Byg en uafhængig kandidatkilde for én fælles agentmodelpulje og en ren beslutningsfunktion, der returnerer en fuldt valideret rute plus `route_source` og afvisningsårsager. Vælg puljemodel først og den **konkrete** parents model som sidste, autoriserede fallback. Et eksplicit hårdt modelkrav må ikke omgås. Fjern cheap-lane fallback fra agentstart og gem beslutningen før modellen eller et værktøj kaldes. Test modelvalg med to forskellige parents, tom pulje, værktøjsinkompatibilitet, budgetafslag og fork med ændret rute. Derefter kobles funktionen til den varige assignment-/run-kontrakt i spec'en.

## Overvejede alternativer

- **Bruge cheap lanes kandidatliste med ny rangering:** kræver få ændringer, men holder agentpolitik, kvoter og fallback bundet til et andet formål. Det er netop den nuværende utilsigtede kobling.
- **Altid arve parentens model som DSH's standard:** er enkelt og gør fork-cache mulig, men ignorerer ønsket om billige, egnede agenter og kan gøre parallel delegation dyr.
- **Altid bruge billigste model:** sparer penge, men ignorerer observeret værktøjsegnethed og kvalitetskrav; Jarvis har allerede kodekommentarer om modeller, der finder på toolresultater.
- **Stiltiende skifte til enhver ledig model:** skjuler budget- og adgangsbrud og gør fejl svære at efterprøve. Kun puljen og den autoriserede parentrute indgår i beslutningen.
- **Kopiere DSH's process-lokale inbox:** giver hurtigt in-process arbejde, men opfylder ikke krav om genstart, klientbro og levering til en inaktiv parent.

## Konsekvenser

Agentpuljen får særskilt konfiguration og migrationsarbejde, og parentens faktiske rute skal kunne hentes på dispatchtidspunktet. Preflight, fallback og hvert afslag skal være synligt i run- og omkostningssporet. En billig agent er kun en gevinst, hvis kvalitet, værktøjsformat og genbehandlet fork-kontekst regnes med. DSH's aktuelle begrænsninger viser, at varig inbox/outbox og tværproces-leases fortsat skal bygges i Jarvis; gennemgangen er ikke et bevis for, at den eksisterende Jarvis-kode allerede leverer garantierne.
