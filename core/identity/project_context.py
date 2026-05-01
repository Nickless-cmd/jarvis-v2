"""Project context — current "where am I working" as set by JarvisX.

When the desktop app sends X-JarvisX-Project on a request, the middleware
binds the path here. Downstream services (prompt_contract awareness
section, bash_session default cwd, future @file completions) read it via
current_project_root() to know what filesystem location the human is
focused on.

Default is empty string — no anchor. Tools should still work in the
absence of an anchor; this is purely a hint for "where the user expects
me to be acting".
"""
from __future__ import annotations

import contextvars

_current_project: contextvars.ContextVar[str] = contextvars.ContextVar(
    "jarvis_project_root",
    default="",
)


def current_project_root() -> str:
    """Return the current project root path, or empty string if none."""
    return _current_project.get()


def set_project_root(path: str) -> contextvars.Token:
    """Set the project root for the current context.

    Returns a Token so the caller can reset_project_root(token) when the
    request scope ends. Prefer this paired with try/finally; the JarvisX
    user-routing middleware does that automatically.
    """
    return _current_project.set(str(path or "").strip())


def reset_project_root(token: contextvars.Token) -> None:
    _current_project.reset(token)
