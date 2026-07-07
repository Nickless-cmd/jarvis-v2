"""JarvisX-specific routes — small endpoints used by the desktop app.

Endpoints:
  /api/whoami            — which workspace did the X-JarvisX-User header
                           resolve to (verifies user-routing middleware)
  /api/workspace/tree    — list canonical workspace files + dreams + daily
  /api/workspace/read    — fetch a single workspace file's content
  /api/workspace/list    — list all available workspaces (for switcher)

This module was split (behavior-preserving) into feature submodules:
  jarvisx_common      — shared constants + path guards + owner check
  jarvisx_workspace   — whoami, workspace list/tree/read, mind, pins, chronicle
  jarvisx_project     — project tree/list/read/notes + file watch
  jarvisx_channels    — channels/state + scheduling/state
  jarvisx_sessions    — preferences, tools/inventory, todos, chat search,
                        staged edits, tool-result, plans, session fork
  jarvisx_processes   — process supervisor, trading state, operator wakeup
  jarvisx_dispatches  — Claude-Code dispatch dashboard
  jarvisx_authtokens  — bearer-token issuance + verification

The aggregate `router` below carries every route from those submodules, so
imports of `router` (and any symbol) from this module keep working exactly
as before.
"""
from __future__ import annotations

import logging
from datetime import datetime  # noqa: F401 — re-exported for back-compat
from pathlib import Path  # noqa: F401 — re-exported for back-compat
from typing import Any  # noqa: F401 — re-exported for back-compat

from fastapi import APIRouter

# ── Shared constants / guards (re-exported) ───────────────────────
from apps.api.jarvis_api.routes.jarvisx_common import (  # noqa: F401
    CANONICAL_FILES,
    MAX_DIR_ENTRIES,
    MAX_READ_BYTES,
    SAFE_EXTENSIONS,
    WORKSPACES_DIR,
    _require_owner,
    _resolve_workspace,
    _safe_subpath,
)
from core.runtime.config import WORKSPACES_DIR as _WORKSPACES_DIR_RAW  # noqa: F401

# ── Submodule routers ─────────────────────────────────────────────
from apps.api.jarvis_api.routes import jarvisx_authtokens as _authtokens
from apps.api.jarvis_api.routes import jarvisx_channels as _channels
from apps.api.jarvis_api.routes import jarvisx_dispatches as _dispatches
from apps.api.jarvis_api.routes import jarvisx_processes as _processes
from apps.api.jarvis_api.routes import jarvisx_project as _project
from apps.api.jarvis_api.routes import jarvisx_sessions as _sessions
from apps.api.jarvis_api.routes import jarvisx_workspace as _workspace

# ── Endpoint functions + models (re-exported so patch("...jarvisx.<name>")
#    and direct imports keep resolving) ─────────────────────────────
from apps.api.jarvis_api.routes.jarvisx_workspace import (  # noqa: F401
    _ChroniclePayload,
    _PinPayload,
    add_identity_pin,
    list_workspaces,
    mind_snapshot,
    remove_identity_pin,
    whoami,
    workspace_read,
    workspace_tree,
    write_chronicle_entry,
)
from apps.api.jarvis_api.routes.jarvisx_project import (  # noqa: F401
    ProjectNotesUpdate,
    WatchAddRequest,
    WatchPollRequest,
    _PROJECT_READ_MAX_BYTES,
    _PROJECT_TREE_MAX_ENTRIES,
    _PROJECT_TREE_SKIP_DIRS,
    _resolve_project_root,
    _safe_project_subpath,
    _watch_lock,
    _watch_lock_holder,
    _watch_state,
    project_list,
    project_notes_get,
    project_notes_set,
    project_read,
    project_tree,
    project_watch_add,
    project_watch_clear,
    project_watch_poll,
)
from apps.api.jarvis_api.routes.jarvisx_channels import (  # noqa: F401
    _SCHEDULING_USER_KEYS,
    _filter_scheduling_payload,
    _scheduling_visible_to,
    channels_state,
    scheduling_state,
)
from apps.api.jarvis_api.routes.jarvisx_sessions import (  # noqa: F401
    PreferencesUpdate,
    TodoStatusUpdate,
    _ForkPayload,
    approve_plan,
    chat_search,
    dismiss_plan,
    fork_session,
    get_tool_result,
    list_plans,
    preferences_get,
    preferences_set,
    staged_edits,
    staged_edits_commit,
    staged_edits_discard,
    todos_list,
    todos_status,
    tools_inventory,
)
from apps.api.jarvis_api.routes.jarvisx_processes import (  # noqa: F401
    _OP_WAKEUP_MAX_PER_HOUR,
    _OP_WAKEUP_TIMES,
    _SpawnPayload,
    _trading_inactive_default,
    list_managed_processes,
    operator_wakeup_fired,
    remove_managed_process,
    spawn_managed_process,
    stop_managed_process,
    tail_managed_process_log,
    trading_state,
)
from apps.api.jarvis_api.routes.jarvisx_dispatches import (  # noqa: F401
    dispatch_budget,
    get_dispatch,
    get_dispatch_diff,
    list_dispatches,
)
from apps.api.jarvis_api.routes.jarvisx_authtokens import (  # noqa: F401
    _IssueTokenPayload,
    _RefreshTokenPayload,
    issue_auth_token,
    refresh_auth_token,
    whoami_token,
)

logger = logging.getLogger(__name__)


# Aggregate router — carries every route from the submodules so the public
# import (`from ...routes.jarvisx import router as jarvisx_router`) stays
# identical. Each submodule uses prefix="/api", so include_router preserves
# the exact same paths.
router = APIRouter()
for _sub in (
    _workspace.router,
    _project.router,
    _channels.router,
    _sessions.router,
    _processes.router,
    _dispatches.router,
    _authtokens.router,
):
    router.include_router(_sub)
