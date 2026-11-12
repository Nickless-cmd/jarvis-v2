"""Smoke tests for health_monitor_tools.

Specifically guards against the ollama preset URL reverting from
127.0.0.1 back to the old 10.0.0.25 LXC.
"""
from __future__ import annotations


def test_ollama_preset_uses_localhost():
    """The 'ollama' preset endpoint must point at 127.0.0.1, not the
    pre-2026-05-26 LXC 107 (10.0.0.25)."""
    from core.tools.health_monitor_tools import _PRESET_ENDPOINTS
    assert "ollama" in _PRESET_ENDPOINTS
    url = _PRESET_ENDPOINTS["ollama"]
    assert url == "http://127.0.0.1:11434/api/tags", (
        f"ollama preset must be localhost, got {url!r}. See "
        "MEMORY.md reference_ollama_host.md for migration context."
    )
    assert "10.0.0.25" not in url


def test_module_imports_clean():
    from core.tools import health_monitor_tools  # noqa: F401


# ── jarvis-api-preset'et pegede på en port der aldrig lyttede (12/11-2026) ─────
#
# `jarvis-api` → http://localhost:8000/health, men API'et lytter på 8080
# (systemd: --port 8080; resolveren er `jarvisx_bridge._api_port`). Resultatet på
# CT105: `Connection refused` på 0 ms, og værktøjet meldte `UNHEALTHY` om en
# tjeneste der svarede 200 på 2,6 ms. Jarvis tolkede det som «ingen endpoints i
# runtime.json» — værktøjet læser slet ikke runtime.json. En vagt der råber op om
# noget der har det fint æder opmærksomhed fra de rigtige alarmer.
import http.server
import threading

import pytest


@pytest.fixture
def lokal_server():
    class _H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *a):  # stille
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), _H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield srv.server_address[1]
    srv.shutdown()


def test_jarvis_api_preset_bruger_api_portens_kilde(monkeypatch):
    from core.tools.health_monitor_tools import _presets

    monkeypatch.delenv("JARVIS_API_PORT", raising=False)
    assert _presets()["jarvis-api"] == "http://127.0.0.1:8080/health"
    monkeypatch.setenv("JARVIS_API_PORT", "9123")
    assert _presets()["jarvis-api"] == "http://127.0.0.1:9123/health"


def test_runtime_har_sit_eget_preset_paa_runtime_porten(monkeypatch):
    """API'et og runtime er to processer; `/health` på den ene siger intet om den anden."""
    from core.tools.health_monitor_tools import _presets

    monkeypatch.delenv("JARVIS_RUNTIME_PORT", raising=False)
    assert _presets()["jarvis-runtime"] == "http://127.0.0.1:8011/health"


def test_health_check_jarvis_api_rammer_den_konfigurerede_port(monkeypatch, tmp_path, lokal_server):
    """Hele vejen: værktøjet kalder en RIGTIG server på den konfigurerede port."""
    from core.tools import health_monitor_tools as h

    monkeypatch.setattr(h, "_STATE_PATH", tmp_path / "health_monitor.json")
    monkeypatch.setenv("JARVIS_API_PORT", str(lokal_server))

    r = h._exec_health_check({"name": "jarvis-api"})

    assert r["status"] == "ok"
    assert r["url"] == f"http://127.0.0.1:{lokal_server}/health"
    assert (r["reachable"], r["healthy"], r["http_status"], r["error"]) == (True, True, 200, None)
    assert r["text"].startswith("✓ jarvis-api: healthy")


def test_health_status_lister_runtime_og_api_med_deres_urler(monkeypatch, tmp_path):
    from core.tools import health_monitor_tools as h

    monkeypatch.setattr(h, "_STATE_PATH", tmp_path / "health_monitor.json")
    monkeypatch.delenv("JARVIS_API_PORT", raising=False)
    monkeypatch.delenv("JARVIS_RUNTIME_PORT", raising=False)

    urls = {e["name"]: e["url"] for e in h._exec_health_status({})["endpoints"]}

    assert urls["jarvis-api"] == "http://127.0.0.1:8080/health"
    assert urls["jarvis-runtime"] == "http://127.0.0.1:8011/health"
