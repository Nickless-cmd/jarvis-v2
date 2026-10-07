# Varige formater

47 nøgler skrives til disken under `~/.jarvis-v2/state/`, spredt ud over hele
træet. Før 20/9-2026 fandtes der ingen fortegnelse: ingen kunne svare på
«hvad skriver vi egentlig til disken, og hvem ejer det» uden at grepe.

DeepSeek-harness kræver en DATERET record for hver ændring i et persisteret
format, med en tvungen klassifikation — et nyt valgfrit felt er `same-version`;
omdøb eller fjern er `version-bump`. Samme dag jeg læste det, havde jeg selv
indført `device_presence.json` uden at registrere det nogen steder. Der var
intet sted at registrere det.

`register.json` er det sted. Hver nøgle har en ejer, en beskrivelse og en
dato. `scripts/verify_persistens.py` afviser et format der skrives eller
læses uden at stå der — og melder når en registreret nøgle ikke længere
røres, for så ligger der måske stadig data på disken.

## Hvad registret IKKE kan

Det ser at en NØGLE opstår eller forsvinder. Det ser **ikke** at et FELT inde
i en nøgle skifter form. Harness kan, fordi TypeScript giver dem en typegraf
at hashe; Python-dicts giver ingen. Det er en ægte begrænsning, og den bliver
ikke mindre af at blive fortiet.

Ændrer du et felt i et format der allerede står her, er det derfor dit eget
ansvar at skrive en note under `docs/notes/implementeret/arkitektur/` om hvad
gamle filer på disken gør når den nye kode læser dem. `device_presence`
dropper poster ældre end sin TTL og ignorerer ukendte felter; det er den slags
beslutning der skal stå et sted.

## Beskrivelserne

De kommer fra ejer-modulets egen docstring. En «UDFYLD»-plads bliver aldrig
udfyldt, mens modulets egen tekst allerede er skrevet af nogen der vidste
hvad filen var til. Tre moduler har ingen docstring; de står som efterslæb og
blokerer ikke.

## SQLite-skemaet på CT105

`sqlite-schema.json` er et snapshot fra CT105's levende database, læst i
read-only-tilstand. Det registrerer kolonner og indeks med et SHA-256-digest
pr. tabel (kolonadskilte hex-bytes). Snapshottet har 304 applikationstabeller;
SQLite's interne `sqlite_sequence` er udeladt. `source_host` dokumenterer hvor
snapshottet blev taget.

`scripts/verify_sqlite_schema.py` sammenligner mod snapshottet. Pre-commit
kører den kun på CT105 (`Jarvis`), fordi udviklermaskinens DB har andre
tabeller. Brug `--require-db` ved en eksplicit audit. Undersøg en migration,
før `--write-snapshot` køres på CT105; en snapshot-opdatering er en anmeldelse
af ændringen, ikke selve migrationen.

`created_at_formats` bygger på de første og sidste tre ikke-tomme værdier i
hver tabel. Den prøvesamling fanger almindelig fremadrettet drift, men beviser
ikke at alle historiske rækker har samme format. `unobserved` betyder ingen
værdi endnu; `unknown` kræver manuel undersøgelse. Kode der sammenligner datoer
på tværs af tabeller skal normalisere tidsstemplerne.
