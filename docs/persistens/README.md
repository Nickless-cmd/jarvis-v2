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
