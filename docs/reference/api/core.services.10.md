# `core.services.10` — reference

> Generated 2026-07-08 from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/flow_state_detection.py`
_Flow State Detection — when everything clicks._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `update_flow_detection` | `(*, recent_outcomes, correction_count=…, sustained_minutes=…)` | — | [src](../../../core/services/flow_state_detection.py#L11) |
| function | `get_flow_state` | `()` | — | [src](../../../core/services/flow_state_detection.py#L33) |
| function | `build_flow_state_surface` | `()` | — | [src](../../../core/services/flow_state_detection.py#L37) |

## `core/services/followup_observer.py`
_Followup-cluster — gør den agentiske followup-loop synlig i Den Intelligente Central._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe` | `(nerve, run_id, **data)` | — | [src](../../../core/services/followup_observer.py#L24) |
| function | `note_round` | `(run_id, round_num, provider=…, model=…, *, exchanges=…)` | En agentisk followup-runde startede. Metadata-only. | [src](../../../core/services/followup_observer.py#L33) |
| function | `note_round_failed` | `(run_id, round_num, provider=…, error=…, **data)` | En followup-runde fejlede (provider-fejl) → synlig. Det er her copilot-400 / | [src](../../../core/services/followup_observer.py#L41) |
| function | `note_round_retry` | `(run_id, round_num, attempt, reason=…, *, outcome=…, **data)` | RUND-NIVEAU RETRY (spec §4.1/S7): en forbigående runde-fejl blev retry'et | [src](../../../core/services/followup_observer.py#L49) |
| function | `note_lean_prompt` | `(run_id, round_num, *, provider=…, model=…, before_chars=…, after_chars=…, saved_tokens=…, applied=…)` | LEAN AGENTIC-PROMPT (spec §4.7/I7): på runde ≥2 trimmede vi den tunge per-turn- | [src](../../../core/services/followup_observer.py#L67) |
| function | `note_loop_complete` | `(run_id, *, rounds=…, exit_reason=…, provider=…, model=…)` | Followup-loopet sluttede → observe runder kørt + exit-grund (completed/ | [src](../../../core/services/followup_observer.py#L81) |
| function | `note_empty_completion` | `(run_id, *, provider=…, model=…, rounds=…, tools_executed=…, session_id=…, path=…)` | TAVS CUT-OFF: loopet sluttede 'completed' men producerede INTET synligt svar. | [src](../../../core/services/followup_observer.py#L90) |
| function | `note_hollow_promise` | `(run_id, *, provider=…, model=…, round_index=…, session_id=…, resolved=…)` | TOM LØFTE (4. jul): modellen lovede imminent handling men kaldte NUL værktøj hele | [src](../../../core/services/followup_observer.py#L129) |
| function | `note_resend` | `(run_id, *, provider=…, model=…, recovered=…)` | RESEND-PÅ-TOM (Bjørn option 1): runtimen fangede en transient tom completion | [src](../../../core/services/followup_observer.py#L142) |
| function | `note_leak` | `(run_id, *, provider=…, model=…, chars=…, reason=…)` | LEAK/DUMP: modellen echoede et råt (kæmpe) tool-result som prosa-svar i stedet | [src](../../../core/services/followup_observer.py#L151) |
| function | `note_degeneration` | `(run_id, *, provider=…, model=…, reason=…, chars=…)` | MODEL-LOOP: streaming-laget fangede en runaway-repetition og dræbte den ved | [src](../../../core/services/followup_observer.py#L170) |
| function | `followup_summary` | `(*, window=…)` | Read-only: nylig followup-loop-aktivitet (til MC). Self-safe. | [src](../../../core/services/followup_observer.py#L189) |

## `core/services/forgetting_curve.py`
_Forgetting Curve — active forgetting as a feature._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_memory` | `(*, memory_key, content_preview=…, initial_decay=…)` | Register a memory for decay tracking. | [src](../../../core/services/forgetting_curve.py#L21) |
| function | `reinforce_memory` | `(memory_key)` | Reinforce a memory — reset decay, increment reinforcement count. | [src](../../../core/services/forgetting_curve.py#L37) |
| function | `apply_decay_tick` | `(decay_increment=…)` | Apply one decay tick to all registered memories. | [src](../../../core/services/forgetting_curve.py#L46) |
| function | `get_active_memories` | `()` | Return memories with decay < 0.9 (still active). | [src](../../../core/services/forgetting_curve.py#L72) |
| function | `get_faded_memories` | `()` | Return memories with decay >= 0.9 (faded but archived). | [src](../../../core/services/forgetting_curve.py#L81) |
| function | `build_forgetting_curve_surface` | `()` | — | [src](../../../core/services/forgetting_curve.py#L90) |

## `core/services/forgetting_engine.py`
_Forgetting engine — Lag 11 deletion logic._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `is_fredet_path` | `(path)` | — | [src](../../../core/services/forgetting_engine.py#L64) |
| function | `is_fredet_table` | `(table)` | — | [src](../../../core/services/forgetting_engine.py#L68) |
| function | `compute_period_label` | `(released_at, now)` | Render an aged period as a human label. | [src](../../../core/services/forgetting_engine.py#L76) |
| function | `_id_column_for` | `(table)` | Return the primary-key column name for a fade-eligible table. | [src](../../../core/services/forgetting_engine.py#L105) |
| function | `_scan_table_for_candidates` | `(*, table, workspace_id, decay_threshold, min_age_days, limit)` | Find IDs of rows that should fade. | [src](../../../core/services/forgetting_engine.py#L112) |
| function | `_soft_delete_row` | `(table, row_id)` | Mark row as soft-deleted. Returns True if updated. | [src](../../../core/services/forgetting_engine.py#L158) |
| function | `_hard_delete_expired_rows` | `(table, grace_days)` | Hard-delete rows whose grace window has expired. | [src](../../../core/services/forgetting_engine.py#L171) |
| function | `run_auto_cycle` | `(*, workspace_id)` | One auto-track cycle: scan, soft-delete, grace-sweep. | [src](../../../core/services/forgetting_engine.py#L185) |
| function | `release_memory` | `(*, memory_kind, memory_id, workspace_id=…, why=…)` | Self-track release: hard-delete + marker. Irrevocable. | [src](../../../core/services/forgetting_engine.py#L261) |
| function | `_is_anniversary` | `(released_at, now)` | True if the age of released_at is within 1 day of a round-number bucket. | [src](../../../core/services/forgetting_engine.py#L361) |
| function | `_is_proximity` | `(released_at, now)` | True if released_at is in the active 14–90 day window. | [src](../../../core/services/forgetting_engine.py#L368) |
| function | `format_forgetting_section_for_heartbeat` | `(*, workspace_id=…)` | Compact prompt-injection lines for the heartbeat awareness section. | [src](../../../core/services/forgetting_engine.py#L378) |

## `core/services/forgetting_runtime.py`
_Daemon for the forgetting (Lag 11) auto-track._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get_workspace_lock` | `(workspace_id)` | Lazy per-workspace lock. | [src](../../../core/services/forgetting_runtime.py#L24) |
| function | `_run_one_cycle` | `(workspace_id)` | Acquire workspace lock, run engine, release. Never raises. | [src](../../../core/services/forgetting_runtime.py#L34) |
| function | `_list_active_workspaces` | `()` | Phase 1: only the default workspace. | [src](../../../core/services/forgetting_runtime.py#L63) |
| function | `_resolve_interval_seconds` | `()` | Read cadence from settings each loop entry — picks up edits. | [src](../../../core/services/forgetting_runtime.py#L68) |
| function | `_loop` | `()` | — | [src](../../../core/services/forgetting_runtime.py#L78) |
| function | `start_forgetting_runtime` | `()` | Start the periodic forgetting daemon. Idempotent. | [src](../../../core/services/forgetting_runtime.py#L98) |
| function | `stop_forgetting_runtime` | `()` | Signal the loop to exit. | [src](../../../core/services/forgetting_runtime.py#L111) |

## `core/services/gate_adapters.py`
_Gate-adaptere (unified-gate A.5) — wrapper EKSISTERENDE gates som Verdict-returnerende._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `claim_scanner_adapter` | `(ctx)` | claim_scanner.scan_response: repareret tekst ≠ input → claims fanget (YELLOW). | [src](../../../core/services/gate_adapters.py#L17) |
| function | `fact_gate_adapter` | `(ctx)` | fact_gate_enforce: uverificerede tal-/status-påstande → YELLOW (warn/fodnote). | [src](../../../core/services/gate_adapters.py#L32) |
| function | `diagnosis_adapter` | `(ctx)` | analyze_completion_claim: blocked→RED, ikke-verificeret completion→YELLOW. | [src](../../../core/services/gate_adapters.py#L56) |
| function | `register_truthgate_adapters` | `(k)` | Registrér TruthGate-cluster-adapterne i kernen (post_output, kognitiv). | [src](../../../core/services/gate_adapters.py#L78) |
| function | `register_truthgate_adapters_once` | `(k)` | Idempotent — registrér KUN hvis ikke allerede registreret (kaldes pr. run i | [src](../../../core/services/gate_adapters.py#L85) |

## `core/services/gate_auth.py`
_Auth-cluster gate 🔒 — tool-access (rolle-håndhævelse), SECURITY fail-CLOSED._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `auth_gate` | `(ctx)` | ctx: {role, scope, name}. Returnér ét SECURITY-Verdict for tool-access. | [src](../../../core/services/gate_auth.py#L25) |

## `core/services/gate_commit.py`
_Commit-cluster gate (beslutnings-disciplin)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `commit_gate` | `(ctx)` | Kør Commit-clusterens decision-conflict-check og returnér ét GRADERET Verdict. | [src](../../../core/services/gate_commit.py#L18) |
| function | `veto_gate` | `(ctx)` | Commit-cluster: affektiv bruger-pushback gater tool-eksekvering. | [src](../../../core/services/gate_commit.py#L44) |

## `core/services/gate_enforcement.py`
_Governed per-gate enforce-kill-switch for PRE-eksekverings-gates._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `is_enforced` | `(nerve, klass)` | True hvis gatens håndhævelse er aktiv. | [src](../../../core/services/gate_enforcement.py#L32) |
| function | `note_suppressed_block` | `(nerve, cluster, reason)` | En gate ville have blokeret, men håndhævelsen er governed-OFF → registrér det som | [src](../../../core/services/gate_enforcement.py#L47) |

## `core/services/gate_eval.py`
_Gate-eval & paritets-harness (unified-gate Task 0.2)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_as_verdict` | `(name, raw)` | Normalisér en gate-returværdi til Verdict (genbruger kernens parser). | [src](../../../core/services/gate_eval.py#L21) |
| function | `replay` | `(turns, gate_fn, *, name=…)` | Kør gate_fn over hver turns `ctx` og returnér normaliserede verdicts. | [src](../../../core/services/gate_eval.py#L26) |
| function | `parity` | `(turns, old_fn, new_fn)` | Sammenlign to gate-implementeringer pr. turn. Grøn paritet = nul mismatches. | [src](../../../core/services/gate_eval.py#L38) |
| function | `score` | `(turns, gate_fn, *, label_key=…)` | Mål en gates beslutning mod ground-truth-labels pr. turn. | [src](../../../core/services/gate_eval.py#L52) |
| function | `load_fixtures` | `(path)` | Læs et jsonl-fixturset (én turn pr. linje). Tomme/kommenterede linjer ignoreres. | [src](../../../core/services/gate_eval.py#L73) |

## `core/services/gate_execution.py`
_Execution-cluster gate 🔒 — én graderet SECURITY-gate for ALLE tool-eksekverings-_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_red` | `(nerve, reason, classification)` | — | [src](../../../core/services/gate_execution.py#L42) |
| function | `_yellow` | `(nerve, classification)` | — | [src](../../../core/services/gate_execution.py#L47) |
| function | `_green` | `(nerve, classification)` | — | [src](../../../core/services/gate_execution.py#L52) |
| function | `execution_gate` | `(ctx)` | Én SECURITY-gate, dispatch på ctx['action']. Returnér ét graderet Verdict. | [src](../../../core/services/gate_execution.py#L58) |
| class | `ExecCheck` | `` | — | [src](../../../core/services/gate_execution.py#L159) |
| function | `_to_check` | `(v)` | — | [src](../../../core/services/gate_execution.py#L166) |
| function | `_decide` | `(nerve, ctx)` | Route gennem Den Intelligente Central (SECURITY). Defense-in-depth: hvis central- | [src](../../../core/services/gate_execution.py#L182) |
| function | `check_command` | `(command, session_id=…, *, blocked_only=…)` | — | [src](../../../core/services/gate_execution.py#L211) |
| function | `check_file` | `(path, session_id=…, *, kind=…, blocked_only=…)` | — | [src](../../../core/services/gate_execution.py#L218) |
| function | `check_workspace_trust` | `(tool_name)` | — | [src](../../../core/services/gate_execution.py#L225) |
| function | `check_operator` | `(path, session_id=…, *, file_exists=…)` | — | [src](../../../core/services/gate_execution.py#L230) |
| function | `check_upload` | `(path, *, block_on_unavailable=…)` | Malware-scan en uploadet fil GENNEM Centralen (SECURITY). .allowed=False ⇔ infected/ | [src](../../../core/services/gate_execution.py#L237) |

## `core/services/gate_kernel.py`
_GateKernel — central orchestrator for alle gates (spec 2026-06-21)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Decision` | `` | — | [src](../../../core/services/gate_kernel.py#L23) |
| class | `GateClass` | `` | — | [src](../../../core/services/gate_kernel.py#L30) |
| class | `Verdict` | `` | — | [src](../../../core/services/gate_kernel.py#L39) |
| method | `Verdict.is_blocking` | `(self)` | — | [src](../../../core/services/gate_kernel.py#L49) |
| function | `worst` | `(verdicts)` | Aggregeret beslutning efter præcedens RED>YELLOW>GREEN>SKIP. | [src](../../../core/services/gate_kernel.py#L53) |
| class | `_Gate` | `` | — | [src](../../../core/services/gate_kernel.py#L61) |
| class | `GateKernel` | `` | — | [src](../../../core/services/gate_kernel.py#L70) |
| method | `GateKernel.__init__` | `(self, *, flag_reader=…, emit=…)` | — | [src](../../../core/services/gate_kernel.py#L71) |
| method | `GateKernel.register` | `(self, name, phase, fn, *, klass=…, timeout_ms=…, flag_key=…)` | — | [src](../../../core/services/gate_kernel.py#L79) |
| method | `GateKernel.gates_for` | `(self, phase)` | — | [src](../../../core/services/gate_kernel.py#L84) |
| method | `GateKernel._fail_verdict` | `(self, g, reason)` | — | [src](../../../core/services/gate_kernel.py#L88) |
| method | `GateKernel._run_one` | `(self, g, ctx)` | — | [src](../../../core/services/gate_kernel.py#L94) |
| method | `GateKernel.run_phase` | `(self, phase, ctx)` | Kør alle gates i en fase isoleret; emit ÉT event; returnér verdicts. | [src](../../../core/services/gate_kernel.py#L122) |
| function | `_normalize` | `(g, raw)` | Tillad gates at returnere en færdig Verdict, et dict, eller None (=GREEN). | [src](../../../core/services/gate_kernel.py#L149) |
| function | `_default_flag_reader` | `(flag_key)` | Returnér True/False hvis flag'et er EKSPLICIT sat i shared_cache, ellers None | [src](../../../core/services/gate_kernel.py#L168) |
| function | `_default_emit` | `(kind, payload)` | — | [src](../../../core/services/gate_kernel.py#L183) |
| function | `kernel` | `()` | — | [src](../../../core/services/gate_kernel.py#L195) |

## `core/services/gate_loop.py`
_Loop-cluster gate — agentisk loop-kontrol, GRADERET._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `loop_gate` | `(ctx)` | ctx: {round, max_rounds, consecutive_empty, max_empty, consecutive_tool_only, | [src](../../../core/services/gate_loop.py#L25) |

## `core/services/gate_memory.py`
_Memory-cluster gate — promotion til identitets-filer, GRADERET._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_candidate_text` | `(candidate)` | — | [src](../../../core/services/gate_memory.py#L25) |
| function | `memory_promotion_gate` | `(ctx)` | ctx: {candidate, kind: 'user_md'|'memory_md'}. Returnér ét GRADERET Verdict. | [src](../../../core/services/gate_memory.py#L32) |

## `core/services/gate_mutation.py`
_Mutation-cluster gate 🔒 — én graderet SECURITY-gate + ÉN kanonisk kilde for de_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_hits` | `(target, blocklist)` | — | [src](../../../core/services/gate_mutation.py#L60) |
| function | `mutation_gate` | `(ctx)` | Én SECURITY-gate, dispatch på ctx['kind']: 'module' | 'prompt' | 'record'. | [src](../../../core/services/gate_mutation.py#L66) |
| class | `MutCheck` | `` | — | [src](../../../core/services/gate_mutation.py#L128) |
| function | `_decide` | `(nerve, ctx)` | Route gennem Den Intelligente Central (SECURITY, fail-CLOSED). Defense-in-depth: | [src](../../../core/services/gate_mutation.py#L133) |
| function | `check_module` | `(target)` | auto_improvement_proposer._is_safe_target — True ⇔ sikkert at foreslå. | [src](../../../core/services/gate_mutation.py#L147) |
| function | `check_prompt_target` | `(name)` | prompt_mutation_loop._check_target — allowed + besked (kald-stedet raiser). | [src](../../../core/services/gate_mutation.py#L152) |
| function | `check_record` | `(target_path)` | identity_mutation_log.record_mutation — allowed + blok-grund. | [src](../../../core/services/gate_mutation.py#L158) |

## `core/services/gate_privacy.py`
_Privacy-cluster gate 🔒 — cross-user-deling, GRADERET + fail-CLOSED._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `privacy_gate` | `(ctx)` | ctx: {text, current_user_id}. Returnér ét SECURITY-Verdict for cross-user-deling. | [src](../../../core/services/gate_privacy.py#L26) |

## `core/services/gate_proactivity.py`
_Proactivity-cluster gate — verifikations-disciplin, GRADERET (R2 blød / R2.5 hård)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `proactivity_gate` | `(ctx)` | ctx: {reasoning_tier}. Returnér ét GRADERET Verdict for verifikations-disciplin. | [src](../../../core/services/gate_proactivity.py#L26) |

## `core/services/gate_review.py`
_Review-cluster gate — selv-review-vurdering, GRADERET._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `review_gate` | `(ctx)` | ctx: {review} hvor review har risk_level (low/med/high) + score. | [src](../../../core/services/gate_review.py#L23) |

## `core/services/gate_shadow.py`
_Track 2 — SHADOW-kørsel af de sovende post_output-gates._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_enforced` | `(nerve)` | True hvis gaten er graduated til enforce (i _ENFORCED) OG ikke kill-switchet fra. | [src](../../../core/services/gate_shadow.py#L60) |
| function | `_enforce_verdict` | `(nerve, cluster, klass, verdict)` | Håndhæv en enforced gates ikke-grønne verdict = gør det SYNLIGT som central-incident. | [src](../../../core/services/gate_shadow.py#L71) |
| function | `POST_OUTPUT_GATES_CLUSTERS` | `()` | (nerve, cluster) i kald-rækkefølge — til test/introspektion. | [src](../../../core/services/gate_shadow.py#L88) |
| function | `_shadow_enabled` | `()` | True medmindre gate_kernel.shadow er EKSPLICIT slået fra. Fail-open til ON | [src](../../../core/services/gate_shadow.py#L93) |
| function | `_resolve` | `(mod_path, fn_attr)` | — | [src](../../../core/services/gate_shadow.py#L103) |
| function | `run_post_output_shadow` | `(ctx)` | Kør de 5 sovende gates i SKYGGE via central().decide. | [src](../../../core/services/gate_shadow.py#L108) |

## `core/services/gate_skill.py`
_Skill-Safety-cluster gate 🔒 — graderet SECURITY-gate for skill-indholds-scanning_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `skill_gate` | `(ctx)` | Scan skill-indhold via skill_scanner; returnér graderet Verdict. | [src](../../../core/services/gate_skill.py#L29) |
| class | `SkillScanVerdict` | `` | ScanResult-lignende facade så call-sites er near-drop-in. | [src](../../../core/services/gate_skill.py#L48) |
| method | `SkillScanVerdict.as_dict` | `(self)` | — | [src](../../../core/services/gate_skill.py#L55) |
| function | `_decide` | `(ctx)` | Route gennem Centralen (SECURITY, fail-CLOSED). Central-katastrofe → kør gaten | [src](../../../core/services/gate_skill.py#L59) |
| function | `check_skill_scan` | `(content)` | Scan skill-indhold gennem Centralen. Returnér ScanResult-lignende facade. | [src](../../../core/services/gate_skill.py#L74) |

## `core/services/gate_truth.py`
_Unified TruthGate (cluster B). Smelter Truth-klyngens tre homogene Verdict-gates_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `truth_gate` | `(ctx)` | Kør de tre Truth-checks på samme ctx og kombinér til ét Verdict. | [src](../../../core/services/gate_truth.py#L17) |
| function | `register_truth_nerve` | `(central)` | Registrér den unified TruthGate som post_output-nerve i Centralen. | [src](../../../core/services/gate_truth.py#L29) |

## `core/services/gate_verdict_ledger.py`
_Gate-verdict-ledger — in-memory akkumulator + batchet flush til persistent tabel._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record` | `(nerve, cluster, decision, reason=…)` | Akkumulér ét verdict in-memory. Billig, låst, kaster ALDRIG. | [src](../../../core/services/gate_verdict_ledger.py#L27) |
| function | `_drain` | `()` | Snapshot + nulstil akkumulatoren under lås. Returnerer delta-liste til UPSERT. | [src](../../../core/services/gate_verdict_ledger.py#L53) |
| function | `flush` | `()` | Skriv akkumulerede deltas til den persistente tabel. Returnerer antal rækker rørt. | [src](../../../core/services/gate_verdict_ledger.py#L67) |
| function | `summary` | `()` | Aggregeret verdict-fordeling pr. nerve fra den persistente tabel (survives restart). | [src](../../../core/services/gate_verdict_ledger.py#L81) |

## `core/services/ghost_networks.py`
_Ghost Networks — traces of old patterns._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `archive_dead_nodes` | `(node_ids)` | — | [src](../../../core/services/ghost_networks.py#L9) |
| function | `describe_ghost_network` | `()` | — | [src](../../../core/services/ghost_networks.py#L18) |
| function | `format_ghost_for_prompt` | `()` | — | [src](../../../core/services/ghost_networks.py#L24) |
| function | `reset_ghost_networks` | `()` | — | [src](../../../core/services/ghost_networks.py#L30) |
| function | `build_ghost_networks_surface` | `()` | — | [src](../../../core/services/ghost_networks.py#L34) |

## `core/services/git_actions.py`
_Rolle-aware git-eksekvering for code mode._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_git_container` | `(repo, *a, timeout=…)` | — | [src](../../../core/services/git_actions.py#L16) |
| function | `commit_all_container` | `(repo, message)` | — | [src](../../../core/services/git_actions.py#L20) |
| function | `_operator_exec` | `(name, args)` | — | [src](../../../core/services/git_actions.py#L38) |
| function | `_ws_git` | `(root, uid, gitargs, timeout=…)` | Kør `git -C <root> <gitargs>` på brugerens bro. Returnér (rc, stdout, stderr). | [src](../../../core/services/git_actions.py#L43) |
| function | `commit_all_workstation` | `(root, uid, message)` | — | [src](../../../core/services/git_actions.py#L53) |
| function | `commit_all` | `(target, container_repo, uid, message)` | — | [src](../../../core/services/git_actions.py#L71) |
| function | `parse_owner_repo` | `(remote_url)` | — | [src](../../../core/services/git_actions.py#L83) |
| function | `_ws_git_raw` | `(root, uid, cmd, timeout=…)` | Kør vilkårlig kommando i `root` på brugerens bro (til gh). | [src](../../../core/services/git_actions.py#L94) |
| function | `create_pr` | `(target, container_repo, uid, title, body)` | Commit → branch hvis på default → push → PR (API, ellers gh-fallback). | [src](../../../core/services/git_actions.py#L104) |
| function | `_create_pr_gh` | `(ws, root, uid, base, branch, title, body)` | — | [src](../../../core/services/git_actions.py#L140) |
| function | `_split_gh` | `(args)` | — | [src](../../../core/services/git_actions.py#L154) |

## `core/services/github_connector.py`
_GitHub-connector — API-klient + tool-handlers (v1: issues + PRs)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_headers` | `(token)` | — | [src](../../../core/services/github_connector.py#L53) |
| function | `_get` | `(user_id, path, params=…)` | — | [src](../../../core/services/github_connector.py#L61) |
| function | `list_issues` | `(user_id, repo, *, state=…)` | Issues i `repo` (owner/name). state: open|closed|all. | [src](../../../core/services/github_connector.py#L77) |
| function | `list_prs` | `(user_id, repo, *, state=…)` | Pull requests i `repo` (owner/name). state: open|closed|all. | [src](../../../core/services/github_connector.py#L92) |
| function | `_post` | `(user_id, path, payload)` | — | [src](../../../core/services/github_connector.py#L107) |
| function | `create_pr` | `(user_id, repo, *, head, base, title, body=…)` | Opret PR i `repo` (owner/name). head/base = branch-navne. | [src](../../../core/services/github_connector.py#L123) |

## `core/services/global_workspace.py`
_Global Workspace — shared broadcast buffer (Experiment 3: Global Workspace Theory)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `publish_to_workspace` | `(source, topic, signal_type, payload_summary)` | Add an entry to the shared workspace buffer. | [src](../../../core/services/global_workspace.py#L45) |
| function | `get_workspace_snapshot` | `()` | Return current workspace buffer as a list (newest last). | [src](../../../core/services/global_workspace.py#L63) |
| function | `_extract_topic` | `(event_kind, payload)` | Extract a short topic string from an event payload. | [src](../../../core/services/global_workspace.py#L69) |
| function | `_topic_jaccard` | `(topic_a, topic_b)` | Jaccard similarity between two topic strings (word-level). | [src](../../../core/services/global_workspace.py#L80) |
| function | `_handle_event` | `(kind, payload)` | Map eventbus event to workspace entry. | [src](../../../core/services/global_workspace.py#L91) |
| function | `_listener_loop` | `(q)` | — | [src](../../../core/services/global_workspace.py#L104) |
| function | `register_event_listeners` | `()` | Start background eventbus listener thread. | [src](../../../core/services/global_workspace.py#L120) |
| function | `stop_event_listeners` | `()` | Stop the background listener thread. | [src](../../../core/services/global_workspace.py#L141) |

## `core/services/gmail_connector.py`
_Gmail-connector — API-klient + tool-handlers (vertical: search + list)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_token` | `(user_id)` | — | [src](../../../core/services/gmail_connector.py#L78) |
| function | `_headers` | `(token)` | — | [src](../../../core/services/gmail_connector.py#L85) |
| function | `_clamp` | `(n, lo, hi, default)` | — | [src](../../../core/services/gmail_connector.py#L89) |
| function | `_fetch_messages` | `(user_id, query, max_results)` | Fælles kerne for search/list: hent id-liste → berig med headers/snippet. | [src](../../../core/services/gmail_connector.py#L97) |
| function | `search` | `(user_id, query, *, max_results=…)` | — | [src](../../../core/services/gmail_connector.py#L142) |
| function | `list_inbox` | `(user_id, *, max_results=…)` | — | [src](../../../core/services/gmail_connector.py#L148) |
| function | `send_message` | `(user_id, to, subject, body)` | Send en mail på brugerens vegne. KRÆVER approval-flow før den eksponeres som tool. | [src](../../../core/services/gmail_connector.py#L152) |

## `core/services/goal_signal_synthesizer.py`
_Goal signal synthesizer — surface candidate goals from dreams/reflections._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_gather_signals` | `()` | Collect recent introspective signals as text for LLM. | [src](../../../core/services/goal_signal_synthesizer.py#L23) |
| function | `synthesize_candidate_goals` | `(*, max_candidates=…)` | Run one synthesis pass — propose new goals from recent signals. | [src](../../../core/services/goal_signal_synthesizer.py#L46) |

## `core/services/goal_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_goal_signals_for_visible_turn` | `(*, session_id, run_id, user_message)` | — | [src](../../../core/services/goal_signal_tracking.py#L23) |
| function | `refresh_runtime_goal_signal_statuses` | `()` | — | [src](../../../core/services/goal_signal_tracking.py#L64) |
| function | `build_runtime_goal_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/goal_signal_tracking.py#L101) |
| function | `_extract_goal_candidates` | `(*, user_message, completed_domains)` | — | [src](../../../core/services/goal_signal_tracking.py#L126) |
| function | `_goal_from_active_focus` | `(focus, *, user_message, completed_domains)` | — | [src](../../../core/services/goal_signal_tracking.py#L152) |
| function | `_persist_goal_signals` | `(*, goals, session_id, run_id)` | — | [src](../../../core/services/goal_signal_tracking.py#L225) |
| function | `_apply_completion_signals` | `(domains)` | — | [src](../../../core/services/goal_signal_tracking.py#L292) |
| function | `_supersede_replaced_goal_signals` | `(persisted_item, *, updated_at)` | — | [src](../../../core/services/goal_signal_tracking.py#L347) |
| function | `_completed_goal_domains` | `(message)` | — | [src](../../../core/services/goal_signal_tracking.py#L377) |
| function | `_blocking_state_for_domain` | `(domain_key)` | — | [src](../../../core/services/goal_signal_tracking.py#L385) |
| function | `_has_completed_goal_history` | `(domain_key)` | — | [src](../../../core/services/goal_signal_tracking.py#L430) |
| function | `_domain_key_from_focus` | `(canonical_key)` | — | [src](../../../core/services/goal_signal_tracking.py#L439) |
| function | `_domain_key_from_critic` | `(canonical_key)` | — | [src](../../../core/services/goal_signal_tracking.py#L454) |
| function | `_domain_key_from_self_model` | `(canonical_key)` | — | [src](../../../core/services/goal_signal_tracking.py#L463) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/goal_signal_tracking.py#L472) |
| function | `_message_domain_key` | `(text)` | — | [src](../../../core/services/goal_signal_tracking.py#L476) |
| function | `_goal_title` | `(domain_key, fallback)` | — | [src](../../../core/services/goal_signal_tracking.py#L485) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/goal_signal_tracking.py#L493) |
| function | `_rank` | `(value)` | — | [src](../../../core/services/goal_signal_tracking.py#L502) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/goal_signal_tracking.py#L506) |

## `core/services/good_enough_gate.py`
_Good-enough gate — completion criterion for autonomous runs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_recent_run_signals` | `(run_id, limit=…)` | — | [src](../../../core/services/good_enough_gate.py#L34) |
| function | `evaluate_good_enough` | `(*, run_id=…, iterations_done=…, iteration_budget=…, minutes_elapsed=…, minutes_budget=…)` | — | [src](../../../core/services/good_enough_gate.py#L57) |
| function | `_exec_check_good_enough` | `(args)` | — | [src](../../../core/services/good_enough_gate.py#L148) |

## `core/services/google_connector.py`
_Google-pakke-connector — Calendar/Drive/Docs/Sheets/Slides (læse-tools)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get` | `(user_id, url, params, err_prefix)` | Fælles GET med brugerens Google-token. → {status, data} | {status:error,...}. | [src](../../../core/services/google_connector.py#L168) |
| function | `_send` | `(user_id, method, url, *, json_body=…, params=…, err_prefix=…)` | Skrive-kald (POST/PUT) med brugerens Google-token. Bruges af create/edit-tools. | [src](../../../core/services/google_connector.py#L188) |
| function | `_clamp` | `(n, lo, hi, default)` | — | [src](../../../core/services/google_connector.py#L209) |
| function | `list_events` | `(user_id, *, max_results=…)` | — | [src](../../../core/services/google_connector.py#L216) |
| function | `drive_search` | `(user_id, *, query=…, max_results=…)` | — | [src](../../../core/services/google_connector.py#L237) |
| function | `_doc_text` | `(content)` | — | [src](../../../core/services/google_connector.py#L259) |
| function | `docs_read` | `(user_id, document_id)` | — | [src](../../../core/services/google_connector.py#L272) |
| function | `sheets_read` | `(user_id, spreadsheet_id, cell_range)` | — | [src](../../../core/services/google_connector.py#L283) |
| function | `_slides_text` | `(pres)` | — | [src](../../../core/services/google_connector.py#L297) |
| function | `slides_read` | `(user_id, presentation_id)` | — | [src](../../../core/services/google_connector.py#L311) |
| function | `create_event` | `(user_id, summary, start, *, end=…, description=…, location=…)` | Opret en begivenhed i brugerens primære kalender. start/end = ISO-8601. | [src](../../../core/services/google_connector.py#L325) |
| function | `append_doc` | `(user_id, document_id, text)` | Tilføj tekst i slutningen af et Google Docs-dokument. | [src](../../../core/services/google_connector.py#L355) |
| function | `write_sheet` | `(user_id, spreadsheet_id, cell_range, values)` | Skriv celler i et Google Sheets-regneark (overskriver range). values = liste af rækker. | [src](../../../core/services/google_connector.py#L370) |

## `core/services/google_login.py`
_Google app-login (§12) — kort-levende login-resultat-store + orkestrering._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_resolve_role` | `(user_id)` | Find brugerens faktiske rolle (SQLite-user_db → ellers users.json → member). | [src](../../../core/services/google_login.py#L25) |
| function | `_gc` | `(now)` | — | [src](../../../core/services/google_login.py#L44) |
| function | `begin_login` | `(app_id=…, *, now=…)` | Start et login. Returnerer (nonce, state_uid) — state_uid lægges i OAuth-state. | [src](../../../core/services/google_login.py#L49) |
| function | `begin_link` | `(user_id, *, now=…)` | Start en Google-linking for en EKSISTERENDE (indlogget) bruger. | [src](../../../core/services/google_login.py#L58) |
| function | `is_login_state` | `(state_uid)` | — | [src](../../../core/services/google_login.py#L67) |
| function | `complete` | `(state_uid, google_email, *, now=…)` | Kaldt af callbacken med den VERIFICEREDE Google-email. Returnerer en kort | [src](../../../core/services/google_login.py#L71) |
| function | `take_result` | `(nonce, *, now=…)` | Engangs-hent af login-resultatet (fjernes ved hentning når det er færdigt). | [src](../../../core/services/google_login.py#L108) |

## `core/services/governance_bootstrap.py`
_Governance bootstrap — idempotent setup of default windows, jobs handlers, automations._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_default_windows` | `()` | Ensure default scheduled job windows exist. Returns list of window_ids | [src](../../../core/services/governance_bootstrap.py#L15) |
| function | `ensure_default_job_handlers` | `()` | Register default job-type handlers. Returns list of job_type names registered. | [src](../../../core/services/governance_bootstrap.py#L73) |
| function | `ensure_default_automations` | `()` | Seed a couple of baseline automations so the DSL surface has examples. | [src](../../../core/services/governance_bootstrap.py#L277) |
| function | `ensure_warmup_job` | `()` | Enqueue a single low-priority warmup job on first boot so the | [src](../../../core/services/governance_bootstrap.py#L341) |
| function | `bootstrap_all` | `()` | Run all idempotent bootstrap helpers. Safe at any startup. | [src](../../../core/services/governance_bootstrap.py#L366) |

## `core/services/gratitude_tracker.py`
_Gratitude Tracker — accumulated appreciation over time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_gratitude` | `(*, trigger_event, detail=…)` | — | [src](../../../core/services/gratitude_tracker.py#L20) |
| function | `detect_gratitude_from_interaction` | `(*, user_mood, outcome_status, was_corrected, autonomy_granted=…)` | — | [src](../../../core/services/gratitude_tracker.py#L44) |
| function | `build_gratitude_surface` | `()` | — | [src](../../../core/services/gratitude_tracker.py#L59) |

## `core/services/ground_truth_registry.py`
_Ground Truth Registry — Layer 3 of the Lying Engine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_detect_host` | `()` | Detect which machine Jarvis runs on — hostname + primary IP. | [src](../../../core/services/ground_truth_registry.py#L146) |
| function | `_read_config_provider` | `()` | Read the current provider name from runtime.json. | [src](../../../core/services/ground_truth_registry.py#L169) |
| function | `_read_config_model` | `()` | Read the current model name from runtime.json. | [src](../../../core/services/ground_truth_registry.py#L186) |
| function | `_query_expression_count` | `()` | Count expressions from the DB. Returns None on failure. | [src](../../../core/services/ground_truth_registry.py#L204) |
| function | `_query_commit_count` | `()` | Count total commits in the repo. | [src](../../../core/services/ground_truth_registry.py#L218) |
| function | `_query_recent_commit_sha` | `()` | Get the current HEAD SHA (short). | [src](../../../core/services/ground_truth_registry.py#L232) |
| function | `_query_daemon_count` | `()` | Count active (enabled) daemons via daemon manager. | [src](../../../core/services/ground_truth_registry.py#L244) |
| function | `_query_gpu_info` | `()` | Quick GPU summary if available. | [src](../../../core/services/ground_truth_registry.py#L254) |
| function | `_query_uname` | `()` | Kernel/OS info. | [src](../../../core/services/ground_truth_registry.py#L269) |
| function | `collect_ground_truth` | `()` | Collect all available ground truth about Jarvis. Slow — call rarely. | [src](../../../core/services/ground_truth_registry.py#L282) |
| function | `refresh_ground_truth` | `()` | Force refresh the ground truth cache. Returns the fresh registry. | [src](../../../core/services/ground_truth_registry.py#L300) |
| function | `get_ground_truth` | `(key=…, force_refresh=…)` | Get ground truth from cache, auto-refreshing if stale. | [src](../../../core/services/ground_truth_registry.py#L315) |
| function | `ground_truth_summary` | `()` | Return a human-readable summary block for injection or repair. | [src](../../../core/services/ground_truth_registry.py#L343) |
| function | `verify_system_claim` | `(claim_text)` | Verify a system claim (IP, host, path) against ground truth. | [src](../../../core/services/ground_truth_registry.py#L370) |
| function | `lookup_infrastructure_fact` | `(key)` | Look up a known infrastructure fact (host/path/port) for ground-truth | [src](../../../core/services/ground_truth_registry.py#L438) |
| function | `verify_stats_claim` | `(claim_text)` | Verify a statistic claim (counts of expressions, daemons, commits) | [src](../../../core/services/ground_truth_registry.py#L455) |
| function | `ground_truth_daemon_tick` | `()` | Called by heartbeat daemon — refreshes cache and returns summary. | [src](../../../core/services/ground_truth_registry.py#L506) |

## `core/services/guided_learning_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_guided_learning_runtime_surface` | `()` | — | [src](../../../core/services/guided_learning_runtime.py#L11) |
| function | `_build_guided_learning_runtime_surface_uncached` | `()` | — | [src](../../../core/services/guided_learning_runtime.py#L19) |
| function | `build_guided_learning_runtime_from_sources` | `(*, adaptive_planner, adaptive_reasoning, epistemic_runtime_state, prompt_evolution, dream_articulation, dream_influence, loop_runtime, council_runtime)` | — | [src](../../../core/services/guided_learning_runtime.py#L32) |
| function | `build_guided_learning_prompt_section` | `(surface=…)` | — | [src](../../../core/services/guided_learning_runtime.py#L150) |
| function | `_derive_learning_focus` | `(*, planner, reasoning, epistemic, prompt_summary, dream_summary, dream_influence, loop_summary, council)` | — | [src](../../../core/services/guided_learning_runtime.py#L177) |
| function | `_derive_learning_mode` | `(*, learning_focus, planner, reasoning, epistemic, prompt_summary, dream_summary, dream_influence, council)` | — | [src](../../../core/services/guided_learning_runtime.py#L214) |
| function | `_derive_learning_posture` | `(*, learning_mode, council, reasoning, dream_influence)` | — | [src](../../../core/services/guided_learning_runtime.py#L247) |
| function | `_derive_next_learning_bias` | `(*, learning_mode, learning_focus, planner, reasoning, epistemic, prompt_summary, dream_influence)` | — | [src](../../../core/services/guided_learning_runtime.py#L265) |
| function | `_derive_learning_pressure` | `(*, learning_mode, planner, epistemic, council, prompt_summary, dream_summary, dream_influence)` | — | [src](../../../core/services/guided_learning_runtime.py#L296) |
| function | `_derive_confidence` | `(*, learning_mode, learning_focus, learning_pressure, council, epistemic)` | — | [src](../../../core/services/guided_learning_runtime.py#L321) |
| function | `_source_contributors` | `(*, adaptive_planner, adaptive_reasoning, epistemic, prompt_summary, dream_summary, dream_influence, loop_summary, council)` | — | [src](../../../core/services/guided_learning_runtime.py#L340) |
| function | `_guidance_for_learning` | `(state)` | — | [src](../../../core/services/guided_learning_runtime.py#L427) |
| function | `_safe_adaptive_planner` | `()` | — | [src](../../../core/services/guided_learning_runtime.py#L442) |
| function | `_safe_adaptive_reasoning` | `()` | — | [src](../../../core/services/guided_learning_runtime.py#L450) |
| function | `_safe_epistemic_runtime_state` | `()` | — | [src](../../../core/services/guided_learning_runtime.py#L458) |
| function | `_safe_prompt_evolution` | `()` | — | [src](../../../core/services/guided_learning_runtime.py#L466) |
| function | `_safe_dream_articulation` | `()` | — | [src](../../../core/services/guided_learning_runtime.py#L474) |
| function | `_safe_dream_influence` | `()` | — | [src](../../../core/services/guided_learning_runtime.py#L482) |
| function | `_safe_loop_runtime` | `()` | — | [src](../../../core/services/guided_learning_runtime.py#L489) |
| function | `_safe_council_runtime` | `()` | — | [src](../../../core/services/guided_learning_runtime.py#L497) |

## `core/services/gut_calibration.py`
_Gut-calibration wiring — fodrer cognitive_gut_state fra run-livscyklussen._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `observe_run_event` | `(kind, payload)` | Dispatch fra run_closure_gate's listener. Kaster aldrig. | [src](../../../core/services/gut_calibration.py#L29) |
| function | `_on_started` | `(payload)` | — | [src](../../../core/services/gut_calibration.py#L40) |
| function | `_on_outcome` | `(payload, actual_outcome)` | — | [src](../../../core/services/gut_calibration.py#L70) |

## `core/services/gut_engine.py`
_Gut Engine — intuition and calibration tracking._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `derive_gut_signal` | `(*, task_description, confidence=…, recent_error_count=…, recent_success_count=…)` | Generate a gut-feel hunch about a task. | [src](../../../core/services/gut_engine.py#L21) |
| function | `_consumer_mode` | `()` | — | [src](../../../core/services/gut_engine.py#L94) |
| function | `_gate_threshold` | `()` | — | [src](../../../core/services/gut_engine.py#L104) |
| function | `gut_gate` | `(proceed_confidence, *, context=…)` | Beslut om et proceed-valg må fortsætte, gated på gut-confidence. | [src](../../../core/services/gut_engine.py#L112) |
| function | `record_gut_outcome` | `(*, hunch, actual_outcome)` | Record whether the gut hunch was correct. | [src](../../../core/services/gut_engine.py#L159) |
| function | `build_gut_surface` | `()` | — | [src](../../../core/services/gut_engine.py#L181) |

## `core/services/habit_tracker.py`
_Habit Tracker — detects recurring patterns and friction points._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_habit_from_run` | `(*, run_id, task_signature, outcome_status, attempt_count=…)` | Track habit pattern and friction from a visible run. | [src](../../../core/services/habit_tracker.py#L24) |
| function | `build_habit_surface` | `()` | — | [src](../../../core/services/habit_tracker.py#L69) |
| function | `_normalize_signature` | `(text)` | Create a stable signature from task description. | [src](../../../core/services/habit_tracker.py#L83) |

## `core/services/habits_pipeline.py`
_Habits Pipeline — detect → track → suggest automation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/habits_pipeline.py#L34) |
| function | `_ensure_tables` | `()` | Tables exist from v2 db.py — this is idempotent no-op unless schema changes. | [src](../../../core/services/habits_pipeline.py#L38) |
| function | `_normalize_signature` | `(message)` | — | [src](../../../core/services/habits_pipeline.py#L91) |
| function | `_upsert_habit` | `(pattern_key, now)` | — | [src](../../../core/services/habits_pipeline.py#L105) |
| function | `_upsert_friction` | `(task_signature, now)` | — | [src](../../../core/services/habits_pipeline.py#L136) |
| function | `_maybe_create_suggestion` | `(*, source_type, source_id, suggestion_text, confidence, now)` | — | [src](../../../core/services/habits_pipeline.py#L167) |
| function | `record_habit_signal` | `(*, message)` | Main entry: record a habit signal from a chat message. | [src](../../../core/services/habits_pipeline.py#L199) |
| function | `list_habits` | `(*, limit=…)` | — | [src](../../../core/services/habits_pipeline.py#L286) |
| function | `list_friction` | `(*, limit=…)` | — | [src](../../../core/services/habits_pipeline.py#L298) |
| function | `list_suggestions` | `(*, status=…, limit=…)` | — | [src](../../../core/services/habits_pipeline.py#L310) |
| function | `accept_suggestion` | `(*, suggestion_id)` | — | [src](../../../core/services/habits_pipeline.py#L323) |
| function | `reject_suggestion` | `(*, suggestion_id)` | — | [src](../../../core/services/habits_pipeline.py#L350) |
| function | `build_habits_pipeline_surface` | `()` | — | [src](../../../core/services/habits_pipeline.py#L369) |

