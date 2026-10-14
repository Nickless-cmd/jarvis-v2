from __future__ import annotations

import inspect


def test_embedding_listing_accepts_explicit_private_scope_filters() -> None:
    from core.runtime.db_embeddings import list_embeddings

    parameters = inspect.signature(list_embeddings).parameters
    assert "user_id" in parameters
    assert "private_statuses" in parameters
