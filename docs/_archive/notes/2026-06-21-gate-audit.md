---
status: forældet
audited: 2026-07-08
ground_truth: "Git history: audit created 2026-06-21 15:23 → all 8 cluster-gates (gate_truth/commit/loop/memory/review/proactivity/privacy/auth) deployed by 2026-06-22 18:37 via commits 590c8c43, 56ccadef, 27e12569, etc. Code verified: GateKernel exists (gate_kernel.py:70), central().decide liv"
superseded_by: reference_truthgate_c2_ready.md, project_intelligent_central.md
---
# Gate-audit: kortlægning af ALLE gates/guards (read-only)

**Dato:** 2026-06-21 · **Forfatter:** Claude (på Bjørns observation) · **Status:** Audit, ingen ændringer

## Tese (Bjørn)

Over tid er der bygget *dusinvis* af separate gates/guards. De overlapper, kører
sekventielt, injicerer hver sin prompt-surface og emitterer hver sit event. Resultatet
er ikke et sikkerhedsnet — det er et net af bevægelige dele der interagerer
uforudsigeligt → **emergent ustabilitet + afbrudte loops**. De 15 Jarvis fandt var
KUN prompt-systemet; der er lige så mange i agentic-loopen og tool-exec.

## Inventory: ~50 gate/guard/scanner/review-filer, fordelt på 4 lag

### Lag 1 — Prompt-injicerede gates (bygger surface hver tur → token + cache-brud)
self_deception_guard · verification_gate · veto_gate · good_enough_gate ·
apophenia_guard · read_before_write_guard · signal_noise_guard · decision_gate ·
decision_adherence · fact_gate · diagnosis_gate · pressure_threshold_gate ·
proactive_question_gate · run_closure_gate · r2_5_blocking_gate · + ~10 signal-surfaces

### Lag 2 — Agentic-loop gates (kører i visible_runs pr. runde)
claim_scanner (scan_response) · fact_gate_enforce · tool-only-loop-guard (MAX=4) ·
capability-cap (MAX_CAPABILITIES_PER_TURN=5) · gate_blocked-håndtering (veto/decision) ·
presentation-invariant · run_closure_gate · proactive_question_gate-tracking ·
open_loop_closure-tracking

### Lag 3 — Tool-exec gates (pr. tool-kald)
tool_scoping.is_tool_allowed · execute_tool role-gate (effective_role) ·
tool_intent_runtime + tool_intent_approval_runtime · workspace_capabilities
sudo/mutating-verdicts (4-dels-allowlist) · classify_command · identity_guard ·
security_guard (lock/lockdown) · abuse_monitor (injection/rate)

### Lag 4 — Frittstående service/daemon-gates
communication_guard(_daemon) · cross_user_share_guard · share_guard_store ·
daemon_memory_safeguard · skill_scanner · skill_security_scanner · self_monitor ·
self_review_unified + 6 self_review_*-trackers · decision_review_daemon · auto_code_review

## Overlap-matrix — gates grupperet efter HVAD de faktisk checker

| Cluster | Gates (samme grundjob) | Antal |
|---|---|---|
| **Anti-konfabulation / ærlighed** | self_deception_guard, fact_gate(+enforce), apophenia_guard, claim_scanner, hallucination_guard, diagnosis_gate, verification_gate, ground_truth | **~8** |
| **Tool/handling-autorisation** | tool_scoping, execute_tool role-gate, tool_intent(+approval), sudo/mutating-verdicts, classify_command, veto_gate, identity_guard, security_guard, abuse_monitor | **~9** |
| **Loop/run-terminering** | run_closure_gate, tool-only-loop-guard, capability-cap, good_enough_gate, agentic_checkpoints, presentation-invariant | **~6** |
| **Beslutning/commitment** | decision_gate, decision_adherence_gate, decision_review_daemon, promise-ledger | **~4** |
| **Signal/støj/proaktivitet** | signal_noise_guard, pressure_threshold_gate, proactive_question_gate, r2_5_blocking_gate | **~4** |
| **Selv-review** | self_review_unified + 6 trackers, self_monitor, self_narrative_review | **~9** |
| **Privatliv/deling** | cross_user_share_guard, share_guard_store, communication_guard | **~3** |

## Ustabilitets-mekanismen (hvorfor afbrudte loops)

1. **Sekventiel fejl-multiplikation** — hvert lag kører gates i rækkefølge; én timeout/
   exception/misfortolkning kan afbryde eller hænge hele runnet.
