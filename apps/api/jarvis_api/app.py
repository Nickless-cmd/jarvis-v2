from __future__ import annotations

from fastapi import FastAPI

from apps.api.jarvis_api.routes.chat import router as chat_router
from apps.api.jarvis_api.routes.health import router as health_router
from apps.api.jarvis_api.routes.live import router as live_router
from apps.api.jarvis_api.routes.mission_control import router as mc_router
from core.eventbus.bus import event_bus
from core.identity.workspace_bootstrap import ensure_default_workspace
from core.runtime.bootstrap import ensure_runtime_dirs
from core.runtime.db import init_db


def create_app() -> FastAPI:
    ensure_runtime_dirs()
    init_db()
    ensure_default_workspace()

    app = FastAPI(title="Jarvis V2 API")

    app.include_router(chat_router)
    app.include_router(health_router)
    app.include_router(mc_router)
    app.include_router(live_router)

    @app.on_event("startup")
    async def on_startup() -> None:
        event_bus.publish("runtime.started", {"component": "api"})

    return app


app = create_app()
