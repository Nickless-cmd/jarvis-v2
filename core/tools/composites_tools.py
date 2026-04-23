"""Composite tools interface — self-extension for Jarvis.

composite_propose: draft a new tool as a sequence of existing ones
composite_list: see proposals and approved composites
composite_get: detail on one composite (steps, schema, status)
composite_invoke: call an approved composite by name
composite_approve: (restricted) mark a proposal as approved
composite_revoke: (restricted) retire an approved composite

Approval and revocation are gated: the handler expects created_by='user'
or equivalent. Jarvis can *propose* and *invoke*, but not approve his
own proposals — that's the whole point of the safety boundary.
"""
from __future__ import annotations

from typing import Any

from core.services import composite_tools


def _exec_composite_propose(args: dict[str, Any]) -> dict[str, Any]:
    name = str(args.get("name") or "").strip()
    description = str(args.get("description") or "").strip()
    input_schema = args.get("input_schema") or {}
    steps = args.get("steps") or []
    if not isinstance(input_schema, dict):
        return {"status": "error", "error": "input_schema must be an object"}
    if not isinstance(steps, list):
        return {"status": "error", "error": "steps must be an array"}
    created_by = str(args.get("created_by") or "jarvis").strip() or "jarvis"
    try:
        proposal = composite_tools.propose(
            name=name,
            description=description,
            input_schema=input_schema,
            steps=steps,
            created_by=created_by,
        )
    except ValueError as exc:
        return {"status": "error", "error": str(exc)}
    return {
        "status": "ok",
        "composite": proposal,
        "note": "Proposal saved with status='proposed'. A human must approve before it can be invoked.",
    }


def _exec_composite_list(args: dict[str, Any]) -> dict[str, Any]:
    status = args.get("status")
    status = str(status).strip().lower() if status else None
    if status == "all":
        status = None
    items = composite_tools.list_available(status=status)
    return {
        "status": "ok",
        "count": len(items),
        "composites": items,
        "stats": composite_tools.get_stats(),
    }


def _exec_composite_get(args: dict[str, Any]) -> dict[str, Any]:
    name = str(args.get("name") or "").strip()
    if not name:
        return {"status": "error", "error": "name is required"}
    composite = composite_tools.get(name)
    if composite is None:
        return {"status": "error", "error": "composite not found"}
    return {"status": "ok", "composite": composite}


def _exec_composite_invoke(args: dict[str, Any]) -> dict[str, Any]:
    name = str(args.get("name") or "").strip()
    if not name:
        return {"status": "error", "error": "name is required"}
    call_args = args.get("args") or {}
    if not isinstance(call_args, dict):
        return {"status": "error", "error": "args must be an object"}
    return composite_tools.invoke(name, call_args)


def _exec_composite_approve(args: dict[str, Any]) -> dict[str, Any]:
    name = str(args.get("name") or "").strip()
    approved_by = str(args.get("approved_by") or "").strip()
    if not name:
        return {"status": "error", "error": "name is required"}
    if not approved_by or approved_by == "jarvis":
        return {
            "status": "error",
            "error": "approved_by must be a human principal (not 'jarvis').",
        }
    result = composite_tools.approve(name, approved_by=approved_by)
    if result is None:
        return {"status": "error", "error": "composite not found"}
    return {"status": "ok", "composite": result}


def _exec_composite_revoke(args: dict[str, Any]) -> dict[str, Any]:
    name = str(args.get("name") or "").strip()
    if not name:
        return {"status": "error", "error": "name is required"}
    result = composite_tools.revoke(name)
    if result is None:
        return {"status": "error", "error": "composite not found"}
    return {"status": "ok", "composite": result}


COMPOSITE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "composite_propose",
            "description": (
                "Propose a new tool as a sequence of existing tool calls. "
                "Use when you notice yourself doing the same sequence of "
                "tool calls repeatedly — package it so you can call it "
                "as one unit next time. Args can reference {{input.X}} "
                "(params supplied at call time) or {{step_N.path}} / "
                "{{bind_name.path}} (results of earlier steps). No "
                "arbitrary Python — only composition of existing tools. "
                "A human must approve the proposal before it becomes "
                "callable via composite_invoke."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "lowercase snake_case identifier (3-64 chars).",
                    },
                    "description": {
                        "type": "string",
                        "description": "What this composite does and when to use it.",
                    },
                    "input_schema": {
                        "type": "object",
                        "description": "JSON Schema fragment describing params this composite accepts.",
                    },
                    "steps": {
                        "type": "array",
                        "description": "Ordered list of {tool, args, bind?} steps.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "tool": {"type": "string"},
                                "args": {"type": "object"},
                                "bind": {"type": "string"},
                            },
                            "required": ["tool", "args"],
                        },
                    },
                    "created_by": {
                        "type": "string",
                        "description": "Defaults to 'jarvis'.",
                    },
                },
                "required": ["name", "description", "input_schema", "steps"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "composite_list",
            "description": "List composites, optionally filtered by status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["proposed", "approved", "revoked", "all"],
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "composite_get",
            "description": "Full detail on one composite (steps, schema, status).",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "composite_invoke",
            "description": (
                "Call an approved composite by name with its declared args. "
                "Returns the per-step results and the final step's output."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "args": {"type": "object"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "composite_approve",
            "description": (
                "Approve a proposed composite so it becomes callable. "
                "approved_by must be a human principal — Jarvis cannot "
                "approve his own proposals."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "approved_by": {"type": "string"},
                },
                "required": ["name", "approved_by"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "composite_revoke",
            "description": "Retire an approved (or proposed) composite.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
    },
]


COMPOSITE_TOOL_HANDLERS: dict[str, Any] = {
    "composite_propose": _exec_composite_propose,
    "composite_list": _exec_composite_list,
    "composite_get": _exec_composite_get,
    "composite_invoke": _exec_composite_invoke,
    "composite_approve": _exec_composite_approve,
    "composite_revoke": _exec_composite_revoke,
}