2. **Overlap → uenighed** — 8 gates checker konfabulation hver for sig; de kan give
   modstridende verdicts (én blokker, én siger fortsæt) → uforudsigelig adfærd.
3. **Surface-støj → cache-brud** — hver prompt-gate injicerer dynamisk tekst → bryder
   prompt-cache → dyrere + langsommere + mere variabel.
4. **Empirisk bevis (2026-06-21):** næsten ALLE bugs jaget i dag var gate-interaktioner
   (operator-blok = role-gate × scope-CtxVar-tab; "3-4 så blok" = capability-cap ×
   scope-gate; override-flicker = TTL-gate × executor-kontekst; run_closure tomme svar).
   Og: Jarvis konfabulerede HELE dagen **på trods af** 8 anti-konfabulations-gates.
   Gatene gjorde ham ikke ærlig — de tilføjede fejlflade mens han stadig konfabulerede.

## Anbefaling: én intelligent gate pr. cluster, migreret én ad gangen

Ikke ét gigantisk gate — men **konsolidér hver cluster til ÉN gate** der læser konteksten
én gang, kører grupperede checks inline, og returnerer ét verdict (grøn/gul/rød + én
reason) med eksplicit præcedens.

**Første migrations-mål: anti-konfabulations-clusteret (8 → 1).** Begrundelse:
- Højeste overlap (8 gates, ét job).
- Demonstrabelt *virkningsløst* (Jarvis konfabulerer alligevel) → at fjerne dem kan
  næsten kun forbedre stabiliteten.
- Lavest risiko: det er ikke en sikkerheds-/autorisations-gate (dem rører vi sidst).

Migrér bag flag, kør shadow side-by-side, mål stabilitet + konfabulations-rate før/efter.

---

## KOMPLETHEDS-TJEK (rev. 2 — efter Bjørn fangede 3 manglende)

Første udgave manglede: read_before_write_guard, daemon_memory_safeguard, "emotional"
(sidstnævnte er IKKE en gate — den er et affekt-SURFACE-subsystem, ~11 filer). Plus
to policies jeg ikke havde talt med: `delete_policy`, `memory_write_policy`.

### Fuld gate→cluster-mapping (26 ægte beslutnings-gates — INGEN forældreløse)

| Cluster | Gates (komplet) |
|---|---|
| **TruthGate** (output-tid) | self_deception_guard, fact_gate(+enforce), apophenia_guard, hallucination_guard, diagnosis_gate, verification_gate(+telemetry), claim_scanner, **communication_guard(+daemon)** (output-frase-sikkerhed, samme emit-punkt) |
| **AuthGate** | tool_scoping/is_tool_allowed, execute_tool role-gate, tool_intent(+approval), sudo/mutating-verdicts, classify_command, veto_gate, identity_guard, security_guard, abuse_monitor, **read_before_write_guard**, **daemon_memory_safeguard**, **delete_policy**, **memory_write_policy**, skill_gate_tool |
| **LoopGate** | run_closure_gate, tool-only-loop-guard, capability-cap, good_enough_gate, agentic_checkpoints, presentation-invariant |
| **CommitGate** | decision_gate, decision_adherence_gate, decision_review_daemon |
| **PrivacyGate** | cross_user_share_guard, share_guard_store |
| **ReviewGate** (async) | self_review_unified + 6 trackers, self_monitor, narrative_review |
| **ProactivityGate** | signal_noise_guard, pressure_threshold_gate, proactive_question_gate, r2_5_blocking_gate |

### IKKE gates (forbliver — ikke del af konsolideringen)
- **Infra/ops:** provider_retry_policy, cheap_lane_balancer, provider_health_check, health_monitor — drift, ikke kognition.
- **Eksekvering:** staged_edits, file_tools_exec, runtime_action_executor, task_worker, *_runtime, daemons (heartbeat, jarvis_brain, active_sensing, scheduled_tasks) — DET gates autoriserer, ikke gates selv.
- **Signal-trackers / surfaces:** alle `*_signal_tracking`, `prompt_support_signals`, affekt-surfaces — **AwarenessContext-sporet (c), tages efter gates lander.**
- **Kanaler:** discord/telegram/fcm/ntfy_gateway — transport, ikke gates.

### Verdikt
**Ingen flere overlaps tilbage uplaceret.** 26 ægte gates → 7 cluster-gates + 1 GateKernel.
Surface-sporet (~25 build_*_surface) er separat og venter til gates er landet.

