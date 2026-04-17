from __future__ import annotations

import re

_NOISE_PATTERNS = (
    re.compile(r"\bmake\s+stabilize\b", re.IGNORECASE),
    re.compile(r"\bland\s+visibly\b", re.IGNORECASE),
    re.compile(r"\bcould\s+be\s+approached\s+differently\b", re.IGNORECASE),
    re.compile(r"^observed:\s*", re.IGNORECASE),
)

_TECHNICAL_HINTS = (
    "api",
    "approval",
    "archive",
    "audit",
    "branch",
    "build",
    "chronicle",
    "ci",
    "cleanup",
    "commit",
    "compile",
    "config",
    "council",
    "daemon",
    "db",
    "debug",
    "deploy",
    "docs",
    "file",
    "fix",
    "git",
    "hook",
    "import",
    "inner voice",
    "jarvis",
    "json",
    "lane",
    "log",
    "memory",
    "mission control",
    "model",
    "patch",
    "pipeline",
    "plugin",
    "pre-commit",
    "prompt",
    "provider",
    "py",
    "pytest",
    "refactor",
    "repo",
    "route",
    "runtime",
    "script",
    "secret",
    "service",
    "signal",
    "sql",
    "sqlite",
    "systemd",
    "test",
    "token",
    "tool",
    "uvicorn",
    "workflow",
    "workspace",
)

_ACTION_HINTS = (
    "add",
    "archive",
    "audit",
    "build",
    "check",
    "clean",
    "compile",
    "create",
    "debug",
    "emit",
    "fix",
    "generate",
    "improve",
    "inject",
    "install",
    "move",
    "persist",
    "read",
    "refactor",
    "remove",
    "repair",
    "replace",
    "rotate",
    "run",
    "scan",
    "stabilize",
    "test",
    "track",
    "update",
    "verify",
    "write",
)

_EMOJI_OR_CHATTER = re.compile(r"[😀-🙏🌀-🫶😉😛❤️🙂]|(^|\s)(ven|hey|hej|min ven|buddy)(\s|$)", re.IGNORECASE)
_NON_WORDS = re.compile(r"[^a-z0-9/._ -]+", re.IGNORECASE)
_WHITESPACE = re.compile(r"\s+")


def normalize_signal_text(text: str) -> str:
    return _WHITESPACE.sub(" ", str(text or "").strip())


def strip_signal_wrappers(text: str) -> str:
    cleaned = normalize_signal_text(text)
    wrappers = (
        ("Current goal: make stabilize ", ""),
        ("Current goal: ", ""),
        ("Reflected on: ", ""),
        ("Hypothesis from ", ""),
        ("Observed: ", ""),
        ("What if ", ""),
    )
    for prefix, replacement in wrappers:
        if cleaned.lower().startswith(prefix.lower()):
            cleaned = replacement + cleaned[len(prefix):]
            break
    cleaned = re.sub(r"\s*→\s*(completed|failed|success|error)\s*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+land visibly\s*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+could be approached differently\??\s*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"^Development state is pushing toward .*? around ",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return normalize_signal_text(cleaned)


def is_noisy_signal_text(text: str) -> bool:
    normalized = normalize_signal_text(text)
    stripped = strip_signal_wrappers(normalized)
    lowered = stripped.lower()
    if not stripped or len(stripped) < 8:
        return True
    if any(pattern.search(normalized) for pattern in _NOISE_PATTERNS):
        return True
    if lowered in {"?", "none", "n/a"}:
        return True
    if stripped.startswith("http://") or stripped.startswith("https://") or stripped.startswith("htttp:/"):
        return True
    if _EMOJI_OR_CHATTER.search(stripped) and not looks_like_substantive_runtime_topic(stripped):
        return True
    return not looks_like_substantive_runtime_topic(stripped)


def looks_like_substantive_runtime_topic(text: str) -> bool:
    normalized = strip_signal_wrappers(text)
    lowered = normalized.lower()
    if not normalized:
        return False
    if any(hint in lowered for hint in _TECHNICAL_HINTS):
        return True
    words = [word for word in _NON_WORDS.sub(" ", lowered).split() if word]
    if len(words) >= 4 and words[0] in _ACTION_HINTS:
        return True
    if "/" in normalized or ".py" in lowered or ".md" in lowered or ".json" in lowered:
        return True
    return False


def stable_signal_slug(text: str, *, fallback: str = "") -> str:
    topic = strip_signal_wrappers(text).lower()
    topic = _NON_WORDS.sub(" ", topic)
    topic = _WHITESPACE.sub("-", topic).strip("-")
    if not topic:
        return fallback
    words = [part for part in topic.split("-") if part]
    trimmed = "-".join(words[:10]).strip("-")
    if len(trimmed) < 6:
        return fallback
    return trimmed[:96]


def build_bounded_hypothesis_text(topic: str) -> str:
    cleaned = strip_signal_wrappers(topic)
    return (
        f"En lille hypotese er ved at tage form omkring {cleaned.lower()}: "
        "måske kræver det en mere afgrænset, rolig iteration frem for endnu et bredt skift."
    )
