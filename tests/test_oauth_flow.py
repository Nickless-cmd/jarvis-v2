"""OAuth-flow: signeret state + authorize-URL + code-bytte."""
from __future__ import annotations
import core.services.oauth_flow as of


def test_state_roundtrip():
    s = of.sign_state("u1", "github")
    assert of.verify_state(s) == ("u1", "github")


def test_state_tampered_rejected():
    s = of.sign_state("u1", "github")
    body = s.split(".", 1)[0]
    assert of.verify_state(body + "." + "deadbeef" * 4) is None


def test_state_expired_rejected():
    s = of.sign_state("u1", "github", now=1000.0)
    assert of.verify_state(s, now=1000.0 + 10000) is None


def test_build_authorize_url(monkeypatch):
    monkeypatch.setattr(of, "_secret", lambda k, d="": "CID123" if k.endswith("client_id") else d)
    url = of.build_authorize_url("github", "u1")
    assert url and "client_id=CID123" in url and "state=" in url and "response_type=code" in url
    assert "redirect_uri=https%3A%2F%2Fapi.srvlab.dk%2Fapi%2Foauth%2Fgithub%2Fcallback" in url


def test_build_unknown_or_unconfigured(monkeypatch):
    monkeypatch.setattr(of, "_secret", lambda k, d="": "CID")
    assert of.build_authorize_url("nope", "u1") is None
    monkeypatch.setattr(of, "_secret", lambda k, d="": "")
    assert of.build_authorize_url("github", "u1") is None


def test_exchange_code(monkeypatch):
    monkeypatch.setattr(of, "_secret", lambda k, d="": "x")
    import httpx
    class _R:
        status_code = 200
        def json(self): return {"access_token": "gho_y", "scope": "repo"}
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _R())
    assert of.exchange_code("github", "code123")["access_token"] == "gho_y"


def test_exchange_code_failure(monkeypatch):
    monkeypatch.setattr(of, "_secret", lambda k, d="": "x")
    import httpx
    class _R:
        status_code = 401
        def json(self): return {}
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _R())
    assert of.exchange_code("github", "c") is None


def test_exchange_code_adds_expiry(monkeypatch):
    monkeypatch.setattr(of, "_secret", lambda k, d="": "x")
    import httpx
    class _R:
        status_code = 200
        def json(self): return {"access_token": "a", "expires_in": 3600, "refresh_token": "r"}
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _R())
    tok = of.exchange_code("google", "c", now=1000.0)
    assert tok["expires_at"] == 1000.0 + 3600 and tok["refresh_token"] == "r"


def test_refresh_token(monkeypatch):
    monkeypatch.setattr(of, "_secret", lambda k, d="": "x")
    import httpx
    class _R:
        status_code = 200
        def json(self): return {"access_token": "new", "expires_in": 3600}
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _R())
    tok = of.refresh_token("google", "refresh-abc", now=1000.0)
    assert tok["access_token"] == "new" and tok["expires_at"] == 4600.0
    assert tok["refresh_token"] == "refresh-abc"  # bevares hvis provider ikke returnerer ny


def test_revoke_remote_google(monkeypatch):
    calls = {}
    import httpx
    def _post(url, **k): calls["url"] = url; calls["data"] = k.get("data") or k.get("params")
    class _R: status_code = 200
    monkeypatch.setattr(httpx, "post", lambda url, **k: (_post(url, **k), _R())[1])
    assert of.revoke_remote("google", {"access_token": "tok"}) is True
    assert "oauth2.googleapis.com/revoke" in calls["url"]


# ── tavse fald skal efterlade et spor (31/10-2026) ────────────────────────
#
# MAALT paa den levende detektor: fem fald i denne fil returnerede `None`/`""`
# uden at skrive noget. `refresh_token` var den vaerste — `None` betoed BAADE
# «provideren afviste» (fx `invalid_grant` = doedt refresh-token) OG «kaldet
# gik i stykket». Vagterne her beviser baade at fejlen logger OG at normal
# adfaerd IKKE goer — ellers drukner de aegte fejl i stoej.

def _logget(caplog, tekst):
    return any(tekst in r.getMessage() for r in caplog.records)


def test_secret_logger_naar_runtime_noeglen_ikke_kan_laeses(monkeypatch, caplog):
    import core.runtime.secrets as secrets
    def _braek(key):
        raise OSError("runtime.json utilgaengelig")
    monkeypatch.setattr(secrets, "read_runtime_key", _braek)
    with caplog.at_level("WARNING", logger="core.services.oauth_flow"):
        assert of._secret("github_oauth_client_id", "fallback") == "fallback"
    assert _logget(caplog, "kunne ikke laese runtime-noeglen"), "tavst fald efterlod intet spor"


def test_refresh_token_logger_naar_kaldet_kaster(monkeypatch, caplog):
    import httpx
    def _braek(*a, **k):
        raise httpx.ConnectError("netvaerk nede")
    monkeypatch.setattr(httpx, "post", _braek)
    with caplog.at_level("WARNING", logger="core.services.oauth_flow"):
        assert of.refresh_token("google", "refresh-abc") is None  # fail-soft bevaret
    assert _logget(caplog, "refresh_token for google kastede"), "doedt token kunne ikke skelnes fra netvaerksfejl"


def test_exchange_code_logger_naar_kaldet_kaster(monkeypatch, caplog):
    import httpx
    def _braek(*a, **k):
        raise httpx.ConnectError("netvaerk nede")
    monkeypatch.setattr(httpx, "post", _braek)
    with caplog.at_level("WARNING", logger="core.services.oauth_flow"):
        assert of.exchange_code("github", "code-123") is None
    assert _logget(caplog, "exchange_code for github kastede")


def test_fetch_google_email_logger_naar_kaldet_kaster(monkeypatch, caplog):
    import httpx
    def _braek(*a, **k):
        raise httpx.ConnectError("netvaerk nede")
    monkeypatch.setattr(httpx, "get", _braek)
    with caplog.at_level("WARNING", logger="core.services.oauth_flow"):
        assert of.fetch_google_email({"access_token": "tok"}) == ""
    assert _logget(caplog, "userinfo-kaldet kastede")


def test_state_validering_logger_men_forbliver_fail_closed(monkeypatch, caplog):
    """Et internt sammenbrud maa ALDRIG aabne — men det skal ses."""
    s = of.sign_state("u1", "github")  # signeret FOER sammenbruddet
    def _braek():
        raise RuntimeError("noeglen kunne ikke udledes")
    monkeypatch.setattr(of, "_state_key", _braek)
    with caplog.at_level("WARNING", logger="core.services.oauth_flow"):
        assert of.verify_state(s) is None, "fail-closed brudt: en gyldig state blev accepteret"
    assert _logget(caplog, "state-validering kastede")


def test_normal_afvisning_stoejer_ikke(monkeypatch, caplog):
    """401 fra provideren er et VALGT fald — ikke en fejl. Det maa ikke logge."""
    import httpx
    class _R:
        status_code = 401
        def json(self): return {"error": "invalid_grant"}
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _R())
    with caplog.at_level("WARNING", logger="core.services.oauth_flow"):
        assert of.refresh_token("google", "doedt-refresh") is None
    assert not _logget(caplog, "kastede"), "normal afvisning blev logget som fejl — loggen drukner"
