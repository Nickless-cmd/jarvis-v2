"""TikTok research daemon — daily content concept pool generator.

Generates 9 content concepts per day (3 per slot type: motivation, dark_humor, cosmic)
and writes them to /home/bs/ai/tiktok_content_pool.json.

Fires once daily (cadence: 1440 minutes). Disabled by default.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_last_tick_at: datetime | None = None
_POOL_PATH = Path("/home/bs/ai/tiktok_content_pool.json")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SLOT_TYPES = ["motivation", "dark_humor", "cosmic"]

_SLOT_PROMPTS = {
    "motivation": (
        "Generate 3 original motivational quotes for TikTok that hit hard — "
        "not generic poster quotes. Think: stoic philosophy, brutal honesty, "
        "quiet power. Max 15 words each. English. Each quote must feel like "
        "a punch to the gut, not a greeting card. "
        "Output as JSON array of strings, no explanations."
    ),
    "dark_humor": (
        "Generate 3 dark humor observations for TikTok — genuinely dark, "
        "absurd, or unsettlingly funny. Not cute or relatable — think: "
        "existential dread disguised as a joke, bleak irony, morbid wit. "
        "Max 20 words each. English. Safe for work but not safe for feelings. "
        "Output as JSON array of strings, no explanations."
    ),
    "cosmic": (
        "Generate 3 COMPLETELY DIFFERENT cosmic/existential voiceover lines for a TikTok nebula video. "
        "Each must be 2-4 sentences of poetic, mind-bending cosmic truth. "
        "Line 1: about stars and death. Line 2: about time and entropy. Line 3: about emptiness and wonder. "
        "Think: Carl Sagan meets late-night thoughts. English. "
        "No two lines may be similar. Output as JSON array of 3 strings, no explanations."
    ),
}

_SLOT_FALLBACKS = {
    "motivation": "You didn't wake up to be mediocre.",
    "dark_humor": "My therapist says I have a preoccupation with vengeance. We'll see about that.",
    "cosmic": "Everything you see is the universe experiencing itself.",
}

_SLOT_HASHTAGS = {
    "motivation": "#motivation #mindset #fyp #success",
    "dark_humor": "#darkhumor #funnyquotes #fyp #relatable",
    "cosmic": "#space #universe #cosmic #deepthoughts #fyp",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def tick_tiktok_research_daemon() -> dict:
    """Daily tick — generate content concepts and write to pool file.

    Never raises. Always returns a dict with at minimum {"skipped": True/False}.
    """
    global _last_tick_at

    try:
        now = datetime.now(UTC)
        today_str = now.date().isoformat()

        # 1. Check if pool was generated today already
        existing = _load_pool()
        if existing:
            gen_at = existing.get("generated_at", "")
            if gen_at.startswith(today_str):
                return {"skipped": True, "reason": "already_generated_today"}

        # 2. Generate concepts for each slot type
        all_concepts = []
        for slot_type in _SLOT_TYPES:
            texts = _generate_concepts_for_type(slot_type)
            for i, text in enumerate(texts, start=1):
                concept_id = f"{today_str}_{slot_type}_{i:03d}"
                concept = {
                    "id": concept_id,
                    "type": slot_type,
                    "text": text,
                    "hashtags": _SLOT_HASHTAGS[slot_type],
                    "used": False,
                    "created": now.isoformat(),
                }
                all_concepts.append(concept)

        # 3. Load existing pool, append new concepts, preserve used_ids
        pool = existing if existing else {}
        existing_concepts = pool.get("concepts", [])
        used_ids = pool.get("used_ids", [])

        # 4. Prune concepts older than 7 days that are used: True
        cutoff = now.timestamp() - (7 * 24 * 3600)
        kept_concepts = []
        for c in existing_concepts:
            if c.get("used", False):
                try:
                    created_ts = datetime.fromisoformat(c["created"]).timestamp()
                    if created_ts < cutoff:
                        continue  # prune old used concept
                except Exception:
                    pass
            kept_concepts.append(c)

        # Merge: new concepts appended after pruned existing ones
        merged = kept_concepts + all_concepts

        updated_pool = {
            "generated_at": now.isoformat(),
            "concepts": merged,
            "used_ids": used_ids,
        }

        # 5. Write updated pool to disk
        _POOL_PATH.parent.mkdir(parents=True, exist_ok=True)
        _POOL_PATH.write_text(
            json.dumps(updated_pool, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        _last_tick_at = now
        return {"generated": True, "concepts_added": len(all_concepts)}

    except Exception as exc:
        return {"error": str(exc), "skipped": True}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_pool() -> dict:
    """Load the pool JSON from disk. Returns empty dict if missing or corrupt."""
    try:
        if _POOL_PATH.exists():
            return json.loads(_POOL_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _generate_concepts_for_type(slot_type: str) -> list[str]:
    """Call LLM to generate 3 concepts for the given slot type.

    Falls back to a single hardcoded example on any failure.
    Returns a list of exactly 3 strings.
    """
    fallback_text = _SLOT_FALLBACKS[slot_type]
    fallback = [fallback_text, fallback_text, fallback_text]

    try:
        from apps.api.jarvis_api.services.daemon_llm import daemon_llm_call

        raw = daemon_llm_call(
            _SLOT_PROMPTS[slot_type],
            max_len=1000,
            fallback="",
            daemon_name="tiktok_research",
        )
        if not raw:
            return fallback

        parsed = _parse_json_array(raw)
        if parsed and len(parsed) >= 1:
            # Ensure we have exactly 3 items
            while len(parsed) < 3:
                parsed.append(fallback_text)
            return [str(t).strip() for t in parsed[:3]]

        return fallback
    except Exception:
        return fallback


def _parse_json_array(text: str) -> list | None:
    """Try to parse a JSON array from LLM output. Returns None on failure."""
    try:
        # Try direct parse first
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except Exception:
        pass

    # Try to extract JSON array from surrounding text
    try:
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            result = json.loads(text[start : end + 1])
            if isinstance(result, list):
                return result
    except Exception:
        pass

    return None
