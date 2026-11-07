"""Gate-adaptere (unified-gate A.5) — wrapper EKSISTERENDE gates som Verdict-returnerende.

Fase A ændrer INGEN gate-logik. En adapter kalder den eksisterende gate og oversætter
dens resultat til en `Verdict`, så kernen kan køre den isoleret + emittere ét event.
Den faktiske EFFEKT (strip/blok) ligger stadig på de gamle kald-sites indtil A.6
router gennem kernen og B-H konsoliderer.

Disse tre hører til TruthGate-clusteret (post_output, kognitiv → fail-OPEN).
"""
from __future__ import annotations

from typing import Any

from core.services.gate_kernel import Decision, GateClass, Verdict


def claim_scanner_adapter(ctx: dict[str, Any]) -> Verdict:
    """claim_scanner.scan_response: repareret tekst ≠ input → claims fanget (YELLOW)."""
    text = str(ctx.get("text") or "")
    if not text.strip():
        return Verdict("claim_scanner", Decision.GREEN, "empty")
    from core.services.claim_scanner import scan_response
    repaired = scan_response(text)
    if repaired != text:
        # 2026-07-06: claim_scanner appender nu fodnoter (bevarer teksten) —
        # action="warn", ikke "strip". Detektionen er uændret.
        return Verdict("claim_scanner", Decision.YELLOW, "uverificerede claims markeret (fodnote)",
                       action="warn", evidence={"annotated": True})
    return Verdict("claim_scanner", Decision.GREEN, "ren")


def fabricated_claim_adapter(ctx: dict[str, Any]) -> Verdict:
    """detect_fabricated_work_claims: work-claim uden tool-evidens → YELLOW.

    Dækker et hul de to andre truth-adaptere ikke har: `scan_response` og
    `fact_gate_enforce` læser begge kun TEKSTEN. Denne adapter kobler påstanden
    til de værktøjer der faktisk kørte i samme run — «jeg har committet X» uden
    et commit-kald i runnet er en anden fejl end et forkert tal.

    Målt 7/11-2026: funktionen havde nul kaldesteder i produktion (kun en
    kommentar og sin egen definition), så hele evidens-koblingen var død kode.
    Den kører nu som skygge-gate via ``gate_shadow._GATES`` — ren
    observabilitet; den blokerer eller omskriver aldrig teksten.
    """
    text = str(ctx.get("text") or "")
    if not text.strip():
        return Verdict("fabricated_claim", Decision.GREEN, "empty")
    tools = ctx.get("tool_names") or ctx.get("tools_used") or []
    from core.services.claim_scanner import detect_fabricated_work_claims
    claims = detect_fabricated_work_claims(text, list(tools)) or []
    if not claims:
        return Verdict("fabricated_claim", Decision.GREEN, "alle work-claims har tool-evidens")
    lead = claims[0]
    return Verdict(
        "fabricated_claim",
        Decision.YELLOW,
        f"{len(claims)} work-claim(s) uden tool-evidens: {lead.pattern_name}",
        action="warn",
        detected_text=str(lead.matched_text)[:120],
        trigger_pattern=str(lead.pattern_name),
        session_id=str(ctx.get("session_id") or ""),
        run_id=str(ctx.get("run_id") or ""),
    )


def fact_gate_adapter(ctx: dict[str, Any]) -> Verdict:
    """fact_gate_enforce: uverificerede tal-/status-påstande → YELLOW (warn/fodnote).

    2026-07-06: fact_gate blokerer aldrig mere (blocked altid False). Gaten
    detekterer stadig og fylder block_reasons — vi udtrykker det som en YELLOW
    'warn' i stedet for RED 'strip'."""
    text = str(ctx.get("text") or "")
    tools = ctx.get("tool_names") or ctx.get("tools_used") or []
    from core.services.fact_gate import fact_gate_enforce
    res = fact_gate_enforce(text, list(tools)) or {}
    _reasons = res.get("block_reasons") or []
    if _reasons:
        # block_reasons er en liste af DICTS ({pattern, matched, description, …}) — IKKE
        # strings. Et rå "; ".join(...) kastede 'expected str instance, dict found' og væltede
        # HELE truth-decide (fail-incident). Udtræk en læsbar streng pr. reason i stedet.
        reason = "; ".join(
            str(br.get("description") or br.get("pattern") or br) if isinstance(br, dict)
            else str(br)
            for br in _reasons
        )[:200] or "fact-gate markeret"
        # Rig attribuering (2026-07-13): detected_text (matched substring) + trigger_pattern
        # (mønster-navn) FANDTES allerede i block_reasons — bær dem videre på Verdiktet, så
        # Centralen kan aggregere pr. mønster. Lead = første fund (det mest fremtrædende).
        _lead = _reasons[0] if isinstance(_reasons[0], dict) else {}
        _detected = str(_lead.get("matched") or "")[:120]
        _pattern = str(_lead.get("pattern") or "")
        _sid = str(ctx.get("session_id") or "")
        _rid = str(ctx.get("run_id") or "")
        # Vane-bryder: registrér mønsteret (durabelt, self-safe). Krydser det tærsklen
        # emitter modulet selv en central-nudge (gate_pattern_repeat).
        try:
            from core.services.gate_pattern_learning import record_gate_pattern
            if _pattern:
                record_gate_pattern(_pattern, _detected, session_id=_sid)
        except Exception:
            pass
        return Verdict("fact_gate", Decision.YELLOW, reason, action="warn",
                       detected_text=_detected, trigger_pattern=_pattern,
                       session_id=_sid, run_id=_rid)
    return Verdict("fact_gate", Decision.GREEN, "ok")


