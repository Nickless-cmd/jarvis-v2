"""Unified memory recall — bridge across all memory sources with mood-weighting.

Quality scoring (added 2026-06-08, Memory Fix Phase 1):
- compute_recall_score() — composite quality score for cold-tier filtering
- cold_tier_recall() — wraps unified_recall with quality-scored private_brain
- _gather_private_brain_quality() — embedding-based search with quality filter

Multi-signal retrieval (added 2026-06-08, Memory Fix Phase B1):
- multi_signal_recall() — BM25 + entity fusion + embedding + recency
- fuse_with_bm25_entity() — re-scores gather results with multi-signal fusion
- Requires: core/services/multi_signal_retrieval.py

See: docs/superpowers/specs/2026-06-08-memory-fix-phase1-design.md
     docs/superpowers/plans/2026-06-08-memory-fix-phase1-implementation.md
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np

from core.services.multi_signal_retrieval import BM25Index, entity_overlap_score, fuse_signals

logger = logging.getLogger(__name__)


# Default per-source priority weights (tunable).
#
# 2026-05-22 (Claude, after Codex+Bjørn diagnosis): re-ranked to put
# CURATED truth above SELF-GENERATED content.
#
# The old hierarchy gave private_brain (1.2) the highest weight, above
# the curated workspace files (1.0). This created a self-reinforcing
# hallucination loop: Jarvis would invent a fact in chat → consolidation
# wrote it into private_brain/daily memory → search_memory surfaced it
# again as "internal record" → confirmed in next chat → reinforced.
#
# New hierarchy:
#   workspace (MEMORY.md, IDENTITY.md, SOUL.md, USER.md) — 2.0
#     These are the only sources Bjørn directly curates. They are the
#     ground truth for infrastructure facts, identity, user prefs.
#   chronicle — 1.1
#     Weekly narratives are consolidated and human-supervised. Trustworthy.
#   chat_history — 0.9 (unchanged)
#     Past conversations are evidence-of-said but not ground truth.
#   sensory — 0.8 (unchanged)
#     Recent perceptions are accurate but ephemeral.
#   council — 0.8 (was 1.0)
#     Council deliberations are reasoning artifacts, not facts.
#   private_brain — 0.5 (was 1.2)
#     Self-generated thoughts. Useful for continuity / mood / feel.
#     NEVER trusted as factual ground truth.
_SOURCE_WEIGHTS_DEFAULT: dict[str, float] = {
    "workspace": 2.0,         # CURATED — MEMORY.md, IDENTITY.md, SOUL.md, USER.md
    "chronicle": 1.1,         # consolidated weekly narratives
    "chat_history": 0.9,      # past conversations (evidence-of-said, not truth)
    "sensory": 0.8,           # recent perceptions, time-bounded
    "council": 0.8,           # past council deliberations (reasoning, not facts)
    "private_brain": 0.5,     # SELF-GENERATED — continuity/feel only, never truth
}


# Mood signals → which keyword classes to boost
_MOOD_BOOST_PATTERNS: dict[str, list[str]] = {
    "curiosity": ["lære", "undersøg", "udforsk", "ny", "interessant", "hvordan", "hvorfor"],
    "frustration": ["fejl", "stoppe", "fix", "løsning", "ro", "pause", "afklaring"],
    "fatigue": ["pause", "hvile", "ro", "kort", "simpelt", "afslut"],
    "confidence": ["lykkedes", "virkede", "godt", "stærk", "bekræftet"],
}


def _current_mood() -> dict[str, float]:
    try:
        from core.services.mood_oscillator import get_current_mood, get_mood_intensity
        mood_name = str(get_current_mood() or "")
        intensity = float(get_mood_intensity() or 0.0)
        if mood_name:
            return {mood_name: intensity}
    except Exception:
        pass
    return {}


def _mood_keywords_for_boost(mood: dict[str, float], threshold: float = 0.6) -> set[str]:
    """For each mood dimension above threshold, collect keywords to boost."""
    boost_keywords: set[str] = set()
    for dim, level in mood.items():
        if level >= threshold and dim in _MOOD_BOOST_PATTERNS:
            for kw in _MOOD_BOOST_PATTERNS[dim]:
                boost_keywords.add(kw)
    return boost_keywords


def _apply_mood_boost(text: str, base_score: float, boost_keywords: set[str], boost_factor: float = 0.15) -> float:
    if not boost_keywords or not text:
        return base_score
    lower = text.lower()
    hits = sum(1 for kw in boost_keywords if kw in lower)
    if hits == 0:
        return base_score
    return base_score * (1.0 + boost_factor * min(hits, 3))


# ── Quality scoring (Memory Fix Phase 1, 2026-06-08) ──────────────


def compute_recall_score(
    *,
    query_embedding: list[float],
    record_embedding: list[float],
    created_at: str | datetime,
    importance: float = 0.5,
    recall_freq: int = 0,
    now: Optional[datetime] = None,
    config: Optional[dict] = None,
) -> float:
    """Composite quality score for cold-tier memory filtering.

    Score = (embedding_sim × 0.4) + (recency × 0.3) + (recall_freq × 0.2) + (importance × 0.1)

    Components:
    - **embedding_sim**: cosine similarity between query and record embeddings
    - **recency**: exponential decay with halflife (default 90 days)
    - **recall_freq**: capped at configurable max (default 5), then normalised
    - **importance**: the record's own importance rating (0.0-1.0)

    Args:
        query_embedding: Embedding vector of the search query.
        record_embedding: Embedding vector of the stored record.
        created_at: ISO datetime string or datetime when record was created.
        importance: Record importance 0.0-1.0 (default 0.5).
        recall_freq: Number of times record has been recalled (default 0).
        now: Reference time for recency calculation (default UTC now).
        config: Override dict with keys:
            - recency_half_life_days (default 90)
            - recall_frequency_cap (default 5)

    Returns:
        Float 0.0-1.0 representing the composite quality score.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    cfg = config or {}
    half_life_days = cfg.get("recency_half_life_days", 90)
    freq_cap = cfg.get("recall_frequency_cap", 5)

    # 1. Embedding similarity (cosine)
    q = np.array(query_embedding, dtype=np.float32)
    r = np.array(record_embedding, dtype=np.float32)
    q_norm = np.linalg.norm(q)
    r_norm = np.linalg.norm(r)
    norm_product = q_norm * r_norm
    if norm_product > 0:
        embedding_sim = float(np.dot(q, r) / norm_product)
    else:
        embedding_sim = 0.0
    # Clamp to [0, 1] (cosine is [-1, 1] in theory, but embeddings are non-negative)
    embedding_sim = max(0.0, min(1.0, embedding_sim))

    # 2. Recency — exponential decay
    if isinstance(created_at, str):
        try:
            from dateutil.parser import isoparse
            created = isoparse(created_at)
        except Exception:
            created = now
    else:
        created = created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    days_since = max(0.0, (now - created).total_seconds() / 86400.0)
    recency = math.exp(-days_since / half_life_days)

    # 3. Recall frequency — capped linear normalisation
    freq = min(recall_freq, freq_cap) / freq_cap

    # 4. Importance
    imp = max(0.0, min(1.0, importance))

    # Composite
    score = embedding_sim * 0.4 + recency * 0.3 + freq * 0.2 + imp * 0.1
    return max(0.0, min(1.0, score))


