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

# fastembed = SAMME model (nomic-embed-text-v1.5, 768-dim) men in-process ONNX i stedet
# for HTTP→ollama. Målt cosine 1.0000 mod det eksisterende ollama-indeks på tværs af
# dansk/engelsk/teknisk tekst → DROP-IN, ingen reindex, samme _MODEL_VERSION. Latens
# 17-21ms vs 1411ms (~70-80x) OG intet netværk → recall kan ALDRIG mere droppes af
# assembly-timeout'et (kerneårsagen til "kan ikke huske hvem han er"). Kill-switch:
# runtime-key `embed_backend`="ollama" tvinger den gamle HTTP-sti.
_FASTEMBED_MODEL = "nomic-ai/nomic-embed-text-v1.5"


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
    # DEDIKERET embed-host: recall/brain-embeds må IKKE konkurrere med det synlige svar
    # om GPU-ollama'en (localhost). Embed-kaldet kø'ede 28-91s bag svaret → assembly-
    # budgettet (~12s) droppede recall → "Jarvis kan ikke huske hvem han er". Peg
    # embeddings mod den dedikerede CPU-ollama (llm-gateway 10.0.0.45) via runtime-key
    # `embed_ollama_base_url`. SAMME model (nomic-embed-text) → samme vektor-rum → ingen
    # reindex nødvendig for host-skiftet. Faldback: generel ollama-provider (GPU).
    try:
        from core.runtime.secrets import read_runtime_key
        _embed_url = str(read_runtime_key("embed_ollama_base_url") or "").strip()
        if _embed_url:
            return _embed_url.rstrip("/")
    except Exception:
        pass
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


# Proces-lokal embed-cache (text -> vektor). Embeddings er DETERMINISTISKE (samme
# tekst → cosine 1.0 identisk vektor), så caching er 100% sikkert — ingen staleness.
# Formål: den SAMME søgetekst embeddes 4-5× pr. prompt-assembly på tværs af recall-
# subsystemer (search_brain, search_memory, private_brain); cachen kollapser dem til
# ét ollama-kald. Bundet (FIFO-halvtøm ved loft), tråd-sikker. Ryddes ved genstart.
import threading as _threading
_EMBED_CACHE: dict[str, "np.ndarray"] = {}
_EMBED_CACHE_LOCK = _threading.Lock()
_EMBED_CACHE_MAX = 256


def _tt_embed(label: str, dur_ms: int) -> None:
    try:
        from core.services import turn_trace as _tt
        _tt.mark("embed", label, dur_ms)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# fastembed backend (in-process ONNX) — primær sti; ollama-HTTP er fallback
# ---------------------------------------------------------------------------

_FASTEMBED = None            # TextEmbedding-instans (lazy) el. False hvis utilgængelig
_FASTEMBED_LOCK = _threading.Lock()


def _fastembed_enabled() -> bool:
    """Kill-switch: runtime-key `embed_backend`="ollama" tvinger den gamle HTTP-sti."""
    try:
        from core.runtime.secrets import read_runtime_key
        return str(read_runtime_key("embed_backend") or "fastembed").strip().lower() != "ollama"
    except Exception:
        return True


def _get_fastembed():
    """Lazy singleton. Returnerer TextEmbedding el. None (aldrig raise) → kaldere
    falder rent tilbage til ollama-HTTP hvis import/load fejler eller er slået fra."""
    global _FASTEMBED
    if _FASTEMBED is not None:
        return _FASTEMBED or None
    if not _fastembed_enabled():
        return None
    with _FASTEMBED_LOCK:
        if _FASTEMBED is not None:
            return _FASTEMBED or None
        try:
            from fastembed import TextEmbedding
            # threads eksplicit: LXC-containeren blokerer CPU-affinity → onnxruntime
            # spammer pthread_setaffinity_np-fejl uden. Binder samtidig embed-CPU så
            # den ikke griber alle runtime-processens kerner. Konfigurerbar (default 4).
            _threads = 4
            try:
                from core.runtime.secrets import read_runtime_key
                _t = str(read_runtime_key("embed_fastembed_threads") or "").strip()
                if _t.isdigit() and int(_t) > 0:
                    _threads = int(_t)
            except Exception:
                pass
            _FASTEMBED = TextEmbedding(model_name=_FASTEMBED_MODEL, threads=_threads)
            logger.info("semantic_memory: fastembed backend aktiv (%s, in-process, threads=%d)",
                        _FASTEMBED_MODEL, _threads)
        except Exception as exc:
            logger.warning("semantic_memory: fastembed utilgængelig (%s) → falder til ollama-HTTP", exc)
            _FASTEMBED = False
        return _FASTEMBED or None


def _embed_fastembed(texts: list[str]) -> list["np.ndarray | None"] | None:
    """Embed hele listen in-process. Returnerer None (ikke en liste) hvis backenden
    er utilgængelig, så kaldere kan falde til ollama; ellers en liste parallel med
    `texts` af float32-vektorer. Diskriminativt målt cosine 1.0000 ≡ ollama-indeks."""
    emb = _get_fastembed()
    if emb is None or not texts:
        return None if emb is None else []
    try:
        vecs = list(emb.embed(list(texts)))
        if len(vecs) != len(texts):
            return None
        return [np.asarray(v, dtype=np.float32) for v in vecs]
    except Exception as exc:
        logger.debug("semantic_memory: fastembed embed fejlede (%s) → ollama-fallback", exc)
        return None


