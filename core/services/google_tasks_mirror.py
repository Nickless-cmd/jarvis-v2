"""Best-effort Google Tasks-spejl for Jarvis' lokale planlagte opgaver.

Den lokale ``scheduled_tasks``-række er altid sandheden og oprettes først.
Google-kopien er et ekstra varigt lag, der kan ses selv hvis Jarvis-runtime er
nede. Hvert resultat er struktureret, så en connectorfejl aldrig forsvinder
tavst eller får en lokal reminder til at se mislykket ud.

Google Tasks gemmer kun datodelen af ``due``; det præcise RFC3339-tidspunkt
skrives derfor også i noten sammen med det lokale task-id.
"""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

from core.runtime.db_core import get_runtime_state_value, set_runtime_state_value
from core.services.oauth_store import get_fresh_token

_API = "https://tasks.googleapis.com/tasks/v1"
_PROVIDER = "google"
_STATE_KEY = "google_task_mirrors"
logger = logging.getLogger(__name__)


def _token(user_id: str) -> dict[str, Any] | None:
    token = get_fresh_token(user_id, _PROVIDER)
    return token if token and token.get("access_token") else None


def _headers(token: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {token['access_token']}"}


def _mapping(user_id: str, local_task_id: str) -> dict[str, Any] | None:
    state = get_runtime_state_value(_STATE_KEY, {}) or {}
    bucket = state.get(user_id) if isinstance(state, dict) else None
    row = bucket.get(local_task_id) if isinstance(bucket, dict) else None
    return row if isinstance(row, dict) else None


def _record(user_id: str, local_task_id: str, remote_task_id: str) -> bool:
    try:
        state = get_runtime_state_value(_STATE_KEY, {}) or {}
        if not isinstance(state, dict):
            state = {}
        bucket = state.get(user_id)
        if not isinstance(bucket, dict):
            bucket = {}
        bucket[local_task_id] = {"tasklist_id": "@default", "task_id": remote_task_id}
        state[user_id] = bucket
        set_runtime_state_value(_STATE_KEY, state)
        return _mapping(user_id, local_task_id) == bucket[local_task_id]
    except Exception:
        logger.warning(
            "google_tasks: kunne ikke gemme spejl-reference for %s/%s",
            user_id, local_task_id, exc_info=True,
        )
        return False


def _forget(user_id: str, local_task_id: str) -> None:
    state = get_runtime_state_value(_STATE_KEY, {}) or {}
    if not isinstance(state, dict):
        return
    bucket = state.get(user_id)
    if not isinstance(bucket, dict):
        return
    bucket.pop(local_task_id, None)
    if bucket:
        state[user_id] = bucket
    else:
        state.pop(user_id, None)
    set_runtime_state_value(_STATE_KEY, state)


def _http_error(status_code: int) -> dict[str, Any]:
    if status_code == 401:
        return {"status": "not_connected", "error": "google_tasks_not_connected"}
    if status_code == 403:
        return {"status": "unavailable", "error": "google_tasks_scope_or_api_unavailable"}
    return {"status": "error", "error": f"google_tasks_http_{status_code}"}


def create_task_mirror(user_id: str, task: dict[str, Any]) -> dict[str, Any]:
    """Opret en Google Task for en allerede gemt lokal opgave."""
    uid = str(user_id or "").strip()
    local_task_id = str(task.get("task_id") or "").strip()
    focus = str(task.get("focus") or "").strip()
    run_at = str(task.get("run_at") or "").strip()
    if not uid:
        return {"status": "unavailable", "error": "user_id_missing"}
    if not local_task_id or not focus or not run_at:
        return {"status": "error", "error": "local_task_incomplete"}
    token = _token(uid)
    if not token:
        return {"status": "not_connected", "error": "google_tasks_not_connected"}
    try:
        import httpx
        response = httpx.post(
            f"{_API}/lists/@default/tasks",
            headers=_headers(token),
            json={
                "title": focus[:1024],
                "notes": f"Jarvis reminder: {run_at}\nLocal task: {local_task_id}",
                "due": run_at,
            },
            timeout=20,
        )
        if response.status_code not in {200, 201}:
            return _http_error(response.status_code)
        remote_id = str((response.json() or {}).get("id") or "").strip()
        if not remote_id:
            return {"status": "error", "error": "google_tasks_missing_id"}
        tracked = _record(uid, local_task_id, remote_id)
        return {
            "status": "mirrored" if tracked else "mirrored_untracked",
            "task_id": remote_id,
            "local_task_id": local_task_id,
        }
    except Exception as exc:  # noqa: BLE001 — connectorfejl skal returneres, ikke vælte lokal oprettelse
        return {"status": "error", "error": f"google_tasks_request_failed: {exc}"}


def update_task_mirror(user_id: str, task: dict[str, Any]) -> dict[str, Any]:
    """Opdatér Google-kopien efter en vellykket lokal redigering."""
    uid = str(user_id or "").strip()
    local_task_id = str(task.get("task_id") or "").strip()
    row = _mapping(uid, local_task_id) if uid and local_task_id else None
    if not row:
        return {"status": "not_mirrored"}
    token = _token(uid)
    if not token:
        return {"status": "not_connected", "error": "google_tasks_not_connected"}
    remote_id = quote(str(row.get("task_id") or ""), safe="")
    list_id = quote(str(row.get("tasklist_id") or "@default"), safe="@")
    run_at = str(task.get("run_at") or "")
    try:
        import httpx
        response = httpx.patch(
            f"{_API}/lists/{list_id}/tasks/{remote_id}",
            headers=_headers(token),
            json={
                "title": str(task.get("focus") or "")[:1024],
                "notes": f"Jarvis reminder: {run_at}\nLocal task: {local_task_id}",
                "due": run_at,
            },
            timeout=20,
        )
        if response.status_code not in {200, 201}:
            return _http_error(response.status_code)
        return {"status": "mirrored", "task_id": str(row.get("task_id") or "")}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": f"google_tasks_request_failed: {exc}"}


def cancel_task_mirror(user_id: str, local_task_id: str) -> dict[str, Any]:
    """Slet Google-kopien efter en vellykket lokal annullering."""
    uid = str(user_id or "").strip()
    task_id = str(local_task_id or "").strip()
    row = _mapping(uid, task_id) if uid and task_id else None
    if not row:
        return {"status": "not_mirrored"}
    token = _token(uid)
    if not token:
        return {"status": "not_connected", "error": "google_tasks_not_connected"}
    remote_id = quote(str(row.get("task_id") or ""), safe="")
    list_id = quote(str(row.get("tasklist_id") or "@default"), safe="@")
    try:
        import httpx
        response = httpx.delete(
            f"{_API}/lists/{list_id}/tasks/{remote_id}",
            headers=_headers(token),
            timeout=20,
        )
        if response.status_code not in {200, 204, 404}:
            return _http_error(response.status_code)
        _forget(uid, task_id)
        return {"status": "cancelled", "task_id": str(row.get("task_id") or "")}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": f"google_tasks_request_failed: {exc}"}


__all__ = ["create_task_mirror", "update_task_mirror", "cancel_task_mirror"]
