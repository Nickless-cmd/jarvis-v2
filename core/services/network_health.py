"""core/services/network_health.py

Samlet netværks-helbred — ÉN nerve der fuser al spredt netværks-telemetri til ét
signal Centralen kan svare på (Bjørn 2. jul: "hvad siger Centralen om netværket?").

HVORFOR: infra_sense skriver 14+ spredte ``infra:reach_*``/``infra:*``-nerver, og
``provider_health_check`` sit eget. Der fandtes INTET samlet netværks-signal — og
INTET der målte den API-latens klienten FAKTISK føler (klientens 3ms→900ms-sving 2.
jul kunne ingen nerve forklare). Jarvis diagnosticerede selv hullet: "der findes ikke
en dedikeret network_health-nerve". Denne synthesizer lukker det:

  1. Måler live API-latens loopback (runtime → api:8080/health) = klientens føltee latens.
  2. Læser hosts-reachability fra infra_sense' friske tidsserie (down = value < 0).
  3. Læser provider-helbred + HA-utilgængelighed.
  4. Fuser til ét grønt/gult/rødt verdikt → ``network:health``-tidsserie + incident ved rødt.

SIKKERHED/M0: READ-ONLY observabilitet. Ingen mutation, ingen firewall-skrivning, ingen
egress ud over de probes infra_sense allerede laver. Self-safe: kaster ALDRIG (samme
kontrakt som central().observe). Kører på Jarvis-containeren (loopback til egen API).
"""
from __future__ import annotations

import time
import urllib.request
from typing import Any

from core.services import central_timeseries
from core.services.central_core import central

# Loopback-mål: den lokale API-proces. Latens herfra ≈ hvad en klient på samme subnet
# oplever, MINUS selve nettet (~få ms lokalt) → fanger event-loop-blokering (§--workers 1).
_API_HEALTH_URL = "http://127.0.0.1:8080/health"
_API_TIMEOUT = 5.0

# Tærskler for API-latens (ms). Lokal loopback bør være < 50ms; alt over ~400ms betyder
# at event-loop'en er presset (blokerende kald / tool-exec) — præcis 2.-juli-symptomet.
_API_YELLOW_MS = 250.0
_API_RED_MS = 800.0

# Hosts vi betragter som KRITISKE for at Jarvis kan nås/fungere. Fald her → rødt.
_CRITICAL_HOSTS = ("pve", "pfsense")


def measure_api_latency(url: str = _API_HEALTH_URL, timeout: float = _API_TIMEOUT) -> tuple[bool, float | None]:
    """(ok, latency_ms) for den lokale API. TCP+HTTP round-trip mod /health. Self-safe."""
    t0 = time.monotonic()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "jarvis-network-health"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read(64)
            ok = 200 <= resp.status < 500  # 4xx = auth-krav, men API'et SVARER = oppe
        return ok, round((time.monotonic() - t0) * 1000.0, 1)
    except Exception:
        return False, None


def _latest(cluster: str, nerve: str) -> float | None:
    """Seneste tidsserie-værdi for en nerve (samme proces). None hvis tom."""
    try:
        s = central_timeseries.recent(cluster, nerve, limit=1)
        return s[-1].value if s else None
    except Exception:
        return None


def _hosts_down() -> list[str]:
    """Hosts hvis seneste reachability-sample er 'nede' (infra_sense skriver -1.0 ved nede)."""
    down: list[str] = []
    try:
        for cluster, nerve in central_timeseries.nerves():
            if cluster != "infra" or not nerve.startswith("reach_"):
                continue
            v = _latest(cluster, nerve)
            if v is not None and v < 0:
                down.append(nerve[len("reach_"):])
    except Exception:
        pass
    return down


def run_network_health_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence-producer: fuse netværks-telemetri → ét signal. Bulletproof — kaster ALDRIG."""
    try:
        api_ok, api_ms = measure_api_latency()
    except Exception:
        api_ok, api_ms = False, None
    down = _hosts_down()
    provider = _latest("system", "provider_health_check")  # 1.0 ok / 0.0 fejl (best-effort)
    ha_unavail = _latest("infra", "ha_unavailable")
    critical_down = [h for h in down if h in _CRITICAL_HOSTS]

    # Verdikt: rødt hvis API ikke svarer / meget langsom, eller en kritisk host er nede.
    # Gult ved forhøjet API-latens, ikke-kritisk host nede, eller provider-fejl.
    if not api_ok or (api_ms is not None and api_ms >= _API_RED_MS) or critical_down:
        status = "red"
    elif ((api_ms is not None and api_ms >= _API_YELLOW_MS) or down
          or (provider is not None and provider < 1.0)):
        status = "yellow"
    else:
        status = "green"

    meta: dict[str, Any] = {
        "status": status,
        "api_ok": api_ok,
        "api_latency_ms": api_ms,
        "hosts_down": down,
        "critical_down": critical_down,
        "provider_ok": (None if provider is None else provider >= 1.0),
        "ha_unavailable": (None if ha_unavail is None else int(ha_unavail)),
        "trigger": trigger,
    }

    # ÉT samlet signal: value = API-latens (klientens føltee tal), meta = hele billedet.
    try:
        central_timeseries.record("network", "health", value=api_ms, meta=meta)
    except Exception:
        pass
    # Fodr central-sløjfen (observe → støjfang → flag) med det fusede signal.
    try:
        central().observe({"cluster": "network", "nerve": "health", "kind": "observe", **meta})
    except Exception:
        pass

    # Kun ÆGTE forværring bliver et flag (Bjørns princip: kun afvigelser er signal).
    if status == "red":
        try:
            from core.runtime.db_central_incidents import record_central_incident
            reason = ("API svarer ikke" if not api_ok
                      else f"API-latens {api_ms}ms ≥ {_API_RED_MS:.0f}ms" if api_ms and api_ms >= _API_RED_MS
                      else f"kritisk host nede: {', '.join(critical_down)}")
            record_central_incident(
                cluster="network", nerve="health", kind="network_degraded", severity="error",
                message=(f"Netværks-helbred RØDT: {reason}. "
                         f"api_ok={api_ok} latency={api_ms}ms hosts_down={down or 'ingen'}"))
        except Exception:
            pass

    return {"status": status, "api_ok": api_ok, "api_latency_ms": api_ms,
            "hosts_down": down, "provider_ok": meta["provider_ok"], "ha_unavailable": meta["ha_unavailable"]}


def register_network_health_producer() -> None:
    """Registrér netværks-helbred som cadence-producer (~hvert 2 min). Read-only, self-safe."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="network_health",
        cooldown_minutes=2,
        visible_grace_minutes=0,
        run_fn=run_network_health_tick,
        priority=7,
    ))
