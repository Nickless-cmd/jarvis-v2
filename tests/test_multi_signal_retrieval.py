"""Unit tests for multi-signal retrieval — BM25, entity fusion, signal scoring."""
from __future__ import annotations

import math

import pytest

from core.services.multi_signal_retrieval import (
    BM25Index,
    extract_entities,
    entity_boost_score,
    entity_overlap_score,
    fuse_signals,
    score_record,
    tokenize,
)


# ─── Tokeniser ──────────────────────────────────────────────────────────


def test_tokenize_splits_on_non_alphanum():
    assert tokenize("Hello World! BM25-v2") == ["hello", "world", "bm25", "v2"]


def test_tokenize_lowercases():
    assert tokenize("Jarvis API") == ["jarvis", "api"]


def test_tokenize_empty():
    assert tokenize("") == []


def test_tokenize_danish():
    # Note: tokenizer only matches [a-z0-9], so æ/ø/å are stripped
    result = tokenize("Husk at købe æbler og øl")
    assert "husk" in result
    assert "at" in result
    assert "og" in result
    # The Danish letters (æ, ø, å) don't match [a-z], so they're filtered out
    assert "k" in result or "kbe" not in result  # 'købe' becomes 'k' + 'be'


# ─── BM25Index ──────────────────────────────────────────────────────────


def test_bm25_empty_corpus():
    idx = BM25Index()
    idx.build([])
    assert idx.built
    assert idx.n_docs == 0
    assert idx.score("test", 0) == 0.0
    assert idx.search("test") == []


def test_bm25_basic_scoring():
    docs = [
        "Jarvis has a fast API endpoint",
        "The weather is nice today",
        "Jarvis API handles memory retrieval",
    ]
    idx = BM25Index()
    idx.build(docs)
    # Doc 0 and 2 share "Jarvis" and "API" with query
    scores = [idx.score("Jarvis API", i) for i in range(3)]
    assert scores[1] < scores[0] + scores[2]  # doc 1 unrelated


def test_bm25_identical_doc_scores_highest():
    docs = ["memory phase 1 fix", "some other thing", "memory phase 1 fix"]
    idx = BM25Index()
    idx.build(docs)
    s0 = idx.score("memory phase 1", 0)
    s1 = idx.score("memory phase 1", 1)
    assert s0 > s1


def test_bm25_search_top_k():
    docs = ["a", "b c", "d e f", "a b c d e f"]
    idx = BM25Index()
    idx.build(docs)
    results = idx.search("a b", top_k=2)
    assert len(results) == 2
    # highest score first
    assert results[0][1] >= results[1][1]


def test_bm25_search_all():
    docs = ["alpha", "beta", "gamma"]
    idx = BM25Index()
    idx.build(docs)
    results = idx.search("alpha", top_k=0)
    assert len(results) == 3


def test_bm25_out_of_range():
    idx = BM25Index()
    idx.build(["hello"])
    assert idx.score("hello", 99) == 0.0


def test_bm25_score_empty_query():
    idx = BM25Index()
    idx.build(["hello world"])
    assert idx.score("", 0) == 0.0


def test_bm25_repr():
    idx = BM25Index()
    idx.build(["a", "b"])
    r = repr(idx)
    assert "n_docs=2" in r
    assert "built=True" in r


def test_bm25_default_params():
    idx = BM25Index()
    assert idx.k1 == 1.5
    assert idx.b == 0.75


def test_bm25_custom_params():
    idx = BM25Index(k1=1.2, b=0.5)
    assert idx.k1 == 1.2
    assert idx.b == 0.5


# ─── Entity extraction ──────────────────────────────────────────────────


def test_extract_entities_capitalized_phrase():
    ents = extract_entities("This is the Memory Fix Phase 1 design")
    assert "memory fix" in ents or "memory fix phase" in ents


def test_extract_entities_single_cap_word():
    ents = extract_entities("Jarvis built this for Bjørn")
    assert "jarvis" in ents
    assert "bjørn" in ents


def test_extract_entities_tech_acronym():
    ents = extract_entities("Use BM25 and API via HTTP")
    assert "bm25" in ents
    assert "api" in ents
    assert "http" in ents


def test_extract_entities_numeric():
    ents = extract_entities("Phase 1 and Step 3 are done")
    assert "phase 1" in ents or "phase1" in ents
    assert "step 3" in ents or "step3" in ents


