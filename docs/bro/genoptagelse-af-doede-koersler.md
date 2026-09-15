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

## Opstarts-fejning var ikke nok (15/9-2026)

Jeg genstartede `jarvis-api`. Den udgav pligtskyldigt «api-nedlukning» for
Bjørns kørsel — og lytteren bor i `jarvis-runtime`, som **ikke** blev
genstartet. Eventet lå i DB'en, ingen så det, og hans besked blev aldrig
genoptaget.

Rettelsen fra natten lukkede kun det ene hul: lytteren læste DB'en **ved sin
egen opstart**. Men event-bussens abonnenter er process-lokale, og DB'en er den
delte sandhed — så en lytter der kun kigger ved opstart er blind for alt hvad
den anden proces udgiver imens.

Lytterens løkke tikker allerede hvert sekund, så fejningen kører nu løbende
derfra — hvert 60. sekund, uden en ny tråd. Nøglen pr. kørsel er kvitteringen,
så en gentagen fejning kan ikke genoptage det samme to gange.

To mutationer til, og den ene overlevede først: fjerner man `sidst_fejet =
time.monotonic()` inde i grenen, fejer den ved **hver** tik efter første gang —
samme skade som intet interval, ad en anden vej. En test på konstanten kan ikke
se det, fordi konstanten er uændret. Takten måles nu over tid med et styret ur.

## Er brugeren gået videre? (15/9-2026)

Genoptagelsen tjekkede ikke om arbejdet allerede var gjort om. Målt samme dag:
Bjørns kørsel blev afbrudt 10:41:31, og han fik sit svar **32 sekunder senere**
fra en ny kørsel. Genoptagelsen vidste det ikke, vækkede Jarvis, og han brugte
en runde på at undersøge en afbrydelse ingen ventede på længere.

Reglen: **er der kommet en senere synlig kørsel helt igennem, er brugeren gået
videre.**

Vejen dertil var mest udelukkelse. `cognitive_episodes` har både
`source_run_id` og `session_id` — og er tom for synlige kørsler (målt: 50
kørsler, 0 episoder). `chat_messages` har session og indhold, men intet
`run_id`. `visible_runs` har intet `session_id`. Så den eksakte kobling
findes ikke i praksis, og reglen bruger det der faktisk er fyldt.

Fejlretningen: kan basen ikke læses, siger vagten **nej** — altså genoptag.
«Et run må aldrig dø», så tvivlen falder ud til fordel for at prøve.

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
