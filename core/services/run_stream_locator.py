"""Locate replayable run streams across API/runtime process boundaries."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Lifecycle = Literal["running", "terminal", "stale_owner", "unknown"]
ProducerProcess = Literal["api", "runtime", "unknown"]

_TERMINAL = frozenset({"completed", "cancelled", "failed_terminal"})


@dataclass(frozen=True, slots=True)
class RunStreamLocation:
    run_id: str
    session_id: str
    lifecycle: Lifecycle
    producer_process: ProducerProcess
    local_available: bool
    journal_status: str


def _role(value: object) -> ProducerProcess:
    role = str(value or "").strip().lower()
    return role if role in {"api", "runtime"} else "unknown"


def _local_role() -> ProducerProcess:
    try:
        from core.services.central_xproc import process_role

        return _role(process_role())
    except Exception:  # role discovery is optional for process-local replay
        return "unknown"


def _unknown(run_id: str) -> RunStreamLocation:
    return RunStreamLocation(
        run_id=str(run_id or ""),
        session_id="",
        lifecycle="unknown",
        producer_process="unknown",
        local_available=False,
        journal_status="",
    )


def _from_record(run_id: str, record: dict) -> RunStreamLocation:
    from core.services import in_flight_runs as ifr

    status = str(record.get("status") or "running")
    if status in _TERMINAL:
        lifecycle: Lifecycle = "terminal"
    elif status == "running":
        owner = str(record.get("owner_proc") or "")
        alive = ifr.owner_still_alive(owner) if owner else None
        lifecycle = "stale_owner" if alive is False else "running"
    else:
        lifecycle = "stale_owner"
    return RunStreamLocation(
        run_id=str(record.get("run_id") or run_id),
        session_id=str(record.get("session_id") or ""),
        lifecycle=lifecycle,
        producer_process=_role(record.get("producer_process")),
        local_available=False,
        journal_status=status,
    )


def locate_run(run_id: str) -> RunStreamLocation:
    """Resolve one stable run ID without mutating either authority."""
    from core.services import in_flight_runs as ifr
    from core.services import run_event_log as rel

    requested = str(run_id or "").strip()
    if not requested:
        return _unknown(requested)
    local_session = rel.session_for_run(requested)
    record = ifr.get_record(requested)
    if local_session is not None:
        _frames, done, _next_idx = rel.read_from(requested, 0)
        return RunStreamLocation(
            run_id=requested,
            session_id=local_session,
            lifecycle="terminal" if done else "running",
            producer_process=_local_role(),
            local_available=True,
            journal_status=str((record or {}).get("status") or ""),
        )
    if record is not None:
        return _from_record(requested, record)
    return _unknown(requested)


def active_locations(max_idle_s: float = 1800.0) -> list[RunStreamLocation]:
    """All currently running streams, de-duplicated by stable run ID."""
    from core.services import in_flight_runs as ifr
    from core.services import run_event_log as rel

    locations: list[RunStreamLocation] = []
    seen: set[str] = set()
    for log_id in rel.aabne_run_ids(max_alder_s=max_idle_s):
        client_id = rel.klient_run_id(log_id)
        location = locate_run(client_id)
        if location.lifecycle == "running" and client_id not in seen:
            seen.add(client_id)
            locations.append(location)
    for record in ifr.levende_koersler(max_alder_s=max_idle_s):
        run_id = str(record.get("run_id") or "")
        if not run_id or run_id in seen:
            continue
        location = _from_record(run_id, record)
        if location.lifecycle == "running":
            seen.add(run_id)
            locations.append(location)
    return locations


def live_run_for_session(session_id: str) -> RunStreamLocation | None:
    """Newest authoritative live stream for a session, if one exists."""
    target = str(session_id or "").strip()
    if not target:
        return None
    from core.services import run_event_log as rel

    local_id = rel.active_run_for_session(target)
    if local_id:
        return locate_run(rel.klient_run_id(local_id))
    candidates = [item for item in active_locations() if item.session_id == target]
    return candidates[-1] if candidates else None