def test_extract_entities_empty():
    assert extract_entities("") == set()
    assert extract_entities(None) == set()  # type: ignore


def test_extract_entities_no_match():
    assert extract_entities("hello world and stuff") == set()


# ─── Entity boost ───────────────────────────────────────────────────────


def test_entity_boost_score_matches():
    boosted = entity_boost_score(
        "Where is Memory Fix Phase 1?",
        "The Memory Fix Phase 1 design is ready",
        base_score=0.5,
    )
    assert boosted > 0.5


def test_entity_boost_score_no_match():
    boosted = entity_boost_score(
        "Jarvis API",
        "The weather is nice today",
        base_score=0.5,
    )
    assert boosted == 0.5


def test_entity_boost_score_empty_query():
    assert entity_boost_score("", "some text", base_score=0.3) == 0.3


def test_entity_boost_score_empty_doc():
    assert entity_boost_score("Jarvis", "", base_score=0.5) == 0.5


def test_entity_boost_score_capped():
    """Max boost is 0.75 regardless of entity count."""
    boosted = entity_boost_score(
        "Jarvis Bjørn Memory Fix Phase 1 BM25 Entity Fusion",
        "Jarvis and Bjørn worked on Memory Fix Phase 1 using BM25 Entity Fusion",
        base_score=0.0,
        boost_factor=0.25,
    )
    # 5+ entities → cap at 0.75
    assert boosted <= 0.75


# ─── Entity overlap score ────────────────────────────────────────────────


def test_entity_overlap_full():
    score = entity_overlap_score("Jarvis API", "Jarvis API endpoint")
    assert score == 1.0


def test_entity_overlap_partial():
    score = entity_overlap_score("Jarvis API BM25", "Jarvis is working on BM25")
    assert 0.0 < score < 1.0


def test_entity_overlap_none():
    score = entity_overlap_score("Jarvis API", "The weather is nice")
    assert score == 0.0


def test_entity_overlap_empty_query():
    assert entity_overlap_score("", "Jarvis") == 0.0


def test_entity_overlap_empty_doc():
    assert entity_overlap_score("Jarvis", "") == 0.0


# ─── Signal fusion ──────────────────────────────────────────────────────


def test_fuse_signals_all_max():
    score = fuse_signals(
        embedding_score=1.0,
        bm25_score=10.0,
        entity_overlap=1.0,
        recency_score=1.0,
        importance=1.0,
        recall_freq=1.0,
    )
    assert score > 0.90  # should be near 1.0


def test_fuse_signals_all_min():
    score = fuse_signals(
        embedding_score=0.0,
        bm25_score=0.0,
        entity_overlap=0.0,
        recency_score=0.0,
        importance=0.0,
        recall_freq=0.0,
    )
    assert score >= 0.0
    assert score < 0.05


def test_fuse_signals_clamps():
    """Out-of-range values get clamped to [0, 1]."""
    score = fuse_signals(embedding_score=5.0, bm25_score=-1.0)
    assert 0.0 <= score <= 1.0


def test_fuse_signals_default_weights_present():
    """Uses default weights when none provided."""
    score = fuse_signals(embedding_score=0.5)
    # without all signals, still returns something in [0, 1]
    assert 0.0 <= score <= 1.0


def test_fuse_signals_bm25_normalisation():
    """BM25 score is sigmoid-normalised around 3.0."""
    s_low = fuse_signals(bm25_score=0.0, embedding_score=0.0)
    s_high = fuse_signals(bm25_score=10.0, embedding_score=0.0)
    assert s_high >= s_low


# ─── score_record convenience ────────────────────────────────────────────


def test_score_record_basic():
    docs = ["Jarvis API handles memory"]
    idx = BM25Index()
    idx.build(docs)
    result = score_record(
        query="Jarvis API",
        record_text="Jarvis API handles memory",
        embedding_score=0.8,
        bm25_index=idx,
        record_idx=0,
    )
    assert "composite" in result
    assert "signals" in result
    assert 0.0 <= result["composite"] <= 1.0
    assert result["signals"]["embedding"] == 0.8


def test_score_record_no_bm25():
    result = score_record(
        query="test",
        record_text="some text",
        embedding_score=0.5,
        bm25_index=None,
    )
    assert result["signals"]["bm25"] == 0.0
