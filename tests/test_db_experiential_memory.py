from __future__ import annotations


def test_experiential_store_exports_scoped_persistence_contract() -> None:
    from core.runtime import db_experiential_memory as store

    assert callable(store.insert_cognitive_experiential_memory)
    assert callable(store.get_experiential_memory_candidates)
