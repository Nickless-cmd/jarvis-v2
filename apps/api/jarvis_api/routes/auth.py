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
