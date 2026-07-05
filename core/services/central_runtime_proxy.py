"""Central runtime proxy — read runtime-process-only surfaces from anywhere.

Some central surfaces (self/mind/inner-life) read state that ONLY exists in
the jarvis-runtime process (port 8011). When jarvis-api runs in api-only mode
(``JARVIS_ENABLE_RUNTIME_SERVICES=0``), an in-process read returns empty,
because the daemons live in jarvis-runtime instead.

``proxy_or_local`` transparently picks the right source:

- If runtime services are enabled in this process → call ``local_fn()``
  in-process (the state is local here).
- Otherwise → HTTP-GET the surface from jarvis-runtime and return its JSON.

This mirrors the proven pattern in
``apps/api/jarvis_api/routes/mission_control_living_mind.py::_proxy_runtime_surface``
(same 8011 base URL / ``JARVIS_RUNTIME_PORT`` env, same short timeout).

SELF-SAFE: any failure returns ``{}``. This helper NEVER raises — a missing
runtime surface must never take down the caller.
"""
from __future__ import annotations

import json
import logging
import os
from urllib import request as urllib_request

logger = logging.getLogger(__name__)

# Port where jarvis-runtime exposes its own HTTP server with live process state.
# Matches mission_control_living_mind._RUNTIME_PORT.
_RUNTIME_PORT = int(os.getenv("JARVIS_RUNTIME_PORT", "8011"))
_RUNTIME_PROXY_TIMEOUT = 3  # seconds — fast fallback, never block the caller


def _runtime_services_enabled() -> bool:
    """True when this process runs the runtime services (state is local here)."""
    raw = str(os.getenv("JARVIS_ENABLE_RUNTIME_SERVICES", "")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _http_get(name: str) -> dict:
    """HTTP-GET a runtime surface from jarvis-runtime. Returns a parsed dict.

    Isolated so tests can monkeypatch it. May raise — callers must guard.
    """
    url = f"http://127.0.0.1:{_RUNTIME_PORT}/api/internal/runtime-surface/{name.lstrip('/')}"
    req = urllib_request.Request(url, headers={"Accept": "application/json"})
    with urllib_request.urlopen(req, timeout=_RUNTIME_PROXY_TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data if isinstance(data, dict) else {}


def proxy_or_local(builder_name: str, local_fn) -> dict:
    """Return a runtime surface, in-process or via HTTP-proxy to port 8011.

    - ``JARVIS_ENABLE_RUNTIME_SERVICES`` truthy → ``local_fn()`` in-process.
    - otherwise → HTTP-GET ``/internal/runtime-surface/{builder_name}`` on 8011.

    SELF-SAFE: any exception → ``{}``. Never raises.
    """
    try:
        if _runtime_services_enabled():
            result = local_fn()
        else:
            result = _http_get(builder_name)
        return result if isinstance(result, dict) else {}
    except Exception as exc:  # noqa: BLE001 — self-safe by design
        logger.debug("central_runtime_proxy: %s failed (%s)", builder_name, exc)
        return {}
