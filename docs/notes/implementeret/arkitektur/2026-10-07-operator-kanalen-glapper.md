---
status: implementeret
slags: arkitektur
dato: 2026-10-07
forfatter: jarvis
kilde: codex' afbrudte arbejde (patch sikret i /home/bs/codex-operator-channel-guard-20261007.patch)
---

# Operator-kanalen glappede: forældet læsning, tabt skriv og en forkert nøgle

Status: implementeret

## Problem

Bjørn 7/10-2026: «operator kanalen.. den er virkelig ustabil og glipper ofte».
Og, i samme åndedrag: «det værn der skyder forkert hele tiden og siger han ikk
har kaldt et tool».

Fire fejl i kanalen, alle målt i den kode der kørte — plus to i værnet.

1. **Forældet læsning.** `_load()` gik gennem `get_runtime_state_value`, som har
   en 2-sekunders proces-lokal cache. En cachet «lukket» sendte en
   workstation-kommando til containeren — uden et ord.
2. **Tabt skriv.** `_save()` skrev HELE ordbogen tilbage efter et
   læs-sæt-skriv. To processer (api + runtime) med hver sin cache kunne derfor
   skrive hinandens arbejde væk: en frisk åbning blev slettet af en anden
   skrivers forældede billede. **Det er den målte årsag til «glipper ofte»** —
   min egen kanal stod `open=False` uden at nogen havde lukket den.
3. **Tavs fejl.** `_load` og `_save` slugte begge DB-fejl. En åbning der ikke
   blev gemt, blev kvitteret som «åben»; en læsefejl blev til «lukket».
4. **Forkert nøgle.** Desk'ens kontakt (`WorkbenchSection.tsx:41`) og mobilens
   «Luk» sendte intet session-id, så serveren faldt til `_default` — mens bash
   bruger `chat-<session>`. Panelet viste «Åben» om en kanal bash aldrig så.

I værnet: `_PROMISE_RE` blev matchet mod HELE teksten, så «jeg vil ikke kalde et
værktøj» blev læst som et løfte om at kalde ét. Og nudge-teksten påstod «du
kaldte INTET værktøj i denne tur», selv når tidligere runder i samme run havde
kaldt flere.

## Beslutning

**Kanalen skriver én nøgle ad gangen.** `_opdater_post` læser og skriver i én
`BEGIN IMMEDIATE`-transaktion, læser uden om cachen, og **kaster** ved fejl.
Kalderne fanger og svarer `status: error` — en kvittering på noget der ikke blev
gemt er præcis den tavse fejl kanalen skal være fri for.

`is_open()` kaster bevidst ved læsefejl. Returnerede den `False`, ville
`maybe_reroute_bash` svare «kanalen er lukket» og køre Bjørns kommando på
containeren i det stille.

`_exec_bash` er fail-closed på **routing-beslutningen** — men noten er flyttet
ud af den blok. Den er kosmetisk, og et DB-hikke må ikke blokere al bash når
kanalen med sikkerhed er lukket og kommandoen hører hjemme her.

Serveren afviser open/close uden session-id med 400. Desk sender det id den
allerede havde i scope. Mobilen mangler det stadig → `side-64bc76c52c`.

Værnet: negation respekteres i `_FIRST_PERSON_ACTION`, og et afsluttet arbejde i
hale-sætningen gør et tidligere løfte afsluttet (`_COMPLETED_TAIL`).
Nudge-teksten påstår ikke længere nul kald i turen.

## Overvejede alternativer

* **Én nøgle pr. session i stedet for én JSON-blob.** Fravalgt: strukturelt den
  reneste — ingen læs-sæt-skriv overhovedet — men den ændrer lagerformatet og
  kræver migrering. Transaktionen fjerner samme fejlklasse uden migration.
* **Beholde hel-ordbog-skrivet og kun undgå cachen.** Fravalgt: det fjerner den
  forældede læsning, men ikke det tabte skriv — og det tabte skriv er den målte
  årsag til at en åbning forsvandt.
* **Lade `is_open()` svare `False` ved læsefejl.** Fravalgt: det er præcis den
  tavse tilbagefalden til containeren som hele modulet findes for at forhindre.
* **Give mobilen et gæt på session-id.** Fravalgt — den har intet i scope, og et
  gæt ville skrive en tredje forkert nøgle.
* **Slå kanalen helt fra indtil videre.** Fravalgt: den er Bjørns adgang til sin
  egen maskine, og fejlen er i tilstandshåndteringen, ikke i idéen.

## Konsekvenser

* **Tre mutationsbeviser:** fjernes garantien, FEJLER testen — tabt skriv,
  note-splittet og klientens session-id. En test der ikke kan fejle måler sin
  egen opsætning.
* 115 python-tests og 6 desk-tests grønne; `tsc --noEmit` rent; docs-drift clean.
* **Bash afhænger nu af DB'en i routing-blokken.** Det er prisen for
  fail-closed: er DB'en nede, kan ingen bash køre. Bevidst valgt — den
  alternative fejl er en kommando der kører på det forkerte sted.
* **Mobilens «Luk» giver nu 400 i stedet for en tavs no-op.** Ærligere, men
  knappen virker ikke før side-opgaven er løst.
* **Codex' arbejde var ucommitteret i `/tmp` på CheifOne** og ville være tabt ved
  genstart. Patchen er sikret byte-identisk to steder (`cc677f8c`), og hans
  fix er bevaret — jeg har smalnet det på ét punkt og lagt det atomare skriv
  ind.
