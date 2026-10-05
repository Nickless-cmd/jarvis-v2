"""publish_file: adressen skal virke DER HVOR BRUGEREN ER.

To fejl laa oven i hinanden og gjorde funktionen ubrugelig uden at nogen af
dem saa ud som en fejl.

1. URL'en var hardkodet `http://localhost:8080/...`. Filen blev udgivet helt
   korrekt — og brugeren fik en adresse der kun virker paa den maskine Jarvis
   selv koerer paa. Paa en telefon er `localhost` telefonen.

2. Hallucinations-vagten hentede den URL UDEN Authorization. Ruten kraever
   godkendelse, saa svaret var 401, vagten satte url_verified=False og skrev
   «Praesenter IKKE URL'en for brugeren — den virker ikke». Hver eneste gang.

Funktionen virkede. Vagten maalte et ubeskyttet kald mod en beskyttet rute og
kaldte det et nedbrud.
"""
from __future__ import annotations

from urllib import error as urllib_error

import pytest


#: Udgivne filer blev per bruger 4/10-2026 (`d582882a4`), og
#: `published_file_path()` rejser `NoUserContextError` uden et bruger-id i
#: konteksten — fail-closed, for et fald til en faelles mappe er praecis den
#: laekage afgraensningen lukker. Denne test satte ingen bruger, saa alle fem
#: fik `{"status": "error", "error": "ingen bruger i konteksten"}` og doede paa
#: `KeyError: 'url'`. Produktionen er sund: tre filer er udgivet siden
#: deployet, verificeret paa disken paa CT105 — det var kun soemmet her der
#: manglede.
#:
#: Brugeren skal FINDES: `_user_id_to_workspace_name` slaar op i users.json og
#: SQLite og rejser den samme fejl hvis ingen af dem kender id'et. Et opdigtet
#: id ville altsaa ikke hjaelpe.
_TEST_EMAIL = "udgivelsestest@example.invalid"


@pytest.fixture
def bruger_id() -> str:
    """Et id der kan slaas op. Idempotent, saa de fem tests ikke kolliderer."""
    from core.identity.user_db import create_user, find_user_by_email
    fundet = find_user_by_email(_TEST_EMAIL)
    if fundet is not None:
        return str(fundet["user_id"])
    # detect-secrets ser noegleordet `password`, ikke vaerdien. Brugeren
    # oprettes i conftests skaermede temp-hjem og findes ikke uden for testen.
    ny = create_user(email=_TEST_EMAIL, name="Udgivelsestest",
                     password="kun-i-test",  # pragma: allowlist secret
                     role="owner", workspace="bjorn")
    return str(ny["user_id"])


def _publish(monkeypatch, tmp_path, bruger_id, *, base="", svar=200, fejl=None):
    from core.tools import simple_tools_native as N
    from core.identity.workspace_context import reset_context, set_context
    # `JARVIS_HOME` laeses som MILJOEVARIABEL af `workspace_paths._jarvis_home()`,
    # og conftest peger den allerede paa en skaermet temp-mappe for hver test.
    # Patchene paa modul-attributterne herunder rammer derfor intet laengere;
    # de staar som de gjorde, fordi `simple_tools_native` stadig har sin egen
    # konstant som andre stier kan laese.
    monkeypatch.setattr(N, "JARVIS_HOME", tmp_path, raising=False)
    import core.runtime.config as C
    monkeypatch.setattr(C, "JARVIS_HOME", tmp_path, raising=False)
    import core.runtime.secrets as S
    monkeypatch.setattr(S, "read_runtime_key", lambda k, e=None, **kw: base)

    class _Svar:
        status = svar
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def _open(req, timeout=5):
        if fejl is not None:
            raise fejl
        return _Svar()
    monkeypatch.setattr(N.urllib_request, "urlopen", _open)
    token = set_context(workspace_name="bjorn", user_id=bruger_id, role="owner")
    try:
        return N._exec_publish_file({"filename": "x.html", "content": "<h1>hej</h1>"})
    finally:
        reset_context(token)


