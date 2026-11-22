"""Small Desk-facing operational routers grouped for app registration."""
from fastapi import APIRouter

from apps.api.jarvis_api.routes.github import router as github_router
from apps.api.jarvis_api.routes.git_panel import router as git_panel_router
from apps.api.jarvis_api.routes.tool_hooks import router as tool_hooks_router

router = APIRouter()
router.include_router(tool_hooks_router)
router.include_router(github_router)
router.include_router(git_panel_router)
