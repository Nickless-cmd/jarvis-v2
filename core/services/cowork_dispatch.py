"""Cowork dispatch — runtime→app instruktioner (spec §18.5).

Efter §18-skiftet er appen den der HANDLER (sender beskeder via kanal-plugins,
viser notifikationer), og runtime den der TÆNKER. Når runtime vil have noget gjort
på brugerens enhed — "send vejrudsigt til Mikkel på Discord", "påmind Bjørn om møde",
"generer rapport og send på Slack" — bygger den en struktureret instruktion og
signalerer den via eventbus. Appen (jarvis-desk) lytter og udfører via sit plugin.

Ren bygge-funktion (`build_app_instruction`) + en dispatch der emitterer eventet.
Selve udførelsen sker klient-side (Fase 2-wiring). Backend-skelet, fuldt testbart.
"""
from __future__ import annotations

_VALID_ACTIONS = ("send_message", "notify", "send_report")


def build_app_instruction(*, action: str, target_user: str,
                          channel: str | None = None,
                          payload: dict | None = None,
                          requester: str = "") -> dict:
    """Byg en struktureret app-instruktion. Rejser ValueError ved ugyldig action
    eller manglende target_user."""
    act = str(action or "").strip().lower()
    if act not in _VALID_ACTIONS:
        raise ValueError(f"ugyldig action: {action!r} (gyldige: {_VALID_ACTIONS})")
    target = str(target_user or "").strip()
    if not target:
        raise ValueError("target_user påkrævet")
    return {
        "action": act,
        "target_user": target,
        "channel": str(channel).strip() if channel else None,
        "payload": dict(payload or {}),
        "requester": str(requester or ""),
    }


def dispatch_to_app(*, action: str, target_user: str,
                    channel: str | None = None,
                    payload: dict | None = None,
                    requester: str = "") -> dict:
    """Byg + signalér en app-instruktion via eventbus. Appen udfører den lokalt.

    Returnerer {ok, instruction} eller {ok: False, reason} ved valideringsfejl.
    """
    try:
        instruction = build_app_instruction(
            action=action, target_user=target_user,
            channel=channel, payload=payload, requester=requester,
        )
    except ValueError as exc:
        return {"ok": False, "reason": str(exc)}

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("cowork.app_dispatch", dict(instruction))
    except Exception:
        pass
    # Fase 2: persistér i kø så desk-appen kan polle + udføre + ack'e (cross-proces).
    try:
        from core.services.app_dispatch_store import enqueue
        enqueue(dict(instruction))
    except Exception:
        pass
    return {"ok": True, "instruction": instruction}