def _gather_private_brain_quality(
    query: str,
    limit: int,
    quality_threshold: float = 0.25,
) -> list[dict[str, Any]]:
    """Embedding-based private brain search with quality scoring.

    Uses ``jarvis_brain.search_brain()`` directly to get embedding similarity
    + full BrainEntry metadata, then applies ``compute_recall_score()`` for
    composite filtering. Only returns records above quality_threshold.

    Args:
        query: Search query string.
        limit: Max results to return.
        quality_threshold: Minimum composite quality score (0.0-1.0).
                          Default 0.25 — filters out very weak matches.

    Returns:
        List of result dicts with quality_score metadata.
    """
    try:
        from core.services import jarvis_brain
        entries = jarvis_brain.search_brain(
            query_text=query,
            visibility_ceiling="personal",
            limit=limit * 2,  # fetch extra, filter down
            include_archived=False,
        )
    except Exception:
        # Fallback to keyword-based gatherer
        return _gather_private_brain(query, limit)

    if not entries:
        return []

    # Get query embedding for quality scoring
    try:
        qv = jarvis_brain._embed_text(query)
    except Exception:
        # Can't compute quality score without query embedding
        # Fall through to simple score sort
        results = []
        for e in entries[:limit]:
            results.append({
                "source": "private_brain",
                "subsource": e.kind,
                "section": "",
                "text": e.content[:500],
                "score": e.importance,
                "quality_score": e.importance,
                "method": "embedding",
                "entry_id": e.id,
                "created_at": e.created_at.isoformat(),
                "importance": e.importance,
            })
        return results

    scored: list[tuple[float, dict[str, Any]]] = []
    for e in entries:
        # Get record embedding from DB
        try:
            conn = jarvis_brain.connect_index()
            row = conn.execute(
                "SELECT embedding, embedding_dim FROM brain_index WHERE id = ?",
                (e.id,),
            ).fetchone()
            conn.close()
            if row and row[0] and row[1]:
                record_emb = jarvis_brain._embedding_from_blob(row[0], row[1])
                record_emb_list = record_emb.tolist()
            else:
                # No embedding stored — use zero vector = low similarity
                record_emb_list = [0.0] * 768
        except Exception:
            record_emb_list = [0.0] * 768

        quality = compute_recall_score(
            query_embedding=qv.tolist(),
            record_embedding=record_emb_list,
            created_at=e.created_at,
            importance=e.importance,
            recall_freq=e.recall_count,
        )

        if quality < quality_threshold:
            continue

        scored.append((quality, {
            "source": "private_brain",
            "subsource": e.kind,
            "section": "",
            "text": e.content[:500],
            "score": quality,
            "quality_score": quality,
            "method": "embedding+quality",
            "entry_id": e.id,
            "created_at": e.created_at.isoformat(),
            "importance": e.importance,
            "salience_bumps": e.salience_bumps,
            "recall_count": e.recall_count,
        }))

    scored.sort(key=lambda t: t[0], reverse=True)
    return [item[1] for item in scored[:limit]]


