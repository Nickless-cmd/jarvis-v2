"""Legitimation paa en WebSocket — uden at skrive tokenet i adgangsloggen.

## Hvorfor den findes (15/9-2026)

`/ws` streamer hele event-bussen og havde INGEN auth. Middlewaren er registreret
som ``app.middleware("http")``, saa WebSockets gaar uden om den helt. Maalt: en
forbindelse uden token gav straks rigtige interne events, og Caddy videresender
alle stier paa det offentligt naaelige api.srvlab.dk.

Hvad der laa i stroemmen (sidste time paa bussen, maalt foer rettelsen):

    thought_stream.fragment_generated        hans indre stemme
    private_brain.continuity_completed
    reasoning.conclusion.captured      1.144
    cognitive_state.somatic_body_updated

Det er ikke telemetri.

## Hvorfor subprotokol og ikke ?token=

Browsere kan ikke saette headers paa en WebSocket, saa tokenet skal ind ad en
anden vej. Den naerliggende er en query-parameter — og den er forkert her:
uvicorns adgangslog skriver hele stien med query, saa hver eneste forbindelse
ville laegge et gyldigt token i journalen.

``Sec-WebSocket-Protocol`` kan browseren derimod saette, og den logges ikke.
Klienten byder ``[_SUBPROTOKOL, <token>]``, serveren bekraefter kun navnet.

Headeren accepteres ogsaa, for klienter der ikke er en browser.
"""
from __future__ import annotations

from typing import Any, Mapping

SUBPROTOKOL = "jarvis-bearer"


def _foerste_bearer(vaerdi: str) -> str:
    v = (vaerdi or "").strip()
    if v.lower().startswith("bearer "):
        return v[7:].strip()
    return ""


def token_fra_handshake(headers: Mapping[str, str]) -> tuple[str, str | None]:
    """Find tokenet i et WS-handshake.

    Returnerer ``(token, subprotokol_der_skal_bekraeftes)``. Den anden vaerdi er
    ``None`` naar klienten ikke bad om en subprotokol — saa maa serveren heller
    ikke vaelge én, for en browser afviser en protokol den ikke selv bad om.

    Begge veje stoettes, og headeren vinder: en klient der kan saette headers
    har ikke brug for omvejen.
    """
    h = {str(k).lower(): str(v) for k, v in dict(headers or {}).items()}

    fra_header = _foerste_bearer(h.get("authorization", ""))

    raa = h.get("sec-websocket-protocol", "")
    dele = [d.strip() for d in raa.split(",") if d.strip()]
    bad_om = SUBPROTOKOL if SUBPROTOKOL in dele else None

    fra_sub = ""
    if bad_om is not None:
        i = dele.index(SUBPROTOKOL)
        # Tokenet er delen LIGE efter navnet. Staar navnet sidst, bad klienten
        # om protokollen uden at sende noget — det er ikke legitimation.
        if i + 1 < len(dele):
            fra_sub = dele[i + 1]

    return (fra_header or fra_sub), bad_om


def verificer(token: str) -> dict[str, Any] | None:
    """Verificér tokenet. Returnerer claims, eller None hvis det ikke holder.

    Self-safe: enhver fejl er et NEJ. Fejlretningen er vigtig her — en vagt der
    slipper igennem naar den selv braekker, er ingen vagt.
    """
    if not token:
        return None
    try:
        from core.runtime.jarvisx_auth import verify_token

        krav = verify_token(f"Bearer {token}")
        return krav if isinstance(krav, dict) else None
    except Exception:
        return None


def kraeves_auth() -> bool:
    """Er auth slaaet til i denne runtime?

    Samme udvej som bro-socketen bruger: en enkeltbruger-localhost uden auth
    skal stadig kunne koere. Fejlretning: kan vi ikke laese indstillingen, siger
    vi NEJ — ellers ville en fejl i opslaget laase alle klienter ude.
    """
    try:
        from core.runtime.jarvisx_auth import auth_required

        return bool(auth_required())
    except Exception:
        return False
