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


def _exec_tail_log(args: dict[str, Any]) -> dict[str, Any]:
    """Read recent journalctl lines for a systemd service.

    Lets the model verify behavior post-action ("did the restart actually work?")
    without falling back to a generic ``bash`` call. Caps lines and only allows
    -u <service> / -t <tag> filters so it can't be turned into an arbitrary
    journal scrape.
    """
    service = str(args.get("service") or "").strip()
    if not service:
        return {"status": "error", "error": "service is required"}
    if not all(c.isalnum() or c in "-_.@" for c in service):
        return {"status": "error", "error": "service name has invalid characters"}
    lines = max(1, min(int(args.get("lines") or 30), 200))
    try:
        result = subprocess.run(
            ["journalctl", "-u", service, "-n", str(lines), "--no-pager", "-o", "short-iso"],
            capture_output=True, text=True, timeout=10,
        )
        return {
            "status": "ok",
            "service": service,
            "lines": lines,
            "log": result.stdout[-12000:],
            "stderr": result.stderr[-500:] if result.returncode != 0 else "",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _exec_gpu_status(_args: dict[str, Any]) -> dict[str, Any]:
    """Snapshot of NVIDIA GPU state (memory, utilization, processes).

    Important for embodied awareness — Jarvis runs visible inference on GPU
    via Ollama, and knowing the card is at 95% VRAM should change his choice
    of model or his pacing of follow-up calls.
    """
    try:
        # Query the local GPU first; the Ollama host (10.0.0.25) is queried
        # only if the local machine has no NVIDIA driver. Both paths fall
        # through to a clear ``no-gpu`` status rather than an error so the
        # model can read the result and decide what to do.
        local = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if local.returncode != 0:
            return {"status": "ok", "host": "local", "available": False, "note": "nvidia-smi not available"}
        gpus = []
        for line in local.stdout.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 5:
                gpus.append({
                    "name": parts[0],
                    "memory_total_mb": int(parts[1]),
                    "memory_used_mb": int(parts[2]),
                    "memory_free_mb": int(parts[3]),
                    "utilization_pct": int(parts[4]),
                })
        return {"status": "ok", "host": "local", "available": True, "gpus": gpus}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _exec_run_pytest(args: dict[str, Any]) -> dict[str, Any]:
    """Run a specific pytest target so the model can verify behavior by test.

    Accepts a path or ``-k`` filter; both must be substrings of the repo's
    own ``tests/`` tree. Bounded by --maxfail=3 and a 60s wall clock so a
    runaway test doesn't lock the model into a long blocking call.
    """
    import os
    target = str(args.get("target") or "tests/").strip()
    k_filter = str(args.get("k") or "").strip()
    # Containment: target must start with tests/ and contain no shell metachars.
    if not target.startswith("tests/") or any(c in target for c in ";&|`$<>"):
        return {"status": "error", "error": "target must start with tests/ and have no shell metachars"}
    if k_filter and any(c in k_filter for c in ";&|`$<>"):
        return {"status": "error", "error": "k filter has invalid characters"}
    cmd = ["python", "-m", "pytest", target, "--maxfail=3", "-q", "--tb=short"]
    if k_filter:
        cmd += ["-k", k_filter]
    repo_root = os.environ.get("JARVIS_REPO_ROOT", "/media/projects/jarvis-v2")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, cwd=repo_root,
        )
        # Strip excessive output but keep the failure summary visible.
        out = (result.stdout + "\n" + result.stderr)[-8000:]
        return {
            "status": "ok",
            "target": target,
            "k": k_filter or None,
            "exit_code": result.returncode,
            "passed": result.returncode == 0,
            "output_tail": out,
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "pytest exceeded 60s wall clock"}
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
    {
        "type": "function",
        "function": {
            "name": "tail_log",
            "description": (
                "Read recent journalctl lines for a systemd service. Use this to "
                "verify the actual effect of an action (restart, config change) "
                "rather than guessing — read the log, then say what you see."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {"type": "string", "description": "Systemd service name, e.g. 'jarvis-api'."},
                    "lines": {"type": "integer", "description": "Number of recent lines (default 30, max 200)."},
                },
                "required": ["service"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gpu_status",
            "description": (
                "Snapshot of NVIDIA GPU memory and utilization on this host. "
                "Use it before launching heavy inference, or to explain a slow "
                "response. Returns no-gpu cleanly when nvidia-smi is unavailable."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_pytest",
            "description": (
                "Run a pytest target inside the Jarvis repo to verify behavior. "
                "Target must start with 'tests/'. Bounded by 60s wall clock and "
                "--maxfail=3 so a runaway test cannot hang you."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Test path under tests/, e.g. 'tests/test_visible_runs_capability_smoke.py'."},
                    "k": {"type": "string", "description": "Optional pytest -k filter expression."},
                },
                "required": ["target"],
            },
        },
    },
]
