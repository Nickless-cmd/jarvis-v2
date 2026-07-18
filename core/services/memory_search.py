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

# In-memory cache of the unpickled index, per-workspace (keyed by .pkl path).
# Avoids re-unpickling the on-disk index (multi-MB) on every search_memory call.
# Guarded by _INDEX_LOCK (all reads/writes happen inside _load_or_build_index,
# which search_memory only calls while holding _INDEX_LOCK).
_MEM_INDEX: dict[str, dict] = {}


class Chunk(NamedTuple):
    text: str
    source: str       # relative filename
    section: str      # nearest heading above this chunk


def _workspace_dir() -> Path:
    from core.runtime.workspace_paths import workspace_dir as _ws_dir
    return _ws_dir()


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
    """Embed a list of texts via Ollama. Returns (N, D) array or None on failure.

    Batch-kald (/api/embed, ÉT round-trip for hele listen) i stedet for N serielle
    /api/embeddings-kald. Dette var den STØRSTE assembly-hotspot: recall-søgningen
    embeddede memory-korpusset 85-229× ét ad gangen (~1,8s på idle GPU, kø'er under
    load). Vektorerne er identiske med per-tekst (cosine 1.0, verificeret). Falder
    tilbage til per-tekst-loopet hvis batch-endpointet mangler (ældre ollama)."""
    if not texts:
        return None
    try:
        import httpx
        resp = httpx.post(
            f"{_OLLAMA_BASE}/api/embed",
            json={"model": _EMBED_MODEL, "input": list(texts)},
            timeout=30,
        )
        if resp.status_code == 200:
            embs = resp.json().get("embeddings")
            if isinstance(embs, list) and len(embs) == len(texts) and embs:
                return np.array(embs, dtype=np.float32)
        logger.debug("memory_search: batch embed uventet svar (%s) — falder til per-tekst",
                     resp.status_code)
    except Exception as exc:
        logger.debug("memory_search: batch embed fejlede — falder til per-tekst: %s", exc)
    # Fallback: per-tekst (bevarer korrekthed hvis batch-endpointet ikke virker).
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
    # Delegér til semantic_memory's CACHEDE embedder, så query-embeddet deles med
    # search_brain/private_brain (samme tekst embeddes ellers 4-5× pr. assembly).
    # Samme model/endpoint/output-form; falder tilbage til lokal impl ved fejl.
    try:
        from core.services.semantic_memory import _embed_ollama as _shared_embed
        return _shared_embed(text)
    except Exception:
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


_REBUILD_LOCK = threading.Lock()
_REBUILD_ACTIVE = False


def _chunk_all_files(files: list[Path]) -> list[Chunk]:
    """Læs + chunk alle memory-filer. HURTIGT — kun fil-I/O, INGEN embedding."""
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
    return all_chunks


def _build_and_cache_index(files: list[Path], current_mtimes: dict[str, float]) -> None:
    """Byg indeks fra bunden (chunk + embed ALLE chunks) og skriv cache. LANGSOM (embedding).
    Kaldes KUN fra baggrunds-tråden — aldrig i en bruger-søgnings request-path."""
    all_chunks = _chunk_all_files(files)
    if not all_chunks:
        return
    embeddings = _embed_ollama([c.text for c in all_chunks])
    try:
        cache = _cache_path()
        cache.parent.mkdir(parents=True, exist_ok=True)
        with open(cache, "wb") as fh:
            pickle.dump({
                "chunks": all_chunks, "embeddings": embeddings,
                "mtimes": current_mtimes, "model": _EMBED_MODEL,
                "built_at": datetime.now(UTC).isoformat(),
            }, fh)
        logger.info("memory_search: index rebuilt in bg (%d chunks, embeddings=%s)",
                    len(all_chunks), embeddings is not None)
    except Exception as exc:
        logger.warning("memory_search: cache save failed: %s", exc)


def _schedule_background_rebuild(files: list[Path], current_mtimes: dict[str, float]) -> None:
    """Kør en fuld re-embed i BAGGRUNDEN (fire-and-forget, kun én ad gangen). Så en bruger-søgning
    ALDRIG blokerer på et fuldt re-embed (Bjørn 9. jul: 'search_memory hænger' — hver memory-fil-
    ændring invaliderede HELE indekset → inline re-embed af alle chunks = minutter → run/stream-hang)."""
    global _REBUILD_ACTIVE
    with _REBUILD_LOCK:
        if _REBUILD_ACTIVE:
            return
        _REBUILD_ACTIVE = True

    # Propagér kalderens kontekst (bl.a. user_id) til baggrunds-tråden — ContextVars arves IKKE af
    # nye tråde, og _chunk_all_files → _workspace_dir() KRÆVER et user-context. Uden dette fejler
    # rebuild'en (kan ikke læse workspace-filer) og indekset genopbygges aldrig.
    import contextvars
    ctx = contextvars.copy_context()

    def _run() -> None:
        global _REBUILD_ACTIVE
        try:
            _build_and_cache_index(files, current_mtimes)
        except Exception as exc:
            logger.warning("memory_search: background rebuild failed: %s", exc)
        finally:
            with _REBUILD_LOCK:
                _REBUILD_ACTIVE = False

    threading.Thread(target=lambda: ctx.run(_run), name="memory-search-reindex", daemon=True).start()


