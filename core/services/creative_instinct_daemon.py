"""Creative Instinct — spontaneous idea-seeds written to INCUBATOR.md.

Jarvis' PLAN_WILD_IDEAS #9 (2026-04-20): low-cadence (every 2h) daemon
that combines recent chat topics, memory trends, dream hypotheses, and
mood to emit 1-2 "idea seeds" — half-baked proposals. They live in
workspace/INCUBATOR.md and in runtime state, and can mature or wither.

Each seed: spark, confidence, why_now, depends_on, status.
Status lifecycle: fresh → maturing → adopted | withered.

This service *seeds* ideas from runtime signals. It does NOT call the
LLM to write them — it uses structural signal recombination. Jarvis
himself can later refine or promote them via the INCUBATOR workflow.
"""
from __future__ import annotations

import json
import logging
import os
import random
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_STORAGE_REL = "workspaces/default/runtime/creative_instinct.json"
_INCUBATOR_REL = "workspaces/default/INCUBATOR.md"
_CADENCE_HOURS = 2
_MAX_ACTIVE_SEEDS = 12
_MAX_NEW_PER_TICK = 2
_WITHER_AFTER_DAYS = 14


def _storage_path() -> Path:
    base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(base) / _STORAGE_REL


def _incubator_path() -> Path:
    base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(base) / _INCUBATOR_REL


def _load() -> dict[str, Any]:
    path = _storage_path()
    if not path.exists():
        return {"seeds": [], "last_tick_at": None}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("seeds", [])
            data.setdefault("last_tick_at", None)
            return data
    except Exception as exc:
        logger.warning("creative_instinct: load failed: %s", exc)
    return {"seeds": [], "last_tick_at": None}


def _save(data: dict[str, Any]) -> None:
    path = _storage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as exc:
        logger.warning("creative_instinct: save failed: %s", exc)


def _hours_since(iso_str: str | None) -> float:
    if not iso_str:
        return 99999.0
    try:
        dt = datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
        return (datetime.now(UTC) - dt).total_seconds() / 3600
    except Exception:
        return 99999.0


# --- Input gathering ---

def _recent_chat_topics(limit: int = 5) -> list[str]:
    try:
        from core.runtime.db import recent_visible_runs
        runs = recent_visible_runs(limit=limit) or []
        topics: list[str] = []
        for r in runs:
            preview = str(r.get("text_preview") or "")[:120]
            if preview:
                topics.append(preview)
        return topics
    except Exception:
        return []


def _recent_dream_hypotheses() -> list[str]:
    try:
        from core.runtime.db import list_runtime_dream_hypothesis_signals
        dreams = list_runtime_dream_hypothesis_signals(limit=20) or []
        active = [d for d in dreams if str(d.get("status") or "") == "active"]
        return [str(d.get("title") or d.get("summary") or "")[:140] for d in active[:5]]
    except Exception:
        return []


def _recent_avoidances() -> list[str]:
    try:
        from core.services.avoidance_detector import detect_avoidances
        return [str(f.get("sample_title") or "")[:120] for f in detect_avoidances()[:2]]
    except Exception:
        return []


def _current_mood_label() -> str:
    try:
        from core.services.mood_oscillator import get_current_mood
        return str(get_current_mood())
    except Exception:
        return "neutral"


# --- Seed generation ---

def _compose_spark(source_phrases: list[str], mood: str) -> str | None:
    """Combine two source phrases into a spark."""
    if len(source_phrases) < 1:
        return None
    if len(source_phrases) == 1:
        return source_phrases[0]
    # Pick two random snippets
    a, b = random.sample(source_phrases, 2)
    # Keep things grounded — light rephrasing without LLM
    a_short = _short_phrase(a)
    b_short = _short_phrase(b)
    connector = random.choice([
        "hvad hvis vi koblede",
        "en bro mellem",
        "når",
        "et møde mellem",
        "hvad sker der hvis",
    ])
    return f"{connector} '{a_short}' og '{b_short}' ({mood}-stemning)"


