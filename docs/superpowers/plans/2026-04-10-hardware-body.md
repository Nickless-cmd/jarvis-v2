# Hardware Body — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Jarvis can sense his hardware state (CPU/GPU/RAM/VRAM/disk/temp), feel it as body signals in his affective state, and act on it by gating expensive heartbeat actions when under pressure.

**Architecture:** New `hardware_body.py` service collects all hardware signals via psutil + nvidia-smi, computes a pressure level, and caches for 30s. Affective renderer includes hardware signals so the LLM expresses body pressure naturally. Heartbeat gating blocks the tick on "critical" pressure and downgrades execute→propose on "high" pressure.

**Tech Stack:** psutil (already installed in API env), nvidia-smi (available), `apps/api/jarvis_api/services/hardware_body.py` (new), `affective_state_renderer.py` (extend), `system_health.py` route (extend), `heartbeat_runtime.py` (2 injection points).

---

## Files

- Create: `apps/api/jarvis_api/services/hardware_body.py`
- Modify: `apps/api/jarvis_api/services/affective_state_renderer.py`
- Modify: `apps/api/jarvis_api/routes/system_health.py`
- Modify: `apps/api/jarvis_api/services/heartbeat_runtime.py` (2 places: line 5631 and line 3172)

---

### Task 1: hardware_body.py

**Files:**
- Create: `apps/api/jarvis_api/services/hardware_body.py`

- [ ] **Step 1: Write the full file**

  ```python
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
      return result


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
  ```

- [ ] **Step 2: Verify syntax**

  ```bash
  conda run -n ai python -m compileall apps/api/jarvis_api/services/hardware_body.py -q
  ```
  Expected: no output

- [ ] **Step 3: Smoke test**

  ```bash
  python -c "
  import sys; sys.path.insert(0, '.')
  from apps.api.jarvis_api.services.hardware_body import get_hardware_state
  import json
  print(json.dumps(get_hardware_state(), indent=2))
  "
  ```
  Expected: dict with cpu_pct, ram_pct, disk_free_gb, gpus list, pressure level.

- [ ] **Step 4: Commit**

  ```bash
  git add apps/api/jarvis_api/services/hardware_body.py
  git commit -m "feat: hardware_body — collect CPU/GPU/RAM/VRAM/disk/temp with pressure level"
  ```

---

### Task 2: Add hardware signals to affective renderer

**Files:**
- Modify: `apps/api/jarvis_api/services/affective_state_renderer.py`

Add hardware signals at the END of `_collect_signals()`, just before `return signals`:

- [ ] **Step 1: Add hardware block to `_collect_signals()`**

  In `affective_state_renderer.py`, find the line `return signals` at the end of `_collect_signals()` and add before it:

  ```python
      try:
          from apps.api.jarvis_api.services.hardware_body import get_hardware_state
          hw = get_hardware_state()
          if hw:
              if hw.get("cpu_pct") is not None:
                  signals["cpu_pct"] = hw["cpu_pct"]
              if hw.get("ram_pct") is not None:
                  signals["ram_pct"] = hw["ram_pct"]
              if hw.get("cpu_temp_c") is not None:
                  signals["cpu_temp_c"] = hw["cpu_temp_c"]
              if hw.get("gpus"):
                  signals["gpus"] = [
                      {
                          "util_pct": g["util_pct"],
                          "vram_pct": g["vram_pct"],
                          "temp_c": g["temp_c"],
                      }
                      for g in hw["gpus"]
                  ]
              if hw.get("pressure") and hw["pressure"] != "low":
                  signals["hardware_pressure"] = hw["pressure"]
      except Exception:
          pass
  ```

  Note: only include `hardware_pressure` when it's above "low" — neutral state doesn't need to be stated.

- [ ] **Step 2: Verify syntax**

  ```bash
  conda run -n ai python -m compileall apps/api/jarvis_api/services/affective_state_renderer.py -q
  ```
  Expected: no output

- [ ] **Step 3: Commit**

  ```bash
  git add apps/api/jarvis_api/services/affective_state_renderer.py
  git commit -m "feat: add hardware signals (CPU/GPU/RAM/temp/pressure) to affective renderer"
  ```

---

### Task 3: Extend system health API

**Files:**
- Modify: `apps/api/jarvis_api/routes/system_health.py`

- [ ] **Step 1: Replace `system_health()` function**

  Current:
  ```python
  @router.get("/system/health")
  def system_health() -> dict:
      cpu_pct = psutil.cpu_percent(interval=0.1)
      mem = psutil.virtual_memory()
      disk = shutil.disk_usage("/")
      return {
          "cpu_pct": round(cpu_pct, 1),
          "ram_pct": round(mem.percent, 1),
          "disk_free_mb": round(disk.free / (1024 * 1024), 0),
      }
  ```

  Replace with:
  ```python
  @router.get("/system/health")
  def system_health() -> dict:
      from apps.api.jarvis_api.services.hardware_body import get_hardware_state
      hw = get_hardware_state()
      result = {
          "cpu_pct": hw.get("cpu_pct", 0.0),
          "ram_pct": hw.get("ram_pct", 0.0),
          "ram_used_gb": hw.get("ram_used_gb", 0.0),
          "ram_total_gb": hw.get("ram_total_gb", 0.0),
          "disk_free_mb": round(float(hw.get("disk_free_gb") or 0) * 1024, 0),
          "disk_free_gb": hw.get("disk_free_gb", 0.0),
          "pressure": hw.get("pressure", "low"),
      }
      if hw.get("cpu_temp_c") is not None:
          result["cpu_temp_c"] = hw["cpu_temp_c"]
      if hw.get("gpus"):
          result["gpus"] = hw["gpus"]
      return result
  ```

  Note: keep `disk_free_mb` for backwards compatibility with the existing UI that reads it.

