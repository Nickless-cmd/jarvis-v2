"""Smoke test for core.services.memory_search.

The semantic search entry point should rank the most similar cached chunk first
when embeddings are available.
"""

import numpy as np

from core.services import memory_search


def test_search_memory_returns_top_embedding_hit(monkeypatch) -> None:
    chunks = [
        memory_search.Chunk(
            text="Project roadmap and architecture notes.",
            source="MEMORY.md",
            section="Roadmap",
        ),
        memory_search.Chunk(
            text="Personal preferences and tone reminders.",
            source="USER.md",
            section="Preferences",
        ),
    ]
    embeddings = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)

    monkeypatch.setattr(
        memory_search,
        "_load_or_build_index",
        lambda: (chunks, embeddings, {}),
    )
    monkeypatch.setattr(
        memory_search,
        "_embed_single",
        lambda query: np.array([1.0, 0.0], dtype=np.float32),
    )

    results = memory_search.search_memory("roadmap", limit=2)

    assert results[0]["source"] == "MEMORY.md"
    assert results[0]["method"] == "embedding"
