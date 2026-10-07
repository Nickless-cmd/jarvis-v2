---
status: implementeret
slags: arkitektur
dato: 2026-10-07
forfatter: opus
---

# Agent-brokeren forbliver i serverprocessen — bevidst ikke bygget som egen proces

Status: implementeret

## Problem

Leverance C's hul 5 spurgte om policybrokeren (`_Broker` i
`core/services/agent_worker_runner.py`) skal være en særskilt proces i stedet
for en tråd i den proces der startede agentens worker. Spørgsmålet er værd at
stille, fordi spec'en bruger ordet «broker» flere steder. Læst ord for ord:

* §12.1: «Hvert aktivt run får en særskilt, serverstyret **workerproces**… API-
  processen og Desk kører ikke barnets model-/toolløkke… Værktøjskald går
  gennem **serverens** policybroker.» Workeren er den særskilte proces.
  Brokeren er *serverens*.
* §8: «Agentens loop, modelkald, checkpoint, inbox og værktøjsbeslutning
  forbliver på serveren.»
* §9 Procesansvar: kun to roller er navngivet — `jarvis-runtime` (periodisk
  reconciliation og worker-supervision) og `jarvis-api` (start af synlige
  parentfortsættelser). En tredje procesrolle for brokeren står ingen steder.
* §11.1 Procesgrænse: testen kræver forskellige worker-PID'er, at hverken API-
  eller runtimeprocessen udfører agentens *løkke*, og at credentials og andre
  ejeres filer er utilgængelige *inde i workeren*. Alt tre er bygget og testet
  (`test_agent_worker_runner`, `test_agent_sandbox*`).

Målt i koden 7/10-2026: brokeren er ca. 80 linjer (`_Broker`, linje 107-187), den har ingen egen tilstand
ud over en tæller og et sæt påbegyndte kald (`_started`), og alt varigt — lease,
fencing-token, tool-kald, checkpoints — står i DB, ikke i brokerens hukommelse.

## Beslutning

Brokeren forbliver en tråd i den proces der kalder `execute_agent_task`. Der
bygges **ingen** separat brokerproces. Det er en bevidst beslutning, ikke en
udeladelse.

Det er en tolkning af §11.1's «model-/toolløkke», som jeg forstår som
agentens beslutningsløkke (hvad næste skridt er). Selve udførelsen af ét
modelkald og ét værktøjskald på workerens anmodning sker på serveren, det
siger §8 udtrykkeligt. **Bjørn: sig til hvis du har ment løkken som «også
udførelsen»** — så er svaret et andet, og det ville kræve en egen proces med
adgang til provider-nøgler og værktøjsdispatchen.

## Overvejede alternativer

* **Egen brokerproces mellem worker og server.** Fravalgt. Brokeren skal kunne
  (1) læse provider-nøgler for at kalde modellen, (2) køre værktøjer gennem
  `execute_tool` med godkendelser og scoping, (3) skrive bogføring og
  checkpoints i DB. Det er netop serverens rettigheder. En separat proces med
  de samme tre rettigheder flytter ikke grænsen; den tilføjer en ekstra
  deployment-enhed, en ekstra fejltilstand og en ekstra ting at holde i sync
  med `jarvis-api`/`jarvis-runtime` (to enheder kører allerede samme app).
  Grænsen der betyder noget — worker ↔ resten — er allerede en proces- og
  sandboxgrænse.
* **Pris som argument.** Fravalgt som begrundelse. Målt: en
  rundtur over en proces-grænse (socketpair, ca. 350 byte ramme) tager ca. 9 µs
  i gennemsnit over 3000 kald. Et ekstra hop ville være ubetydeligt ift. et
  modelkald på sekunder. Beslutningen hviler på at det ikke giver sikkerhed,
  ikke på at det er dyrt.
* **Broker i `jarvis-runtime` i stedet for `jarvis-api`.** Ikke afgjort her.
  Dispatch sker i dag i den proces hvor kaldet kommer fra (typisk det synlige run i `jarvis-api` — ikke verificeret her), og
  `_start_execution` starter brokertråden i den proces. §9 siger at
  `jarvis-runtime` ejer *supervision*, ikke udførelse, så det er ikke i strid
  med spec'en — men se Konsekvenser.

## Konsekvenser

* En fejl i et værktøj der kører i brokeren (et langsomt eller hængende
  `execute_tool`) kan optage en tråd i `jarvis-api`. Det er samme risiko
  som Jarvis' egne værktøjer har i det synlige run i forvejen; den er ikke ny,
  men den er heller ikke fjernet. De skrivende kode-værktøjer (`wt_bash`,
  `wt_write_file`) kører ikke i brokerprocessen: de kører i deres egen
  bwrap-sandbox med egen pids-grænse (leverance C hul 2).
* Genstart af serverprocessen tager brokeren med. Det er forudset: workerens
  lease udløber (90 s), supervisoren overtager med atomisk claim, og et
  værktøjskald i luften giver `outcome_unknown` — ingen blind genudførelse (§9).
* Hvis spec'en senere kræver at API-processen ikke må udføre agent-værktøjer
  overhovedet, er det en ny leverance med egen note: flyt
  `_start_execution` til `jarvis-runtime` (en enkelt dispatchvej, ikke en ny
  proces) før man overvejer en tredje proces.
* Det jeg *ikke* kan love: at en kompromitteret broker er sikker. Den har
  serverens rettigheder. Beskyttelsen mod en ondsindet agent ligger i
  protokollen (workeren kan kun bede om «med/uden» værktøjer og navngivne
  allowlist-værktøjer) og i sandboxen, ikke i at brokeren er en særskilt proces.
