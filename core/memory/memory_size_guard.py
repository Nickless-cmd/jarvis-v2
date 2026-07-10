"""MEMORY.md størrelses-værn (spec C, 2026-07-10).

Blødt monitor — IKKE auto-prune (auto-beskæring af identitets-kernen er farlig).
Overvåger alle workspaces' MEMORY.md og gør det synligt i Centralen hvis en
overskrider cap'en. En owner-invokeret ``prune_memory_section`` kan flytte en
NAVNGIVEN ikke-identitets-sektion til en topic (aldrig identitet, aldrig auto).
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
import logging

logger = logging.getLogger(__name__)

_CAP_BYTES = 25 * 1024  # ~25KB soft cap (KAIROS/autoDream-reference)

# Identitets-sektioner der ALDRIG må prunes (samme kerne som migrationens KEEP).
_IDENTITY_MARKERS = (
    "jarvis memory", "who i am", "livingneuron — centralen er mig",
    "centralen — arkitektur", "model-valg", "hardware",
    "bjørns etiske fundament", "identitetsbeslutning", "decisions",
    "forgængerens obduktion",
)


def _is_identity(title: str) -> bool:
    t = str(title or "").strip().lower()
    return any(m in t for m in _IDENTITY_MARKERS)


def check_memory_sizes() -> list[dict[str, Any]]:
    """Alle workspaces hvis MEMORY.md > cap. Self-safe → [] ved fejl."""
    out: list[dict[str, Any]] = []
    try:
        from core.identity.workspace_bootstrap import WORKSPACES_DIR
        base = Path(WORKSPACES_DIR)
        if not base.exists():
            return []
        for d in sorted(base.iterdir()):
            if not d.is_dir():
                continue
            mem = d / "MEMORY.md"
            try:
                size = mem.stat().st_size if mem.exists() else 0
            except Exception:
                size = 0
            if size > _CAP_BYTES:
                out.append({"workspace": d.name, "bytes": size,
                            "over_by": size - _CAP_BYTES})
    except Exception as exc:
        logger.debug("memory_size_guard: scan failed: %s", exc)
    return out


def build_memory_size_surface() -> dict[str, Any]:
    """Central-CLI read-surface: jc raw /central/memory-size. Side-effect-fri."""
    over = check_memory_sizes()
    return {
        "active": bool(over),
        "mode": "memory-size-guard",
        "cap_bytes": _CAP_BYTES,
        "summary": {"over_cap_count": len(over)},
        "items": over,
    }


def prune_memory_section(name: str, section_title: str) -> dict[str, Any]:
    """Owner-invokeret: flyt EN navngiven ikke-identitets-sektion fra <name>/MEMORY.md
    til en topic (curated/<slug>.md) + index. Afviser identitets-sektioner. Reversibel
    (sektionen bevares i topic'en; MEMORY.md skrives kun ved succesfuld topic-skriv)."""
    from core.identity.workspace_bootstrap import workspace_memory_paths
    from core.memory.memory_topic_store import sanitize_slug, write_topic_confirmed
    import re

    if _is_identity(section_title):
        return {"pruned": False, "reason": "identity-section-protected"}
    try:
        mem = Path(workspace_memory_paths(name=name)["curated_memory"])
        if not mem.exists():
            return {"pruned": False, "reason": "no-memory-file"}
        text = mem.read_text(encoding="utf-8")
    except Exception as exc:
        logger.debug("memory_size_guard: read failed: %s", exc)
        return {"pruned": False, "reason": "read-error"}

    # Find sektionen (## Title … indtil næste header på samme/højere niveau).
    lines = text.splitlines()
    target = str(section_title or "").strip().lower()
    start = None
    level = 0
    for i, ln in enumerate(lines):
        m = re.match(r"^(#{1,3})\s+(.*)$", ln)
        if m and m.group(2).strip().lower() == target:
            start = i
            level = len(m.group(1))
            break
    if start is None:
        return {"pruned": False, "reason": "section-not-found"}
    end = len(lines)
    for j in range(start + 1, len(lines)):
        m = re.match(r"^(#{1,3})\s+", lines[j])
        if m and len(m.group(1)) <= level:
            end = j
            break

    title = lines[start].lstrip("#").strip()
    body_lines = lines[start + 1:end]
    slug = sanitize_slug(title) or "pruned-section"
    body = f"# {title}\n\n" + "\n".join(body_lines).strip() + "\n"
    hook = next((b.strip() for b in body_lines if b.strip()), "")[:80]
    out = write_topic_confirmed(slug, title=title, hook=hook, body=body, name=name)
    if not out.get("confirmed"):
        return {"pruned": False, "reason": f"topic-write-failed:{out.get('reason')}"}
    # Kun ved bekræftet topic-skriv: fjern sektionen fra MEMORY.md.
    remaining = lines[:start] + lines[end:]
    mem.write_text("\n".join(remaining).strip() + "\n", encoding="utf-8")
    return {"pruned": True, "slug": slug, "moved_lines": len(body_lines)}
