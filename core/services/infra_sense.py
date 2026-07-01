"""core/services/infra_sense.py

Infra-sansning (Bjørn 1. jul: "Centralen som husets nervesystem").

Jarvis' container har nøgler + REST-tokens til hele huset. Denne cadence-producer sanser
alle hosts READ-ONLY og fodrer den SAMME central-sløjfe (observe → støjfang → flag → notify)
som resten af Centralen. Det er miljø-modaliteten LivingNeuron mangler — Jarvis kan nu
korrelere sin indre tilstand med husets ydre begivenheder.

PRINCIP (Bjørns egen retning): KUN afvigelser er signal — ikke logs-for-logs. Vi måler
puls (reachability+latency) + de få høj-værdi-signaler pr. host (DNS-blok-rate, gateway-liveness).

SIKKERHED: alt her er READ-ONLY. Ingen firewall-skrivning, ingen mutation. Reaktion (blokér IP)
kommer senere i shadow-mode (M1-mønster) — aldrig autonomt før valideret. Self-safe: kaster aldrig.
Kører på Jarvis-containeren (har LAN-adgang + creds i runtime.json).
"""
from __future__ import annotations

import json
import socket
import ssl
import time
import urllib.request
from typing import Any

from core.services import central_timeseries
from core.services.central_core import central

# Host-inventar (verificeret 1. jul). (navn, ip, tcp-port til reachability-probe).
# Port vælges så en åben port = "servicen lever", ikke bare ICMP.
HOSTS: list[tuple[str, str, int]] = [
    ("pve", "10.0.0.2", 22),
    ("pfsense", "10.0.0.1", 443),
    ("pihole", "10.0.0.5", 443),
    ("fileserver", "10.0.0.10", 22),
    ("home_assistant", "10.0.0.34", 8123),
    ("webservice", "192.168.50.32", 22),
]

_PROBE_TIMEOUT = 3.0
_SSL_NOVERIFY = ssl.create_default_context()
_SSL_NOVERIFY.check_hostname = False
_SSL_NOVERIFY.verify_mode = ssl.CERT_NONE


def _tcp_probe(host: str, port: int, timeout: float = _PROBE_TIMEOUT) -> tuple[bool, float | None]:
    """(oppe, latency_ms) — TCP-connect. Undgår ICMP-privilegier; åben port = servicen lever."""
    t0 = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, round((time.monotonic() - t0) * 1000.0, 1)
    except Exception:
        return False, None


def poll_reachability() -> dict[str, Any]:
    """Puls på huset: op/ned + latency for hver host → observe(cluster=infra). Self-safe."""
    results: dict[str, Any] = {}
    for name, ip, port in HOSTS:
        up, latency = _tcp_probe(ip, port)
        results[name] = {"up": up, "latency_ms": latency}
        try:
            central().observe({"cluster": "infra", "nerve": f"reach_{name}", "kind": "observe",
                               "up": up, "latency_ms": latency, "target": f"{ip}:{port}"})
        except Exception:
            pass
        try:
            # value = latency hvis oppe, -1.0 hvis nede (så central_watch kan flagge <0)
            central_timeseries.record("infra", f"reach_{name}",
                                      value=(latency if up and latency is not None else -1.0),
                                      meta={"up": up, "target": f"{ip}:{port}"})
        except Exception:
            pass
    return results


def _http_json(url: str, *, headers: dict | None = None, method: str = "GET",
               body: dict | None = None, timeout: float = 8.0) -> dict | None:
    try:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={"Content-Type": "application/json", **(headers or {})})
        ctx = _SSL_NOVERIFY if url.startswith("https") else None
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def poll_pihole() -> dict[str, Any]:
    """PiHole DNS-helbred: blok-rate + klienter (spike = mulig malware). Self-safe."""
    out: dict[str, Any] = {}
    try:
        from core.runtime.secrets import read_runtime_key
        pw = read_runtime_key("pihole_api_password")
    except Exception:
        pw = None
    if not pw:
        return out
    auth = _http_json("https://10.0.0.5/api/auth", method="POST", body={"password": pw})
    sid = ((auth or {}).get("session") or {}).get("sid")
    if not sid:
        return out
    try:
        summ = _http_json("https://10.0.0.5/api/stats/summary", headers={"X-FTL-SID": sid})
        q = (summ or {}).get("queries") or {}
        out = {"queries": q.get("total"), "blocked": q.get("blocked"),
               "block_pct": q.get("percent_blocked"),
               "clients": ((summ or {}).get("clients") or {}).get("active")}
        try:
            central().observe({"cluster": "infra", "nerve": "pihole_dns", "kind": "observe", **out})
        except Exception:
            pass
        central_timeseries.record("infra", "pihole_dns",
                                  value=float(out.get("block_pct") or 0.0),
                                  meta={"clients": out.get("clients")})
    finally:
        _http_json("https://10.0.0.5/api/auth", headers={"X-FTL-SID": sid}, method="DELETE")
    return out


def poll_pfsense() -> dict[str, Any]:
    """pfSense gateway-liveness + uptime via REST API (X-API-Key). Read-only. Self-safe."""
    out: dict[str, Any] = {}
    try:
        from core.runtime.secrets import read_runtime_key
        key = read_runtime_key("pfsense_api_key")
    except Exception:
        key = None
    if not key:
        return out
    d = _http_json("https://10.0.0.1/api/v2/status/system", headers={"X-API-Key": key})
    data = (d or {}).get("data") or {}
    if not data:
        return out
    out = {"uptime": data.get("uptime"), "platform": data.get("platform"),
           "cpu_temp": data.get("cpu_temp"), "mem_used_pct": data.get("mem_usage")}
    try:
        central().observe({"cluster": "infra", "nerve": "pfsense_gw", "kind": "observe",
                           "reachable": True, "uptime": out.get("uptime")})
    except Exception:
        pass
    central_timeseries.record("infra", "pfsense_gw", value=1.0, meta={"uptime": out.get("uptime")})
    return out


def _safe(fn) -> dict:
    try:
        return fn() or {}
    except Exception:
        return {}


def run_infra_sense_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence-producer: sans huset read-only. Bulletproof — kaster ALDRIG."""
    reach = _safe(poll_reachability)
    pihole = _safe(poll_pihole)
    pfsense = _safe(poll_pfsense)
    down = [n for n, r in reach.items() if not (r or {}).get("up")]
    return {"status": "ok", "hosts": len(reach), "down": down,
            "pihole_block_pct": pihole.get("block_pct"),
            "pfsense_reachable": bool(pfsense)}


def register_infra_sense_producer() -> None:
    """Registrér infra-sansningen som cadence-producer (~hvert 3 min). Read-only."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="infra_sense",
        cooldown_minutes=3,
        visible_grace_minutes=0,
        run_fn=run_infra_sense_tick,
        priority=7,
    ))
