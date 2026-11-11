# Heartbeat-stilstand 2026-11-11 — findings

## Målt (fra opgavebeskrivelsen, IKKE selv verificeret af executor)
- state: scheduler_active=1, health=active, started 19:15:40Z, next_tick 19:29:34Z.
- Nyeste tick id 10353, 19:14:13Z–19:14:34Z. Intet slag derefter.

## IKKE målt af executor (ingen shell/DB/journal-adgang i denne kørsel)
- `is_running()` / `iterations()` på den levende proces.
- Journalen (`heartbeat scheduler loop entered`, `HEARTBEAT-LOOP: iteration=`).
- Årsag: **årsag ikke fundet.** Afgrænsning ud fra kode: den indledende
  `_poll_heartbeat_schedule_with_trigger` kører FØR while-løkken, med
  `_ITERATION == 0`, og tick-tråden er afgrænset til 90 s — så et hængende
  startpoll alene forklarer ikke 68 min. Kandidater at måle: tråd død (proces
  dræbt/start-exception efter state-skrivning) vs. løkke der tæller uden slag.
  Måling: `iterations()` to gange med 60 s mellemrum + journal-grep.

## Fejlformen (verificeret i kode)
`_prepare_scheduler_startup` skrev `scheduler_health="active"` før tråden havde
gennemført nogen iteration, og `heartbeat_status` læste kun flaget.
Desuden: `is_running()` er proces-lokal. Kører `heartbeat_status` i en anden
proces end API'et (hvor scheduleren startes), vil den altid melde
`flag_active_but_thread_not_running` → DEGRADED. Skal verificeres.
