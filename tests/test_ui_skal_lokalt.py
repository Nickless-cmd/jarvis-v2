"""UI'ens login-side lå selv bag login'et. Døren var låst udefra.

## Målt 15/9-2026

Bjørn: «apps/ui har ikk rigtigt nogen login side... og jeg kan ikk åbene den i
min browser».

    GET http://127.0.0.1:8080/  →  401 {"detail":"authentication required"}

Bagenden havde alt: `/api/auth/login`, `/api/auth/google/start`,
`/api/auth/google/result` er allerede public. Det der manglede var at browseren
kunne hente den HTML der bruger dem.

## Hvorfor kun lokalt

`api.srvlab.dk` peger offentligt på 185.107.14.241 — den er nåelig udefra, og
det er sådan mobilen virker ude. En blank undtagelse ville derfor lægge
login-siden på internettet. Bjørn: «Lad os bar holde den lokalt åben».

## Hvorfor afsender-IP'en kan bæres

Målt før den blev brugt: tre kald gennem Caddy til api.srvlab.dk — ét rent, og
to med forfalsket `X-Forwarded-For` (10.0.0.99 og 8.8.8.8). Alle tre blev
logget som den ægte afsender 10.0.0.20. Caddy og uvicorn tager det betroede
hop, ikke klientens påstand.

## Hvad porten IKKE åbner

Kun skallen — HTML, JS, CSS. Hvert `/mc/*` og `/chat/*` kræver stadig token.
Uden login viser siden en login-skærm og intet andet.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from apps.api.jarvis_api.middleware import jarvisx_user_routing as m


def _req(vaert: str | None):
    return SimpleNamespace(client=SimpleNamespace(host=vaert) if vaert is not None else None)


# ─────────────────────────────────────────────────────────── hvem er lokal

@pytest.mark.parametrize("vaert", ["127.0.0.1", "::1", "10.0.0.20", "192.168.1.5", "172.16.3.9"])
def test_loopback_og_privat_er_lokalt(vaert):
    assert m._er_lokal_afsender(_req(vaert)) is True


@pytest.mark.parametrize("vaert", ["8.8.8.8", "185.107.14.241", "1.1.1.1"])
def test_offentlige_adresser_er_IKKE_lokale(vaert):
    """185.107.14.241 er hans egen offentlige adresse. Kommer kaldet derfra,
    er det udefra."""
    assert m._er_lokal_afsender(_req(vaert)) is False


@pytest.mark.parametrize("vaert", [None, "", "   ", "ikke-en-adresse", "10.0.0.999"])
def test_kan_adressen_ikke_laeses_er_svaret_NEJ(vaert):
    """Fejlretning: en dør man ikke kan se hvem der står foran, skal blive
    lukket. Et manglende `client` må aldrig kunne åbne noget."""
    assert m._er_lokal_afsender(_req(vaert)) is False


# ──────────────────────────────────────────────────────── hvad der åbnes

@pytest.mark.parametrize("sti", ["/", "/index.html", "/assets/index-abc123.js",
                                 "/assets/style.css", "/favicon.ico"])
def test_skallen_er_med(sti):
    assert m._er_ui_skal(sti) is True


@pytest.mark.parametrize("sti", ["/mc/system/health", "/chat/sessions", "/api/auth/pair/create",
                                 "/mc/runs", "/api/dispatches", "/anthropic/v1/messages"])
def test_DATA_er_ikke_med(sti):
    """Hele pointen. Ville disse også åbne, var login'et pynt."""
    assert m._er_ui_skal(sti) is False


def test_assets_uden_skraastreg_er_ikke_et_smuthul():
    """«/assetsmin-hemmelige-rute» må ikke slippe med fordi den starter med de
    samme bogstaver."""
    assert m._er_ui_skal("/assetsmin-rute") is False
    assert m._er_ui_skal("/assets") is False


def test_stien_til_data_aabner_ikke_selv_lokalt():
    """Lokal afsender + data-sti er STADIG lukket. De to betingelser er et
    OG, ikke et ELLER."""
    assert m._er_lokal_afsender(_req("10.0.0.20")) is True
    assert m._er_ui_skal("/chat/sessions") is False


# ───────────────────────────────────────────── og er porten KOBLET i middlewaren?

def test_porten_er_faktisk_koblet_ind():
    """Aftenens gennemgående lektie: en mekanisme ingen kalder er død kode."""
    import ast
    import inspect
    kilde = inspect.getsource(m.jarvisx_user_routing_middleware)
    tree = ast.parse(kilde.strip())
    navne = {n.func.id for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "_er_ui_skal" in navne, "skallen spoerges ikke"
    assert "_er_lokal_afsender" in navne, "afsenderen tjekkes ikke"


# ─────────────────────────────── den SAMMENSATTE beslutning, ikke delene hver for sig

class _Url:
    def __init__(self, sti): self.path = sti


class _Anmodning:
    def __init__(self, sti, vaert, metode="GET"):
        self.method = metode
        self.url = _Url(sti)
        self.headers = {}
        self.client = SimpleNamespace(host=vaert)
        self.state = SimpleNamespace()


async def _svar_paa(sti, vaert, monkeypatch):
    """Kør den ÆGTE middleware og se hvad den beslutter."""
    from core.runtime import jarvisx_auth
    monkeypatch.setattr(jarvisx_auth, "auth_required", lambda: True)

    naaede_igennem = {"ja": False}

    async def _videre(_req):
        naaede_igennem["ja"] = True
        return SimpleNamespace(status_code=200)

    svar = await m.jarvisx_user_routing_middleware(_Anmodning(sti, vaert), _videre)
    return getattr(svar, "status_code", None), naaede_igennem["ja"]


@pytest.mark.asyncio
async def test_lokal_afsender_faar_SKALLEN(monkeypatch):
    kode, igennem = await _svar_paa("/index.html", "10.0.0.20", monkeypatch)
    assert igennem, f"skallen blev afvist lokalt (kode {kode})"


@pytest.mark.asyncio
async def test_lokal_afsender_faar_IKKE_data_uden_token(monkeypatch):
    """Mutationen der overlevede første runde: `and` → `or` i middlewaren gør
    enhver lokal afsender til fuld adgang uden token.

    De to enhedstests kunne ikke se det, fordi de måler hver betingelse for
    sig. Beslutningen er sammensat, så den skal måles sammensat.
    """
    kode, igennem = await _svar_paa("/chat/sessions", "10.0.0.20", monkeypatch)
    assert not igennem, "lokal afsender slap ind paa DATA uden token"
    assert kode == 401, kode


@pytest.mark.asyncio
async def test_fjern_afsender_faar_ikke_engang_skallen(monkeypatch):
    """Det er hele grunden til at det er lokalt og ikke offentligt."""
    kode, igennem = await _svar_paa("/index.html", "185.107.14.241", monkeypatch)
    assert not igennem
    assert kode == 401, kode
