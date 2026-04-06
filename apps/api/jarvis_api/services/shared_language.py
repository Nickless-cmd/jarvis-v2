"""Shared Language — tracks shorthand terms that develop between Jarvis and user.

Over time, certain phrases gain shared meaning:
"presset i venstre side" = layout width bug
"hold nu!!!" = user frustration about confusion
"experiment-hatten" = creative/exploratory mode
"""

from __future__ import annotations

import logging
import re

from core.eventbus.bus import event_bus
from core.runtime.db import (
    list_cognitive_shared_language,
    upsert_cognitive_shared_language_term,
)

logger = logging.getLogger(__name__)

_TOKEN_PATTERN = re.compile(r"[a-z0-9æøå][a-z0-9æøå_\-/]{2,}", re.IGNORECASE)


def scan_for_shared_terms(
    *,
    user_message: str,
    assistant_response: str,
    run_id: str = "",
) -> list[dict[str, object]]:
    """Scan conversation for potential shared language terms.

    Looks for distinctive multi-word phrases that appear in user messages.
    """
    results = []
    msg_lower = user_message.lower()

    # Extract 2-3 word phrases (bigrams/trigrams)
    words = [m.group(0).lower() for m in _TOKEN_PATTERN.finditer(msg_lower)]
    bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
    trigrams = [f"{words[i]} {words[i+1]} {words[i+2]}" for i in range(len(words) - 2)]

    # Track distinctive phrases (length > 8 chars, not common)
    for phrase in bigrams + trigrams:
        if len(phrase) >= 8 and not _is_common_phrase(phrase):
            result = upsert_cognitive_shared_language_term(
                phrase=phrase[:60],
            )
            if result:
                results.append(result)

    if results:
        event_bus.publish(
            "cognitive_shared_language.terms_updated",
            {"run_id": run_id, "count": len(results)},
        )

    return results


def build_shared_language_surface() -> dict[str, object]:
    terms = list_cognitive_shared_language(limit=20)
    high_confidence = [t for t in terms if float(t.get("confidence", 0)) > 0.7]
    return {
        "active": bool(terms),
        "terms": terms,
        "high_confidence_count": len(high_confidence),
        "summary": (
            f"{len(terms)} terms tracked, {len(high_confidence)} established"
            if terms else "No shared language yet"
        ),
    }


_COMMON_WORDS = {
    "det", "er", "ikke", "jeg", "vil", "kan", "har", "med", "den", "som",
    "til", "for", "der", "var", "men", "fra", "have", "blive", "være", "gøre",
    "the", "and", "for", "that", "this", "with", "from", "but", "not", "are",
}


def _is_common_phrase(phrase: str) -> bool:
    words = phrase.split()
    if all(w in _COMMON_WORDS for w in words):
        return True
    if len(phrase) < 6:
        return True
    return False
