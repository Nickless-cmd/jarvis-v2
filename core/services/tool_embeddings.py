"""Tool description embedding cache.

Each tool gets one embedding (vector) of its name + description, computed
once via Ollama (configurable model) and persisted to sqlite. Used by
tool_router to find context-relevant tools.

Also provides `top_k_similar(query, k)` — embed the query, return the
k tool names most similar by cosine distance.
"""
from __future__ import annotations

import hashlib
import logging
import math
import os
import sqlite3
import struct
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_DB_PATH = Path(
    os.getenv("JARVIS_STATE_DIR") or (Path.home() / ".jarvis-v2" / "state")
) / "tool_embeddings.sqlite"


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(_DB_PATH))
    c.execute(
        "CREATE TABLE IF NOT EXISTS tool_embeddings ("
        "  name TEXT PRIMARY KEY, "
        "  description_hash TEXT, "
        "  embedding BLOB, "
        "  computed_at TEXT"
        ")"
    )
    return c


def _pack(vec: list[float]) -> bytes:
    return struct.pack(f"<{len(vec)}f", *vec)


def _unpack(blob: bytes) -> list[float]:
    n = len(blob) // 4
    return list(struct.unpack(f"<{n}f", blob))


def _hash_desc(desc: str) -> str:
    return hashlib.sha256(desc.encode("utf-8")).hexdigest()[:16]


def _compute_embedding(text: str) -> list[float]:
    """Call Ollama embedding endpoint. Override in tests."""
    from core.runtime.settings import RuntimeSettings
    s = RuntimeSettings()
    model = s.tool_router_embedding_model
    import requests
    base_url = os.getenv("OLLAMA_BASE_URL", "http://10.0.0.25:11434")
    r = requests.post(
        f"{base_url}/api/embeddings",
        json={"model": model, "prompt": text},
        timeout=15,
    )
    r.raise_for_status()
    return list(r.json().get("embedding") or [])


def get_embedding(name: str, description: str) -> list[float]:
    h = _hash_desc(description)
    with _connect() as c:
        row = c.execute(
            "SELECT description_hash, embedding FROM tool_embeddings WHERE name = ?",
            (name,),
        ).fetchone()
        if row and row[0] == h:
            return _unpack(row[1])
    vec = _compute_embedding(f"{name}: {description}")
    with _connect() as c:
        c.execute(
            "INSERT OR REPLACE INTO tool_embeddings(name, description_hash, embedding, computed_at) "
            "VALUES (?, ?, ?, ?)",
            (name, h, _pack(vec), time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())),
        )
        c.commit()
    return vec


def invalidate(name: str) -> None:
    with _connect() as c:
        c.execute("DELETE FROM tool_embeddings WHERE name = ?", (name,))
        c.commit()


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def top_k_similar(query: str, k: int = 30) -> list[tuple[str, float]]:
    """Return (tool_name, similarity) sorted desc by cosine similarity."""
    qv = _compute_embedding(query)
    out: list[tuple[str, float]] = []
    with _connect() as c:
        rows = c.execute("SELECT name, embedding FROM tool_embeddings").fetchall()
    for name, blob in rows:
        sim = _cosine(qv, _unpack(blob))
        out.append((name, sim))
    out.sort(key=lambda r: r[1], reverse=True)
    return out[:k]


def warmup_all() -> int:
    """Compute embeddings for every registered tool. Returns count computed."""
    from core.tools.simple_tools import get_tool_definitions
    defs = get_tool_definitions() or []
    n = 0
    for d in defs:
        fn = d.get("function") or d
        name = fn.get("name") or ""
        desc = str(fn.get("description") or "").strip()
        if not name:
            continue
        try:
            get_embedding(name, desc)
            n += 1
        except Exception as exc:
            logger.warning("tool_embeddings.warmup_all skipped %s: %s", name, exc)
    return n
