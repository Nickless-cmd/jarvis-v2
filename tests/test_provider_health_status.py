"""Provider-sundhed: «svarede» er ikke «virker».

BAGGRUND (28/10-2026). `provider_health.json` meldte 8/8 «reachable» mens fem af otte
providers svarede med fejlkode: groq 403, mistral 401, opencode 403, gemini 404,
cloudflare 404. Kun tre kunne faktisk bruges.

Årsagen stod som en hensigt i koden: `_ping_host` satte `reachable = exc.code < 500`
med kommentaren «401/403 = host is up, just denying us — that's "reachable" for our
purposes». Det er sandt om HOSTEN og falsk om PROVIDEREN, og det er provideren vi
spørger om.

Testen vogter det der let kollapser igen: at en fejlkode ikke kan tælles som sund.
"""

from __future__ import annotations

import urllib.error

import pytest

from core.services import provider_health_check as phc


# ── klassifikationen ──────────────────────────────────────────────

@pytest.mark.parametrize("code,forventet", [
    (200, "healthy"),
    (204, "healthy"),
    (401, "auth_failed"),
    (403, "auth_failed"),
    (404, "wrong_endpoint"),
    (429, "rate_limited"),
    (400, "bad_request"),
    (500, "unreachable"),
    (503, "unreachable"),
    (None, "unreachable"),
])
def test_http_kode_klassificeres(code, forventet):
    assert phc.classify_http_code(code) == forventet


def test_kun_2xx_er_healthy():
    """Kernen i sagen: en fejlkode må ALDRIG give healthy."""
    for code in (400, 401, 403, 404, 429, 500, 503):
        assert phc.classify_http_code(code) != "healthy", f"{code} blev talt som sund"


# ── ping-funktionen ───────────────────────────────────────────────

def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://x", code, "err", {}, None)  # type: ignore[arg-type]


def test_403_er_ikke_reachable(monkeypatch):
    """Den ægte hændelse: groq svarede 403 og blev talt som reachable."""
    def fake_urlopen(*a, **k):
        raise _http_error(403)

    monkeypatch.setattr(phc.urllib.request, "urlopen", fake_urlopen)
    r = phc._ping_host("https://api.groq.com/openai/v1/models")
    assert r["status"] == "auth_failed"
    assert r["reachable"] is False
    assert r["http_code"] == 403


def test_404_er_ikke_reachable(monkeypatch):
    def fake_urlopen(*a, **k):
        raise _http_error(404)

    monkeypatch.setattr(phc.urllib.request, "urlopen", fake_urlopen)
    r = phc._ping_host("https://generativelanguage.googleapis.com/")
    assert r["status"] == "wrong_endpoint"
    assert r["reachable"] is False


def test_200_er_healthy(monkeypatch):
    class FakeResp:
        def getcode(self):
            return 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(phc.urllib.request, "urlopen", lambda *a, **k: FakeResp())
    r = phc._ping_host("https://openrouter.ai/api/v1/models")
    assert r["status"] == "healthy"
    assert r["reachable"] is True


# ── snapshot'et ───────────────────────────────────────────────────

def test_snapshot_taeller_kun_2xx_som_sunde(monkeypatch):
    """Fem fejlkoder + tre 2xx må give healthy_count=3, ikke 8."""
    koder = {
        "groq": 403, "mistral": 401, "opencode": 403,
        "gemini": 404, "cloudflare": 404,
        "nvidia-nim": 200, "openrouter": 200, "sambanova": 200,
    }

    def fake_ping(url: str):
        for navn, kode in koder.items():
            if navn in url or (navn == "gemini" and "googleapis" in url):
                return {"reachable": kode == 200, "status": phc.classify_http_code(kode),
                        "http_code": kode, "latency_ms": 10}
        return {"reachable": True, "status": "healthy", "http_code": 200, "latency_ms": 10}

    monkeypatch.setattr(phc, "_ping_host", fake_ping)
    monkeypatch.setattr(phc, "_PING_ENDPOINTS", {k: f"https://{k}.example/" for k in koder})
    snap = phc.health_check_all_providers()

    assert snap["healthy_count"] == 3, "fejlkoder blev talt som sunde"
    assert snap["total_count"] == 8
    assert set(snap["auth_failed"]) == {"groq", "mistral", "opencode"}
    assert set(snap["wrong_endpoint"]) == {"gemini", "cloudflare"}


def test_health_section_naevner_auth_fejl(monkeypatch):
    """Sektionen var tavs om netop det den findes for."""
    snap = {
        "results": {}, "unreachable": [], "healthy_count": 3, "total_count": 8,
        "auth_failed": ["groq", "mistral"], "wrong_endpoint": ["gemini"],
    }
    monkeypatch.setattr(phc, "latest_health_snapshot", lambda: snap)
    tekst = phc.health_section()
    assert tekst is not None
    assert "3/8" in tekst
    assert "groq" in tekst and "mistral" in tekst
    assert "gemini" in tekst


def test_health_section_er_tav_naar_alt_virker(monkeypatch):
    snap = {"results": {}, "unreachable": [], "healthy_count": 8, "total_count": 8,
            "auth_failed": [], "wrong_endpoint": []}
    monkeypatch.setattr(phc, "latest_health_snapshot", lambda: snap)
    assert phc.health_section() is None
