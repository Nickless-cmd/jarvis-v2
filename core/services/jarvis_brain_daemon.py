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
