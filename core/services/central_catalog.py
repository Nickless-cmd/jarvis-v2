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
    # veto = affektiv bruger-pushback, pre-execution-disciplin ved siden af decision_gate
    # (IKKE truth — surveyet foreslog truth, men det er en commit-beslutning). MERGED
    # 2026-06-22: var rå inline fail-open i visible_runs:4869 → nu gennem central().decide.
    NerveSpec("veto", "commit", GateClass.COGNITIVE, "verdict", "merged",
              "core/services/gate_commit.py:veto_gate (check_veto)"),
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
    # outbound_scrub = kanal-egress-scrubbing (hård afslutnings-fraser i discord/telegram/
    # notification). Tekst-TRANSFORMATION (ikke allow/block) → passer observe, ikke decide.
    # Instrumenteret 2026-06-22: guard_channel_text → central.observe.
    NerveSpec("outbound_scrub", "privacy", GateClass.SECURITY, "filter", "instrument",
              "core/services/communication_guard.py:374 guard_channel_text (observe)"),
    # KORRIGERET 2026-06-22 merge→leave: visibility_ceiling + brain_recall er fail-closed
    # filtre i RECALL-stien (hvad der hentes/surfaces), IKKE request-path allow/block-gates.
    # Surveyets dybere analyse bekræftede leave. De bevarer deres fail-closed adfærd in-situ.
    NerveSpec("visibility_ceiling", "privacy", GateClass.SECURITY, "filter", "leave",
              "core/services/jarvis_brain_visibility.py:35-63 (recall-filter, ej request-path)"),
    NerveSpec("brain_recall_gate", "privacy", GateClass.SECURITY, "filter", "leave",
              "core/services/jarvis_brain.py:616-648 (recall-filter, ej request-path)"),
    NerveSpec("share_guard_store", "privacy", GateClass.SECURITY, "persistence", "leave",
              "core/services/share_guard_store.py:28-72"),
    NerveSpec("workspace_encryption", "privacy", GateClass.SECURITY, "inline", "leave",
              "core/services/workspace_crypto.py:46-193"),
    NerveSpec("private_brain_scoping", "privacy", GateClass.SECURITY, "filter", "leave",
              "core/runtime/db_private_brain.py:88-150"),
    # A3 2026-06-22: cross-user attachment-adgang (clean security-bool → observe ved roden).
    NerveSpec("attachment_access", "privacy", GateClass.SECURITY, "filter", "instrument",
              "core/services/attachment_service.py:attachment_visible_to_user (observe wrapper)"),
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
    # KORRIGERET 2026-06-22 (ærlig fit efter kode-læsning): permission_engine = kanonisk
    # tool-access-matrix-DETEKTOR som gate_auth allerede kalder (leave, som tool_scoping).
    NerveSpec("permission_engine", "auth", GateClass.SECURITY, "filter", "leave",
              "core/services/permission_engine.py:112-138 (matrix-detektor for gate_auth)"),
    # override_command + identity_guard = request-path security ved incoming-grænsen.
    # Returnerer rige {action,reply}/{ok,...}-dicts (ikke allow/block-Verdicts) → INSTRUMENT
    # (central.observe via tynd wrapper), ikke decide. Incoming-security nu synlig pr. session.
    NerveSpec("override_command", "auth", GateClass.SECURITY, "verdict", "instrument",
              "core/services/override_command.py:handle_override_command (observe wrapper)"),
    NerveSpec("identity_guard", "auth", GateClass.SECURITY, "verdict", "instrument",
              "core/services/identity_guard.py:guard_incoming (observe wrapper)"),
    # abuse_monitor = sub-komponent KALDT inde i guard_incoming (rate-limit+injection);
    # dens udfald fanges via guard_incoming's observe → leave (ikke selvstændig request-gate).
    NerveSpec("abuse_monitor", "auth", GateClass.SECURITY, "verdict", "leave",
              "core/services/abuse_monitor.py:101-131 (sub-komponent af guard_incoming)"),
    NerveSpec("security_guard", "auth", GateClass.SECURITY, "persistence", "leave",
              "core/services/security_guard.py:54-210"),
    # A2+A4 2026-06-22: plugin-inbound hardblock + kvote-udfald (orchestrator-dict → observe).
    NerveSpec("plugin_inbound", "auth", GateClass.SECURITY, "verdict", "instrument",
              "core/services/channel_inbound.py:route_inbound (observe wrapper)"),
    # A5 2026-06-22: anti-CSRF oauth-state-validering (fejlet = muligt angreb → observe).
    NerveSpec("oauth_state", "auth", GateClass.SECURITY, "validation", "instrument",
              "core/services/oauth_flow.py:verify_state (observe wrapper)"),
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
    # A1 2026-06-22: malware-scan på uploads — scanneren (malware_scan.is_upload_allowed) var
    # bygget men UWIRET (0 call-sites → uploads uscannede). Nu wiret i /attachments/upload
    # gennem central().decide: infected → RED (slet+afvis), clean/unavailable → GREEN (fail-open).
    NerveSpec("exec_upload_scan", "execution", GateClass.SECURITY, "verdict", "merged",
              "core/services/gate_execution.py (malware_scan.is_upload_allowed, /upload)"),
    # ── Mutation-cluster 🔒 KONSOLIDERET 2026-06-22 (autonom selv-mutations-sikkerhed) ──
    # DUAL-TRUTH fjernet: INFRASTRUCTURE_BLOCKED_MODULES lå byte-identisk i identity_mutation_log
    # OG auto_improvement_proposer; prompt_mutation_loop havde egen _PROTECTED_FILES. Nu ÉN
    # kanonisk kilde (gate_mutation) + ÉN graderet SECURITY-gate routet gennem central().decide.
    # Tre håndhævelses-funktioner (record_mutation/audit · _check_target/prompt-fil · _is_safe_
    # target/kode-modul) beholder signaturer (dict/raise/bool) men DECISIONEN + trace + breaker
    # + incident sker centralt. Fail-CLOSED (blokér selv-mutation ved tvivl). De gamle lister
    # re-eksporteres for bagudkompat.
    NerveSpec("mut_record", "mutation", GateClass.SECURITY, "verdict", "merged",
              "core/services/gate_mutation.py (identity_mutation_log.record_mutation)"),
    NerveSpec("mut_prompt", "mutation", GateClass.SECURITY, "verdict", "merged",
              "core/services/gate_mutation.py (prompt_mutation_loop._check_target)"),
    NerveSpec("mut_module", "mutation", GateClass.SECURITY, "verdict", "merged",
              "core/services/gate_mutation.py (auto_improvement_proposer._is_safe_target)"),
    NerveSpec("infrastructure_blocklist", "mutation", GateClass.SECURITY, "filter", "leave",
              "core/services/gate_mutation.py (kanonisk liste — var dual-truth)"),
    # ── Skill-Safety-cluster 🔒 KONSOLIDERET 2026-06-22 ──
    # scan_skill-detektoren (injection/malware/boundary) lå wired på 3 spredte call-sites
    # (skill_engine create=hard-block · skill_engine read=advisory · agent_dispatch=dispatch-
    # blok), hver med eget except:pass + ingen trace. Nu ÉN graderet SECURITY-gate (gate_skill)
    # routet gennem central().decide: RED=blokeret (≥high)/YELLOW=advisory-fund/GREEN=ren →
    # trace + breaker + incident. Fail-CLOSED (uscanbar skill oprettes ikke). check_permissions
    # = manifest-scope-detektor uden live call-site (leave).
    NerveSpec("skill_scan", "skill", GateClass.SECURITY, "verdict", "merged",
              "core/services/gate_skill.py (skill_scanner.scan_skill, 3 call-sites)"),
    NerveSpec("skill_contract", "skill", GateClass.SECURITY, "validation", "leave",
              "core/services/skill_contract_registry.py:67 (check_permissions — ingen live caller)"),
    # ── Stream-cluster KONSOLIDERET 2026-06-22 (observabilitet, IKKE en blokerende gate) ──
    # Streaming er en LANE, ikke en beslutning: ~18 fejl-punkter + ~25 tavse except:pass i
    # SSE-pipelinen hvor hængende streams/zombie-slots/manglende message_stop levede USYNLIGT.
    # Nu emitterer hver lane-overgang central.observe pr. run_id (stream_sentinel), + en
    # stall-backstop (300s > translatorens 180s idle-oprydning) der flagger ægte zombier som
    # incident (severity='error', pollbar). Alle COGNITIVE/instrument — ingen håndhævelse.
    NerveSpec("stream_start", "stream", GateClass.COGNITIVE, "inline", "instrument",
              "core/services/stream_sentinel.py (visible_runs_sse_v2 message_start)"),
    NerveSpec("stream_stop", "stream", GateClass.COGNITIVE, "inline", "instrument",
              "core/services/stream_sentinel.py (message_stop: done/fallback)"),
    NerveSpec("stream_stall", "stream", GateClass.COGNITIVE, "daemon", "instrument",
              "core/services/stream_sentinel.py (message_start uden message_stop >300s → incident)"),
    NerveSpec("stream_event", "stream", GateClass.COGNITIVE, "inline", "instrument",
              "core/services/stream_sentinel.py (idle/cancel/error/zombie_slot/subscriber_timeout)"),
    # ── Kategori-B observe (2026-06-22): stille daemon/provider-fejl gjort synlige ──
    NerveSpec("provider_call", "stream", GateClass.COGNITIVE, "daemon", "instrument",
              "core/services/heartbeat_provider_fallback.py (B10: provider-fejl pr. kald)"),
    NerveSpec("provider_fallback", "stream", GateClass.COGNITIVE, "daemon", "instrument",
              "core/services/heartbeat_provider_fallback.py (B10: alle providers udtømt)"),
    NerveSpec("provider_health", "stream", GateClass.COGNITIVE, "daemon", "instrument",
              "core/services/provider_health_check.py (B7: ping-helbred pr. provider)"),
    NerveSpec("scheduled_task_fire", "loop", GateClass.COGNITIVE, "daemon", "instrument",
              "core/services/scheduled_tasks.py (B6: påmindelse fyret/dispatch-fejl)"),
    # B-batch 2 (2026-06-22): heartbeat-producer-helbred + notifikations-levering synlige.
    NerveSpec("cadence_producers", "stream", GateClass.COGNITIVE, "daemon", "instrument",
              "core/services/cadence_producers.py (heartbeat-producer-fire pr. tick)"),
    NerveSpec("notification_route", "stream", GateClass.COGNITIVE, "daemon", "instrument",
              "core/services/notification_router.py:route_proactive_notification (delivery-udfald)"),
    # ── Prompt-cluster KONSOLIDERET 2026-06-22 (Phase 1: live on/off + trace) ──
    # prompt_contract.py byggede ~73 sektioner blindt og skar støj via HARDCODET blacklist
    # (_DIAGNOSTIC_NOISE_LABELS) — ændring krævede kode+deploy, ingen trace af HVORFOR droppet.
    # Phase 1: hver sektion er nu live-styrbar pr. label (central_switches scope=prompt_section)
    # + ÉT central.observe pr. build (assembly) med included/dropped_disabled/dropped_budget.
    # BEVIDST UDEN per-sektion decide() (latency) og uden ændret indhold (cache-prefix urørt) —
    # de to risici Jarvis flagged. Gradering/kondensering/8→1-konsolidering = Phase 2+.
    NerveSpec("assembly", "prompt", GateClass.COGNITIVE, "inline", "instrument",
              "core/services/prompt_observer.py (build-trace) + prompt_contract.py:791 _awareness_add"),
    NerveSpec("section_switch", "prompt", GateClass.COGNITIVE, "filter", "instrument",
              "core/services/prompt_observer.py:section_enabled (live on/off pr. label, erstatter blacklist)"),
    # ── DB-cluster KONSOLIDERET 2026-06-22 (observabilitet + flag, ALDRIG destruktiv) ──
    # Centralen ser jarvis.db's struktur+vækst og flagger uregelmæssigheder, men dropper/
    # ændrer ALDRIG noget. Daglig census (db_sentinel.observe via internal_cadence-producer):
    # row-counts + vækst-delta. Egregious vækst (fordobling+stor abs. tilvækst) → incident.
    # Autoclean = FORESLÅ-til-review (tom tabel = kandidat, ikke handling — cognitive_*-lektien:
    # 'død' var afløst, ikke død). Intet DDL/DML i modulet.
    NerveSpec("census", "db", GateClass.COGNITIVE, "daemon", "instrument",
              "core/services/db_sentinel.py (daglig table-census + total-rows)"),
    NerveSpec("table_growth", "db", GateClass.COGNITIVE, "daemon", "instrument",
              "core/services/db_sentinel.py (egregious-vækst-flag → incident)"),
    NerveSpec("dead_table_review", "db", GateClass.COGNITIVE, "validation", "leave",
              "core/services/db_sentinel.py:dead_table_candidates (review-liste, ALDRIG auto-drop)"),
    # ── Tools-cluster KONSOLIDERET 2026-06-22 (Phase 1: observe + kategorisering) ──
    # 400+ tools (mange overlap) routes alle gennem execute_tool-chokepunktet. Phase 1: ÉT
    # observe pr. kald tagger native vs operator + chat/code-scope + rolle + session + udfald
    # → debugging af "fejl ude af huset" (hvilket operator-/chat-tool i hvilken session).
    # tool_observer.py = query-helpers. Phase 2 = konsolidering 20→1 på forbrugs/overlap-data.
    NerveSpec("tool_call", "tools", GateClass.COGNITIVE, "inline", "instrument",
              "core/tools/simple_tools.py:execute_tool (observe pr. kald, native/operator+session)"),
    NerveSpec("tool_query", "tools", GateClass.COGNITIVE, "validation", "leave",
              "core/services/tool_observer.py (recent_tool_failures — debugging-indgang)"),
    # Phase 2 (2026-06-22): persistent forbrugs-statistik (DB, cross-proces api↔runtime).
    # Centralen tæller mest/ofte/nogle-gange/sjældent/ALDRIG → ordn katalog (mest-først, døde-
    # sidst) + flag døde tools. Daglig observe via internal_cadence-producer. Katalog-omrække-
    # følge = Phase 2b (afventer akkumuleret data + cache-håndtering i tool_catalog).
    NerveSpec("tool_usage_stats", "tools", GateClass.COGNITIVE, "daemon", "instrument",
              "core/services/tool_usage_store.py:observe_stats (daglig forbrugs-summary + døde-flag)"),
    NerveSpec("tool_usage_order", "tools", GateClass.COGNITIVE, "validation", "leave",
              "core/services/tool_usage_store.py:tool_order/dead_tools (katalog-rækkefølge, Phase 2b-wiring)"),
    # API-endpoint forbrugs-statistik (2026-06-22, parallel til tool_usage): middleware tæller
    # de ~412 endpoints → most/aldrig + flag DØDE (registreret men aldrig kaldt). Daglig observe.
    NerveSpec("endpoint_usage_stats", "tools", GateClass.COGNITIVE, "daemon", "instrument",
              "core/services/endpoint_usage_store.py:observe_stats (endpoint-forbrug + døde-flag)"),
    NerveSpec("endpoint_call", "tools", GateClass.COGNITIVE, "inline", "instrument",
              "apps/api/jarvis_api/app.py:_endpoint_usage_middleware (tæl pr. request)"),
    # ── System-cluster KONSOLIDERET 2026-06-22 (kartografen MELDER til Centralen) ──
    # system_cartographer kortlagde ALLEREDE systemet (services/daemons/surfaces/dark-edges/
    # theater/coverage/health) + auto-triagerede (enqueuer observability+theater-repair-tasks
    # til Jarvis over score-tærskler) — men meldte ALDRIG til Centralen. Nu: daemon-loopet
    # (hver 15. min) → central.observe af systemkortet, så vi kun skal kigge ÉT sted.
    # Read-only statisk analyse — ALDRIG destruktiv.
    NerveSpec("cartographer", "system", GateClass.COGNITIVE, "daemon", "instrument",
              "core/services/system_cartographer.py:_observe_to_central (systemkort → Centralen)"),
    NerveSpec("cartographer_autotask", "system", GateClass.COGNITIVE, "persistence", "leave",
              "core/services/system_cartographer.py:_maybe_enqueue_* (auto-triage: huller→runtime_tasks)"),
    # §1 self-helbred (2026-06-22): "hvem overvåger Centralen?" Den prober SIG SELV hver time
    # (decide+observe-probe + åbne breakers + uløste-severe-tæller) → observe + eskalér (ntfy +
    # incident) hvis degraded. #5: breakers in-memory→nulstilles ved genstart (bevidst). #6:
    # escalation-path ud over logging.
    NerveSpec("central_health", "system", GateClass.COGNITIVE, "daemon", "instrument",
              "core/services/central_health.py:observe_and_escalate (Centralen prober sig selv)"),
    # §7 config-drift (2026-06-22): fang når deklareret config ≠ runtime (8010/8011-buggen kostede
    # DAGE — settings.port vs faktisk lyttende port). Daglig probe → observe + incident. Read-only.
    NerveSpec("config_drift", "system", GateClass.COGNITIVE, "daemon", "instrument",
              "core/services/config_drift.py:observe_config_drift (port-drift declared↔runtime)"),
)


def clusters() -> list[str]:
    return sorted({n.cluster for n in CATALOG})


# Et cluster er SIKKERHEDS-cluster hvis mindst én af dets nerver er SECURITY — så kan det
# ALDRIG slås helt fra (§11.3-invariant: sikkerhed isoleres kun mod deny, slukkes ikke).
_SECURITY_CLUSTERS: frozenset[str] = frozenset(
    n.cluster for n in CATALOG if n.klass is GateClass.SECURITY)


def is_security_cluster(cluster: str) -> bool:
    """True hvis clusteret har mindst én SECURITY-nerve (→ kan ikke slås fra)."""
    return str(cluster or "") in _SECURITY_CLUSTERS


def security_clusters() -> list[str]:
    return sorted(_SECURITY_CLUSTERS)


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
