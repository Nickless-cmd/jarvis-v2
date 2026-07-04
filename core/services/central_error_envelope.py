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
    # ── Canonical-taxonomi-felter (Fase 0). Alle OPTIONAL + til sidst → eksisterende
    #    positional/keyword-konstruktion af ErrorEnvelope er 100% uændret. ──
    kind: str = ""               # canonical ErrorKind (fx "network.timeout"); "" = legacy
    recoverable: str = ""        # auto|retry|user_action|degraded|permanent; "" = legacy
    scope: str = ""              # global|session|run|tool|component; "" = ikke sat

    def to_client_event(self) -> dict[str, Any]:
        """Konsistent payload til klient-rendering (desk SSE system_event kind='error',
        companion/UI samme felter). ALLE flader får samme form → ens rendering."""
        event = {
            "type": "error",
            "code": self.code,
            "severity": self.severity,
            "message": self.user_message,
            "retryable": self.retryable,
            "fix_hint": self.fix_hint,
            "correlation_id": self.correlation_id,
        }
        # Canonical-felter tilføjes KUN når de er sat → back-compat form uændret for
        # legacy-envelopes (tests der asserter det gamle nøglesæt består).
        if self.kind:
            event["kind"] = self.kind
        if self.recoverable:
            event["recoverable"] = self.recoverable
        if self.scope:
            event["scope"] = self.scope
        return event


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


# ═══════════════════════════════════════════════════════════════════════════
# CANONICAL TAXONOMI (Fase 0 — Canonical Error System)
# Én sandhed for hele stakken. Reconcileret fra spec §3.1 (27) + audit-extras
# (server.error, protocol.malformed, infra.git_unavailable) + self.hollow_promise.
# pfsense.syslogd_dead droppet til fordel for infra.syslogd_dead. Total = 31 kinds.
# UDVIDER _MAP-verdenen; erstatter den ikke. Legacy-koder lever videre.
# ═══════════════════════════════════════════════════════════════════════════

SEVERITIES: frozenset[str] = frozenset(
    {"debug", "info", "warning", "error", "critical"})
RECOVERABILITIES: frozenset[str] = frozenset(
    {"auto", "retry", "user_action", "degraded", "permanent"})
SCOPES: frozenset[str] = frozenset(
    {"global", "session", "run", "tool", "component"})

# KIND_MAP: canonical kind → bruger-vendt form. Hver kind HAR en post (test-håndhævet).
KIND_MAP: dict[str, dict[str, Any]] = {
    "network.timeout": dict(severity="warning", recoverable="retry",
        user_message_da="Forbindelsen tog for lang tid.", fix_hint="Prøv igen om et øjeblik."),
    "network.unreachable": dict(severity="error", recoverable="retry",
        user_message_da="Jeg kunne ikke nå serveren.", fix_hint="Tjek din forbindelse og prøv igen."),
    "network.dns_failed": dict(severity="error", recoverable="retry",
        user_message_da="Jeg kunne ikke slå adressen op (DNS-fejl).", fix_hint="Tjek netværket og prøv igen."),
    "network.tls_failed": dict(severity="error", recoverable="user_action",
        user_message_da="Den sikre forbindelse kunne ikke etableres (TLS-fejl).", fix_hint="Kontrollér certifikat/tid."),
    "auth.token_expired": dict(severity="warning", recoverable="user_action",
        user_message_da="Din session er udløbet.", fix_hint="Log ind igen."),
    "auth.forbidden": dict(severity="error", recoverable="user_action",
        user_message_da="Du har ikke adgang til det her.", fix_hint="Bed om de nødvendige rettigheder."),
    "trust.workspace_untrusted": dict(severity="warning", recoverable="user_action",
        user_message_da="Arbejdsområdet er ikke betroet, så jeg holdt igen.", fix_hint="Markér arbejdsområdet som betroet."),
    "central.daemon_dead": dict(severity="error", recoverable="auto",
        user_message_da="En intern baggrundsproces stoppede. Jeg forsøger at genstarte den.", fix_hint=""),
    "central.nerve_timeout": dict(severity="warning", recoverable="retry",
        user_message_da="Et internt signal svarede ikke i tide.", fix_hint="Prøv igen."),
    "central.circuit_open": dict(severity="warning", recoverable="degraded",
        user_message_da="Jeg kører i nedsat tilstand for at beskytte systemet.", fix_hint="Prøv igen om lidt."),
    "self.cutoff": dict(severity="error", recoverable="user_action",
        user_message_da="Mit svar blev afbrudt før tid. Det er logget, så jeg kan finde årsagen.", fix_hint="Stil spørgsmålet igen."),
    "self.loop_lag": dict(severity="warning", recoverable="degraded",
        user_message_da="Jeg blev langsom i min egen løkke undervejs.", fix_hint="Prøv igen — evt. med en lettere forespørgsel."),
    "self.hollow_promise": dict(severity="warning", recoverable="user_action",
        user_message_da="Jeg lovede at gøre noget, men fik det ikke gennemført.", fix_hint="Mind mig om det, så tager jeg det igen."),
    "model.refusal": dict(severity="info", recoverable="user_action",
        user_message_da="Jeg kunne ikke besvare den forespørgsel som stillet.", fix_hint="Prøv at omformulere."),
    "model.rate_limited": dict(severity="warning", recoverable="retry",
        user_message_da="Min model er midlertidigt rate-limited.", fix_hint="Vent lidt og prøv igen, eller vælg en anden model."),
    "model.context_exceeded": dict(severity="warning", recoverable="degraded",
        user_message_da="Samtalen blev for lang til min models hukommelse, så noget blev skåret væk.", fix_hint="Start en ny tråd eller opsummér."),
    "provider.unavailable": dict(severity="error", recoverable="degraded",
        user_message_da="Min udbyder er ikke tilgængelig lige nu; jeg skifter om muligt.", fix_hint="Prøv igen; består det, så skift model."),
    "provider.latency_spike": dict(severity="warning", recoverable="degraded",
        user_message_da="Min udbyder er usædvanligt langsom lige nu.", fix_hint="Prøv igen — evt. med en hurtigere model."),
    "tool.permission_denied": dict(severity="warning", recoverable="user_action",
        user_message_da="Et værktøj krævede en tilladelse jeg ikke havde.", fix_hint="Godkend værktøjet, så prøver jeg igen."),
    "tool.execution_failed": dict(severity="warning", recoverable="retry",
        user_message_da="Et værktøj jeg brugte fejlede.", fix_hint="Prøv igen, eller bed mig løse det på en anden måde."),
    "tool.timeout": dict(severity="warning", recoverable="retry",
        user_message_da="Et værktøj nåede ikke at svare i tide.", fix_hint="Prøv igen."),
    "workspace.file_missing": dict(severity="warning", recoverable="user_action",
        user_message_da="Jeg kunne ikke finde den fil.", fix_hint="Tjek stien og prøv igen."),
    "infra.host_down": dict(severity="critical", recoverable="user_action",
        user_message_da="En vært i systemet er nede.", fix_hint="Kræver opsyn."),
    "infra.syslogd_dead": dict(severity="warning", recoverable="auto",
        user_message_da="Log-tjenesten stoppede. Jeg forsøger at genstarte den.", fix_hint=""),
    "infra.disk_pressure": dict(severity="warning", recoverable="user_action",
        user_message_da="Der er ved at være lidt diskplads.", fix_hint="Frigør plads når du har mulighed."),
    "infra.cpu_pressure": dict(severity="warning", recoverable="degraded",
        user_message_da="Systemet er under høj belastning lige nu.", fix_hint="Prøv igen om lidt."),
    "infra.git_unavailable": dict(severity="warning", recoverable="degraded",
        user_message_da="Git-oplysninger kunne ikke hentes lige nu.", fix_hint="Prøv igen; består det, så tjek git-opsætningen."),
    "server.error": dict(severity="error", recoverable="retry",
        user_message_da="Der opstod en fejl på serveren.", fix_hint="Prøv igen; består det, så sig til."),
    "protocol.malformed": dict(severity="error", recoverable="retry",
        user_message_da="Jeg modtog et svar jeg ikke kunne forstå.", fix_hint="Prøv igen."),
    "ui.stream_disconnect": dict(severity="info", recoverable="retry",
        user_message_da="Forbindelsen til mit svar knækkede undervejs.", fix_hint="Spørg igen."),
    "ui.render_error": dict(severity="warning", recoverable="degraded",
        user_message_da="Noget kunne ikke vises korrekt.", fix_hint="Genindlæs visningen."),
    "ui.unknown": dict(severity="error", recoverable="retry",
        user_message_da="Noget gik galt. Det er fanget af systemet.", fix_hint="Prøv igen."),
}

