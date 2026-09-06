"""Substance gates for memory writers (memory repair 2026-09-04, R3/R6).

The private promotion chain produced 16.497 "promote" decisions whose text was
a template around an empty topic — ``I should keep carrying what helped around
hmm`` (1.340× "open conversation", 153× "?", 138× a provider error) — and that
template was what the prompt received as "retained memory". Private-brain
continuity carried raw telemetry fragments ("Current conductor mode: clarify",
"tick quality trend: …") which Jarvis himself flagged as injected telemetry.

Two pure helpers, no I/O:

- ``has_substance(text)`` — is this worth persisting as a memory?
- ``strip_telemetry_fragments(text)`` / ``is_telemetry_fragment(segment)`` —
  drop machine-state fragments before they become memory.
"""
from __future__ import annotations

import re

_MIN_CHARS = 30

# Topics the private inner note falls back to when the run had no real focus.
_EMPTY_TOPICS = frozenset({
    "", "hmm", "?", "??", "…", "...", "open conversation", "open", "[self",
    "[self]", "tool:", "tool", "interrupted", "unknown", "none", "n/a",
    "visible work", "visible-work", "visible run", "autonomous run",
})

_PROVIDER_ERROR_MARKERS = (
    "sorry, to prevent abuse",
    "rate limit",
    "quota exceeded",
    "insufficient_quota",
    "http 429",
    "error code:",
    "traceback (most recent call last)",
)

# Words that carry no topic on their own (Danish + English, lowercase).
_STOPWORDS = frozenset({
    "should", "keep", "carrying", "what", "helped", "around", "still", "feels",
    "more", "stable", "now", "that", "this", "with", "from", "about", "have",
    "been", "were", "will", "just", "into", "than", "then", "them", "they",
    "there", "here", "when", "where", "which", "would", "could", "also",
    "værd", "holde", "fast", "hjalp", "omkring", "peger", "stadig", "mere",
    "stabilt", "virker", "det", "der", "som", "med", "for", "til", "ikke",
    "noget", "mere", "denne", "dette", "være", "bliver", "blive", "kræver",
    "varsom", "hånd", "følge", "tråden", "quietly", "watching", "careful",
    "conversation", "visible", "work", "run", "session", "signal", "carry",
    "private", "thread", "loop", "state", "mode", "item", "trend", "quality",
})

_TELEMETRY_PREFIXES = (
    "current conductor mode",
    "conductor mode",
    "most salient item",
    "tick quality",
    "visible run completed after tools",
    "visible run completed",
    "private carry",
    "private thread",
    "witness trace",
    "open loop:",
    "open loop",
    "development focus",
    "loop=",
    "body=",
    "experiential continuity",
    "attentional posture",
    "initiative shading",
    "cognitive bearing",
    "experiential influence",
    "support posture",
    "support bias",
    "support mode",
    "experiential support",
    "personality bearing",
    "conflict outcome",
    "conflict pressure",
    "idle consolidation settled",
    "diverse inner threads",
    "across 6 records",
    "across 5 records",
    "across 4 records",
)

_WORD_RE = re.compile(r"[a-zA-ZæøåÆØÅ][a-zA-ZæøåÆØÅ\-]{3,}")


def _norm(text: str) -> str:
    return " ".join(str(text or "").split()).strip()


def is_telemetry_fragment(segment: str) -> bool:
    """True when a text segment is a rendered runtime-telemetry label/value."""
    s = _norm(segment).lower().strip("\"'«»[]()- ")
    if not s:
        return False
    for prefix in _TELEMETRY_PREFIXES:
        if s.startswith(prefix):
            return True
    # "[carry] Diverse inner threads (6 types) are all still active."
    if s.startswith("[carry]") or s.startswith("carry]"):
        return True
    # snake_case machine identifiers as the whole segment
    core = s.split(":", 1)[-1].strip()
    if core and " " not in core and core.count("_") >= 2:
        return True
    return False


def strip_telemetry_fragments(text: str) -> str:
    """Remove telemetry fragments from a ' + ' / ' - ' / newline joined text.

    Keeps segment order and the original ' + ' joiner when present.
    Returns "" when nothing but telemetry remains.
    """
    raw = str(text or "")
    if not raw.strip():
        return ""
    if " + " in raw:
        joiner = " + "
        parts = raw.split(" + ")
    elif "\n" in raw:
        joiner = "\n"
        parts = raw.split("\n")
    else:
        parts = [raw]
        joiner = ""
    keep: list[str] = []
    for part in parts:
        cleaned = _strip_dash_chain(part)
        if cleaned.strip() and not is_telemetry_fragment(cleaned):
            keep.append(cleaned)
    return joiner.join(keep)


def _strip_dash_chain(part: str) -> str:
    """Handle the inner ``"a" - "b" - "c"`` chains the inner-voice renderer emits."""
    if '" - "' not in part:
        return part
    segs = [seg.strip().strip('"') for seg in part.split('" - "')]
    kept = [seg for seg in segs if seg.strip() and not is_telemetry_fragment(seg)]
    return " - ".join(kept)


def topic_of(text: str) -> str:
    """Best-effort topic extraction from the promotion template.

    ``"… what helped around hmm. It still …"`` → ``"hmm"``;
    ``"… hjalp omkring open conversation. Det …"`` → ``"open conversation"``.
    Returns the whole text when no template marker is found.
    """
    s = _norm(text)
    low = s.lower()
    for marker in ("helped around ", "hjalp omkring ", "careful around ", "watching ",
                   "varsom hånd omkring ", "tråden omkring "):
        i = low.find(marker)
        if i >= 0:
            rest = s[i + len(marker):]
            rest = re.split(r"[.!?]", rest, maxsplit=1)[0]
            return rest.strip().strip("\"'«»")
    return s


def has_substance(text: str) -> bool:
    """Is ``text`` worth persisting as a memory/promotion?

    False when: empty or shorter than 30 chars; the topic is one of the
    known empty fallbacks ("hmm", "?", "open conversation", "[SELF", "tool:",
    "interrupted"); it carries a provider error; or no content word (≥ 4
    letters) survives the stoplist.
    """
    s = _norm(text)
    if len(s) < _MIN_CHARS:
        return False
    low = s.lower()
    if any(m in low for m in _PROVIDER_ERROR_MARKERS):
        return False
    topic = topic_of(s).lower().strip()
    if topic in _EMPTY_TOPICS or topic.startswith("[self") or topic.startswith("tool:"):
        return False
    if is_telemetry_fragment(topic):
        return False
    words = [w.lower() for w in _WORD_RE.findall(topic if topic != low else s)]
    content = [w for w in words if w not in _STOPWORDS]
    return bool(content)


def is_empty_topic(topic: str) -> bool:
    """True when a short topic/focus label carries no content (for gates that
    see the topic alone, e.g. the retained-memory prompt signal)."""
    raw = _norm(topic).lower()
    if raw.startswith("[self") or raw.startswith("tool:"):
        return True
    t = raw.strip("\"'«»[]()- ")
    if not t or t in _EMPTY_TOPICS:
        return True
    if is_telemetry_fragment(t):
        return True
    words = [w.lower() for w in _WORD_RE.findall(t)]
    return not [w for w in words if w not in _STOPWORDS]
