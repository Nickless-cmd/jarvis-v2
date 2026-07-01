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
import subprocess
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


# ── SSH dyb-health-pollers (disk/services/guests) — read-only bundlede kommandoer ──
# Kører fra Jarvis-containeren (bs har nøgler). Hver kommando udskriver ÉN linje key=value.
SSH_HOSTS: list[tuple[str, str, str]] = [
    ("pve", "root@10.0.0.2",
     "R=$(( $(pct list 2>/dev/null|tail -n+2|grep -cw running) + $(qm list 2>/dev/null|tail -n+2|grep -cw running) ));"
     "T=$(( $(pct list 2>/dev/null|tail -n+2|wc -l) + $(qm list 2>/dev/null|tail -n+2|wc -l) ));"
     "echo guests_running=$R guests_total=$T maxdisk=$(df --output=pcent 2>/dev/null|tail -n+2|tr -d ' %'|sort -n|tail -1) load1=$(cut -d' ' -f1 /proc/loadavg)"),
    ("webservice", "root@192.168.50.32",
     "echo disk=$(df --output=pcent / 2>/dev/null|tail -1|tr -d ' %') "
     "svc_down=$(systemctl is-active apache2 postfix dovecot mariadb clamav-daemon fail2ban cloudflared 2>/dev/null|grep -vc '^active')"),
    ("fileserver", "root@10.0.0.10",
     "echo disk=$(df --output=pcent /mnt/shares 2>/dev/null|tail -1|tr -d ' %') "
     "smb=$(systemctl is-active smbd 2>/dev/null||echo inactive)"),
]


def _ssh_run(target: str, remote_cmd: str, timeout: float = 8.0) -> str | None:
    try:
        p = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
             "-o", "StrictHostKeyChecking=accept-new", target, remote_cmd],
            capture_output=True, text=True, timeout=timeout)
        return p.stdout.strip() if p.returncode == 0 else None
    except Exception:
        return None


def _parse_kv(s: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for tok in (s or "").split():
        if "=" in tok:
            k, v = tok.split("=", 1)
            try:
                out[k] = int(v)
            except ValueError:
                out[k] = v
    return out


def poll_ssh_hosts() -> dict[str, Any]:
    """Dyb health (disk/services/guests) via read-only SSH. Self-safe pr. host."""
    results: dict[str, Any] = {}
    for name, target, cmd in SSH_HOSTS:
        kv = _parse_kv(_ssh_run(target, cmd) or "")
        if not kv:
            continue
        results[name] = kv
        try:
            central().observe({"cluster": "infra", "nerve": f"{name}_health", "kind": "observe", **kv})
        except Exception:
            pass
        # disk-tidsserie (health-proxy, higher=worse) pr. host
        disk = kv.get("maxdisk", kv.get("disk"))
        if isinstance(disk, int):
            central_timeseries.record("infra", f"{name}_disk", value=float(disk), meta=dict(kv))
        if "svc_down" in kv:
            central_timeseries.record("infra", f"{name}_svc_down", value=float(kv["svc_down"]))
    return results


def poll_ha() -> dict[str, Any]:
    """Home Assistant: tilstedeværelse + enheder offline (netværks-/device-signal). Self-safe."""
    try:
        from core.runtime.secrets import read_runtime_key
        tok = read_runtime_key("home_assistant_token")
    except Exception:
        tok = None
    if not tok:
        return {}
    states = _http_json("http://10.0.0.34:8123/api/states",
                        headers={"Authorization": "Bearer " + tok})
    if not isinstance(states, list):
        return {}
    unavailable = sum(1 for e in states if e.get("state") in ("unavailable", "unknown"))
    persons_home = sum(1 for e in states
                       if str(e.get("entity_id", "")).startswith("person.") and e.get("state") == "home")
    out = {"entities": len(states), "unavailable": unavailable, "persons_home": persons_home}
    try:
        central().observe({"cluster": "infra", "nerve": "home_assistant", "kind": "observe", **out})
    except Exception:
        pass
    central_timeseries.record("infra", "ha_unavailable", value=float(unavailable),
                              meta={"entities": len(states), "persons_home": persons_home})
    return out


def _notify_owner_security(title: str, message: str) -> None:
    try:
        from core.identity.owner_resolver import get_owner_discord_id
        uid = (get_owner_discord_id() or "").strip()
        if not uid:
            return
        from core.services.notification_router import route_proactive_notification
        route_proactive_notification(uid, "infra_security",
                                     {"title": title, "message": message}, importance="high")
    except Exception:
        pass


def poll_syslog() -> dict[str, Any]:
    """Dræn pfSense-syslog-detektioner (port-scan/brute-force) → Centralen: observe + incident
    + notifikation. Plus lytter-liveness. READ-ONLY detektion. Self-safe."""
    out: dict[str, Any] = {}
    try:
        from core.services import pfsense_syslog
        dets = pfsense_syslog.drain_detections()
        stats = pfsense_syslog.syslog_stats()
        out = {"detections": len(dets), "packets": stats.get("packets"),
               "blocks": stats.get("blocks")}
        # liveness/tidsserie (så vi ser om syslog overhovedet flyder ind)
        central_timeseries.record("infra", "pfsense_syslog",
                                  value=float(len(dets)), meta={"packets": stats.get("packets")})
        for d in dets:
            src = d.get("src"); kind = d.get("kind")
            msg = (f"{kind} fra {src}: {d.get('blocks')} blokke, "
                   f"{d.get('distinct_ports')} porte (mål {d.get('sample_dst')})")
            try:
                central().observe({"cluster": "infra", "nerve": "pfsense_security",
                                   "kind": "flag", "severity": "severe", "src": src,
                                   "detection": kind, "message": msg[:300]})
            except Exception:
                pass
            try:
                from core.runtime.db_central_incidents import record_central_incident
                record_central_incident(cluster="infra", nerve="pfsense_security",
                                        kind="security", severity="severe", message=msg[:300])
            except Exception:
                pass
            _notify_owner_security(f"⚠️ Netværks-trussel: {kind}", msg)
    except Exception:
        pass
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
    ssh_hosts = _safe(poll_ssh_hosts)
    ha = _safe(poll_ha)
    syslog = _safe(poll_syslog)
    down = [n for n, r in reach.items() if not (r or {}).get("up")]
    return {"status": "ok", "hosts": len(reach), "down": down,
            "pihole_block_pct": pihole.get("block_pct"),
            "pfsense_reachable": bool(pfsense),
            "ssh_polled": list(ssh_hosts), "ha_unavailable": ha.get("unavailable"),
            "syslog_detections": syslog.get("detections"), "syslog_packets": syslog.get("packets")}


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
