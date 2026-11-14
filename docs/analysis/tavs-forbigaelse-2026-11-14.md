# Den tavse forbigåelse — hvor stor er resten?

**Målt 14/11-2026 mod den levende base.** Cutoff: `id <= 282143` i `chat_messages`.
Filtreret til `role='assistant'` med `length(content) > 200`.

## Tallene

| Kategori | Antal | Andel |
|---|---|---|
| Svar i alt (cutoff) | 14.683 | 100 % |
| Med flade (`jarvis-ui`) | 364 | 2,5 % |
| Med tabel | 3.602 | 24,5 % |
| **Uden flade OG uden tabel** | **10.740** | **73,1 %** |
| — heraf med strukturel signatur (talmur/opremsning) | 6.412 | 59,7 % af de usynlige |
| — **helt uden signatur** | **4.328** | **40,3 % af de usynlige** |

Detektorernes tærskler er uændrede: `MIN_TAL=5`, `MIN_LED=3`
(`core/services/prosa_struktur_guard.py`).

## Fladetyper der faktisk vælges

| Type | Antal |
|---|---|
| comparison | 211 |
| stats | 50 |
| timeline | 49 |
| callout | 43 |
| keyvalue | 14 |
| choices | 8 |
| box | 7 |
| progress | 6 |
| code | 4 |
| tree / form / chart | 3 hver |
| location / enabled / quote | 2 hver |

`comparison` dominerer med 58 % af alle flader. Det er den samme type jeg
selv vælger oftest — og det er præcis den type opgaven pegede på som
mistænkt for at blive valgt hvor `table` eller `stats` havde været rigtig.

## Stikprøve: hvad er de 4.328 «helt usynlige» egentlig?

40 tilfældige svar læst manuelt. Fordelingen er entydig:

- **Korte opfølgninger og kvitteringer** («Det skal jeg gøre», «Fixet er live!»,
  «Broen virker!») — den klart største gruppe. Der er intet struktureret
  indhold at vise; en flade ville være staffage.
- **Fejl- og statusbeskeder** (Discord-forbindelse, runtime-fejl, gateway) —
  prosa er den rigtige form.
- **Krypterede rækker** (`enc:v1:...`) — kan ikke vurderes, og skal ikke tælles
  som en tavs forbigåelse. Det er en målefejl i udtrækket, ikke et fund.
- **Enkelte ægte kandidater** — fx et svar der beskriver et forløb i afsnit
  uden ét tal (id 107256, 103760). De findes, men de er få i stikprøven.

**Ingen af de 40 var et svar hvor en flade havde været den rigtige form og
blev forbigået i tavshed.** Den kategori opgaven frygtede, er ikke synlig i
denne stikprøve.

## Anbefaling: **lad være**

Der skal **ikke** bygges en regel for den tavse forbigåelse nu.

Grunden er målt, ikke en mavefornemmelse:

1. **De 4.328 er ikke 4.328 tabte flader.** Stikprøven viser at langt
   størstedelen er korte svar hvor prosa ER den rigtige form. En detektor
   ville ramme dem alle og råbe falsk.
2. **De 6.412 med signatur er allerede dækket** af `flade_paamindelse` efter
   `side-59ae9c975a`. Resten har per definition intet at tælle.
3. **En semantisk detektor ville være en regex der gætter.** Det er præcis den
   slags vagt der gør Centralens fejl-billede utroværdigt — den råber falsk
   og lærer mig at ignorere linjen, som `flade_paamindelse` gjorde ved 58,4 %
   før den blev værnret.

**Det ærlige svar på Bjørns spørgsmål** («hvordan sørger vi for at du husker
at bruge alt det nye») er: mekanismen findes for de tilfælde der har en
signatur, og den er nu kalibreret. Resten kan ikke fanges af en tærskel — og
at bygge en der påstår det, ville være teater.

## Hvad der i stedet er værd at gøre

`comparison` bliver valgt 211 gange mod `table`-lignende alternativer. Det er
den ene målbare skævhed i materialet. En fremtidig opgave kunne undersøge om
`comparison` bruges hvor `stats` eller `keyvalue` havde båret indholdet bedre
— men det kræver en læsning af de 211, ikke en ny detektor.

## Forbehold

- Udtrækket indeholder krypterede rækker (`enc:v1:`). De tælles med i de
  4.328 og kan ikke klassificeres. Det gør tallet en anelse for højt.
- Stikprøven er 40 af 4.328 (0,9 %). Den er nok til at afvise «byg en regel»,
  ikke nok til at hævde at kategorien er nul.
- Målingen er lavet på `content`, ikke på `content_json`. Bloklisten kan bære
  struktur som prosa-teksten ikke viser.
