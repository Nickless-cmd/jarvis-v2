"""Multi-signal retrieval — BM25 keyword scoring + entity fusion.

Part of Memory Architecture Phase B1 (2026-06-08).
Adds keyword-based retrieval (BM25) and entity-aware boosting alongside
existing cosine similarity for more robust memory recall.

BMI25 formula (Okapi BM25):
    score(D, Q) = Σ IDF(q) · (tf(q,D) · (k1 + 1)) / (tf(q,D) + k1 · (1 - b + b · |D|/avgdl))

Reference: https://en.wikipedia.org/wiki/Okapi_BM25

Entity fusion:
    When named entities overlap between query and stored record,
    the record's score is boosted by entity_boost_factor per matching entity.

Usage:
    index = BM25Index()
    index.build([doc.text for doc in records])
    scores = [index.score(query, i) for i in range(len(records))]

    boost = entity_boost_score(query, record_text)
"""
from __future__ import annotations

import logging
import math
import re
from collections import Counter
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tokeniser — shared across BM25 and entity extraction
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokens."""
    return _WORD_RE.findall(text.lower())


# ---------------------------------------------------------------------------
# BM25 Index
# ---------------------------------------------------------------------------

class BM25Index:
    """Pure-Python BM25 (Okapi) index.

    Build from a list of document texts, then score queries against any
    indexed document by index position.

    Thread-safe once built (read-only scoring).
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._corpus_tokens: list[list[str]] = []
        self._doc_freq: Counter[str] = Counter()
        self._n_docs: int = 0
        self._avgdl: float = 0.0
        self._built: bool = False

    # ── Public API ───────────────────────────────────────────────────

    def build(self, documents: list[str]) -> None:
        """Build the BM25 index from a list of document texts.

        Args:
            documents: List of raw text strings, one per document.
                       Empty documents are skipped.
        """
        self._corpus_tokens = [tokenize(d) for d in documents if d.strip()]
        self._n_docs = len(self._corpus_tokens)

        if self._n_docs == 0:
            self._avgdl = 0.0
            self._doc_freq = Counter()
            self._built = True
            return

        total_terms = sum(len(tokens) for tokens in self._corpus_tokens)
        self._avgdl = total_terms / self._n_docs

        # Document frequency: count how many docs contain each term
        self._doc_freq = Counter()
        for doc_tokens in self._corpus_tokens:
            for term in set(doc_tokens):
                self._doc_freq[term] += 1

        self._built = True

    def score(self, query: str, doc_idx: int) -> float:
        """BM25 score for a query against a specific document.

        Args:
            query: Raw query string.
            doc_idx: Index into the build-order document list.

        Returns:
            BM25 score (≥ 0). 0 if doc_idx out of range or query empty.
        """
        if not self._built or doc_idx < 0 or doc_idx >= self._n_docs:
            return 0.0

        query_terms = tokenize(query)
        if not query_terms:
            return 0.0

        doc_tokens = self._corpus_tokens[doc_idx]
        dl = len(doc_tokens)
        if dl == 0:
            return 0.0

        term_freq = Counter(doc_tokens)
        score = 0.0

        for q in query_terms:
            df = self._doc_freq.get(q, 0)
            if df == 0:
                continue

            # IDF with smoothing (same as Elasticsearch / rank_bm25)
            idf = math.log((self._n_docs - df + 0.5) / (df + 0.5) + 1.0)

            tf = term_freq.get(q, 0)
            if tf == 0:
                continue

            numerator = tf * (self.k1 + 1.0)
            denominator = tf + self.k1 * (1.0 - self.b + self.b * dl / self._avgdl)
            score += idf * numerator / denominator

        return score

    def search(self, query: str, top_k: int = 10) -> list[tuple[int, float]]:
        """Return (doc_idx, score) pairs for top-k documents, highest first.

        Args:
            query: Raw query string.
            top_k: Maximum number of results. Pass 0 for all results.

        Returns:
            List of (doc_idx, score) tuples sorted descending by score.
        """
        if not self._built or self._n_docs == 0:
            return []

        scores = [(i, self.score(query, i)) for i in range(self._n_docs)]
        scores.sort(key=lambda x: x[1], reverse=True)

        if top_k > 0:
            scores = scores[:top_k]
        return scores

    @property
    def built(self) -> bool:
        return self._built

    @property
    def n_docs(self) -> int:
        return self._n_docs

    def __repr__(self) -> str:
        return f"BM25Index(n_docs={self._n_docs}, built={self._built})"