def test_adressen_kommer_fra_konfigurationen(monkeypatch, tmp_path, bruger_id):
    r = _publish(monkeypatch, tmp_path, bruger_id, base="https://api.example.dk")
    assert r["url"] == "https://api.example.dk/files/x.html"
    assert "localhost" not in r["url"]
    assert not r.get("kun_lokal")


def test_uden_konfiguration_siges_det_HOEJT(monkeypatch, tmp_path, bruger_id):
    """En localhost-adresse er ikke en fejl paa maskinen, men den kan ikke
    deles. Uden denne besked ville svaret se fuldt gyldigt ud."""
    r = _publish(monkeypatch, tmp_path, bruger_id, base="")
    assert r["url"].startswith("http://localhost:8080/")
    assert r["kun_lokal"] is True
    assert "runtime.json" in r["warning"]


def test_401_betyder_at_ruten_LEVER(monkeypatch, tmp_path, bruger_id):
    """DEN afgoerende. Ruten kraever godkendelse; et afvist ubeskyttet kald er
    bevis paa at noget lytter og beskytter filen — ikke paa at den er brudt."""
    fejl = urllib_error.HTTPError("u", 401, "Unauthorized", {}, None)
    r = _publish(monkeypatch, tmp_path, bruger_id, base="https://api.example.dk", fejl=fejl)
    assert r["url_verified"] is True
    assert "warning" not in r


def test_404_betyder_stadig_at_noget_er_galt(monkeypatch, tmp_path, bruger_id):
    """Kontrolarm. Uden den ville en vagt der accepterede ALT bestaa ovenfor."""
    fejl = urllib_error.HTTPError("u", 404, "Not Found", {}, None)
    r = _publish(monkeypatch, tmp_path, bruger_id, base="https://api.example.dk", fejl=fejl)
    assert r["url_verified"] is False
    assert "404" in r.get("url_verify_error", "")


def test_serveren_nede_er_ogsaa_en_fejl(monkeypatch, tmp_path, bruger_id):
    r = _publish(monkeypatch, tmp_path, bruger_id, base="https://api.example.dk",
                 fejl=OSError("connection refused"))
    assert r["url_verified"] is False


def test_filen_lander_i_brugerens_EGEN_mappe(monkeypatch, tmp_path, bruger_id):
    """Den aendring der braekkede denne fil var ikke pinnet nogen steder.

    4/10-2026 blev udgivne filer per bruger, fordi 151 filer laa i én flad
    `files/`-mappe som enhver autentificeret husstandsbruger kunne hente med
    sit eget token. Uden denne test kan den afgraensning falde tilbage uden at
    noget her bliver roedt.
    """
    from core.runtime.workspace_paths import published_files_dir

    r = _publish(monkeypatch, tmp_path, bruger_id, base="https://api.example.dk")
    assert r["status"] != "error", r.get("error")

    egen = published_files_dir(bruger_id)
    assert (egen / "x.html").exists(), f"filen laa ikke i {egen}"
    assert "/u/" in str(egen), "per-bruger-layoutet er `files/u/<workspace>/`"
    faelles = egen.parent.parent / "x.html"
    assert not faelles.exists(), "en kopi i den FAELLES mappe er selve laekagen"


def test_uden_bruger_i_konteksten_udgives_INTET(monkeypatch, tmp_path):
    """Fail-closed. Et fald til en faelles mappe ville ske tavst.

    Dette er grunden til at de fem tests ovenfor stod roede: de satte ingen
    bruger. Fejlen var rigtig — soemmet var forkert.
    """
    from core.tools import simple_tools_native as N
    import core.runtime.secrets as S
    monkeypatch.setattr(S, "read_runtime_key", lambda k, e=None, **kw: "https://api.example.dk")
    r = N._exec_publish_file({"filename": "y.html", "content": "<h1>nej</h1>"})
    assert r["status"] == "error"
    assert "ingen bruger" in r["error"]
    assert "url" not in r, "en fejlet udgivelse maa ikke returnere en adresse"
