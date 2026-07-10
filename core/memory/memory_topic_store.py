"""Topic-memory store (spec 2026-07-10 Spec B).

Tre-lags kurateret memory pr. bruger-workspace: altid-loadet index (MEMORY.md) +
on-demand topic-filer (memory/curated/<slug>.md). Denne fil ejer slug-sanitering,
per-user path-scoping (sikkerheds-invariant), bekraeftet skrivning og index-upsert.
Al sti-resolution gaar gennem workspace_memory_paths — aldrig hardkodet default.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
import re
import logging

from core.identity.workspace_bootstrap import workspace_memory_paths

logger = logging.getLogger(__name__)

_SLUG_RE = re.compile(r"[^a-z0-9_-]+")


def sanitize_slug(raw: str) -> str | None:
    """Kun [a-z0-9_-]. Alt andet → '-'. Tom/kun-symboler → None."""
    s = _SLUG_RE.sub("-", str(raw or "").strip().lower()).strip("-")
    return s or None


def curated_path_for(slug: str, *, name: str = "default") -> Path | None:
    """Absolut sti til <user>/memory/curated/<slug>.md for den RESOLVEDE bruger.
    Returnerer None hvis slug er ugyldigt ELLER stien ville falde uden for
    curated_dir (sikkerheds-invariant — kan ikke escape / naa anden bruger)."""
    safe = sanitize_slug(slug)
    if not safe:
        return None
    try:
        paths = workspace_memory_paths(name=name)
        curated_dir = Path(paths["curated_dir"]).resolve()
        candidate = (curated_dir / f"{safe}.md").resolve()
        candidate.relative_to(curated_dir)  # kaster ValueError hvis udenfor
        return candidate
    except Exception as exc:
        logger.debug("memory_topic_store: path resolve failed: %s", exc)
        return None
