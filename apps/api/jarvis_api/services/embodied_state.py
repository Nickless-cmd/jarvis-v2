from __future__ import annotations

import os
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

_LAST_EMBODIED_STATE: dict[str, object] | None = None
_RECOVERY_WINDOW = timedelta(minutes=15)


def build_embodied_state_surface() -> dict[str, object]:
    global _LAST_EMBODIED_STATE

    facts = collect_host_facts()
    surface = build_embodied_state_from_facts(
        facts,
        previous=_LAST_EMBODIED_STATE,
    )
    _LAST_EMBODIED_STATE = surface
    return surface


def build_embodied_state_from_facts(
    facts: dict[str, object],
    *,
    previous: dict[str, object] | None = None,
) -> dict[str, object]:
    sampled_at = _parse_iso(facts.get("sampled_at")) or datetime.now(UTC)
    built_at = datetime.now(UTC)
    freshness_seconds = max(int((built_at - sampled_at).total_seconds()), 0)

    cpu = _build_cpu_fact(facts)
    memory = _build_memory_fact(facts)
    disk = _build_disk_fact(facts)
    thermal = _build_thermal_fact(facts)
    facts_surface = {
        "cpu": cpu,
        "memory": memory,
        "disk": disk,
        "thermal": thermal,
    }

    primary_state = _derive_primary_state(facts_surface)
    recovery_state = _derive_recovery_state(
        previous=previous,
        current_primary_state=primary_state,
        built_at=built_at,
    )
    embodied_state = "recovering" if recovery_state == "recovering" else primary_state
    strain_level = _strain_level_for_state(primary_state)
    stability = "degraded" if primary_state == "degraded" else "stable"

    active_signals = []
    for label, item in facts_surface.items():
        bucket = str(item.get("bucket") or "unavailable")
        if bucket not in {"steady", "unavailable"}:
            active_signals.append(f"{label}:{bucket}")

    return {
        "state": embodied_state,
        "primary_state": primary_state,
        "strain_level": strain_level,
        "recovery_state": recovery_state,
        "stability": stability,
        "summary": (
            f"{embodied_state} host/body state"
            if not active_signals
            else f"{embodied_state} host/body state from {', '.join(active_signals)}"
        ),
        "freshness": {
            "sampled_at": sampled_at.isoformat(),
            "built_at": built_at.isoformat(),
            "age_seconds": freshness_seconds,
            "state": "fresh" if freshness_seconds <= 15 else "stale",
        },
        "facts": facts_surface,
        "seam_usage": {
            "runtime_self_model": True,
            "mission_control_runtime_truth": True,
            "heartbeat_context": True,
            "heartbeat_prompt_grounding": True,
        },
        "authority": "authoritative",
        "visibility": "internal-only",
        "kind": "embodied-runtime-state",
    }


