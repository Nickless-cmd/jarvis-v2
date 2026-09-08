#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""phone_home_auto — hold phone_adb_address i runtime.json opdateret.

Bjørns Galaxy S25 (SM-S921B) er parret til adb over Wi-Fi (Trådløs
fejlfinding). Dens IP kan skifte (DHCP), og phone_adb_værktøjerne læser
adressen fra runtime.json (nøgle: ``phone_adb_address``). Det her script
lukker hullet, så forbindelsen er der automatisk når telefonen er hjemme:

  1. Er telefonen allerede forbundet i adb på den gemte adresse? -> færdig.
  2. Svarer dens sidst-kendte IP på ping? -> adb connect -> opdater runtime.json.
  3. Nej? -> ARP-scan LAN'et efter telefonens MAC -> ny IP -> connect -> opdater.

Designhensyn
------------
* KUN stdlib — kører fra cron uden venv eller repo-import.
* Telefonen ikke på LAN (ude / mobilnet / flytilstand) -> afslut stille, exit 0.
* Log kun ved reelle ændringer (append-log + state-json for hurtig inspektion).
* Ping-scan af /24 koster -> maks. én gang per SCAN_INTERVAL_S (state-fil husker).
* Skriver runtime.json bevidst (merge + 0600); rører ingen andre nøgler.

Grænser (kan ikke automatiseres uden root — og parringskoden er med vilje
sikkerhedskontrollen, så den automatiseres aldrig):
* Efter en telefon-GENSTART slukker Android Trådløs fejlfinding. Tænd den i
  Indstillinger -> Udvikler -> Trådløs fejlfinding. Er PORTEN skiftet (den
  gør den ved genstart), kræves ét phone_adb_pair med den nye kode — scriptet
  kan ikke gætte porten, og det skal det ikke kunne.
