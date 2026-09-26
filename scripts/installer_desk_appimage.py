#!/usr/bin/env python
"""Installér desk-AppImage'en, og hold `.desktop` og AppArmor-profil i takt med den.

HVORFOR DEN FINDES (målt 26/9-2026)

To fejl ramte samtidig, og begge havde samme symptom: «ikonet gør ingenting».

1. `StartupWMClass` i `~/.local/share/applications/jarvis-desktop.desktop`
   var sat til filnavnet (`jarvis-desktop`) i stedet for vinduets klasse
   (`J.A.R.V.I.S.`). Uden match kan GNOME ikke koble vinduet til filen — intet
   ikon, og intet at fastgøre til favoritter.

2. `kernel.apparmor_restrict_unprivileged_userns=1` på denne maskine. Startet
   fra en terminal arvede appen en unconfined profil og virkede; startet af
   `gnome-shell` blev den begrænset, og Electrons zygote døde før vinduet:

       Failed to move to new namespace: ... errno = Operation not permitted
       FATAL:zygote_host_impl_linux.cc(207) Check failed

   Derfor kunne den startes fra kommandolinjen men ikke fra ikonet — og derfor
   kunne jeg tre gange sige «den kører» mens den ikke gjorde det for Bjørn.

Huset har allerede løst den ANDEN halvdel for `.deb`-vejen: `afterPack.cjs`
(23/7) og `build-hooks/deb-after-install.sh` (17/8) sætter `chrome-sandbox`
setuid 4755. Det virker ikke for en AppImage — squashfs-mountet er `nosuid`, så
SUID-helperen kan ikke bruges. For AppImages er en AppArmor-profil svaret.

INTET HARDKODES

Alt udledes af artefakten: AppImages bærer deres egen `.desktop` og deres egne
ikoner. `StartupWMClass` og `Icon` læses derfra, ikke fra en antagelse. Det er
netop det der gør at en ny udgivelse — nyt versionsnummer, nyt filnavn, nyt
produktnavn — ikke efterlader profilen pegende på en sti der ikke findes mere.

`--no-sandbox` FJERNES BEVIDST

electron-builder lægger `Exec=AppRun --no-sandbox %U` i den indlejrede
`.desktop`. Det er deres måde at komme uden om userns-begrænsningen, og den
virker — men appen renderer indhold fra nettet og fra modellerne, og sandkassen
er netop det der holder det inde. Med profilen er den ikke nødvendig, så den
tages ud.

Brug:

    python scripts/installer_desk_appimage.py                 # find nyeste i dist/
    python scripts/installer_desk_appimage.py --appimage FIL
    python scripts/installer_desk_appimage.py --toerloeb      # vis, skriv intet
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROD = Path(__file__).resolve().parents[1]
DESK = ROD / "apps" / "jarvis-desk"

#: Den kanoniske sti. Den er stabil MED VILJE: en versioneret sti ville kræve
#: at profilen blev skrevet om ved hver eneste udgivelse, og hver omskrivning
#: er en chance for at glemme det.
STANDARD_MAAL = Path.home() / "Applications" / "J.A.R.V.I.S.AppImage"

APPLIKATIONER = Path.home() / ".local" / "share" / "applications"
IKON_ROD = Path.home() / ".local" / "share" / "icons" / "hicolor"
PROFIL_MAPPE = Path("/etc/apparmor.d")


class Fejl(RuntimeError):
    """En fejl brugeren skal se, ikke et stakspor."""


def _koer(*args: str, tjek: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, check=tjek)


def byg_mappe() -> Path:
    """electron-builders output-mappe, LÆST af package.json.

    Jeg antog `dist/` da scriptet blev skrevet. Konfigurationen siger
    `release/`, og fejlen viste sig ved allerførste rigtige brug — i et script
    hvis hele pointe er ikke at antage. Nu står der ét sted hvor det slås op.
    """
    import json

    try:
        b = json.loads((DESK / "package.json").read_text(encoding="utf-8")).get("build") or {}
        ud = (b.get("directories") or {}).get("output") or "release"
    except (OSError, json.JSONDecodeError) as exc:
        raise Fejl(f"kunne ikke læse {DESK / 'package.json'}: {exc}") from exc
    return DESK / ud


def find_appimage() -> Path:
    """Nyeste AppImage i electron-builders output-mappe."""
    mappe = byg_mappe()
    kandidater = sorted(
        mappe.glob("*.AppImage"),
        key=lambda p: p.stat().st_mtime, reverse=True,
    )
    if not kandidater:
        raise Fejl(
            f"ingen AppImage i {mappe} — byg den først:\n"
            f"    cd {DESK} && npm run package:linux"
        )
    return kandidater[0]


def udpak(appimage: Path, moenster: str, ud: Path) -> None:
    """Udpak et mønster fra AppImage'en til `ud`. Kaster ved fejl."""
    r = subprocess.run(
        [str(appimage), "--appimage-extract", moenster],
        cwd=ud, capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise Fejl(f"kunne ikke udpakke {moenster!r} fra {appimage.name}:\n"
                   f"{(r.stderr or r.stdout).strip()[:300]}")


def laes_indlejret_desktop(appimage: Path) -> dict[str, str]:
    """Nøgle→værdi fra AppImage'ens EGEN `.desktop`.

    Det er sandhedskilden for `StartupWMClass` og `Icon`. Læses de ikke herfra,
    er de et gæt — og gættet var netop fejlen.
    """
    with tempfile.TemporaryDirectory() as t:
        udpak(appimage, "*.desktop", Path(t))
        filer = list((Path(t) / "squashfs-root").glob("*.desktop"))
        if not filer:
            raise Fejl(f"{appimage.name} indeholder ingen .desktop-fil")
        felter: dict[str, str] = {}
        for linje in filer[0].read_text(encoding="utf-8").split("\n"):
            if "=" in linje and not linje.startswith("["):
                k, _, v = linje.partition("=")
                felter[k.strip()] = v.strip()
    for paakraevet in ("Name", "Icon", "StartupWMClass"):
        if not felter.get(paakraevet):
            raise Fejl(f"{appimage.name}s .desktop mangler {paakraevet} — "
                       "uden den kan vinduet ikke kobles til ikonet")
    return felter


def byg_desktop(felter: dict[str, str], maal: Path) -> str:
    """`.desktop`-indholdet, med `--no-sandbox` fjernet og stien sat."""
    # Exec bygges HELT om: AppRun findes kun inde i mountet, og `--no-sandbox`
    # er ikke nødvendig når AppArmor-profilen er på plads.
    hale = " %U" if "%U" in felter.get("Exec", "") else ""
    egne = dict(felter, Exec=f"{maal}{hale}")

    # Rækkefølgen er den electron-builder selv bruger. En `.desktop` er
    # nøgle-værdi, så orden betyder intet for systemet — men den betyder noget
    # for scriptet: skriver vi felterne i en anden orden, melder det
    # «opdateret» hver gang uden at ændre noget, og et script der altid siger
    # det lærer man at overse.
    linjer = ["[Desktop Entry]"]
    for n in ("Name", "Exec", "Terminal", "Type", "Icon", "StartupWMClass",
              "Comment", "Categories"):
        if egne.get(n):
            linjer.append(f"{n}={egne[n]}")
    return "\n".join(linjer) + "\n"


def byg_profil(navn: str, maal: Path) -> str:
    return f"""# Giver desk-AppImage'en lov til at lave et user namespace, saa Electrons
# sandkasse kan starte. Samme form som Ubuntus egen /etc/apparmor.d/1password.
#
# SKREVET AF scripts/installer_desk_appimage.py — ret ikke stien i haanden.
# Koer scriptet igen naar AppImage'en flytter sig, saa foelger profilen med.
#
# Uden den doer Electrons zygote naar gnome-shell starter appen
# (kernel.apparmor_restrict_unprivileged_userns=1), og symptomet er at ikonet
# ikke goer noget. Alternativet — `--no-sandbox` i Exec — er fravalgt: appen
# renderer indhold fra nettet og fra modellerne.

abi <abi/4.0>,
include <tunables/global>

profile {navn} {maal} flags=(unconfined) {{
  userns,

  include if exists <local/{navn}>
}}
"""


def _skriv_hvis_anderledes(sti: Path, indhold: str, toerloeb: bool) -> bool:
    nuvaerende = sti.read_text(encoding="utf-8") if sti.exists() else None
    if nuvaerende == indhold:
        return False
    if toerloeb:
        return True
    sti.parent.mkdir(parents=True, exist_ok=True)
    if nuvaerende is not None:
        shutil.copy2(sti, sti.with_suffix(sti.suffix + ".bak"))
    sti.write_text(indhold, encoding="utf-8")
    return True


def skriv_profil(navn: str, indhold: str, toerloeb: bool) -> bool:
    """Skriv profilen med sudo og genindlæs den. True hvis den ændrede sig."""
    sti = PROFIL_MAPPE / navn
    try:
        nuvaerende = sti.read_text(encoding="utf-8")
    except (OSError, PermissionError):
        nuvaerende = None
    if nuvaerende == indhold:
        return False
    if toerloeb:
        return True
    r = subprocess.run(["sudo", "tee", str(sti)], input=indhold,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise Fejl(f"kunne ikke skrive {sti} (sudo): {r.stderr.strip()[:200]}")
    r = subprocess.run(["sudo", "apparmor_parser", "-r", str(sti)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise Fejl(f"profilen blev skrevet men kunne ikke indlaeses: "
                   f"{r.stderr.strip()[:300]}")
    return True


def installer_ikoner(appimage: Path, toerloeb: bool) -> int:
    """Kopiér AppImage'ens egne ikoner ind i temaet. Giver antallet."""
    with tempfile.TemporaryDirectory() as t:
        udpak(appimage, "usr/share/icons/*", Path(t))
        kilde = Path(t) / "squashfs-root" / "usr" / "share" / "icons" / "hicolor"
        if not kilde.is_dir():
            return 0
        n = 0
        for png in kilde.rglob("*.png"):
            maal = IKON_ROD / png.relative_to(kilde)
            if not toerloeb:
                maal.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(png, maal)
            n += 1
    return n


def verificer(maal: Path) -> tuple[bool, str]:
    """Start appen SOM GNOME-SHELL GOER DET og se om zygoten overlever.

    `systemd-run --user --scope` er den samme indpakning gnome-shell bruger.
    Det er hele pointen: en start fra en almindelig terminal arver kalderens
    profil og beviser INTET om hvad der sker naar ikonet klikkes.
    """
    import time

    # `systemd-run --scope` blokerer indtil processen doer, saa den startes
    # detached og vi ser efter processen i stedet for at vente paa exit.
    proc = subprocess.Popen(
        ["systemd-run", "--user", "--scope", "--collect", str(maal)],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        start_new_session=True, text=True,
    )
    frist = time.monotonic() + 40
    fundet = False
    while time.monotonic() < frist:
        if proc.poll() is not None:
            break
        u = subprocess.run(["pgrep", "-f", r"mount_.*/" + maal.stem.split(".")[0]],
                           capture_output=True, text=True)
        if u.returncode == 0 and u.stdout.strip():
            fundet = True
            break
        time.sleep(1)

    j = subprocess.run(
        ["journalctl", "--user", "--since", "2 min ago", "--no-pager"],
        capture_output=True, text=True)
    doede = re.search(r"namespace.*not permitted|zygote_host_impl_linux.*Check failed",
                      j.stdout or "", re.I)
    if doede:
        return False, ("zygoten doede stadig — AppArmor-profilen slog ikke "
                       f"igennem:\n    {doede.group(0)[:160]}")
    if not fundet:
        return False, "appen startede ikke, men der er ingen namespace-fejl i journalen"
    return True, "startet i et systemd-scope uden namespace-fejl"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--appimage", type=Path, help="stien til AppImage'en (ellers nyeste i dist/)")
    p.add_argument("--maal", type=Path, default=STANDARD_MAAL, help=f"hvor den installeres (standard: {STANDARD_MAAL})")
    p.add_argument("--toerloeb", action="store_true", help="vis hvad der ville ske; skriv intet")
    p.add_argument("--spring-verifikation-over", action="store_true",
                   help="start ikke appen til sidst (til headless)")
    a = p.parse_args(argv)

    try:
        kilde = a.appimage or find_appimage()
        if not kilde.is_file():
            raise Fejl(f"{kilde} findes ikke")
        if not os.access(kilde, os.X_OK) and not a.toerloeb:
            kilde.chmod(kilde.stat().st_mode | 0o111)

        felter = laes_indlejret_desktop(kilde)
        navn = Path(felter["Icon"]).name          # fx "jarvis-desktop"
        maal = a.maal.expanduser()
        version = felter.get("X-AppImage-Version", "?")

        print(f"  artefakt   {kilde.name} (version {version})")
        print(f"  maal       {maal}")
        print(f"  WM-klasse  {felter['StartupWMClass']}   (fra AppImage'ens egen .desktop)")

        # 1. selve binæren
        flyttet = not maal.exists() or maal.stat().st_size != kilde.stat().st_size
        if flyttet and not a.toerloeb:
            maal.parent.mkdir(parents=True, exist_ok=True)
            if maal.exists():
                shutil.copy2(maal, maal.with_name(f"{maal.stem}-forrige{maal.suffix}"))
            shutil.copy2(kilde, maal)
            maal.chmod(maal.stat().st_mode | 0o111)
        print(f"  binaer     {'installeret' if flyttet else 'uaendret'}")

        # 2. ikoner
        n = installer_ikoner(kilde, a.toerloeb)
        print(f"  ikoner     {n} stoerrelser")

        # 3. .desktop
        d_sti = APPLIKATIONER / f"{navn}.desktop"
        d_aendret = _skriv_hvis_anderledes(d_sti, byg_desktop(felter, maal), a.toerloeb)
        print(f"  .desktop   {'opdateret' if d_aendret else 'uaendret'}  ({d_sti})")

        # 4. AppArmor — den der driver naar stien skifter
        p_aendret = skriv_profil(navn, byg_profil(navn, maal), a.toerloeb)
        print(f"  apparmor   {'opdateret' if p_aendret else 'uaendret'}  ({PROFIL_MAPPE / navn})")

        if not a.toerloeb and (d_aendret or n):
            subprocess.run(["update-desktop-database", str(APPLIKATIONER)],
                           capture_output=True)
            subprocess.run(["gtk-update-icon-cache", "-f", "-t", str(IKON_ROD)],
                           capture_output=True)

        if a.toerloeb:
            print("\n  (tørløb — intet blev skrevet)")
            return 0
        if a.spring_verifikation_over:
            print("\n  verifikation sprunget over")
            return 0

        ok, hvorfor = verificer(maal)
        print(f"\n  verifikation: {'OK' if ok else 'FEJLEDE'} — {hvorfor}")
        return 0 if ok else 1

    except Fejl as e:
        print(f"\n❌ {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
