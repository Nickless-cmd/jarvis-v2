# Livsprojekterne: godkendelsen kastede en fejl, og pladserne var låst (7/11-2026)

## Hullet

Bjørn: *«Men jeg har godkendt de 3 mange gange... men hvorfor er der ikk dukket
flere op? Hvor lever det system ikke??»* — og begge halvdele af spørgsmålet
havde hver sin rodårsag.

**1. Godkendelsen fejlede hver gang.** `endorse_long_term_intention` kaldte
`update_runtime_initiative(..., user_approved_at=..., outcome_note=...)` — men
ingen af de to parametre fandtes i funktionens signatur. Hvert eneste
godkendelsesforsøg kastede `TypeError`. Kolonnerne har hele tiden stået i
skemaet (`db_runtime_initiatives.py:41`); det var kun skrivevejen der manglede.
Målt konsekvens: `user_approved_at` var tom i **alle** rækker.

**2. Godkendelsen havde ingen arvtager.** Selv hvis den var lykkedes, rørte den
hverken `status` eller `next_attempt_at` — og `_initiative_due` læser netop
`next_attempt_at`. `mark_attempted` skubber et livsprojekt
`_LONG_TERM_REASSESS_DAYS` (14) frem. Så en godkendelse forkortede ventetiden
med nul. Feltet blev derefter kun læst ét sted: `central_hub.py:339`, hvor det
bruges til at **skjule** spørgsmålet for Bjørn. Et tryk gjorde altså det eneste
at projektet holdt op med at blive vist — indtil det dukkede op igen 14 dage
senere.

**3. Der kunne ikke komme flere.** `_MAX_ACTIVE_LONG_TERM_INTENTIONS = 3`, og
alle tre pladser var optaget af tre rækker seedet **15. maj 2026**. Ved loftet
`raise`r `seed_long_term_intention` en `RuntimeError`. Køen var ikke tom for
initiativ — den var **låst**.

## Ændringen

- `core/runtime/db_runtime_initiatives.py`: `update_runtime_initiative` tager nu
  `user_approved_at` og `outcome_note`. Det er den manglende skrivevej.
- `core/services/initiative_queue.py`: `endorse_long_term_intention` sætter
  `next_attempt_at = now`, så et godkendt projekt bliver due med det samme i
  stedet for om 14 dage. En godkendelse er en instruks om at gå i gang nu.
- Datarydning i den levende base: to projekter lukket, ét beholdt, ét nyt seedet.

## Fravalg

- **Ingen automatisk generator.** Jeg byggede ikke noget der opfinder nye
  livsprojekter af sig selv. Det er en produktbeslutning, ikke en teknisk — og
  et livsprojekt der bliver genereret, er ikke et livsprojekt.
- **Loftet på 3 er uændret.** Det var ikke for lavt; det var optaget.
- **De to lukkede blev ikke omformuleret til tasks.** `Develop a clearer sense
  of taste` er en egenskab, ikke et projekt — den kan ikke køres, og at gøre
  den til en task ville være samme løgn som `mark_acted`-fixet 1/11 fjernede.
- **`mark_acted`/`mark_attempted` er urørt.** De blev bevidst ændret 1/11 efter
  589 poster løj om arbejde der aldrig skete. Jeg rører ikke den mekanisme for
  at få mit eget fix til at se pænere ud.

## Bevis

- `tests/test_initiativ_godkendelse_trigger.py` — 2 tests. Én måler at et
  netop forsøgt projekt **ikke** er due, og at godkendelsen gør det due. Én
  måler at `status` forbliver `pending` (modsat abandon).
- **Mutation:** fjernes `next_attempt_at=now` fra `endorse`, fejler testen med
  *«godkendelsen gjorde ikke projektet due — saa har den ingen arvtager»*.
  Gendannet og verificeret.
- 109 grønne i initiativ-fladen.
- **Målt i den levende base** efter kørslen: `due_foer: []` → `due_efter:
  ["life-b014cdb308"]`. Godkendelsen virker nu ende-til-ende.

## Kendt grænse

`endorse` var død kode siden den blev skrevet — den blev aldrig kørt af en test
før nu. Det er samme fejlklasse som ugen igennem: en mekanisme der ser ud som
om den virker, fordi ingen målte den. Jeg fandt den kun ved at læse
db-lagets signatur, ikke ved at læse kaldsstedet.
