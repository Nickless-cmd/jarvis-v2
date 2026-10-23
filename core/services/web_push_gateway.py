"""Web-push via VAPID — fjerde udgang på push-stakken (side-67aea8c5b6).

Bruger ``pywebpush`` (RFC 8291 / aes128gcm). VAPID-nøglerne ligger i
``runtime.json`` (samme sted som FCM-service-accounten), aldrig i kilden.

Self-safe: enhver fejl giver ``(False, årsag)`` — en web-push må aldrig vælte
den FCM-levering der kører ved siden af.
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_SUBJECT = "mailto:admin@srvlab.dk"


def _key(name: str) -> str:
    """Læs en VAPID-nøgle fra runtime.json. Tom streng hvis den ikke findes."""
    try:
        from core.runtime.secrets import read_runtime_key
    except Exception:  # self-safe: uden secrets-modulet er der ingen noegle at laese
        return ""
    try:
        return str(read_runtime_key(name) or "")
    except Exception:  # self-safe: en laesefejl paa config giver tom noegle, ikke en veltet push
        return ""


def vapid_public_key() -> str:
    """Den offentlige VAPID-nøgle — gives til klienten ved abonnement."""
    return _key("vapid_public_key")


def _der_key(raw: str) -> str:
    """PEM → base64-DER uden headers.

    ``py_vapid.Vapid.from_string`` fjerner kun newlines, ikke PEM-headerne, og
    sender derefter HELE strengen gennem ``b64urldecode``. Med en PEM-nøgle
    bliver ``-----BEGIN…`` dekodet til skrald, og ``load_der_private_key``
    kaster ``ASN.1 parsing error: invalid length`` (målt 23/10-2026: Apple
    afviste intet — vi fejlede før requesten blev sendt).

    Derfor: er nøglen PEM, strip header-linjerne og send kun base64-DER.
    """
    s = (raw or "").strip()
    if "-----BEGIN" not in s:
        return s
    return "".join(
        ln.strip() for ln in s.splitlines()
        if ln.strip() and not ln.strip().startswith("-----")
    )


def send(subscription: dict[str, Any], data: dict[str, Any]) -> tuple[bool, str]:
    """Send én web-push. Returnerer ``(ok, årsag)``.

    ``invalid`` betyder abonnementet er dødt (404/410) og skal slettes — samme
    kontrakt som FCM-stien bruger.
    """
    endpoint = str((subscription or {}).get("endpoint") or "").strip()
    p256dh = str((subscription or {}).get("p256dh") or "").strip()
    auth = str((subscription or {}).get("auth") or "").strip()
    if not (endpoint and p256dh and auth):
        return False, "invalid"
    private_key = _der_key(_key("vapid_private_key"))
    if not private_key:
        return False, "no-vapid"
    try:
        from pywebpush import webpush
    except Exception:  # self-safe: pywebpush er valgfri — uden den leverer FCM alene
        return False, "unavailable"
    try:
        webpush(
            subscription_info={
                "endpoint": endpoint,
                "keys": {"p256dh": p256dh, "auth": auth},
            },
            data=json.dumps(data, ensure_ascii=False),
            vapid_private_key=private_key,
            vapid_claims={"sub": _key("vapid_subject") or _DEFAULT_SUBJECT},
        )
        return True, "ok"
    except Exception as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        if status in (404, 410):
            return False, "invalid"
        logger.warning("web-push: send-fejl: %s", e)
        return False, "error"
