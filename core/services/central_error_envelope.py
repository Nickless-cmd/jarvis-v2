"""Unified fejl-meddelelses-system — Centralen ejer hvad brugeren ser når noget knækker.

FØR: hver fejl-sti lavede sin egen ad-hoc bruger-besked (eller ingen) med forskellig form
på desk vs companion vs UI. En provider-429, en hængende stream, en agent-fejl, et afbrudt
run — alle forskellige tekster, ingen fælles form, ingen sporbarhed tilbage til run'et.
Det var derfor "💭 modtaget"-hæng kunne ske: fejlen nåede aldrig brugeren ærligt.

NU: Centralen fanger allerede ~alle fejl (stream/provider/tool/agent/run/loop efter
revisionen 23. jun). Dette modul mapper en intern fejl → ÉT bruger-envelope og giver
ÉN form alle flader renderer ens:

    intern fejl ──build_envelope──▶ ErrorEnvelope{severity, da-besked, retryable,
                                                   fix_hint, correlation_id}
                          │
                          ├─ to_client_event() ──▶ desk SSE system_event (synkron, under run)
                          └─ emit() ──────────────▶ central.observe(user_error)
                                                    + notification_router (async flade)

`correlation_id` = run_id → fra brugerens klage kan Bjørn/Claude spore direkte til run'et
i central_trace/correlate. Self-safe; kaster aldrig ind i fejl-stien.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ── Mapping-tabel: kanonisk fejl-kode → bruger-vendt form ────────────────────
# severity: info | warning | error | critical. retryable: kan brugeren bare prøve igen?
# Bygger på _classify_visible_run_interruption-taksonomien + provider/agent/stream-koder.
_MAP: dict[str, dict[str, Any]] = {
    # provider (visible-lane)
    "provider_rate_limited": dict(
        severity="warning", retryable=True,
        message="Min model er midlertidigt rate-limited (for mange kald lige nu). Prøv igen om et øjeblik — eller skift til en anden model.",
        fix_hint="Vent lidt og prøv igen, eller vælg en anden model i composeren."),
    "provider_timeout": dict(
        severity="warning", retryable=True,
        message="Min model svarede ikke i tide. Det sker ved tunge forespørgsler eller langsomme udbydere.",
        fix_hint="Prøv igen — evt. med en hurtigere model."),
    "provider_error": dict(
        severity="error", retryable=True,
        message="Min udbyder returnerede en fejl. Det er ude af mine hænder lige nu.",
        fix_hint="Prøv igen om lidt; består det, så skift model."),
    # run-interruption (fra _classify_visible_run_interruption)
    "approval-wait-timeout": dict(
        severity="info", retryable=True,
        message="Jeg ventede på din godkendelse til et værktøj, men der kom intet svar, så jeg stoppede.",
        fix_hint="Bed mig fortsætte, eller godkend værktøjet når kortet dukker op."),
    "process-restart": dict(
        severity="warning", retryable=True,
        message="Min runtime genstartede midt i dit svar. Intet gik tabt — spørg mig igen.",
        fix_hint="Stil spørgsmålet igen."),
    "runtime-crash": dict(
        severity="error", retryable=True,
        message="Noget gik galt internt mens jeg svarede. Det er logget, så jeg kan finde årsagen.",
        fix_hint="Prøv igen — sker det igen, så sig til."),
    "runtime-error": dict(
        severity="error", retryable=True,
        message="Der opstod en intern fejl under dit svar. Den er fanget og logget.",
        fix_hint="Prøv igen."),
    "provider-timeout": dict(  # alias for interruption-reason-stavning
        severity="warning", retryable=True,
        message="Min model svarede ikke i tide og svaret blev afbrudt.",
        fix_hint="Prøv igen."),
    "client-disconnect": dict(
        severity="info", retryable=True,
        message="Forbindelsen til din enhed blev afbrudt mens jeg svarede.",
        fix_hint="Tjek forbindelsen og spørg igen."),
    "user-interrupted": dict(
        severity="info", retryable=True,
        message="Jeg stoppede svaret fordi du afbrød.",
        fix_hint=""),
    # agent / stream / loop
    "agent_error": dict(
        severity="error", retryable=True,
        message="En af mine agenter fejlede under opgaven. Hovedsvaret er ikke nødvendigvis ramt.",
        fix_hint="Bed mig prøve den del igen."),
    "stream_error": dict(
        severity="error", retryable=True,
        message="Forbindelsen til mit svar knækkede undervejs.",
        fix_hint="Spørg igen."),
    "presentation_invariant": dict(
        severity="warning", retryable=True,
        message="Jeg kom til at gentage værktøjs-resultater som tekst i stedet for at kalde værktøjet rigtigt.",
        fix_hint="Spørg mig igen, så svarer jeg ordentligt."),
    "tool_failed": dict(
        severity="warning", retryable=True,
        message="Et værktøj jeg brugte fejlede.",
        fix_hint="Prøv igen, eller bed mig løse det på en anden måde."),
    # generisk fallback
    "unknown": dict(
        severity="error", retryable=True,
        message="Noget gik galt. Det er fanget af systemet.",
        fix_hint="Prøv igen."),
}


@dataclass(frozen=True)
class ErrorEnvelope:
    """Den ENE bruger-vendte fejl-form. Alle flader (desk/companion/UI) renderer den ens."""
    code: str
    severity: str
    user_message: str
    retryable: bool
    fix_hint: str
    correlation_id: str          # = run_id → spor tilbage til run'et i central_trace
    origin_cluster: str
    detail: str = ""             # rå intern detalje (til log/MC, IKKE altid til bruger)

    def to_client_event(self) -> dict[str, Any]:
        """Konsistent payload til klient-rendering (desk SSE system_event kind='error',
        companion/UI samme felter). ALLE flader får samme form → ens rendering."""
        return {
            "type": "error",
            "code": self.code,
            "severity": self.severity,
            "message": self.user_message,
            "retryable": self.retryable,
            "fix_hint": self.fix_hint,
            "correlation_id": self.correlation_id,
        }


def build_envelope(*, code: str, origin_cluster: str = "", run_id: str = "",
                   detail: str = "") -> ErrorEnvelope:
    """Map en kanonisk fejl-kode → bruger-vendt envelope. Ukendt kode → 'unknown'-fallback
    (men beholder den rå kode så MC kan se hvad der reelt skete)."""
    spec = _MAP.get(str(code or ""), _MAP["unknown"])
    return ErrorEnvelope(
        code=str(code or "unknown"),
        severity=str(spec["severity"]),
        user_message=str(spec["message"]),
        retryable=bool(spec["retryable"]),
        fix_hint=str(spec.get("fix_hint") or ""),
        correlation_id=str(run_id or ""),
        origin_cluster=str(origin_cluster or ""),
        detail=str(detail or "")[:300],
    )


def emit(envelope: ErrorEnvelope, *, session_id: str = "", user_id: str = "",
         notify: bool = False) -> dict[str, Any]:
    """Gør fejlen synlig + (valgfrit) rut den til en async flade. Returnerer klient-eventet
    så kalderen kan yield'e det synkront i en aktiv SSE-stream. Self-safe — kaster ALDRIG.

    - ALTID: central.observe(nerve=user_error) → sporbar i Centralen pr. correlation_id.
    - notify=True (run ER slut / baggrund): route via notification_router til desk/companion/push.
    - synkron (run kører): kalderen yield'er to_client_event() i streamen (ingen notify)."""
    event = envelope.to_client_event()
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "system", "nerve": "user_error",
            "code": envelope.code, "severity": envelope.severity,
            "origin_cluster": envelope.origin_cluster,
            "correlation_id": envelope.correlation_id,
            "retryable": envelope.retryable,
            "session_id": str(session_id or ""),
            "surface": "notify" if notify else "inline",
        })
    except Exception:
        pass
    if notify and user_id:
        try:
            from core.services.notification_router import route_proactive_notification
            route_proactive_notification(
                user_id=str(user_id),
                payload={"title": "Jarvis-fejl", "body": envelope.user_message,
                         **event},
                kind="error",
            )
        except Exception:
            pass
    return event


def for_interruption(*, reason: str, run_id: str = "", detail: str = "") -> ErrorEnvelope:
    """Bekvemheds-bro fra _classify_visible_run_interruption's reason → envelope."""
    return build_envelope(code=str(reason or "unknown"), origin_cluster="loop",
                          run_id=run_id, detail=detail)
