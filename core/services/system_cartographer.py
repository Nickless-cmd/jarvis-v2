"""System Cartographer — broad map of Jarvis' runtime and inner layers.

This is wider than the Agency Map vision edges. It inventories code/runtime
surfaces so Jarvis can ask "what exists in me, what emits, what is visible, and
what is probably still dark?"
"""
from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]

_PUBLISH_RE = re.compile(r"event_bus\.publish\(\s*[\"']([^\"']+)[\"']")
_EMIT_RE = re.compile(r"emit\(\s*[\"']([^\"']+)[\"']")
_SURFACE_RE = re.compile(r"def\s+(build_[a-zA-Z0-9_]*surface)\s*\(")
_TOOL_RE = re.compile(r"[\"']name[\"']\s*:\s*[\"']([^\"']+)[\"']")


def build_system_cartographer_surface() -> dict[str, Any]:
    files = _service_files()
    services = [_service_node(path, text) for path, text in files.items()]
    services.sort(key=lambda item: str(item["id"]))
    daemons = _daemon_nodes()
    surfaces = _surface_nodes(services)
    event_families = _event_family_nodes(services)
    tool_count = _tool_count()
    edges = _edges(services=services, daemons=daemons, surfaces=surfaces, event_families=event_families)
    dark_edges = _dark_edges(services)
    return {
        "fetchedAt": datetime.now(UTC).isoformat(),
        "mode": "system-cartographer-v1",
        "summary": {
            "services": len(services),
            "daemons": len(daemons),
            "surfaces": len(surfaces),
            "event_families": len(event_families),
            "edges": len(edges),
            "dark_edges": len(dark_edges),
            "tools": tool_count,
        },
        "nodes": {
            "services": services,
            "daemons": daemons,
            "surfaces": surfaces,
            "event_families": event_families,
        },
        "edges": edges,
        "darkEdges": dark_edges,
        "notes": [
            "Phase 1 is code/runtime inventory, not proof of causal influence.",
            "Eventbus is the right evidence stream; a daemon is the right mapper.",
            "Next phase should correlate event families with causal_edges and MC surfaces.",
        ],
    }


def _service_files() -> dict[str, str]:
    root = _REPO_ROOT / "core" / "services"
    result: dict[str, str] = {}
    for path in root.glob("*.py"):
        if path.name.startswith("__"):
            continue
        try:
            result[str(path.relative_to(_REPO_ROOT))] = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except Exception:
            continue
    return result


def _service_node(path: str, text: str) -> dict[str, Any]:
    name = Path(path).stem
    publishes = sorted(set(_PUBLISH_RE.findall(text)) | set(_EMIT_RE.findall(text)))
    surfaces = sorted(set(_SURFACE_RE.findall(text)))
    imports_eventbus = "event_bus" in text or "core.eventbus" in text
    uses_llm = "daemon_llm_call" in text or "execute_public_safe_cheap_lane" in text
    uses_db = "core.runtime.db" in text or "connect()" in text
    reads_state = "load_json(" in text or "state_store" in text
    writes_state = "save_json(" in text or "state_store" in text
    return {
        "id": name,
        "path": path,
        "kind": _classify_service(name=name, text=text),
        "surface_count": len(surfaces),
        "surfaces": surfaces[:12],
        "publishes_count": len(publishes),
        "publishes": publishes[:16],
        "uses": {
            "eventbus": imports_eventbus,
            "llm": uses_llm,
            "db": uses_db,
            "state_store": reads_state or writes_state,
        },
    }


def _daemon_nodes() -> list[dict[str, Any]]:
    try:
        from core.services import daemon_manager

        states = daemon_manager.get_all_daemon_states()
        registry = getattr(daemon_manager, "_REGISTRY", {})
    except Exception:
        return []
    result = []
    for item in states:
        name = str(item.get("name") or "")
        reg = registry.get(name, {}) if isinstance(registry, dict) else {}
        result.append({
            "id": name,
            "module": str(reg.get("module") or ""),
            "enabled": bool(item.get("enabled")),
            "cadence_minutes": item.get("effective_cadence_minutes"),
            "last_run_at": item.get("last_run_at") or "",
            "description": item.get("description") or "",
        })
    return result


def _surface_nodes(services: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for service in services:
        for surface in service.get("surfaces") or []:
            nodes.append({
                "id": f"{service['id']}::{surface}",
                "service": service["id"],
                "name": surface,
            })
    return nodes


def _event_family_nodes(services: list[dict[str, Any]]) -> list[dict[str, Any]]:
    families: dict[str, int] = {}
    for service in services:
        for kind in service.get("publishes") or []:
            family = str(kind).split(".", 1)[0]
            families[family] = families.get(family, 0) + 1
    return [
        {"id": family, "publish_markers": count}
        for family, count in sorted(families.items())
    ]


def _edges(
    *,
    services: list[dict[str, Any]],
    daemons: list[dict[str, Any]],
    surfaces: list[dict[str, Any]],
    event_families: list[dict[str, Any]],
) -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    service_ids = {str(s["id"]) for s in services}
    for daemon in daemons:
        module = str(daemon.get("module") or "")
        service = module.rsplit(".", 1)[-1]
        if service in service_ids:
            edges.append({"from": f"daemon:{daemon['id']}", "to": f"service:{service}", "type": "runs"})
    for surface in surfaces:
        edges.append({"from": f"service:{surface['service']}", "to": f"surface:{surface['name']}", "type": "exposes"})
    families = {str(item["id"]) for item in event_families}
    for service in services:
        for kind in service.get("publishes") or []:
            family = str(kind).split(".", 1)[0]
            if family in families:
                edges.append({"from": f"service:{service['id']}", "to": f"event:{family}", "type": "publishes"})
    return edges[:1200]


def _dark_edges(services: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dark: list[dict[str, Any]] = []
    for service in services:
        uses = service.get("uses") or {}
        if (uses.get("db") or uses.get("state_store") or service.get("publishes_count")) and not service.get("surface_count"):
            dark.append({
                "service": service["id"],
                "path": service["path"],
                "reason": "runtime/state/event influence with no local build_*surface marker",
                "kind": service["kind"],
            })
    dark.sort(key=lambda item: (str(item["kind"]), str(item["service"])))
    return dark[:80]


def _tool_count() -> int:
    path = _REPO_ROOT / "core" / "tools" / "simple_tools.py"
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return 0
    return len(set(_TOOL_RE.findall(text)))


def _classify_service(*, name: str, text: str) -> str:
    lowered = f"{name}\n{text[:1000]}".lower()
    if "daemon" in lowered:
        return "daemon"
    if "signal" in lowered or "tracking" in lowered:
        return "signal"
    if "memory" in lowered or "brain" in lowered:
        return "memory"
    if "executive" in lowered or "action" in lowered or "tool" in lowered:
        return "action"
    if "surface" in lowered or "mission control" in lowered:
        return "surface"
    return "service"
