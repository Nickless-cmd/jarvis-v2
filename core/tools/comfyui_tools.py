"""ComfyUI integration tools for Jarvis.

Talks to the local ComfyUI instance on localhost:8188 via its REST API.

Tools:
  comfyui_status   — system stats + queue status
  comfyui_workflow — submit a workflow/prompt for execution
  comfyui_history  — get execution history and results
  comfyui_objects  — list available node types / models
"""
from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from typing import Any

logger = logging.getLogger(__name__)

COMFYUI_HOST = "http://127.0.0.1:8188"
_TIMEOUT_SECONDS = 30


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _comfy_get(path: str, *, host: str = COMFYUI_HOST) -> dict[str, Any]:
    """GET from ComfyUI API, return parsed JSON."""
    url = f"{host}{path}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        return {"status": "error", "error": f"ComfyUI not reachable: {exc.reason}"}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _comfy_post(path: str, data: dict[str, Any], *, host: str = COMFYUI_HOST) -> dict[str, Any]:
    """POST JSON to ComfyUI API, return parsed JSON."""
    url = f"{host}{path}"
    try:
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        return {"status": "error", "error": f"ComfyUI not reachable: {exc.reason}"}
    except urllib.error.HTTPError as exc:
        body_text = ""
        try:
            body_text = exc.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        return {"status": "error", "error": f"HTTP {exc.code}: {body_text}"}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# ---------------------------------------------------------------------------
# Executor functions
# ---------------------------------------------------------------------------

def _exec_comfyui_status(args: dict[str, Any]) -> dict[str, Any]:
    """Get ComfyUI system stats and queue status."""
    stats = _comfy_get("/system_stats")
    if stats.get("status") == "error":
        return stats

    queue = _comfy_get("/queue")
    if queue.get("status") == "error":
        return queue

    return {
        "status": "ok",
        "system": stats.get("system", {}),
        "devices": stats.get("devices", []),
        "queue_running": queue.get("queue_running", []),
        "queue_pending": queue.get("queue_pending", []),
    }


def _exec_comfyui_workflow(args: dict[str, Any]) -> dict[str, Any]:
    """Submit a ComfyUI workflow for execution.

    Args:
        prompt: The workflow dict (node graph) to submit.
        client_id: Optional client ID for websocket tracking.
    """
    prompt = args.get("prompt")
    if not prompt:
        return {"status": "error", "error": "prompt (workflow dict) is required"}

    # Accept string or dict
    if isinstance(prompt, str):
        try:
            prompt = json.loads(prompt)
        except json.JSONDecodeError as exc:
            return {"status": "error", "error": f"Invalid JSON in prompt: {exc}"}

    client_id = args.get("client_id", "jarvis")

    result = _comfy_post("/prompt", {"prompt": prompt, "client_id": client_id})
    if result.get("status") == "error":
        return result

    return {
        "status": "ok",
        "prompt_id": result.get("prompt_id", ""),
        "number": result.get("number", 0),
        "node_errors": result.get("node_errors", {}),
    }


def _exec_comfyui_history(args: dict[str, Any]) -> dict[str, Any]:
    """Get ComfyUI execution history.

    Args:
        prompt_id: Optional specific prompt ID to look up.
        limit: Max entries to return (default 5, max 20).
    """
    prompt_id = args.get("prompt_id", "")
    limit = min(int(args.get("limit", 5)), 20)

    if prompt_id:
        history = _comfy_get(f"/history/{prompt_id}")
        if history.get("status") == "error":
            return history
        # history is a dict keyed by prompt_id
        entry = history.get(prompt_id, history)
        return {"status": "ok", "history": entry}

    history = _comfy_get("/history")
    if history.get("status") == "error":
        return history

    # history is a dict keyed by prompt_id — take last N
    if isinstance(history, dict):
        items = list(history.items())[-limit:]
        return {"status": "ok", "count": len(items), "history": dict(items)}

    return {"status": "ok", "history": history}


def _exec_comfyui_objects(args: dict[str, Any]) -> dict[str, Any]:
    """List available ComfyUI node types / models.

    Args:
        node_type: Optional specific node class to inspect (e.g. 'CheckpointLoaderSimple').
    """
    node_type = args.get("node_type", "")

    objects = _comfy_get("/object_info")
    if objects.get("status") == "error":
        return objects

    if node_type:
        info = objects.get(node_type)
        if info is None:
            available = list(objects.keys())[:50]
            return {
                "status": "error",
                "error": f"Node type '{node_type}' not found",
                "available_sample": available,
                "total_available": len(objects.keys()),
            }
        return {"status": "ok", "node_type": node_type, "info": info}

    # Return summary of all available node types
    node_names = sorted(objects.keys())
    return {
        "status": "ok",
        "total_nodes": len(node_names),
        "node_types": node_names,
    }


# ---------------------------------------------------------------------------
# Tool definitions (Ollama-compatible JSON schemas)
# ---------------------------------------------------------------------------

COMFYUI_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "comfyui_status",
            "description": "Get ComfyUI system status: GPU/VRAM info, queue running/pending jobs. Use to check if ComfyUI is alive and capacity.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "comfyui_workflow",
            "description": "Submit a ComfyUI workflow (node graph) for execution. The prompt dict defines nodes and connections.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "JSON string of the ComfyUI workflow (node graph). Will be parsed as JSON if string.",
                    },
                    "client_id": {
                        "type": "string",
                        "description": "Optional client ID for websocket tracking. Default: 'jarvis'.",
                    },
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "comfyui_history",
            "description": "Get ComfyUI execution history. Returns completed job results including output images.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt_id": {
                        "type": "string",
                        "description": "Specific prompt ID to look up. Omit for recent history.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max history entries to return (default 5, max 20).",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "comfyui_objects",
            "description": "List available ComfyUI node types and models. Pass node_type to inspect a specific node's inputs/outputs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_type": {
                        "type": "string",
                        "description": "Specific node class to inspect (e.g. 'CheckpointLoaderSimple', 'KSampler'). Omit for all.",
                    },
                },
            },
        },
    },
]