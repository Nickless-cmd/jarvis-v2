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


def read_topic(slug: str, *, name: str = "default") -> str | None:
    """Læs en kurateret topic-krop for den aktuelle bruger. None hvis ugyldigt/mangler."""
    path = curated_path_for(slug, name=name)
    if path is None or not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.debug("memory_topic_store: read failed: %s", exc)
        return None


def write_topic_confirmed(slug: str, *, title: str, hook: str, body: str,
                          name: str = "default") -> dict[str, Any]:
    """Skriv en topic-krop og BEKRAEFT den (fil eksisterer + indhold matcher).
    Index-linjen tilfoejes KUN ved bekraeftet krops-skriv (Task 3 wirer det).
    Returnerer {'confirmed': bool, 'reason': str, 'slug': str}."""
    safe = sanitize_slug(slug)
    if not safe:
        return {"confirmed": False, "reason": "bad-slug", "slug": ""}
    path = curated_path_for(safe, name=name)
    if path is None:
        return {"confirmed": False, "reason": "bad-slug", "slug": safe}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(body or ""), encoding="utf-8")
        # BEKRAEFT: læs tilbage + sammenlign (strict write discipline).
        if not path.exists() or path.read_text(encoding="utf-8") != str(body or ""):
            return {"confirmed": False, "reason": "body-write-failed", "slug": safe}
    except Exception as exc:
        logger.debug("memory_topic_store: write failed: %s", exc)
        return {"confirmed": False, "reason": "body-write-failed", "slug": safe}
    ok = upsert_index_line(title=title, slug=safe, hook=hook, name=name)
    if not ok:
        # Krop skrevet, men index fejlede → topic er en orphan (ikke en loegn i
        # index'et). Rapportér ærligt; Jarvis maa ikke sige "gemt".
        return {"confirmed": False, "reason": "index-update-failed", "slug": safe}
    return {"confirmed": True, "reason": "ok", "slug": safe}


def _index_line(title: str, slug: str, hook: str) -> str:
    t = str(title or slug).strip()
    h = str(hook or "").strip()
    return f"- [{t}](curated/{slug}.md) — {h}" if h else f"- [{t}](curated/{slug}.md)"


def upsert_index_line(*, title: str, slug: str, hook: str, name: str = "default") -> bool:
    """Tilfoej/opdatér én index-linje i <user>/MEMORY.md. Idempotent pr. slug.
    Bekraefter ved at gen-læse. True hvis linjen er til stede efter skriv."""
    safe = sanitize_slug(slug)
    if not safe:
        return False
    try:
        idx_path = Path(workspace_memory_paths(name=name)["curated_memory"])
        idx_path.parent.mkdir(parents=True, exist_ok=True)
        existing = idx_path.read_text(encoding="utf-8") if idx_path.exists() else ""
        marker = f"(curated/{safe}.md)"
        new_line = _index_line(title, safe, hook)
        lines = existing.splitlines()
        replaced = False
        for i, ln in enumerate(lines):
            if marker in ln:
                lines[i] = new_line
                replaced = True
                break
        if not replaced:
            lines.append(new_line)
        idx_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return marker in idx_path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.debug("memory_topic_store: index upsert failed: %s", exc)
        return False
