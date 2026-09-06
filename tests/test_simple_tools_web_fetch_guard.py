"""web_fetch: omdirigering revalideres, og samme side hentes ikke to gange.

SSRF-tjekket paa den FOERSTE url er uden vaerdi hvis 302 foelges blindt —
saa peger man bare paa noget offentligt der stiller om indad.
"""
import time

import pytest

from core.tools import simple_tools_web as w


@pytest.fixture(autouse=True)
def _ryd_cache(monkeypatch):
    """Cachen ligger nu i DB'en (delt mellem api og runtime), saa den
    neutraliseres her i stedet for at blive ryddet — testene handler om
    redirect-vaernet og om hentningen sker, ikke om lagringen."""
    gemt: dict[str, str] = {}
    monkeypatch.setattr(w, "_fetch_cache_get", lambda u: gemt.get(u))
    monkeypatch.setattr(w, "_fetch_cache_put", lambda u, r: gemt.__setitem__(u, r))
    yield gemt


def test_redirect_mod_internt_maal_stoppes():
    from core.services.egress_guard import check_redirect_hop
    # Forudsaetningen bag testen: vaernet anser metadata-adressen for usikker.
    assert check_redirect_hop("http://169.254.169.254/latest/meta-data/") ["safe"] is False

    h = w._RevaliderendeRedirect()
    with pytest.raises(Exception) as ei:
        h.redirect_request(
            None, None, 302, "Found", {}, "http://169.254.169.254/latest/meta-data/",
        )
    assert "blokeret" in str(ei.value)


def test_offentlig_redirect_slipper_igennem(monkeypatch):
    kaldt = {}

    def _super(self, req, fp, code, msg, headers, newurl):
        kaldt["url"] = newurl
        return "videre"

    monkeypatch.setattr(
        w.urllib_request.HTTPRedirectHandler, "redirect_request", _super, raising=True,
    )
    ud = w._RevaliderendeRedirect().redirect_request(
        None, None, 302, "Found", {}, "https://example.org/side",
    )
    assert ud == "videre"
    assert kaldt["url"] == "https://example.org/side"


def test_cachen_sparer_andet_kald(monkeypatch):
    kald = {"n": 0}

    class _Svar:
        def read(self):
            kald["n"] += 1
            return b"<html>hej</html>"
        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setattr(
        w.urllib_request, "build_opener", lambda *a: type("O", (), {"open": lambda s, r, timeout=0: _Svar()})(),
    )
    a = w._hent_side("https://example.org/x")
    b = w._hent_side("https://example.org/x")
    assert a == b
    assert kald["n"] == 1, "anden hentning skulle komme fra cachen"


def test_udloebet_cache_henter_igen(monkeypatch):
    monkeypatch.setattr(w, "_fetch_cache_get", lambda u: None)  # altid koldt
    kald = {"n": 0}

    class _Svar:
        def read(self):
            kald["n"] += 1
            return b"x"
        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setattr(
        w.urllib_request, "build_opener", lambda *a: type("O", (), {"open": lambda s, r, timeout=0: _Svar()})(),
    )
    w._hent_side("https://example.org/y")
    time.sleep(0.01)
    w._hent_side("https://example.org/y")
    assert kald["n"] == 2
