# Heartbeat-stilstand 2026-11-11

## Konklusion

Scheduler-tråden døde ikke. Den påståede stilstand var et måleproblem: et
lokalt klokkeslæt omkring 20:22 CET blev sammenlignet direkte med UTC-tiderne i
DB'en. Den ene times forskel gjorde et 8 minutter gammelt tick til et 68
minutter gammelt tick og gjorde et tidspunkt 7 minutter i fremtiden til et
tidspunkt 53 minutter i fortiden.

Journalen blev læst med
`journalctl --directory=/var/log/journal/0def5f1e75fd4a4f87b1088b71c5d9ff/`
og UTC-output. Tjenesten blev ikke genstartet som del af undersøgelsen, og
runtime-DB'en blev kun læst.

## Faktiske målinger

- DB-række 10353 startede `2026-11-11T19:14:13.761854+00:00` og sluttede
  `19:14:34.466187+00:00`.
- PID 3334054 startede scheduler-løkken `19:15:40.081770Z` med
  `next_tick_at=19:29:34.466187Z`.
- Løkken talte uafbrudt fra iteration 1 kl. `19:16:10.231684Z` til iteration
  18 kl. `19:25:01.337686Z`. Omkring det rapporterede lokale klokkeslæt 20:22
  var den altså levende og talte videre (iteration 12 kl. `19:21:58.343283Z`
  og iteration 13 kl. `19:22:28.497370Z`).
- `next_tick_at=19:29:34Z` var på dette tidspunkt cirka 7 minutter i fremtiden,
  ikke 53 minutter overskredet. Seneste tick var cirka 8 minutter gammelt,
  ikke 68 minutter gammelt.
- Systemd bad processen lukke rent kl. `19:25:10Z`; journalen viser
  `Shutting down`, `heartbeat scheduler stopped` og `Finished server process`.
  Næste runtime PID 3339733 startede kl. `19:25:12Z`, talte fra iteration 1
  og observerede `due=True` kl. `19:29:45Z`.
- DB-rækkerne 10354/10355 dokumenterer det efterfølgende planlagte slag:
  start `19:29:45.430027Z`, slut `19:30:48.651262Z`.

De samtidige `database is locked`-tracebacks kom fra
`signal_tracking_framework._sweep_older_than`; heartbeat-iterationerne fortsatte
efter dem. Der er ingen journal-evidens for start-exception, sat `_STOP` eller en
uventet død scheduler-tråd i det undersøgte forløb.

`is_running()` og `iterations()` er proceslokale modulmålinger. De kan ikke
læses sandt fra en separat analyseproces; det ville måle analyseprocessens tomme
modulglobals. I ejerprocessen er de samme målinger eksponeret af
`heartbeat_status`, og den bevarede journal viser iterationsværdierne ovenfor.

## Lukning af fejlformen

- `heartbeat_status` dømmer allerede STALLED ud fra overskredet `next_tick_at`
  og viser et eksplicit mismatch, hvis ejerprocessen ser en død tråd.
- Startup-gennemløbet tælles nu, før `scheduler_health` sættes til `active`.
  Dermed kan `active` ikke observeres sammen med `iterations=0`.
- Status viser nu også, om den uafhængige watchdog-tråd lever i ejerprocessen.
- `heartbeat_runtime.start_heartbeat_scheduler()` starter både scheduler og
  watchdog. Watchdog-genstart kræver både STALLED og uændret iterationstal og
  skriver et `central_incidents`-incident med `severity="error"` før genstart.
