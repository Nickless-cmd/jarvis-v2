"""Tool tag taxonomy.

Three layers, override-first:
  1. tool_tags.overrides.json — manual overrides (wins)
  2. tool_tags.json           — LLM-bootstrap auto tags
Pinned set lives in tool_tags.pinned.json (separate axis from tags).

Cached in-memory; invalidate_cache() forces re-read.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Allowed tag domains (LLM bootstrap is constrained to this set)
ALLOWED_DOMAINS = {
    "memory", "code", "system", "web", "social", "audio", "video",
    "image", "identity", "scheduling", "hardware", "dev", "planning",
    "search",
}

_STATE_DIR = Path(os.getenv("JARVIS_STATE_DIR") or (Path.home() / ".jarvis-v2" / "state"))
_TAGS_PATH = _STATE_DIR / "tool_tags.json"
_OVERRIDES_PATH = _STATE_DIR / "tool_tags.overrides.json"
_PINNED_PATH = _STATE_DIR / "tool_tags.pinned.json"

# Fallback to repo paths if state dir doesn't have them yet (first-run)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_REPO_OVERRIDES = _REPO_ROOT / "state" / "tool_tags.overrides.json"
_REPO_PINNED = _REPO_ROOT / "state" / "tool_tags.pinned.json"

_cache: dict[str, object] = {"loaded": False}


def _load_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text())
    except FileNotFoundError:
        return {}
    except Exception as exc:
        logger.warning("tool_tagger: failed to read %s: %s", p, exc)
        return {}


def _ensure_loaded() -> None:
    if _cache.get("loaded"):
        return
    auto = _load_json(_TAGS_PATH).get("tags", {}) or {}
    overrides = _load_json(_OVERRIDES_PATH).get("overrides", {}) or {}
    if not overrides and _REPO_OVERRIDES.exists():
        overrides = _load_json(_REPO_OVERRIDES).get("overrides", {}) or {}
    pinned = set(_load_json(_PINNED_PATH).get("pinned", []) or [])
    if not pinned and _REPO_PINNED.exists():
        pinned = set(_load_json(_REPO_PINNED).get("pinned", []) or [])
    _cache["auto"] = auto
    _cache["overrides"] = overrides
    _cache["pinned"] = pinned
    _cache["loaded"] = True


def get_tags(tool_name: str) -> list[str]:
    """Return tags for `tool_name`. Overrides win over auto. Empty if unknown."""
    _ensure_loaded()
    overrides = _cache["overrides"]  # type: ignore[index]
    if tool_name in overrides:
        return list(overrides[tool_name])
    auto = _cache["auto"]  # type: ignore[index]
    return list(auto.get(tool_name, []))


def get_pinned_set() -> set[str]:
    _ensure_loaded()
    return set(_cache["pinned"])  # type: ignore[arg-type]


def invalidate_cache() -> None:
    _cache.clear()
    _cache["loaded"] = False


def bootstrap_tags(*, dry_run: bool = False) -> dict[str, list[str]]:
    """Use cheap-lane LLM to generate domain tags for every registered tool.

    Returns the {tool_name: [tags]} dict. If dry_run is False, writes to
    `_TAGS_PATH` (the auto layer; overrides remain untouched).
    """
    from core.tools.simple_tools import get_tool_definitions
    from core.services.cheap_provider_runtime import execute_cheap_lane_via_pool

    defs = get_tool_definitions() or []
    catalog = []
    for d in defs:
        fn = d.get("function") or d
        name = fn.get("name") or "?"
        desc = str(fn.get("description") or "").strip().split("\n", 1)[0][:200]
        catalog.append({"name": name, "desc": desc})

    prompt = (
        "Tag each tool with 1-3 domain tags from this fixed set:\n"
        f"{sorted(ALLOWED_DOMAINS)}\n\n"
        "Return strict JSON only: {\"tags\": {\"tool_name\": [\"tag1\", \"tag2\"]}}.\n"
        "No prose, no code fences. Only tags from the allowed set.\n\n"
        f"Tools:\n{json.dumps(catalog, ensure_ascii=False)}"
    )

    response = execute_cheap_lane_via_pool(
        message=prompt,
        task_kind="tool_tag_bootstrap",
    )
    response_text = str(response.get("text") or "")

    # Strip code fences if present
    if "```" in response_text:
        parts = response_text.split("```")
        for p in parts:
            p_strip = p.strip()
            if p_strip.startswith("{") or p_strip.startswith("json\n"):
                response_text = p_strip.removeprefix("json\n").strip()
                break

    try:
        parsed = json.loads(response_text)
        tags = parsed.get("tags", {})
    except Exception as exc:
        logger.error("tool_tagger.bootstrap_tags parse failed: %s; head=%r", exc, response_text[:200])
        tags = {}

    cleaned = {
        name: [t for t in tag_list if t in ALLOWED_DOMAINS][:3]
        for name, tag_list in tags.items()
        if isinstance(tag_list, list)
    }

    if not dry_run:
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
        _TAGS_PATH.write_text(
            json.dumps({"tags": cleaned}, ensure_ascii=False, indent=2)
        )
        invalidate_cache()

    return cleaned


