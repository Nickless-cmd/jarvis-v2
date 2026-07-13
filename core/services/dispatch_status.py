"""Typed dispatch-status enum for the dispatch-redesign.

Pure, dependency-light. A dispatch always ends in one of six terminal
statuses. This module is the single source of truth for what those statuses
are and how to classify them (failure vs non-failure, terminal vs unknown).

Self-safe: all classifiers coerce input to str and never raise.
"""

from __future__ import annotations


class DispatchStatus:
    """String constants for the six terminal dispatch outcomes."""

    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"
    NEEDS_CONTEXT = "needs_context"
    CONCERNS = "concerns"

    @classmethod
    def all(cls) -> set[str]:
        """Return the set of all six known statuses."""
        return {
            cls.COMPLETED,
            cls.FAILED,
            cls.TIMEOUT,
            cls.BLOCKED,
            cls.NEEDS_CONTEXT,
            cls.CONCERNS,
        }


# Statuses that mean the dispatch genuinely failed to deliver.
# NOT completed (success), NOT concerns (success-with-doubt),
# NOT needs_context (a request-for-help, not a failure).
_FAILURE_STATUSES = {
    DispatchStatus.FAILED,
    DispatchStatus.TIMEOUT,
    DispatchStatus.BLOCKED,
}


def is_failure(status: object) -> bool:
    """True for failed/timeout/blocked. Unknown status -> False."""
    return str(status) in _FAILURE_STATUSES


def is_terminal(status: object) -> bool:
    """True for any of the six known statuses. Unknown status -> False."""
    return str(status) in DispatchStatus.all()