def _load_or_build_index() -> tuple[list[Chunk], np.ndarray | None, dict[str, float]]:
    """Returnér (chunks, embeddings, mtimes). BLOKERER ALDRIG på et fuldt re-embed:
      - frisk cache → brug den (semantisk søgning).
      - FORÆLDET cache → server den STRAKS + genopbyg i baggrunden (let-forældet ≫ hængende).
      - ingen/brudt cache → chunk filerne hurtigt (ingen embed) → embeddings=None → tfidf-fallback,
        og embed i baggrunden.
    Kun-fil-mtime-ændring invaliderer ikke længere søgningen synkront (den var roden til hanget).

    2026-07-18: det unpicklede indeks holdes nu i memory (per-workspace, nøglet på .pkl-
    filens mtime). FØR: hvert search_memory-kald `pickle.load`'ede HELE indekset fra disk
    (Bjørns var 4,6 MB) under _INDEX_LOCK → samtidige ture serialiserede på ~2-3s unpickle
    pr. tur = den næststørste synlige svartid-post efter experience-embedderen. Nu unpickles
    kun når .pkl'en faktisk skifter (mtime); ellers genbruges den in-memory-kopi. Awareness-
    neutralt (identisk indhold/resultat)."""
    files = _memory_files()
    current_mtimes = {str(f): _file_mtime(f) for f in files}
    cache = _cache_path()
    if cache.exists():
        try:
            key = str(cache)
            pkl_mtime = _file_mtime(cache)
            mem = _MEM_INDEX.get(key)
            if mem is not None and mem.get("pkl_mtime") == pkl_mtime:
                cached = mem["data"]  # in-memory hit — ingen disk-unpickle
            else:
                with open(cache, "rb") as fh:
                    cached = pickle.load(fh)
                _MEM_INDEX[key] = {"pkl_mtime": pkl_mtime, "data": cached}
            if cached.get("mtimes") == current_mtimes and cached.get("model") == _EMBED_MODEL:
                return cached["chunks"], cached.get("embeddings"), current_mtimes
            # Forældet → server den gamle index straks, genopbyg async.
            _schedule_background_rebuild(files, current_mtimes)
            return cached.get("chunks", []), cached.get("embeddings"), cached.get("mtimes", current_mtimes)
        except Exception as exc:
            logger.warning("memory_search: cache load failed: %s", exc)
    # Ingen/brudt cache: chunk hurtigt (ingen embed) → tfidf-fallback nu; embed i baggrunden.
    all_chunks = _chunk_all_files(files)
    _schedule_background_rebuild(files, current_mtimes)
    return all_chunks, None, current_mtimes


def _is_quarantined(text: str) -> bool:
    """True if a chunk has been marked as retracted/false.

    2026-05-22 (Claude): added so search_memory cannot resurface
    chunks that contain known-false claims. Quarantine marker is the
    literal token "[QUARANTINED" anywhere in the chunk text. The
    marker is written by humans (or by Claude during review) after a
    hallucination has been identified and corrected — the entry stays
    in the file for audit trail, but ranking treats it as filtered.

    Examples that match:
      "[QUARANTINED 2026-05-22 — HALLUCINATION] ~~Assets domain ...~~"
      "[QUARANTINE NOTE 2026-05-22 (Claude)] ..."
    """
    if not text:
        return False
    return "[QUARANTINED" in text or "[QUARANTINE NOTE" in text


def search_memory(query: str, *, limit: int = 5) -> list[dict]:
    """Search workspace memory files by semantic similarity.

    Returns a list of matching chunks with source, section, and score.

    Quarantined chunks (containing "[QUARANTINED" or "[QUARANTINE NOTE"
    markers) are excluded — they remain in the source files for audit
    but cannot resurface as evidence in recall.
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
            # 2026-05-22 (Claude): apply CANDIDATE penalty BEFORE picking
            # top_idx so genuinely-curated entries surface above legacy
            # [CANDIDATE→...] entries that the bulk-rewrite preserved as
            # low-confidence hints. 0.3x penalty matches recall_engine.
            adjusted_scores = scores.copy()
            for i in range(len(chunks)):
                if "[CANDIDATE→" in chunks[i].text:
                    adjusted_scores[i] = adjusted_scores[i] * 0.3
            top_idx = np.argsort(adjusted_scores)[::-1][:limit * 3]
            results = []
            for i in top_idx:
                if adjusted_scores[i] <= 0.1:
                    continue
                if _is_quarantined(chunks[i].text):
                    continue
                results.append({
                    "text": chunks[i].text,
                    "source": chunks[i].source,
                    "section": chunks[i].section,
                    "score": float(adjusted_scores[i]),
                    "raw_score": float(scores[i]),
                    "candidate_penalty": "[CANDIDATE→" in chunks[i].text,
                    "method": "embedding",
                })
                if len(results) >= limit:
                    break
            return results

    # Fallback (also applies quarantine filter)
    raw = _tfidf_search(query, chunks, limit * 2)
    filtered = [r for r in raw if not _is_quarantined(r.get("text", ""))]
    return filtered[:limit]


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
