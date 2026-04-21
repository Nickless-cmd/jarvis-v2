from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from core.services.heartbeat_runtime import (
    start_heartbeat_scheduler,
    stop_heartbeat_scheduler,
)
from core.services.notification_bridge import (
    start_notification_bridge,
    stop_notification_bridge,
)
from core.services.scheduled_tasks import (
    start_scheduled_tasks_service,
    stop_scheduled_tasks_service,
)
from core.services.runtime_hook_runtime import (
    start_runtime_hook_runtime,
    stop_runtime_hook_runtime,
)
from core.services.approval_feedback_subscriber import (
    start_approval_feedback_subscriber,
    stop_approval_feedback_subscriber,
)
from core.services.mood_oscillator import (
    register_event_listeners as start_mood_listener,
    stop_event_listeners as stop_mood_listener,
)
from core.services.emotion_concepts import (
    register_event_listeners as start_emotion_concept_listener,
    stop_event_listeners as stop_emotion_concept_listener,
)
from core.services.global_workspace import (
    register_event_listeners as start_global_workspace_listener,
    stop_event_listeners as stop_global_workspace_listener,
)
from core.services.discord_gateway import (
    start_discord_gateway,
    stop_discord_gateway,
)
from core.services.telegram_gateway import (
    start_telegram_gateway,
    stop_telegram_gateway,
)
from core.services.voice_daemon import (
    start_voice_daemon,
    stop_voice_daemon,
)
from apps.api.jarvis_api.routes.attachments import router as attachments_router
from apps.api.jarvis_api.routes.files import router as files_router
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


def _runtime_services_enabled() -> bool:
    raw = str(os.getenv("JARVIS_ENABLE_RUNTIME_SERVICES", "1")).strip().lower()
    return raw not in {"0", "false", "no", "off"}


def create_app() -> FastAPI:
    ensure_runtime_dirs()
    init_db()
    ensure_default_workspace()

    mcp_app = create_mcp_app()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime_services_enabled = _runtime_services_enabled()
        logger.info("jarvis api startup begin")
        logger.info(
            "jarvis api startup mode runtime_services_enabled=%s",
            runtime_services_enabled,
        )
        if runtime_services_enabled:
            start_runtime_hook_runtime()
            start_approval_feedback_subscriber()
            start_heartbeat_scheduler()
            start_notification_bridge()
            start_scheduled_tasks_service()
            start_mood_listener()
            start_emotion_concept_listener()
            start_global_workspace_listener()
            start_discord_gateway()
            start_telegram_gateway()
            start_voice_daemon()
            try:
                from core.services.agent_runtime import recover_crashed_agents
                recovery = recover_crashed_agents()
                if recovery["recovered"]:
                    logger.info("agent recovery: %s", recovery)
            except Exception as _exc:
                logger.warning("agent recovery failed: %s", _exc)
            try:
                from core.services.cadence_producers import produce_emergent_signals_from_history
                produce_emergent_signals_from_history()
            except Exception as _exc:
                logger.warning("emergent signal warm-start failed: %s", _exc)
            try:
                from core.services.governance_bootstrap import bootstrap_all
                _gov_result = bootstrap_all()
                logger.info("governance bootstrap: %s", _gov_result)
            except Exception as _exc:
                logger.warning("governance bootstrap failed: %s", _exc)
            event_bus.publish("runtime.started", {"component": "api"})
        logger.info("jarvis api startup complete")
        async with mcp_app.lifespan(app):
            yield
        logger.info("jarvis api shutdown begin")
        if runtime_services_enabled:
            stop_heartbeat_scheduler()
            stop_notification_bridge()
            stop_scheduled_tasks_service()
            stop_discord_gateway()
            stop_telegram_gateway()
            stop_voice_daemon()
            stop_global_workspace_listener()
            stop_emotion_concept_listener()
            stop_mood_listener()
            stop_approval_feedback_subscriber()
            stop_runtime_hook_runtime()
        try:
            from core.browser.playwright_session import stop_browser_session
            stop_browser_session()
        except Exception:
            pass
        if runtime_services_enabled:
            try:
                from core.services.inheritance_seed import write_inheritance_seed
                write_inheritance_seed()
            except Exception:
                pass
        logger.info("jarvis api shutdown complete")

    app = FastAPI(title="Jarvis V2 API", lifespan=lifespan)

    app.include_router(attachments_router)
    app.include_router(files_router)
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
