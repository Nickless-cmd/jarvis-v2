# Hvorfor model-benchmarken findes

*Denne note findes fordi begrundelsen røg tabt: koden blev committet under
en «docs:»-besked ved en fejl (4009d48c5), og rebase er blokeret i dette repo,
så beskeden kan ikke rettes. Begrundelsen hører til i historikken — her er
den i stedet.*

## Problemet

Efter første fejning af cheap lane (7/9-2026) stod **65 af 67 egnede modeller
med `probe_score` 100**, og den første i rotationen var en 3B-model foran
`deepseek-v4-pro`. Rækkefølgen var reelt vilkårlig.

Sonden (`model_probe`) kan afgøre om en model **kan** kalde et værktøj og
bruge svaret. Den kan ikke afgøre hvor **god** den er.

## Hvorfor en hårdere sonde ikke løser det

`copilot-free/gpt-4.1` bestod hver eneste skærpelse — larmende værktøjssvar
med svaret begravet, en opdigt-detektor, `follows` tre gange i træk — og
opdigtede alligevel tre funktionsnavne i produktion, med «Confidence: høj
(begrundet i direkte søgeresultater)» ovenpå.

Fejlen udløses af den ægte opgaves **form**: lang rolle-prompt plus «giv mig
en liste med N ting». En enkeltstående quiz rammer aldrig dét.

## Det bærende valg

**Facit hentes fra kildekoden i samme øjeblik prøven køres.** Opgaverne
skrives ikke i hånden; de genereres fra repoet, og svaret sammenlignes navn
for navn og linje for linje.

En håndskrevet prøve ville være forkert to uger efter nogen omdøbte en
funktion — og så ville vi rangere modeller efter hvor godt de husker gammel
kode.

## Vægtningen

Præcision 0,7 mod dækningens 0,3. **At opfinde er værre end at overse.** En
agent der nævner ting der ikke findes, sender Jarvis i en blindgyde han selv
skal opdage; en der overser noget, siger i det mindste sandt om resten.

## Hvorfor `kvalitets_score` er adskilt fra `probe_score`

At blande dem ville skjule netop det problem der udløste arbejdet: at 65
modeller stod ens på den ene måling og var vidt forskellige på den anden.
