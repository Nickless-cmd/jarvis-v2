"""Pure helper: render an ``<env>`` block for the /v1/agent/step system prompt
(jarvis-code Fase 4, Task 2). No FastAPI import — this is a plain string
transform, trivially unit-testable on its own and safe to call from anywhere.

Why this matters for caching (Task 4): callers append this block at the very
TAIL of the system prompt (the client's cwd/git-branch/date are the most
volatile facts in the whole prompt — they change every turn). Everything
BEFORE this block stays a stable, cacheable prefix. Internally this function
also uses a FIXED key order regardless of the input dict's iteration order,
so identical env content always serializes byte-identically — useful for
humans diffing prompt dumps, even though Task 4's cache-prefix signature
excludes this block entirely (it is computed over the prefix head only).
"""
from __future__ import annotations

# Fixed, stable order — do not reorder without checking Task 4 assumptions.
# Mirrors the client's collect_env() shape (src/jc_env.py in jarvis-code).
_KEY_ORDER = ("cwd", "git_branch", "git_status", "os", "platform", "date", "recent_commits")
_MAX_FIELD_CHARS = 500
_MAX_GIT_STATUS_CHARS = 1000
_MAX_COMMIT_LINES = 5
_MAX_COMMIT_LINE_CHARS = 200


def _clamp(value: object, max_chars: int = _MAX_FIELD_CHARS) -> str:
    text = str(value if value is not None else "").strip()
    if len(text) > max_chars:
        text = text[:max_chars] + "…"
    return text


def render_env_block(env: dict | None) -> str:
    """Render a fenced ``<env>...</env>`` block from a client-supplied env dict.

    Fixed key order (`_KEY_ORDER`) so identical content always serializes
    identically, then any unrecognized extra keys, sorted for the same reason.
    Field lengths are clamped so a runaway git_status/recent_commits value
    can't blow up the prompt. Self-safe: never raises; missing/empty/non-dict
    env -> "" (inert)."""
    try:
        if not env or not isinstance(env, dict):
            return ""
        lines: list[str] = []
        for key in _KEY_ORDER:
            if key not in env:
                continue
            value = env.get(key)
            if key == "recent_commits":
                if isinstance(value, list):
                    commits = [str(c) for c in value]
                else:
                    commits = str(value or "").splitlines()
                commits = [c.strip() for c in commits if c and c.strip()]
                commits = commits[:_MAX_COMMIT_LINES]
                if not commits:
                    continue
                rendered = " | ".join(_clamp(c, _MAX_COMMIT_LINE_CHARS) for c in commits)
                lines.append(f"{key}: {rendered}")
            elif key == "git_status":
                clamped = _clamp(value, _MAX_GIT_STATUS_CHARS)
                if clamped:
                    lines.append(f"{key}: {clamped}")
            else:
                clamped = _clamp(value)
                if clamped:
                    lines.append(f"{key}: {clamped}")

        extra_keys = sorted(k for k in env.keys() if k not in _KEY_ORDER)
        for key in extra_keys:
            clamped = _clamp(env.get(key))
            if clamped:
                lines.append(f"{key}: {clamped}")

        if not lines:
            return ""
        return "\n\n<env>\n" + "\n".join(lines) + "\n</env>"
    except Exception:
        return ""
