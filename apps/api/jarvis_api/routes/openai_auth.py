from __future__ import annotations

import html

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

from core.auth.openai_oauth import build_openai_launch_intent, save_openai_callback

router = APIRouter(prefix="/auth/openai", tags=["auth"])


@router.get("/launch")
async def openai_oauth_launch(
    profile: str = Query(default="default"),
) -> JSONResponse:
    launch = build_openai_launch_intent(profile=profile)
    return JSONResponse(
        content={
            "ok": True,
            "provider": "openai",
            "profile": profile,
            "launch": launch,
        }
    )


@router.get("/callback/{profile}")
async def openai_oauth_callback(
    profile: str,
    request: Request,
) -> HTMLResponse:
    callback_url = str(request.url)
    save_openai_callback(profile=profile, callback_url=callback_url)
    safe_profile = html.escape(profile)
    return HTMLResponse(
        content=(
            "<html><body style='font-family: sans-serif; padding: 2rem;'>"
            "<h1>OpenAI OAuth callback received</h1>"
            f"<p>Profile: <code>{safe_profile}</code></p>"
            "<p>Jarvis has stored the callback. Complete the flow with the CLI command:</p>"
            f"<pre>python scripts/jarvis.py exchange-openai-oauth-code --auth-profile {safe_profile}</pre>"
            "</body></html>"
        )
    )
