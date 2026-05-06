import pytest

from core.services import tool_embeddings as te


@pytest.fixture
def fake_embed(monkeypatch):
    def _embed(text: str) -> list[float]:
        # Deterministic fake: hash-based vector
        h = sum(ord(c) for c in text) % 100
        return [float(h), 0.5, 0.5]
    monkeypatch.setattr(te, "_compute_embedding", _embed)
    return _embed


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(te, "_DB_PATH", tmp_path / "tool_embeddings.sqlite")
    return tmp_path


def test_get_embedding_caches(isolated_db, fake_embed):
    v1 = te.get_embedding("read_file", "read file from path")
    v2 = te.get_embedding("read_file", "read file from path")
    assert v1 == v2


def test_top_k_returns_most_similar(isolated_db, fake_embed):
    te.get_embedding("read_file", "read file from path")
    te.get_embedding("bash", "run shell command")
    te.get_embedding("grep", "search across files")
    hits = te.top_k_similar("read file something", k=2)
    assert len(hits) == 2
    assert hits[0][0] in {"read_file", "bash", "grep"}


def test_invalidate_forces_recompute(isolated_db, fake_embed):
    te.get_embedding("read_file", "v1 description")
    te.invalidate("read_file")
    v2 = te.get_embedding("read_file", "v2 description")
    assert v2 == fake_embed("read_file: v2 description")


def test_cosine_basic():
    assert te._cosine([1, 0], [1, 0]) == pytest.approx(1.0)
    assert te._cosine([1, 0], [0, 1]) == pytest.approx(0.0)
    assert te._cosine([], [1, 0]) == 0.0
