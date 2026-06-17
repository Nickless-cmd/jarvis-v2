"""Auth-routes (spec 2026-06-15 §5): register / verify-email / login.

Public (ingen bearer påkrævet). Login kræver email_verified. Password håndteres
kun som hash; klartekst forlader aldrig request-scope.
"""
from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.identity import user_db
from core.runtime.jarvisx_auth import issue_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterReq(BaseModel):
    email: str
    name: str
    password: str


class LoginReq(BaseModel):
    email: str
    password: str


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


@router.post("/register")
def register(req: RegisterReq, request: Request) -> JSONResponse:
    try:
        user, _token = user_db.register_user(
            email=req.email, name=req.name, password=req.password,
            base_url=_base_url(request))
    except ValueError as exc:
        return JSONResponse(status_code=409, content={"ok": False, "error": str(exc)})
    return JSONResponse(content={"ok": True, "user_id": user["user_id"],
                                 "email": user["email"], "email_verified": False})


@router.get("/verify-email")
def verify_email(token: str = Query(...)) -> JSONResponse:
    ok = user_db.verify_email_token(token)
    if not ok:
        return JSONResponse(status_code=400,
                            content={"ok": False, "verified": False,
                                     "error": "ugyldigt eller udløbet token"})
    return JSONResponse(content={"ok": True, "verified": True})


@router.post("/login")
def login(req: LoginReq) -> JSONResponse:
    user = user_db.verify_login(req.email, req.password)
    if not user:
        return JSONResponse(status_code=401,
                            content={"ok": False, "error": "forkert email eller password"})
    if not user["email_verified"]:
        return JSONResponse(status_code=403,
                            content={"ok": False, "error": "email ikke verificeret"})
    tok = issue_token(user_id=user["user_id"], role=user["role"])
    return JSONResponse(content={"ok": True, "token": tok["token"],
                                 "user_id": user["user_id"], "role": user["role"]})


# ── Google app-login (§12) ─────────────────────────────────────────────────
# Login med Google for FORUD-oprettede konti (ingen self-service). Genbruger den
# allerede-registrerede /api/oauth/google/callback via en login-intent i state.

@router.get("/google/start")
def google_login_start(app_id: str = Query("")) -> JSONResponse:
    """Returnér Google authorize-URL + nonce. Appen åbner URL'en i browseren og
    poller /google/result?nonce for det udstedte Jarvis-token."""
    from core.services.oauth_flow import build_authorize_url
    from core.services import google_login
    nonce, state_uid = google_login.begin_login(app_id=app_id)
    url = build_authorize_url("google", state_uid, scopes=["openid", "email"])
    if not url:
        return JSONResponse({"error": "provider_not_configured"}, status_code=400)
    return JSONResponse({"authorize_url": url, "nonce": nonce})


@router.get("/google/result")
def google_login_result(nonce: str = Query(...)) -> JSONResponse:
    """Engangs-hent af login-resultatet. {status: pending|ok|error}."""
    from core.services import google_login
    res = google_login.take_result(nonce)
    if res is None:
        return JSONResponse({"status": "unknown"}, status_code=404)
    return JSONResponse(res)


@router.get("/google/link/start")
def google_link_start() -> JSONResponse:
    """Start Google-linking for den INDLOGGEDE bruger (migration: knyt Gmail til
    eksisterende konto). Kræver auth. Appen poller /google/result?nonce."""
    from core.identity.workspace_context import current_user_id
    from core.services.oauth_flow import build_authorize_url
    from core.services import google_login
    uid = current_user_id() or ""
    if not uid:
        return JSONResponse({"error": "not_authenticated"}, status_code=401)
    nonce, state_uid = google_login.begin_link(uid)
    url = build_authorize_url("google", state_uid, scopes=["openid", "email"])
    if not url:
        return JSONResponse({"error": "provider_not_configured"}, status_code=400)
    return JSONResponse({"authorize_url": url, "nonce": nonce})


# ── QR device-pairing (mobile companion) ───────────────────────────────────

@router.post("/pair/create")
def pair_create() -> JSONResponse:
    """Opret en kort-levende pairing-kode for den INDLOGGEDE bruger. Desktop viser
    den som QR; mobilen scanner + redeem'er. Kræver auth."""
    from core.identity.workspace_context import current_user_id
    from core.services import device_pairing
    uid = current_user_id() or ""
    if not uid:
        return JSONResponse({"error": "not_authenticated"}, status_code=401)
    role = "owner"
    try:
        from core.identity.users import find_user_by_discord_id
        u = find_user_by_discord_id(str(uid))
        role = (getattr(u, "role", "") or "member") if u else "member"
    except Exception:
        role = "member"
    return JSONResponse(device_pairing.create_pairing(uid, role))


class PairRedeemReq(BaseModel):
    code: str


@router.post("/pair/redeem")
def pair_redeem(req: PairRedeemReq) -> JSONResponse:
    """Indløs en pairing-kode → friskt Jarvis-token. PUBLIC (mobilen har intet token endnu)."""
    from core.services import device_pairing
    res = device_pairing.redeem((req.code or "").strip())
    if not res:
        return JSONResponse({"status": "error", "error": "invalid_or_expired"}, status_code=404)
    return JSONResponse(res)