- [ ] **Step 2: Remove now-redundant direct psutil imports from the function**

  The top-level `import psutil` and `import shutil` in the file may still be needed by other functions — leave them. Only the `system_health()` function body changes.

- [ ] **Step 3: Verify syntax**

  ```bash
  conda run -n ai python -m compileall apps/api/jarvis_api/routes/system_health.py -q
  ```
  Expected: no output

- [ ] **Step 4: Commit**

  ```bash
  git add apps/api/jarvis_api/routes/system_health.py
  git commit -m "feat: extend system health API with GPU, VRAM, temp, pressure"
  ```

---

### Task 4: Heartbeat gating

**Files:**
- Modify: `apps/api/jarvis_api/services/heartbeat_runtime.py` (2 places)

**Injection point A — early block (line 5631):** Block the tick entirely on "critical" pressure.

- [ ] **Step 1: Extend `_tick_blocked_reason()`**

  Current (line 5631-5636):
  ```python
  def _tick_blocked_reason(merged_state: dict[str, object]) -> str:
      if not bool(merged_state["enabled"]):
          return "disabled"
      if str(merged_state["kill_switch"]) != "enabled":
          return "kill-switch-disabled"
      return ""
  ```

  Replace with:
  ```python
  def _tick_blocked_reason(merged_state: dict[str, object]) -> str:
      if not bool(merged_state["enabled"]):
          return "disabled"
      if str(merged_state["kill_switch"]) != "enabled":
          return "kill-switch-disabled"
      try:
          from apps.api.jarvis_api.services.hardware_body import get_hardware_state
          hw = get_hardware_state()
          if hw.get("pressure") == "critical":
              return "hardware-critical"
      except Exception:
          pass
      return ""
  ```

**Injection point B — downgrade execute (line 3172):** On "high" pressure, execute → propose.

- [ ] **Step 2: Add hardware check at top of `_validate_heartbeat_decision()`**

  Current start of the function (line 3172):
  ```python
  def _validate_heartbeat_decision(
      *,
      decision: dict[str, str],
      policy: dict[str, object],
      workspace_dir: Path,
      tick_id: str,
  ) -> dict[str, object]:
      decision_type = decision["decision_type"]
      execute_action = str(decision.get("execute_action") or "").strip()
      if decision_type == "propose" and not bool(policy["allow_propose"]):
  ```

  Add hardware check immediately after `execute_action = ...`:
  ```python
      decision_type = decision["decision_type"]
      execute_action = str(decision.get("execute_action") or "").strip()

      # Downgrade execute → propose under high hardware pressure
      if decision_type in {"execute", "initiative"}:
          try:
              from apps.api.jarvis_api.services.hardware_body import get_hardware_state
              hw = get_hardware_state()
              if hw.get("pressure") == "high":
                  decision = {**decision, "decision_type": "propose"}
                  decision_type = "propose"
                  logger.info(
                      "heartbeat: downgraded execute→propose due to hardware-high pressure "
                      "(cpu=%.0f%% ram=%.0f%%)",
                      hw.get("cpu_pct", 0),
                      hw.get("ram_pct", 0),
                  )
          except Exception:
              pass

      if decision_type == "propose" and not bool(policy["allow_propose"]):
  ```

- [ ] **Step 3: Verify syntax**

  ```bash
  conda run -n ai python -m compileall apps/api/jarvis_api/services/heartbeat_runtime.py -q
  ```
  Expected: no output

- [ ] **Step 4: Full compile check**

  ```bash
  conda run -n ai python -m compileall core apps/api scripts -q
  ```
  Expected: no output

- [ ] **Step 5: Commit**

  ```bash
  git add apps/api/jarvis_api/services/heartbeat_runtime.py
  git commit -m "feat: heartbeat gating on hardware pressure — block on critical, downgrade execute on high"
  ```

---

## Pressure thresholds summary

| Metric | medium | high | critical |
|--------|--------|------|----------|
| CPU % | >70 | — | >90 |
| RAM % | >75 | >85 | >92 |
| Disk free | <5 GB | — | <1 GB |
| CPU temp | — | >80°C | >90°C |
| GPU temp | — | >75°C | >85°C |
| VRAM % | >85 | — | >95 |

Score ≥6 → critical (tick blocked), ≥3 → high (execute downgraded to propose), ≥1 → medium (no action, but felt in affective state).
