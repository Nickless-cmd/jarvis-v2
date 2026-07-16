# `core.services.11` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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
| class | `Decision` | `` | — | [src](../../../core/services/gate_kernel.py#L24) |
| class | `GateClass` | `` | — | [src](../../../core/services/gate_kernel.py#L31) |
| class | `Verdict` | `` | — | [src](../../../core/services/gate_kernel.py#L40) |
| method | `Verdict.is_blocking` | `(self)` | — | [src](../../../core/services/gate_kernel.py#L59) |
| function | `worst` | `(verdicts)` | Aggregeret beslutning efter præcedens RED>YELLOW>GREEN>SKIP. | [src](../../../core/services/gate_kernel.py#L63) |
| class | `_Gate` | `` | — | [src](../../../core/services/gate_kernel.py#L71) |
| function | `_source_loc` | `(fn)` | Gatens egen registrerings-placering (fil + firstlineno) via inspect. Self-safe: | [src](../../../core/services/gate_kernel.py#L82) |
| class | `GateKernel` | `` | — | [src](../../../core/services/gate_kernel.py#L103) |
| method | `GateKernel.__init__` | `(self, *, flag_reader=…, emit=…)` | — | [src](../../../core/services/gate_kernel.py#L104) |
| method | `GateKernel.register` | `(self, name, phase, fn, *, klass=…, timeout_ms=…, flag_key=…)` | — | [src](../../../core/services/gate_kernel.py#L112) |
| method | `GateKernel.gates_for` | `(self, phase)` | — | [src](../../../core/services/gate_kernel.py#L120) |
| method | `GateKernel._fail_verdict` | `(self, g, reason)` | — | [src](../../../core/services/gate_kernel.py#L124) |
| method | `GateKernel._run_one` | `(self, g, ctx)` | — | [src](../../../core/services/gate_kernel.py#L130) |
| method | `GateKernel.run_phase` | `(self, phase, ctx)` | Kør alle gates i en fase isoleret; emit ÉT event; returnér verdicts. | [src](../../../core/services/gate_kernel.py#L173) |
| function | `_normalize` | `(g, raw)` | Tillad gates at returnere en færdig Verdict, et dict, eller None (=GREEN). | [src](../../../core/services/gate_kernel.py#L204) |
| function | `_default_flag_reader` | `(flag_key)` | Returnér True/False hvis flag'et er EKSPLICIT sat i shared_cache, ellers None | [src](../../../core/services/gate_kernel.py#L223) |
| function | `_default_emit` | `(kind, payload)` | — | [src](../../../core/services/gate_kernel.py#L238) |
| function | `kernel` | `()` | — | [src](../../../core/services/gate_kernel.py#L250) |

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

## `core/services/gate_pattern_learning.py`
_Gate-mønster-læring — vane-bryder oven på gate-substratet (2026-07-13)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_hydrated` | `()` | Genindlæs den durable snapshot ÉN gang ved første brug (ikke ved import → tests offline-rene). | [src](../../../core/services/gate_pattern_learning.py#L40) |
| function | `_normalize_detected` | `(text)` | Normalisér den detekterede substring til en vane-FORM: lowercase, whitespace-kollaps, | [src](../../../core/services/gate_pattern_learning.py#L56) |
| function | `record_gate_pattern` | `(pattern, detected_text, *, session_id=…, now=…)` | Registrér én gate-fyring for (pattern, detected_text). Self-safe — kaster ALDRIG. | [src](../../../core/services/gate_pattern_learning.py#L67) |
| function | `repeated_patterns` | `(threshold=…, now=…)` | Overflade vane-kandidaterne: mønstre med count ≥ threshold indenfor alders-vinduet. | [src](../../../core/services/gate_pattern_learning.py#L121) |
| function | `_evict_oldest_locked` | `()` | Drop den ældste (mindst nyligt sete) nøgle. Kaldes under _LOCK. | [src](../../../core/services/gate_pattern_learning.py#L140) |
| function | `_emit_repeat_nudge` | `(pattern, sample, count, *, n_sessions)` | Nudge-substratet: fortæl Centralen at et gate-mønster er blevet en VANE. Self-safe. | [src](../../../core/services/gate_pattern_learning.py#L149) |
| function | `_persist_best_effort` | `(force=…)` | Bedste-indsats durabel snapshot til runtime_state (overlever genstart). Fire-and-forget, | [src](../../../core/services/gate_pattern_learning.py#L167) |
| function | `hydrate` | `()` | Genindlæs durabel snapshot fra runtime_state ind i in-memory-store. Kaldes eksplicit | [src](../../../core/services/gate_pattern_learning.py#L195) |
| function | `_reset` | `()` | Test-hook: ryd in-memory-store + durabel snapshot + hydrate-flag (ren slate, så | [src](../../../core/services/gate_pattern_learning.py#L227) |

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
| function | `POST_OUTPUT_GATES_CLUSTERS` | `()` | (nerve, cluster) i kald-rækkefølge — til test/introspektion. | [src](../../../core/services/gate_shadow.py#L97) |
| function | `_shadow_enabled` | `()` | True medmindre gate_kernel.shadow er EKSPLICIT slået fra. Fail-open til ON | [src](../../../core/services/gate_shadow.py#L102) |
| function | `_resolve` | `(mod_path, fn_attr)` | — | [src](../../../core/services/gate_shadow.py#L112) |
| function | `run_post_output_shadow` | `(ctx)` | Kør de 5 sovende gates i SKYGGE via central().decide. | [src](../../../core/services/gate_shadow.py#L117) |

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
| function | `register_truth_nerve` | `(central)` | Registrér den unified TruthGate som post_output-nerve i Centralen. | [src](../../../core/services/gate_truth.py#L33) |

## `core/services/gate_verdict_ledger.py`
_Gate-verdict-ledger — in-memory akkumulator + batchet flush til persistent tabel._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record` | `(nerve, cluster, decision, reason=…)` | Akkumulér ét verdict in-memory. Billig, låst, kaster ALDRIG. | [src](../../../core/services/gate_verdict_ledger.py#L27) |
| function | `_drain` | `()` | Snapshot + nulstil akkumulatoren under lås. Returnerer delta-liste til UPSERT. | [src](../../../core/services/gate_verdict_ledger.py#L53) |
| function | `_requeue` | `(deltas)` | Læg ubekræftede deltas TILBAGE i akkumulatoren (merge-forward), så en fejlet flush | [src](../../../core/services/gate_verdict_ledger.py#L67) |
| function | `flush` | `()` | Skriv akkumulerede deltas til den persistente tabel. Returnerer antal rækker rørt. | [src](../../../core/services/gate_verdict_ledger.py#L100) |
| function | `summary` | `()` | Aggregeret verdict-fordeling pr. nerve fra den persistente tabel (survives restart). | [src](../../../core/services/gate_verdict_ledger.py#L125) |

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

## `core/services/hallucination_guard.py`
_Hallucination Guard — forced memory-check before answering._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_word_present` | `(word, text_lower)` | Word-boundary check: True if `word` appears as a standalone token (with optional plural). | [src](../../../core/services/hallucination_guard.py#L85) |
| function | `_section_keywords_for_message` | `(message)` | Derive keywords from the message so we can find the right MEMORY section. | [src](../../../core/services/hallucination_guard.py#L101) |
| function | `classify_question` | `(message)` | Classify the message: 'factual' | 'casual' | 'tool_call'. | [src](../../../core/services/hallucination_guard.py#L115) |
| function | `_ws_has_content` | `(path)` | Eksistens-tjek encryption-aware: plaintext eller member .enc. | [src](../../../core/services/hallucination_guard.py#L145) |
| function | `_find_memory_path` | `()` | Find MEMORY.md — look in runtime workspace first, then repo. | [src](../../../core/services/hallucination_guard.py#L153) |
| function | `_find_curated_paths` | `()` | Locate all curated workspace files for hallucination-guard recall. | [src](../../../core/services/hallucination_guard.py#L182) |
| function | `_extract_relevant_sections` | `(memory_text, keywords, max_chars=…)` | Find MEMORY.md-sektioner der matcher keywords, returnér som tekst. | [src](../../../core/services/hallucination_guard.py#L216) |
| function | `_observe_guard_decision` | `(*, activated, reason)` | Egress-frit Central-observe af hallucination-guardens beslutning (§7.2). | [src](../../../core/services/hallucination_guard.py#L300) |
| function | `inject_memory_into_prompt` | `(message, chat_messages, *, memory_path=…)` | Inject relevant memory as a system-role message into the prompt. | [src](../../../core/services/hallucination_guard.py#L324) |

## `core/services/hardware_body.py`
_Hardware body — collects CPU/GPU/RAM/VRAM/disk/temp signals._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `get_hardware_state` | `()` | Return current hardware state. Cached for 30s. Never raises. | [src](../../../core/services/hardware_body.py#L22) |
| function | `_collect` | `()` | — | [src](../../../core/services/hardware_body.py#L34) |
| function | `_somatic_overlay` | `(state)` | — | [src](../../../core/services/hardware_body.py#L98) |
| function | `_compute_pressure` | `(state)` | Compute overall pressure: low / medium / high / critical. | [src](../../../core/services/hardware_body.py#L121) |
| function | `_derive_energy_budget` | `(energy_level, drain_score, pressure)` | — | [src](../../../core/services/hardware_body.py#L172) |
| function | `_derive_circadian_preference` | `(clock_phase)` | — | [src](../../../core/services/hardware_body.py#L189) |
| function | `_derive_wake_state` | `(clock_phase, energy_level)` | — | [src](../../../core/services/hardware_body.py#L195) |
| function | `build_hardware_body_surface` | `()` | — | [src](../../../core/services/hardware_body.py#L204) |
| function | `run_hardware_body_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence-producer: Jarvis mærker sin egen krop (rådets #1 — "start med kroppen"). | [src](../../../core/services/hardware_body.py#L213) |
| function | `register_hardware_body_producer` | `()` | Registrér krop-sansningen som cadence-producer (~hvert 60s — hardware ændrer sig | [src](../../../core/services/hardware_body.py#L270) |
| function | `_emit_body_event` | `(metric, value)` | — | [src](../../../core/services/hardware_body.py#L283) |

## `core/services/heartbeat_phases.py`
_Heartbeat phases — explicit Sense / Reflect / Act structure on top of existing tick._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_user_active_recently` | `(*, window_minutes=…)` | Cheap check: has any user-role chat message landed in the last N minutes? | [src](../../../core/services/heartbeat_phases.py#L39) |
| function | `sense_phase` | `(*, name=…)` | Gather signals for this tick. Pure-read — no side effects. | [src](../../../core/services/heartbeat_phases.py#L64) |
| function | `_classify_activity` | `(signals)` | Classify current activity level from signals. | [src](../../../core/services/heartbeat_phases.py#L149) |
| function | `_identify_priorities` | `(signals)` | Heuristic — what should this tick attend to? | [src](../../../core/services/heartbeat_phases.py#L159) |
| function | `reflect_phase` | `(signals)` | Synthesize reflection. Heuristic-only by default; LLM optional. | [src](../../../core/services/heartbeat_phases.py#L175) |
| function | `_collect_active_goals` | `()` | Fetch active goals for chain proposal targeting. | [src](../../../core/services/heartbeat_phases.py#L235) |
| function | `_propose_skill_chains_in_idle` | `(max_goals=…)` | Propose skill chains for active goals. Time-bounded, never blocks. | [src](../../../core/services/heartbeat_phases.py#L244) |
| function | `format_chain_proposals` | `(max_chars=…)` | Format recent chain proposals for awareness injection. | [src](../../../core/services/heartbeat_phases.py#L291) |
| function | `clear_chain_proposals` | `()` | Clear cached chain proposals (e.g. after execution or user dismiss). | [src](../../../core/services/heartbeat_phases.py#L314) |
| function | `get_chain_proposals` | `()` | Return current chain proposals for inspection. | [src](../../../core/services/heartbeat_phases.py#L319) |
| function | `productive_idle` | `(*, budget_seconds=…)` | Run light maintenance work when there's no clear action. Time-bounded. | [src](../../../core/services/heartbeat_phases.py#L324) |
| function | `act_phase` | `(*, signals, reflection, name=…, trigger=…)` | Either run normal heartbeat tick OR productive idle, based on reflection. | [src](../../../core/services/heartbeat_phases.py#L564) |
| function | `tick_with_phases` | `(*, name=…, trigger=…)` | Run all 3 phases in sequence, return structured result. | [src](../../../core/services/heartbeat_phases.py#L640) |
| function | `_exec_phased_tick` | `(args)` | — | [src](../../../core/services/heartbeat_phases.py#L685) |
| function | `_exec_sense_only` | `(args)` | Read-only: gather current signals without running reflection or action. | [src](../../../core/services/heartbeat_phases.py#L692) |

## `core/services/heartbeat_provider_fallback.py`
_Heartbeat provider fallback — cheap cloud lane when primary (Groq) fails._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `execute_openai_compat_heartbeat_prompt` | `(*, prompt, target)` | Call an OpenAI-chat/completions-compatible provider for heartbeat. | [src](../../../core/services/heartbeat_provider_fallback.py#L53) |
| function | `try_heartbeat_cheap_fallback` | `(prompt)` | Try cheap lane providers (skip groq + ollamafreeapi) as heartbeat fallback. | [src](../../../core/services/heartbeat_provider_fallback.py#L121) |

## `core/services/heartbeat_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `HeartbeatExecutionResult` | `` | — | [src](../../../core/services/heartbeat_runtime.py#L239) |
| function | `start_heartbeat_scheduler` | `(*, name=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L245) |
| function | `stop_heartbeat_scheduler` | `(*, name=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L287) |
| function | `_cheap_heartbeat_schedule_state` | `(name)` | Compute just the schedule-state dict without touching sub-surfaces. | [src](../../../core/services/heartbeat_runtime.py#L299) |
| function | `poll_heartbeat_schedule` | `(*, name=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L317) |
| function | `_run_heartbeat_tick_with_deadline` | `(*, name, trigger, deadline_seconds=…)` | Run a heartbeat tick on a background thread with a wall-clock deadline. | [src](../../../core/services/heartbeat_runtime.py#L360) |
| function | `_poll_heartbeat_schedule_with_trigger` | `(*, name, due_trigger)` | — | [src](../../../core/services/heartbeat_runtime.py#L421) |
| function | `heartbeat_runtime_surface` | `(name=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L451) |
| function | `_heartbeat_runtime_surface_uncached` | `(name=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L475) |
| function | `_build_cognitive_surfaces` | `()` | Build cognitive architecture surfaces safely (never raise). | [src](../../../core/services/heartbeat_runtime.py#L573) |
| function | `_safe_surface` | `(target, key, builder)` | Call builder and store result; swallow any errors. | [src](../../../core/services/heartbeat_runtime.py#L1148) |
| function | `run_heartbeat_tick` | `(*, name=…, trigger=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L1177) |
| function | `_daemon_tick_with_deadline` | `(name, fn, *args, deadline_seconds=…, **kwargs)` | Run a daemon tick on a background thread with a wall-clock deadline. | [src](../../../core/services/heartbeat_runtime.py#L1196) |
| function | `_run_heartbeat_tick_locked` | `(*, name=…, trigger=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L1259) |
| function | `load_heartbeat_policy` | `(name=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L2231) |
| function | `_build_heartbeat_context` | `(*, policy, merged_state, trigger)` | — | [src](../../../core/services/heartbeat_runtime.py#L2277) |
| function | `_build_heartbeat_cognitive_frame` | `(*, merged_state)` | — | [src](../../../core/services/heartbeat_runtime.py#L2490) |
| function | `_build_executive_visible_state` | `(*, merged_state, context)` | — | [src](../../../core/services/heartbeat_runtime.py#L2510) |
| function | `_decide_executive_action` | `(*, merged_state, context, now_iso)` | — | [src](../../../core/services/heartbeat_runtime.py#L2529) |
| function | `_execute_executive_decision` | `(executive_decision)` | — | [src](../../../core/services/heartbeat_runtime.py#L2596) |
| function | `_log_liveness_dedup` | `(signal, trigger)` | — | [src](../../../core/services/heartbeat_runtime.py#L2636) |
| function | `_build_heartbeat_liveness_signal` | `(*, merged_state, trigger)` | — | [src](../../../core/services/heartbeat_runtime.py#L2659) |
| function | `_select_heartbeat_target` | `(policy=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L3263) |
| function | `_runtime_selected_local_target` | `(*, settings)` | — | [src](../../../core/services/heartbeat_runtime.py#L3388) |
| function | `_phase1_rule_based_decision` | `(*, policy, open_loops, liveness=…, prompt=…)` | Rule-based heartbeat decision for phase1-runtime or LLM-failure fallback. | [src](../../../core/services/heartbeat_runtime.py#L3411) |
| function | `_execute_heartbeat_model` | `(*, prompt, target, policy, open_loops, liveness=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L3520) |
| function | `_recent_ping_history` | `(*, limit=…)` | Return the last N assistant ping_text strings already delivered. | [src](../../../core/services/heartbeat_runtime.py#L3607) |
| function | `_user_recently_active` | `(minutes)` | Return True if any user-role chat message landed within the window. | [src](../../../core/services/heartbeat_runtime.py#L3641) |
| function | `_active_chat_gate_blocked_result` | `(*, tick_id, decision_type, minutes)` | Build the blocked-result + emit deferred event for active-chat gate. | [src](../../../core/services/heartbeat_runtime.py#L3673) |
| function | `_heartbeat_prompt_text` | `(base_text)` | — | [src](../../../core/services/heartbeat_runtime.py#L3703) |
| function | `_parse_heartbeat_decision` | `(raw_text)` | — | [src](../../../core/services/heartbeat_runtime.py#L3825) |
| function | `_parse_heartbeat_decision_bounded` | `(raw_text)` | — | [src](../../../core/services/heartbeat_runtime.py#L3847) |
| function | `_bounded_heartbeat_failure_decision` | `(*, failure_kind, detail, target)` | — | [src](../../../core/services/heartbeat_runtime.py#L3861) |
| function | `_validate_heartbeat_decision` | `(*, decision, policy, workspace_dir, tick_id)` | — | [src](../../../core/services/heartbeat_runtime.py#L3887) |
| function | `_deliver_heartbeat_proposal` | `(*, policy, tick_id, summary, proposed_action)` | — | [src](../../../core/services/heartbeat_runtime.py#L4435) |
| function | `_deliver_heartbeat_ping_directly` | `(*, policy, tick_id, ping_text, summary)` | Deliver an LLM-authored ping straight to webchat. | [src](../../../core/services/heartbeat_runtime.py#L4592) |
| function | `_dispatch_runtime_hook_events_safely` | `(*, event_kinds=…, limit=…)` | — | [src](../../../core/services/heartbeat_runtime.py#L4812) |
| function | `_recover_bounded_heartbeat_liveness_decision` | `(*, decision, policy, liveness)` | — | [src](../../../core/services/heartbeat_runtime.py#L4832) |
| function | `_run_bounded_conflict_resolution` | `(*, decision, context, policy)` | Run conflict resolution using existing runtime signals. | [src](../../../core/services/heartbeat_runtime.py#L4890) |
| function | `_apply_conflict_resolution_to_decision` | `(*, decision, conflict_trace)` | Apply conflict resolution to modify or preserve the decision. | [src](../../../core/services/heartbeat_runtime.py#L4977) |
| function | `_execute_continue_internal` | `(*, conflict_trace, trigger)` | Execute a bounded internal continuation when conflict chose continue_internal. | [src](../../../core/services/heartbeat_runtime.py#L4993) |
| function | `_heartbeat_ping_candidate_ready` | `(*, policy)` | — | [src](../../../core/services/heartbeat_runtime.py#L5048) |
| function | `_execute_heartbeat_internal_action` | `(*, action_type, tick_id, workspace_dir)` | — | [src](../../../core/services/heartbeat_runtime.py#L5069) |
| function | `_summarize_heartbeat_capability_invocations` | `(invocations)` | — | [src](../../../core/services/heartbeat_runtime.py#L6576) |
| function | `_record_heartbeat_outcome` | `(*, policy, persisted, tick_id, trigger, tick_status, decision_type, decision_summary, decision_reason, blocked_reason, currently_ticking, last_trigger_source, provider, model, lane, budget_status, model_source=…, resolution_status=…, fallback_used=…, execution_status=…, parse_status=…, ping_eligible, ping_result, action_status, action_summary, action_type, action_artifact, raw_response, input_tokens, output_tokens, cost_usd, started_at, finished_at, workspace_dir)` | — | [src](../../../core/services/heartbeat_runtime.py#L6616) |
| function | `_merge_runtime_state` | `(*, policy, persisted, now)` | — | [src](../../../core/services/heartbeat_runtime.py#L6794) |
| function | `_tick_blocked_reason` | `(merged_state)` | — | [src](../../../core/services/heartbeat_runtime.py#L6881) |
| function | `_compute_next_tick_at` | `(*, interval_minutes, last_tick_at, enabled)` | — | [src](../../../core/services/heartbeat_runtime.py#L6895) |
| function | `_resolve_tick_activity_state` | `(*, persisted, now)` | — | [src](../../../core/services/heartbeat_runtime.py#L6905) |
| function | `_write_heartbeat_state_artifact` | `(*, workspace_dir, payload)` | — | [src](../../../core/services/heartbeat_runtime.py#L6941) |
| function | `_default_persisted_state` | `()` | — | [src](../../../core/services/heartbeat_runtime.py#L6952) |
| function | `_heartbeat_state_summary` | `(*, enabled, schedule_status, last_decision_type, last_result)` | — | [src](../../../core/services/heartbeat_runtime.py#L6991) |
| function | `_persist_runtime_state` | `(*, policy, persisted, now, overrides)` | — | [src](../../../core/services/heartbeat_runtime.py#L7005) |
| function | `_load_provider_api_key` | `(*, provider, profile)` | — | [src](../../../core/services/heartbeat_runtime.py#L7068) |
| function | `_heartbeat_busy_result` | `(*, name, trigger)` | — | [src](../../../core/services/heartbeat_runtime.py#L7095) |
| function | `_heartbeat_scheduler_loop` | `(*, name, startup_recovery_requested)` | — | [src](../../../core/services/heartbeat_runtime.py#L7145) |
| function | `_detect_startup_drift` | `(*, name, phase, overrides, actual_state)` | Compare intended overrides against what SELECT-back actually returned. | [src](../../../core/services/heartbeat_runtime.py#L7186) |
| function | `_persist_runtime_state_with_diagnostics` | `(*, name, phase, policy, persisted, now, overrides)` | Wrapper around _persist_runtime_state that re-raises with stack trace | [src](../../../core/services/heartbeat_runtime.py#L7250) |
| function | `_prepare_scheduler_startup` | `(*, name)` | — | [src](../../../core/services/heartbeat_runtime.py#L7291) |
| function | `_mark_scheduler_stopped` | `(*, name)` | — | [src](../../../core/services/heartbeat_runtime.py#L7429) |
| function | `_emit_schedule_transitions` | `(state)` | — | [src](../../../core/services/heartbeat_runtime.py#L7454) |
| function | `_heartbeat_runtime_bias_from_recent_work` | `(*, kind)` | — | [src](../../../core/services/heartbeat_runtime.py#L7495) |
| function | `call_heartbeat_llm_simple` | `(prompt, *, max_tokens=…)` | Call the heartbeat model with a plain prompt. Returns the response text. | [src](../../../core/services/heartbeat_runtime.py#L7535) |

## `core/services/heartbeat_runtime_helpers.py`
_Pure leaf helpers extracted from ``heartbeat_runtime``._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_log_debug` | `(message, **fields)` | — | [src](../../../core/services/heartbeat_runtime_helpers.py#L25) |
| function | `_hours_since_iso` | `(value)` | — | [src](../../../core/services/heartbeat_runtime_helpers.py#L33) |
| function | `_detect_visible_language` | `()` | Detect the language Bjørn is currently using in webchat. | [src](../../../core/services/heartbeat_runtime_helpers.py#L47) |
| function | `_classify_heartbeat_execution_exception` | `(exc)` | — | [src](../../../core/services/heartbeat_runtime_helpers.py#L105) |
| function | `_http_error_detail` | `(exc)` | — | [src](../../../core/services/heartbeat_runtime_helpers.py#L114) |
| function | `_parse_heartbeat_key_values` | `(text)` | — | [src](../../../core/services/heartbeat_runtime_helpers.py#L124) |
| function | `_parse_bool` | `(value, *, default, truthy=…)` | — | [src](../../../core/services/heartbeat_runtime_helpers.py#L136) |
| function | `_parse_int` | `(value, *, default, minimum)` | — | [src](../../../core/services/heartbeat_runtime_helpers.py#L154) |
| function | `_extract_json_object` | `(text)` | — | [src](../../../core/services/heartbeat_runtime_helpers.py#L164) |
| function | `_extract_openai_text` | `(data)` | — | [src](../../../core/services/heartbeat_runtime_helpers.py#L192) |
| function | `_extract_openrouter_text` | `(data)` | — | [src](../../../core/services/heartbeat_runtime_helpers.py#L208) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/heartbeat_runtime_helpers.py#L219) |
| function | `_estimate_tokens` | `(text)` | — | [src](../../../core/services/heartbeat_runtime_helpers.py#L228) |
| function | `_value_drifted` | `(expected, actual)` | True if expected ≠ actual under tolerant comparison. | [src](../../../core/services/heartbeat_runtime_helpers.py#L232) |

## `core/services/heartbeat_runtime_influence.py`
_``_build_influence_trace`` extracted from ``heartbeat_runtime`` (Boy-Scout)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_build_influence_trace` | `(*, private_brain, liveness, self_knowledge_summary, embodied_state=…, affective_meta_state=…, epistemic_runtime_state=…, loop_runtime=…, prompt_evolution=…, subagent_ecology=…, council_runtime=…, adaptive_planner=…, adaptive_reasoning=…, dream_influence=…, guided_learning=…, adaptive_learning=…, self_system_code_awareness=…, tool_intent=…)` | Build a bounded trace of what cognitive inputs were available to heartbeat. | [src](../../../core/services/heartbeat_runtime_influence.py#L27) |

## `core/services/heartbeat_runtime_providers.py`
_Concrete heartbeat provider-executor bodies extracted from ``heartbeat_runtime``._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_execute_ollama_prompt` | `(*, prompt, target)` | — | [src](../../../core/services/heartbeat_runtime_providers.py#L23) |
| function | `_execute_openai_prompt` | `(*, prompt, target)` | — | [src](../../../core/services/heartbeat_runtime_providers.py#L66) |
| function | `_execute_openrouter_prompt` | `(*, prompt, target)` | — | [src](../../../core/services/heartbeat_runtime_providers.py#L92) |
| function | `_execute_groq_prompt` | `(*, prompt, target)` | — | [src](../../../core/services/heartbeat_runtime_providers.py#L136) |

## `core/services/hf_connector.py`
_Hugging Face-connector — søg modeller/datasets via Hub API._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_headers` | `()` | — | [src](../../../core/services/hf_connector.py#L43) |
| function | `_get` | `(path, params=…)` | — | [src](../../../core/services/hf_connector.py#L52) |
| function | `search_models` | `(query, *, limit=…)` | — | [src](../../../core/services/hf_connector.py#L67) |
| function | `model_info` | `(model_id)` | — | [src](../../../core/services/hf_connector.py#L85) |