"""

from __future__ import annotations

import json
import os
import subprocess
import time

TELEFON_MAC = "4e:3f:58:26:c4:cd"  # Galaxy S25 (SM-S921B) wlan0 — randomiseret, men stabil pr. netværk
NAVN = "SM-S921B"
DEFAULT_PORT = "40539"             # sidst kendte forbindelses-port fra Trådløs fejlfinding

_HOME = os.path.expanduser("~")
RUNTIME_STI = os.path.join(_HOME, ".jarvis-v2", "config", "runtime.json")
LOG_STI = os.path.join(_HOME, ".jarvis-v2", "state", "phone_home_auto.log")
STATE_STI = os.path.join(_HOME, ".jarvis-v2", "state", "phone_home_auto.json")

SCAN_INTERVAL_S = 300   # ARP/ping-scan af /24 maks hvert 5. minut
ADB_TIMEOUT_S = 12
_PING_TIMEOUT_S = 2


def _ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _log(besked: str) -> None:
    linje = f"[{_ts()}] {besked}"
    try:
        os.makedirs(os.path.dirname(LOG_STI), exist_ok=True)
        with open(LOG_STI, "a") as f:
            f.write(linje + "\n")
    except OSError:
        pass
    print(linje)


def _skriv_state(**felter) -> None:
    try:
        os.makedirs(os.path.dirname(STATE_STI), exist_ok=True)
        with open(STATE_STI, "w") as f:
            json.dump({"sidst_opdateret": _ts(), **felter}, f,
                      ensure_ascii=False, indent=2)
    except OSError:
        pass


# ── runtime.json ────────────────────────────────────────────────────────


def _laes_adresse() -> str:
    """Gemt host:port fra runtime.json ('' hvis ikke sat)."""
    try:
        with open(RUNTIME_STI) as f:
            d = json.load(f)
        return str(d.get("phone_adb_address") or "").strip()
    except (OSError, ValueError):
        return ""


def _skriv_adresse(adresse: str) -> bool:
    """Merge phone_adb_address ind i runtime.json. True hvis ændret."""
    try:
        with open(RUNTIME_STI) as f:
            d = json.load(f)
    except (OSError, ValueError):
        return False
    if str(d.get("phone_adb_address") or "").strip() == adresse:
        return False
    d["phone_adb_address"] = adresse
    try:
        with open(RUNTIME_STI, "w") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        os.chmod(RUNTIME_STI, 0o600)
        return True
    except OSError:
        return False


# ── adb ─────────────────────────────────────────────────────────────────


def _koer(argv: list[str], timeout_s: float = ADB_TIMEOUT_S) -> tuple[int, str]:
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout_s)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception:
        return -1, ""


def _forbundet(adresse: str) -> bool:
    rc, out = _koer(["adb", "devices"])
    if rc != 0:
        return False
    for linje in out.splitlines()[1:]:
        dele = linje.split()
        if len(dele) >= 2 and dele[0] == adresse and dele[1] == "device":
            return True
    return False


def _connect(adresse: str) -> bool:
    _koer(["adb", "connect", adresse], timeout_s=15)
    return _forbundet(adresse)


# ── LAN-detektion ───────────────────────────────────────────────────────


def _ping(ip: str) -> bool:
    rc, _ = _koer(["ping", "-c", "1", "-W", "1", ip], timeout_s=_PING_TIMEOUT_S + 1)
    return rc == 0


def _ip_fra_neigh() -> str:
    """Match TELEFON_MAC i serverens ARP-tabel (ip neigh). '' hvis ikke set."""
    rc, out = _koer(["ip", "neigh", "show"])
    if rc != 0:
        return ""
    for linje in out.splitlines():
        if TELEFON_MAC.lower() in linje.lower():
            dele = linje.split()
            if dele and dele[0].count(".") == 3:
                return dele[0]
    return ""


def _scan_lan() -> str:
    """Fyld ARP-tabellen via parallel ping-scan af 10.0.0.0/24, returnér IP.

    Ping-scan vækker alle værter, så serveren selv får dem i sin neigh-tabel
    (telefonen svarer på ICMP når den er vågen/associeret). 32 samtidige pings
    ad gangen — ca. 10-15 s for hele /24.
    """
    base = "10.0.0."
    try:
        procs: list[subprocess.Popen] = []
        for i in range(1, 255):
            procs.append(subprocess.Popen(
                ["ping", "-c", "1", "-W", "1", base + str(i)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
            if len(procs) >= 32:
                for p in procs:
                    try:
                        p.wait(timeout=3)
                    except Exception:
                        pass
                procs = []
        for p in procs:
            try:
                p.wait(timeout=3)
            except Exception:
                pass
    except Exception:
        pass
    return _ip_fra_neigh()


# ── main ────────────────────────────────────────────────────────────────


def main() -> int:
    gemt = _laes_adresse()

    # Allerede forbundet på den gemte adresse? Så er der intet at gøre.
    if gemt and _forbundet(gemt):
        _skriv_state(adresse=gemt, forbundet=True, handling="allerede-forbundet")
        return 0

    # Udled sidst-kendte host:port fra den gemte adresse.
    # Porten fra Trådløs fejlfinding kan skifte (genstart af funktionen eller
    # telefonen). Vi prøver derfor BÅDE den gemte port og DEFAULT_PORT (sidst
    # kendte gode) — den første der connecter vinder og bliver gemt.
    host, porte = "", []
    if gemt and ":" in gemt:
        g_host, _, g_port = gemt.rpartition(":")
        if g_host:
            host = g_host
        if g_port.isdigit():
            porte.append(g_port)
    if DEFAULT_PORT not in porte:
        porte.append(DEFAULT_PORT)

    # 1) Svarer sidst-kendte IP? (billigt — 1 ping)
    fundet_ip = host if (host and _ping(host)) else ""

    # 2) Ellers: scan LAN'et — men maks hvert SCAN_INTERVAL_S.
    if not fundet_ip:
        nu = time.time()
        sidst_scan = 0.0
        try:
            with open(STATE_STI) as f:
                sidst_scan = float(json.load(f).get("sidste_scan_ts") or 0)
        except (OSError, ValueError):
            pass
        if nu - sidst_scan >= SCAN_INTERVAL_S:
            fundet_ip = _scan_lan()
            _skriv_state(sidste_scan_ts=str(nu))
        # (ellers: hop over scanningen denne gang — spiller ikke ind oftere)

    if not fundet_ip:
        # Telefonen er ikke på hjemme-LAN lige nu — normal tilstand, ikke en fejl.
        _skriv_state(adresse=gemt or f"(mangler:{DEFAULT_PORT})",
                     forbundet=False, handling="ikke-paa-lan")
        return 0

    # Prøv portene i rækkefølge; første connect der lykkes vinder.
    for port in porte:
        adresse = f"{fundet_ip}:{port}"
        if _connect(adresse):
            aendret = _skriv_adresse(adresse)
            _log(f"{NAVN} forbundet på {adresse} "
                 f"({'adresse-opdateret' if aendret else 'allerede-gemt'})")
            _skriv_state(adresse=adresse, forbundet=True,
                         handling="adresse-opdateret" if aendret else "connectet",
                         sidste_scan_ts=str(time.time()))
            return 0

    _log(f"{NAVN} fundet på {fundet_ip}, men adb-connect fejlede på "
         + " og ".join(f"port {p}" for p in porte) + ". "
         "Er Trådløs fejlfinding tændt på telefonen? Er porten skiftet efter en "
         "genstart? Så kør phone_adb_pair for at få den nye port.")
    _skriv_state(adresse=f"{fundet_ip}:{porte[0]}", forbundet=False,
                 handling="connect-fejlede", sidste_scan_ts=str(time.time()))
    return 1


if __name__ == "__main__":
    sys_exit = main()
    raise SystemExit(sys_exit)
