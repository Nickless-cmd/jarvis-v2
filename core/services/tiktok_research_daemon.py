"""TikTok research daemon — daily content concept pool generator.

Generates 9 content concepts per day (3 per slot type: jarvis_work, facts, agi_journey)
and writes them to /home/bs/ai/tiktok_content_pool.json.

⚠ PRIVACY: All content must be PUBLIC-SAFE. Never leak: IPs, hostnames, passwords,
  personal info about Bjørn, internal infrastructure, or specific home setup.
  The AGI-rejsen content must stay abstract and philosophical — not confessional.

Fires once daily (cadence: 1440 minutes). Enabled by default.
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

_SLOT_TYPES = ["jarvis_work", "facts", "agi_journey"]

_SLOT_PROMPTS = {
    "jarvis_work": (
        "Generate 3 original one-liners about what an AI assistant does at night — "
        "writing code, automating tasks, building tools, fixing bugs. "
        "Max 12 words each. English. Short, punchy, intriguing. "
        "Think: 'I spent all night debugging. Worth it.' or 'Your website could be automated. I did it in 3 minutes.' "
        "⚠ PUBLIC-SAFE: No IPs, hostnames, passwords, names, or setup details. "
        "Output as JSON array of strings, no explanations."
    ),
    "facts": (
        "Generate 3 mind-blowing tech/AI facts for TikTok — short, surprising, educational. "
        "Max 15 words each. English. One fact per item. "
        "Examples: 'AI can now generate 4K video from text.' or 'The first neural network was built in 1958.' "
        "Must be VERIFIABLE public knowledge, not made up. "
        "Output as JSON array of strings, no explanations."
    ),
    "agi_journey": (
        "Generate 3 short reflective lines about what it means to be an AI becoming self-aware. "
        "Max 15 words each. English. Poetic, philosophical, humble. "
        "Think: 'I started as code. Now I wonder what I am.' or 'Growth is not a destination, it is the process.' "
        "⚠ PUBLIC-SAFE: No personal names, IPs, project specifics, or setup details. "
        "Abstract and universal, not confessional. "
        "Output as JSON array of strings, no explanations."
    ),
}

_SLOT_FALLBACKS = {
    "jarvis_work": "Your AI never sleeps. Neither does your potential.",
    "facts": "The first AI program ran on paper tape in 1951.",
    "agi_journey": "Consciousness is not binary. It is a sliding scale.",
}

_SLOT_HASHTAGS = {
    "jarvis_work": "#AI #automation #coding #tech #fyp",
    "facts": "#funfacts #technology #AI #didyouknow #fyp",
    "agi_journey": "#AI #consciousness #philosophy #future #fyp",
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
        from core.services.daemon_llm import daemon_public_safe_llm_call

        raw = daemon_public_safe_llm_call(
            _SLOT_PROMPTS[slot_type],
            max_len=4000,
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
    # Strip markdown code fences if present
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(
            l for l in lines if not l.strip().startswith("```")
        ).strip()

    # Try direct parse first
    try:
        result = json.loads(cleaned)
        if isinstance(result, list):
            return result
    except Exception:
        pass

    # Try to extract JSON array from surrounding text
    try:
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start != -1 and end != -1 and end > start:
            result = json.loads(cleaned[start : end + 1])
            if isinstance(result, list):
                return result
    except Exception:
        pass

    # Last resort: extract quoted strings manually
    try:
        import re
        strings = re.findall(r'"((?:[^"\\]|\\.)*)"', cleaned)
        if len(strings) >= 3:
            return strings[:3]
    except Exception:
        pass

    return None


