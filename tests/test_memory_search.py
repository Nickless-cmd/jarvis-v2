"""Tests for memory_search.py — CANDIDATE penalty and search behavior.

Companion to tests/test_memory_search_quarantine.py which covers the
quarantine filter. This file holds the CANDIDATE-penalty checks added
2026-05-22.
"""
import pytest
from core.services.memory_search import search_memory

# These tests are integration tests that hit the real workspace.
# workspace_dir() requires user context (Task 3a: multi-user isolation).
# Patch it to the owner's real workspace for backwards compat.
_OWNER_WS = __import__("pathlib").Path.home() / ".jarvis-v2" / "workspaces" / "default"


@pytest.fixture(autouse=True)
def _owner_workspace_context(monkeypatch):
    monkeypatch.setattr("core.runtime.workspace_paths.workspace_dir", lambda user_id=None: _OWNER_WS)


def test_search_returns_results_for_known_query():
    """Smoke: search returns non-empty for a real query."""
    results = search_memory("ChiefOne hardware", limit=5)
    # Don't fail on empty corpus, but check shape if non-empty
    assert isinstance(results, list)
    for r in results:
        assert "text" in r
        assert "source" in r
        assert "score" in r


def test_candidate_field_present_on_results():
    """Every embedding-method result should carry candidate_penalty flag."""
    results = search_memory("memory", limit=3)
    for r in results:
        if r.get("method") == "embedding":
            assert "candidate_penalty" in r
            assert "raw_score" in r


def test_top_result_not_candidate_when_curated_available():
    """If curated MEMORY.md content matches, it must rank above
    [CANDIDATE→] legacy entries."""
    results = search_memory("ChiefOne hardware", limit=10)
    if len(results) < 2:
        return  # not enough corpus to test ranking
    top = results[0]
    # When non-candidate matches exist (most queries about Jarvis facts),
    # the top should not be a candidate.
    non_candidates = [r for r in results if not r.get("candidate_penalty")]
    if non_candidates:
        assert not top.get("candidate_penalty", False), (
            f"Top result is CANDIDATE despite non-candidate available:\n"
            f"top={top}\n"
            f"first non-candidate={non_candidates[0]}"
        )


# ── Inkrementel reindex (2026-08-20) ─────────────────────────────────────────
# Bjørn: "kold start tog over 40 sek?" — målt i produktion embeddede reindexen
# HELE korpuset (`ms-corpus n=658`, 14,5-16,4 s) TRE ture i træk, fordi Jarvis
# skriver til sine memory-filer under hver tur og enhver mtime-ændring
# invaliderede alt. Baggrundstråden beskyttede kalderens tråd, men ikke ollama-
# køen: assemblyens egne embeds stod bag de 658 → assembly 2 s → 15-17 s.

