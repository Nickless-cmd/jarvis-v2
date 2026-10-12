def test_routine_migration_public_api():
    from core.services.routine_migration import apply_report, classify_legacy_sources

    assert callable(classify_legacy_sources)
    assert callable(apply_report)
