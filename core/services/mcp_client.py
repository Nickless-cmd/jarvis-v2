"""MCP-klient — stdio og HTTP, med trust-gate foran hver forbindelse.

Porteret fra jarvis-code 2026-09-06. Runtime havde kun `mcp_registry`, som
er et KONFIGURATIONS-lager og siger det ærligt i sin egen docstring: det
kunne liste, tilføje og fjerne servere, men intet kunne tale med dem. Hele
MCP-økosystemet lå uden for rækkevidde.

## To forskelle fra jarvis-code, begge tvunget af arkitekturen

**Forbindelser er proces-lokale.** jarvis-code er én langlivet REPL og kan
holde stdio-subprocesser i live i en manager. Runtime er to request/response-
processer (jarvis-api og jarvis-runtime), så en pulje her gælder kun den
proces der lavede den, og forsvinder ved genstart. Det er acceptabelt fordi
puljen kun er en CACHE: en stdio-server er billig at starte, og HTTP er
statsløs i forvejen. Tilliden derimod — allowliste og pins — ligger i delt
state, for den MÅ ikke være proces-lokal.

**Ingen `.mcp.json` i et arbejdstræ.** jarvis-code leder efter en configfil
ved siden af koden. Her kommer serverne fra `mcp_registry`, som er der hvor
Bjørn i forvejen tilføjer dem fra UI'et. Ét sted, ikke to.

Resultater fra en MCP-server er indhegnet som utroet indhold før de når
modellen — en fremmed server er præcis den slags kilde der kan være skrevet
til at ligne en instruks.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import threading
from typing import Any

from core.services import mcp_trust

logger = logging.getLogger(__name__)

_PROTOKOL_VERSION = "2024-11-05"
_KLIENT_NAVN = "jarvis-v2"
_STDIO_TIMEOUT_S = 20
_HTTP_TIMEOUT_S = 20


def parse_mcp_http_body(tekst: str, content_type: str = "") -> dict[str, Any]:
    """Læs et MCP-over-HTTP-svar — JSON *eller* SSE.

    MÅLT 18/10-2026: Context7 (`https://mcp.context7.com/mcp`) svarer
    `text/event-stream`, ikke `application/json`. Klienten kaldte
    `response.json()`, som kaster på `event: message\\ndata: {...}` — den
    meldte altså en sund server som død. MCP-specifikationen tillader begge
    formater for HTTP-transport, så det er klienten der var for snæver.

    SSE kan bære flere `data:`-linjer; vi tager den FØRSTE der er gyldig
    JSON, fordi et request/response-kald kun har ét svar. `[DONE]` og tomme
    linjer springes over.
    """
    tekst = (tekst or "").strip()
    if not tekst:
        return {"error": "tomt svar fra MCP-serveren"}
    ser_sse = (
        "event-stream" in (content_type or "").lower()
        or tekst.startswith("event:")
        or tekst.startswith("data:")
    )
    if ser_sse:
        for linje in tekst.splitlines():
            linje = linje.strip()
            if not linje.startswith("data:"):
                continue
            raa = linje[len("data:"):].strip()
            if not raa or raa == "[DONE]":
                continue
            try:
                pakke = json.loads(raa)
            except Exception:
                continue
            if isinstance(pakke, dict):
                return pakke
        return {"error": "SSE-svar uden gyldig JSON-data"}
    try:
        pakke = json.loads(tekst)
    except Exception:
        return {"error": f"ikke-JSON svar fra MCP-serveren: {tekst[:200]}"}
    return pakke if isinstance(pakke, dict) else {"error": "uventet svarform"}


class MCPClient:
    """Én forbindelse til én MCP-server."""

    def __init__(self, name: str, config: dict[str, Any]):
        self.name = str(name)
        self.config = dict(config or {})
        self.transport = str(self.config.get("transport") or
                             ("http" if self.config.get("url") else "stdio")).lower()
        self.url = str(self.config.get("url") or "")
        self.process: subprocess.Popen | None = None
        self.tools: list[dict[str, Any]] = []
        self.connect_error: str | None = None
        self._request_id = 0
        self._connected = False

    # ── forbindelse ────────────────────────────────────────────────────────

    def connect(self) -> bool:
        """Trust-gate først, DERNÆST forbindelse. Rækkefølgen er hele pointen."""
        self.connect_error = None
        if not mcp_trust.is_allowlisted(self.name):
            self.connect_error = (
                f"MCP-serveren {self.name!r} er ikke godkendt. "
                "Godkend den med mcp_trust(action='allow') før den kan bruges."
            )
            return False
        if self.transport == "http":
            ok, fejl = mcp_trust.check_pin_http(self.name, self.url)
            if not ok:
                self.connect_error = fejl
                return False
            return self._connect_http()
        return self._connect_stdio()

    def _connect_stdio(self) -> bool:
        command = str(self.config.get("command") or "")
        if not command:
            self.connect_error = "stdio-transport kræver 'command'"
            return False
        ok, fejl = mcp_trust.check_pin_stdio(self.name, command)
        if not ok:
            self.connect_error = fejl
            return False
        try:
            self.process = subprocess.Popen(
                [shutil.which(command) or command, *list(self.config.get("args") or [])],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, env={**os.environ, **dict(self.config.get("env") or {})},
            )
            self._connected = True
            if not self._initialize():
                self.disconnect()
                return False
            self.tools = self._discover_tools()
            return True
        except Exception as exc:
            self.connect_error = f"kunne ikke starte {command!r}: {exc}"
            self._connected = False
            return False

    def _connect_http(self) -> bool:
        if not self.url:
            self.connect_error = "http-transport kræver 'url'"
            return False
        try:
            if not self._initialize():
                return False
            self.tools = self._discover_tools()
            self._connected = True
            return True
        except Exception as exc:
            self.connect_error = str(exc)
            self._connected = False
            return False

    def disconnect(self) -> None:
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None
        self._connected = False

    @property
    def connected(self) -> bool:
        if self.transport == "http":
            return self._connected
        return (self._connected and self.process is not None
                and self.process.poll() is None)

    # ── JSON-RPC ───────────────────────────────────────────────────────────

    def _send_request(self, method: str, params: dict | None = None) -> dict[str, Any]:
        self._request_id += 1
        req: dict[str, Any] = {"jsonrpc": "2.0", "id": self._request_id, "method": method}
        if params:
            req["params"] = params
        if self.transport == "http":
            return self._send_http(req)
        return self._send_stdio(req)

    def _send_stdio(self, req: dict) -> dict[str, Any]:
        if not self.process or not self.process.stdin or not self.process.stdout:
            return {"error": "ikke forbundet"}
        # En server der aldrig svarer maa ikke haenge turen. jarvis-code kunne
        # leve med et blokerende readline i en REPL; her ville det spaerre en
        # request-tråd i api'et.
        svar: dict[str, Any] = {}

        def _laes() -> None:
            try:
                linje = self.process.stdout.readline()  # type: ignore[union-attr]
                svar.update(json.loads(linje) if linje else {"error": "intet svar"})
            except Exception as exc:
                svar.update({"error": str(exc)})

        try:
            self.process.stdin.write(json.dumps(req) + "\n")
            self.process.stdin.flush()
        except Exception as exc:
            return {"error": f"kunne ikke skrive: {exc}"}
        t = threading.Thread(target=_laes, daemon=True)
        t.start()
        t.join(timeout=_STDIO_TIMEOUT_S)
        if t.is_alive():
            return {"error": f"{self.name} svarede ikke inden {_STDIO_TIMEOUT_S}s"}
        return svar or {"error": "intet svar"}

    def _http_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        try:
            from core.services import mcp_auth
            headers = dict(mcp_auth.resolve_headers(self.name, self.config) or {})
        except Exception as exc:
            # En server uden auth (Context7) skal stadig kunne forbindes: at
            # mangle et token er en gyldig tilstand, ikke en fejl. Men den
            # sluges ikke tavst — den logges, så et brudt auth-modul kan
            # skelnes fra en server der bare ikke kræver nøgle.
            logger.debug("mcp %s: ingen auth-headere (%s)", self.name, exc)
            headers = {}
        # MÅLT 18/10-2026: Context7 svarer `406 Not Acceptable` uden denne.
        # MCP over HTTP må svare enten JSON eller SSE, så klienten skal
        # annoncere at den kan læse BEGGE — ellers afviser serveren før den
        # overhovedet svarer, og det ser ud som om serveren er nede.
        headers.setdefault("Accept", "application/json, text/event-stream")
        return headers

    def _send_http(self, req: dict) -> dict[str, Any]:
        try:
            import httpx
            svar = httpx.post(self.url, json=req, timeout=_HTTP_TIMEOUT_S,
                              headers=self._http_headers())
            if svar.status_code == 401:
                try:
                    from core.services import mcp_auth
                    if mcp_auth.refresh(self.name):
                        svar = httpx.post(self.url, json=req, timeout=_HTTP_TIMEOUT_S,
                                          headers=self._http_headers())
                except Exception as exc:
                    # Refresh er et FORSØG, ikke et krav: fejler den, er det
                    # oprindelige 401 stadig det sande svar, og det returneres
                    # nedenfor. Men den logges — ellers kan et brudt auth-modul
                    # ikke skelnes fra en server der afviser vores token.
                    logger.debug("mcp %s: token-refresh fejlede (%s)", self.name, exc)
            svar.raise_for_status()
            return parse_mcp_http_body(svar.text, svar.headers.get("content-type", ""))
        except Exception as exc:
            return {"error": str(exc)}

    def _send_notification(self, method: str) -> None:
        msg = {"jsonrpc": "2.0", "method": method}
        try:
            if self.transport == "http":
                import httpx
                httpx.post(self.url, json=msg, timeout=_HTTP_TIMEOUT_S,
                           headers=self._http_headers())
            elif self.process and self.process.stdin:
                self.process.stdin.write(json.dumps(msg) + "\n")
                self.process.stdin.flush()
        except Exception:
            pass  # best-effort; en manglende notice maa ikke braekke connect

    def _initialize(self) -> bool:
        """MCP kræver dette håndtryk før alt andet — mange servere afviser
        `tools/list` indtil det er kørt."""
        svar = self._send_request("initialize", {
            "protocolVersion": _PROTOKOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": _KLIENT_NAVN, "version": "2"},
        })
        if "error" in svar:
            self.connect_error = f"initialize fejlede ({self.name}): {svar['error']}"
            return False
        self._send_notification("notifications/initialized")
        return True

    def _discover_tools(self) -> list[dict[str, Any]]:
        svar = self._send_request("tools/list")
        if "error" in svar:
            logger.warning("mcp: tools/list fejlede for %s: %s", self.name, svar["error"])
            return []
        return list((svar.get("result") or {}).get("tools") or [])

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        svar = self._send_request("tools/call",
                                  {"name": tool_name, "arguments": arguments or {}})
        if "error" in svar:
            return {"status": "error", "error": svar["error"]}
        result = svar.get("result")
        if not isinstance(result, dict):
            result = {"status": "ok", "content": str(result)}
        # En fremmed server er praecis den slags kilde der kan vaere SKREVET
        # til at ligne en instruks. Hegnet siger til modellen at det er data.
        try:
            from core.services.untrusted_fencing import fence_tool_result
            return fence_tool_result(f"mcp_{self.name}_{tool_name}", result)
        except Exception:
            return result
