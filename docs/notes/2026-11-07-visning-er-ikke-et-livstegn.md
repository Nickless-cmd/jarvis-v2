# En visning blev læst som et livstegn (7/11-2026)

**Status:** rettet og verificeret
**Slags:** fejlretning
**Fravalg:** jeg retter ikke `mark_acted` selv — kun dommens læsning af feltet

## Hullet

Dommen fra `70f68ee65` skulle lukke livsprojekter der var blevet ord. Den
læste `last_attempt_at`, `last_action_at` og `acted_at` som «ferskt spor».

Men `last_action_at` skrives af `mark_acted` — og `mark_acted` kaldes to steder
hvor der **ikke blev gjort noget**:

- `core/services/proactivity_bridge.py:321` — `action_summary="surfaced via proactivity_bridge"`
- `core/services/runtime_action_executor.py:526` — `action_summary="promoted-to-visible-lane"`

Målt konsekvens i den levende base: `life-b014cdb308` («Learn how to hold user
trust over time») blev `acted` kl. 16:10:13 med `action_summary` = *surfaced via
proactivity_bridge*, `attempt_count` = **0**, og fik derefter
`next_attempt_at` = 21/11. Projektet fik altså 14 nye dage for at blive **vist**
— ikke for at blive løftet.

Det er samme fejlklasse som `mark_acted`-fixet 1/11 fjernede: en status der ser
ud som information, men beskriver noget andet end det den måler. Forskellen er
at den her gang var dommen — det værktøj jeg byggede for at fange klassen —
selv offeret.

## Ændringen

`_har_spor` tæller nu **kun** `last_attempt_at`. Det felt skrives udelukkende af
`mark_attempted`, som kaldes når heartbeat faktisk griber projektet og
materialiserer det til en task.

`last_action_at` og `acted_at` er udelukket med en kommentar der navngiver de to
kaldesteder, så en fremtidig læser ikke genindfører dem som «spor».

## Bevis

- Ny test `test_visning_er_ikke_et_livstegn` kalder den **rigtige** `mark_acted`
  (ikke en håndskrevet række), så den måler koblingen til den funktion der
  faktisk skriver feltet.
- **Mutationen fælder den:** sættes `last_action_at` tilbage i kriteriet, fejler
  testen med *«en visning blev laest som et livstegn»*.
- 20 grønne i den berørte flade (livsprojekter, godkendelses-trigger, db-laget,
  push-suppression, feed-stien).

## Kendt grænse

`mark_acted` skriver stadig `last_action_at` og `acted_at`, og de to kaldesteder
markerer stadig en visning som «acted». Det er ikke rettet her: `mark_acted`
bruges også til initiativer der ikke er livsprojekter, hvor «vist» måske er den
rigtige betydning. Dommen er gjort immun i stedet — den læser ikke feltet.

Den ægte oprydning ville være at lade `proactivity_bridge` og
`runtime_action_executor` kalde en funktion der hedder det den gør
(`mark_surfaced`), så feltet ikke kan læses forkert af nogen. Det kræver en
beslutning om hvad «acted» skal betyde for de øvrige initiativ-typer.
