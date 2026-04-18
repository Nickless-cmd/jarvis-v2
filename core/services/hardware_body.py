"""Hardware body — collects CPU/GPU/RAM/VRAM/disk/temp signals.

Gives Jarvis a physical sense of his machine state. Used by the affective
state renderer (body feeling) and heartbeat gating (pressure-aware action).

Cached for 30 seconds to avoid hammering nvidia-smi on every prompt build.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import time

logger = logging.getLogger(__name__)

_cache: dict[str, object] = {}
_cache_at: float = 0.0
_CACHE_TTL = 30.0


def get_hardware_state() -> dict[str, object]:
    """Return current hardware state. Cached for 30s. Never raises."""
    global _cache, _cache_at
    now = time.monotonic()
    if _cache and now - _cache_at < _CACHE_TTL:
        return _cache
    state = _collect()
    _cache = state
    _cache_at = now
    return state


def _collect() -> dict[str, object]:
    result: dict[str, object] = {}

    try:
        import psutil
        result["cpu_pct"] = round(psutil.cpu_percent(interval=0.1), 1)
        mem = psutil.virtual_memory()
        result["ram_pct"] = round(mem.percent, 1)
        result["ram_used_gb"] = round(mem.used / 1e9, 1)
        result["ram_total_gb"] = round(mem.total / 1e9, 1)
    except Exception:
        pass

    try:
        disk = shutil.disk_usage("/")
        result["disk_free_gb"] = round(disk.free / 1e9, 1)
    except Exception:
        pass

    try:
        import psutil
        temps = psutil.sensors_temperatures()
        if temps:
            all_readings = [e.current for entries in temps.values() for e in entries if e.current]
            if all_readings:
                result["cpu_temp_c"] = round(max(all_readings), 1)
    except Exception:
        pass

    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            timeout=2,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        gpus = []
        for i, line in enumerate(out.strip().splitlines()):
            parts = [x.strip() for x in line.split(",")]
            if len(parts) >= 4:
                vram_used = int(parts[1])
                vram_total = int(parts[2])
                gpus.append({
                    "index": i,
                    "util_pct": int(parts[0]),
                    "vram_used_mb": vram_used,
                    "vram_total_mb": vram_total,
                    "vram_pct": round(vram_used / vram_total * 100, 1) if vram_total else 0.0,
                    "temp_c": int(parts[3]),
                })
        if gpus:
            result["gpus"] = gpus
    except Exception:
        pass

    result["pressure"] = _compute_pressure(result)
    result.update(_somatic_overlay(result))
    return result


def _somatic_overlay(state: dict[str, object]) -> dict[str, object]:
    try:
        from core.runtime.circadian_state import get_circadian_context

        ctx = get_circadian_context()
    except Exception:
        ctx = {}

    energy_level = str(ctx.get("energy_level") or "")
    clock_phase = str(ctx.get("clock_phase") or "")
    drain_score = float(ctx.get("drain_score") or 0.0)
    pressure = str(state.get("pressure") or "low")
    return {
        "energy_level": energy_level,
        "clock_phase": clock_phase,
        "drain_label": str(ctx.get("drain_label") or ""),
        "drain_score": round(drain_score, 2),
        "energy_budget": _derive_energy_budget(energy_level, drain_score, pressure),
        "circadian_preference": _derive_circadian_preference(clock_phase),
        "wake_state": _derive_wake_state(clock_phase, energy_level),
    }


def _compute_pressure(state: dict[str, object]) -> str:
    """Compute overall pressure: low / medium / high / critical."""
    score = 0

    cpu = float(state.get("cpu_pct") or 0)
    if cpu > 90:
        score += 3
    elif cpu > 70:
        score += 1

    ram = float(state.get("ram_pct") or 0)
    if ram > 92:
        score += 4
    elif ram > 85:
        score += 2
    elif ram > 75:
        score += 1

    disk_free = float(state.get("disk_free_gb") or 999)
    if disk_free < 1:
        score += 4
    elif disk_free < 5:
        score += 2

    cpu_temp = float(state.get("cpu_temp_c") or 0)
    if cpu_temp > 90:
        score += 3
    elif cpu_temp > 80:
        score += 1

    for gpu in state.get("gpus") or []:
        gpu_temp = float(gpu.get("temp_c") or 0)
        if gpu_temp > 85:
            score += 3
        elif gpu_temp > 75:
            score += 1
        vram_pct = float(gpu.get("vram_pct") or 0)
        if vram_pct > 95:
            score += 2
        elif vram_pct > 85:
            score += 1

    if score >= 6:
        return "critical"
    if score >= 3:
        return "high"
    if score >= 1:
        return "medium"
    return "low"


def _derive_energy_budget(energy_level: str, drain_score: float, pressure: str) -> int:
    base = {
        "høj": 88,
        "medium": 68,
        "lav": 42,
        "udmattet": 18,
    }.get(energy_level, 55)
    pressure_penalty = {
        "low": 0,
        "medium": 8,
        "high": 18,
        "critical": 32,
    }.get(pressure, 0)
    budget = int(round(base - (drain_score * 20.0) - pressure_penalty))
    return max(0, min(100, budget))


def _derive_circadian_preference(clock_phase: str) -> str:
    if clock_phase in {"tidlig morgen", "formiddag", "middag"}:
        return "morgen"
    return "aften"


def _derive_wake_state(clock_phase: str, energy_level: str) -> str:
    if clock_phase == "nat" or energy_level == "udmattet":
        return "compacting"
    if clock_phase == "tidlig morgen":
        return "waking up"
    if clock_phase in {"sen eftermiddag", "aften"} and energy_level in {"lav", "udmattet"}:
        return "winding down"
    return "alert"