# ── Gather functions ───────────────────────────────────────────────


def _gather_failed(source: str, exc: Exception) -> list[dict[str, Any]]:
    """Memory-cluster trace (2026-06-22): en recall-kilde fejlede. FØR sluttede
    gather-funktionerne stille (`return []` / debug-log som filtreres i runtime) →
    'prompten bygges uden den kilde' var USYNLIGT. NU: WARNING + central-trace, så
    en brækket recall-kilde ses. Returnerer [] (fail-soft bevaret)."""
    logger.warning("recall-kilde '%s' fejlede — udeladt fra recall: %s", source, exc)
    try:
        from core.services.central_core import central as _central_recall
        _central_recall().observe({
            "cluster": "memory", "nerve": f"recall_{source}", "kind": "gather_error",
        })
    except Exception:
        pass
    return []


def _gather_workspace(query: str, limit: int) -> list[dict[str, Any]]:
    try:
        from core.services.memory_search import search_memory
        results = search_memory(query, limit=limit) or []
        return [
            {
                "source": "workspace",
                "subsource": str(r.get("source", "")),
                "section": str(r.get("section", "")),
                "text": str(r.get("text", "")),
                "score": float(r.get("score", 0.0)),
                "method": str(r.get("method", "")),
            }
            for r in results
        ]
    except Exception as exc:
        return _gather_failed("workspace", exc)


