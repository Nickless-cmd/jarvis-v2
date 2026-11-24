# Morgenbrief fyrede gentagne gange 24/11-2026

## Konklusion
`rec-2a7fcce8e0` fyrede kun én planlagt forekomst: 05:15:39 UTC. Dens
`next_fire_at` blev rykket til 25/11 05:15 UTC. De senere briefs kom ikke fra
`recurring_tasks`, men fra en gammel inbox-vækning for Routine-runnet
`run_d29e517a38324b759d95ecbf9c2d92c6` fra 12/11.

Den konkrete fejl er en sammensat inbox-fejl:

1. `inbox_idle_waker.kandidater()` læser `db_inbox.liste_aktiv()`
   (`core/services/inbox_idle_waker.py:152`). Visningen indeholder både åbne og
   nyligt lukkede poster (`core/runtime/db_inbox.py:1344-1379`). Kandidatfilteret
   kontrollerer ikke `status`; en `vaekning` erklæres moden ubetinget på
   `core/services/inbox_idle_waker.py:95-96`. Derfor blev den lukkede `drop`-post
   `vaek-run_d29e...` fra 12/11 valgt igen.
2. Den atomare markering `noter_vaekning()` returnerer `ikke_aaben` for posten,
   men returværdien ignoreres på `core/services/inbox_idle_waker.py:687-692`.
   Koden fortsætter til `_start_run()` på linje 695. Dermed starter en lukket
   post igen, og samtidige pollere kan også starte samme post flere gange.

## Faktiske recurring-rækker
Tabellen har felterne `task_id`, `next_fire_at`, `interval_minutes` og
`last_fired_at`; felterne `next_run_at`, `interval` og `last_run_at` findes ikke.
Eksakt fokus-match for Bjørns aktuelle morgenbrief: 1 række.

| task_id | status | next_fire_at | interval_minutes | last_fired_at | fire_count |
|---|---|---|---:|---|---:|
| rec-2a7fcce8e0 | active | 2026-11-25T05:15:00+00:00 | 1440 | 2026-11-24T05:15:39.126712+00:00 | 160 |

Der findes andre historiske/cancelled morgenbrief-rækker og aktive briefs for
Michelle/Mikkel, men ingen anden aktiv række med Bjørns aktuelle fokus.

## Kørselsspor og kaldesteder
Driften har seks, ikke fem, synlige `[ROUTINE WAKEUP]`-runs: 07:11:03,
14:13:52, 14:28:33, 14:46:37, 15:16:41 og 15:17:41 UTC. Alle seks completion-
events bærer samme gamle `task_id=run_d29e...`; dagens Routine-run er derimod
`run_32e2728...`, oprettet 05:15:39 med idempotency key
`recurring:2026-11-24T05:15:00+00:00` og status `succeeded`.

Det eneste produktionskald til `dispatch_recurring` er
`core/services/recurring_tasks.py:1119`; det kaldes af `_fire_due()` fra polleren
på linje 1176. API-starten er `apps/api/jarvis_api/app.py:378`.
Routine-scheduleren kører fra `core/services/routine_runtime.py:58-60`, men
springer legacy-linkede rutiner over på `core/services/routine_scheduler.py:144-150`.
Den gentagne faktiske trigger var inbox-wakeren, kaldt fra
`core/services/scheduled_tasks.py:521-526`, ikke heartbeat/autonomous wake.

## Minimal rettelse og regressionstest
Brug `db_inbox.liste(..., kun_aabne=True)` i `kandidater()` eller filtrér
eksplicit `status == aaben`; kræv desuden `noter_vaekning().status == "ok"` før
`_start_run()`. Test med én nyligt lukket `vaekning`-post og to samtidige kald:
nul runs for den lukkede post, og højst ét run for en åben post.

`_legacy`-returværdien er fortsat inkonsistent med kommentaren: `_advance`
kaldes ubetinget på `recurring_tasks.py:1129`, men det gav ikke gentagelserne.

Ikke afgjort: hvilken proces/poller der stod bag hvert enkelt starttidspunkt;
DB-sporet identificerer triggerpost og kodevej, men bærer ikke proces-id.