def build_embodied_state_prompt_section(
    surface: dict[str, object] | None = None,
) -> str | None:
    state = surface or build_embodied_state_surface()
    facts = state.get("facts") or {}
    cpu = facts.get("cpu") or {}
    memory = facts.get("memory") or {}
    disk = facts.get("disk") or {}
    thermal = facts.get("thermal") or {}
    freshness = state.get("freshness") or {}

    cpu_detail = f"{cpu.get('bucket') or 'unavailable'}"
    load_per_cpu = cpu.get("load_per_cpu")
    if isinstance(load_per_cpu, (int, float)):
        cpu_detail += f"(load/cpu={load_per_cpu:.2f})"

    memory_detail = f"{memory.get('bucket') or 'unavailable'}"
    pressure_ratio = memory.get("pressure_ratio")
    if isinstance(pressure_ratio, (int, float)):
        memory_detail += f"(pressure={pressure_ratio:.2f})"

    disk_detail = f"{disk.get('bucket') or 'unavailable'}"
    used_ratio = disk.get("used_ratio")
    if isinstance(used_ratio, (int, float)):
        disk_detail += f"(used={used_ratio:.2f})"

    thermal_detail = f"{thermal.get('bucket') or 'unavailable'}"
    celsius = thermal.get("celsius")
    if isinstance(celsius, (int, float)):
        thermal_detail += f"({celsius:.0f}C)"

    guidance = (
        "Prefer bounded noop/ping over extra internal work while host/body state is strained or degraded."
        if state.get("primary_state") in {"strained", "degraded"}
        else "Host/body state is not currently a suppressive factor."
    )

    return "\n".join(
        [
            "Embodied host state (authoritative runtime truth, internal-only):",
            (
                f"- state={state.get('state') or 'unknown'}"
                f" | primary={state.get('primary_state') or 'unknown'}"
                f" | strain={state.get('strain_level') or 'unknown'}"
                f" | recovery={state.get('recovery_state') or 'steady'}"
                f" | freshness={freshness.get('state') or 'unknown'}"
            ),
            f"- cpu={cpu_detail} | memory={memory_detail} | disk={disk_detail} | thermal={thermal_detail}",
            f"- guidance={guidance}",
        ]
    )


def collect_host_facts() -> dict[str, object]:
    sampled_at = datetime.now(UTC).isoformat()
    load_1m: float | None = None
    cpu_count = os.cpu_count() or 1
    load_source = "unavailable"
    try:
        load_1m = float(os.getloadavg()[0])
        load_source = "os.getloadavg"
    except (AttributeError, OSError):
        pass

    meminfo = _read_meminfo()
    memory_source = "proc-meminfo" if meminfo else "unavailable"

    disk_total = None
    disk_free = None
    disk_source = "unavailable"
    try:
        usage = shutil.disk_usage(Path.cwd())
        disk_total = int(usage.total)
        disk_free = int(usage.free)
        disk_source = "shutil.disk_usage"
    except OSError:
        pass

    thermal = _read_thermal_celsius()
    thermal_source = "sysfs-thermal" if thermal is not None else "unavailable"

    return {
        "sampled_at": sampled_at,
        "cpu_count": cpu_count,
        "load_1m": load_1m,
        "load_source": load_source,
        "memory_total_bytes": meminfo.get("MemTotal"),
        "memory_available_bytes": meminfo.get("MemAvailable"),
        "memory_source": memory_source,
        "disk_total_bytes": disk_total,
        "disk_free_bytes": disk_free,
        "disk_source": disk_source,
        "temperature_celsius": thermal,
        "thermal_source": thermal_source,
    }


def _build_cpu_fact(facts: dict[str, object]) -> dict[str, object]:
    load = facts.get("load_1m")
    cpu_count = max(int(facts.get("cpu_count") or 1), 1)
    if not isinstance(load, (int, float)):
        return {"bucket": "unavailable", "source": str(facts.get("load_source") or "unavailable")}

    per_cpu = float(load) / cpu_count
    return {
        "bucket": _bucket_from_thresholds(per_cpu, (0.7, 1.0, 1.3)),
        "load_1m": round(float(load), 2),
        "cpu_count": cpu_count,
        "load_per_cpu": round(per_cpu, 2),
        "source": str(facts.get("load_source") or "unknown"),
    }


def _build_memory_fact(facts: dict[str, object]) -> dict[str, object]:
    total = facts.get("memory_total_bytes")
    available = facts.get("memory_available_bytes")
    if not isinstance(total, int) or not isinstance(available, int) or total <= 0:
        return {"bucket": "unavailable", "source": str(facts.get("memory_source") or "unavailable")}

    pressure_ratio = 1.0 - (available / total)
    return {
        "bucket": _bucket_from_thresholds(pressure_ratio, (0.7, 0.82, 0.92)),
        "pressure_ratio": round(pressure_ratio, 3),
        "total_bytes": total,
        "available_bytes": available,
        "source": str(facts.get("memory_source") or "unknown"),
    }


