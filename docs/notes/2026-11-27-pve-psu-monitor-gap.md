# PVE PSU-overvågning: verificeret hul 2026-11-27

`~/.jarvis-v2/state/pve_psu_monitor_state` må ikke slettes som om dens ansvar
var overtaget. Git-historikken indeholder ingen writer til filnavnet eller dens
felter, og den gamle writer er ikke længere i repoet.

Den nuværende dækning er kun delvis:

- `core/services/infra_sense.py` poller i9 (`10.0.0.36`) cirka hvert tredje
  minut og måler CPU-temperatur, pumpe-RPM, GPU-temperatur og uptime. Den
  registrerer ikke et fald i uptime som en reboot og måler ikke PSU-temperatur.
- Samme service poller M900/PVE (`10.0.0.2`) for gæster, disk/pool og load, men
  ikke temperatur eller PSU-telemetri.
- `scripts/beacon_vagt.py` og `scripts/vaert_boot_vagt.py` kan opdage og
  klassificere i9-genstarter, men ingen systemd- eller cron-wiring til dem blev
  fundet. `vaert_boot_vagt.json` var sidst skrevet 2026-11-17.
- Direkte SSH-verifikation fra assignment-containeren var blokeret af netværks-
  sandboxen, så hostens aktuelle `sensors`-output kunne ikke bekræftes.

Næste handling er at vælge en levende ejer: enten wire reboot-overgang fra
`infra_sense`/crash-beacon ind i Centralen og dokumentér at PSU-temperatur ikke
er eksponeret, eller etabler en host-sensor der faktisk leverer PSU-telemetri.
Først derefter kan den gamle state-fil slettes med dokumenteret erstatning.
