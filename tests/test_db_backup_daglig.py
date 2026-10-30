"""Den daglige DB-backup: at den tager en BRUGBAR kopi, og at rotationen er smal.

Baggrund (30/10-2026): der fandtes ingen automatisk backup af den levende
`jarvis.db`. De eneste fulde backups var to manuelle engangs-filer. Dette
script lukker hullet — men kun hvis det gør tre ting rigtigt, og hver af dem
har en fælde der ser rigtig ud når den er forkert:

1. **Kopien skal være konsistent.** `cp` af en live WAL-DB giver en fil med
   den rigtige størrelse som SQLite afviser med «file is not a database».
   Testen tager en rigtig WAL-database med ulavet WAL-indhold og kræver at
   backup-filen kan åbnes og at rækkerne er der.

2. **En dårlig backup skal AFVISES, ikke gemmes.** En fil der ikke kan åbnes
   er værre end ingen fil, fordi den ser ud som en. Testen kører verificer()
   mod korrupt, tom og næsten-tom base.

3. **Rotationen må kun røre vores egne filer.** `state/backups/` indeholder
   også MEMORY.md.bak, brain-index-snapshots og manuelle engangs-filer.
   Testen lægger dem ind ved siden af og kræver at de overlever.

Testene bruger rigtig sqlite — en fake forbindelse kan ikke se forskel på en
gyldig og en korrupt fil, og så måler testen ingenting.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from scripts.db_backup_daglig import (
    PRAEFIKS,
    backup_sti,
    eksisterende_backups,
    rotér,
    ryd_sidefiler,
    tag_backup,
    verificer,
)


def _lav_db(sti: Path, *, raekker: int = 60) -> None:
    """En lille database med nok tabeller til at bestå tabel-tærsklen."""
    conn = sqlite3.connect(sti)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        for i in range(raekker):
            conn.execute(f"CREATE TABLE t{i} (a INTEGER)")
            conn.execute(f"INSERT INTO t{i} VALUES (?)", (i,))
        conn.commit()
    finally:
        conn.close()


def test_backup_af_live_wal_db_er_laesbar(tmp_path: Path) -> None:
    """Kernen: en kopi af en WAL-database med aaben WAL skal kunne aabnes."""
    kilde = tmp_path / "kilde.db"
    _lav_db(kilde)

    # Skriv gennem en STADIG AABEN forbindelse, saa indholdet ligger i WAL'en
    # og ikke i hovedfilen. Det er praecis den tilstand `cp` fejler paa.
    holder = sqlite3.connect(kilde)
    try:
        holder.execute("PRAGMA journal_mode = WAL")
        holder.execute("INSERT INTO t0 VALUES (999)")
        holder.commit()
        assert Path(str(kilde) + "-wal").exists(), "WAL-filen skal vaere der"

        maal = tmp_path / "backup.db"
        tag_backup(kilde, maal)
    finally:
        holder.close()

    ok, beskrivelse = verificer(maal)
    assert ok, beskrivelse

    conn = sqlite3.connect(maal)
    try:
        vaerdier = [r[0] for r in conn.execute("SELECT a FROM t0")]
    finally:
        conn.close()
    assert 999 in vaerdier, "raekken der kun laa i WAL'en skal med i backup'en"


def test_korrupt_fil_afvises(tmp_path: Path) -> None:
    """Rigtig SQLite-header + skrald bagefter = «file is not a database»."""
    sti = tmp_path / "korrupt.db"
    sti.write_bytes(b"SQLite format 3\x00" + b"\xde\xad\xbe\xef" * 2000)
    ok, beskrivelse = verificer(sti)
    assert not ok
    assert "ikke åbnes" in beskrivelse or "quick_check" in beskrivelse


def test_tom_fil_afvises(tmp_path: Path) -> None:
    sti = tmp_path / "tom.db"
    sti.write_bytes(b"")
    ok, beskrivelse = verificer(sti)
    assert not ok
    assert "0 bytes" in beskrivelse


def test_naesten_tom_base_afvises(tmp_path: Path) -> None:
    """En fil der aabner fint men er tom er den anden fejlform."""
    sti = tmp_path / "lille.db"
    conn = sqlite3.connect(sti)
    try:
        conn.execute("CREATE TABLE x (a)")
        conn.commit()
    finally:
        conn.close()
    ok, beskrivelse = verificer(sti)
    assert not ok
    assert "tabeller" in beskrivelse


def test_manglende_fil_afvises(tmp_path: Path) -> None:
    ok, beskrivelse = verificer(tmp_path / "findes_ikke.db")
    assert not ok
    assert "findes ikke" in beskrivelse


def test_rotation_roerer_kun_vores_egne_filer(tmp_path: Path) -> None:
    """Fremmede filer i backup-mappen skal overleve rotationen."""
    base = datetime(2026, 10, 27, 3, 0, tzinfo=UTC)
    for dage in range(5):
        (tmp_path / f"{PRAEFIKS}{(base + timedelta(days=dage)).strftime('%Y%m%dT%H%M%SZ')}.db").write_text("x")

    fremmede = [
        tmp_path / "MEMORY.md.bak",
        tmp_path / "jarvis-before-manuel.db",
        tmp_path / "jarvis_brain_index-pre-abc.sqlite",
    ]
    for f in fremmede:
        f.write_text("fremmed")

    slettede = rotér(tmp_path, behold=3)

    assert len(slettede) == 2, "5 filer med behold=3 skal give 2 slettede"
    # De to AEldste skal vaere vaek.
    assert not (tmp_path / f"{PRAEFIKS}20261027T030000Z.db").exists()
    assert not (tmp_path / f"{PRAEFIKS}20261028T030000Z.db").exists()
    # De nyeste tre skal staa.
    assert len(eksisterende_backups(tmp_path)) == 3
    # Og de fremmede skal alle overleve.
    for f in fremmede:
        assert f.exists(), f"{f.name} blev slettet af rotationen"


def test_rotation_under_graensen_sletter_intet(tmp_path: Path) -> None:
    (tmp_path / f"{PRAEFIKS}20261030T030000Z.db").write_text("x")
    assert rotér(tmp_path, behold=3) == []
    assert len(eksisterende_backups(tmp_path)) == 1


def test_backup_sti_er_sorterbar(tmp_path: Path) -> None:
    """Navnesortering skal give tidssortering — rotationen hviler paa det."""
    tidlig = backup_sti(tmp_path, datetime(2026, 10, 27, 3, 0, tzinfo=UTC))
    sen = backup_sti(tmp_path, datetime(2026, 10, 30, 3, 0, tzinfo=UTC))
    assert tidlig.name < sen.name


def test_ryd_sidefiler_fjerner_shm_og_wal(tmp_path: Path) -> None:
    """En backup skal vaere ÉN fil — ikke tre."""
    sti = tmp_path / "backup.db"
    sti.write_text("x")
    Path(str(sti) + "-shm").write_text("x")
    Path(str(sti) + "-wal").write_text("x")

    ryd_sidefiler(sti)

    assert sti.exists(), "hovedfilen maa ikke roeres"
    assert not Path(str(sti) + "-shm").exists()
    assert not Path(str(sti) + "-wal").exists()
