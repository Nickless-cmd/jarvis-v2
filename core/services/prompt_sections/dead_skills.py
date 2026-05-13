"""Dead-skill detector: installed skills never invoked.

Tool Invention Phase 1 made it easy to install new skills. Without
adoption tracking, dead weight accumulates: skills proposed in a moment,
approved, then never used.

This module checks each installed skill against recent skill_invoked
events. Skills with no invocation in the last 30 days surface as a
"prune candidate" awareness section.

Added 2026-05-13.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)

_INACTIVITY_DAYS = 30


def dead_skills_section() -> str:
    try:
        from core.services import skill_engine
        from core.runtime.db import connect
    except Exception as exc:
        logger.debug("dead_skills: import failed: %s", exc)
        return ""

    try:
        all_skills = skill_engine.list_skills()
    except Exception:
        return ""
    if not all_skills:
        return ""

    cutoff = (datetime.now(UTC) - timedelta(days=_INACTIVITY_DAYS)).isoformat()
    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT payload_json FROM events "
                "WHERE kind = 'cognitive_state.skill_invoked' "
                "AND created_at > ? LIMIT 500",
                (cutoff,),
            ).fetchall()
        invoked_names: set[str] = set()
        import json as _json
        for r in rows:
            try:
                p = _json.loads(r[0] or "{}")
                n = str(p.get("name") or "").strip()
                if n:
                    invoked_names.add(n)
            except Exception:
                continue
    except Exception as exc:
        logger.debug("dead_skills: query failed: %s", exc)
        return ""

    dead: list[dict] = []
    for s in all_skills:
        name = s.get("name", "")
        if not name or name in invoked_names:
            continue
        # Don't flag skills loaded today/recently
        loaded_at = str(s.get("loaded_at") or "")
        if loaded_at >= cutoff:
            continue
        dead.append(s)

    if not dead:
        return ""

    lines = [
        f"Skills uden invocation seneste {_INACTIVITY_DAYS} dage "
        f"({len(dead)} stk; viser 5):"
    ]
    for s in dead[:5]:
        desc = str(s.get("description") or "")[:80]
        lines.append(f"  {s['name']}: {desc}")
    lines.append("Mekanisme: delete_skill fjerner uden brug; ingen auto-deletion.")
    return "\n".join(lines)
