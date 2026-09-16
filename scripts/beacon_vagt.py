#!/usr/bin/env python3
"""Vagt paa vaertens beacon-log. Læser linjer fra stdin, skriver KUN hændelser.

    ssh root@10.0.0.36 'tail -F /var/log/crash-beacon.log' | python scripts/beacon_vagt.py

HVORFOR DEN FINDES
------------------
Foerste udgave af vagten var en regex skrevet i haanden direkte i
overvaagnings-kommandoen: `cpu[=: ]+(\\d+)` og `gpu[=: ]+(\\d+)`. Loggen
skriver `pkgC=57.0` og `gpuW_C=11.61,38`. Ingen af de to moenstre kunne
ramme noget som helst, og vagten koerte i en halv time og meldte «ingen
haendelser». Stilhed lignede ro og var i virkeligheden en doed maaling.

Derfor: vagten bruger den SAMME parser som rapporten, og den er testet.

TÆRSKLERNE
----------
«CPU 65+ VEDVARENDE» — ikke et enkelt udsving. Vaerten spidser rutinemæssigt
til 72 C i tomgang (maalt i dag: median 38, p95 60, maks 72), saa en alarm
paa én proeve ville vaere stoej hver time. Der skal VARIGHED til.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta

sys.path.insert(0, __file__.rsplit("/scripts/", 1)[0])
from scripts.beacon_rapport import parse_linje  # noqa: E402

CPU_GRAENSE = 65.0
CPU_VARIGHED_S = 30.0       # 6 proever i traek ved 5-sekunders takt
GPU_GRAENSE = 80.0
PUMPE_GRAENSE = 3000.0
STILHED_S = 300.0           # samme slags alarm gentages hoejst hvert 5. minut


def main() -> int:
    sidste_alarm: dict[str, datetime] = {}
    forrige = None
    cpu_siden: datetime | None = None

    def sig(slags: str, besked: str, tid: datetime) -> None:
        sidst = sidste_alarm.get(slags)
        if sidst and (tid - sidst).total_seconds() < STILHED_S:
            return
        sidste_alarm[slags] = tid
        print(f"{tid:%H:%M:%S} {besked}", flush=True)

    for linje in sys.stdin:
        p = parse_linje(linje)
        if p is None:
            continue

        # 1. Genstart: uptime falder. Det ENESTE spor et haardt crash efterlader.
        if forrige is not None and p.uptime < forrige.uptime:
            nede = (p.tid - forrige.tid).total_seconds()
            print(f"{p.tid:%H:%M:%S} VAERTEN ER GENSTARTET — nede ca. {nede:.0f}s "
                  f"(uptime {forrige.uptime:.0f}s → {p.uptime:.0f}s)", flush=True)
            sidste_alarm.clear()
            cpu_siden = None
        forrige = p

        # 2. CPU varmt LÆNGE. Et enkelt spids til 72 C er normal tomgang her.
        if p.pkg_c is not None and p.pkg_c >= CPU_GRAENSE:
            cpu_siden = cpu_siden or p.tid
            varighed = (p.tid - cpu_siden).total_seconds()
            if varighed >= CPU_VARIGHED_S:
                sig("cpu", f"CPU {p.pkg_c:.0f} C i {varighed:.0f}s i traek "
                           f"(hotspot {p.hot_c:.0f} C)", p.tid)
        else:
            cpu_siden = None

        # 3. GPU.
        if p.gpu_c is not None and p.gpu_c >= GPU_GRAENSE:
            sig("gpu", f"GPU {p.gpu_c:.0f} C ({p.gpu_w:.0f} W)", p.tid)

        # 4. Pumpen. Kanalen findes som den hurtigste — den flyttede fan5→fan2
        #    15/9-2026, og en haardkodet kanal gav en falsk alarm paa telefonen.
        if p.blaesere:
            kanal = max(p.blaesere, key=lambda n: p.blaesere[n])
            rpm = p.blaesere[kanal]
            if 0 < rpm < PUMPE_GRAENSE:
                sig("pumpe", f"PUMPE {kanal} nede paa {rpm:.0f} RPM", p.tid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