def _build_disk_fact(facts: dict[str, object]) -> dict[str, object]:
    total = facts.get("disk_total_bytes")
    free = facts.get("disk_free_bytes")
    if not isinstance(total, int) or not isinstance(free, int) or total <= 0:
        return {"bucket": "unavailable", "source": str(facts.get("disk_source") or "unavailable")}

    used_ratio = 1.0 - (free / total)
    return {
        "bucket": _bucket_from_thresholds(used_ratio, (0.75, 0.88, 0.95)),
        "used_ratio": round(used_ratio, 3),
        "total_bytes": total,
        "free_bytes": free,
        "source": str(facts.get("disk_source") or "unknown"),
    }


def _build_thermal_fact(facts: dict[str, object]) -> dict[str, object]:
    celsius = facts.get("temperature_celsius")
    if not isinstance(celsius, (int, float)):
        return {"bucket": "unavailable", "source": str(facts.get("thermal_source") or "unavailable")}

    return {
        "bucket": _bucket_from_thresholds(float(celsius), (70.0, 82.0, 90.0)),
        "celsius": round(float(celsius), 1),
        "source": str(facts.get("thermal_source") or "unknown"),
    }


def _derive_primary_state(facts_surface: dict[str, dict[str, object]]) -> str:
    severities = []
    for item in facts_surface.values():
        bucket = str(item.get("bucket") or "unavailable")
        if bucket != "unavailable":
            severities.append(_severity(bucket))
    if not severities:
        return "steady"

    highest = max(severities)
    strained_count = sum(1 for value in severities if value >= 2)
    loaded_count = sum(1 for value in severities if value >= 1)

    if highest >= 3:
        return "degraded"
    if strained_count >= 1:
        return "strained"
    if loaded_count >= 1:
        return "loaded"
    return "steady"


def _derive_recovery_state(
    *,
    previous: dict[str, object] | None,
    current_primary_state: str,
    built_at: datetime,
) -> str:
    if previous is None:
        return "steady"

    previous_state = str(previous.get("primary_state") or previous.get("state") or "steady")
    previous_built_at = _parse_iso((previous.get("freshness") or {}).get("built_at"))
    if previous_state not in {"strained", "degraded"}:
        return "steady"
    if current_primary_state not in {"steady", "loaded"}:
        return "steady"
    if previous_built_at is None or (built_at - previous_built_at) > _RECOVERY_WINDOW:
        return "steady"
    return "recovering"


def _read_meminfo() -> dict[str, int]:
    path = Path("/proc/meminfo")
    if not path.exists():
        return {}

    result: dict[str, int] = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if ":" not in line:
                continue
            key, raw_value = line.split(":", 1)
            number = raw_value.strip().split()[0]
            if number.isdigit():
                result[key] = int(number) * 1024
    except OSError:
        return {}
    return result


def _read_thermal_celsius() -> float | None:
    temps: list[float] = []
    for path in Path("/sys/class/thermal").glob("thermal_zone*/temp"):
        try:
            raw = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        try:
            value = float(raw)
        except ValueError:
            continue
        if value > 1000:
            value = value / 1000.0
        if value > 0:
            temps.append(value)
    if not temps:
        return None
    return max(temps)


def _bucket_from_thresholds(value: float, thresholds: tuple[float, float, float]) -> str:
    low, medium, high = thresholds
    if value < low:
        return "steady"
    if value < medium:
        return "loaded"
    if value < high:
        return "strained"
    return "degraded"


def _severity(bucket: str) -> int:
    return {
        "steady": 0,
        "loaded": 1,
        "strained": 2,
        "degraded": 3,
    }.get(bucket, 0)


def _strain_level_for_state(state: str) -> str:
    return {
        "steady": "low",
        "loaded": "elevated",
        "recovering": "easing",
        "strained": "high",
        "degraded": "critical",
    }.get(state, "low")


def _parse_iso(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
