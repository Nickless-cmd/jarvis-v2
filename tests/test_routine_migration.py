def test_routine_migration_public_api():
    from core.services.routine_migration import apply_report, classify_legacy_sources

    assert callable(classify_legacy_sources)
    assert callable(apply_report)


def test_halvt_link_taeller_ikke_som_migreret():
    """Et link uden ``routine_id`` peger paa intet og maa ikke blokere reparation.

    Regression 17/11-2026: fire raekker stod med ``routine_id IS NULL``, og
    ``_legacy_link_exists`` svarede «findes» — saa ``apply_report`` sprang dem
    over som ``already`` for evigt og kunne aldrig reparere hullet.
    """
    import sqlite3

    from core.services.routine_migration import _legacy_link_exists

    conn = sqlite3.connect(":memory:")
    conn.execute(
        """CREATE TABLE routine_legacy_links (
            legacy_link_id TEXT PRIMARY KEY,
            routine_id TEXT,
            run_id TEXT,
            source_kind TEXT NOT NULL,
            source_id TEXT NOT NULL,
            source_ref_enc BLOB NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(source_kind, source_id))"""
    )
    conn.execute(
        "INSERT INTO routine_legacy_links VALUES "
        "('l1', NULL, NULL, 'recurring', 'rec-x', x'00', '2026-01-01')"
    )
    conn.commit()

    assert _legacy_link_exists(conn, "recurring", "rec-x") is False, (
        "et halvt link er ikke et link"
    )

    conn.execute("UPDATE routine_legacy_links SET routine_id='routine_1'")
    conn.commit()

    assert _legacy_link_exists(conn, "recurring", "rec-x") is True
