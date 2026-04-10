from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from apps.api.jarvis_api.services.heartbeat_runtime import (
    start_heartbeat_scheduler,
    stop_heartbeat_scheduler,
)
from apps.api.jarvis_api.services.notification_bridge import (
    start_notification_bridge,
    stop_notification_bridge,
)
from apps.api.jarvis_api.services.scheduled_tasks import (
    start_scheduled_tasks_service,
    stop_scheduled_tasks_service,
)
from apps.api.jarvis_api.services.runtime_hook_runtime import (
    start_runtime_hook_runtime,
    stop_runtime_hook_runtime,
)
from apps.api.jarvis_api.routes.chat import router as chat_router
from apps.api.jarvis_api.routes.health import router as health_router
from apps.api.jarvis_api.routes.live import router as live_router
from apps.api.jarvis_api.routes.mission_control import router as mc_router
from apps.api.jarvis_api.routes.openai_compat import router as openai_compat_router
from apps.api.jarvis_api.routes.system_health import router as system_health_router
from apps.api.jarvis_api.mcp_server import create_mcp_app
from core.eventbus.bus import event_bus
from core.identity.workspace_bootstrap import ensure_default_workspace
from core.runtime.bootstrap import ensure_runtime_dirs
from core.runtime.db import init_db

logger = logging.getLogger("uvicorn.error")


def create_app() -> FastAPI:
    ensure_runtime_dirs()
    init_db()
    ensure_default_workspace()

    mcp_app = create_mcp_app()
    app = FastAPI(title="Jarvis V2 API", lifespan=mcp_app.lifespan)

    app.include_router(chat_router)
    app.include_router(health_router)
    app.include_router(mc_router)
    app.include_router(live_router)
    app.include_router(system_health_router, prefix="/mc")
    app.include_router(openai_compat_router)
    app.mount("/mcp", mcp_app)

    # Serve the built React UI from apps/ui/dist — must be LAST so API routes
    # take priority. html=True makes the SPA work (serves index.html for 404s).
    _ui_dist = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "apps", "ui", "dist"
    )
    _ui_dist = os.path.normpath(_ui_dist)
    if os.path.isdir(_ui_dist):
        app.mount("/", StaticFiles(directory=_ui_dist, html=True), name="ui")

    @app.on_event("startup")
    async def on_startup() -> None:
        logger.info("jarvis api startup begin")
        start_runtime_hook_runtime()
        start_heartbeat_scheduler()
        start_notification_bridge()
        start_scheduled_tasks_service()
        event_bus.publish("runtime.started", {"component": "api"})
        logger.info("jarvis api startup complete")

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        logger.info("jarvis api shutdown begin")
        stop_heartbeat_scheduler()
        stop_notification_bridge()
        stop_scheduled_tasks_service()
        stop_runtime_hook_runtime()
        logger.info("jarvis api shutdown complete")

    return app


app = create_app()
