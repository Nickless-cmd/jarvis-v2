"""The SQLite drift guard must reject schema and timestamp changes."""
import sqlite3

from scripts import verify_sqlite_schema as guard


def test_canonical_schema_ignores_creation_order_but_rejects_drift():
    first = sqlite3.connect(":memory:")
    second = sqlite3.connect(":memory:")
    first.executescript("""
        CREATE TABLE alpha (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL);
        CREATE INDEX ix_alpha_created ON alpha(created_at);
        CREATE TABLE beta (value TEXT DEFAULT 'x');
        INSERT INTO alpha VALUES (1, '2026-09-29T07:38:59.148486+00:00');
    """)
    second.executescript("""
        CREATE TABLE beta (value TEXT DEFAULT 'x');
        CREATE TABLE alpha (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL);
        CREATE INDEX ix_alpha_created ON alpha(created_at);
        INSERT INTO alpha VALUES (1, '2026-09-29T07:38:59.148486+00:00');
    """)
    expected = guard.inventory(first)
    assert guard.inventory(second) == expected
    second.execute("ALTER TABLE beta ADD COLUMN status TEXT NOT NULL DEFAULT 'new'")
    assert guard.compare(guard.inventory(second), expected) == [
        "CHANGED beta.digest: " + expected["tables"]["beta"]["digest"]
        + " -> " + guard.inventory(second)["tables"]["beta"]["digest"]
    ]


def test_timestamp_format_drift_is_separate_from_schema_digest():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, created_at TEXT)")
    conn.execute("INSERT INTO events VALUES (1, '2026-09-29T07:38:59.148486+00:00')")
    expected = guard.inventory(conn)
    conn.execute("INSERT INTO events VALUES (2, '2026-09-29 05:30:26')")
    actual = guard.inventory(conn)
    assert actual["tables"]["events"]["digest"] == expected["tables"]["events"]["digest"]
    assert guard.compare(actual, expected) == [
        "CHANGED events.created_at_formats: ['iso_utc_offset'] -> "
        "['iso_utc_offset', 'sqlite_utc_seconds']"
    ]


def test_new_table_and_third_format_are_visible():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE events (created_at TEXT)")
    expected = guard.inventory(conn)
    conn.execute("CREATE TABLE next_events (created_at TEXT)")
    conn.execute("INSERT INTO next_events VALUES ('2026-09-29T07:38:59Z')")
    actual = guard.inventory(conn)
    assert actual["tables"]["next_events"]["created_at_formats"] == ["iso_utc_z"]
    assert guard.compare(actual, expected) == ["NEW next_events"]


def test_partial_index_predicate_changes_digest():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE events (id INTEGER, status TEXT)")
    conn.execute("CREATE INDEX ix_events ON events(status) WHERE status = 'open'")
    expected = guard.inventory(conn)
    conn.execute("DROP INDEX ix_events")
    conn.execute("CREATE INDEX ix_events ON events(status) WHERE status = 'closed'")
    assert guard.inventory(conn)["tables"]["events"]["digest"] != expected["tables"]["events"]["digest"]


def test_precommit_skips_non_runtime_host(monkeypatch, tmp_path):
    monkeypatch.setattr(guard.socket, "gethostname", lambda: "developer-laptop")
    assert guard.main(["--only-host", "Jarvis", "--require-db",
                       "--db", str(tmp_path / "missing.db")]) == 0


# ── En vagt der kun siger NEJ er en blokade (29/9-2026) ─────────────────────
#
# Den der bliver stoppet er som regel Jarvis, midt i noget andet. Foer denne
# besked fik han 45 linjer «CHANGED x / MISSING y» og intet om hvad han saa
# skulle goere. Uden en vej videre er valget mellem at gaette og at give op,
# og begge dele er vaerre end det skema-drift koster.
#
# Formen er laant fra `verify_silent_except.py`, som allerede afslutter med
# «Vaelg én:» og tre konkrete udveje.


def test_en_blokeret_commit_faar_at_vide_hvad_den_skal_goere(capsys):
    from pathlib import Path
    guard._forklar(["CHANGED alpha.digest: a -> b"], Path("docs/persistens/sqlite-schema.json"))
    ud = capsys.readouterr().out
    assert "--write-snapshot" in ud, "kommandoen der loeser det staar ikke der"
    assert "VAR DET DIG?" in ud, "den spoerger ikke om aendringen var tilsigtet"
    assert "only-host" in ud or "CT105" in ud


def test_en_FORSVUNDET_tabel_kaldes_alvorlig():
    """NEW og MISSING er ikke lige alvorlige. En tabel der er vaek uden at
    nogen fjernede den er det vagten findes for."""
    from pathlib import Path
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        guard._forklar(["MISSING research_runs"], Path("s.json"))
    ud = buf.getvalue()
    assert "alvorlige" in ud.lower()
    assert "STOP" in ud


def test_et_skiftet_TIDSFORMAT_faar_sin_egen_forklaring():
    """Den dyreste af de tre, og den mest tavse: et skiftet format giver et
    troværdigt tal, ikke en fejl."""
    from pathlib import Path
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        guard._forklar(["CHANGED events.created_at_formats: ['iso_utc_z'] -> ['sqlite_utc_seconds']"],
                       Path("s.json"))
    ud = buf.getvalue()
    assert "TIDSFORMAT" in ud
    assert "0 %" in ud or "100 %" in ud, "den siger ikke HVORDAN fejlen ser ud"


