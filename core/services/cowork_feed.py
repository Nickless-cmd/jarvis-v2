"""Cowork-feed: normaliserer items fra eksisterende kilder til én rolle-scopet
liste til cowork-dashboardet. INGEN FastAPI-afhængighed — ren + testbar.

Item-shape: {id, kind, title, detail, user_id, source, diff?}
 - kind: "initiative" | "capability" | "tool_intent" | "file_edit"
 - source: hvilket eksisterende approve/reject-endpoint der skal kaldes
"""
from __future__ import annotations

from typing import Any


def _initiative_items() -> list[dict[str, Any]]:
    """Afventende initiativ-forslag fra initiative_queue."""
    try:
        from core.services.initiative_queue import get_initiative_queue_state
        state = get_initiative_queue_state()
        return [dict(i) for i in (state.get("pending") or [])]
    except Exception:
        return []


def _capability_items() -> list[dict[str, Any]]:
    """Afventende capability-/tool-godkendelses-requests (Mission Control surface)."""
    try:
        from apps.api.jarvis_api.routes.mission_control import _capability_invocation_surface
        surface = _capability_invocation_surface()
        reqs = list(surface.get("recent_approval_requests") or [])
        return [dict(r) for r in reqs if str(r.get("status") or "") == "pending"]
    except Exception:
        return []


def _norm_initiative(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(raw.get("id") or raw.get("initiative_id") or ""),
        "kind": "initiative",
        "title": str(raw.get("title") or raw.get("summary") or "Initiativ"),
        "detail": str(raw.get("detail") or raw.get("rationale") or ""),
        "user_id": str(raw.get("user_id") or ""),
        "source": "initiative",
    }


def _norm_capability(raw: dict[str, Any]) -> dict[str, Any]:
    name = str(raw.get("capability_name") or raw.get("tool") or raw.get("capability_id") or "handling")
    kind = "file_edit" if raw.get("target_path") or raw.get("write_content") else (
        "tool_intent" if raw.get("command_text") else "capability"
    )
    item = {
        "id": str(raw.get("id") or raw.get("request_id") or raw.get("capability_id") or ""),
        "kind": kind,
        "title": name,
        "detail": str(raw.get("target_path") or raw.get("command_text") or raw.get("message") or ""),
        "user_id": str(raw.get("user_id") or ""),
        "source": "capability",
    }
    if raw.get("diff"):
        item["diff"] = str(raw.get("diff"))
    return item


def _proposal_items() -> list[dict[str, Any]]:
    """Afventende autonomy-proposals (prop-xxxxxx): commits, planer, prompt-
    ændringer m.m. som Jarvis har lagt til godkendelse. Owner-only."""
    try:
        from core.services.autonomy_proposal_queue import list_pending_proposals
        return [dict(p) for p in list_pending_proposals(limit=50)]
    except Exception:
        return []


def _norm_proposal(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(raw.get("proposal_id") or raw.get("id") or ""),
        "kind": "proposal",
        "title": str(raw.get("title") or raw.get("kind") or "Forslag"),
        "detail": str(raw.get("rationale") or raw.get("kind") or ""),
        # Owner-only: tom user_id → vises kun for owner (member-filter dropper dem).
        "user_id": "",
        "source": "proposal",
        "proposal_kind": str(raw.get("kind") or ""),
    }


def build_queue(*, user_id: str | None, is_owner: bool) -> list[dict[str, Any]]:
    """Saml + normalisér + rolle-scope den fulde godkendelses-kø."""
    items: list[dict[str, Any]] = []
    items += [_norm_proposal(r) for r in _proposal_items()]
    items += [_norm_initiative(r) for r in _initiative_items()]
    items += [_norm_capability(r) for r in _capability_items()]
    items = [i for i in items if i["id"]]
    if not is_owner:
        uid = str(user_id or "")
        items = [i for i in items if i["user_id"] == uid]
    return items


def _all_plans() -> list[dict[str, Any]]:
    """Alle planer fra plan_proposals (normaliseret med trin-progress)."""
    try:
        from core.services import plan_proposals
        data = plan_proposals._load_all()  # {plan_id: plan_dict}
        out: list[dict[str, Any]] = []
        for pid, p in (data or {}).items():
            steps = list(p.get("steps") or [])
            done = len([s for s in steps if str(s.get("status") or "") == "completed"])
            out.append({
                "plan_id": pid,
                "title": str(p.get("title") or p.get("goal") or "Plan"),
                "user_id": str(p.get("user_id") or ""),
                "status": str(p.get("status") or ""),
                "steps_done": done,
                "steps_total": len(steps),
            })
        return out
    except Exception:
        return []


def list_plans(*, user_id: str | None, is_owner: bool) -> list[dict[str, Any]]:
    plans = [
        {"id": p["plan_id"], "title": p["title"], "status": p.get("status", ""),
         "steps_done": int(p.get("steps_done") or 0), "steps_total": int(p.get("steps_total") or 0),
         "user_id": p.get("user_id", "")}
        for p in _all_plans()
    ]
    if not is_owner:
        uid = str(user_id or "")
        plans = [p for p in plans if p["user_id"] == uid]
    return plans


def _all_todos() -> list[dict[str, Any]]:
    """Alle todos på tværs af sessioner (agent_todos er session-keyed)."""
    try:
        from core.services.agent_todos import _load_all
        out: list[dict[str, Any]] = []
        for _sid, items in (_load_all() or {}).items():
            for t in items:
                out.append({
                    "id": str(t.get("id") or ""),
                    "content": str(t.get("content") or ""),
                    "status": str(t.get("status") or "pending"),
                })
        return out
    except Exception:
        return []


def list_todos_feed(*, user_id: str | None, is_owner: bool) -> list[dict[str, Any]]:
    """Todos til cowork. Owner ser alle; member får [] (todos er ikke user-
    attribuerede endnu — sandboxes i v2)."""
    if not is_owner:
        return []
    return [t for t in _all_todos() if t["id"] and t["content"]]


def _raw_channels() -> dict[str, Any]:
    """Konfigurerede kanaler (online = konfigureret/aktiv). Live connection-state
    ligger i gateway-processerne; v1 viser hvilke kanaler der er sat op."""
    chans: dict[str, Any] = {}
    try:
        from core.services.discord_config import is_discord_configured
        chans["discord"] = {"online": bool(is_discord_configured()), "unread": 0}
    except Exception:
        pass
    try:
        from core.runtime.secrets import read_runtime_key
        if read_runtime_key("telegram_bot_token"):
            chans["telegram"] = {"online": True, "unread": 0}
    except Exception:
        pass
    chans["webchat"] = {"online": True, "unread": 0}
    return chans


def channel_status() -> list[dict[str, Any]]:
    raw = _raw_channels()
    return [
        {"name": str(name), "online": bool(info.get("online")), "unread": int(info.get("unread") or 0)}
        for name, info in raw.items()
    ]