def _gather_private_brain(query: str, limit: int) -> list[dict[str, Any]]:
    # FIX 2026-06-22: importerede et IKKE-eksisterende modul (core.services.
    # private_brain.search_private_brain) → kastede ModuleNotFoundError på HVERT
    # kald → recall så ALDRIG de ~92k private_brain-records (Memory-clusterens
    # største kilde var død+usynlig). Nu: list seneste aktive records (auto-scopet
    # til bruger via scope_uid i list_private_brain_records) + keyword-overlap-score,
    # samme mønster som _gather_chronicle. Bounded (recency), fail-soft.
    # SQL-tekst-søgning over HELE tabellen (de ~92k) — IKKE kun de seneste/aktive.
    # search_private_brain_records LIKE-matcher focus/summary/detail, auto-scopet til
    # bruger, ekskl. 'released'. Python re-scorer for ranking. (FTS5 = perf-fix hvis
    # recall-latency bliver et problem.)
    try:
        from core.runtime.db_private_brain import search_private_brain_records
        records = search_private_brain_records(query, limit=60) or []
    except Exception as exc:
        return _gather_failed("private_brain", exc)
    words = {w for w in query.lower().split() if len(w) > 3}
    if not words:
        return []
    scored: list[tuple[float, dict[str, Any]]] = []
    for r in records:
        text = " ".join(
            str(r.get(k) or "") for k in ("focus", "summary", "detail")
        ).strip()
        if not text:
            continue
        tl = text.lower()
        hits = sum(1 for w in words if w in tl)
        if hits == 0:
            continue
        score = min(1.0, hits / max(1, len(words)))
        scored.append((score, {
            "source": "private_brain",
            "subsource": str(r.get("record_type") or ""),
            "section": "",
            "text": text[:500],
            "score": score,
            "method": "keyword-overlap",
        }))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [item[1] for item in scored[:limit]]


def _gather_chronicle(query: str, limit: int) -> list[dict[str, Any]]:
    try:
        from core.services.chronicle_engine import list_cognitive_chronicle_entries
        entries = list_cognitive_chronicle_entries(limit=20) or []
    except Exception as exc:
        return _gather_failed("chronicle", exc)
    q_lower = query.lower()
    scored: list[tuple[float, dict[str, Any]]] = []
    for e in entries:
        text = str(e.get("narrative") or e.get("summary") or "")
        if not text:
            continue
        # Crude keyword overlap score
        words = set(q_lower.split())
        text_lower = text.lower()
        hits = sum(1 for w in words if w in text_lower and len(w) > 3)
        if hits == 0:
            continue
        score = min(1.0, hits / max(1, len(words)))
        scored.append((score, {
            "source": "chronicle",
            "subsource": str(e.get("period") or "weekly"),
            "section": "",
            "text": text[:500],
            "score": score,
            "method": "keyword-overlap",
        }))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [item[1] for item in scored[:limit]]


# ── Cold-tier recall with quality scoring (Memory Fix Phase 1, 2026-06-08) ──


