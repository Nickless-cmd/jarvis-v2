"""Session topic tracker — real-time topic extraction and accumulation.

During a long session, Jarvis loses track of topics discussed earlier
due to context compression (/compact) or topic switching. This module
extracts key topics from user messages every N turns and stores them
in a DB table so they survive compression and restarts.

Architecture:
  - Lightweight keyword-based topic extraction from user messages
    (no LLM call needed — uses technical term detection + noun phrases)
  - Topic accumulator: topics are merged/boosted when rementioned
  - DB persistence via session_topics table
  - Prompt section injector so Jarvis sees active topics in awareness

Usage in visible_runs.py:
  track_session_topics(session_id, run_id, user_message)

In awareness injector:
  build_session_topics_prompt_section() → returns markdown or None
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import UTC, datetime
from typing import Sequence

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# How many user turns between topic re-extraction
_EXTRACT_EVERY_N_TURNS = 3
# Max topics to show in prompt section
_MAX_TOPICS_PROMPT = 8
# Minimum times a topic must be mentioned to qualify
_MIN_MENTIONS = 1
# How many recent user messages to scan for topics
_SCAN_WINDOW = 10

# ---------------------------------------------------------------------------
# In-memory topic accumulator (per session)
# ---------------------------------------------------------------------------

# Stops words to skip during topic extraction
_STOP_WORDS = frozenset({
    "det", "den", "denne", "dette", "de", "dem", "du", "dig", "din",
    "jeg", "mig", "min", "mit", "vi", "os", "vores",
    "er", "har", "havde", "var", "blev", "bliver", "være", "været",
    "ikke", "og", "eller", "men", "for", "til", "af", "på", "i",
    "med", "om", "at", "en", "et", "det", "de", "den",
    "kan", "skal", "vil", "skulle", "ville", "kunne", "må",
    "gøre", "gør", "gjorde", "sige", "siger", "sagde",
    "komme", "kom", "gå", "går", "se", "ser", "så",
    "bare", "også", "jo", "da", "så", "nu", "lige", "allerede",
    "godt", "ok", "ja", "nej", "hej", "hey",
    "hvad", "hvor", "hvem", "hvordan", "hvorfor", "hvornår",
    "når", "hvis", "fordi", "selvom", "selv",
    "værsgo", "tak", "gerne", "undskyld",
    "the", "a", "an", "is", "are", "was", "were", "been",
    "it", "its", "this", "that", "these", "those",
    "i", "you", "your", "we", "our",
    "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might",
    "just", "like", "well", "yes", "no", "okay",
    "what", "where", "who", "why", "when", "how",
    "so", "then", "there", "here", "now", "then",
})

# Technical terms patterns — code-related keywords that are likely topics
_TECH_TERM_RE = re.compile(
    r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)*)\b'  # CamelCase (class names)
)

# Noun-like patterns (capitalized words, file extensions, paths)
_NOUN_RE = re.compile(
    r'\b(?:[A-Z]\w{2,}|\.\w{2,4})\b'  # Capitalized 3+ chars or .ext
)

# Known common topics that are likely noise
_NOISE_TOPICS = frozenset({
    "github", "email", "file", "code", "text", "data", "word", "line",
    "type", "value", "key", "url", "path", "name", "id", "number",
    "error", "status", "state", "mode", "set", "get", "run",
    "done", "working", "test", "work", "time", "day", "thing", "ting",
    "page", "view", "step", "case", "end", "start", "back", "new",
})


def _extract_topics_from_text(text: str) -> list[str]:
    """Extract candidate topic labels from a user message.

    Returns a list of normalized topic strings, ordered by confidence.
    No LLM call — pure regex + stop-word filtering.
    """
    if not text or not text.strip():
        return []

    topics: list[str] = []
    seen: set[str] = set()

    # 1. Extract technical terms (CamelCase, snake_case identifiers)
    # Also grab inline code blocks and backtick terms
    code_terms = re.findall(r'`([^`]+)`', text)
    for term in code_terms:
        term = term.strip()
        if len(term) >= 3 and term.lower() not in _STOP_WORDS:
            normalized = term.lower().replace("_", " ").replace("-", " ")
            if normalized not in seen and len(normalized.split()) <= 4:
                topics.append(term)
                seen.add(normalized)

    # 2. Extract CamelCase terms (class/type names)
    for match in _TECH_TERM_RE.finditer(text):
        term = match.group(1)
        lower = term.lower()
        if lower not in _STOP_WORDS and lower not in seen and len(term) >= 3:
            topics.append(term)
            seen.add(lower)

    # 3. Extract noun-like terms (capitalized words)
    for match in _NOUN_RE.finditer(text):
        term = match.group(0)
        lower = term.lower()
        if lower.startswith("."):  # file extension
            ext_name = term[1:].upper()
            if len(ext_name) >= 2 and ext_name not in seen and ext_name != "":
                topics.append(ext_name)
                seen.add(ext_name)
            continue
        if (lower not in _STOP_WORDS
                and lower not in seen
                and lower not in _NOISE_TOPICS
                and len(term) >= 3):
            topics.append(term)
            seen.add(lower)

    # 4. Split compound words (e.g. "topicTracker" → "topic tracker")
    #    Already handled by CamelCase pattern above

    # 5. Look for technical abbreviations (HTTP, API, DB, SQL, etc.)
    abbrev = re.findall(r'\b([A-Z]{2,})\b', text)
    for a in abbrev:
        lower = a.lower()
        if lower not in seen and len(a) >= 2:
            topics.append(a)
            seen.add(lower)

    # Deduplicate by case-insensitive match
    final: list[str] = []
    final_seen: set[str] = set()
    for topic in topics:
        key = topic.lower().replace("_", " ").replace("-", " ").strip()
        if key not in final_seen and key:
            final.append(topic)
            final_seen.add(key)

    return final[:6]  # cap at 6 topics per message


# ---------------------------------------------------------------------------
# Module-level session topic state
# ---------------------------------------------------------------------------

# {session_id: {topic_label: {"count": int, "first_seen": str, "last_seen": str}}}
_session_topics: dict[str, dict[str, dict]] = defaultdict(lambda: defaultdict(dict))
# {session_id: turn_count}
_session_turn_counts: dict[str, int] = defaultdict(int)


def _increment_turn(session_id: str) -> int:
    """Increment turn counter for session. Returns new count."""
    _session_turn_counts[session_id] += 1
    return _session_turn_counts[session_id]


def _should_extract(session_id: str) -> bool:
    """Return True if it's time to extract topics for this session."""
    count = _session_turn_counts.get(session_id, 0)
    return count > 0 and count % _EXTRACT_EVERY_N_TURNS == 0


