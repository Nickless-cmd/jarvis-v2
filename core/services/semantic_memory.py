"""Semantic memory — unified embedding + cosine search across memory surfaces.

Covers:
- sensory_memories (visual, audio, atmosphere, mixed)
- private_brain_records (inner-voice, chronicle, reflections, dreams, etc.)

Extensible: new surfaces just register a resolver that maps source_id back
to the content row. All rows are embedded via Ollama nomic-embed-text
(resolved through provider_router) and stored in memory_embeddings.

Public entry points:
- index_memory(source_table, source_id, content, modality) — embed + store
- search(query, modalities=None, source_tables=None, limit=20) — top-k
- backfill_all() — embed anything not yet indexed
- get_stats() — overview for MC
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any, Callable

import numpy as np

from core.runtime.db_embeddings import (
    count_embeddings,
    get_embedding,
    list_embeddings,
    list_indexed_source_ids,
    upsert_embedding,
)

logger = logging.getLogger(__name__)

_EMBED_MODEL = "nomic-embed-text"
_MODEL_VERSION = f"ollama/{_EMBED_MODEL}/v1"
_MAX_CONTENT_CHARS = 4000  # clip anything longer to keep embeddings stable


# ---------------------------------------------------------------------------
# Resolvers — how we fetch full records back after a vector hit
# ---------------------------------------------------------------------------

_RESOLVERS: dict[str, Callable[[str], dict[str, Any] | None]] = {}
_LISTERS: dict[str, Callable[[], list[dict[str, Any]]]] = {}


def register_source(
    table: str,
    *,
    resolver: Callable[[str], dict[str, Any] | None],
    lister: Callable[[], list[dict[str, Any]]],
) -> None:
    """Register a source table so backfill + search can map IDs to rows."""
    _RESOLVERS[table] = resolver
    _LISTERS[table] = lister


def _default_sources_registered() -> None:
    """Register sensory_memories + private_brain_records if not already."""
    if "sensory_memories" not in _RESOLVERS:
        from core.runtime.db_sensory import (
            get_sensory_memory,
            list_sensory_memories,
        )

        register_source(
            "sensory_memories",
            resolver=lambda sid: get_sensory_memory(sid),
            lister=lambda: list_sensory_memories(limit=10000),
        )

    if "private_brain_records" not in _RESOLVERS:
        from core.runtime.db import (
            get_private_brain_record,
            list_private_brain_records,
        )

        register_source(
            "private_brain_records",
            resolver=lambda sid: get_private_brain_record(sid),
            lister=lambda: list_private_brain_records(limit=5000),
        )


# ---------------------------------------------------------------------------
# Ollama access
# ---------------------------------------------------------------------------

def _ollama_base_url() -> str:
    try:
        from core.runtime.provider_router import load_provider_router_registry
        registry = load_provider_router_registry()
        for p in registry.get("providers", []):
            if str(p.get("provider", "")).lower() == "ollama" and p.get("enabled"):
                url = str(p.get("base_url") or "").strip()
                if url:
                    return url.rstrip("/")
    except Exception:
        pass
    return "http://127.0.0.1:11434"


def _embed_ollama(text: str) -> np.ndarray | None:
    try:
        import httpx
        resp = httpx.post(
            f"{_ollama_base_url()}/api/embeddings",
            json={"model": _EMBED_MODEL, "prompt": text},
            timeout=30,
        )
        if resp.status_code != 200:
            logger.debug("semantic_memory: embed HTTP %s", resp.status_code)
            return None
        emb = resp.json().get("embedding")
        if not emb:
            return None
        return np.array(emb, dtype=np.float32)
    except Exception as exc:
        logger.debug("semantic_memory: embed failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Encoding helpers
# ---------------------------------------------------------------------------

def _encode_vector(vec: np.ndarray) -> bytes:
    return vec.astype(np.float32).tobytes()


def _decode_vector(data: bytes) -> np.ndarray:
    return np.frombuffer(data, dtype=np.float32)


def _hash_content(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:32]


def _prepare_text(text: str) -> str:
    cleaned = str(text or "").strip()
    return cleaned[:_MAX_CONTENT_CHARS]


# ---------------------------------------------------------------------------
# Public: index + search
# ---------------------------------------------------------------------------

def index_memory(
    *,
    source_table: str,
    source_id: str,
    content: str,
    modality: str,
) -> bool:
    """Embed content and upsert. Returns True on success, False if embed fails
    or content is empty. Skips re-embedding when content_hash is unchanged.
    """
    text = _prepare_text(content)
    if not text:
        return False
    content_hash = _hash_content(text)

    existing = get_embedding(source_table, source_id)
    if existing and existing.get("content_hash") == content_hash \
            and existing.get("model_version") == _MODEL_VERSION:
        return True

    vec = _embed_ollama(text)
    if vec is None:
        return False

    upsert_embedding(
        source_table=source_table,
        source_id=source_id,
        modality=modality,
        content_hash=content_hash,
        embedding_bytes=_encode_vector(vec),
        model_version=_MODEL_VERSION,
    )
    return True


def search(
    query: str,
    *,
    modalities: list[str] | None = None,
    source_tables: list[str] | None = None,
    limit: int = 20,
    min_score: float = 0.35,
) -> list[dict[str, Any]]:
    """Return top-k memories by cosine similarity.

    Each hit includes: score, source_table, source_id, modality, indexed_at,
    plus 'record' containing the resolved source row (content, timestamp,
    summary, etc.) when a resolver is available.
    """
    q = str(query or "").strip()
    if not q:
        return []

    _default_sources_registered()

    rows = list_embeddings(
        modalities=modalities,
        source_tables=source_tables,
    )
    if not rows:
        return []

    q_vec = _embed_ollama(q)
    if q_vec is None:
        return []

    matrix = np.stack([_decode_vector(r["embedding"]) for r in rows])
    q_norm = q_vec / (np.linalg.norm(q_vec) + 1e-10)
    mat_norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10
    scores = (matrix / mat_norms) @ q_norm

    order = np.argsort(scores)[::-1][: max(1, limit)]
    out: list[dict[str, Any]] = []
    for idx in order:
        score = float(scores[idx])
        if score < min_score:
            continue
        row = rows[idx]
        source_table = str(row["source_table"])
        source_id = str(row["source_id"])
        resolver = _RESOLVERS.get(source_table)
        record = resolver(source_id) if resolver else None
        out.append(
            {
                "score": round(score, 4),
                "source_table": source_table,
                "source_id": source_id,
                "modality": row.get("modality"),
                "indexed_at": row.get("indexed_at"),
                "record": record,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Backfill + stats
# ---------------------------------------------------------------------------

def _extract_content_for_row(table: str, row: dict[str, Any]) -> tuple[str, str]:
    """Return (content_text, modality) for a raw row from a known table."""
    if table == "sensory_memories":
        return str(row.get("content") or ""), str(row.get("modality") or "mixed")
    if table == "private_brain_records":
        summary = str(row.get("summary") or "").strip()
        detail = str(row.get("detail") or "").strip()
        text = summary
        if detail and detail != summary:
            text = f"{summary}\n{detail}" if summary else detail
        modality = str(row.get("record_type") or row.get("layer") or "inner")
        return text, modality
    return "", "unknown"


def _row_id(table: str, row: dict[str, Any]) -> str:
    if table == "sensory_memories":
        return str(row.get("id") or "")
    if table == "private_brain_records":
        return str(row.get("record_id") or row.get("id") or "")
    return str(row.get("id") or row.get("record_id") or "")


def backfill_all(*, max_per_table: int | None = None) -> dict[str, Any]:
    """Embed every unindexed row across registered source tables.

    Safe to run repeatedly — skips rows whose content_hash matches an
    existing embedding.
    """
    _default_sources_registered()
    summary: dict[str, Any] = {"tables": {}, "total_indexed": 0, "total_failed": 0}
    for table, lister in _LISTERS.items():
        try:
            rows = lister()
        except Exception as exc:
            logger.warning("semantic_memory: lister %s failed: %s", table, exc)
            summary["tables"][table] = {"error": str(exc)}
            continue
        if max_per_table is not None:
            rows = rows[: int(max_per_table)]
        indexed = 0
        failed = 0
        skipped = 0
        already = list_indexed_source_ids(table)
        for row in rows:
            sid = _row_id(table, row)
            if not sid:
                continue
            content, modality = _extract_content_for_row(table, row)
            if not content.strip():
                skipped += 1
                continue
            if sid in already and _content_hash_unchanged(table, sid, content):
                skipped += 1
                continue
            ok = index_memory(
                source_table=table,
                source_id=sid,
                content=content,
                modality=modality,
            )
            if ok:
                indexed += 1
            else:
                failed += 1
        summary["tables"][table] = {
            "indexed": indexed,
            "failed": failed,
            "skipped": skipped,
            "total_rows": len(rows),
        }
        summary["total_indexed"] += indexed
        summary["total_failed"] += failed
    return summary


def _content_hash_unchanged(
    table: str, source_id: str, new_content: str
) -> bool:
    existing = get_embedding(table, source_id)
    if not existing:
        return False
    return existing.get("content_hash") == _hash_content(_prepare_text(new_content))


def get_stats() -> dict[str, Any]:
    _default_sources_registered()
    total = count_embeddings()
    by_table = {}
    for table in _LISTERS.keys():
        by_table[table] = count_embeddings(source_table=table)
    return {
        "total_embeddings": total,
        "by_source_table": by_table,
        "model_version": _MODEL_VERSION,
    }
