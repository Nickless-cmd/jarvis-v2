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
            # decide: cluster-tag + trace + drift + circuit-breaker. SHADOW: resultatet
            # bruges ALDRIG til kontrol-flow — klass styrer kun fail-mode i trace'et.
            central().decide(nerve, ctx, fn, cluster=cluster, klass=klass)
        except Exception:
            # én gates fejl (import/decide/central) må ikke stoppe de andre eller turen
            continue
    return None