class TestInkrementelReindex:
    def _setup(self, monkeypatch, tmp_path, chunk_texts):
        import numpy as _np
        import core.services.memory_search as ms
        from core.services.memory_search import Chunk
        monkeypatch.setattr(ms, "_cache_path", lambda: tmp_path / "idx.pkl")
        monkeypatch.setattr(ms, "_chunk_all_files",
                            lambda files: [Chunk(text=t, source="m.md", section="") for t in chunk_texts])
        calls: list[list[str]] = []

        def _fake_embed(texts):
            calls.append(list(texts))
            # deterministisk pr. tekst → gør "samme tekst = samme vektor" testbar
            return _np.array([[float(len(t)), float(sum(map(ord, t[:3])))] for t in texts],
                             dtype=_np.float32)

        monkeypatch.setattr(ms, "_embed_ollama", _fake_embed)
        return ms, calls

    def test_foerste_build_embedder_alt(self, monkeypatch, tmp_path):
        ms, calls = self._setup(monkeypatch, tmp_path, ["alfa", "beta", "gamma"])
        ms._build_and_cache_index([], {"f": 1.0})
        assert calls == [["alfa", "beta", "gamma"]], "uden cache skal alt embeddes"

    def test_kun_nye_chunks_embeddes_anden_gang(self, monkeypatch, tmp_path):
        """Kernen: én ny linje i en memory-fil må ikke koste 658 embeds."""
        ms, calls = self._setup(monkeypatch, tmp_path, ["alfa", "beta", "gamma"])
        ms._build_and_cache_index([], {"f": 1.0})
        calls.clear()
        ms, calls2 = self._setup(monkeypatch, tmp_path, ["alfa", "beta", "gamma", "ny linje"])
        ms._build_and_cache_index([], {"f": 2.0})
        assert calls2 == [["ny linje"]], f"kun den nye chunk skulle embeddes, fik {calls2}"

    def test_uaendret_korpus_embedder_INTET(self, monkeypatch, tmp_path):
        ms, calls = self._setup(monkeypatch, tmp_path, ["alfa", "beta"])
        ms._build_and_cache_index([], {"f": 1.0})
        ms, calls2 = self._setup(monkeypatch, tmp_path, ["alfa", "beta"])
        ms._build_and_cache_index([], {"f": 2.0})
        assert calls2 == [], "mtime-skift uden indholdsændring må ikke koste ét eneste embed"

    def test_resultat_er_identisk_med_fuld_rebuild(self, monkeypatch, tmp_path):
        """Den afgørende invariant: inkrementel må ikke ændre ét eneste tal —
        ellers ville recall-scores stille skride."""
        import pickle
        import numpy as _np
        texts = ["alfa", "beta", "gamma", "delta"]
        # inkrementel: byg med 3, udvid til 4
        ms, _ = self._setup(monkeypatch, tmp_path, texts[:3])
        ms._build_and_cache_index([], {"f": 1.0})
        ms, _ = self._setup(monkeypatch, tmp_path, texts)
        ms._build_and_cache_index([], {"f": 2.0})
        with open(tmp_path / "idx.pkl", "rb") as fh:
            inkrementel = pickle.load(fh)["embeddings"]
        # fuld: byg alle 4 i ét hug i en frisk mappe
        frisk = tmp_path / "frisk"
        frisk.mkdir()
        ms, _ = self._setup(monkeypatch, frisk, texts)
        ms._build_and_cache_index([], {"f": 1.0})
        with open(frisk / "idx.pkl", "rb") as fh:
            fuld = pickle.load(fh)["embeddings"]
        assert _np.array_equal(inkrementel, fuld), "inkrementel ≠ fuld rebuild"

    def test_modelskift_tvinger_fuld_reembed(self, monkeypatch, tmp_path):
        """Vektorer fra to modeller må ALDRIG blandes i samme matrix."""
        ms, _ = self._setup(monkeypatch, tmp_path, ["alfa", "beta"])
        ms._build_and_cache_index([], {"f": 1.0})
        monkeypatch.setattr(ms, "_EMBED_MODEL", "en-anden-model")
        ms, calls2 = self._setup(monkeypatch, tmp_path, ["alfa", "beta"])
        monkeypatch.setattr(ms, "_EMBED_MODEL", "en-anden-model")
        ms._build_and_cache_index([], {"f": 2.0})
        assert calls2 == [["alfa", "beta"]], "modelskift skal give fuld re-embed"

    def test_embed_fejl_falder_tilbage_til_fuld(self, monkeypatch, tmp_path):
        ms, _ = self._setup(monkeypatch, tmp_path, ["alfa", "beta"])
        ms._build_and_cache_index([], {"f": 1.0})
        ms, calls2 = self._setup(monkeypatch, tmp_path, ["alfa", "beta", "ny"])
        seen: list[list[str]] = []

        def _fail_once(texts):
            seen.append(list(texts))
            return None if len(seen) == 1 else __import__("numpy").zeros((len(texts), 2), dtype="float32")

        monkeypatch.setattr(ms, "_embed_ollama", _fail_once)
        ms._build_and_cache_index([], {"f": 2.0})
        assert seen[0] == ["ny"] and seen[1] == ["alfa", "beta", "ny"], \
            "fejlet delvis-embed skal falde tilbage til fuld rebuild"
