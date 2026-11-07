# Centralens egne tilstands-lag koblet + silence-anker (7/11-2026)

To leverancer i én commit (docs-drift-hooken sammenligner staged-træet med
de genererede docs — del-commits rammer derfor «stale», målt to gange).

## 1: `GET /central/central-state`

72 flader med `central`-præfiks stod uden indgang i de syv aggregatorer og
i central_hub. Rodårsagen var ikke at de var døde: `central_hub._SURFACE_GROUPS`
peger på navne i `cognitive_architecture_surface`, og den funktion kalder
IKKE `build_*_surface`-funktionerne — navnene findes to steder der ikke taler
sammen. Derfor så de synlige ud i én måling og var mørke i den næste.

Alle 72 kaldt før registrering: 72/72 leverer, 0 fejl, 0 tomme.
`build_layer_surface` udeladt med grund (kræver positionelt argument).
Aggregator: `core/services/central_state_surface.py`.

## 2: silence-markøren ankeret til producer-formen

Anden måling samme aften: fuldtekst-mønsteret forkastede også blandet tekst
— «Der er en svag summen fra køleskabet. Klassifikation: silence …» — og et
ægte indtryk gik tabt i den regnsed der skulle redde det fra. Nu tæller
silence kun når HELE teksten er kvitteringen: markøren ankeret til den
kendte producer-form fra `active_sensing_daemon`.

## Tests

`tests/test_central_state_surface.py`: registrering af alle 72, gruppering,
isolation af kastende producent (patcher producenten, ikke fangeren).
`tests/test_sensory_archive.py::test_blandet_silence_arkiveres`: den
blandede tekst arkiveres; mutationstest beviser den fælder fuldtekst-formen.
