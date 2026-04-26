"""Verification tools — wrap "do then check" into one call.

Phase 2's self-correction nudges told Jarvis to verify before claiming done.
The previous turn proved he doesn't always read the status field afterward
— he hallucinates "skrevet" / "snapshot taget" without checking. The fix
is to give him verbs whose name *literally* says "verify": when he calls
``verify_file_contains`` he can't pretend the file is there if it isn't.

Three opinionated wrappers, each runs the check directly:

- verify_file_contains(path, expected_substring, must_exist=True)
- verify_service_active(name)
- verify_endpoint_responds(url, expected_status, timeout)

Each returns ``status: "ok"`` only when the assertion holds. ``status:
"failed"`` (not "error") when the check ran cleanly but the expectation
was wrong — this distinction matters because "failed" is the model's
own fault to report; "error" means the verification itself broke.
"""
from __future__ import annotations

import logging
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _exec_verify_file_contains(args: dict[str, Any]) -> dict[str, Any]:
    path = str(args.get("path") or "").strip()
    expected = str(args.get("expected_substring") or "")
    must_exist = bool(args.get("must_exist", True))
    if not path:
        return {"status": "error", "error": "path is required"}
    p = Path(path).expanduser()
    if not p.exists():
        if must_exist:
            return {"status": "failed", "path": str(p), "reason": "file does not exist"}
        return {"status": "ok", "path": str(p), "exists": False, "note": "file missing as expected"}
    try:
        size = p.stat().st_size
        # Cap read at 1 MB so a wild path doesn't pull a giant binary.
        with open(p, "rb") as fh:
            content = fh.read(1024 * 1024)
    except OSError as exc:
        return {"status": "error", "error": f"read failed: {exc}"}
    if not expected:
        return {"status": "ok", "path": str(p), "exists": True, "bytes": size, "note": "exists check only"}
    text = content.decode("utf-8", errors="replace")
    if expected in text:
        return {
            "status": "ok",
            "path": str(p),
            "exists": True,
            "bytes": size,
            "found_substring": True,
        }
    return {
        "status": "failed",
        "path": str(p),
        "exists": True,
        "bytes": size,
        "found_substring": False,
        "reason": "expected_substring not present in file",
        "preview": text[:300],
    }


def _exec_verify_service_active(args: dict[str, Any]) -> dict[str, Any]:
    name = str(args.get("name") or "").strip()
    if not name or not all(c.isalnum() or c in "-_.@" for c in name):
        return {"status": "error", "error": "name is required and must be a valid systemd service name"}
    try:
        result = subprocess.run(
            ["systemctl", "is-active", name],
            capture_output=True, text=True, timeout=5,
        )
        state = result.stdout.strip()
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
    if state == "active":
        return {"status": "ok", "service": name, "active": True}
    return {
        "status": "failed",
        "service": name,
        "active": False,
        "actual_state": state or "unknown",
        "reason": f"service is {state or 'unknown'}, expected active",
    }


def _exec_verify_endpoint_responds(args: dict[str, Any]) -> dict[str, Any]:
    url = str(args.get("url") or "").strip()
    expected = int(args.get("expected_status") or 200)
    timeout = float(args.get("timeout") or 5.0)
    if not url:
        return {"status": "error", "error": "url is required"}
    if not (url.startswith("http://") or url.startswith("https://")):
        return {"status": "error", "error": "url must be http:// or https://"}
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.getcode()
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception as exc:
        return {
            "status": "failed",
            "url": url,
            "actual_status": None,
            "reason": f"request failed: {exc}",
        }
    if code == expected:
        return {"status": "ok", "url": url, "actual_status": code}
    return {
        "status": "failed",
        "url": url,
        "actual_status": code,
        "expected_status": expected,
        "reason": f"got HTTP {code}, expected {expected}",
    }


VERIFY_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "verify_file_contains",
            "description": (
                "Read a file and assert it contains a substring. Use after "
                "any write/edit to PROVE the change landed before claiming "
                "done. Returns status='ok' when the file exists and contains "
                "the substring; 'failed' when the assertion is wrong (with "
                "a preview of what's actually there); 'error' only when the "
                "verification itself broke (e.g. permission denied)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute file path."},
                    "expected_substring": {"type": "string", "description": "Substring that must be present. Empty = existence check only."},
                    "must_exist": {"type": "boolean", "description": "If false, missing file counts as ok. Default true."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verify_service_active",
            "description": (
                "Assert a systemd service is in 'active' state. Use after a "
                "restart/install/start to prove the service is actually up."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Systemd service name."},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verify_endpoint_responds",
            "description": (
                "GET a URL and assert it returns the expected HTTP status "
                "(default 200). Use after starting/restarting a server to "
                "confirm it's actually serving."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full http(s) URL."},
                    "expected_status": {"type": "integer", "description": "Expected HTTP status (default 200)."},
                    "timeout": {"type": "number", "description": "Seconds to wait (default 5)."},
                },
                "required": ["url"],
            },
        },
    },
]
