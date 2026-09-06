"""MCP-tillid: allowliste + TOFU-pinning.

Porteret fra jarvis-code 2026-09-06. Ét ansvar: forsyningskæde-tillid til
MCP-servere. To lag, og rækkefølgen er vigtig.

1. **Allowliste.** Et servernavn skal være eksplicit godkendt FØR der
   overhovedet forsøges forbindelse — før en subprocess startes, før en HTTP-
   forbindelse åbnes. En ukendt server bliver aldrig auto-forbundet.

2. **TOFU-pin.** Ved FØRSTE godkendte forbindelse pinnes målet: for stdio den
   absolutte sti til binæren plus dens sha256, for HTTP værtsnavnet. Ændrer
   målet sig senere, BLOKERES forbindelsen. Det er fail-closed med vilje —
   at en «betroet» server-binær bliver skiftet ud under os er præcis det
   signal man ikke må sove i.

Forskel fra jarvis-code: tilstanden ligger i state_store ved siden af
`mcp_registry`, ikke i en config-fil. To processer skal se samme allowliste,
og en pin der kun gjaldt i den ene proces ville være værre end ingen.
"""
from __future__ import annotations

import hashlib
import logging
import shutil
from typing import Any
from urllib.parse import urlparse

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)

_STATE_KEY = "mcp_trust"


def _load() -> dict[str, Any]:
    raw = load_json(_STATE_KEY, {})
    if not isinstance(raw, dict):
        raw = {}
    raw.setdefault("allowlist", [])
    raw.setdefault("pins", {})
    return raw


def _save(data: dict[str, Any]) -> None:
    save_json(_STATE_KEY, data)


def is_allowlisted(name: str) -> bool:
    return str(name or "") in _load().get("allowlist", [])


def allow(name: str) -> dict[str, Any]:
    """Godkend et servernavn. Idempotent."""
    navn = str(name or "").strip()
    if not navn:
        return {"status": "error", "error": "navn mangler"}
    data = _load()
    if navn not in data["allowlist"]:
        data["allowlist"].append(navn)
        _save(data)
        logger.info("mcp_trust: %r godkendt", navn)
    return {"status": "ok", "allowlist": data["allowlist"]}


def revoke(name: str) -> dict[str, Any]:
    """Fjern fra allowlisten OG drop pinnen. Idempotent.

    Pinnen droppes med, saa en genkendelse er en bevidst ny beslutning og
    ikke en tavs genoptagelse af den gamle tillid.
    """
    navn = str(name or "").strip()
    data = _load()
    if navn in data["allowlist"]:
        data["allowlist"].remove(navn)
    data["pins"].pop(navn, None)
    _save(data)
    return {"status": "ok", "allowlist": data["allowlist"]}


def list_trust() -> dict[str, Any]:
    d = _load()
    return {"status": "ok", "allowlist": d["allowlist"], "pins": d["pins"]}


def _sha256_file(path: str) -> str | None:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def check_pin_stdio(name: str, command: str) -> tuple[bool, str | None]:
    """Pin en stdio-servers binær (sti + sha256). Første syn pinner."""
    resolved = shutil.which(command) or command
    digest = _sha256_file(resolved)
    data = _load()
    pin = data["pins"].get(name)
    if pin is None:
        data["pins"][name] = {"kind": "stdio", "path": resolved, "sha256": digest}
        _save(data)
        return True, None
    if pin.get("kind") != "stdio":
        return False, f"MCP-pin ændret — transport-skift for {name!r}, godkend igen"
    if pin.get("path") != resolved:
        return False, (f"MCP-pin ændret — {name!r} peger nu på {resolved!r} "
                       f"i stedet for {pin.get('path')!r}, godkend igen")
    if digest is not None and pin.get("sha256") != digest:
        return False, (f"MCP-pin ændret — binæren bag {name!r} har en anden "
                       "sha256 end første gang, godkend igen")
    return True, None


def check_pin_http(name: str, url: str) -> tuple[bool, str | None]:
    """Pin en HTTP-servers vaert. Første syn pinner."""
    host = urlparse(str(url or "")).hostname or ""
    data = _load()
    pin = data["pins"].get(name)
    if pin is None:
        data["pins"][name] = {"kind": "http", "host": host}
        _save(data)
        return True, None
    if pin.get("kind") != "http":
        return False, f"MCP-pin ændret — transport-skift for {name!r}, godkend igen"
    if pin.get("host") != host:
        return False, (f"MCP-pin ændret — {name!r} peger nu på værten {host!r} "
                       f"i stedet for {pin.get('host')!r}, godkend igen")
    return True, None
