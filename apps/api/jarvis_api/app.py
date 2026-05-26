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
from core.services.recurring_tasks import start_recurring_tasks_service
from core.services.runtime_hook_runtime import (
    start_runtime_hook_runtime,
    stop_runtime_hook_runtime,
)
from core.services.approval_feedback_subscriber import (
    start_approval_feedback_subscriber,
    stop_approval_feedback_subscriber,
)
from core.services.inner_voice_notifier import (
    start_inner_voice_notifier,
    stop_inner_voice_notifier,
)
from core.services.semantic_indexer import (
    start_semantic_indexer,
    stop_semantic_indexer,
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
from core.coding_lane.auto_reviewer import (
    register_event_listeners as start_coding_lane_reviewer,
    stop_event_listeners as stop_coding_lane_reviewer,
)
from core.services.run_closure_gate import (
    start_run_closure_gate,
    stop_run_closure_gate,
)
from core.services.metacognition_signal_tracker import (
    start_metacognition_tracker,
    stop_metacognition_tracker,
)
from core.services.theory_of_mind import (
    start_theory_of_mind_tracker,
    stop_theory_of_mind_tracker,
)
from core.services.spatial_entity_ledger import (
    start_spatial_entity_ledger,
    stop_spatial_entity_ledger,
)
from core.services.session_inbox import (
    start_session_inbox,
    stop_session_inbox,
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
from apps.api.jarvis_api.routes.jarvisx import router as jarvisx_router
from apps.api.jarvis_api.routes.status import router as status_router
from apps.api.jarvis_api.routes.sensory import router as sensory_router
from apps.api.jarvis_api.routes.live import router as live_router
from apps.api.jarvis_api.routes.jarvisx_bridge import router as jarvisx_bridge_router
from apps.api.jarvis_api.routes.mission_control import router as mc_router
from apps.api.jarvis_api.routes.interlanguage_blind import router as interlanguage_blind_router
from apps.api.jarvis_api.routes.cheap_balancer import router as cheap_balancer_router
from apps.api.jarvis_api.routes.agentic_guards import router as agentic_guards_router
from apps.api.jarvis_api.routes.tool_router import router as tool_router_router
from apps.api.jarvis_api.routes.anthropic_compat import router as anthropic_compat_router
from apps.api.jarvis_api.routes.openai_compat import router as openai_compat_router
from apps.api.jarvis_api.routes.openai_auth import router as openai_auth_router
from apps.api.jarvis_api.routes.system_health import router as system_health_router
from apps.api.jarvis_api.routes.internal_discord import router as internal_discord_router
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
        # Register the main asyncio loop so sync tool-handlers can submit
        # bridge-dispatch coroutines via run_coroutine_threadsafe instead
        # of spawning their own loops (which broke cross-loop semantics).
        try:
            import asyncio as _asyncio_mod
            from core.services.jarvisx_bridge import set_main_loop
            set_main_loop(_asyncio_mod.get_running_loop())
        except Exception:
            pass
        if runtime_services_enabled:
            start_runtime_hook_runtime()
            start_approval_feedback_subscriber()
            start_inner_voice_notifier()
            start_semantic_indexer()
            start_heartbeat_scheduler()
            start_notification_bridge()
            start_scheduled_tasks_service()
            start_recurring_tasks_service()
            start_mood_listener()
            start_emotion_concept_listener()
            start_global_workspace_listener()
            start_coding_lane_reviewer()
            start_run_closure_gate()
            start_metacognition_tracker()
            start_theory_of_mind_tracker()
            start_spatial_entity_ledger()
            start_session_inbox()
            start_discord_gateway()
            start_telegram_gateway()
            start_voice_daemon()
            try:
                from core.services.my_projects import ensure_my_projects_running
                _mp_result = ensure_my_projects_running()
                logger.info("my_projects boot spawn: %s", _mp_result)
            except Exception as _exc:
                logger.warning("my_projects boot spawn failed: %s", _exc)
            try:
                from core.services.process_watcher import start_watcher_daemon
                start_watcher_daemon()
                logger.info("process_watcher daemon started")
            except Exception as _exc:
                logger.warning("process_watcher start failed: %s", _exc)
            try:
                from core.services.self_repair_engine import start_listener as start_self_repair
                start_self_repair()
                logger.info("self_repair_engine listener started")
            except Exception as _exc:
                logger.warning("self_repair_engine start failed: %s", _exc)
            try:
                from core.services.experience_correction_listener import (
                    start_listener as start_experience_correction,
                )
                start_experience_correction()
                logger.info("experience_correction listener started")
            except Exception as _exc:
                logger.warning("experience_correction start failed: %s", _exc)
            try:
                from core.services.living_executive import start_listener as start_living_executive
                start_living_executive()
                logger.info("living_executive listener started")
            except Exception as _exc:
                logger.warning("living_executive start failed: %s", _exc)
            try:
                from core.services.agency_cartographer import start_agency_cartographer_daemon
                start_agency_cartographer_daemon()
                logger.info("agency_cartographer daemon started")
            except Exception as _exc:
                logger.warning("agency_cartographer start failed: %s", _exc)
            try:
                from core.services.system_cartographer import start_system_cartographer_daemon
                start_system_cartographer_daemon()
                logger.info("system_cartographer daemon started")
            except Exception as _exc:
                logger.warning("system_cartographer start failed: %s", _exc)
            try:
                from core.services.jarvis_brain_daemon import start_brain_daemon
                start_brain_daemon()
                logger.info("jarvis_brain daemon started")
            except Exception as _exc:
                logger.warning("jarvis_brain daemon start failed: %s", _exc)
            try:
                from core.services.tool_router_runtime import start_tool_router_runtime
                start_tool_router_runtime()
                logger.info("tool_router_runtime daemon started")
            except Exception as _exc:
                logger.warning("tool_router_runtime start failed: %s", _exc)
            try:
                # Cadence scheduler — decoupled from heartbeat (2026-05-13).
                # Was: heartbeat called cadence at end of tick. But heartbeat
                # gets blocked during active-chat-gate or already-ticking,
                # which silently killed cache-warmer + other cadence
                # producers. Now runs independently every 60s.
                from core.services.internal_cadence import start_cadence_scheduler
                start_cadence_scheduler()
                logger.info("cadence_scheduler daemon started")
            except Exception as _exc:
                logger.warning("cadence_scheduler start failed: %s", _exc)
            try:
                from core.services.counterfactual_engine_runtime import start_counterfactual_runtime
                start_counterfactual_runtime()
                logger.info("counterfactual_runtime daemon started")
            except Exception as _exc:
                logger.warning("counterfactual_runtime start failed: %s", _exc)
            try:
                from core.services.forgetting_runtime import start_forgetting_runtime
                start_forgetting_runtime()
                logger.info("forgetting_runtime daemon started")
            except Exception as _exc:
                logger.warning("forgetting_runtime start failed: %s", _exc)
            try:
                from core.services.user_temperature_runtime import start_user_temperature_runtime
                start_user_temperature_runtime()
                logger.info("user_temperature_runtime daemon started")
            except Exception as _exc:
                logger.warning("user_temperature_runtime start failed: %s", _exc)
            try:
                from core.services.agent_runtime import recover_crashed_agents
                recovery = recover_crashed_agents()
                if recovery["recovered"]:
                    logger.info("agent recovery: %s", recovery)
            except Exception as _exc:
                logger.warning("agent recovery failed: %s", _exc)
            try:
                # Sweep jobs_engine zombies — "running" jobs from a dead
                # process that never reached completed/error. Without this,
                # periodic_jobs_scheduler can silently lose recurring work
                # (e.g. wakeup_dispatch) because zombies look like recent
                # activity inside the cadence window.
                from core.services.jobs_engine import sweep_zombie_jobs
                _zsr = sweep_zombie_jobs(stale_seconds=600)
                if _zsr.get("swept", 0):
                    logger.info("jobs_engine zombie sweep: %s", _zsr)
            except Exception as _exc:
                logger.warning("jobs_engine zombie sweep failed: %s", _exc)
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
            try:
                from core.identity.user_attribution_migrations import run_user_attribution_migrations
                _attr_result = run_user_attribution_migrations()
                logger.info("user_attribution migrations: added=%d present=%d",
                            len(_attr_result.get("added", [])),
                            len(_attr_result.get("already_present", [])))
            except Exception as _exc:
                logger.warning("user_attribution migrations failed: %s", _exc)
            event_bus.publish("runtime.started", {"component": "api"})
        # Send restart confirmation if pending
        from core.tools.restart_self_tools import send_pending_restart_confirmation
        try:
            send_pending_restart_confirmation()
        except Exception as _exc:
            logger.warning("restart confirmation check failed: %s", _exc)

        # Pre-warm prompt-assembly caches in EVERY worker process. Each
        # uvicorn worker has its own module-level cache for
        # build_runtime_awareness_signal_surface; without warm-up the
        # first visible turn that lands on a fresh worker pays a ~7s
        # cold-call cost. Run in background thread so startup itself
        # doesn't block. Two limits (8 default, 6 from autonomy_pressure
        # / proactive_question_gate) — warm both slots.
        try:
            import threading
            def _prewarm_prompt_caches() -> None:
                try:
                    from core.services.runtime_awareness_signal_tracking import (
                        build_runtime_awareness_signal_surface,
                    )
                    build_runtime_awareness_signal_surface(limit=8)
                    build_runtime_awareness_signal_surface(limit=6)
                    logger.info("prompt-cache prewarm complete")
                except Exception as _e:
                    logger.warning("prompt-cache prewarm failed: %s", _e)
            threading.Thread(
                target=_prewarm_prompt_caches,
                name="prompt-cache-prewarm",
                daemon=True,
            ).start()
        except Exception as _exc:
            logger.warning("prompt-cache prewarm dispatch failed: %s", _exc)

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
            try:
                from core.services.process_watcher import stop_watcher_daemon
                stop_watcher_daemon()
            except Exception:
                pass
            try:
                from core.services.self_repair_engine import stop_listener as stop_self_repair
                stop_self_repair()
            except Exception:
                pass
            try:
                from core.services.living_executive import stop_listener as stop_living_executive
                stop_living_executive()
            except Exception:
                pass
            try:
                from core.services.agency_cartographer import stop_agency_cartographer_daemon
                stop_agency_cartographer_daemon()
            except Exception:
                pass
            try:
                from core.services.system_cartographer import stop_system_cartographer_daemon
                stop_system_cartographer_daemon()
            except Exception:
                pass
            try:
                from core.services.jarvis_brain_daemon import stop_brain_daemon
                stop_brain_daemon()
            except Exception:
                pass
            try:
                from core.services.tool_router_runtime import stop_tool_router_runtime
                stop_tool_router_runtime()
            except Exception:
                pass
            try:
                from core.services.counterfactual_engine_runtime import stop_counterfactual_runtime
                stop_counterfactual_runtime()
            except Exception:
                pass
            try:
                from core.services.forgetting_runtime import stop_forgetting_runtime
                stop_forgetting_runtime()
            except Exception:
                pass
            try:
                from core.services.user_temperature_runtime import stop_user_temperature_runtime
                stop_user_temperature_runtime()
            except Exception:
                pass
            stop_global_workspace_listener()
            stop_coding_lane_reviewer()
            stop_emotion_concept_listener()
            stop_mood_listener()
            stop_semantic_indexer()
            stop_inner_voice_notifier()
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

    # JarvisX user-routing — binds workspace ContextVars from the
    # X-JarvisX-User header injected by the desktop app. Webchat / Discord
    # / Telegram paths are unaffected (no header → default context).
    from apps.api.jarvis_api.middleware.jarvisx_user_routing import (
        jarvisx_user_routing_middleware,
    )
    app.middleware("http")(jarvisx_user_routing_middleware)

    app.include_router(attachments_router)
    app.include_router(files_router)
    app.include_router(chat_router)
    app.include_router(health_router)
    app.include_router(jarvisx_router)
    app.include_router(status_router)
    app.include_router(sensory_router)
    app.include_router(mc_router)
    app.include_router(interlanguage_blind_router)
    app.include_router(cheap_balancer_router)
    app.include_router(agentic_guards_router)
    app.include_router(tool_router_router)
    app.include_router(anthropic_compat_router)
    app.include_router(live_router)
    app.include_router(jarvisx_bridge_router)
    app.include_router(system_health_router, prefix="/mc")
    app.include_router(openai_compat_router)
    app.include_router(openai_auth_router)
    app.include_router(internal_discord_router)
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
