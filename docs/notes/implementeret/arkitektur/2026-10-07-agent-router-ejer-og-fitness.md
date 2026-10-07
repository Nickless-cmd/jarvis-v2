---
status: implementeret
slags: arkitektur
dato: 2026-10-07
forfatter: jarvis
---

# Agent-routeren kender nu sin ejer — og fejler synligt

Status: implementeret

## Problem

Spec'ens §7.1 hviler på ét argument: kun Bjørns opgaver må falde tilbage til
hans DeepSeek-API, og ingen anden ejer må nå den. Målt 7/10-2026:

* `route_agent_task()` tog `kind`, `min_tokens`, `quality_threshold`,
  `allow_paid` og `exclude` — **ikke ejeren.** Reglen kunne derfor ikke
  håndhæves nogen steder i kæden; den kunne ikke engang formuleres.
* Fitnessvagten hed `except Exception: pass` med kommentaren «fitness må aldrig
  kunne blokere en agent i at blive født». Den kunne ikke skelne «fitness-
  tabellen er tom» (ukendt → tilladt, korrekt) fra «fitness-kontrollen er i
  stykker». En måling der ALDRIG kørte så ud som et lovligt svar.
* **Nul tests** dækkede nogen af delene.

## Beslutning

* `route_agent_task(*, …, owner_user_id: str | None = None)`. Ejerens id følger
  med ind i `central_route`-beslutningen, og `None` sendes ærligt når ejeren er
  ukendt — ikke et gæt.
* Returværdien bærer `route_source="agent_pool"`, så kalderen kan se om svaret
  kom fra puljen eller fra et fald nedenfor.
* Fitnessgrenen logger på WARNING og sætter `fitness_ukendt=True`. «Ukendt» og
  «godkendt» er nu to forskellige svar.
* Fire tests. Begge garantier er bevist at kunne **fejle**: sendes ejeren som
  `None`, fejler ejer-testen; gendannes den tavse gren, fejler fitness-testen.
  Gendannet efter prøven: 7 grønne.

## Overvejede alternativer

* **Lukke ejergrænsen helt i routeren.** Fravalgt: spec'en kræver at
  rettigheden kontrolleres igen VED providerkaldet, ikke kun i routeren. En
  router-gate alene ville være endnu en «to sandheder». Parameteren er
  forudsætningen for det værn — ikke dets afløser.
* **Lade `fitness_ukendt` være en log-linje alene.** Fravalgt: kalderen skal
  kunne skelne, ikke kun læse loggen.
* **Vente med begge til den nye agentmotor er bygget.** Fravalgt: spec'ens §3
  siger at begge «skal ændres, før agentrouteren bruges som sikkerhedsgrænse».
  At bygge fallback-logik oven på en funktion der ikke kender ejeren er den
  dyre vej.

## Konsekvenser

* Kalderne skal sende ejeren med. I dag er der ingen produktionskalder uden for
  flaget `agent_pool_router_enabled` (OFF), så ændringen er uden driftseffekt nu.
* **Det jeg IKKE kan love:** at grænsen holder. Parameteren findes og bæres
  igennem; kontrollen ved providerkaldet er ikke bygget.
