# Note: tool-nudgens regel 1 blev fjernet, ikke udvidet

Status: implementeret

## Problem

Den første udgave af `tool_hunt_nudge` gættede på hvilket værktøj Jarvis
ledte efter, ud fra hans søgekommandoer. Idéen var rigtig nok: han bruger
`bash` til at lede efter et værktøj han allerede har.

Målt over 14 døgn på 12.328 af hans EGNE kald — de øvrige 27.057
`tool.invoked` er desk'ens pollere uden `_runtime_turn_id`, og tages de med,
bliver enhver frekvens tre gange for lav:

* Det leksikalske opslag fyrede **7 gange, og alle 7 var falske.** Han
  greppede efter strengene `tool_result`, `home_assistant` og
  `council_status` i KILDEKODEN, og der fandtes tilfældigvis værktøjer med
  de navne.
* Reglen så kun **2 %** af hans søgninger overhovedet. Hans stil er
  `cd X && echo "=== A ===" && grep …`, og funktionen læste kun første led.

## Beslutning

Reglen er fjernet. Tilbage står kun regler hvor signalet er entydigt: et
værktøjsnavn der ikke findes, en søgning uden træf, en tabel der ikke
eksisterer, en fil skrevet hvor han plejer at udgive fra.

## Overvejede alternativer

**Udvide opslaget til hele kommando-kæden.** Det var den nærliggende
rettelse, og den var forkert. Præcisionen var 0 ud af 7 på de 2 % vi så; en
tredobling af dækningen ville give FLERE falske, ikke færre. Et nudge-spor
man lærer at overse, er værre end intet spor.

**Hæve tærsklen i stedet for at fjerne reglen.** Der var ingen tærskel at
hæve — fejlen var ikke mængden, men at ordsammenfald ikke er et signal.

**Lade den stå, siden den kun fyrede 7 gange.** Syv falske noter er syv
lektioner i at ignorere kanalen. Prisen betales af de regler der er sande.

## Konsekvenser

Nudgen ser færre situationer end før, og det er meningen. Den ved ikke
hvornår han leder efter noget uden at sige det; den ved kun hvornår han har
ledt FORGÆVES. Det er et smallere løfte, og det er det eneste der kunne
holdes.

Reglen er ikke gemt bag et flag. Et flag ville lade tallene fra dengang
forsvinde ud af hukommelsen og invitere til at tænde den igen uden at måle
forfra.
