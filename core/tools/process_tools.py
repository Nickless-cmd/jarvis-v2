"""Process and system health monitoring tools."""
from __future__ import annotations

import subprocess
from typing import Any


def _exec_service_status(args: dict[str, Any]) -> dict[str, Any]:
    name = str(args.get("name") or "").strip()
    if not name:
        return {"status": "error", "error": "name is required"}
    try:
        result = subprocess.run(
            ["systemctl", "is-active", name],
            capture_output=True, text=True, timeout=10,
        )
        state = result.stdout.strip()
        enabled_result = subprocess.run(
            ["systemctl", "is-enabled", name],
            capture_output=True, text=True, timeout=10,
        )
        enabled = enabled_result.stdout.strip()
        return {"status": "ok", "service": name, "active": state, "enabled": enabled, "running": state == "active"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _exec_process_list(args: dict[str, Any]) -> dict[str, Any]:
    filter_str = str(args.get("filter") or "").strip().lower()
    limit = min(int(args.get("limit") or 20), 100)
    try:
        import psutil
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status", "username"]):
            try:
                info = p.info
                if filter_str and filter_str not in info["name"].lower():
                    continue
                procs.append({
                    "pid": info["pid"],
                    "name": info["name"],
                    "cpu_pct": round(info["cpu_percent"] or 0, 1),
                    "mem_pct": round(info["memory_percent"] or 0, 2),
                    "status": info["status"],
                    "user": info["username"],
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        procs.sort(key=lambda x: x["cpu_pct"], reverse=True)
        return {"status": "ok", "processes": procs[:limit], "total_shown": min(len(procs), limit), "filter": filter_str or None}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _exec_disk_usage(args: dict[str, Any]) -> dict[str, Any]:
    path = str(args.get("path") or "/").strip()
    try:
        import psutil
        usage = psutil.disk_usage(path)
        partitions = []
        for p in psutil.disk_partitions(all=False):
            try:
                u = psutil.disk_usage(p.mountpoint)
                partitions.append({
                    "mountpoint": p.mountpoint,
                    "device": p.device,
                    "fstype": p.fstype,
                    "total_gb": round(u.total / 1e9, 2),
                    "used_gb": round(u.used / 1e9, 2),
                    "free_gb": round(u.free / 1e9, 2),
                    "percent": u.percent,
                })
            except (PermissionError, OSError):
                continue
        return {
            "status": "ok",
            "path": path,
            "total_gb": round(usage.total / 1e9, 2),
            "used_gb": round(usage.used / 1e9, 2),
            "free_gb": round(usage.free / 1e9, 2),
            "percent": usage.percent,
            "partitions": partitions,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _exec_memory_usage(args: dict[str, Any]) -> dict[str, Any]:
    try:
        import psutil
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            "status": "ok",
            "ram": {
                "total_gb": round(vm.total / 1e9, 2),
                "available_gb": round(vm.available / 1e9, 2),
                "used_gb": round(vm.used / 1e9, 2),
                "percent": vm.percent,
            },
            "swap": {
                "total_gb": round(swap.total / 1e9, 2),
                "used_gb": round(swap.used / 1e9, 2),
                "free_gb": round(swap.free / 1e9, 2),
                "percent": swap.percent,
            },
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


PROCESS_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "service_status",
            "description": "Check whether a systemd service is running on this machine.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Systemd service name, e.g. 'jarvis-api' or 'nginx'."},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "process_list",
            "description": "List active processes sorted by CPU usage, optionally filtered by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter": {"type": "string", "description": "Optional substring to filter process names."},
                    "limit": {"type": "integer", "description": "Max processes to return (default 20, max 100)."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "disk_usage",
            "description": "Show disk usage for a path and list all mounted partitions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to check (default '/')."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_usage",
            "description": "Show current RAM and swap usage on this machine.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
