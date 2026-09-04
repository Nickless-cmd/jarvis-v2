"""One recall path over every memory source (memory repair 2026-09-04, R5).

Before: ten tools over four vector indexes plus LIKE-scans, each seeing a
slice; ``unified_recall.py`` was dead on all three arms; the associative
path returned nothing in 73 % of calls. Now: ``recall()`` asks every source
for candidates with a native score in [0, 1], re-scores them together with
BM25 over the candidate texts, dedupes, and returns one ranked list.

Sources (default): workspace (MEMORY.md/USER.md/curated/daily via the
embedding index), brain (jarvis_brain, cosine floor 0.5), private_brain
(active/settling only, embeddings), session_summary (FTS5), chronicle
(keyword overlap). ``chat`` (FTS5 over chat_messages) is opt-in because it is
noisy. Every source is fail-soft: an exception in one source never hides the
others.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Callable

logger = logging.getLogger(__name__)

DEFAULT_SOURCES: tuple[str, ...] = ("workspace", "brain", "private_brain", "session_summary", "chronicle")
ALL_SOURCES: tuple[str, ...] = DEFAULT_SOURCES + ("chat", "sensory")

_NATIVE_WEIGHT = 0.6
_BM25_WEIGHT = 0.4
_DEDUPE_CHARS = 80
_TEXT_CAP = 500

_ACTIVE_PRIVATE_BRAIN = frozenset({"active", "settling", "fading", "completed"})


def _clip(text: str, cap: int = _TEXT_CAP) -> str:
    t = " ".join(str(text or "").split())
    return t if len(t) <= cap else t[: cap - 1].rstrip() + "…"


def _dedupe_key(text: str) -> str:
    t = re.sub(r"[^0-9a-zæøå]+", " ", str(text or "").lower())
    return " ".join(t.split())[:_DEDUPE_CHARS]


# ── sources ─────────────────────────────────────────────────────────────


def _source_workspace(query: str, limit: int) -> list[dict[str, Any]]:
    from core.services.memory_search import search_memory

    out = []
    for r in search_memory(query, limit=limit) or []:
        section = str(r.get("section") or "").strip()
        text = str(r.get("text") or "")
        out.append({
            "source": "workspace",
            "score": max(0.0, min(1.0, float(r.get("score") or 0.0))),
            "text": _clip(f"§ {section}: {text}" if section else text),
            "ref": str(r.get("source") or ""),
        })
    return out


def _source_brain(query: str, limit: int) -> list[dict[str, Any]]:
    from core.services import jarvis_brain

    out = []
    scored = jarvis_brain.search_brain_scored(query_text=query, limit=limit, min_cosine=0.5)
    for score, eid in scored:
        try:
            e = jarvis_brain.read_entry(eid)
        except Exception:
            continue
        out.append({
            "source": "brain",
            "score": max(0.0, min(1.0, float(score))),
            "text": _clip(f"{e.title}: {e.content}"),
            "ref": eid,
        })
    return out


def _source_private_brain(query: str, limit: int) -> list[dict[str, Any]]:
    from core.services import semantic_memory

    out = []
    hits = semantic_memory.search(
        query, source_tables=["private_brain_records"], limit=limit * 2, min_score=0.35,
    )
    for h in hits:
        rec = h.get("record") or {}
        if str(rec.get("status") or "active") not in _ACTIVE_PRIVATE_BRAIN:
            continue
        text = str(rec.get("summary") or rec.get("detail") or "")
        if not text.strip():
            continue
        out.append({
            "source": "private_brain",
            "score": max(0.0, min(1.0, float(h.get("score") or 0.0))),
            "text": _clip(text),
            "ref": str(h.get("source_id") or ""),
        })
        if len(out) >= limit:
            break
    return out


def _source_sensory(query: str, limit: int) -> list[dict[str, Any]]:
    from core.services import semantic_memory

    out = []
    for h in semantic_memory.search(query, source_tables=["sensory_memories"], limit=limit, min_score=0.35):
        rec = h.get("record") or {}
        text = str(rec.get("content") or "")
        if not text.strip():
            continue
        out.append({
            "source": "sensory",
            "score": max(0.0, min(1.0, float(h.get("score") or 0.0))),
            "text": _clip(text),
            "ref": str(h.get("source_id") or ""),
        })
    return out


def _source_session_summary(query: str, limit: int) -> list[dict[str, Any]]:
    from core.runtime.db_fts import search_session_summaries

    out = []
    for r in search_session_summaries(query, limit=limit):
        out.append({
            "source": "session_summary",
            "score": max(0.0, min(1.0, float(r.get("score") or 0.0))),
            "text": _clip(f"[{str(r.get('created_at') or '')[:10]}] {r.get('summary') or ''}"),
            "ref": str(r.get("session_id") or ""),
        })
    return out


def _source_chat(query: str, limit: int) -> list[dict[str, Any]]:
    from core.runtime.db_fts import search_chat_messages

    out = []
    for r in search_chat_messages(query, limit=limit):
        out.append({
            "source": "chat",
            "score": max(0.0, min(1.0, float(r.get("score") or 0.0))),
            "text": _clip(f"[{str(r.get('created_at') or '')[:10]} {r.get('role')}] {r.get('content') or ''}"),
            "ref": str(r.get("message_id") or ""),
        })
    return out


def _source_chronicle(query: str, limit: int) -> list[dict[str, Any]]:
    from core.services.memory_recall_engine import _gather_chronicle

    out = []
    for r in _gather_chronicle(query, limit) or []:
        if r.get("error"):
            continue
        out.append({
            "source": "chronicle",
            "score": max(0.0, min(1.0, float(r.get("score") or 0.0))),
            "text": _clip(str(r.get("text") or "")),
            "ref": str(r.get("subsource") or "chronicle"),
        })
    return out


SOURCE_FUNCS: dict[str, Callable[[str, int], list[dict[str, Any]]]] = {
    "workspace": _source_workspace,
    "brain": _source_brain,
    "private_brain": _source_private_brain,
    "session_summary": _source_session_summary,
    "chronicle": _source_chronicle,
    "chat": _source_chat,
    "sensory": _source_sensory,
}


# ── fusion ──────────────────────────────────────────────────────────────


def fuse(query: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Re-score candidates: 0.6 × native + 0.4 × BM25 (over the candidate texts),
    dedupe by the first 80 normalized chars, sort descending."""
    if not candidates:
        return []
    bm25_norm: dict[int, float] = {}
    try:
        from core.services.multi_signal_retrieval import BM25Index

        idx = BM25Index(k1=1.2, b=0.5)
        idx.build([c["text"] for c in candidates])
        raw = {i: s for i, s in idx.search(query, top_k=0)}
        top = max(raw.values()) if raw else 0.0
        if top > 0:
            bm25_norm = {i: max(0.0, s) / top for i, s in raw.items()}
    except Exception as exc:
        logger.debug("recall.fuse: bm25 failed: %s", exc)

    fused: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, c in enumerate(candidates):
        key = _dedupe_key(c.get("text", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        native = float(c.get("score") or 0.0)
        bm = bm25_norm.get(i, 0.0)
        item = dict(c)
        item["native_score"] = round(native, 4)
        item["bm25"] = round(bm, 4)
        item["score"] = round(_NATIVE_WEIGHT * native + _BM25_WEIGHT * bm, 4)
        fused.append(item)
    fused.sort(key=lambda x: x["score"], reverse=True)
    return fused


# ── entry point ─────────────────────────────────────────────────────────


def empty_message(query: str) -> str:
    return f"Ingen hukommelse matchede: «{query}». Prøv færre eller andre ord."


def recall(
    query: str,
    *,
    limit: int = 8,
    sources: list[str] | tuple[str, ...] | None = None,
    session_id: str | None = None,
    min_score: float = 0.3,
    per_source: int | None = None,
) -> dict[str, Any]:
    """Search every memory source with one fused ranking.

    Returns ``{"status": "ok", "query", "count", "results": [...], "sources",
    "text"}``. On zero hits ``text`` explains it and ``memory.recall_empty``
    is emitted (best-effort).
    """
    q = " ".join(str(query or "").split()).strip()
    if not q:
        return {"status": "error", "error": "query is required", "results": [], "count": 0}
    limit = max(1, min(50, int(limit or 8)))
    wanted = [s for s in (sources or DEFAULT_SOURCES) if s in SOURCE_FUNCS]
    if not wanted:
        wanted = list(DEFAULT_SOURCES)
    k = per_source or max(3, limit)

    candidates: list[dict[str, Any]] = []
    errors: dict[str, str] = {}
    for name in wanted:
        try:
            candidates.extend(SOURCE_FUNCS[name](q, k))
        except Exception as exc:  # fail-soft per source
            errors[name] = str(exc)[:160]
            logger.debug("recall: source %s failed: %s", name, exc)

    fused = [c for c in fuse(q, candidates) if c["score"] >= float(min_score)]
    results = fused[:limit]

    if not results:
        try:
            from core.services.memory_recall_telemetry import emit_recall_empty
            emit_recall_empty(tool="recall", query=q)
        except Exception:
            pass
        return {
            "status": "ok", "query": q, "count": 0, "results": [],
            "sources": wanted, "errors": errors, "text": empty_message(q),
        }

    lines = [f"Hukommelse for «{q}» — {len(results)} hit(s):"]
    for r in results:
        lines.append(f"- [{r['source']} {r['score']:.2f}] {r['text']}")
    return {
        "status": "ok", "query": q, "count": len(results), "results": results,
        "sources": wanted, "errors": errors, "text": "\n".join(lines),
    }