def cold_tier_recall(
    *,
    query: str,
    max_results: int = 6,
    with_mood: bool = True,
    quality_threshold: float = 0.25,
    include_private_brain: bool = True,
) -> dict[str, Any]:
    """Cold-tier recall across curated sources + quality-scored private brain.

    Unlike ``unified_recall()`` which uses the same per-source weights for
    all results, this function:

    1. Searches **workspace** + **chronicle** (truth-bearing, weight 2.0/1.1)
       via the existing ``_gather_*`` functions.
    2. Searches **private_brain** via ``_gather_private_brain_quality()``
       which applies ``compute_recall_score()`` — only records above
       *quality_threshold* are included.
    3. Applies source-weight: private_brain results get 0.5 (low trust),
       but their *quality_score* is preserved in ``quality_score`` field
       so the caller can make their own trust decision.
    4. Optionally mood-boosts (same mechanism as unified_recall).

    This replaces the old hard exclusion of private_brain from cold tier
    with a **quality gate** — good self-generated content surfaces,
    noise and hallucinations are filtered out.

    Args:
        query: Search query.
        max_results: Total results to return across all sources.
        with_mood: Apply mood-weighted boost.
        quality_threshold: Minimum quality score for private_brain results
                          (0.0-1.0). Default 0.25.
        include_private_brain: If False, skip private_brain entirely
                              (behaves like old cold tier).

    Returns:
        Dict with keys: status, results, count, sources_searched, quality_filtered.
    """
    query = (query or "").strip()
    if not query:
        return {"status": "ok", "results": [], "count": 0}

    limit_per_source = max(2, max_results // 2)

    # 1. Truth-bearing sources (workspace + chronicle)
    all_results: list[dict[str, Any]] = []
    all_results.extend(_gather_workspace(query, limit_per_source))
    all_results.extend(_gather_chronicle(query, limit_per_source))
    sources_searched = ["workspace", "chronicle"]

    # 2. Quality-scored private brain
    quality_filtered = 0
    if include_private_brain:
        sources_searched.append("private_brain")
        pb_results = _gather_private_brain_quality(
            query, limit_per_source, quality_threshold=quality_threshold,
        )
        quality_filtered = limit_per_source - len(pb_results)
        all_results.extend(pb_results)

    # 3. Apply per-source weights
    weights = _SOURCE_WEIGHTS_DEFAULT
    for r in all_results:
        src = str(r.get("source", ""))
        r["weighted_score"] = float(r.get("quality_score", r.get("score", 0.0))) * weights.get(src, 1.0)

    # 4. Candidate penalty
    for r in all_results:
        if "[CANDIDATE→" in str(r.get("text", "")):
            r["weighted_score"] = float(r.get("weighted_score", 0.0)) * 0.3
            r["candidate_penalty"] = True

    # 5. Mood boost
    mood_boosted = False
    if with_mood:
        mood = _current_mood()
        boost_kws = _mood_keywords_for_boost(mood)
        if boost_kws:
            mood_boosted = True
            for r in all_results:
                r["weighted_score"] = _apply_mood_boost(
                    r.get("text", ""),
                    r["weighted_score"],
                    boost_kws,
                )

    all_results.sort(key=lambda r: r["weighted_score"], reverse=True)
    top = all_results[:max_results]
    return {
        "status": "ok",
        "results": top,
        "count": len(top),
        "total_candidates": len(all_results),
        "mood_boosted": mood_boosted,
        "sources_searched": sources_searched,
        "quality_filtered": quality_filtered,
        "quality_threshold": quality_threshold,
        "tier": "cold",
    }


# ── Unified recall (legacy, mood-weighted aggregator) ──────────────


def unified_recall(
    *,
    query: str,
    sources: list[str] | None = None,
    limit_per_source: int = 3,
    total_limit: int = 8,
    with_mood: bool = True,
) -> dict[str, Any]:
    """Search across all configured memory sources, mood-weighted."""
    query = (query or "").strip()
    if not query:
        return {"status": "ok", "results": [], "count": 0, "mood_boosted": False}

    enabled = set(sources or _SOURCE_WEIGHTS_DEFAULT.keys())
    weights = _SOURCE_WEIGHTS_DEFAULT

    all_results: list[dict[str, Any]] = []
    if "workspace" in enabled:
        all_results.extend(_gather_workspace(query, limit_per_source))
    if "private_brain" in enabled:
        all_results.extend(_gather_private_brain(query, limit_per_source))
    if "chronicle" in enabled:
        all_results.extend(_gather_chronicle(query, limit_per_source))

    # Apply per-source weight
    for r in all_results:
        src = str(r.get("source", ""))
        r["weighted_score"] = float(r.get("score", 0.0)) * weights.get(src, 1.0)

    # 2026-05-22 (Claude): legacy [CANDIDATE→] penalty. The bulk-rewrite
    # script (scripts/rewrite_legacy_memory_provenance.py) renamed ~2045
    # daily entries from fake `[MEMORY.md]` provenance to honest
    # `[CANDIDATE→MEMORY.md]` provenance — they were proposals that may
    # never have been adopted. Source-weight alone doesn't penalize them
    # (they live in workspace dailies → weight 2.0), so they still surface
    # at top ranks for keyword matches. Multiply weighted_score by 0.3 so
    # they only surface when nothing else is available, but don't drop
    # them entirely — they CAN be useful as low-confidence hints.
    for r in all_results:
        if "[CANDIDATE→" in str(r.get("text", "")):
            r["weighted_score"] = float(r.get("weighted_score", 0.0)) * 0.3
            r["candidate_penalty"] = True

    # Mood boost
    mood_boosted = False
    if with_mood:
        mood = _current_mood()
        boost_kws = _mood_keywords_for_boost(mood)
        if boost_kws:
            mood_boosted = True
            for r in all_results:
                r["weighted_score"] = _apply_mood_boost(
                    r.get("text", ""),
                    r["weighted_score"],
                    boost_kws,
                )

    all_results.sort(key=lambda r: r["weighted_score"], reverse=True)
    top = all_results[:total_limit]
    return {
        "status": "ok",
        "results": top,
        "count": len(top),
        "total_searched": len(all_results),
        "mood_boosted": mood_boosted,
        "sources_searched": sorted(enabled),
    }


def unified_recall_section(query: str, *, max_results: int = 4) -> str | None:
    """Format unified recall as a prompt-awareness section. Optional callsite."""
    result = unified_recall(query=query, total_limit=max_results)
    items = result.get("results") or []
    if not items:
        return None
    lines = ["Relevante hukommelser (mood-vægtet hvis aktiv):"]
    for r in items:
        src = str(r.get("source", "?"))
        text = str(r.get("text", ""))[:160].replace("\n", " ")
        lines.append(f"  • [{src}] {text}")
    return "\n".join(lines)


# ── Multi-signal retrieval (B1, 2026-06-08) ────────────────────────

_MULTI_SIGNAL_SOURCES = ("workspace", "chronicle", "private_brain")


def _compute_multi_signal_scores(
    query: str,
    records: list[dict[str, Any]],
    recency_fn: Any = None,
) -> list[dict[str, Any]]:
    """Re-score gathered records with BM25 + entity fusion + embedding."""
    if not records or not query:
        return records

    # Build BM25 index from record texts
    texts = [str(r.get("text", "") or "") for r in records]
    index = BM25Index(k1=1.2, b=0.5)
    index.build(texts)

    # Compute recency if callable provided
    for i, r in enumerate(records):
        embedding_score = float(r.get("score", 0.0))
        text = texts[i]

        # BM25
        bm25_val = index.score(query, i)

        # Entity overlap
        entity_val = entity_overlap_score(query, text)

        # Recency (use created_at if available)
        recency_score = 0.5  # default middle value
        if recency_fn:
            try:
                created = r.get("created_at") or r.get("timestamp") or ""
                if created:
                    recency_score = recency_fn(created)
            except Exception:
                pass

        # Importance
        importance = float(r.get("importance", 0.5) or 0.5)
        recall_freq_raw = int(r.get("recall_count", 0) or 0)
        freq_cap = 5
        recall_freq = min(recall_freq_raw, freq_cap) / freq_cap

        # Fuse signals
        composite = fuse_signals(
            embedding_score=embedding_score,
            bm25_score=bm25_val,
            entity_overlap=entity_val,
            recency_score=recency_score,
            importance=importance,
            recall_freq=recall_freq,
        )

        r["multi_signal_score"] = round(composite, 4)
        r["signals"] = {
            "embedding": round(embedding_score, 4),
            "bm25": round(bm25_val, 4),
            "entity": round(entity_val, 4),
            "recency": round(recency_score, 4),
            "importance": round(importance, 4),
            "recall_freq": round(recall_freq, 4),
        }
        r["method"] = "multi_signal"

    return records


def multi_signal_recall(
    *,
    query: str,
    sources: list[str] | None = None,
    limit_per_source: int = 3,
    total_limit: int = 8,
    with_mood: bool = True,
    min_score: float = 0.0,
) -> dict[str, Any]:
    """Multi-signal recall: BM25 + entity fusion + embedding + recency.

    Gathers records from all enabled sources, then re-scores each using
    a fused combination of:
    - **Embedding similarity** (cosine, from gather functions) — 30%
    - **BM25 keyword score** — 25%
    - **Entity overlap** — 15%
    - **Recency** — 15%
    - **Importance** — 10%
    - **Recall frequency** — 5%

    This provides more robust retrieval than pure embedding search,
    especially for keyword-rich queries (e.g. "Phase 1 quality scoring
    cold tier") where BM25 catches exact terms the embedding might miss.

    Args:
        query: Search query.
        sources: Subset of sources to search. Default: workspace + chronicle
                + private_brain.
        limit_per_source: Max records per source before fusion (default 3).
        total_limit: Total results after fusion (default 8).
        with_mood: Apply mood-weighted boost (default True).

    Returns:
        Dict with keys: status, results, count, sources_searched,
        multi_signal, signal_weights.
    """
    query = (query or "").strip()
    if not query:
        return {
            "status": "ok", "results": [], "count": 0,
            "multi_signal": False,
        }

    enabled = set(sources or _MULTI_SIGNAL_SOURCES)
    weights = _SOURCE_WEIGHTS_DEFAULT

    # 1. Gather records from all sources (same as unified_recall)
    all_results: list[dict[str, Any]] = []
    if "workspace" in enabled:
        all_results.extend(_gather_workspace(query, limit_per_source))
    if "chronicle" in enabled:
        all_results.extend(_gather_chronicle(query, limit_per_source))
    if "private_brain" in enabled:
        all_results.extend(_gather_private_brain(query, limit_per_source))

    if not all_results:
        return {
            "status": "ok", "results": [], "count": 0,
            "multi_signal": True,
            "sources_searched": sorted(enabled),
            "signal_weights": {
                "embedding": 0.30,
                "bm25": 0.25,
                "entity": 0.15,
                "recency": 0.15,
                "importance": 0.10,
                "recall_freq": 0.05,
            },
        }

    # 2. Apply source weights
    for r in all_results:
        src = str(r.get("source", ""))
        r["weighted_score"] = float(r.get("score", 0.0)) * weights.get(src, 1.0)

    # 3. Multi-signal fusion scoring
    all_results = _compute_multi_signal_scores(query, all_results)

    # 4. Candidate penalty (legacy)
    for r in all_results:
        if "[CANDIDATE→" in str(r.get("text", "")):
            r["multi_signal_score"] = float(r.get("multi_signal_score", 0.0)) * 0.3
            r["candidate_penalty"] = True

    # 5. Mood boost
    mood_boosted = False
    if with_mood:
        mood = _current_mood()
        boost_kws = _mood_keywords_for_boost(mood)
        if boost_kws:
            mood_boosted = True
            for r in all_results:
                r["multi_signal_score"] = _apply_mood_boost(
                    r.get("text", ""),
                    r["multi_signal_score"],
                    boost_kws,
                )

    # 5b. Temporal boost (B4, 2026-06-09)
    temporal_boosted = False
    entry_ids_in_results = [
        r["entry_id"] for r in all_results
        if r.get("entry_id") and r.get("source") == "private_brain"
    ]
    if entry_ids_in_results:
        try:
            from core.services.jarvis_brain import temporal_boost_recall
            boosts = temporal_boost_recall(
                entry_ids_in_results,
                boost_factor=0.15,
                min_confidence=0.5,
            )
            if boosts:
                temporal_boosted = True
                for r in all_results:
                    eid = r.get("entry_id")
                    if eid and eid in boosts:
                        r["multi_signal_score"] = round(
                            r.get("multi_signal_score", 0.0) + boosts[eid], 4
                        )
                        r["temporal_boost"] = True
        except Exception:
            # Best-effort — never let temporal boost block recall
            pass

    # 6. Cutoff under tærskel (støj som "No active runtime loop" score=0.28 slap FØR
    #    igennem — multi_signal_score brugtes kun til sort, aldrig som filter), så sortér.
    if min_score > 0.0:
        all_results = [r for r in all_results if r.get("multi_signal_score", 0.0) >= min_score]
    all_results.sort(key=lambda r: r.get("multi_signal_score", 0.0), reverse=True)
    top = all_results[:total_limit]

    return {
        "status": "ok",
        "results": top,
        "count": len(top),
        "total_candidates": len(all_results),
        "mood_boosted": mood_boosted,
        "temporal_boosted": temporal_boosted,
        "multi_signal": True,
        "sources_searched": sorted(enabled),
        "signal_weights": {
            "embedding": 0.30,
            "bm25": 0.25,
            "entity": 0.15,
            "recency": 0.15,
            "importance": 0.10,
            "recall_freq": 0.05,
        },
    }


def multi_signal_recall_section(query: str, *, max_results: int = 4) -> str | None:
    """Format multi-signal recall as a prompt-awareness section."""
    # Ekskludér private_brain — det surfacer ALLEREDE i "private continuity"-sektionen
    # (dublet: "No active runtime loop" / "Du dør hver gang du bruger tools" stod begge
    #  steder). Cutoff under 0.32 fjerner støj-poster. (Jarvis-spec 2026-06-23 #4 + #6.)
    result = multi_signal_recall(query=query, total_limit=max_results, with_mood=True,
                                 sources=["workspace", "chronicle"], min_score=0.32)
    items = result.get("results") or []
    if not items:
        return None
    lines = ["🔀 Multi-signal hukommelser (BM25 + entity + embedding):"]
    for r in items:
        src = str(r.get("source", "?"))
        ms = r.get("multi_signal_score", 0.0)
        sig = r.get("signals", {})
        sig_str = f"B={sig.get('bm25', 0):.2f} E={sig.get('entity', 0):.2f}"
        text = str(r.get("text", ""))[:120].replace("\n", " ")
        lines.append(f"  • [{src}] (score={ms:.2f}, {sig_str}) {text}")
    return "\n".join(lines)


def _exec_unified_recall(args: dict[str, Any]) -> dict[str, Any]:
    return unified_recall(
        query=str(args.get("query") or ""),
        sources=args.get("sources"),
        limit_per_source=int(args.get("limit_per_source") or 3),
        total_limit=int(args.get("total_limit") or 8),
        with_mood=bool(args.get("with_mood", True)),
    )


UNIFIED_RECALL_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "unified_recall",
            "description": (
                "Search across ALL memory sources at once: workspace files "
                "(MEMORY/SOUL/IDENTITY), private_brain records, chronicle "
                "narratives. Optionally mood-weighted: current affective state "
                "boosts memories matching dominant mood themes (curiosity → "
                "exploratory; frustration → coping; etc). Returns top-K most "
                "relevant across sources."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Subset of: workspace, private_brain, chronicle. Default = all.",
                    },
                    "limit_per_source": {"type": "integer"},
                    "total_limit": {"type": "integer"},
                    "with_mood": {"type": "boolean"},
                },
                "required": ["query"],
            },
        },
    },
]