# ---------------------------------------------------------------------------
# Entity extraction & fusion
# ---------------------------------------------------------------------------

# Regex patterns for entity detection
_CAPITALIZED_PHRASE_RE = re.compile(r"\b([A-Z][a-zà-öø-ÿ]+(?:\s+[A-Z][a-zà-öø-ÿ]+)*)")
_CAPITALIZED_WORD_RE = re.compile(r"\b([A-Z][a-zà-öø-ÿ]{2,})\b")
_TECH_TERM_RE = re.compile(r"\b([A-Z]{2,}(?:\d+)?)\b")  # BM25, API, CPU, Phase1
_NUMERIC_ENTITY_RE = re.compile(r"\b(Phase\s*\d|Step\s*\d|Uge\s*\d+)\b", re.IGNORECASE)


def extract_entities(text: str) -> set[str]:
    """Extract named entities from text using pattern heuristics.

    Detects:
    - Capitalised phrases (propers name: "Memory Fix", "Identity Sketch")
    - Capitalised single words (proper nouns: "Jarvis", "Bjørn")
    - Tech acronyms ("BM25", "API", "GPU")
    - Numeric entities ("Phase 1", "Uge 25", "Step 3")

    Args:
        text: Raw text to analyse.

    Returns:
        Set of lowercased entity strings.
    """
    if not text:
        return set()

    entities: set[str] = set()

    # Capitalised phrases (2+ consecutive capitalised words)
    for match in _CAPITALIZED_PHRASE_RE.finditer(text):
        phrase = match.group(1).strip()
        words = phrase.split()
        if len(words) >= 2:
            entities.add(phrase.lower())

    # Single capitalised words (≥3 chars to filter abbreviations)
    for match in _CAPITALIZED_WORD_RE.finditer(text):
        entities.add(match.group(1).lower())

    # Tech acronyms (ALL CAPS, optionally with numbers)
    for match in _TECH_TERM_RE.finditer(text):
        entities.add(match.group(1).lower())

    # Numeric entities like "Phase 1", "Step 3"
    for match in _NUMERIC_ENTITY_RE.finditer(text):
        entities.add(match.group(1).lower())

    return entities


def entity_boost_score(
    query: str,
    document_text: str,
    base_score: float = 0.0,
    boost_factor: float = 0.25,
    max_boost: float = 0.75,
) -> float:
    """Compute entity-aware boost for a query-document pair.

    When entities from the query overlap with entities in the document,
    the base score is boosted by boost_factor per matching entity
    (capped at max_boost).

    Args:
        query: Raw query string.
        document_text: Raw document text to compare against.
        base_score: Pre-existing score to boost (0.0 = pure entity score).
        boost_factor: Additional boost per matching entity (default 0.25).
        max_boost: Maximum total boost (default 0.75, caps at 3 entities).

    Returns:
        Boosted score as float.
    """
    if not query or not document_text:
        return base_score

    query_entities = extract_entities(query)
    doc_entities = extract_entities(document_text)

    if not query_entities:
        return base_score

    overlap = query_entities & doc_entities
    if not overlap:
        return base_score

    boost = min(len(overlap), 3) * boost_factor
    return base_score + min(boost, max_boost)


def entity_overlap_score(query: str, document_text: str) -> float:
    """Pure entity overlap score (0.0–1.0) without a base score.

    Useful when entity overlap should be a separate signal component:
        score = 0.7 * embedding_sim + 0.3 * entity_overlap_score(...)

    Returns:
        Float 0.0–1.0: (matched_entities / query_entities) capped.
    """
    if not query or not document_text:
        return 0.0

    query_entities = extract_entities(query)
    doc_entities = extract_entities(document_text)

    if not query_entities:
        return 0.0

    overlap = query_entities & doc_entities
    return min(1.0, len(overlap) / max(1, len(query_entities)))


