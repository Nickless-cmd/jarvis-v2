"""Lazy tool schema loader for visible-lane tool pruning."""

from __future__ import annotations

from copy import deepcopy

from core.tools.simple_tools_definitions import TOOL_DEFINITIONS


def _tool_name(tool_def: dict) -> str:
    fn = tool_def.get("function") or tool_def
    return str(fn.get("name") or tool_def.get("name") or "")


def _tool_load_more_tools(arguments: dict) -> dict:
    """Resolve tools to add to the next round and return their full schemas."""
    import json as _json

    from core.eventbus.bus import event_bus
    from core.runtime.db import connect

    names = list(arguments.get("names") or [])
    query = (arguments.get("query") or "").strip()

    all_by_name = {
        _tool_name(d): d
        for d in (TOOL_DEFINITIONS or [])
        if _tool_name(d)
    }

    resolved: list[str] = []
    unknown: list[str] = []
    for n in names:
        if n in all_by_name:
            resolved.append(n)
        else:
            unknown.append(n)

    if query and not resolved:
        try:
            from core.services.tool_embeddings import top_k_similar
            hits = top_k_similar(query, k=10)
            resolved = [n for n, _ in hits if n in all_by_name][:5]
        except Exception:
            resolved = []

    if not resolved and unknown:
        return {
            "status": "error",
            "error": f"tools not found: {unknown}. Use names from the TOOL CATALOG.",
        }

    if not resolved:
        return {
            "status": "ok",
            "added": [],
            "message": "no strong matches",
            "tool_definitions": [],
            "schemas": [],
        }

    try:
        event_bus.publish("tool_router.load_more_fired", {
            "requested_names": names,
            "requested_query": query,
            "resolved_names": resolved,
        })
    except Exception:
        pass

    try:
        with connect() as c:
            c.execute(
                "INSERT INTO tool_router_load_more("
                "requested_names_json, requested_query, resolved_names_json, created_at) "
                "VALUES (?,?,?, datetime('now'))",
                (_json.dumps(names), query, _json.dumps(resolved)),
            )
            c.commit()
    except Exception:
        pass

    tool_definitions = [deepcopy(all_by_name[n]) for n in resolved if n in all_by_name]
    schemas: list[dict] = []
    for d in tool_definitions:
        fn = d.get("function") or d
        schemas.append(
            {
                "name": fn.get("name"),
                "description": fn.get("description"),
                "parameters": fn.get("parameters"),
            }
        )

    return {
        "status": "ok",
        "added": resolved,
        "schemas": schemas,
        "tool_definitions": tool_definitions,
        "message": (
            f"Added {len(resolved)} tool(s). Full schema below — call directly "
            "using exactly these parameter names; do not guess."
        ),
    }
