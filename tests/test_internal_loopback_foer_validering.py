"""Loopback-vagten svarer FØR body-validering — ikke efter.

MÅLT 28/10-2026 (side-opgave side-eeb268d69d): `/api/internal` er undtaget
Bearer-token i `_PUBLIC_PATHS`, og hver rute håndhævede loopback-only inde i
funktionskroppen. Det betød at FastAPI's body-validering kørte først: et kald
med `X-Forwarded-For` (præcis hvad Caddy sender) og en UGYLDIG body gav 422
med feltnavne i stedet for 403. Vagten blev aldrig evalueret.

Der var ingen reel eksponering — med gyldig body gav samme kald 403. Men den
uautoriserede klient kunne probe rutens skema, og kommentaren påstod en grænse
koden ikke håndhævede der hvor den blev afprøvet. Samme fejlklasse som
`/api/auth/register` (22/10-2026).

Disse tests værner at vagten ligger som `Depends()` på routeren, så den kører
før validering — og modprøven at et ægte loopback-kald stadig slipper igennem.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _app(router_module: str) -> FastAPI:
    import importlib

    mod = importlib.import_module(router_module)
    app = FastAPI()
    app.include_router(mod.router)
    return app


def _local(app: FastAPI) -> TestClient:
    return TestClient(app, client=("127.0.0.1", 5000))


def _remote(app: FastAPI) -> TestClient:
    return TestClient(app)  # default "testclient" = ikke-loopback


_ROUTERS = [
    "apps.api.jarvis_api.routes.internal_discord",
    "apps.api.jarvis_api.routes.internal_errors",
    "apps.api.jarvis_api.routes.internal_run_stream",
    "apps.api.jarvis_api.routes.internal_runtime_surface",
]


@pytest.mark.parametrize("router_module", _ROUTERS)
def test_dependency_er_sat_paa_routeren(router_module: str) -> None:
    """Vagten SKAL være en router-dependency. Ligger den kun i kroppen, kører
    den efter body-validering og svarer 422 i stedet for 403."""
    import importlib

    mod = importlib.import_module(router_module)
    navne = [getattr(d, "dependency", None).__name__ for d in mod.router.dependencies]
    assert "require_loopback" in navne, (
        f"{router_module} mangler require_loopback som router-dependency — "
        f"fundet: {navne}"
    )


def test_xff_med_ugyldig_body_giver_403_ikke_422() -> None:
    """MODPRØVEN PÅ HELE FIXET.

    Før fixet gav dette kald 422 (Pydantic afviste den tomme body før vagten
    blev kaldt). Nu skal det give 403 — vagten svarer først, så den
    uautoriserede klient får intet at vide om skemaet.
    """
    app = _app("apps.api.jarvis_api.routes.internal_errors")
    r = _local(app).post(
        "/api/internal/errors/report",
        json={},  # bevidst ugyldig: mangler alle påkrævede felter
        headers={"x-forwarded-for": "8.8.8.8", "x-forwarded-proto": "https"},
    )
    assert r.status_code == 403, (
        f"forventede 403 fra vagten, fik {r.status_code}: {r.text[:200]}"
    )
    assert "detail" in r.json()
    # Ingen feltnavne må lække ud til en uautoriseret klient.
    assert "loc" not in r.text


def test_xff_med_gyldig_body_giver_403() -> None:
    """Den oprindelige vej: gyldig body + XFF → 403. Må ikke regressere."""
    app = _app("apps.api.jarvis_api.routes.internal_errors")
    r = _local(app).post(
        "/api/internal/errors/report",
        json={
            "kind": "model.rate_limited", "severity": "warning",
            "recoverable": "retry", "message": "probe", "source": "runtime",
        },
        headers={"x-forwarded-for": "8.8.8.8"},
    )
    assert r.status_code == 403


def test_non_loopback_giver_403() -> None:
    """En fremmed klient afvises uanset body."""
    app = _app("apps.api.jarvis_api.routes.internal_errors")
    r = _remote(app).post("/api/internal/errors/report", json={})
    assert r.status_code == 403


def test_aegte_loopback_slipper_igennem() -> None:
    """MODPRØVE: et ægte, lokalt IPC-kald må ikke blokeres af fixet.

    Uden denne kunne nogen 'løse' opgaven ved at afvise alt.
    """
    app = _app("apps.api.jarvis_api.routes.internal_errors")
    r = _local(app).post(
        "/api/internal/errors/report",
        json={
            "kind": "model.rate_limited", "severity": "warning",
            "recoverable": "retry", "message": "ægte IPC", "source": "runtime",
        },
    )
    assert r.status_code == 202, f"ægte loopback blev blokeret: {r.text[:200]}"


def test_forwarded_header_afvises_ogsaa() -> None:
    """Standard-Forwarded (ikke kun X-Forwarded-For) skal også afvises."""
    app = _app("apps.api.jarvis_api.routes.internal_errors")
    r = _local(app).post(
        "/api/internal/errors/report", json={},
        headers={"forwarded": "for=8.8.8.8"},
    )
    assert r.status_code == 403
