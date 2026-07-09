"""Track 2 — SHADOW-kørsel af de sovende post_output-gates.

Seks gates er bygget+testet men KØRTE ALDRIG i runtime: 5 kognitive
  (commit_gate / loop_gate / proactivity_gate / review_gate / fact_gate_adapter)
  \+ 1 SECURITY (privacy_gate — cross-user-lækage i output; kræver current_user_id i ctx).

Denne modul vækker dem i SKYGGE: hver gate rutes gennem Centralens
`central().decide(...)` på post_output-punktet, så vi får cluster-tag + trace +
drift-flag + circuit-breaker + fail-open — men resultatet BRUGES ALDRIG til at
blokere, ændre eller stoppe turen.

HÅRDT INVARIANT (§28 shadow-mode):
  SHADOW = record verdict, ALDRIG enforce. run_post_output_shadow returnerer
  None, kaster aldrig, og ingen kalder bruger dens output til kontrol-flow.

Nerve-navnene matcher hver gates `Verdict(navn, ...)` (= Verdict.gate), så
trace/observabilitet er konsistent med gaten selv:
  commit_gate        -> Verdict("decision_gate", ...)  cluster=commit
  loop_gate          -> Verdict("loop_control", ...)   cluster=loop
  proactivity_gate   -> Verdict("verification", ...)   cluster=proactivity
  review_gate        -> Verdict("self_review", ...)    cluster=review
  fact_gate_adapter  -> Verdict("fact_gate", ...)      cluster=truth
"""
from __future__ import annotations

from typing import Any

from core.services.central_core import central
from core.services.gate_kernel import GateClass

# (nerve, modul, fn-attr, cluster, klass) — nerve = Verdict.gate returneret af fn.
# klass: COGNITIVE = crash→SKIP (stille). privacy_gate er SECURITY (crash→RED), men i SHADOW
# bruges verdict'et ALDRIG — RED/YELLOW er ren observabilitet (en detekteret cross-user-lækage
# SKAL være synlig, ikke tavs). Kræver current_user_id i ctx (beriget på post_output-punktet).
_GATES: tuple[tuple[str, str, str, str, GateClass], ...] = (
    ("decision_gate", "core.services.gate_commit", "commit_gate", "commit", GateClass.COGNITIVE),
    ("loop_control", "core.services.gate_loop", "loop_gate", "loop", GateClass.COGNITIVE),
    ("verification", "core.services.gate_proactivity", "proactivity_gate", "proactivity", GateClass.COGNITIVE),
    ("self_review", "core.services.gate_review", "review_gate", "review", GateClass.COGNITIVE),
    ("fact_gate", "core.services.gate_adapters", "fact_gate_adapter", "truth", GateClass.COGNITIVE),
    ("cross_user_share", "core.services.gate_privacy", "privacy_gate", "privacy", GateClass.SECURITY),
)

# Flag-scope/name: flag:central.switch.gate_kernel.shadow (default ON).
_FLAG_SCOPE = "gate_kernel"
_FLAG_NAME = "shadow"

# ── ENFORCE-GRADUERING (6. jul): flippet fra shadow→enforce på ~1 døgns rene verdicts ──
# Disse 5 havde 0-6% ikke-grøn UDEN false-positives → sikre at håndhæve. loop_control holdes i
# shadow (dens gule = ægte "blød brems" der ville PAUSE runs = adfærdsændring, samler mere data).
# ENFORCEMENT for POST-OUTPUT-gates (kører i _post_process EFTER streaming → kan ikke real-tids-
# blokere/footnote det brugeren allerede så): gør ikke-grønne verdicts SYNLIGE som central-incident
# (privacy-læk RED→severe, kognitiv→error) i stedet for tavs shadow-trace. NON-DESTRUKTIVT — beskeden
# røres aldrig; enforcement = synlighed+governance. Kill-switch pr. gate: flag gate_enforce.<nerve>.
_ENFORCED: frozenset[str] = frozenset({
    "decision_gate", "self_review", "fact_gate", "verification", "cross_user_share",
})


