"""`GET /chat/artifacts` — ejer-laast, og svarer med listen."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


def _app(ejer: bool) -> TestClient:
    from apps.api.jarvis_api.routes.chat_artifacts import router
    from core.runtime.jarvisx_auth import require_owner

    def _vagt() -> None:
        if not ejer:
            raise HTTPException(status_code=403, detail="kun ejeren")

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[require_owner] = _vagt
    return TestClient(app)


def test_svarer_med_listen(isolated_runtime) -> None:
    r = _app(ejer=True).get("/chat/artifacts", params={"root": "/media/projects/jarvis-v2"})
    assert r.status_code == 200
    krop = r.json()
    assert krop["ok"] is True
    assert isinstance(krop["artifacts"], list)
    assert "scanned" in krop


# Svaret viser stier og aendringer fra HELE historikken — ikke for andre end ejeren.
def test_er_ejer_laast(isolated_runtime) -> None:
    r = _app(ejer=False).get("/chat/artifacts", params={"root": "/media/projects/jarvis-v2"})
    assert r.status_code == 403


def test_ruten_er_registreret_i_appen() -> None:
    from apps.api.jarvis_api.app import app
    stier = {getattr(r, "path", "") for r in app.routes}
    assert "/chat/artifacts" in stier