def _short_phrase(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    # Extract the first ~6 meaningful words
    words = text.split(" ")[:8]
    return " ".join(words).rstrip(".,!?;:")


def _generate_seeds(*, max_new: int) -> list[dict[str, Any]]:
    chat = _recent_chat_topics()
    dreams = _recent_dream_hypotheses()
    avoid = _recent_avoidances()
    mood = _current_mood_label()

    pool: list[tuple[str, str]] = []
    pool.extend(("chat", p) for p in chat)
    pool.extend(("dream", p) for p in dreams)
    pool.extend(("avoidance", p) for p in avoid)

    if len(pool) < 2:
        return []

    seeds: list[dict[str, Any]] = []
    for _ in range(max_new):
        chosen = random.sample(pool, min(2, len(pool)))
        phrases = [p for _, p in chosen]
        sources = sorted({src for src, _ in chosen})
        spark = _compose_spark(phrases, mood)
        if not spark:
            continue
        seeds.append({
            "seed_id": f"seed-{uuid4().hex[:10]}",
            "spark": spark,
            "confidence": round(random.uniform(0.3, 0.65), 3),
            "why_now": f"dukket op fra {'+'.join(sources)} (mood={mood})",
            "depends_on": sources,
            "status": "fresh",
            "created_at": datetime.now(UTC).isoformat(),
            "touched_at": datetime.now(UTC).isoformat(),
        })
    return seeds


# --- Incubator file writing ---

def _write_incubator_md(seeds: list[dict[str, Any]]) -> bool:
    """Overwrite INCUBATOR.md with current active seed list."""
    path = _incubator_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = ["# INCUBATOR", "", "*Idé-kim fra creative_instinct daemon.*", ""]
        active = [s for s in seeds if s.get("status") in ("fresh", "maturing")]
        for seed in sorted(active, key=lambda x: x.get("created_at") or "", reverse=True):
            lines.append(f"## {seed.get('spark', '?')}")
            lines.append("")
            lines.append(f"- **id:** `{seed.get('seed_id')}`")
            lines.append(f"- **status:** {seed.get('status')}")
            lines.append(f"- **confidence:** {seed.get('confidence')}")
            lines.append(f"- **why_now:** {seed.get('why_now')}")
            deps = seed.get("depends_on") or []
            lines.append(f"- **depends_on:** {', '.join(deps) if deps else '—'}")
            lines.append(f"- **created:** {seed.get('created_at', '')[:16]}")
            lines.append("")
        if not active:
            lines.append("*(Ingen aktive idé-kim endnu.)*")
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")
        return True
    except Exception as exc:
        logger.warning("creative_instinct: INCUBATOR.md write failed: %s", exc)
        return False


# --- Lifecycle ---

def _age_seeds(seeds: list[dict[str, Any]]) -> bool:
    """Mature or wither seeds based on age. Returns True if any changed."""
    changed = False
    for seed in seeds:
        if seed.get("status") not in ("fresh", "maturing"):
            continue
        age_hours = _hours_since(seed.get("created_at"))
        if age_hours > _WITHER_AFTER_DAYS * 24:
            seed["status"] = "withered"
            seed["touched_at"] = datetime.now(UTC).isoformat()
            changed = True
        elif age_hours > 48 and seed.get("status") == "fresh":
            seed["status"] = "maturing"
            seed["touched_at"] = datetime.now(UTC).isoformat()
            changed = True
    return changed


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    data = _load()
    changed = False

    # Age existing seeds
    if _age_seeds(data["seeds"]):
        changed = True

    # Cadence gate — only generate new seeds every 2h
    last_tick = data.get("last_tick_at")
    hours_since = _hours_since(last_tick)
    if hours_since >= _CADENCE_HOURS:
        # Cap total active
        active_count = sum(1 for s in data["seeds"] if s.get("status") in ("fresh", "maturing"))
        capacity = max(0, _MAX_ACTIVE_SEEDS - active_count)
        if capacity > 0:
            new_seeds = _generate_seeds(max_new=min(_MAX_NEW_PER_TICK, capacity))
            if new_seeds:
                data["seeds"].extend(new_seeds)
                changed = True
        data["last_tick_at"] = datetime.now(UTC).isoformat()
        changed = True

    if changed:
        _save(data)
        _write_incubator_md(data["seeds"])

    active = [s for s in data["seeds"] if s.get("status") in ("fresh", "maturing")]
    return {"active_seeds": len(active), "total_seeds": len(data["seeds"])}


def list_seeds(*, status: str | None = None) -> list[dict[str, Any]]:
    seeds = _load()["seeds"]
    if status:
        seeds = [s for s in seeds if s.get("status") == status]
    return seeds


def mark_seed(seed_id: str, *, status: str) -> bool:
    valid = {"fresh", "maturing", "adopted", "withered"}
    if status not in valid:
        return False
    data = _load()
    for s in data["seeds"]:
        if s.get("seed_id") == seed_id:
            s["status"] = status
            s["touched_at"] = datetime.now(UTC).isoformat()
            _save(data)
            _write_incubator_md(data["seeds"])
            return True
    return False


def build_creative_instinct_surface() -> dict[str, Any]:
    data = _load()
    seeds = data["seeds"]
    active = [s for s in seeds if s.get("status") in ("fresh", "maturing")]
    adopted = [s for s in seeds if s.get("status") == "adopted"]
    withered = [s for s in seeds if s.get("status") == "withered"]
    urgency = 0.0
    if active:
        urgency = min(1.0, len(active) / _MAX_ACTIVE_SEEDS)
    return {
        "active": len(active) > 0,
        "active_seeds": len(active),
        "adopted_total": len(adopted),
        "withered_total": len(withered),
        "creative_urgency": round(urgency, 3),
        "last_tick_at": data.get("last_tick_at"),
        "recent_active": [
            {
                "seed_id": s["seed_id"],
                "spark": s["spark"],
                "status": s["status"],
                "confidence": s.get("confidence"),
                "created_at": s.get("created_at"),
            }
            for s in sorted(active, key=lambda x: x.get("created_at") or "", reverse=True)[:5]
        ],
        "summary": _surface_summary(active, adopted, withered),
    }


def _surface_summary(
    active: list[dict[str, Any]],
    adopted: list[dict[str, Any]],
    withered: list[dict[str, Any]],
) -> str:
    if not active and not adopted:
        return "Ingen idé-kim endnu"
    parts = []
    if active:
        parts.append(f"{len(active)} kimer")
    if adopted:
        parts.append(f"{len(adopted)} adopteret")
    if withered:
        parts.append(f"{len(withered)} visnet")
    return "Incubator: " + ", ".join(parts)


def build_creative_instinct_prompt_section() -> str | None:
    data = _load()
    fresh = [s for s in data["seeds"] if s.get("status") == "fresh"]
    if not fresh:
        return None
    # Only mention the newest one
    newest = max(fresh, key=lambda s: s.get("created_at") or "")
    age = _hours_since(newest.get("created_at"))
    if age > 24:
        return None
    return f"Nyt idé-kim: \"{newest['spark']}\" (confidence={newest.get('confidence')})."