def _accumulate_topics(session_id: str, topics: list[str]) -> None:
    """Merge extracted topics into the session's topic store."""
    now = datetime.now(UTC).isoformat()
    store = _session_topics[session_id]
    for topic in topics:
        key = topic.lower().strip()
        if not key:
            continue
        if key in store:
            store[key]["count"] += 1
            store[key]["last_seen"] = now
        else:
            store[key] = {
                "label": topic,
                "count": 1,
                "first_seen": now,
                "last_seen": now,
            }


def track_session_topics(
    session_id: str | None,
    run_id: str,
    user_message: str,
) -> None:
    """Call this after every visible user turn.

    Extracts topics from the user message and accumulates them
    for the current session. Extraction happens every N turns.
    """
    if not session_id:
        return

    turn = _increment_turn(session_id)
    topics = _extract_topics_from_text(user_message)
    if topics:
        _accumulate_topics(session_id, topics)
        logger.debug(
            "session_topics[%s] turn=%d extracted=%s",
            session_id, turn, topics,
        )

    # Persist to DB every extraction cycle
    if _should_extract(session_id) or turn == 1:
        _persist_session_topics(session_id)


# ---------------------------------------------------------------------------
# DB persistence
# ---------------------------------------------------------------------------

_TOPICS_DB_PERSISTED: set[str] = set()  # track which sessions we've written