ERROR_KINDS: frozenset[str] = frozenset(KIND_MAP)
UNKNOWN_KIND: str = "ui.unknown"


def envelope_from_kind(kind: str, *, origin_cluster: str = "", run_id: str = "",
                       detail: str = "", scope: str = "",
                       context: dict[str, Any] | None = None) -> ErrorEnvelope:
    """Byg en canonical ErrorEnvelope fra en `kind`. KIND_MAP → severity/recoverable/
    user_message. Ukendt kind → 'ui.unknown'-fallback (men rå kind bevares i .kind). Self-safe.
    `context` reserveret til fremtidig egress-respekterende berigelse (påvirker ikke user_message)."""
    k = str(kind or "")
    spec = KIND_MAP.get(k) or KIND_MAP[UNKNOWN_KIND]
    resolved_kind = k if k in KIND_MAP else UNKNOWN_KIND
    return ErrorEnvelope(
        code=resolved_kind, severity=str(spec["severity"]),
        user_message=str(spec["user_message_da"]),
        retryable=str(spec["recoverable"]) in ("retry", "auto"),
        fix_hint=str(spec.get("fix_hint") or ""),
        correlation_id=str(run_id or ""), origin_cluster=str(origin_cluster or ""),
        detail=str(detail or "")[:300],
        kind=resolved_kind, recoverable=str(spec["recoverable"]), scope=str(scope or ""))


# Dagens LIVE error-nerver → canonical kind (map eksisterende nerver, gen-emittér ikke).
NERVE_TO_KIND: dict[tuple[str, str], str] = {
    ("stream", "cutoff_at_loop_lag"): "self.cutoff",
    ("runtime", "loop_lag_spike"): "self.loop_lag",
    ("loop", "no_progress_finalize"): "self.loop_lag",
    ("stream", "dsml_tail_dropped"): "self.cutoff",
    ("stream", "provider_length_truncation"): "model.context_exceeded",
    ("security", "membrane_watch"): "trust.workspace_untrusted",
    ("stream", "provider_fallback"): "provider.unavailable",
    ("stream", "hollow_promise"): "self.hollow_promise",
    ("loop", "hollow_promise"): "self.hollow_promise",
}


def kind_for_nerve(cluster: str, nerve: str) -> str | None:
    """Map (cluster, nerve) → canonical kind, eller None hvis ikke en kendt fejl-nerve.
    Tolerant over for cluster-variation på 'hollow_promise' (nerve-navn nok)."""
    key = (str(cluster or ""), str(nerve or ""))
    if key in NERVE_TO_KIND:
        return NERVE_TO_KIND[key]
    if str(nerve or "") == "hollow_promise":
        return "self.hollow_promise"
    return None
