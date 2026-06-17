"""Google app-login (§12) — kort-levende login-resultat-store + orkestrering.

Flow: appen kalder /auth/google/start → får authorize_url + nonce → åbner browser.
Google-callbacken (genbruger /api/oauth/google/callback) ser en login/link-intent i
state og kalder `complete_*` her. Appen poller /auth/google/result?nonce for at hente
det udstedte Jarvis-token (engangs, kort TTL).

Sikkerhed/GDPR:
- Google-login er IKKE self-service: kun en FORUD-oprettet konto med matchende
  google_email_hash kan logge ind. Intet match → fejl, ingen konto oprettes.
- Vi gemmer aldrig rå Google-email — kun det deterministiske hash (i user_db).
- Resultatet er engangs + udløber (TTL) så et lækket nonce ikke kan genbruges.
"""
from __future__ import annotations

import secrets
import time

_TTL = 300.0
_LOGIN_PREFIX = "__login__:"
_LINK_PREFIX = "__link__:"
_RESULTS: dict[str, dict] = {}


def _gc(now: float) -> None:
    for k in [k for k, v in _RESULTS.items() if v.get("exp", 0) < now]:
        _RESULTS.pop(k, None)


def begin_login(app_id: str = "", *, now: float | None = None) -> tuple[str, str]:
    """Start et login. Returnerer (nonce, state_uid) — state_uid lægges i OAuth-state."""
    t = now if now is not None else time.time()
    _gc(t)
    nonce = secrets.token_urlsafe(18)
    _RESULTS[nonce] = {"status": "pending", "exp": t + _TTL}
    return nonce, f"{_LOGIN_PREFIX}{nonce}:{app_id}"


def begin_link(user_id: str, *, now: float | None = None) -> tuple[str, str]:
    """Start en Google-linking for en EKSISTERENDE (indlogget) bruger."""
    t = now if now is not None else time.time()
    _gc(t)
    nonce = secrets.token_urlsafe(18)
    _RESULTS[nonce] = {"status": "pending", "exp": t + _TTL}
    return nonce, f"{_LINK_PREFIX}{user_id}:{nonce}"


def is_login_state(state_uid: str) -> bool:
    return (state_uid or "").startswith((_LOGIN_PREFIX, _LINK_PREFIX))


def complete(state_uid: str, google_email: str, *, now: float | None = None) -> str:
    """Kaldt af callbacken med den VERIFICEREDE Google-email. Returnerer en kort
    bruger-besked til "luk vinduet"-siden. Stasher resultatet under nonce."""
    t = now if now is not None else time.time()
    from core.identity import user_db
    if state_uid.startswith(_LOGIN_PREFIX):
        rest = state_uid[len(_LOGIN_PREFIX):]
        nonce, _, app_id = rest.partition(":")
        if not google_email:
            _RESULTS[nonce] = {"status": "error", "error": "no_email", "exp": t + _TTL}
            return "Kunne ikke læse din Google-email."
        user = user_db.find_user_by_google_email(google_email)
        if not user:
            _RESULTS[nonce] = {"status": "error", "error": "no_account", "exp": t + _TTL}
            return "Ingen Jarvis-konto er knyttet til denne Google-konto."
        from core.runtime.jarvisx_auth import issue_token
        tok = issue_token(user_id=user["user_id"], role=user.get("role", "member"), app_id=app_id or "")
        _RESULTS[nonce] = {
            "status": "ok", "token": tok["token"], "user_id": user["user_id"],
            "role": user.get("role", "member"), "exp": t + _TTL,
        }
        return f"Logget ind som {user.get('name') or 'bruger'} — gå tilbage til appen."
    if state_uid.startswith(_LINK_PREFIX):
        rest = state_uid[len(_LINK_PREFIX):]
        uid, _, nonce = rest.rpartition(":")
        if not google_email or not uid:
            _RESULTS[nonce] = {"status": "error", "error": "no_email", "exp": t + _TTL}
            return "Kunne ikke knytte Google-kontoen."
        user_db.set_google_email(uid, google_email)
        _RESULTS[nonce] = {"status": "ok", "linked": True, "exp": t + _TTL}
        return "Google-konto knyttet — du kan nu logge ind med Google."
    return "Ukendt login-tilstand."


def take_result(nonce: str, *, now: float | None = None) -> dict | None:
    """Engangs-hent af login-resultatet (fjernes ved hentning når det er færdigt)."""
    t = now if now is not None else time.time()
    _gc(t)
    r = _RESULTS.get(nonce)
    if not r:
        return None
    if r.get("status") == "pending":
        return {"status": "pending"}
    _RESULTS.pop(nonce, None)  # engangs
    return {k: v for k, v in r.items() if k != "exp"}