def _persist_session_topics(session_id: str) -> None:
    """Write current in-memory topics to the session_topics DB table."""
    store = _session_topics.get(session_id)
    if not store:
        return

    try:
        from core.runtime.db import session_topic_accumulate
        for key, info in store.items():
            session_topic_accumulate(
                session_id=session_id,
                topic_label=str(info.get("label", key)),
                mention_count=int(info.get("count", 1)),
                first_seen=str(info.get("first_seen", "")),
                last_seen=str(info.get("last_seen", "")),
            )
        _TOPICS_DB_PERSISTED.add(session_id)
    except Exception as exc:
        logger.warning("session_topics: DB persist failed: %s", exc)


def load_session_topics(session_id: str | None) -> list[dict]:
    """Load topics for a session from DB, merging with in-memory state.

    Used at session start to restore topics after restart.
    """
    if not session_id:
        return []
    # Prefer in-memory if we have it (fresher)
    if session_id in _session_topics:
        return _format_topics_for_prompt(_session_topics[session_id])

    # Fall back to DB
    try:
        from core.runtime.db import session_topics_for_session
        rows = session_topics_for_session(session_id)
        if rows:
            # Restore into memory
            store = _session_topics[session_id]
            for row in rows:
                label = str(row.get("topic_label", ""))
                key = label.lower().strip()
                if key:
                    store[key] = {
                        "label": label,
                        "count": int(row.get("mention_count", 1)),
                        "first_seen": str(row.get("first_seen", "")),
                        "last_seen": str(row.get("last_seen", "")),
                    }
            return _format_topics_for_prompt(store)
    except Exception as exc:
        logger.warning("session_topics: DB load failed: %s", exc)
    return []


def _format_topics_for_prompt(
    store: dict[str, dict],
    max_topics: int = _MAX_TOPICS_PROMPT,
) -> list[dict]:
    """Format topics sorted by mention count descending."""
    sorted_topics = sorted(
        store.values(),
        key=lambda t: (int(t.get("count", 0)), t.get("label", "")),
        reverse=True,
    )
    # Filter by min mentions
    filtered = [t for t in sorted_topics if int(t.get("count", 0)) >= _MIN_MENTIONS]
    return filtered[:max_topics]


# ---------------------------------------------------------------------------
# Prompt section builder — injects into awareness
# ---------------------------------------------------------------------------


def build_session_topics_prompt_section(session_id: str | None = None) -> str | None:
    """Build a compact section showing active topics for this session.

    Returns a markdown string like:
      ## Emner i denne samtale
      • topic1 (nævnt 3x)
      • topic2 (nævnt 1x)

    Returns None if no topics or no session_id.
    """
    if not session_id:
        return None

    # First try in-memory, then DB
    if session_id in _session_topics and _session_topics[session_id]:
        topics = _format_topics_for_prompt(_session_topics[session_id])
    else:
        topics = load_session_topics(session_id)

    if not topics:
        return None

    lines = ["## Emner i denne samtale"]
    for t in topics:
        label = str(t.get("label", ""))
        count = int(t.get("count", 1))
        if count == 1:
            lines.append(f"• {label}")
        else:
            lines.append(f"• {label} ({count}x)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


def clear_session_topics(session_id: str | None) -> None:
    """Clear in-memory topics for a session. Called at session end."""
    if session_id and session_id in _session_topics:
        # Persist one last time before clearing
        _persist_session_topics(session_id)
        del _session_topics[session_id]
        _session_turn_counts.pop(session_id, None)
        _TOPICS_DB_PERSISTED.discard(session_id)
