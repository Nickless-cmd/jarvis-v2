"""Semantic memory search — embeddings-based search over Jarvis's workspace memory files.

Uses nomic-embed-text via Ollama for embeddings, numpy for cosine similarity.
Index is cached to disk and invalidated when source files change (mtime check).
Falls back to TF-IDF (sklearn) if Ollama is unavailable.
"""
from __future__ import annotations

import json
import logging
import pickle
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple

import numpy as np

logger = logging.getLogger(__name__)

_INDEX_LOCK = threading.Lock()
_EMBED_MODEL = "nomic-embed-text"
_OLLAMA_BASE = "http://localhost:11434"


class Chunk(NamedTuple):
    text: str
    source: str       # relative filename
    section: str      # nearest heading above this chunk


def _workspace_dir() -> Path:
    from core.runtime.config import JARVIS_HOME
    return Path(JARVIS_HOME) / "workspaces" / "default"


def _memory_files() -> list[Path]:
    ws = _workspace_dir()
    files: list[Path] = []
    for name in ["MEMORY.md", "USER.md", "SOUL.md", "STANDING_ORDERS.md", "SKILLS.md"]:
        p = ws / name
        if p.exists():
            files.append(p)
    for subdir in ["memory/curated", "memory/daily"]:
        d = ws / subdir
        if d.is_dir():
            for f in sorted(d.glob("*.md"))[-30:]:  # last 30 files
                files.append(f)
    return files


def _file_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _chunk_markdown(text: str, source: str) -> list[Chunk]:
    """Split markdown into chunks, tracking the nearest heading."""
    chunks: list[Chunk] = []
    current_heading = ""
    current_lines: list[str] = []

    def flush():
        nonlocal current_lines
        joined = " ".join(l.strip() for l in current_lines if l.strip())
        if len(joined) >= 20:
            chunks.append(Chunk(text=joined[:800], source=source, section=current_heading))
        current_lines = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            flush()
            current_heading = stripped.lstrip("#").strip()
        elif stripped == "" and current_lines:
            flush()
        else:
            current_lines.append(stripped)
    flush()
    return chunks


def _embed_ollama(texts: list[str]) -> np.ndarray | None:
    """Embed a list of texts via Ollama. Returns (N, D) array or None on failure."""
    try:
        import httpx
        embeddings = []
        for text in texts:
            resp = httpx.post(
                f"{_OLLAMA_BASE}/api/embeddings",
                json={"model": _EMBED_MODEL, "prompt": text},
                timeout=20,
            )
            if resp.status_code != 200:
                return None
            emb = resp.json().get("embedding")
            if not emb:
                return None
            embeddings.append(emb)
        return np.array(embeddings, dtype=np.float32)
    except Exception as exc:
        logger.warning("memory_search: Ollama embed failed: %s", exc)
        return None


def _embed_single(text: str) -> np.ndarray | None:
    result = _embed_ollama([text])
    return result[0] if result is not None else None


