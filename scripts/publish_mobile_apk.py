#!/usr/bin/env python
"""Læg en ny mobil-APK op — og behold præcis én version tilbage.

Publiceringen var håndarbejde: scp APK'en op, skriv `latest.json`, håb på at
navnet passede. To ting gik galt ved det, og begge er der nu værn imod.

**1. Der blev ikke ryddet.** Mappen voksede til 1,3 GB i 13 APK'er hvoraf én
var i brug. Scriptet sletter alt undtagen den nye og den forrige.

**2. Der blev ryddet for hårdt.** Da der endelig blev ryddet, blev ALT på nær
den nye slettet — og dermed forsvandt muligheden for at pege `latest.json`
tilbage på en version der virkede. Ét skridt tilbage koster 100 MB og er den
eneste rullebane der findes.

Scriptet genstarter INTET. `mobile_update.py` læser manifestet ved hvert kald,
så en ny APK er synlig i samme øjeblik filen ligger der.

Brug:

    python scripts/publish_mobile_apk.py \
        --apk apps/mobile/android/app/build/outputs/apk/release/app-release.apk \
        --version 0.2.29 --version-code 130 \
        --notes "Hvad brugeren faktisk får ud af det." \
        --host bs@10.0.0.39

Uden `--host` arbejdes der i den lokale `--dir` (standard ~/.jarvis-v2/mobile).
`--dry-run` viser hvad der ville ske uden at røre noget.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

APK_MOENSTER = re.compile(r"^jarvis-mobile-(\d+)\.apk$")


def apk_navn(version_code: int) -> str:
    return f"jarvis-mobile-{version_code}.apk"


def vaelg_hvad_der_slettes(
    filer: list[str], ny: str, forrige: str | None
) -> tuple[list[str], list[str]]:
    """Hvilke APK'er beholdes, og hvilke ryger?

    Ren funktion med vilje: det er DEN beslutning der sletter data, og den skal
    kunne prøves af uden en server i den anden ende.

    Beholder den nye og den forrige (det navn manifestet pegede på før). Er de
    to det samme — en genudgivelse af samme version — beholdes den næstnyeste i
    stedet, så der stadig ER et skridt tilbage.
    """
    apk = sorted(
        (f for f in filer if APK_MOENSTER.match(f)),
        key=lambda f: int(APK_MOENSTER.match(f).group(1)),  # type: ignore[union-attr]
        reverse=True,
    )
    behold = [ny]
    if forrige and forrige != ny and forrige in apk:
        behold.append(forrige)
    else:
        for f in apk:
            if f not in behold:
                behold.append(f)
                break
    return behold, [f for f in apk if f not in behold]


def _kald(host: str | None, kommando: str, *, dry: bool) -> str:
    """Kør en kommando lokalt eller på host. Returnerer stdout."""
    argv = ["ssh", host, "bash", "-c", shlex.quote(kommando)] if host else ["bash", "-c", kommando]
    if dry:
        print("  [dry-run] " + (" ".join(argv) if host else kommando))
        return ""
    res = subprocess.run(argv, capture_output=True, text=True)
    if res.returncode != 0:
        raise SystemExit(f"kommando fejlede: {kommando}\n{res.stderr.strip()}")
    return res.stdout


def hovedet(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apk", required=True, help="sti til den byggede APK")
    p.add_argument("--version", required=True)
    p.add_argument("--version-code", required=True, type=int)
    p.add_argument("--notes", required=True, help="hvad brugeren får ud af det — i klar tekst")
    p.add_argument("--host", default="", help="fx bs@10.0.0.39; tom = lokalt")
    p.add_argument("--dir", default="~/.jarvis-v2/mobile")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)

    apk = Path(a.apk)
    if not apk.is_file():
        raise SystemExit(f"findes ikke: {apk}")
    host = a.host or None
    maal = a.dir
    navn = apk_navn(a.version_code)

    # Manifestet FØR vi rører noget — det er det der udpeger «den forrige».
    raa = _kald(host, f"cat {maal}/latest.json 2>/dev/null || true", dry=False)
    try:
        forrige = str(json.loads(raa).get("filename") or "") or None
    except Exception:
        forrige = None
    print(f"forrige udgave: {forrige or '(ingen)'}")

    # Læg APK'en op FØR manifestet peger på den. Omvendt rækkefølge ville give
    # et vindue hvor manifestet lover en fil der ikke er ankommet endnu.
    print(f"lægger op: {navn} ({apk.stat().st_size / 1048576:.0f} MB)")
    if not a.dry_run:
        dest = f"{host}:{maal}/{navn}" if host else f"{maal}/{navn}"
        argv_scp = ["scp", "-q", str(apk), dest] if host else ["cp", str(apk), Path(maal).expanduser() / navn]
        res = subprocess.run([str(x) for x in argv_scp], capture_output=True, text=True)
        if res.returncode != 0:
            raise SystemExit(f"upload fejlede: {res.stderr.strip()}")
    else:
        print(f"  [dry-run] scp {apk} → {maal}/{navn}")

    # Gem det gamle manifest ved siden af. At beholde den forrige APK er kun
    # den halve rullebane — uden manifestet skal det skrives i hånden igen.
    # Navnet fandtes allerede i mappen fra tidligere håndarbejde; det genbruges.
    _kald(host, f"test -f {maal}/latest.json && cp {maal}/latest.json {maal}/latest.json.forrige || true",
          dry=a.dry_run)

    manifest = json.dumps({
        "version": a.version, "version_code": a.version_code,
        "notes": a.notes, "filename": navn,
    }, ensure_ascii=False)
    _kald(host, f"cat > {maal}/latest.json <<'JSON'\n{manifest}\nJSON", dry=a.dry_run)

    filer = [f for f in _kald(host, f"ls -1 {maal} 2>/dev/null", dry=False).split() if f]
    if a.dry_run and navn not in filer:
        filer.append(navn)          # så oprydningen kan vises realistisk
    behold, slet = vaelg_hvad_der_slettes(filer, navn, forrige)
    print("beholder: " + ", ".join(behold))
    if slet:
        print("sletter:  " + ", ".join(slet))
        _kald(host, "rm -f -- " + " ".join(f"{maal}/{f}" for f in slet), dry=a.dry_run)
    else:
        print("sletter:  (intet)")

    if a.dry_run:
        return 0

    # Efterprøv at det der ligger der, ER det manifestet lover.
    tjek = _kald(host, f"cat {maal}/latest.json; echo; stat -c%s {maal}/{navn}", dry=False).strip().splitlines()
    stoerrelse = int(tjek[-1])
    if stoerrelse != apk.stat().st_size:
        raise SystemExit(f"AFVIGELSE: {navn} er {stoerrelse} bytes, kilden er {apk.stat().st_size}")
    print(f"efterprøvet: {navn} {stoerrelse} bytes — manifest og fil passer sammen")
    print("ingen service genstartet: manifestet læses ved hvert kald")
    if len(behold) > 1:
        print(f"rul tilbage med:  cp {maal}/latest.json.forrige {maal}/latest.json")
    return 0


if __name__ == "__main__":
    sys.exit(hovedet())
