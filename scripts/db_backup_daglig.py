#!/usr/bin/env python3
"""Daglig konsistent backup af den LEVENDE jarvis.db + rotation.

Baggrund (målt 30/10-2026): der fandtes INGEN automatisk backup. De eneste
fulde backups i `state/backups/` var to manuelle engangs-filer fra 18. og
25. oktober — den ældste blev ryddet samme dag, og tilbage stod én fil der
bliver ældre hver dag. Det er den slags hul der ikke råber.

To ting scriptet gør rigtigt, som en naiv løsning gør forkert:

1. **`sqlite3` backup-API'et — ALDRIG `cp`.** En `cp` af en live WAL-DB ser
   rigtig ud (filen har den rigtige størrelse) men SQLite svarer
   «file is not a database», fordi WAL-frames ikke er foldet ind i
   hovedfilen. `src.backup(dst)` læser gennem WAL'en og skriver en
   selvstændig, konsistent fil.

2. **Verifikation FØR rotation.** En backup der ikke kan åbnes er værre end
   ingen backup, fordi den ser ud som en. Hver fil køres gennem
   `PRAGMA quick_check` + en tabel-tælling; fejler den, slettes den straks
   og scriptet afslutter med exit-kode 1 — så cron-loggen viser det.

Rotation: de nyeste `--behold` (default 3) verificerede backups beholdes.
Uden rotation fylder 5,8 GB pr. døgn ~40 GB om ugen.

Kørsel:
    python3 scripts/db_backup_daglig.py            # tag backup + rotér
    python3 scripts/db_backup_daglig.py --dry-run  # vis hvad der ville ske
    python3 scripts/db_backup_daglig.py --behold 5 # anden retention
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

# Repo-roden på sys.path så `core.runtime.db_core` kan importeres når scriptet
# kaldes fra cron med en vilkårlig cwd.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.runtime.db_core import DB_PATH  # noqa: E402

#: Mønster for vores egne backups. Bevidst smalt: `state/backups/` indeholder
#: også MEMORY.md.bak, brain-index-snapshots og manuelle engangs-filer, og
#: rotationen må ALDRIG røre dem.
PRAEFIKS = "jarvis-daglig-"
ENDELSE = ".db"

#: Standard antal verificerede backups der beholdes.
BEHOLD_DEFAULT = 3


def backup_sti(backup_dir: Path, nu: datetime | None = None) -> Path:
    """Filnavn for en ny backup. Tidsstempel i UTC, sorterbart."""
    stamp = (nu or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    return backup_dir / f"{PRAEFIKS}{stamp}{ENDELSE}"


def eksisterende_backups(backup_dir: Path) -> list[Path]:
    """Vores egne backups, nyeste først. Rører intet andet i mappen."""
    if not backup_dir.is_dir():
        return []
    filer = [
        p
        for p in backup_dir.iterdir()
        if p.is_file() and p.name.startswith(PRAEFIKS) and p.name.endswith(ENDELSE)
    ]
    # Navnet er sorterbart (ISO-agtigt tidsstempel) → navnesortering = tidssortering.
    return sorted(filer, key=lambda p: p.name, reverse=True)


def ryd_sidefiler(sti: Path) -> None:
    """Fjern `-shm`/`-wal` som verificeringen efterlader.

    Målt 30/10-2026: en `mode=ro`-åbning af en WAL-database opretter stadig
    sidefilerne. De er harmløse, men de får mappen til at se ud som om der
    ligger halve backups, og de tælles ikke med i rotationen. En backup skal
    være ÉN fil.
    """
    for suffix in ("-shm", "-wal"):
        try:
            Path(str(sti) + suffix).unlink(missing_ok=True)
        except OSError:  # oprydning maa ikke vaelte en ellers gyldig backup
            pass


def verificer(sti: Path) -> tuple[bool, str]:
    """Åbn backup-filen og bevis at den er en brugbar database.

    Returnerer (ok, beskrivelse). `quick_check` fanger korruption; tabel-tallet
    fanger den anden fejlform — en fil der åbner fint men er TOM (fx en
    afbrudt kopi). Begge skal bestå.
    """
    if not sti.exists():
        return False, "filen findes ikke"
    if sti.stat().st_size == 0:
        return False, "filen er 0 bytes"
    try:
        conn = sqlite3.connect(f"file:{sti}?mode=ro", uri=True)
        try:
            raekke = conn.execute("PRAGMA quick_check").fetchone()
            dom = (raekke[0] if raekke else "") or ""
            if dom.lower() != "ok":
                return False, f"quick_check: {dom[:120]}"
            tabeller = conn.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table'"
            ).fetchone()[0]
            if tabeller < 50:
                # Den levende base har 345 tabeller (målt 30/10-2026). Under 50
                # betyder at vi har fanget en næsten-tom fil, ikke en backup.
                return False, f"kun {tabeller} tabeller — ser ikke ud som en fuld base"
            return True, f"quick_check ok, {tabeller} tabeller"
        finally:
            conn.close()
    except sqlite3.DatabaseError as exc:  # IKKE tavs: returneres som dom til kalderen
        return False, f"kan ikke åbnes som database: {exc}"
    except Exception as exc:  # pragma: no cover - uventet, men skal rapporteres
        return False, f"verifikation fejlede: {exc}"


def tag_backup(kilde: Path, maal: Path) -> None:
    """Konsistent kopi via sqlite3's backup-API (sikker under WAL).

    Åbner kilde-forbindelsen eksplicit og read-only-ish: vi bruger den rå
    sqlite3-forbindelse frem for `db_core.connect()`, fordi den er pooled og
    thread-local — en backup skal ikke dele tilstand med runtime.
    """
    maal.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(f"file:{kilde}?mode=ro", uri=True, timeout=30)
    try:
        src.execute("PRAGMA busy_timeout = 30000")
        dst = sqlite3.connect(maal)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def rotér(backup_dir: Path, behold: int, *, dry_run: bool = False) -> list[Path]:
    """Slet de ældste backups ud over `behold`. Returnerer de slettede stier."""
    filer = eksisterende_backups(backup_dir)
    overskydende = filer[behold:]
    if not dry_run:
        for p in overskydende:
            try:
                p.unlink()
            except OSError as exc:
                print(f"KUNNE IKKE SLETTE {p}: {exc}", file=sys.stderr)
    return overskydende


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Daglig konsistent DB-backup med rotation.")
    ap.add_argument(
        "--backup-dir",
        default=str(Path(DB_PATH).parent / "backups"),
        help="Mappe til backups (default: <state>/backups)",
    )
    ap.add_argument(
        "--behold",
        type=int,
        default=BEHOLD_DEFAULT,
        help=f"Antal verificerede backups der beholdes (default {BEHOLD_DEFAULT})",
    )
    ap.add_argument("--dry-run", action="store_true", help="Vis uden at skrive/slette")
    args = ap.parse_args(argv)

    backup_dir = Path(args.backup_dir)
    kilde = Path(DB_PATH)
    nu = datetime.now(UTC)

    if not kilde.exists():
        print(f"FEJL: kilde-databasen findes ikke: {kilde}", file=sys.stderr)
        return 1

    maal = backup_sti(backup_dir, nu)
    print(f"[{nu.isoformat()}] backup: {kilde} -> {maal}")

    if args.dry_run:
        print(f"DRY-RUN: ville kopiere {kilde.stat().st_size} bytes")
        filer = eksisterende_backups(backup_dir)
        print(f"DRY-RUN: {len(filer)} eksisterende backups, beholder {args.behold}")
        for p in filer[args.behold:]:
            print(f"DRY-RUN: ville slette {p.name}")
        return 0

    try:
        tag_backup(kilde, maal)
    except Exception as exc:
        print(f"FEJL under backup: {exc}", file=sys.stderr)
        # En halvskrevet fil må ikke ligge og se ud som en backup.
        try:
            maal.unlink(missing_ok=True)
        except OSError:  # sletning af en halv fil maa ikke skjule den oprindelige fejl
            pass
        return 1

    ok, beskrivelse = verificer(maal)
    if not ok:
        print(f"FEJL: backup-filen er ikke brugbar ({beskrivelse}) — slettes", file=sys.stderr)
        try:
            maal.unlink(missing_ok=True)
        except OSError:  # samme: den daarlige fil skal vaek, men fejlen er allerede rapporteret
            pass
        ryd_sidefiler(maal)
        return 1

    ryd_sidefiler(maal)
    stoerrelse = maal.stat().st_size
    print(f"OK: {maal.name} — {beskrivelse}, {stoerrelse / 1e9:.2f} GB")

    slettede = rotér(backup_dir, args.behold)
    for p in slettede:
        print(f"rotation: slettede {p.name}")

    tilbage = eksisterende_backups(backup_dir)
    print(f"beholdt: {len(tilbage)} backup(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