# ---------------------------------------------------------------------------
# Signal fusion — combine BM25, entity, and embedding scores
# ---------------------------------------------------------------------------

_MULTI_SIGNAL_WEIGHTS: dict[str, float] = {
    "embedding": 0.30,
    "bm25": 0.25,
    "entity": 0.15,
    "recency": 0.15,
    "importance": 0.10,
    "recall_freq": 0.05,
}


def fuse_signals(
    embedding_score: float = 0.0,
    bm25_score: float = 0.0,
    entity_overlap: float = 0.0,
    recency_score: float = 0.0,
    importance: float = 0.5,
    recall_freq: float = 0.0,
    weights: Optional[dict[str, float]] = None,
) -> float:
    """Fuse multiple retrieval signals into a single composite score.

    Weights are normalised automatically so they always sum to 1.0.

    Args:
        embedding_score: Cosine similarity (0.0–1.0).
        bm25_score: BM25 keyword score (raw, normalised internally).
        entity_overlap: Entity overlap fraction (0.0–1.0).
        recency_score: Exponential recency (0.0–1.0, 1.0 = now).
        importance: Record importance (0.0–1.0).
        recall_freq: Normalised recall frequency (0.0–1.0).
        weights: Override signal weights (default _MULTI_SIGNAL_WEIGHTS).

    Returns:
        Fused score 0.0–1.0.
    """
    w = weights or _MULTI_SIGNAL_WEIGHTS

    # Normalise BM25: clip to [0, 10] then sigmoid-normalise
    bm25_norm = 1.0 / (1.0 + math.exp(-min(bm25_score, 10.0) + 3.0))

    total = (
        w.get("embedding", 0.30) * max(0.0, min(1.0, embedding_score))
        + w.get("bm25", 0.25) * bm25_norm
        + w.get("entity", 0.15) * max(0.0, min(1.0, entity_overlap))
        + w.get("recency", 0.15) * max(0.0, min(1.0, recency_score))
        + w.get("importance", 0.10) * max(0.0, min(1.0, importance))
        + w.get("recall_freq", 0.05) * max(0.0, min(1.0, recall_freq))
    )

    return max(0.0, min(1.0, total))


# ---------------------------------------------------------------------------
# Convenience: score a single record against a query
# ---------------------------------------------------------------------------


def score_record(
    query: str,
    record_text: str,
    embedding_score: float = 0.0,
    bm25_index: Optional[BM25Index] = None,
    record_idx: int = 0,
    recency_score: float = 0.0,
    importance: float = 0.5,
    recall_freq: float = 0.0,
) -> dict[str, Any]:
    """Score a single record using all available signals.

    Args:
        query: Original query string.
        record_text: Full text of the record to score.
        embedding_score: Pre-computed cosine similarity (0.0–1.0).
        bm25_index: Pre-built BM25Index containing this record.
        record_idx: This record's index in the BM25Index corpus.
        recency_score: Recency component (0.0–1.0).
        importance: Record importance (0.0–1.0).
        recall_freq: Normalised recall frequency (0.0–1.0).

    Returns:
        Dict with per-signal scores and fused composite.
    """
    # BM25
    bm25_val = bm25_index.score(query, record_idx) if bm25_index and bm25_index.built else 0.0

    # Entity overlap
    entity_val = entity_overlap_score(query, record_text)

    # Fuse
    composite = fuse_signals(
        embedding_score=embedding_score,
        bm25_score=bm25_val,
        entity_overlap=entity_val,
        recency_score=recency_score,
        importance=importance,
        recall_freq=recall_freq,
    )

    return {
        "composite": round(composite, 4),
        "signals": {
            "embedding": round(embedding_score, 4),
            "bm25": round(bm25_val, 4),
            "entity": round(entity_val, 4),
            "recency": round(recency_score, 4),
            "importance": round(importance, 4),
            "recall_freq": round(recall_freq, 4),
        },
    }
