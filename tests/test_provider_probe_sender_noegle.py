"""Proben skal spørge SOM OS — ikke som en anonym fremmed.

BAGGRUND (29/10-2026). `provider_health_check` meldte fem af otte providere døde:

    mistral     401 auth_failed      → virkeligheden: 200
    gemini      404 wrong_endpoint   → virkeligheden: 200
    opencode    403 (proben pingede opencode.ai, men provideren er LOKAL)
    groq        403 «error code: 1010» → Cloudflares UA-blok, ikke nøglen
    cloudflare  404 (rod-URL; /models findes ikke, /ai/models/search gør)

Tre fejl oveni hinanden, og alle tre gjorde signalet utilregneligt på samme måde:
det målte VORES forespørgsel og kaldte svaret providerens helbred.

Disse tests værner hver af de tre:
  1. nøglen sendes med (og gemini får den i den header den vil have)
  2. der sendes en User-Agent (ellers blokerer Cloudflare med 1010)
  3. URL'en kommer fra `provider_router.json` — den ene sandhed om hvor provideren bor
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def ph():
    import core.services.provider_health_check as mod
    return mod


def _creds(monkeypatch, **values):
    monkeypatch.setattr(
        "core.auth.profiles.get_provider_credentials",
        lambda *, profile, provider: dict(values),
    )


def _router(monkeypatch, ph, entry: dict):
    monkeypatch.setattr(ph, "_router_providers", lambda: {"groq": entry})


# ── 1. nøglen ────────────────────────────────────────────────────────────────

def test_proben_sender_vores_noegle(monkeypatch, ph):
    """Uden nøgle måler 401/403 vores adgang — ikke providerens helbred."""
    _creds(monkeypatch, api_key="gsk_hemmelig")  # pragma: allowlist secret
    _router(monkeypatch, ph, {"base_url": "https://api.groq.com/openai/v1",
                              "auth_profile": "groq"})
    req = ph._probe_request("groq")
    assert req["has_credentials"] is True
    assert req["headers"]["Authorization"] == "Bearer gsk_hemmelig"


def test_gemini_faar_noeglen_i_x_goog_api_key(monkeypatch, ph):
    """Gemini afviser `Authorization: Bearer` — den vil have x-goog-api-key."""
    _creds(monkeypatch, api_key="AIzahemmelig")  # pragma: allowlist secret
    monkeypatch.setattr(ph, "_router_providers",
                        lambda: {"gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta",
                                            "auth_profile": "gemini"}})
    req = ph._probe_request("gemini")
    assert req["headers"]["x-goog-api-key"] == "AIzahemmelig"
    assert "Authorization" not in req["headers"]


# ── 2. User-Agent ────────────────────────────────────────────────────────────

def test_proben_sender_user_agent(monkeypatch, ph):
    """Cloudflare svarer urllib's standard-UA med `403 error code: 1010`.

    Det er samme fælde som ntfy-403'erne: et 403 kan betyde «du ligner en bot»,
    ikke «nøglen er ugyldig». Målt: groq gik fra 403 til 200 alene ved denne header.
    """
    _creds(monkeypatch, api_key="k")
    _router(monkeypatch, ph, {"base_url": "https://api.groq.com/openai/v1",
                              "auth_profile": "groq"})
    req = ph._probe_request("groq")
    assert req["headers"].get("User-Agent"), "proben sender ingen User-Agent"


def test_ping_host_sender_headere_videre(monkeypatch, ph):
    """`_ping_host` skal faktisk bruge de headere den får — ellers er de dekoration."""
    set_headers = {}

    class _Resp:
        def getcode(self):
            return 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None):
        set_headers.update(dict(req.header_items()))
        return _Resp()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    ph._ping_host("https://x.example/models", {"Authorization": "Bearer k",
                                               "User-Agent": "JarvisHealthCheck/1.0"})
    # urllib normaliserer header-navne til Titel-Case
    assert set_headers.get("Authorization") == "Bearer k"
    assert set_headers.get("User-agent") or set_headers.get("User-Agent")


def test_health_check_giver_headere_videre_til_ping(monkeypatch, ph):
    """KÆDEN — ikke kun delene.

    Modprøve 29/10-2026: fjernede jeg ``headers`` fra kaldet i
    ``health_check_all_providers``, stod alle tests stadig grønne. De testede hver
    især ``_probe_request`` eller ``_ping_host`` isoleret, så netop den søm der bandt
    dem sammen var udækket — og det var den søm der var brudt i virkeligheden:
    nøglen blev bygget og derefter aldrig sendt.
    """
    kald: list[tuple[str, dict]] = []

    def fake_ping(url, headers=None):
        kald.append((url, dict(headers or {})))
        return {"reachable": True, "status": "healthy", "http_code": 200, "latency_ms": 1}

    monkeypatch.setattr(ph, "_PING_ENDPOINTS", {"groq": "https://api.groq.com/openai/v1"})
    monkeypatch.setattr(ph, "_probe_request", lambda p: {
        "url": "https://api.groq.com/openai/v1/models",
        "headers": {"Authorization": "Bearer k", "User-Agent": "UA"},
        "has_credentials": True})
    monkeypatch.setattr(ph, "_ping_host", fake_ping)
    ph.health_check_all_providers()

    assert kald, "proben blev slet ikke kørt"
    url, headers = kald[0]
    assert url.endswith("/models")
    assert headers.get("Authorization") == "Bearer k", "nøglen blev bygget men ikke sendt"
    assert headers.get("User-Agent") == "UA"


# ── 3. URL'en ────────────────────────────────────────────────────────────────

def test_proben_laeser_base_url_fra_routeren(monkeypatch, ph):
    """Routeren er sandheden om hvor provideren bor — ikke en håndskreven kopi."""
    _creds(monkeypatch, api_key="k")
    _router(monkeypatch, ph, {"base_url": "https://flyttet.example/v9",
                              "auth_profile": "groq"})
    assert ph._probe_request("groq")["url"] == "https://flyttet.example/v9/models"


def test_cloudflare_probes_uden_v1(monkeypatch, ph):
    """Routerens cloudflare-base peger på `.../ai/v1`; model-kataloget ligger FØR `/v1`.

    Målt 29/10-2026: med `/v1` beholdt gav stien 405, uden gav den 200.
    """
    _creds(monkeypatch, api_key="k", account_id="acct123")
    monkeypatch.setattr(ph, "_router_providers", lambda: {"cloudflare": {
        "base_url": "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1",
        "auth_profile": "cloudflare"}})
    url = ph._probe_request("cloudflare")["url"]
    assert url == "https://api.cloudflare.com/client/v4/accounts/acct123/ai/models/search"
    assert "/ai/v1/" not in url


# ── 4. «ingen nøgle» er ikke «provideren er død» ─────────────────────────────

def test_uden_noegle_bliver_status_no_credentials(monkeypatch, ph):
    """Før blev en manglende lokal nøgle rapporteret som en udfaldende udbyder."""
    _creds(monkeypatch)  # tomme credentials
    _router(monkeypatch, ph, {"base_url": "https://api.groq.com/openai/v1",
                              "auth_profile": "groq"})
    monkeypatch.setattr(ph, "_PING_ENDPOINTS", {"groq": "https://api.groq.com/openai/v1"})
    monkeypatch.setattr(ph, "_ping_host",
                        lambda url, headers=None: pytest.fail("skal ikke pinge uden nøgle"))
    snap = ph.health_check_all_providers()
    assert snap["results"]["groq"]["status"] == "no_credentials"
    assert snap["no_credentials"] == ["groq"]
    assert snap["auth_failed"] == [], "en manglende nøgle må ikke meldes som afvist nøgle"


def test_cloudflare_uden_account_id_er_no_credentials(monkeypatch, ph):
    """Uden account_id kan stien ikke bygges — det er en lokal mangel, ikke et udfald."""
    _creds(monkeypatch, api_key="k")
    monkeypatch.setattr(ph, "_router_providers", lambda: {"cloudflare": {
        "base_url": "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1",
        "auth_profile": "cloudflare"}})
    req = ph._probe_request("cloudflare")
    assert req["url"] == ""
    assert req["has_credentials"] is False


def test_manglende_router_entry_falder_tilbage_paa_konstanten(monkeypatch, ph):
    """Kan config ikke læses, skal proben stadig have et sted at spørge."""
    _creds(monkeypatch, api_key="k")
    monkeypatch.setattr(ph, "_router_providers", lambda: {})
    assert ph._probe_request("groq")["url"] == "https://api.groq.com/openai/v1/models"
