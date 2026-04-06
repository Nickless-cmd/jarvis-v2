from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from core.runtime import db as runtime_db

_VALID_STATUSES = {"idle", "ready", "navigating", "observing", "acting", "blocked"}


def ensure_browser_body(
    *,
    profile_name: str = "jarvis-browser",
    active_task_id: str = "",
    active_flow_id: str = "",
) -> dict[str, object]:
    existing = _find_browser_body_by_profile(profile_name)
    now = datetime.now(UTC).isoformat()
    if existing is not None:
        return _decode_browser_body(
            runtime_db.upsert_runtime_browser_body(
                body_id=existing["body_id"],
                profile_name=profile_name,
                status=existing["status"],
                active_task_id=active_task_id or existing["active_task_id"],
                active_flow_id=active_flow_id or existing["active_flow_id"],
                focused_tab_id=existing["focused_tab_id"],
                tabs_json=json.dumps(existing["tabs"], ensure_ascii=False, sort_keys=True),
                last_url=existing["last_url"],
                last_title=existing["last_title"],
                summary=existing["summary"],
                created_at=existing["created_at"],
                updated_at=now,
            )
        )
    return _decode_browser_body(
        runtime_db.upsert_runtime_browser_body(
            body_id=f"browser-body-{uuid4().hex[:12]}",
            profile_name=profile_name,
            status="idle",
            active_task_id=active_task_id,
            active_flow_id=active_flow_id,
            created_at=now,
            updated_at=now,
        )
    )


def record_tab_snapshot(
    *,
    body_id: str,
    tab_id: str,
    url: str,
    title: str = "",
    status: str = "open",
    summary: str = "",
    selected: bool = False,
) -> dict[str, object] | None:
    body = get_browser_body(body_id)
    if body is None:
        return None
    tabs = list(body["tabs"])
    normalized_tab = {
        "tab_id": str(tab_id or "").strip(),
        "url": str(url or "").strip(),
        "title": str(title or "").strip(),
        "status": str(status or "open").strip(),
        "summary": str(summary or "").strip(),
    }
    replaced = False
    for index, item in enumerate(tabs):
        if str(item.get("tab_id") or "") == normalized_tab["tab_id"]:
            tabs[index] = normalized_tab
            replaced = True
            break
    if not replaced:
        tabs.append(normalized_tab)
    return update_browser_body(
        body_id,
        status="observing" if selected else body["status"],
        focused_tab_id=normalized_tab["tab_id"] if selected else body["focused_tab_id"],
        tabs=tabs,
        last_url=normalized_tab["url"],
        last_title=normalized_tab["title"],
        summary=normalized_tab["summary"] or body["summary"],
    )


def get_browser_body(body_id: str) -> dict[str, object] | None:
    body = runtime_db.get_runtime_browser_body(str(body_id or "").strip())
    if body is None:
        return None
    return _decode_browser_body(body)


def list_browser_bodies(limit: int = 10) -> list[dict[str, object]]:
    return [_decode_browser_body(item) for item in runtime_db.list_runtime_browser_bodies(limit=limit)]


def update_browser_body(
    body_id: str,
    *,
    status: str | None = None,
    active_task_id: str | None = None,
    active_flow_id: str | None = None,
    focused_tab_id: str | None = None,
    tabs: list[dict[str, object]] | None = None,
    last_url: str | None = None,
    last_title: str | None = None,
    summary: str | None = None,
) -> dict[str, object] | None:
    current = get_browser_body(body_id)
    if current is None:
        return None
    normalized_status = current["status"]
    if status is not None:
        candidate = str(status or "").strip().lower()
        normalized_status = candidate if candidate in _VALID_STATUSES else current["status"]
    now = datetime.now(UTC).isoformat()
    return _decode_browser_body(
        runtime_db.upsert_runtime_browser_body(
            body_id=current["body_id"],
            profile_name=current["profile_name"],
            status=normalized_status,
            active_task_id=str(active_task_id or current["active_task_id"]).strip(),
            active_flow_id=str(active_flow_id or current["active_flow_id"]).strip(),
            focused_tab_id=str(focused_tab_id or current["focused_tab_id"]).strip(),
            tabs_json=json.dumps(tabs if tabs is not None else current["tabs"], ensure_ascii=False, sort_keys=True),
            last_url=str(last_url or current["last_url"]).strip(),
            last_title=str(last_title or current["last_title"]).strip(),
            summary=str(summary or current["summary"]).strip(),
            created_at=current["created_at"],
            updated_at=now,
        )
    )


def _find_browser_body_by_profile(profile_name: str) -> dict[str, object] | None:
    for item in list_browser_bodies(limit=20):
        if str(item.get("profile_name") or "") == profile_name:
            return item
    return None


def _decode_browser_body(body: dict[str, object]) -> dict[str, object]:
    decoded = dict(body)
    raw_tabs = str(body.get("tabs_json") or "[]").strip() or "[]"
    try:
        decoded["tabs"] = json.loads(raw_tabs)
    except json.JSONDecodeError:
        decoded["tabs"] = []
    return decoded
