# Push-suppressionen efterlader nu et spor (7/11-2026)

## Hullet

Målt 7/11-2026 kl. 13:41:14 i den levende DB: et `push.web_sent` med
`kind: run_done` havde **tomt `run_id`** — selv om notifikationen samme sekund
havde `ref=autonomous-0c6c92db3ef94674bd446b473b0abeed`.

To ting var galt på én gang:

1. **`_maaske_push` byggede payloaden uden `run_id`.** `_push_to_web` skriver
   `data["run_id"]` ind i hver `push.web_*`-række, men feed-stien udelod
   nøglen. Hvert eneste push fra feed-stien fik derfor tomt `run_id` og kunne
   ikke knyttes til det run det gjaldt.
2. **Suppressionen returnerede uden at skrive noget.** `was_consumed_or_active`
   fyrede korrekt, men efterlod nul spor — så «undertrykt» og «aldrig kaldt»
   så ens ud i journalen. Det er samme tavshed som telemetri-fixet 6/11 skulle
   afskaffe, blot et lag længere inde.

## Ændringen

- `notifikations_emittere.py`: payloaden bærer nu `run_id` for `run_done` og
  `run_failed` (hvor `ref` ER run-id'et). For de andre slags er `ref` et
  forslags- eller godkendelses-id og må ikke forveksles med et run — der sendes
  tom streng.
- `notifikations_emittere.py`: suppressionen skriver `push.web_skipped` med
  `reason: "seen_live"` og det undertrykte `run_id`, før den returnerer.

## Fravalg

- **Ingen ændring af selve suppression-politikken.** Den fyrede korrekt; det
  var sporet der manglede. At hæve eller sænke tærsklen er en anden beslutning.
- **Ingen `run_id` for `approval`/`proposal`.** Deres `ref` er ikke et run, og
  at skrive det ind i et `run_id`-felt ville gøre telemetrien misvisende —
  samme fejlklasse som at blande id-rummene i `users` og `web_push_subscriptions`.

## Bevis

- 3 nye tests i `tests/test_push_suppression_spor.py`
- **To mutationer fælder dem:** fjernes `run_id` fra payloaden, fejler
  `test_run_id_foelger_med_i_payloaden`; fjernes skip-sporet, fejler
  `test_suppression_efterlader_seen_live_spor`
- 78 grønne i notifikations-fladen. Én fejl
  (`test_genudsendt_fra_stille_koe_dobler_ikke_feed_raekken`) er **bevist
  præeksisterende** — den fejler identisk på ren HEAD og er klokke-afhængig:
  `_indsaet_koe` skriver med virkelig tid, mens testen kalder
  `fire_due_delayed("12:00")`.

## Kendt grænse

`was_consumed_or_active` læser `_RUNS`, en **in-memory** dict. Er runnet pruned
eller er runtime genstartet, svarer den `False` — og så sendes pushet. Det er
den rigtige retning (et tabt svar er værre end et ekstra push), men det betyder
at suppressionen ikke kan undertrykke på tværs af en genstart. Det er ikke
ændret her.