def _publish_diagnosis_event(kind: str, result: Any, session_id: str, run_id: str) -> None:
    """Publicér det signal mood-regulatoren abonnerer på.

    Self-safe: et tabt signal er ikke et tabt output — gaten må ikke vælte turen.
    """
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(kind, {
            "session_id": session_id, "run_id": run_id,
            "claim": getattr(result, "claim_snippet", ""),
            "pattern": getattr(result, "pattern", ""),
            "blocked": False, "annotated": False,
        })
    except Exception:  # signal-tab maa ikke koste turens sandheds-verdict
        pass


def diagnosis_adapter(ctx: dict[str, Any]) -> Verdict:
    """Uverificeret completion-claim ELLER diagnose → YELLOW 'warn'.

    Publicerer samtidig ``promise.unverified`` og ``diagnosis.unverified``, som
    ``central_mood_regulator`` mapper til correction/confabulation. Uden dem var den
    mapping død kode: den eneste publisher var ``diagnosis_gate_enforce``, som intet
    kaldested har (målt 7/11-2026) — så Jarvis' stemning blev aldrig jordet når han
    konfabulerede eller lovede noget han ikke havde gjort.
    """
    text = str(ctx.get("text") or "")
    tools = ctx.get("tools_used") or ctx.get("tool_names") or []
    session_id = str(ctx.get("session_id") or "")
    run_id = str(ctx.get("run_id") or "")
    from core.services.diagnosis_gate import analyze_completion_claim, analyze_diagnosis

    # 2026-07-06: diagnosis blokerer aldrig mere → uverificeret completion-claim
    # bliver YELLOW 'warn' (fodnote i bunden), ikke RED 'block'.
    promise = analyze_completion_claim(text, tools_used=list(tools))
    if getattr(promise, "detected", False) and not getattr(promise, "verified", True):
        _publish_diagnosis_event("promise.unverified", promise, session_id, run_id)
        return Verdict("diagnosis", Decision.YELLOW,
                       getattr(promise, "reason", "") or "uverificeret completion",
                       action="warn")

    diag = analyze_diagnosis(text, tools_used=list(tools))
    if getattr(diag, "detected", False) and not getattr(diag, "verified", True):
        _publish_diagnosis_event("diagnosis.unverified", diag, session_id, run_id)
        return Verdict("diagnosis", Decision.YELLOW,
                       getattr(diag, "reason", "") or "uverificeret diagnose",
                       action="warn")

    return Verdict("diagnosis", Decision.GREEN, "ok")


# Adaptere i TruthGate-clusteret: (name, fn).
_TRUTHGATE_ADAPTERS = [
    ("claim_scanner", claim_scanner_adapter),
    ("fact_gate", fact_gate_adapter),
    ("diagnosis", diagnosis_adapter),
]


def register_truthgate_adapters(k) -> None:
    """Registrér TruthGate-cluster-adapterne i kernen (post_output, kognitiv)."""
    for name, fn in _TRUTHGATE_ADAPTERS:
        k.register(name, "post_output", fn, klass=GateClass.COGNITIVE,
                   timeout_ms=1500, flag_key=f"gate.{name}")


def register_truthgate_adapters_once(k) -> None:
    """Idempotent — registrér KUN hvis ikke allerede registreret (kaldes pr. run i
    visible_runs A.6; må aldrig duplikere gates)."""
    have = {g.name for g in k.gates_for("post_output")}
    if {n for n, _ in _TRUTHGATE_ADAPTERS} <= have:
        return
    register_truthgate_adapters(k)
