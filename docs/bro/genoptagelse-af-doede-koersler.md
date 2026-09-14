# «Et run må aldrig dø» — hvorfor genoptagelsen aldrig fyrede

**14/9-2026.** Bjørn: «Ja den skal ihf. Ikk død! Et run må aldrig død..» og
«Tag dem».

## Målingen der afgjorde det

I basen står 25 `runtime.visible_run_interrupted`-events. I den levende
direktørs **744 spor er der NUL** om en afbrudt kørsel. Genoptagelsen har
aldrig fyret én eneste gang — ikke i 25 anledninger.

Jeg gik efter nedkølingen, fordi den var det åbenlyse: nøglen var konstanten
`"visible-run-interrupted"` med 900 sekunder, så to crash tre minutter fra
hinanden giver ÉN genoptagelse. Det var rigtigt observeret og **ikke** den
bindende port. Hvis nedkølingen havde været problemet, ville der have stået
ét spor. Der stod nul.

## Grund 1 (den ægte) — eventet udgives før nogen lytter

Genstart-loggen, i rækkefølge:

    21:44:33  jarvis-runtime: session_boot_reconciler   ← stempler de døde
    21:44:34  jarvis-runtime: living_executive: listener started

`event_bus.subscribe()` lægger abonnenten i en liste **i processen**.
`session_boot_reconciler` — den eneste der finder crash-dræbte kørsler — kører
et sekund før lytteren abonnerer. Eventet udgives altså til en tom
abonnent-liste.

Det er ikke et kapløb. Det er en fast rækkefølge, og den kan ikke vindes:
genopretteren SKAL køre tidligt, det er hele dens formål.

Rettelsen læser fra DB'en, som er delt på tværs af processer, i stedet for at
stole på at have været til stede i det rigtige sekund. Forespørgslen filtrerer
på `kind` i SQL — et blankt `limit` ville begrave afbrydelserne under
tusindvis af andre events og give et stille nul. Den fælde har bidt tre gange
i dette hus.

## Grund 2 — nedkølingen behandlede «tabt arbejde» som ÉN ting

Hans egne tal, i nedkølingens eget 15-minutters vindue:

| tabte kørsler i vinduet | vinduer |
|---|---|
| 1 | 191 |
| 2 | 31 |
| 3 | 10 |
| 4 | 6 |
| 5 | 4 |
| 6 | 2 |
| **17** | 1 |

54 af 245 vinduer (22%) havde mere end én. Lagt sammen ville **111 af 356**
tabte kørsler være blevet droppet af nøglen alene.

Nøglen står nu på kørslens id. En nedkøling skal afvise DET SAMME tabte
arbejde to gange — ikke tabt arbejde i almindelighed.

Uden id deles den gamle fælles nøgle. Fejlretningen: kan vi ikke bevise at to
afbrydelser er forskellige, så gang ikke genoptagelserne op. Tavshed er ikke
belæg.

## Grund 3 — genoptagelsen sagde ikke hvilken kørsel

Prompten var «Resume from interrupted visible run: {summary}». Uden id kan den
vækkede umuligt vide hvad der skal genoptages. Den hedder nu «Resume
interrupted visible run {run_id}: …».

## Loftet

Det ene vindue med 17 er grunden til at nøglen pr. kørsel ikke kan stå alene:
en masse-død ville planlægge 17 vækninger på én gang. Det er ikke en redning,
det er et stormløb. Loftet er 5 pr. vindue — det dækker 244 af 245 målte
vinduer.

Loftet sidder i selve HANDLINGEN og ikke i indhentningen, så det også dækker
vejen hvor kørslerne dør live og lytteren får dem ét event ad gangen.

Og det er **ikke tavst**: et ramt loft skriver et spor med status `capped`. At
droppe uden spor er præcis den fejl hele øvelsen handler om.

## Vinduet, rettet af en måling lige inden deploy

Første udgave kiggede 24 timer tilbage. Inden jeg deployede, målte jeg hvad
indhentningen så ville vække på hans base: **præcis ét event — en autonom
kørsel fra i går aftes.**

Det afslørede at vinduet var valgt forkert. Indhentningen findes for at lukke
et ét-sekunds hul, hvor eventene er sekunder gamle. Et døgngammelt afbrudt
arbejde er ikke noget nogen venter på, og et bredt vindue gør hver genstart
til en mulig genoplivning af gammelt arbejde. Vinduet er nu **60 minutter** —
rigeligt til «API'en stemplede ved nedlukning, runtime kom op et minut senere».

## Mutations-prøve

| Mutation | Udfald |
|---|---|
| nøglen tilbage til konstanten | 4 røde |
| run_id ud af prompten | 1 rød |
| indhentningen tager kun den første | 3 røde |
| intet loft | 2 røde |
| loftet dropper tavst (`capped` → `executed`) | 1 rød |
| **indhentningen kaldes aldrig fra `start_listener`** | **9 GRØNNE** |
| nøgle pr. kørsel også uden id | 9 grønne — ÆKVIVALENT |

Den næstsidste er den vigtige. Alle ni tests målte funktionen ved selv at
kalde den, og **en test der selv leverer inputtet kan aldrig se at INGEN
leverer det**. Mutationen ville have genindført nøjagtig den fejl vi retter:
mekanismen findes, kalderen mangler. Der er nu en test på selve koblingen.

Den sidste er ægte ækvivalent: med tomt id giver `f"{noegle}:{rid}"` strengen
`"visible-run-interrupted:"`, som stadig er én konstant nøgle for alle.

Forespørgslen selv blev testet mod en rigtig sqlite, fordi de ti første tests
udskifter den — og det er netop det led der kan give et stille nul. Tre
mutationer til, alle døde: art-filteret fjernet, tidsvinduet vendt om,
rækkefølgen ikke vendt.
