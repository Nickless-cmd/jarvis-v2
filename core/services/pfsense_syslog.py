"""core/services/pfsense_syslog.py

pfSense syslog-lytter — realtids-sikkerhedsdetektion (Bjørn: "ingen blinde vinkler").

pfSense forwarder firewall-logs (UDP) til Jarvis-containeren. Denne lytter parser
`filterlog`-linjer, aggregerer blokke pr. kilde-IP i et glidende vindue, og detekterer
PORT-SCANS (mange distinkte dst-porte fra én IP) + BRUTE-FORCE (mange blokke fra én IP).
Detektioner drænes af infra_sense-cadence → Centralen (incident + notifikation).

⛔ READ-ONLY DETEKTION. Ingen firewall-skrivning her — reaktion (blokér IP) venter til
shadow-mode (M1-mønster), aldrig autonomt før valideret + log-injektion-hærdet.

Port 5514 (UPRIVILEGERET — runtime kører som non-root bs; 514 kræver root). Konfigurér pfSense:
Status → System Logs → Settings → Remote Logging → server `10.0.0.39:5514`, "Firewall events".
Self-safe: en fejl i lytteren må aldrig røre runtime.
"""
from __future__ import annotations

import re
import socket
import threading
import time

_PORT = 5514
_WINDOW_S = 300.0            # 5-min glidende vindue pr. kilde-IP
_SCAN_PORTS = 15            # ≥N distinkte dst-porte fra én IP = port-scan
_BRUTE_BLOCKS = 30         # ≥N blokke fra én IP = brute-force
_DETECT_COOLDOWN_S = 600.0  # samme IP re-detekteres højst hvert 10. min (dedup)

_IPV4 = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")

_lock = threading.Lock()
_agg: dict[str, dict] = {}          # src-IP → {"blocks":int, "ports":set, "first":ts}
_last_detect: dict[str, float] = {}
_detections: list[dict] = []        # drænes af infra_sense-cadence
_stats = {"packets": 0, "blocks": 0, "detections": 0, "last_packet_epoch": 0.0}
_thread_started = False


def _parse_filterlog(line: str) -> dict | None:
    """Tolerant parser af pfSense filterlog-CSV. Returnerer {action, src, dst, dport}."""
    i = line.find("filterlog")
    if i < 0:
        return None
    colon = line.find(":", i)
    if colon < 0:
        return None
    f = line[colon + 1:].strip().split(",")
    if len(f) < 9:
        return None
    action = f[6] if len(f) > 6 else ""
    ips = [x for x in f if _IPV4.match(x)]
    if len(ips) < 2:
        return None
    src, dst = ips[0], ips[1]
    # filterlog-rækkefølge: ...,src,dst,srcport,dstport,... → DESTINATIONS-porten er dst+2.
    dport = None
    try:
        di = f.index(dst)
        if di + 2 < len(f) and f[di + 2].isdigit():
            dport = int(f[di + 2])           # dstport (det attacker scanner)
        elif di + 1 < len(f) and f[di + 1].isdigit():
            dport = int(f[di + 1])           # fallback (icmp/uden srcport)
    except Exception:
        pass
    return {"action": action, "src": src, "dst": dst, "dport": dport}


def _is_internal_src(src: str) -> bool:
    """Er kilde-IP'en PRIVAT (RFC1918 = husets egne maskiner)? Ægte port-scan/brute-force kommer
    UDEFRA (offentlig IP). En intern kilde der får blokke er husets egen maskine (fx CheifOne =
    192.168.50.84) der laver normal spærret udgående trafik → FALSE-POSITIVE brute_force, ikke
    angreb. (Exfil-detektion fra intern host kræver et andet, mere præcist signal — ikke '30
    blokerede udgående'.) Ekskludér interne kilder fra scan/brute-detektionen."""
    try:
        a, b, *_ = (int(x) for x in src.split("."))
        if a == 10:
            return True
        if a == 192 and b == 168:
            return True
        if a == 172 and 16 <= b <= 31:
            return True
        if a == 127:
            return True
    except Exception:
        pass
    return False


def _is_noise_dst(dst: str) -> bool:
    """Multicast/broadcast er normal netværks-støj (mDNS/SSDP/LLMNR/DHCP), IKKE angreb.
    Rigtige scans/brute-force rammer unicast-hosts. Ekskludér så vi ikke får false-positives."""
    try:
        first = int(dst.split(".", 1)[0])
        if 224 <= first <= 239:            # multicast (224.0.0.0/4)
            return True
        if dst == "255.255.255.255" or dst.endswith(".255"):  # broadcast
            return True
    except Exception:
        pass
    return False


def _ingest(rec: dict, now: float) -> None:
    if rec.get("action") != "block":
        return
    if _is_noise_dst(str(rec.get("dst") or "")):
        return  # multicast/broadcast-støj — ikke et angreb
    src = rec.get("src") or ""
    if not src:
        return
    with _lock:
        _stats["blocks"] += 1
        a = _agg.get(src)
        if a is None or now - a["first"] > _WINDOW_S:
            a = {"blocks": 0, "ports": set(), "first": now}
            _agg[src] = a
        a["blocks"] += 1
        if rec.get("dport") is not None:
            a["ports"].add(rec["dport"])
        scan = len(a["ports"]) >= _SCAN_PORTS
        brute = a["blocks"] >= _BRUTE_BLOCKS
        # Kun EKSTERNE kilder detekteres som scan/brute — interne (husets egne maskiner) er
        # false-positives (verificeret 3. jul: 192.168.50.84=CheifOne, .31=husenhed).
        internal = _is_internal_src(src)
        last = _last_detect.get(src)  # None = aldrig detekteret (0.0 er en gyldig tid)
        if (scan or brute) and not internal and (last is None or (now - last) > _DETECT_COOLDOWN_S):
            _last_detect[src] = now
            _detections.append({
                "src": src, "kind": "port_scan" if scan else "brute_force",
                "blocks": a["blocks"], "distinct_ports": len(a["ports"]),
                "sample_dst": rec.get("dst"),
            })
            _stats["detections"] += 1


def _listen() -> None:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", _PORT))
    except Exception:
        return  # kan ikke binde → self-safe, lytteren dør stille (fx port optaget/privilegeret)
    while True:
        try:
            data, _ = s.recvfrom(8192)
            now = time.monotonic()
            with _lock:
                _stats["packets"] += 1
                _stats["last_packet_epoch"] = time.time()
            rec = _parse_filterlog(data.decode("utf-8", "replace"))
            if rec:
                _ingest(rec, now)
        except Exception:
            continue


def start_syslog_listener() -> None:
    """Start UDP-lytteren i en daemon-tråd (idempotent). Kun i runtime-processen."""
    global _thread_started
    if _thread_started:
        return
    _thread_started = True
    threading.Thread(target=_listen, name="pfsense-syslog", daemon=True).start()


def drain_detections() -> list[dict]:
    """Hent + ryd nye detektioner (kaldes af infra_sense-cadence). Self-safe."""
    with _lock:
        out = list(_detections)
        _detections.clear()
        return out


def syslog_stats() -> dict:
    with _lock:
        return dict(_stats)


def _reset_for_tests() -> None:
    with _lock:
        _agg.clear()
        _last_detect.clear()
        _detections.clear()
        for k in _stats:
            _stats[k] = 0 if k != "last_packet_epoch" else 0.0
