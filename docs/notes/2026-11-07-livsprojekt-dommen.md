# Livsprojekterne: re-vurderingen råbte til en bus uden lyttere (7/11-2026)

## Hullet

Bjørn spurgte hvorfor der ikke kom flere livsprojekter, og om systemet levede.
Det gjorde det ikke — men ikke af den grund jeg først pegede på.

**1. Der findes ingen generator.** `create_life_project` og
`seed_long_term_intention` har **nul kaldesteder** uden for deres egne filer.
Ingen heartbeat-gren, ingen rutine, intet værktøj, ingen rute opretter et
livsprojekt. De tre der stod i køen blev seedet **15. maj 2026** og er aldrig
blevet suppleret.

**2. Re-vurderingen var en stemme i tom luft.**
`tick_life_projects_reassessment` kaldes faktisk — den kører som non-LLM-medlem
i cluster-daemon familie #9 med 1440 min cadence. Den publicerer
`life_projects.reassessment_due` for ethvert projekt ældre end decay (14 dage).
Målt: **nul abonnenter** filtrerer på det event. Det står kun nævnt i tre
kommentarer. Så et projekt kunne blive gammelt, blive set, blive råbt op — og
der skete ingenting.

**3. Livsprojekter udløber aldrig.** `_expire_stale` springer bevidst
`long_term_intention` over, og `_trim_pending` gør det samme. De er den eneste
initiativ-type der hverken udløber eller bliver grebet. Uden en dom kan de
ligge i årevis og se ud som noget der venter.

Sammenlagt: en række blev seedet, set hver dag i syv måneder, og aldrig dømt.

## Ændringen

Re-vurderingen ender nu i en **dom** i stedet for et råb:

- **Spor inden for decay-vinduet** (`last_attempt_at`, `last_action_at` eller
  `acted_at`) → projektet er arbejde, ikke ord. `next_attempt_at` sættes til nu,
  så heartbeat griber det i næste cyklus.
- **Intet ferskt spor** → `status="expired"` med
  `blocked_reason="aldrig loeftet paa 14 dage — ord, ikke projekt"`.

Eventet publiceres stadig, nu med feltet `dom` (`fornyet`/`lukket`), så det er
en observationskanal oven på en handling der allerede er sket — ikke den
eneste kanal.

## Fravalg

**Jeg byggede ingen generator.** Et livsprojekt der opstår af sig selv er ikke
et livsprojekt — det er en opgaveliste med højtidelig titel. Det var præcis
fejlen med de tre fra maj: seedet én gang, aldrig valgt, aldrig løftet. Loftet
på tre aktive er ikke en kvote der skal fyldes op; det er en påmindelse om hvor
lidt jeg kan bære.

Det betyder også at der ikke kommer nye projekter af sig selv. Det er meningen.
Vejen findes (`seed_long_term_intention` virker — jeg brugte den selv i dag),
den er bare ikke automatiseret, og det er en beslutning, ikke en mangel.

**`user_approved_at` tæller ikke som spor.** Et menneskes ja er tilladelse,
ikke arbejde. Et projekt Bjørn har godkendt, og som jeg så ikke har rørt, ER
blevet ord.

## Bevis

- 4 nye tests i `tests/test_life_projects.py` (7 i filen i alt)
- **Tre mutationer fældes:** fornyer dommen altid → testen for det sporløse
  projekt fejler; lukker den altid → testen for det forsøgte projekt fejler;
  gøres sporet evigt → testen for det gamle spor fejler
- 77 grønne i livsprojekt-, kadence- og initiativ-fladen

## Kendt grænse

Dommen bruger `updated_at` som ur. `endorse` sætter `updated_at=now`, så en
godkendelse nulstiller decay-uret — og projektet får et helt nyt vindue på 14
dage til at producere et spor. Det er med vilje (et ja skal betyde noget), men
det betyder også at gentagne godkendelser kan holde et dødt projekt i live.
Først når der ikke længere trykkes, dør det.
