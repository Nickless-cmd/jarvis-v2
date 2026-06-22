"""Fit-pass-katalog (§13.2): det maskinlæsbare resultat af kortlægningen af hver nerve.
Bruges senere som kilde til registrering. Fit = 'merge' (homogen, kan smelte sammen),
'merged' (smeltningen ER gennemført — gammel effekt-kode fjernet, kører nu kun via
Centralen), 'instrument' (kald Centralen på stedet), 'leave' (er ikke en request-path-gate)."""
from __future__ import annotations

from dataclasses import dataclass

from core.services.gate_kernel import GateClass

_MECHANISMS = {"verdict", "inline", "daemon", "filter", "tool", "persistence", "validation"}
_FITS = {"merge", "merged", "instrument", "leave"}


@dataclass(frozen=True)
class NerveSpec:
    name: str
    cluster: str
    klass: GateClass
    mechanism: str     # se _MECHANISMS
    fit: str           # se _FITS
    location: str      # fil:linje eller modul


# Kortlagt: Loop, Truth (MERGED), Commit, Review, Proactivity (fit-passet 2026-06-22).
# Mangler: Tools, Memory, Privacy🔒, Auth🔒 (Tools-fitpass findes som note; sikkerheds-
# clustrene tages SIDST med fail-closed paritet). Se reference_central_cluster_taxonomy.
CATALOG: tuple[NerveSpec, ...] = (
    # ── Loop-cluster ──
    NerveSpec("run_closure", "loop", GateClass.COGNITIVE, "daemon", "leave",
              "core/services/run_closure_gate.py"),
    NerveSpec("tool_budget", "loop", GateClass.COGNITIVE, "inline", "instrument",
              "core/services/visible_runs.py:1754-2351"),
    NerveSpec("capability_cap", "loop", GateClass.COGNITIVE, "filter", "leave",
              "core/tools/tool_scoping.py"),
    NerveSpec("good_enough", "loop", GateClass.COGNITIVE, "tool", "leave",
              "core/services/good_enough_gate.py"),
    NerveSpec("checkpoints", "loop", GateClass.COGNITIVE, "persistence", "leave",
              "core/services/agentic_checkpoints.py"),
    NerveSpec("presentation_invariant", "loop", GateClass.COGNITIVE, "validation", "instrument",
              "core/services/visible_runs.py:5758-5806"),
    # ── Truth-cluster (MERGED 2026-06-22, C4) — gamle post-done effekt-gates
    # fjernet fra visible_runs._post_process; detektorerne kører nu kun via
    # central().decide → gate_truth-adaptere (observabilitet). Enforcement =
    # TruthGate v2 pre-done. ──
    NerveSpec("claim_scanner", "truth", GateClass.COGNITIVE, "verdict", "merged",
              "core/services/claim_scanner.py"),
    NerveSpec("fact_gate", "truth", GateClass.COGNITIVE, "verdict", "merged",
              "core/services/fact_gate.py"),
    NerveSpec("diagnosis", "truth", GateClass.COGNITIVE, "verdict", "merged",
              "core/services/diagnosis_gate.py"),
    # ── Commit-cluster (beslutnings-disciplin, fit-passet 2026-06-22) ──
    # decision_gate = eneste request-path-gate → merge. Resten instrument/leave.
    NerveSpec("decision_gate", "commit", GateClass.COGNITIVE, "verdict", "merge",
              "core/services/decision_gate.py:27-92"),
    NerveSpec("decision_create", "commit", GateClass.COGNITIVE, "inline", "instrument",
              "core/services/behavioral_decisions.py:38-89"),
    NerveSpec("decision_signals", "commit", GateClass.COGNITIVE, "inline", "instrument",
              "core/services/decision_signals.py:185-248"),
    NerveSpec("decision_review", "commit", GateClass.COGNITIVE, "persistence", "leave",
              "core/runtime/db_decisions.py:119-184"),
    NerveSpec("credit_assignment", "commit", GateClass.COGNITIVE, "persistence", "leave",
              "core/runtime/db_credit_assignment.py:105-157"),
    # ── Review-cluster (selv-review + trackers, async ud af hot-path) ──
    # Ingen request-path-gates → alle leave; trace-kontrakt attaches på de stille
    # except:return-trackere i _track_runtime_candidates. self_review_unified = daemon.
    NerveSpec("self_review_unified", "review", GateClass.COGNITIVE, "daemon", "leave",
              "core/services/self_review_unified.py:200-300"),
    NerveSpec("self_review_signal", "review", GateClass.COGNITIVE, "inline", "leave",
              "core/services/self_review_signal_tracking.py"),
    NerveSpec("self_review_record", "review", GateClass.COGNITIVE, "inline", "leave",
              "core/services/self_review_record_tracking.py"),
    NerveSpec("self_review_run", "review", GateClass.COGNITIVE, "inline", "leave",
              "core/services/self_review_run_tracking.py"),
    NerveSpec("self_review_outcome", "review", GateClass.COGNITIVE, "inline", "leave",
              "core/services/self_review_outcome_tracking.py"),
    NerveSpec("self_review_cadence", "review", GateClass.COGNITIVE, "inline", "leave",
              "core/services/self_review_cadence_signal_tracking.py"),
    # ── Proactivity-cluster (uopfordret initiativ, fit-passet 2026-06-22) ──
    # request-path-gates (question/loop) = merge; tærskel-bærende nerver = instrument
    # (mange hardcodede tunables → config-kandidater); filtre/køer = leave.
    NerveSpec("signal_noise", "proactivity", GateClass.COGNITIVE, "filter", "leave",
              "core/services/signal_noise_guard.py:140-169"),
    NerveSpec("pressure_threshold", "proactivity", GateClass.COGNITIVE, "daemon", "instrument",
              "core/services/pressure_threshold_gate.py:235-292"),
    NerveSpec("longing_signal", "proactivity", GateClass.COGNITIVE, "daemon", "instrument",
              "core/services/longing_signal_daemon.py"),
    NerveSpec("initiative_queue", "proactivity", GateClass.COGNITIVE, "persistence", "leave",
              "core/services/initiative_queue.py:29-127"),
    NerveSpec("proactive_question_gate", "proactivity", GateClass.COGNITIVE, "inline", "merge",
              "core/services/proactive_question_gate_tracking.py:52-72"),
    NerveSpec("proactive_loop_lifecycle", "proactivity", GateClass.COGNITIVE, "inline", "merge",
              "core/services/proactive_loop_lifecycle_tracking.py:73-93"),
    NerveSpec("r2_5_blocking_gate", "proactivity", GateClass.COGNITIVE, "inline", "instrument",
              "core/services/r2_5_blocking_gate.py:72-194"),
    NerveSpec("action_router", "proactivity", GateClass.COGNITIVE, "daemon", "instrument",
              "core/services/action_router.py:250-345"),
    # ── Memory-cluster (skrive/recall/promotion, fit-passet 2026-06-22) ──
    # INGEN request-path-gates → pointen er TRACE, ikke enforcement. Recall/promotion
    # = instrument (fejler stille → prompt bygges uden memory); skrivning = leave.
    NerveSpec("memory_write", "memory", GateClass.COGNITIVE, "persistence", "leave",
              "core/services/jarvis_brain.py:383-467"),
    NerveSpec("memory_embed", "memory", GateClass.COGNITIVE, "daemon", "leave",
              "core/services/jarvis_brain.py:565-590"),
    NerveSpec("memory_search", "memory", GateClass.COGNITIVE, "inline", "instrument",
              "core/services/jarvis_brain.py:596-722"),
    NerveSpec("memory_unified_recall", "memory", GateClass.COGNITIVE, "inline", "instrument",
              "core/services/memory_recall_engine.py:476-543"),
    NerveSpec("memory_candidate_promotion", "memory", GateClass.COGNITIVE, "inline", "instrument",
              "core/identity/candidate_workflow.py:250-287"),
    NerveSpec("memory_distill", "memory", GateClass.COGNITIVE, "daemon", "leave",
              "core/services/session_distillation.py:164-363"),
    NerveSpec("memory_associative_recall", "memory", GateClass.COGNITIVE, "inline", "instrument",
              "core/services/associative_recall.py:196-250"),
    # ── Privacy-cluster 🔒 (SIKKERHED, fail-CLOSED — migreres SIDST) ──
    # Fit-pass: ALLE nerver fejler closed (deny). 3 request-path-gates = merge
    # (kun med fail-closed paritet); crypto/scoping/kø = leave. ÉT stille fejl-hul:
    # visible_runs.py:~3817 record_pending except:pass (trace-kontrakt skal attache).
    NerveSpec("cross_user_share", "privacy", GateClass.SECURITY, "verdict", "merge",
              "core/services/cross_user_share_guard.py:22-89"),
    NerveSpec("visibility_ceiling", "privacy", GateClass.SECURITY, "verdict", "merge",
              "core/services/jarvis_brain_visibility.py:35-63"),
    NerveSpec("brain_recall_gate", "privacy", GateClass.SECURITY, "filter", "merge",
              "core/services/jarvis_brain.py:616-648"),
    NerveSpec("share_guard_store", "privacy", GateClass.SECURITY, "persistence", "leave",
              "core/services/share_guard_store.py:28-72"),
    NerveSpec("workspace_encryption", "privacy", GateClass.SECURITY, "inline", "leave",
              "core/services/workspace_crypto.py:46-193"),
    NerveSpec("private_brain_scoping", "privacy", GateClass.SECURITY, "filter", "leave",
              "core/runtime/db_private_brain.py:88-150"),
    # ── Auth-cluster 🔒 (SIKKERHED, fail-CLOSED — migreres SIDST) ──
    # Kerne-gates (tool_scoping/permission_engine/override) fejler CLOSED. identity_guard/
    # abuse_monitor fejler OPEN BEVIDST (sikkerhed ≠ selvmål-DoS). simple_tools.py:3925
    # except:pass = BEVIDST defense-in-depth-backstop (primær gate = model-tool-filter).
    # 2 utilsigtede fail-opens noteret: tool_scoping:216 computer_use-policy, abuse-scan.
    NerveSpec("tool_scoping", "auth", GateClass.SECURITY, "filter", "merge",
              "core/tools/tool_scoping.py:203-243"),
    NerveSpec("permission_engine", "auth", GateClass.SECURITY, "filter", "merge",
              "core/services/permission_engine.py:112-138"),
    NerveSpec("override_command", "auth", GateClass.SECURITY, "verdict", "merge",
              "core/services/override_command.py:24-106"),
    NerveSpec("identity_guard", "auth", GateClass.SECURITY, "verdict", "merge",
              "core/services/identity_guard.py:100-196"),
    NerveSpec("abuse_monitor", "auth", GateClass.SECURITY, "verdict", "merge",
              "core/services/abuse_monitor.py:101-131"),
    NerveSpec("security_guard", "auth", GateClass.SECURITY, "persistence", "leave",
              "core/services/security_guard.py:54-210"),
)


def clusters() -> list[str]:
    return sorted({n.cluster for n in CATALOG})


def by_cluster(cluster: str) -> list[NerveSpec]:
    return [n for n in CATALOG if n.cluster == cluster]


def validate() -> list[str]:
    """Returnér liste af problemer (tom = grøn)."""
    problems: list[str] = []
    seen: set[str] = set()
    for n in CATALOG:
        if n.name in seen:
            problems.append(f"duplikat-nerve: {n.name}")
        seen.add(n.name)
        if n.mechanism not in _MECHANISMS:
            problems.append(f"{n.name}: ukendt mekanisme {n.mechanism!r}")
        if n.fit not in _FITS:
            problems.append(f"{n.name}: ukendt fit {n.fit!r}")
    return problems