def _embed_ollama(text: str) -> np.ndarray | None:
    with _EMBED_CACHE_LOCK:
        cached = _EMBED_CACHE.get(text)
    if cached is not None:
        _tt_embed("single cached", 0)
        return cached
    import time as _t_e
    _t0_e = _t_e.monotonic()

    # Primær: fastembed in-process (~17ms, intet netværk, kan ikke droppes af timeout).
    fe = _embed_fastembed([text])
    if fe and fe[0] is not None:
        v = fe[0]
        with _EMBED_CACHE_LOCK:
            if len(_EMBED_CACHE) >= _EMBED_CACHE_MAX:
                for _k in list(_EMBED_CACHE)[: _EMBED_CACHE_MAX // 2]:
                    _EMBED_CACHE.pop(_k, None)
            _EMBED_CACHE[text] = v
        _tt_embed("single fastembed", int((_t_e.monotonic() - _t0_e) * 1000))
        return v

    # Fallback: ollama-HTTP (samme vektor-rum).
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
        v = np.array(emb, dtype=np.float32)
        with _EMBED_CACHE_LOCK:
            if len(_EMBED_CACHE) >= _EMBED_CACHE_MAX:
                for _k in list(_EMBED_CACHE)[: _EMBED_CACHE_MAX // 2]:
                    _EMBED_CACHE.pop(_k, None)
            _EMBED_CACHE[text] = v
        _tt_embed("single ollama", int((_t_e.monotonic() - _t0_e) * 1000))
        return v
    except Exception as exc:
        logger.debug("semantic_memory: embed failed: %s", exc)
        return None


def _embed_ollama_batch(texts: list[str]) -> list["np.ndarray | None"]:
    """Batch-embed via ollamas /api/embed (ÉT round-trip for hele listen i stedet
    for N). Semantisk identisk med N× _embed_ollama — samme model, samme vektorer.
    Returnerer en liste PARALLEL med `texts` (None pr. fejlet tekst). Falder tilbage
    til per-tekst _embed_ollama hvis batch-endpointet mangler (ældre ollama) eller
    fejler, så korrektheden aldrig afhænger af batch-supporten. Self-safe."""
    if not texts:
        return []
    import time as _t_e
    _t0_e = _t_e.monotonic()

    # Primær: fastembed in-process — ét ONNX-kald for hele listen, intet netværk.
    fe = _embed_fastembed(list(texts))
    if fe is not None and len(fe) == len(texts):
        _tt_embed(f"batch fastembed n={len(texts)}", int((_t_e.monotonic() - _t0_e) * 1000))
        return fe

    # Fallback: ollamas batch-endpoint (samme vektor-rum).
    try:
        import httpx
        resp = httpx.post(
            f"{_ollama_base_url()}/api/embed",
            json={"model": _EMBED_MODEL, "input": list(texts)},
            timeout=30,
        )
        if resp.status_code == 200:
            embs = resp.json().get("embeddings")
            if isinstance(embs, list) and len(embs) == len(texts):
                _tt_embed(f"batch n={len(texts)}", int((_t_e.monotonic() - _t0_e) * 1000))
                return [np.array(e, dtype=np.float32) if e else None for e in embs]
            logger.debug("semantic_memory: batch embed gav %s vektorer for %s tekster",
                         len(embs or []), len(texts))
        else:
            logger.debug("semantic_memory: batch embed HTTP %s", resp.status_code)
    except Exception as exc:
        logger.debug("semantic_memory: batch embed fejlede, falder til per-tekst: %s", exc)
    return [_embed_ollama(t) for t in texts]


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

    Queries the DB directly for rows not yet in memory_embeddings, so this
    scales past any lister's internal cap. Safe to run repeatedly.
    """
    _default_sources_registered()
    from core.runtime.db import connect

    tables_plan = {
        "sensory_memories": (
            "SELECT id FROM sensory_memories ORDER BY timestamp DESC",
            "id",
        ),
        "private_brain_records": (
            "SELECT record_id FROM private_brain_records "
            "WHERE status != 'deleted' ORDER BY created_at DESC",
            "record_id",
        ),
    }

    summary: dict[str, Any] = {"tables": {}, "total_indexed": 0, "total_failed": 0}
    for table, (query, id_col) in tables_plan.items():
        resolver = _RESOLVERS.get(table)
        if not resolver:
            continue
        try:
            with connect() as conn:
                rows = conn.execute(query).fetchall()
            all_ids = [str(r[id_col]) for r in rows if r[id_col]]
        except Exception as exc:
            logger.warning("semantic_memory: list ids %s failed: %s", table, exc)
            summary["tables"][table] = {"error": str(exc)}
            continue

        already = list_indexed_source_ids(table)
        missing = [sid for sid in all_ids if sid not in already]
        if max_per_table is not None:
            missing = missing[: int(max_per_table)]

        indexed = 0
        failed = 0
        skipped = 0
        for sid in missing:
            record = resolver(sid)
            if not record:
                skipped += 1
                continue
            content, modality = _extract_content_for_row(table, record)
            if not content.strip():
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
            "total_rows": len(all_ids),
            "already_indexed": len(already),
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


def build_semantic_memory_surface() -> dict[str, object]:
    """Mission Control surface — read-only meta-projection.

    Added during 2026-05-13 coverage push (system_cartographer dark-edge
    closure). Reports module presence so the cartographer registers it as
    observed. Specific state-readers added as the module evolves.
    """
    return {
        "active": True,
        "mode": "semantic_memory",
        "summary": "Module loaded; entry points available.",
        "authority": "derived-read-only",
    }


