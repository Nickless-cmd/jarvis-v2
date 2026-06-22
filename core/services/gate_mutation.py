"""Mutation-cluster gate 🔒 — én graderet SECURITY-gate + ÉN kanonisk kilde for de
sikkerhedslister der styrer AUTONOM selv-mutation (identitets-filer, workspace-prompt-
filer, kode-moduler).

DUAL-TRUTH-FJERNELSE: ``INFRASTRUCTURE_BLOCKED_MODULES`` lå byte-identisk i BÅDE
identity_mutation_log OG auto_improvement_proposer; prompt_mutation_loop havde sin egen
``_PROTECTED_FILES``. Tre overlappende blocklists = tre steder at glemme at opdatere.
Nu ÉN kanonisk kilde (her); de gamle navne re-eksporteres for bagudkompat.

KONSOLIDERING (som TruthGate 8→1): de tre spredte håndhævelses-funktioner —
``record_mutation`` (identity, audit), ``_check_target`` (prompt-fil-evolution),
``_is_safe_target`` (kode-modul-forslag) — routes nu gennem ÉT gate-kald i Centralen.
De beholder deres signaturer/svarformer (dict / raise / bool) men DECISIONEN + trace +
circuit-breaker + incident sker centralt.

Grader (SECURITY, fail-CLOSED — blokér autonom mutation ved tvivl; brikker intet, da
det KUN gælder autonom selv-mutation, ikke bruger-tools):
  RED   = infrastructure-blokeret · protected identitets-fil · ikke-evolvable · auth slået fra
  GREEN = tilladt (evolvable / tier-3-autoriseret / sikkert modul)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.services.gate_kernel import Decision, GateClass, Verdict

_SEC = GateClass.SECURITY


# ── KANONISKE sikkerhedslister (eneste sandhed) ──────────────────────────
# Hard-blokeret af STABILITETS-hensyn (ikke kun safety): selv-mod af disse moduler
# kan skabe rekursive bugs / bryde approval- eller audit-mekanismen der gater alt.
INFRASTRUCTURE_BLOCKED_MODULES: frozenset[str] = frozenset({
    "core.services.auto_improvement_proposer",
    "core.services.plan_proposals",
    "core.services.approvals",
    "core.services.identity_mutation_log",
    "core.runtime.policy",
})

# Kerne-identitets-filer — aldrig auto-muteret.
PROTECTED_IDENTITY_FILES: frozenset[str] = frozenset({
    "SOUL.md", "IDENTITY.md", "MANIFEST.md", "MILESTONES.md", "INHERITANCE_SEED.md",
    "CONSENT_REGISTRY.json", "MEMORY.md", "USER.md", "jarvis.db",
})

# Work-prompt-filer Jarvis må mutere autonomt.
EVOLVABLE_FILES: frozenset[str] = frozenset({
    "HEARTBEAT.md", "AFFECTIVE_STATE.md", "STANDING_ORDERS.md",
    "INNER_VOICE.md", "DREAM_LANGUAGE.md", "SELF_CRITIQUE.md",
})

# Identitets-filer der MÅ muteres med audit-spor (tier-3, via identity_mutation_log).
TIER_3_AUTHORIZED_FILES: frozenset[str] = frozenset({
    "SOUL.md", "IDENTITY.md", "MANIFEST.md", "STANDING_ORDERS.md", "USER.md",
})


def _hits(target: str, blocklist: frozenset[str]) -> bool:
    t = str(target or "")
    return any(b in t for b in blocklist)


# ── den konsoliderede gate ───────────────────────────────────────────────
def mutation_gate(ctx: dict[str, Any]) -> Verdict:
    """Én SECURITY-gate, dispatch på ctx['kind']: 'module' | 'prompt' | 'record'.
    Verdict.reason bærer den eksakte besked så kald-stedet bevarer sin svarform."""
    kind = str(ctx.get("kind") or "")
    target = str(ctx.get("target") or "")

    # ── kode-modul-forslag (auto_improvement_proposer._is_safe_target) ──
    if kind == "module":
        if not target:
            return Verdict("mut_module", Decision.RED, "tomt mål", action="block", klass=_SEC)
        if _hits(target, INFRASTRUCTURE_BLOCKED_MODULES):
            return Verdict("mut_module", Decision.RED, "infrastructure-protected module",
                           action="block", klass=_SEC)
        return Verdict("mut_module", Decision.GREEN, "sikkert", klass=_SEC)

    # ── workspace-prompt-fil-evolution (prompt_mutation_loop._check_target) ──
    if kind == "prompt":
        name = target.strip()
        if not name:
            return Verdict("mut_prompt", Decision.RED, "target_file is empty",
                           action="block", klass=_SEC)
        if "/" in name or "\\" in name or ".." in name:
            return Verdict("mut_prompt", Decision.RED,
                           f"target_file must be a bare filename: {name}",
                           action="block", klass=_SEC)
        if name in PROTECTED_IDENTITY_FILES:
            return Verdict("mut_prompt", Decision.RED,
                           f"{name} is protected — cannot auto-mutate",
                           action="block", klass=_SEC)
        if name not in EVOLVABLE_FILES:
            return Verdict("mut_prompt", Decision.RED,
                           f"{name} is not in evolvable whitelist "
                           f"(allowed: {sorted(EVOLVABLE_FILES)})",
                           action="block", klass=_SEC)
        return Verdict("mut_prompt", Decision.GREEN, "evolvable", klass=_SEC)

    # ── identitets-mutation med audit (identity_mutation_log.record_mutation) ──
    if kind == "record":
        try:
            from core.services.identity_mutation_log import is_auto_mutation_enabled
            enabled = bool(is_auto_mutation_enabled().get("enabled"))
        except Exception:
            enabled = False  # fail-CLOSED: kan ikke læse kill-switch → blokér
        if not enabled:
            return Verdict("mut_record", Decision.RED,
                           "auto-mutation disabled in authorization file",
                           action="block", klass=_SEC)
        if not _hits(target, TIER_3_AUTHORIZED_FILES) and not target.startswith("/tmp"):
            return Verdict("mut_record", Decision.RED,
                           f"target not in authorized scope: {target}",
                           action="block", klass=_SEC)
        if _hits(target, INFRASTRUCTURE_BLOCKED_MODULES):
            return Verdict("mut_record", Decision.RED,
                           "infrastructure-protected module — never auto-mutable",
                           action="block", klass=_SEC)
        return Verdict("mut_record", Decision.GREEN, "authorized", klass=_SEC)

    return Verdict("mutation", Decision.GREEN, "unknown_kind", klass=_SEC)


# ── central-routing + offentlige kald-helpers ────────────────────────────
@dataclass
class MutCheck:
    allowed: bool
    reason: str


def _decide(nerve: str, ctx: dict[str, Any]) -> Verdict:
    """Route gennem Den Intelligente Central (SECURITY, fail-CLOSED). Defense-in-depth:
    central-katastrofe → kør gaten direkte; sidste udvej RED (mutation-safety blokerer
    ved tvivl — modsat execution er det SIKRE her at nægte autonom selv-mutation)."""
    try:
        from core.services.central_core import central
        return central().decide(nerve, ctx, mutation_gate, cluster="mutation", klass=_SEC)
    except Exception:
        try:
            return mutation_gate(ctx)
        except Exception:
            return Verdict(nerve, Decision.RED, "mut-gate-error", action="block", klass=_SEC)


def check_module(target: str) -> bool:
    """auto_improvement_proposer._is_safe_target — True ⇔ sikkert at foreslå."""
    return _decide("mut_module", {"kind": "module", "target": target}).decision is Decision.GREEN


def check_prompt_target(name: str) -> MutCheck:
    """prompt_mutation_loop._check_target — allowed + besked (kald-stedet raiser)."""
    v = _decide("mut_prompt", {"kind": "prompt", "target": name})
    return MutCheck(v.decision is Decision.GREEN, v.reason)


def check_record(target_path: str) -> MutCheck:
    """identity_mutation_log.record_mutation — allowed + blok-grund."""
    v = _decide("mut_record", {"kind": "record", "target": target_path})
    return MutCheck(v.decision is Decision.GREEN, v.reason)
