"""OAuth connect-flow til plugin-connectors (16. jun 2026).

/start  — authenticated: bygger authorize-URL bundet til den indloggede bruger;
          desk åbner den i brugerens browser.
/callback — PUBLIC (browseren rammer den uden auth): verificerer signeret `state`,
          bytter code→token, gemmer KRYPTERET pr. bruger i oauth_store. Returnerer
          en lille "luk vinduet"-side.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter()


def _close_page(ok: bool, msg: str) -> HTMLResponse:
    icon = "✅" if ok else "❌"
    html = (
        "<!doctype html><html lang='da'><head><meta charset='utf-8'>"
        "<title>Jarvis — connector</title><style>body{font-family:system-ui;"
        "background:#0e0f13;color:#e6e6e6;display:grid;place-items:center;height:100vh;"
        "margin:0}div{text-align:center;max-width:28rem;padding:2rem}h2{font-weight:600}"
        "p{opacity:.7}</style></head><body><div>"
        f"<h2>{icon} {msg}</h2><p>Du kan lukke dette vindue og gå tilbage til Jarvis.</p>"
        "</div></body></html>"
    )
    return HTMLResponse(html, status_code=200 if ok else 400)


@router.get("/api/oauth/{provider}/start")
async def oauth_start(provider: str) -> JSONResponse:
    """Returnér authorize-URL for den indloggede bruger. Desk åbner den i browseren."""
    from core.identity.workspace_context import current_user_id
    from core.services.oauth_flow import build_authorize_url, is_known_provider
    uid = current_user_id() or ""
    if not uid:
        return JSONResponse({"error": "not_authenticated"}, status_code=401)
    if not is_known_provider(provider):
        return JSONResponse({"error": "unknown_provider"}, status_code=404)
    url = build_authorize_url(provider, uid)
    if not url:
        return JSONResponse({"error": "provider_not_configured"}, status_code=400)
    return JSONResponse({"authorize_url": url})


@router.get("/api/oauth/{provider}/callback")
async def oauth_callback(provider: str, code: str = "", state: str = "", error: str = ""):
    """Browser-callback. Verificér state → byt code → gem token krypteret pr. bruger."""
    import asyncio
    from core.services.oauth_flow import exchange_code, verify_state
    from core.services.oauth_store import save_token
    if error:
        return _close_page(False, "Forbindelsen blev afvist.")
    vs = verify_state(state)
    if not vs or vs[1] != (provider or "").strip().lower() or not code:
        return _close_page(False, "Ugyldig eller udløbet forbindelse — prøv igen fra appen.")
    uid, prov = vs
    tok = await asyncio.to_thread(exchange_code, prov, code)
    if not tok:
        return _close_page(False, "Kunne ikke fuldføre forbindelsen.")
    save_token(uid, prov, tok)
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("oauth.connected", {"user_id": uid, "provider": prov})
    except Exception:
        pass
    return _close_page(True, f"Forbundet til {prov.capitalize()}!")