def _is_enforced(nerve: str) -> bool:
    """True hvis gaten er graduated til enforce (i _ENFORCED) OG ikke kill-switchet fra."""
    if nerve not in _ENFORCED:
        return False
    try:
        from core.services import central_switches
        return bool(central_switches.is_enabled("gate_enforce", nerve))  # default ON
    except Exception:
        return True


def _enforce_verdict(nerve: str, cluster: str, klass: GateClass, verdict) -> None:
    """Håndhæv en enforced gates ikke-grønne verdict = gør det SYNLIGT som central-incident.
    Non-destruktivt (beskeden røres ikke). Self-safe."""
    try:
        from core.services.gate_kernel import Decision
        if verdict is None or verdict.decision in (Decision.GREEN, Decision.SKIP):
            return
        # Severitet efter GRAD, ikke bare "ikke-grøn". En YELLOW er en blød fodnote-markering =
        # NORMAL governance (gaten gør sit arbejde), ikke system-uhelbred — den må IKKE farve
        # Centralen gul (ellers står den evigt gul for at fungere korrekt). Kun en RED hård blok
        # er fejl-niveau; en SECURITY-RED er severe.
        if klass is GateClass.SECURITY and verdict.decision is Decision.RED:
            sev = "severe"
        elif verdict.decision is Decision.RED:
            sev = "error"
        else:  # YELLOW — synlig i feed'et, men info-niveau (degraderer ikke helbred)
            sev = "info"
        from core.runtime.db_central_incidents import record_central_incident
        record_central_incident(
            cluster=cluster, nerve=nerve, kind="gate_enforce", severity=sev,
            message=f"gate håndhævet: {nerve} → {verdict.decision.value}: {verdict.reason}"[:300],
        )
    except Exception:
        pass


def POST_OUTPUT_GATES_CLUSTERS() -> list[tuple[str, str]]:
    """(nerve, cluster) i kald-rækkefølge — til test/introspektion."""
    return [(nerve, cluster) for (nerve, _mod, _fn, cluster, _kl) in _GATES]


def _shadow_enabled() -> bool:
    """True medmindre gate_kernel.shadow er EKSPLICIT slået fra. Fail-open til ON
    (default ON; en cache-katastrofe må ikke slukke skygge-observabiliteten)."""
    try:
        from core.services import central_switches
        return bool(central_switches.is_enabled(_FLAG_SCOPE, _FLAG_NAME))
    except Exception:
        return True


def _resolve(mod_path: str, fn_attr: str):
    mod = __import__(mod_path, fromlist=[fn_attr])
    return getattr(mod, fn_attr)


def run_post_output_shadow(ctx: dict[str, Any]) -> None:
    """Kør de 5 sovende gates i SKYGGE via central().decide.

    REN OBSERVABILITET — returnerer altid None og KASTER ALDRIG. Hver gate køres i
    eget try/except, så én gates (eller import-) fejl aldrig stopper de øvrige eller
    turen. Resultatet af decide bruges ingen steder til kontrol-flow.
    """
    try:
        if not _shadow_enabled():
            return None
    except Exception:
        # selv flag-tjek må aldrig vælte
        return None

    for nerve, mod_path, fn_attr, cluster, klass in _GATES:
        try:
            fn = _resolve(mod_path, fn_attr)
            # decide: cluster-tag + trace + drift + circuit-breaker.
            verdict = central().decide(nerve, ctx, fn, cluster=cluster, klass=klass)
            # ENFORCE-graduerede gates: gør ikke-grønne verdicts synlige (incident). Shadow-gates
            # (fx loop_control) discarder stadig verdict'et = ren observabilitet.
            if _is_enforced(nerve):
                _enforce_verdict(nerve, cluster, klass, verdict)
        except Exception:
            # én gates fejl (import/decide/central) må ikke stoppe de andre eller turen
            continue
    return None