def test_forklaringen_kommer_KUN_naar_der_er_noget_at_forklare(capsys, tmp_path, monkeypatch):
    """Et rent skema maa ikke give en vaeg af tekst ved hvert commit."""
    import sqlite3
    import json
    db = tmp_path / "t.db"
    con = sqlite3.connect(db)
    con.executescript("CREATE TABLE alpha (id INTEGER PRIMARY KEY);")
    con.commit()
    con.close()
    snap = guard.inventory(sqlite3.connect(db))
    snap["source_host"] = "TestHost"
    (tmp_path / "s.json").write_text(json.dumps(snap))
    kode = guard.main(["--db", str(db), "--snapshot", str(tmp_path / "s.json")])
    ud = capsys.readouterr().out
    assert kode == 0
    assert "0 differences" in ud
    assert "VAR DET DIG?" not in ud


def test_forklaringen_naar_HELT_ud_gennem_main(capsys, tmp_path):
    """De tre tests ovenfor kalder `_forklar` direkte og beviser derfor ikke
    at `main` kalder den. Mutationskoersel: at fjerne kaldet i `main` lod dem
    ALLE bestaa. Denne gaar hele vejen, som den der bliver stoppet goer.
    """
    import sqlite3
    import json
    db = tmp_path / "t.db"
    con = sqlite3.connect(db)
    con.executescript(
        "CREATE TABLE alpha (id INTEGER PRIMARY KEY, created_at TEXT);"
        "INSERT INTO alpha VALUES (1, '2026-09-29T07:38:59+00:00');"
    )
    con.commit()
    con.close()
    snap = guard.inventory(sqlite3.connect(db))
    snap["source_host"] = "TestHost"
    # ægte drift: tidsformatet skifter, og en tabel er vaek
    snap["tables"]["alpha"]["created_at_formats"] = ["sqlite_utc_seconds"]
    snap["tables"]["en_tabel_der_forsvandt"] = {
        "digest": "ab:cd", "schema": {"columns": [], "indexes": []},
        "created_at_formats": [],
    }
    (tmp_path / "s.json").write_text(json.dumps(snap))

    kode = guard.main(["--db", str(db), "--snapshot", str(tmp_path / "s.json")])
    ud = capsys.readouterr().out

    assert kode == 1, "en drift skal blokere"
    # ... og den stoppede skal kunne komme videre UDEN at spoerge nogen
    assert "VAR DET DIG?" in ud
    assert "scripts/verify_sqlite_schema.py --write-snapshot" in ud, (
        "den praecise kommando mangler — en halv kommando er ingen vej videre")
    assert "STOP" in ud, "den forsvundne tabel blev ikke kaldt alvorlig"
    assert "TIDSFORMAT" in ud


def test_empty_table_gaining_rows_is_not_drift():
    """En tom tabel har intet format at sammenligne med.

    Maalt 29/9-2026: cheap_lane_admission_leases (en lease-tabel) fik gaten til
    at fejle mens en lease var aktiv og passere fem minutter senere, da den var
    udloebet — samme kode, samme snapshot. Skriveren var uaendret hele tiden.
    """
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE leases (id INTEGER PRIMARY KEY, created_at TEXT)")
    expected = guard.inventory(conn)
    assert expected["tables"]["leases"]["created_at_formats"] == ["unobserved"]

    # foerste raekke i en tidligere tom tabel -> ingen drift
    conn.execute("INSERT INTO leases VALUES (1, '2026-09-29T11:15:41.123456+00:00')")
    actual = guard.inventory(conn)
    assert actual["tables"]["leases"]["created_at_formats"] == ["iso_utc_offset"]
    assert guard.compare(actual, expected) == []

    # ... og en tabel der tommes igen -> heller ingen drift
    conn.execute("DELETE FROM leases")
    tomt = guard.inventory(conn)
    assert tomt["tables"]["leases"]["created_at_formats"] == ["unobserved"]
    assert guard.compare(tomt, actual) == []


def test_real_format_shift_between_two_observed_states_still_blocks():
    """Fixet maa ikke slukke vagten: to observerede formater er stadig en drift."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, created_at TEXT)")
    conn.execute("INSERT INTO events VALUES (1, '2026-09-29T07:38:59.148486+00:00')")
    expected = guard.inventory(conn)
    conn.execute("INSERT INTO events VALUES (2, '2026-09-29 05:30:26')")
    actual = guard.inventory(conn)
    assert guard.compare(actual, expected) == [
        "CHANGED events.created_at_formats: ['iso_utc_offset'] -> "
        "['iso_utc_offset', 'sqlite_utc_seconds']"
    ]


def test_table_without_created_at_column_is_not_a_format_drift():
    """`[]` er 'ingen kolonne', ikke et format."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE uden_tid (id INTEGER PRIMARY KEY)")
    expected = guard.inventory(conn)
    assert expected["tables"]["uden_tid"]["created_at_formats"] == []
    assert guard.compare(guard.inventory(conn), expected) == []