def _cosine_sim(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Cosine similarity between query (D,) and matrix (N, D)."""
    q = query_vec / (np.linalg.norm(query_vec) + 1e-10)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10
    normed = matrix / norms
    return normed @ q


def _tfidf_search(query: str, chunks: list[Chunk], limit: int) -> list[dict]:
    """Fallback TF-IDF search when Ollama is unavailable."""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity as sk_cosine
        texts = [c.text for c in chunks]
        vec = TfidfVectorizer(ngram_range=(1, 2), max_features=10000)
        matrix = vec.fit_transform(texts)
        q_vec = vec.transform([query])
        scores = sk_cosine(q_vec, matrix)[0]
        top_idx = np.argsort(scores)[::-1][:limit]
        return [
            {
                "text": chunks[i].text,
                "source": chunks[i].source,
                "section": chunks[i].section,
                "score": float(scores[i]),
                "method": "tfidf",
            }
            for i in top_idx
            if scores[i] > 0.01
        ]
    except Exception as exc:
        logger.error("memory_search: tfidf failed: %s", exc)
        return []


# Index structure stored on disk
_INDEX_CACHE_PATH_NAME = "runtime/memory_search_index.pkl"


def _cache_path() -> Path:
    return _workspace_dir() / _INDEX_CACHE_PATH_NAME


def _load_or_build_index() -> tuple[list[Chunk], np.ndarray | None, dict[str, float]]:
    """Load cached index or rebuild from scratch. Returns (chunks, embeddings, mtimes)."""
    files = _memory_files()
    current_mtimes = {str(f): _file_mtime(f) for f in files}
    cache = _cache_path()

    # Try to load cached index
    if cache.exists():
        try:
            with open(cache, "rb") as fh:
                cached = pickle.load(fh)
            if cached.get("mtimes") == current_mtimes and cached.get("model") == _EMBED_MODEL:
                return cached["chunks"], cached.get("embeddings"), current_mtimes
        except Exception as exc:
            logger.warning("memory_search: cache load failed: %s", exc)

    # Build fresh index
    logger.info("memory_search: building index from %d files", len(files))
    all_chunks: list[Chunk] = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
            ws = _workspace_dir()
            try:
                rel = str(f.relative_to(ws))
            except ValueError:
                rel = f.name
            all_chunks.extend(_chunk_markdown(text, rel))
        except Exception as exc:
            logger.warning("memory_search: failed to read %s: %s", f, exc)

    if not all_chunks:
        return [], None, current_mtimes

    # Embed all chunks
    texts = [c.text for c in all_chunks]
    embeddings = _embed_ollama(texts)

    # Save to cache
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        with open(cache, "wb") as fh:
            pickle.dump({
                "chunks": all_chunks,
                "embeddings": embeddings,
                "mtimes": current_mtimes,
                "model": _EMBED_MODEL,
                "built_at": datetime.now(UTC).isoformat(),
            }, fh)
        logger.info("memory_search: index built (%d chunks, embeddings=%s)", len(all_chunks), embeddings is not None)
    except Exception as exc:
        logger.warning("memory_search: cache save failed: %s", exc)

    return all_chunks, embeddings, current_mtimes


def search_memory(query: str, *, limit: int = 5) -> list[dict]:
    """Search workspace memory files by semantic similarity.

    Returns a list of matching chunks with source, section, and score.
    """
    query = query.strip()
    if not query:
        return []

    with _INDEX_LOCK:
        chunks, embeddings, _ = _load_or_build_index()

    if not chunks:
        return []

    if embeddings is not None:
        # Semantic search
        q_emb = _embed_single(query)
        if q_emb is not None:
            scores = _cosine_sim(q_emb, embeddings)
            top_idx = np.argsort(scores)[::-1][:limit]
            return [
                {
                    "text": chunks[i].text,
                    "source": chunks[i].source,
                    "section": chunks[i].section,
                    "score": float(scores[i]),
                    "method": "embedding",
                }
                for i in top_idx
                if scores[i] > 0.1
            ]

    # Fallback
    return _tfidf_search(query, chunks, limit)


def invalidate_index() -> None:
    """Force index rebuild on next search (call after memory file writes)."""
    try:
        _cache_path().unlink(missing_ok=True)
        logger.info("memory_search: index invalidated")
    except Exception as exc:
        logger.warning("memory_search: invalidate failed: %s", exc)


def get_index_stats() -> dict:
    """Return stats about the current index (without rebuilding)."""
    cache = _cache_path()
    if not cache.exists():
        return {"status": "not_built", "chunk_count": 0}
    try:
        with open(cache, "rb") as fh:
            cached = pickle.load(fh)
        chunks = cached.get("chunks") or []
        has_embeddings = cached.get("embeddings") is not None
        return {
            "status": "ready",
            "chunk_count": len(chunks),
            "has_embeddings": has_embeddings,
            "model": cached.get("model", ""),
            "built_at": cached.get("built_at", ""),
            "file_count": len(cached.get("mtimes") or {}),
        }
    except Exception:
        return {"status": "corrupt", "chunk_count": 0}
