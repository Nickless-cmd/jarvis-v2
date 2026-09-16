#!/usr/bin/env python3
"""Opgørelse fra vaertens crash-beacon-log.

Beacon'en (/usr/local/sbin/crash-beacon.sh paa 10.0.0.36) skriver én linje hvert
5. sekund. Loggen er raa maaledata; det her er det der skal siges om et doegn:
genstartede den, hvor varm blev den, og holdt pumpen.

HVORFOR PROEVETAKTEN STAAR I RAPPORTEN
--------------------------------------
15/9-2026 sagde jeg at vaerten koelede hurtigere end foer, og at det maatte
betyde at de nye blaesere og kolepastaen virkede. Det holdt ikke: beacon'en var
i mellemtiden gaaet fra 20- til 5-sekunders proever, saa den nye kurve havde
fire gange saa mange punkter og ramte derfor lavere minimum i samme tidsrum.
Forskellen var min maalemetode, ikke haardwaren.

Derfor staar proevetakten ved HVERT vindue, og en sammenligning mellem to
vinduer med forskellig takt bliver mærket som usammenlignelig. Et tal uden sin
maalemetode er ikke et tal man kan konkludere paa.

Brug:
    python scripts/beacon_rapport.py                      # sidste doegn
    python scripts/beacon_rapport.py --timer 12
    python scripts/beacon_rapport.py --sammenlign         # doegnet foer ved siden af
    ssh root@10.0.0.36 cat /var/log/crash-beacon.log | python scripts/beacon_rapport.py -
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta

STANDARD_LOG = "/var/log/crash-beacon.log"

_TAL = r"[-+]?\d+(?:\.\d+)?"
_FELT = re.compile(rf"(\w+)=({_TAL})")


@dataclass
class Proeve:
    tid: datetime
    uptime: float
    pkg_c: float | None = None
    hot_c: float | None = None
    sys_c: float | None = None
    gpu_c: float | None = None
    gpu_w: float | None = None
    mem_kb: float | None = None
    blaesere: dict[str, float] = field(default_factory=dict)


def _parse_tid(raa: str) -> datetime | None:
    try:
        return datetime.fromisoformat(raa)
    except ValueError:
        return None


def parse_linje(linje: str) -> Proeve | None:
    """Én beacon-linje → Proeve. None hvis linjen ikke er en maaling.

    Linjer uden tidsstempel (fx beacon'ens egne opstartsnoter) springes over —
    de er ikke maalinger, og at tælle dem med ville forskyde proevetakten.
    """
    dele = linje.strip().split(None, 1)
    if len(dele) < 2:
        return None
    tid = _parse_tid(dele[0])
    if tid is None:
        return None

    rest = dele[1]
    felter = {navn: float(vaerdi) for navn, vaerdi in _FELT.findall(rest)}
    if "up" not in felter:
        return None

    p = Proeve(
        tid=tid,
        uptime=felter["up"],
        pkg_c=felter.get("pkgC"),
        hot_c=felter.get("hotC"),
        sys_c=felter.get("sysC"),
        mem_kb=felter.get("memkB"),
        blaesere={n: v for n, v in felter.items() if n.startswith("fan")},
    )
    # gpuW_C=11.61,38 — watt og grader i ét felt, komma imellem.
    gpu = re.search(rf"gpuW_C=({_TAL}),({_TAL})", rest)
    if gpu:
        p.gpu_w = float(gpu.group(1))
        p.gpu_c = float(gpu.group(2))
    return p


def find_genstarter(proever: list[Proeve]) -> list[datetime]:
    """Et FALD i uptime = maskinen har vaeret nede imellem to proever.

    Det er den eneste kilde der overlever et haardt crash: journalen skriver
    intet, men uptime-taelleren starter forfra.
    """
    genstarter: list[datetime] = []
    for foer, efter in zip(proever, proever[1:]):
        if efter.uptime < foer.uptime:
            genstarter.append(efter.tid)
    return genstarter


def _tal(vaerdier: list[float], andel: float) -> float | None:
    if not vaerdier:
        return None
    s = sorted(vaerdier)
    i = min(len(s) - 1, max(0, round(andel * (len(s) - 1))))
    return s[i]


def proevetakt_sekunder(proever: list[Proeve]) -> float | None:
    """Median-afstand mellem to proever. Rapportens vigtigste tal ved en
    sammenligning — se modulets note."""
    if len(proever) < 3:
        return None
    afstande = [
        (efter.tid - foer.tid).total_seconds()
        for foer, efter in zip(proever, proever[1:])
        if efter.uptime >= foer.uptime          # spring genstarts-hullet over
    ]
    return _tal(afstande, 0.5)


def pumpekanal(proever: list[Proeve]) -> str | None:
    """Pumpen er den hurtigste kanal. Den flyttede fra fan5 til fan2 15/9-2026,
    og en haardkodet kanal gav en falsk alarm paa hans telefon. Find den i
    stedet for at vide den."""
    if not proever:
        return None
    bedste, hoejeste = None, 0.0
    for navn in proever[0].blaesere:
        vaerdier = [p.blaesere.get(navn, 0.0) for p in proever]
        median = _tal(vaerdier, 0.5) or 0.0
        if median > hoejeste:
            bedste, hoejeste = navn, median
    return bedste


def opgoer(proever: list[Proeve]) -> dict:
    if not proever:
        return {"proever": 0}
    pumpe = pumpekanal(proever)
    pumpe_rpm = [p.blaesere.get(pumpe, 0.0) for p in proever] if pumpe else []

    def stat(haent) -> dict:
        v = [x for x in (haent(p) for p in proever) if x is not None]
        return {"median": _tal(v, 0.5), "p95": _tal(v, 0.95), "maks": max(v) if v else None,
                "min": min(v) if v else None}

    return {
        "proever": len(proever),
        "fra": proever[0].tid,
        "til": proever[-1].tid,
        "takt_s": proevetakt_sekunder(proever),
        "genstarter": find_genstarter(proever),
        "cpu": stat(lambda p: p.pkg_c),
        "hotspot": stat(lambda p: p.hot_c),
        "kabinet": stat(lambda p: p.sys_c),
        "gpu_c": stat(lambda p: p.gpu_c),
        "gpu_w": stat(lambda p: p.gpu_w),
        "pumpe_navn": pumpe,
        "pumpe_min": min(pumpe_rpm) if pumpe_rpm else None,
        "pumpe_median": _tal(pumpe_rpm, 0.5),
        "fri_ram_gb": (min(p.mem_kb for p in proever if p.mem_kb) / 1024 / 1024)
        if any(p.mem_kb for p in proever) else None,
    }


def _linje(navn: str, s: dict, enhed: str) -> str:
    if s.get("median") is None:
        return f"  {navn:12s} ingen data"
    return (f"  {navn:12s} median {s['median']:.0f}{enhed}"
            f"   p95 {s['p95']:.0f}{enhed}   maks {s['maks']:.0f}{enhed}")


def skriv(rapport: dict, titel: str) -> None:
    print(f"\n{titel}")
    if not rapport.get("proever"):
        print("  ingen maalinger i vinduet")
        return
    takt = rapport["takt_s"]
    print(f"  {rapport['proever']} proever fra {rapport['fra']:%d/%m %H:%M} "
          f"til {rapport['til']:%d/%m %H:%M}   (takt {takt:.0f}s)"
          if takt else f"  {rapport['proever']} proever")
    g = rapport["genstarter"]
    if g:
        print(f"  GENSTARTER: {len(g)} — " + ", ".join(f"{t:%d/%m %H:%M:%S}" for t in g))
    else:
        print("  genstarter:  ingen")
    print(_linje("CPU", rapport["cpu"], " C"))
    print(_linje("hotspot", rapport["hotspot"], " C"))
    print(_linje("kabinet", rapport["kabinet"], " C"))
    print(_linje("GPU", rapport["gpu_c"], " C"))
    print(_linje("GPU effekt", rapport["gpu_w"], " W"))
    if rapport["pumpe_navn"]:
        print(f"  pumpe        {rapport['pumpe_navn']}: median "
              f"{rapport['pumpe_median']:.0f} RPM, lavest {rapport['pumpe_min']:.0f} RPM")
    if rapport["fri_ram_gb"]:
        print(f"  fri RAM      mindst {rapport['fri_ram_gb']:.1f} GB")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("log", nargs="?", default=STANDARD_LOG,
                   help="sti til beacon-loggen, eller - for stdin")
    p.add_argument("--timer", type=float, default=24.0, help="vinduets laengde (default 24)")
    p.add_argument("--sammenlign", action="store_true",
                   help="vis det foregaaende vindue ved siden af")
    args = p.parse_args()

    raa = sys.stdin.read() if args.log == "-" else open(args.log, encoding="utf-8",
                                                        errors="replace").read()
    alle = [x for x in (parse_linje(l) for l in raa.splitlines()) if x]
    if not alle:
        print("ingen maalinger fundet i loggen")
        return 1

    slut = alle[-1].tid
    start = slut - timedelta(hours=args.timer)
    nu = [p for p in alle if p.tid >= start]
    skriv(opgoer(nu), f"SIDSTE {args.timer:.0f} TIMER")

    if args.sammenlign:
        foer_start = start - timedelta(hours=args.timer)
        foer = [p for p in alle if foer_start <= p.tid < start]
        r_foer, r_nu = opgoer(foer), opgoer(nu)
        skriv(r_foer, f"DE {args.timer:.0f} TIMER FOER")
        t1, t2 = r_foer.get("takt_s"), r_nu.get("takt_s")
        if t1 and t2 and abs(t1 - t2) > 1:
            print(f"\n  ADVARSEL: proevetakten er IKKE ens ({t1:.0f}s mod {t2:.0f}s).")
            print("  Minimum og maksimum kan ikke sammenlignes paa tvaers — flere")
            print("  proever rammer lavere og hoejere af sig selv. Brug medianen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
