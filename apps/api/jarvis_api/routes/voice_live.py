"""POST /voice/samtale — åbn en ægte stemme-samtale med Jarvis (LiveKit/WebRTC).

Bjørn 17/9-2026: «det skal være ægte tale og naturlig afbrydelser.. som en
samtale med et menneske». Den gamle samtaletilstand lyttede efter LYDSTYRKE på
en ekstra mikrofon og kunne ikke adskille hans stemme fra Jarvis' egen i
højttaleren. Ægte afbrydelse kræver at mikrofonen er åben HELE tiden, og det
kræver ekko-dæmpning på signalet — det er WebRTC (AEC3), ikke en tærskel.

Arkitektur, alt selvhostet og gratis:

    telefon ⇄ LiveKit-server (CT105)  ⇄  voice-agent (apps/voice_agent)
                                            VAD → whisper → JARVIS → stemme

Denne rute udsteder to billetter, og kun til ejeren:

  1. En LiveKit-billet til telefonen — adgang til ÉT rum.
  2. En kortlivet Jarvis-billet til AGENTEN. Den sendes gennem LiveKits
     agent-dispatch og når aldrig telefonen. Agenten kalder Jarvis ad præcis
     samme vej som appen (/chat/stream/v2), så alle gates, godkendelser og
     log gælder uændret. Ingen intern bagdør der sætter ejer-identitet i hånden.
"""
from __future__ import annotations

import json
import logging
import secrets
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(tags=["voice"])

#: Agent-navnet voice-agent registrerer sig under (eksplicit dispatch).
AGENT_NAVN = "jarvis-stemme"
#: LiveKit lytter lokalt; Caddy sender /rtc* herhen udefra.
_LIVEKIT_LOKAL = "http://127.0.0.1:7880"
#: Hvor længe en samtale-billet gælder. Et opkald er ikke en login-session.
_BILLET_SEKUNDER = 2 * 3600


class SamtaleRequest(BaseModel):
    session_id: str = ""


def _livekit_noegler() -> tuple[str, str]:
    from core.runtime.secrets import read_runtime_key
    try:
        return str(read_runtime_key("livekit_api_key")), str(read_runtime_key("livekit_api_secret"))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="stemme-samtale er ikke sat op (livekit-nøgler mangler)") from exc


def livekit_billet(api_key: str, api_secret: str, *, identitet: str, rum: str,
                   navn: str = "", admin: bool = False, ttl: int = _BILLET_SEKUNDER) -> str:
    """LiveKit-adgangsbillet (JWT HS256, LiveKits eget format)."""
    import jwt
    nu = int(time.time())
    video: dict[str, Any] = {"room": rum, "roomJoin": True, "canPublish": True,
                             "canSubscribe": True, "canPublishData": True}
    if admin:
        video = {"room": rum, "roomAdmin": True, "roomCreate": True}
    krav = {"iss": api_key, "sub": identitet, "nbf": nu - 5, "exp": nu + ttl,
            "name": navn or identitet, "video": video}
    return jwt.encode(krav, api_secret, algorithm="HS256")


def _send_agent(api_key: str, api_secret: str, rum: str, metadata: dict) -> None:
    """Bed LiveKit sende voice-agenten ind i rummet med sin hemmelige metadata."""
    import httpx
    billet = livekit_billet(api_key, api_secret, identitet="jarvis-api", rum=rum, admin=True, ttl=60)
    svar = httpx.post(
        f"{_LIVEKIT_LOKAL}/twirp/livekit.AgentDispatchService/CreateDispatch",
        headers={"Authorization": f"Bearer {billet}", "Content-Type": "application/json"},
        json={"room": rum, "agent_name": AGENT_NAVN, "metadata": json.dumps(metadata)},
        timeout=10,
    )
    if svar.status_code >= 300:
        logger.warning("voice: dispatch fejlede %s %s", svar.status_code, svar.text[:200])
        raise HTTPException(status_code=502, detail="kunne ikke starte stemme-agenten")


@router.post("/voice/samtale")
def aabn_samtale(body: SamtaleRequest, request: Request) -> dict:
    from core.runtime.jarvisx_auth import issue_token, require_owner

    krav = require_owner(request)
    bruger = str(krav.get("sub") or "")
    api_key, api_secret = _livekit_noegler()
    rum = f"stemme-{secrets.token_hex(6)}"

    # Agentens Jarvis-billet: samme ejer, samme app-binding (ellers beder
    # override-reglen om TOTP), kort levetid, og mærket med rummet så en
    # billet i loggen kan spores til sin samtale.
    jarvis = issue_token(
        user_id=bruger, role="owner", ttl_seconds=_BILLET_SEKUNDER,
        app_id=str(krav.get("app_id") or ""),
        extra_claims={"voice_room": rum},
    )["token"]
    _send_agent(api_key, api_secret, rum, {
        "session_id": (body.session_id or "").strip(),
        "jarvis_token": jarvis,
    })
    return {
        "url": "wss://api.srvlab.dk",
        "rum": rum,
        "token": livekit_billet(api_key, api_secret, identitet=f"bruger-{bruger}", rum=rum, navn="Bjørn"),
        "udloeber_sekunder": _BILLET_SEKUNDER,
    }
