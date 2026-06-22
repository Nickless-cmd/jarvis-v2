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
    # ── Loop-cluster (KONSOLIDERET 2026-06-22) ──
    # Enforcement = agentisk loop-kontrol (stop/fortsæt). De spredte stop-betingelser
    # (max runder / tomme-tekst / tool-only / synthese-pause) konsolideret til ÉN graderet
    # gate (gate_loop): RED=hård stop / YELLOW=blød synthese-brems / GREEN=fortsæt, routet
    # gennem central().decide. FAIL-SAFE (gate-fejl→stop, ikke uendelig løkke). Paritet med
    # gammel _is_last_round bevaret. Resten = instrument/leave.
    NerveSpec("loop_control", "loop", GateClass.COGNITIVE, "verdict", "merged",
              "core/services/gate_loop.py"),
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
    # ── Review-cluster (KONSOLIDERET 2026-06-22) — selv-review + trackers, async ──
    # Ingen request-path-blok-gate. Enforcement-ÆKVIVALENT = selv-review-VURDERINGEN:
    # self_review graderes (RED=høj-risiko/YELLOW=med/GREEN=lav) gennem central().decide
    # (gate_review) → trace + flag (høj-risiko → incident). Cascade-trackerne forbundet
    # via _track_step_failed → central observe (kaskade-fix 9c6c1813).
    NerveSpec("self_review", "review", GateClass.COGNITIVE, "verdict", "merged",
              "core/services/gate_review.py"),
    NerveSpec("self_review_unified", "review", GateClass.COGNITIVE, "daemon", "instrument",
              "core/services/self_review_unified.py:200-300 (graderet via gate_review)"),
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
    # ── Proactivity-cluster (KONSOLIDERET 2026-06-22) ──
    # Præcis kortlægning: KUN ÉN request-path enforcement-gate (R2/R2.5 verifikations-
    # disciplin). R2 (blød surface) + R2.5 (hård blok) konsolideret til ÉN graderet gate
    # (gate_proactivity, nerve="verification") routet gennem central().decide → MERGED.
    # verification_gate = data-kilde (R2-detektor). Resten = daemon-instrument / leave.
    NerveSpec("verification", "proactivity", GateClass.COGNITIVE, "verdict", "merged",
              "core/services/gate_proactivity.py"),
    NerveSpec("verification_gate", "proactivity", GateClass.COGNITIVE, "inline", "leave",
              "core/services/verification_gate.py (R2-data-kilde til gate_proactivity)"),
    NerveSpec("pressure_threshold", "proactivity", GateClass.COGNITIVE, "daemon", "instrument",
              "core/services/pressure_threshold_gate.py:169 (observe)"),
    NerveSpec("action_router", "proactivity", GateClass.COGNITIVE, "daemon", "instrument",
              "core/services/action_router.py:439 (observe)"),
    NerveSpec("longing_signal", "proactivity", GateClass.COGNITIVE, "daemon", "instrument",
              "core/services/longing_signal_daemon.py"),
    NerveSpec("signal_noise", "proactivity", GateClass.COGNITIVE, "filter", "leave",
              "core/services/signal_noise_guard.py:140-169 (daemon-input-filter)"),
    NerveSpec("initiative_queue", "proactivity", GateClass.COGNITIVE, "persistence", "leave",
              "core/services/initiative_queue.py:29-127"),
    NerveSpec("proactive_question_gate", "proactivity", GateClass.COGNITIVE, "persistence", "leave",
              "core/services/proactive_question_gate_tracking.py (tracker, ej enforcement)"),
    NerveSpec("proactive_loop_lifecycle", "proactivity", GateClass.COGNITIVE, "persistence", "leave",
              "core/services/proactive_loop_lifecycle_tracking.py (tracker, ej enforcement)"),
    # ── Memory-cluster (KONSOLIDERET 2026-06-22) ──
    # Mest observabilitet (recall/write fejler stille → instrument/leave). ÉN ægte
    # enforcement-gate: memory_promotion — gater hvad der auto-SKRIVES til identitets-
    # filer. De to tidligere eligibility-gates (USER.md + MEMORY.md) konsolideret til
    # ÉN graderet gate (gate_memory): RED=injection-afvist / GREEN=auto-apply / YELLOW=
    # kø-review, routet gennem central().decide. Fail-CLOSED (skriv ikke ved tvivl).
    NerveSpec("memory_promotion", "memory", GateClass.COGNITIVE, "verdict", "merged",
              "core/services/gate_memory.py"),
    NerveSpec("memory_write", "memory", GateClass.COGNITIVE, "persistence", "leave",
              "core/services/jarvis_brain.py:383-467"),
    NerveSpec("memory_embed", "memory", GateClass.COGNITIVE, "daemon", "leave",
              "core/services/jarvis_brain.py:565-590"),
    NerveSpec("memory_search", "memory", GateClass.COGNITIVE, "inline", "instrument",
              "core/services/jarvis_brain.py:596-722"),
    NerveSpec("memory_unified_recall", "memory", GateClass.COGNITIVE, "inline", "instrument",
              "core/services/memory_recall_engine.py (gather-fejl via central observe)"),
    NerveSpec("memory_distill", "memory", GateClass.COGNITIVE, "daemon", "leave",
              "core/services/session_distillation.py:164-363"),
    NerveSpec("memory_associative_recall", "memory", GateClass.COGNITIVE, "inline", "instrument",
              "core/services/associative_recall.py:196-250"),
    # ── Privacy-cluster 🔒 (SIKKERHED, fail-CLOSED — migreres SIDST) ──
    # Fit-pass: ALLE nerver fejler closed (deny). 3 request-path-gates = merge
    # (kun med fail-closed paritet); crypto/scoping/kø = leave. ÉT stille fejl-hul:
    # visible_runs.py:~3817 record_pending except:pass (trace-kontrakt skal attache).
    # cross_user_share KONSOLIDERET 2026-06-22: routet gennem central().decide som
    # SECURITY (fail-CLOSED, kan ikke slås fra), graderet (YELLOW=bekræftelse/GREEN=ren),
    # paritet bevaret (49 sikkerheds-tests grøn). gate_privacy.py. visibility_ceiling/
    # brain_recall = fail-closed filtre i recall-stien (leave — ikke request-path-blok).
    NerveSpec("cross_user_share", "privacy", GateClass.SECURITY, "verdict", "merged",
              "core/services/gate_privacy.py"),
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
    # ── Auth-cluster 🔒 KONSOLIDERET 2026-06-22 (SIDSTE cluster) ──
    # Hoved-enforcement = tool_access (rolle-backstop i execute_tool) routet gennem
    # central().decide som SECURITY (gate_auth): RED=deny / GREEN=tilladt. Backstoppens
    # gamle except:pass (silent fail-open) er nu fail-CLOSED (gate-exception→RED deny);
    # owner/unbound låses ALDRIG ude. permission_engine = kanonisk matrix-detektor (leave).
    # override/identity_guard/abuse_monitor = separate auth-koncerner (verdict, bevidst
    # fail-open hvor de er det ≠ DoS). PARITET 41 tool-scoping/auth-tests grøn.
    NerveSpec("tool_access", "auth", GateClass.SECURITY, "verdict", "merged",
              "core/services/gate_auth.py"),
    NerveSpec("tool_scoping", "auth", GateClass.SECURITY, "filter", "leave",
              "core/tools/tool_scoping.py:203-243 (is_tool_allowed = detektor for gate_auth)"),
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
    # ── Execution-cluster 🔒 KONSOLIDERET 2026-06-22 (tools-lanens fail-open hul) ──
    # Seks spredte rå inline-checks (hver med egen except:pass + ingen trace) smeltet til
    # ÉN graderet SECURITY-gate (gate_execution) routet gennem central().decide:
    # RED=blocked/read-before-write/untrusted → DENY · YELLOW=destructive/approval → kort ·
    # GREEN=auto. 8 call-sites (bash/write/edit/force×3/operator×2/workspace-trust) går nu
    # gennem Centralen → trace + circuit-breaker + drift + incident. classify_*/rbw/trust =
    # detektorer kaldt internt (leave). Lukker observabilitets-hullet ("bugs i blinde").
    NerveSpec("exec_command", "execution", GateClass.SECURITY, "verdict", "merged",
              "core/services/gate_execution.py (bash: rbw+classify)"),
    NerveSpec("exec_file", "execution", GateClass.SECURITY, "verdict", "merged",
              "core/services/gate_execution.py (write/edit: classify+rbw)"),
    NerveSpec("exec_workspace_trust", "execution", GateClass.SECURITY, "verdict", "merged",
              "core/services/gate_execution.py (guard_code_write)"),
    NerveSpec("exec_operator", "execution", GateClass.SECURITY, "verdict", "merged",
              "core/services/gate_execution.py (operator read-before-write)"),
    NerveSpec("classify_command", "execution", GateClass.SECURITY, "filter", "leave",
              "core/tools/simple_tools.py:3786 (detektor for exec_command)"),
    NerveSpec("classify_file_write", "execution", GateClass.SECURITY, "filter", "leave",
              "core/tools/simple_tools.py:3874 (detektor for exec_file)"),
    NerveSpec("read_before_write", "execution", GateClass.SECURITY, "filter", "leave",
              "core/services/read_before_write_guard.py (detektor for exec_file/command/operator)"),
    NerveSpec("workspace_trust", "execution", GateClass.SECURITY, "filter", "leave",
              "core/services/workspace_trust.py:92 (detektor for exec_workspace_trust)"),
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
