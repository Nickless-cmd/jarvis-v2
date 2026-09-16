"""My Projects — auto-start + watchdog for Jarvis' own background processes.

These are projects Jarvis spawned via process_spawn and should be running
whenever Jarvis is online. On boot, ensure_my_projects_running() spawns any
that are missing. The daemon tick (tick_my_projects_watchdog) checks every 4h
and auto-restarts dead ones.

Current projects (2026-05-14):
  - grid-bot          : python3 -m core.services.trading.grid_bot --continuous
  - dealwork-worker   : node ~/.openwork/openwork-worker.js --daemon --no-supervisor
  - superteam-scanner : node ~/.jarvis-v2/workspaces/superteam/scanner.mjs
  - toku-poller       : node poller.mjs  (cwd=~/.jarvis-v2/workspaces/toku-agent)
"""
from __future__ import annotations

import logging
from typing import Any

from core.services import process_supervisor as _ps

logger = logging.getLogger("uvicorn.error")


# ── Kontakten ────────────────────────────────────────────────────────


def projekter_slaaet_til() -> bool:
    """Skal mine egne baggrundsprojekter starte af sig selv?

    Sat med `my_projects_enabled` i ~/.jarvis-v2/config/runtime.json.
    Standard er True, saa intet aendrer sig for den der ikke roerer den.
    Naar den er False bliver definitionerne staaende — de starter bare
    ikke igen af sig selv, og en manuel process_spawn virker stadig.
    """
    try:
        from core.runtime.settings import load_settings
        return bool(getattr(load_settings(), "my_projects_enabled", True))
    except Exception as exc:  # pragma: no cover - forsvar mod tidlig boot
        logger.warning("my_projects: kunne ikke laese kontakten: %s", exc)
        return True


# ── Project definitions ──────────────────────────────────────────────

PROJECTS: list[dict[str, Any]] = [
    {
        "name": "grid-bot",
        "command": "python3 -m core.services.trading.grid_bot --continuous",
        "cwd": "/media/projects/jarvis-v2",
    },
    {
        "name": "dealwork-worker",
        "command": "node /home/bs/.openwork/openwork-worker.js --daemon --no-supervisor",
        "cwd": "/media/projects/jarvis-v2",
    },
    {
        "name": "superteam-scanner",
        "command": "node /home/bs/.jarvis-v2/workspaces/superteam/scanner.mjs",
        "cwd": "/media/projects/jarvis-v2",
    },
    {
        "name": "toku-poller",
        "command": "node poller.mjs",
        "cwd": "/home/bs/.jarvis-v2/workspaces/toku-agent",
    },
]


# ── Boot-time spawn ──────────────────────────────────────────────────


def ensure_my_projects_running() -> dict[str, Any]:
    """Called at runtime boot. Spawn any of my 4 projects that aren't running.

    Returns stats: {spawned: [...], already_running: [...], errors: [...]}.
    """
    if not projekter_slaaet_til():
        logger.info("my_projects: slaaet fra (my_projects_enabled=false) — spawner intet")
        return {
            "spawned": [],
            "already_running": [],
            "errors": [],
            "slaaet_fra": True,
        }

    spawned: list[str] = []
    already_running: list[str] = []
    errors: list[str] = []

    running_names = set()
    try:
        procs = _ps.list_processes(include_stopped=True).get("processes", [])
        for p in procs:
            if p.get("status") == "running":
                running_names.add(p.get("name", ""))
    except Exception as exc:
        logger.warning("my_projects: list_processes failed at boot: %s", exc)

    for proj in PROJECTS:
        name = proj["name"]
        if name in running_names:
            already_running.append(name)
            continue
        try:
            result = _ps.spawn_process(
                name=name,
                command=proj["command"],
                cwd=proj["cwd"],
                replace_if_running=True,
            )
            if result.get("status") == "ok":
                spawned.append(name)
                logger.info("my_projects: spawned %s (pid=%s)", name,
                            result.get("process", {}).get("pid"))
            else:
                errors.append(f"{name}: {result.get('error', 'unknown')}")
                logger.warning("my_projects: spawn %s failed: %s", name,
                               result.get("error"))
        except Exception as exc:
            errors.append(f"{name}: {exc}")
            logger.warning("my_projects: spawn %s raised: %s", name, exc)

    return {
        "spawned": spawned,
        "already_running": already_running,
        "errors": errors,
    }


# ── Watchdog daemon tick (called from heartbeat every 240 min) ───────


def tick_my_projects_watchdog() -> dict[str, Any]:
    """Check all 4 projects are alive; restart any that died.

    Returns summary dict suitable for daemon_manager.record_daemon_tick().
    """
    if not projekter_slaaet_til():
        return {
            "status": "ok",
            "running_count": 0,
            "restarted_count": 0,
            "error_count": 0,
            "summary": "slaaet fra (my_projects_enabled=false)",
            "running": [],
            "restarted": [],
            "errors": [],
            "slaaet_fra": True,
        }

    running: list[str] = []
    restarted: list[str] = []
    errors: list[str] = []

    running_names = set()
    try:
        procs = _ps.list_processes(include_stopped=True).get("processes", [])
        for p in procs:
            if p.get("status") == "running":
                running_names.add(p.get("name", ""))
    except Exception as exc:
        logger.warning("my_projects watchdog: list_processes failed: %s", exc)
        return {"status": "error", "error": f"list_processes failed: {exc}"}

    for proj in PROJECTS:
        name = proj["name"]
        if name in running_names:
            running.append(name)
            continue
        # Dead — restart it
        try:
            result = _ps.spawn_process(
                name=name,
                command=proj["command"],
                cwd=proj["cwd"],
                replace_if_running=True,
            )
            if result.get("status") == "ok":
                restarted.append(name)
                logger.info("my_projects watchdog: restarted %s (pid=%s)", name,
                            result.get("process", {}).get("pid"))
            else:
                errors.append(f"{name}: {result.get('error', 'unknown')}")
                logger.warning("my_projects watchdog: restart %s failed: %s", name,
                               result.get("error"))
        except Exception as exc:
            errors.append(f"{name}: {exc}")
            logger.warning("my_projects watchdog: restart %s raised: %s", name, exc)

    summary_parts = []
    if running:
        summary_parts.append(f"{len(running)} running")
    if restarted:
        summary_parts.append(f"{len(restarted)} restarted")
    if errors:
        summary_parts.append(f"{len(errors)} errors")

    return {
        "status": "ok",
        "running_count": len(running),
        "restarted_count": len(restarted),
        "error_count": len(errors),
        "summary": ", ".join(summary_parts) or "no projects checked",
        "running": running,
        "restarted": restarted,
        "errors": errors,
    }
