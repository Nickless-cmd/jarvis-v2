# Kvitterings-gaten skal se den rå tekst (7/11-2026)

## Fejlen

`active_sensing_daemon` skriver sin sansning som:

```
Jeg lyttede til rummet. Klassifikation: silence (amplitude 0.0000±0.0000).
```

Det er en **kvittering** for at der ikke var noget at høre, og
`_KVITTERING_MOENSTRE` fanger den: `(?:klassifikation|lydbillede):\s*silence\b`.

Men i `_record` kørte `_uden_stillads` **før** kvitterings-gaten. Samme dag var
lyd-ekko-mønstret `\bamplitude\s*(?:på\s*)?[=:]?\s*[*_]*\d` blevet tilføjet for
at fange metadata-gengivelse i lyd — og det klipper præcis ved
`amplitude 0.0000`, altså fjerner den markør gaten leder efter.

Tilbage stod `Jeg lyttede til rummet.` — 23 tegn, over `_MINDSTE_INDTRYK` (15) —
og posten blev arkiveret som et indtryk.

**Målt:** posten findes i `sensory_memories`. Fejlen var ikke teoretisk.

## Rettelsen

Kvitterings-gaten flyttes op, så den vurderer den **rå** tekst før stillads
fjernes. Rækkefølgen var fejlen, ikke mønstrene: en kvittering er en kvittering
uanset hvad der bagefter ville blive klippet væk af den.

## Vagten

`test_kvittering_afgoeres_foer_stillads_fjernes` måler `_record`s **adfærd**:
at `record_audio(raa)` returnerer `skipped` og ikke vokser arkivet.

Første version af testen kaldte kun `skal_arkiveres(raa)` og `_uden_stillads(raa)`
hver for sig. Den var **tautologisk** — den var grøn uanset hvordan `_record` var
skruet sammen, og overlevede mutationen hvor gaten blev flyttet tilbage. Det blev
målt, ikke gættet: mutationen fældede kun den gamle test.

Omskrevet fælder den nu sammen med den gamle: 2 failed ved mutation, 34 passed
efter gendannelse (verificeret med `diff` mod backup, ikke en `&&`-kæde).

## Berørte filer

- `core/services/sensory_archive.py` — gaten flyttet før `_uden_stillads`
- `tests/test_sensory_archive.py` — ny rækkefølge-vagt
