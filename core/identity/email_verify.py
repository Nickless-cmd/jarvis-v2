"""Email-verifikation (spec 2026-06-15 §5). Token-store i runtime_state_kv,
24h TTL, max 3 pr. email pr. dag. Sender via den eksisterende mail-opsætning
(mail_tools._exec_send_mail → SMTP 587/STARTTLS, credential fra runtime.json).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from core.runtime.db import get_runtime_state_value, set_runtime_state_value

_KEY = "email_verify_tokens"
_MAX_PER_DAY = 3


class RateLimited(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> str:
    return _now().date().isoformat()


def _load() -> list[dict]:
    raw = get_runtime_state_value(_KEY, [])
    return raw if isinstance(raw, list) else []


def _save(items: list[dict]) -> None:
    set_runtime_state_value(_KEY, items[-500:])


def create_token(*, user_id: str, email: str, ttl_hours: int = 24) -> str:
    items = _load()
    day = _today()
    em = (email or "").strip().lower()
    used_today = sum(1 for r in items if r.get("email") == em and r.get("created_day") == day)
    if used_today >= _MAX_PER_DAY:
        raise RateLimited(f"max {_MAX_PER_DAY} verifikations-mails pr. dag for {em}")
    token = uuid.uuid4().hex
    expires = (_now() + timedelta(hours=ttl_hours)).isoformat()
    items.append({"token": token, "user_id": str(user_id), "email": em,
                  "expires_at": expires, "created_day": day})
    _save(items)
    return token


def consume_token(token: str) -> str | None:
    """Returnér user_id hvis token er gyldigt + ikke udløbet; fjern det (engangs)."""
    items = _load()
    now = _now()
    found = None
    rest = []
    for r in items:
        if r.get("token") == token and found is None:
            try:
                exp = datetime.fromisoformat(str(r.get("expires_at")))
            except Exception:
                exp = now - timedelta(seconds=1)
            if exp > now:
                found = str(r.get("user_id"))
            # forbruges uanset (udløbet token fjernes også)
            continue
        rest.append(r)
    if found is not None or len(rest) != len(items):
        _save(rest)
    return found


def _send_mail(args: dict) -> dict:
    from core.tools.mail_tools import _exec_send_mail
    return _exec_send_mail(args)


def send_verification_email(*, user_id: str, email: str, base_url: str) -> str:
    token = create_token(user_id=user_id, email=email)
    link = f"{base_url.rstrip('/')}/api/auth/verify-email?token={token}"
    body = (
        "Hej!\n\nBekræft din email for at aktivere din Jarvis-konto:\n\n"
        f"{link}\n\nLinket udløber om 24 timer. Hvis du ikke har oprettet en "
        "konto, kan du ignorere denne mail.\n\n— Jarvis"
    )
    _send_mail({"to": email, "subject": "Bekræft din Jarvis-konto", "body": body})
    return token
