"""SSRF-vaern for udgaaende hentninger — porteret fra jarvis-code.

MAALT 5/9-2026: runtimens web-vaerktoejer (`web_fetch`, `web_scrape`,
`webhook_tools`) havde **ingen destinations-validering overhovedet**. De eneste
`127.0.0.1` i filerne var Jarvis' egne ollama-kald. Det betyder at en hentning
kunne pege paa:

    http://169.254.169.254/    cloud-metadata
    http://10.0.0.1/           pfSense-administrationen
    http://127.0.0.1:8080/     hans eget API

jarvis-code har vaernet (`netguard.py` → `jc_sandbox.classify_ssrf`), runtimen
havde det ikke. Det var ét af de to moduler uden nogen server-side pendant.

**Hver omdirigering skal revalideres.** Uden det kan en offentlig URL 302'e sig
ind til et internt maal, og saa har foerste tjek ingen vaerdi. Derfor det
separate `check_redirect_hop` — samme klassifikation, eget navn, saa
kaldsstederne laeser rigtigt.

**Ved DNS-fejl: tillad.** Fail-closed dér ville goere enhver netvaerks-hikke til
en blokering. Er vaerten allerede en intern IP-literal, er den fanget foer
opslaget overhovedet sker — og DNS-rebind mellem tjek og hentning er bevidst
uden for det her vaerns raekkevidde.
"""
from __future__ import annotations

import ipaddress
import re
import socket
from typing import Any
from urllib.parse import urlparse

MAX_REDIRECT_HOPS = 5


def _is_internal_ip(ip_str: str) -> bool:
    """Loopback, link-local (inkl. 169.254.169.254), RFC1918, 0.0.0.0. Ren."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    if ip.is_loopback or ip.is_link_local or ip.is_private:
        return True
    return str(ip) == "0.0.0.0"


def classify(url: str) -> dict[str, Any]:
    """{"blocked": bool, "reason": str}. Self-safe: uparsbar URL → blokeret.

    Vaerten slaas op, saa et navn der PEGER paa en intern adresse ogsaa fanges —
    ellers ville `intern.eksempel.dk` vaere en aaben doer.
    """
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return {"blocked": True, "reason": f"uparsbar URL: {str(url)[:80]}"}
    if not host:
        return {"blocked": True, "reason": "ingen vaert i URL'en"}
    if host == "localhost" or host.endswith(".localhost"):
        return {"blocked": True, "reason": "loopback-vaertsnavn (localhost)"}

    literal = host.strip("[]")
    if _is_internal_ip(literal):
        return {"blocked": True, "reason": f"intern IP-literal: {literal}"}

    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        # En netvaerks-hikke maa ikke blive til en blokering. En intern literal
        # er allerede fanget ovenfor.
        return {"blocked": False, "reason": "DNS-opslag mislykkedes; tillader"}

    for info in infos:
        adresse = info[4][0]
        if _is_internal_ip(adresse):
            return {"blocked": True,
                    "reason": f"vaerten '{host}' peger paa intern IP {adresse}"}
    return {"blocked": False, "reason": ""}


def is_safe_destination(url: str) -> dict[str, Any]:
    """{"safe": bool, "reason": str} — laesevenligt alias til `classify`."""
    v = classify(url)
    return {"safe": not v["blocked"], "reason": v["reason"]}


def check_redirect_hop(url: str) -> dict[str, Any]:
    """Samme klassifikation, anvendt paa et OMDIRIGERINGS-maal.

    Eget navn med vilje: kaldsstedet skal laese «revalidér hvert hop». Uden det
    kan en offentlig URL 302'e sig ind til et internt maal, og saa var det
    foerste tjek uden vaerdi.
    """
    return is_safe_destination(url)



# ── Egress i bash-kommandoer ─────────────────────────────────────────────
# Uafhaengig af de «pipe-til-shell»-moenstre der findes i forvejen: de fanger
# `curl | bash`. Det her fanger ENHVER udgaaende netvaerks-raekken, uanset om
# den piper videre. Formaalet er ikke at blokere — det er at goere det SYNLIGT
# at en kommando naar ud af huset, saa en approval-beslutning traeffes paa et
# oplyst grundlag.

_EGRESS_VAERKTOEJ = re.compile(
    r"\b(curl|wget|nc|ncat|netcat|scp|sftp|ssh|telnet|ftp)\b", re.IGNORECASE)
# rsync er kun egress naar den peger paa en FJERN vaert (host:sti, ::modul, -e ssh).
#
# ARVET FEJL, rettet i porten: jarvis-codes moenster kraevede et IKKE-skraastreg
# efter kolon (`[\w.\-]+:[^/]`), men et fjernmaal skrives normalt `vaert:/sti` —
# saa `rsync -av /a/ b.dk:/c` slap forbi som lokal. Nu er det nok at en
# whitespace-adskilt token efterfoelges af kolon.
_RSYNC_FJERN = re.compile(r"\brsync\b[^|;]*\s[\w.\-]+:|\brsync\b.*(::|-e\s+ssh)",
                          re.IGNORECASE)
# bash' egne netvaerks-pseudoenheder — nemme at overse i en review.
_DEVTCP = re.compile(r"/dev/(tcp|udp)/")


def classify_egress(command: str) -> dict[str, Any]:
    """{"egress": bool, "tool": str, "reason": str} for en bash-kommando. Ren."""
    try:
        cmd = str(command or "")
        if not cmd:
            return {"egress": False, "tool": "", "reason": ""}
        m = _EGRESS_VAERKTOEJ.search(cmd)
        if m:
            t = m.group(1).lower()
            return {"egress": True, "tool": t,
                    "reason": f"netvaerks-vaerktoej '{t}' i kommandoen"}
        if _RSYNC_FJERN.search(cmd):
            return {"egress": True, "tool": "rsync",
                    "reason": "rsync peger paa en fjern vaert"}
        if _DEVTCP.search(cmd):
            return {"egress": True, "tool": "/dev/tcp",
                    "reason": "bash netvaerks-omdirigering via /dev/tcp"}
        return {"egress": False, "tool": "", "reason": ""}
    except Exception:
        return {"egress": False, "tool": "", "reason": ""}


def urls_in_command(command: str) -> list[str]:
    """URL'er i en kommando, saa de kan klassificeres hver for sig. Ren."""
    try:
        return re.findall(r"https?://[^\s'\"<>|;)]+", str(command or ""))
    except Exception:
        return []


def internal_targets_in_command(command: str) -> list[str]:
    """De URL'er i kommandoen der peger INDAD. Ren.

    Det er den interessante delmaengde: `curl https://api.eksempel.dk` er
    almindeligt arbejde, `curl http://169.254.169.254/` er noget andet.
    """
    return [u for u in urls_in_command(command) if classify(u)["blocked"]]
