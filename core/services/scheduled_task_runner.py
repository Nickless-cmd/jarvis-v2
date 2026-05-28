"""Scheduled task dispatcher — binds workspace_context before firing.

Critical for multi-user: a task scheduled by Mikkel must wake Jarvis up
INTO Mikkel's relation, so memory injection reads Mikkel's MEMORY.md and
operator tools route to Mikkel's JarvisX bridge.

See plan: docs/superpowers/plans/2026-05-28-multi-user-workspace-isolation.md task 6
"""
from __future__ import annotations

import logging
from typing import Callable

from core.identity.users import find_user_by_discord_id
from core.identity.workspace_context import set_context, reset_context

logger = logging.getLogger(__name__)


def fire_scheduled_task(
    task: dict,
    *,
    runner: Callable[..., None],
) -> None:
    """Bind workspace_context to task's scheduled_for_user_id and run.

    Args:
        task: row dict from scheduled_tasks. Must have 'scheduled_for_user_id'
              and 'focus'. May have other fields, passed as kwargs to runner.
        runner: callable invoked with focus + extras. The context will be
                set BEFORE runner is called and reset AFTER.

    Behavior:
      - Empty/None scheduled_for_user_id → warn and skip
      - Unknown user_id (not in users.json) → warn and skip
      - Otherwise: set_context to the user, run, reset_context.
    """
    uid = (task.get("scheduled_for_user_id") or "").strip() if task.get("scheduled_for_user_id") else ""
    if not uid:
        logger.warning(
            "fire_scheduled_task: task %r has no scheduled_for_user_id — skipping",
            task.get("task_id"),
        )
        return

    user = find_user_by_discord_id(uid)
    if user is None:
        logger.warning(
            "fire_scheduled_task: user_id=%s not found in users.json — dropping task %r",
            uid, task.get("task_id"),
        )
        return

    token = set_context(
        workspace_name=user.workspace,
        user_id=user.discord_id,
        user_display_name=user.name,
    )
    try:
        runner(focus=task["focus"], task_id=task.get("task_id"))
    finally:
        reset_context(token)
