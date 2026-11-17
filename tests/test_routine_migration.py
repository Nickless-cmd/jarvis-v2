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


def test_system_producer_udledes_af_kilden_ikke_af_payloaden(monkeypatch):
    """Routing maa ikke afhaenge af en noegle aeldre payloads ikke har.

    Regression 17/11-2026: fem rapporter paa disken har autonome sessioner hvis
    forseglede definition mangler ``system_producer``. Blev routingen laest fra
    payloaden, faldt de igennem til ``routine_migrated_<hash>`` — én rutine pr.
    historisk session (197 saadanne raekker i den levende base).
    """
    import core.services.routine_migration as migration

    monkeypatch.setattr(migration, "_report_master_key", lambda: b"m" * 32)

    item = {
        "source_kind": "autonomous_session",
        "owner_user_id": "canonical-owner",
        "source_ref_enc": migration._sealed_json(
            "canonical-owner", {"source_id": "auto-dream-20261012"}
        ),
    }
    assert migration._system_producer_for_item(item) == "dream"

    ukendt = dict(
        item,
        source_ref_enc=migration._sealed_json(
            "canonical-owner", {"source_id": "auto-recurring-20261012"}
        ),
    )
    assert migration._system_producer_for_item(ukendt) == ""

    assert migration._system_producer_for_item(
        {"source_kind": "recurring", "owner_user_id": "canonical-owner"}
    ) == ""
