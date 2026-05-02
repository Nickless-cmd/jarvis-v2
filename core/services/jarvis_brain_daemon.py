"""Jarvis Brain background daemon — tre uafhængige loops.

Loops:
  - reindex_loop: scanner brain_dir hver 5. min, opdaterer index, embedder pending
  - consolidation_loop: dagligt, finder duplikater + modsigelser + temaer
  - summary_loop: regenererer always-on summary efter meningsfulde ændringer
  - auto_archive: dagligt, arkiverer entries med low salience >90 dage

Spec: docs/superpowers/specs/2026-05-02-jarvis-brain-design.md sektion 7.
"""
from __future__ import annotations
import logging
import threading

logger = logging.getLogger("jarvis_brain_daemon")

_REINDEX_INTERVAL_SECONDS = 300  # 5 min


# ---------------------------------------------------------------------------
# Reindex loop (Task 11)
# ---------------------------------------------------------------------------


def reindex_once() -> int:
    """Et enkelt reindex-pass. Returnerer antal file changes opdaget."""
    from core.services import jarvis_brain
    n = jarvis_brain.rebuild_index_from_files()
    embedded = jarvis_brain.embed_pending_entries()
    if n or embedded:
        logger.info("reindex_once: %s file changes, %s embeddings", n, embedded)
    return n


def reindex_loop(stop_event: threading.Event) -> None:
    """Long-running loop. Stops cleanly when stop_event is set."""
    while not stop_event.is_set():
        try:
            reindex_once()
        except Exception as exc:
            logger.warning("reindex_loop iteration failed: %s", exc)
        stop_event.wait(_REINDEX_INTERVAL_SECONDS)


# ---------------------------------------------------------------------------
# Consolidation Phase 1: duplicate detection (Task 12)
# ---------------------------------------------------------------------------


def find_duplicate_proposals(
    *, threshold: float = 0.92, kinds: list[str] | None = None,
) -> list[tuple[str, str, float]]:
    """Returnerer liste af (a_id, b_id, similarity) hvor sim ≥ threshold.

    Default: kun fakta og observation. Indsigt + reference er for
    individuelle til auto-dedup.
    Threshold 0.92 er bevidst streng — falske positiver er værre end
    missede dubletter.
    """
    import numpy as np
    from core.services import jarvis_brain

    kinds = kinds or ["fakta", "observation"]
    conn = jarvis_brain.connect_index()
    try:
        ph = ",".join("?" * len(kinds))
        rows = conn.execute(
            f"SELECT id, embedding, embedding_dim FROM brain_index "
            f"WHERE status='active' AND kind IN ({ph}) AND embedding IS NOT NULL",
            kinds,
        ).fetchall()
    finally:
        conn.close()

    entries: list[tuple[str, "np.ndarray"]] = []
    for eid, blob, dim in rows:
        v = np.frombuffer(blob, dtype=np.float32).reshape(dim)
        norm = float(np.linalg.norm(v)) or 1e-9
        entries.append((eid, v / norm))

    pairs: list[tuple[str, str, float]] = []
    for i, (a_id, a_v) in enumerate(entries):
        for b_id, b_v in entries[i + 1 :]:
            sim = float(np.dot(a_v, b_v))
            if sim >= threshold:
                pairs.append((a_id, b_id, sim))
    return pairs
