from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

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
from apps.api.jarvis_api.services.mood_oscillator import (
    register_event_listeners as start_mood_listener,
    stop_event_listeners as stop_mood_listener,
)
from apps.api.jarvis_api.services.emotion_concepts import (
    register_event_listeners as start_emotion_concept_listener,
    stop_event_listeners as stop_emotion_concept_listener,
)
from apps.api.jarvis_api.services.discord_gateway import (
    start_discord_gateway,
    stop_discord_gateway,
)
from apps.api.jarvis_api.services.voice_daemon import (
    start_voice_daemon,
    stop_voice_daemon,
)
from apps.api.jarvis_api.routes.attachments import router as attachments_router
from apps.api.jarvis_api.routes.chat import router as chat_router
from apps.api.jarvis_api.routes.health import router as health_router
from apps.api.jarvis_api.routes.live import router as live_router
from apps.api.jarvis_api.routes.mission_control import router as mc_router
from apps.api.jarvis_api.routes.openai_compat import router as openai_compat_router
from apps.api.jarvis_api.routes.openai_auth import router as openai_auth_router
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

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("jarvis api startup begin")
        start_runtime_hook_runtime()
        start_heartbeat_scheduler()
        start_notification_bridge()
        start_scheduled_tasks_service()
        start_mood_listener()
        start_emotion_concept_listener()
        start_discord_gateway()
        start_voice_daemon()
        try:
            from apps.api.jarvis_api.services.agent_runtime import recover_crashed_agents
            recovery = recover_crashed_agents()
            if recovery["recovered"]:
                logger.info("agent recovery: %s", recovery)
        except Exception as _exc:
            logger.warning("agent recovery failed: %s", _exc)
        event_bus.publish("runtime.started", {"component": "api"})
        logger.info("jarvis api startup complete")
        async with mcp_app.lifespan(app):
            yield
        logger.info("jarvis api shutdown begin")
        stop_heartbeat_scheduler()
        stop_notification_bridge()
        stop_scheduled_tasks_service()
        stop_discord_gateway()
        stop_voice_daemon()
        stop_emotion_concept_listener()
        stop_mood_listener()
        stop_runtime_hook_runtime()
        logger.info("jarvis api shutdown complete")

    app = FastAPI(title="Jarvis V2 API", lifespan=lifespan)

    app.include_router(attachments_router)
    app.include_router(chat_router)
    app.include_router(health_router)
    app.include_router(mc_router)
    app.include_router(live_router)
    app.include_router(system_health_router, prefix="/mc")
    app.include_router(openai_compat_router)
    app.include_router(openai_auth_router)
    app.mount("/mcp", mcp_app)

    # Serve the built React UI from apps/ui/dist — must be LAST so API routes
    # take priority. html=True makes the SPA work (serves index.html for 404s).
    _ui_dist = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "apps", "ui", "dist"
    )
    _ui_dist = os.path.normpath(_ui_dist)
    if os.path.isdir(_ui_dist):
        app.mount("/", StaticFiles(directory=_ui_dist, html=True), name="ui")

    return app


app = create_app()
