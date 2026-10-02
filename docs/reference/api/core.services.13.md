# `core.services.13` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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

## `core/services/gate_override.py`
_Per-kald gate-override — Jarvis' eksplicitte, loggede tilsidesættelse af en gate._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `_Armed` | `` | Én armeret one-shot. Forbruges ved første kald der matcher nøglen. | [src](../../../core/services/gate_override.py#L69) |
| function | `_expire_locked` | `(now)` | Fjern udløbne armeringer. Kaldes KUN med ``_LOCK`` taget. Returnerer antal fjernet. | [src](../../../core/services/gate_override.py#L80) |
| function | `_note_key_miss` | `(tool_name, feeling, armed_keys)` | En armering findes for samme værktøj men en ANDEN feeling. | [src](../../../core/services/gate_override.py#L88) |
| function | `arm_override` | `(event_id, reason, *, nerve=…, ttl_seconds=…)` | Armér ÉN one-shot for den hændelse ``event_id`` peger på. | [src](../../../core/services/gate_override.py#L107) |
| function | `consume_override` | `(tool_name, feeling)` | Forbrug en armeret one-shot for (tool_name, feeling). | [src](../../../core/services/gate_override.py#L202) |
| function | `_notify_owner` | `(tool_name, feeling, reason, event_id)` | Fortæl Bjørn at en gate blev overstyret. Kører i en daemon-tråd — en HTTP-request | [src](../../../core/services/gate_override.py#L260) |
| function | `override_state` | `()` | Observabilitet: hvad er armeret lige nu, og hvad er udløbet? Read-only, kaster aldrig. | [src](../../../core/services/gate_override.py#L280) |
| function | `_reset_for_tests` | `()` | Ryd al armeret tilstand. Kun til tests — den rigtige reset er en genstart. | [src](../../../core/services/gate_override.py#L307) |

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
| function | `POST_OUTPUT_GATES_CLUSTERS` | `()` | (nerve, cluster) i kald-rækkefølge — til test/introspektion. | [src](../../../core/services/gate_shadow.py#L98) |
| function | `_shadow_enabled` | `()` | True medmindre gate_kernel.shadow er EKSPLICIT slået fra. Fail-open til ON | [src](../../../core/services/gate_shadow.py#L103) |
| function | `_resolve` | `(mod_path, fn_attr)` | — | [src](../../../core/services/gate_shadow.py#L113) |
| function | `run_post_output_shadow` | `(ctx)` | Kør de 5 sovende gates i SKYGGE via central().decide. | [src](../../../core/services/gate_shadow.py#L118) |

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
_Ghost Networks — spor af mønstre der holdt op med at være aktive._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kernen` | `(navn)` | Skaer kildens praefiks fra: «Private inner note: X» -> «X». | [src](../../../core/services/ghost_networks.py#L70) |
| function | `_load` | `()` | — | [src](../../../core/services/ghost_networks.py#L82) |
| function | `_save` | `(spoegelser)` | — | [src](../../../core/services/ghost_networks.py#L92) |
| function | `_henfald` | `(doede_ved)` | Alderen som henfald. Var 0.0 og blev aldrig opdateret. | [src](../../../core/services/ghost_networks.py#L96) |
| function | `archive_dead_nodes` | `(node_ids, slags=…, doede_ved=…)` | Arkiver doede moenstre. Giver antallet der var nye. | [src](../../../core/services/ghost_networks.py#L106) |
| function | `_med_henfald` | `()` | Spoegelserne med deres AKTUELLE henfald — beregnet, ikke gemt. | [src](../../../core/services/ghost_networks.py#L129) |
| function | `tick` | `(_seconds=…)` | Hjerteslags-krog: saml de moenstre der er doet siden sidst. | [src](../../../core/services/ghost_networks.py#L135) |
| function | `describe_ghost_network` | `()` | Det MINDST falmede spoegelse — ikke det aeldste. | [src](../../../core/services/ghost_networks.py#L162) |
| function | `format_ghost_for_prompt` | `()` | — | [src](../../../core/services/ghost_networks.py#L175) |
| function | `reset_ghost_networks` | `()` | — | [src](../../../core/services/ghost_networks.py#L180) |
| function | `build_ghost_networks_surface` | `()` | — | [src](../../../core/services/ghost_networks.py#L184) |

## `core/services/git_actions.py`
_Rolle-aware git-eksekvering for code mode._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_git_container` | `(repo, *a, timeout=…)` | — | [src](../../../core/services/git_actions.py#L24) |
| function | `_human_attribution` | `()` | — | [src](../../../core/services/git_actions.py#L28) |
| function | `_commit_container` | `(repo, message)` | — | [src](../../../core/services/git_actions.py#L39) |
| function | `commit_all_container` | `(repo, message)` | — | [src](../../../core/services/git_actions.py#L47) |
| function | `_operator_exec` | `(name, args)` | — | [src](../../../core/services/git_actions.py#L65) |
| function | `_ws_git` | `(root, uid, gitargs, timeout=…)` | Kør `git -C <root> <gitargs>` på brugerens bro. Returnér (rc, stdout, stderr). | [src](../../../core/services/git_actions.py#L70) |
| function | `_ws_attributed_commit` | `(root, uid, message, *, timeout=…)` | — | [src](../../../core/services/git_actions.py#L80) |
| function | `commit_all_workstation` | `(root, uid, message)` | — | [src](../../../core/services/git_actions.py#L110) |
| function | `commit_all` | `(target, container_repo, uid, message)` | — | [src](../../../core/services/git_actions.py#L128) |
| function | `parse_owner_repo` | `(remote_url)` | — | [src](../../../core/services/git_actions.py#L140) |
| function | `_ws_git_raw` | `(root, uid, cmd, timeout=…)` | Kør vilkårlig kommando i `root` på brugerens bro (til gh). | [src](../../../core/services/git_actions.py#L151) |
| function | `create_pr` | `(target, container_repo, uid, title, body)` | Commit → branch hvis på default → push → PR (API, ellers gh-fallback). | [src](../../../core/services/git_actions.py#L161) |
| function | `_create_pr_gh` | `(ws, root, uid, base, branch, title, body)` | — | [src](../../../core/services/git_actions.py#L201) |
| function | `_split_gh` | `(args)` | — | [src](../../../core/services/git_actions.py#L215) |

## `core/services/git_workspace_actions.py`
_Git-handlinger for code-mode's workspace-vaelgere._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_koer_lokalt` | `(root, args)` | — | [src](../../../core/services/git_workspace_actions.py#L34) |
| function | `_koer_over_bro` | `(root, args, uid)` | — | [src](../../../core/services/git_workspace_actions.py#L52) |
| function | `_koer` | `(kind, root, args, uid)` | Koer git og faa ét output pr. argument-liste. False = kunne ikke. | [src](../../../core/services/git_workspace_actions.py#L72) |
| function | `_rens` | `(navne)` | Git-linjer → rene navne. Fjerner markoerer, HEAD-pilen og dubletter. | [src](../../../core/services/git_workspace_actions.py#L81) |
| function | `list_branches` | `(*, kind, root, uid=…)` | Alle branches plus den aktuelle. Tomt resultat = ikke et repo. | [src](../../../core/services/git_workspace_actions.py#L94) |
| function | `checkout_branch` | `(*, kind, root, navn, opret=…, uid=…)` | Skift til en branch, eller opret og skift til en ny. | [src](../../../core/services/git_workspace_actions.py#L122) |
| function | `create_worktree` | `(*, kind, root, navn, sti=…, uid=…)` | Opret en ny lokal worktree med sin egen branch. | [src](../../../core/services/git_workspace_actions.py#L150) |

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

## `core/services/goal_reporter.py`
_Goal reporter — fører systemets egne målinger tilbage til målet der bad om dem._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_criterion_fulfilment` | `(measured, target)` | Hvor stor en del af kriteriet er opfyldt — kappet ved 1.0. | [src](../../../core/services/goal_reporter.py#L33) |
| function | `_find_goal` | `(*, title_fragment)` | Slå det aktive mål op hvis titel indeholder fragmentet. | [src](../../../core/services/goal_reporter.py#L48) |
| function | `collect_metrics` | `(*, days=…)` | Læs de tre tal. Fejler aldrig hårdt — et manglende tal bliver None. | [src](../../../core/services/goal_reporter.py#L58) |
| function | `compute_progress` | `(*, tick_score, heed_rate)` | progress_pct + de enkelte kriterier. Svageste led bestemmer. | [src](../../../core/services/goal_reporter.py#L95) |
| function | `_format_note` | `(metrics, progress)` | Én kort note til update-loggen — tallene, ikke fortællingen om dem. | [src](../../../core/services/goal_reporter.py#L132) |
| function | `report_goal_metrics` | `(*, days=…, dry_run=…, goal_title_fragment=…)` | Mål, skriv til målet, returnér hvad der skete. Aldrig stille. | [src](../../../core/services/goal_reporter.py#L155) |

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
| function | `_domain_key_from_critic` | `(canonical_key)` | — | [src](../../../core/services/goal_signal_tracking.py#L463) |
| function | `_domain_key_from_self_model` | `(canonical_key)` | — | [src](../../../core/services/goal_signal_tracking.py#L472) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/goal_signal_tracking.py#L481) |
| function | `_message_domain_key` | `(text)` | — | [src](../../../core/services/goal_signal_tracking.py#L485) |
| function | `_goal_title` | `(domain_key, fallback)` | — | [src](../../../core/services/goal_signal_tracking.py#L494) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/goal_signal_tracking.py#L502) |
| function | `_rank` | `(value)` | — | [src](../../../core/services/goal_signal_tracking.py#L511) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/goal_signal_tracking.py#L515) |

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
| function | `_resolve_role` | `(user_id)` | Find brugerens faktiske rolle (SQLite-user_db → ellers users.json → member). | [src](../../../core/services/google_login.py#L28) |
| function | `_gc` | `(now)` | — | [src](../../../core/services/google_login.py#L47) |
| function | `begin_login` | `(app_id=…, *, now=…)` | Start et login. Returnerer (nonce, state_uid) — state_uid lægges i OAuth-state. | [src](../../../core/services/google_login.py#L52) |
| function | `begin_link` | `(user_id, *, now=…)` | Start en Google-linking for en EKSISTERENDE (indlogget) bruger. | [src](../../../core/services/google_login.py#L61) |
| function | `is_login_state` | `(state_uid)` | — | [src](../../../core/services/google_login.py#L70) |
| function | `complete` | `(state_uid, google_email, *, now=…)` | Kaldt af callbacken med den VERIFICEREDE Google-email. Returnerer en kort | [src](../../../core/services/google_login.py#L74) |
| function | `take_result` | `(nonce, *, now=…)` | Engangs-hent af login-resultatet (fjernes ved hentning når det er færdigt). | [src](../../../core/services/google_login.py#L118) |

## `core/services/governance_bootstrap.py`
_Governance bootstrap — idempotent setup of default windows, jobs handlers, automations._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_default_windows` | `()` | Ensure default scheduled job windows exist. Returns list of window_ids | [src](../../../core/services/governance_bootstrap.py#L15) |
| function | `ensure_default_job_handlers` | `()` | Register default job-type handlers. Returns list of job_type names registered. | [src](../../../core/services/governance_bootstrap.py#L73) |
| function | `ensure_default_automations` | `()` | Seed a couple of baseline automations so the DSL surface has examples. | [src](../../../core/services/governance_bootstrap.py#L290) |
| function | `ensure_warmup_job` | `()` | Enqueue a single low-priority warmup job on first boot so the | [src](../../../core/services/governance_bootstrap.py#L354) |
| function | `bootstrap_all` | `()` | Run all idempotent bootstrap helpers. Safe at any startup. | [src](../../../core/services/governance_bootstrap.py#L379) |

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

## `core/services/grounded_capability_followup.py`
_Grounded capability follow-up — det andet pas efter en udført evne._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_visible_runs` | `()` | Doven import. På modulniveau ville det være en cyklus — visible_runs | [src](../../../core/services/grounded_capability_followup.py#L30) |
| function | `_run_grounded_capability_followup` | `(run, *, capability_id, invocation, initial_model_text)` | — | [src](../../../core/services/grounded_capability_followup.py#L36) |
| function | `_build_grounded_capability_followup_message` | `(run, *, capability_id, invocation, initial_model_text)` | — | [src](../../../core/services/grounded_capability_followup.py#L71) |
| function | `_run_grounded_multi_capability_followup` | `(run, *, capability_results, initial_model_text)` | — | [src](../../../core/services/grounded_capability_followup.py#L113) |
| function | `_build_grounded_multi_capability_followup_message` | `(run, *, capability_results, initial_model_text)` | — | [src](../../../core/services/grounded_capability_followup.py#L146) |
| function | `_is_code_analysis_request` | `(user_message)` | — | [src](../../../core/services/grounded_capability_followup.py#L191) |
| function | `_is_memory_commit_request` | `(user_message)` | — | [src](../../../core/services/grounded_capability_followup.py#L210) |

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
| function | `_now_iso` | `()` | — | [src](../../../core/services/habits_pipeline.py#L54) |
| function | `_ensure_tables` | `()` | Tables exist from v2 db.py — this is idempotent no-op unless schema changes. | [src](../../../core/services/habits_pipeline.py#L58) |
| function | `_normalize_signature` | `(message)` | — | [src](../../../core/services/habits_pipeline.py#L111) |
| function | `_upsert_habit` | `(pattern_key, now)` | — | [src](../../../core/services/habits_pipeline.py#L125) |
| function | `_upsert_friction` | `(task_signature, now)` | — | [src](../../../core/services/habits_pipeline.py#L156) |
| function | `_maybe_create_suggestion` | `(*, source_type, source_id, suggestion_text, confidence, now)` | — | [src](../../../core/services/habits_pipeline.py#L187) |
| function | `record_habit_signal` | `(*, message)` | Main entry: record a habit signal from a chat message. | [src](../../../core/services/habits_pipeline.py#L219) |
| function | `list_habits` | `(*, limit=…)` | — | [src](../../../core/services/habits_pipeline.py#L306) |
| function | `list_friction` | `(*, limit=…)` | — | [src](../../../core/services/habits_pipeline.py#L318) |
| function | `list_suggestions` | `(*, status=…, limit=…)` | — | [src](../../../core/services/habits_pipeline.py#L330) |
| function | `format_pending_suggestions_for_heartbeat` | `(*, max_items=…)` | Kompakt linje af de øverste ventende automations-forslag til heartbeat. | [src](../../../core/services/habits_pipeline.py#L343) |
| function | `cleanup_polluted_suggestions` | `(*, older_than_days=…)` | Luk alle ``pending`` forslag ældre end ``older_than_days`` dage. | [src](../../../core/services/habits_pipeline.py#L384) |
| function | `accept_suggestion` | `(*, suggestion_id)` | — | [src](../../../core/services/habits_pipeline.py#L413) |
| function | `reject_suggestion` | `(*, suggestion_id)` | — | [src](../../../core/services/habits_pipeline.py#L440) |
| function | `build_habits_pipeline_surface` | `()` | — | [src](../../../core/services/habits_pipeline.py#L459) |

## `core/services/hallucination_guard.py`
_Hallucination Guard — forced memory-check before answering._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_word_present` | `(word, text_lower)` | Word-boundary check: True if `word` appears as a standalone token (with optional plural). | [src](../../../core/services/hallucination_guard.py#L110) |
| function | `_section_keywords_for_message` | `(message)` | Derive keywords from the message so we can find the right MEMORY section. | [src](../../../core/services/hallucination_guard.py#L126) |
| function | `classify_question` | `(message)` | Classify the message: 'factual' | 'casual' | 'tool_call'. | [src](../../../core/services/hallucination_guard.py#L140) |
| function | `_ws_has_content` | `(path)` | Eksistens-tjek encryption-aware: plaintext eller member .enc. | [src](../../../core/services/hallucination_guard.py#L170) |
| function | `_find_memory_path` | `()` | Find MEMORY.md — look in runtime workspace first, then repo. | [src](../../../core/services/hallucination_guard.py#L178) |
| function | `_find_curated_paths` | `()` | Locate all curated workspace files for hallucination-guard recall. | [src](../../../core/services/hallucination_guard.py#L207) |
| function | `_extract_relevant_sections` | `(memory_text, keywords, max_chars=…)` | Find MEMORY.md-sektioner der matcher keywords, returnér som tekst. | [src](../../../core/services/hallucination_guard.py#L241) |
| function | `_observe_guard_decision` | `(*, activated, reason)` | Egress-frit Central-observe af hallucination-guardens beslutning (§7.2). | [src](../../../core/services/hallucination_guard.py#L325) |
| function | `inject_memory_into_prompt` | `(message, chat_messages, *, memory_path=…)` | Inject relevant memory as a system-role message into the prompt. | [src](../../../core/services/hallucination_guard.py#L349) |

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

## `core/services/heartbeat_action_hints.py`
_Hvornår er en indre-livs-handling det rigtige valg? Vink til heartbeat-beslutningen._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/heartbeat_action_hints.py#L34) |
| function | `chronicle_days_stale` | `()` | Døgn siden seneste kronik-post. ``None`` hvis ukendt. Self-safe. | [src](../../../core/services/heartbeat_action_hints.py#L45) |
| function | `chronicle_period_covered` | `()` | True når seneste kronik-post allerede dækker indeværende ISO-uge. | [src](../../../core/services/heartbeat_action_hints.py#L61) |
| function | `chronicle_hint` | `()` | Vink om at skrive kronik — kun når handlingen FAKTISK ville skrive noget. | [src](../../../core/services/heartbeat_action_hints.py#L83) |
| function | `inner_life_hints` | `()` | Alle aktive vink for indre-livs-handlinger. Tom liste når intet er forfaldent. | [src](../../../core/services/heartbeat_action_hints.py#L111) |

## `core/services/heartbeat_daemon_ticks.py`
_Jarvis' indre daemoner — ét tik, uanset om han har travlt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_forloebet_sekunder` | `()` | Sekunder siden forrige tik — maalt, ikke antaget. | [src](../../../core/services/heartbeat_daemon_ticks.py#L66) |
| function | `tik_indre_daemoner` | `()` | Tik alle indre daemoner én gang. Kaster aldrig. | [src](../../../core/services/heartbeat_daemon_ticks.py#L100) |
| function | `_tik_for_bruger` | `(arbejdsrum, bruger_id)` | Tik de arbejdsrums-bundne daemoner for ÉN bruger. | [src](../../../core/services/heartbeat_daemon_ticks.py#L410) |

## `core/services/heartbeat_delivery.py`
_Heartbeat-levering: de to veje et hjerteslag naar webchatten ad._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_recent_ping_history` | `(*, limit=…)` | Slaa op i `heartbeat_runtime` ved kaldetid — en modul-import ville vaere | [src](../../../core/services/heartbeat_delivery.py#L39) |
| function | `_deliver_heartbeat_proposal` | `(*, policy, tick_id, summary, proposed_action)` | — | [src](../../../core/services/heartbeat_delivery.py#L54) |
| function | `_deliver_heartbeat_ping_directly` | `(*, policy, tick_id, ping_text, summary)` | Deliver an LLM-authored ping straight to webchat. | [src](../../../core/services/heartbeat_delivery.py#L238) |

## `core/services/heartbeat_manage_runtime_work.py`
_Hjerteslagets `manage_runtime_work`-handling — udskilt fra heartbeat_runtime._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `execute_manage_runtime_work` | `(*, tick_id, workspace_dir)` | — | [src](../../../core/services/heartbeat_manage_runtime_work.py#L18) |

## `core/services/heartbeat_phases.py`
_Heartbeat phases — explicit Sense / Reflect / Act structure on top of existing tick._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_user_active_recently` | `(*, window_minutes=…)` | Cheap check: has any user-role chat message landed in the last N minutes? | [src](../../../core/services/heartbeat_phases.py#L40) |
| function | `_inner_tick_during_chat_enabled` | `()` | Skal de indre daemoner køre mens brugeren aktivt chatter (hans sind vågent mens I | [src](../../../core/services/heartbeat_phases.py#L65) |
| function | `sense_phase` | `(*, name=…)` | Gather signals for this tick. Pure-read — no side effects. | [src](../../../core/services/heartbeat_phases.py#L80) |
| function | `_classify_activity` | `(signals)` | Classify current activity level from signals. | [src](../../../core/services/heartbeat_phases.py#L165) |
| function | `_identify_priorities` | `(signals)` | Heuristic — what should this tick attend to? | [src](../../../core/services/heartbeat_phases.py#L175) |
| function | `reflect_phase` | `(signals)` | Synthesize reflection. Heuristic-only by default; LLM optional. | [src](../../../core/services/heartbeat_phases.py#L191) |
| function | `_collect_active_goals` | `()` | Fetch active goals for chain proposal targeting. | [src](../../../core/services/heartbeat_phases.py#L251) |
| function | `_propose_skill_chains_in_idle` | `(max_goals=…)` | Propose skill chains for active goals. Time-bounded, never blocks. | [src](../../../core/services/heartbeat_phases.py#L260) |
| function | `format_chain_proposals` | `(max_chars=…)` | Format recent chain proposals for awareness injection. | [src](../../../core/services/heartbeat_phases.py#L307) |
| function | `clear_chain_proposals` | `()` | Clear cached chain proposals (e.g. after execution or user dismiss). | [src](../../../core/services/heartbeat_phases.py#L330) |
| function | `get_chain_proposals` | `()` | Return current chain proposals for inspection. | [src](../../../core/services/heartbeat_phases.py#L335) |
| function | `productive_idle` | `(*, budget_seconds=…)` | Run light maintenance work when there's no clear action. Time-bounded. | [src](../../../core/services/heartbeat_phases.py#L340) |
| function | `act_phase` | `(*, signals, reflection, name=…, trigger=…)` | Either run normal heartbeat tick OR productive idle, based on reflection. | [src](../../../core/services/heartbeat_phases.py#L625) |
| function | `tick_with_phases` | `(*, name=…, trigger=…)` | Run all 3 phases in sequence, return structured result. | [src](../../../core/services/heartbeat_phases.py#L713) |
| function | `_exec_phased_tick` | `(args)` | — | [src](../../../core/services/heartbeat_phases.py#L789) |
| function | `_exec_sense_only` | `(args)` | Read-only: gather current signals without running reflection or action. | [src](../../../core/services/heartbeat_phases.py#L796) |

## `core/services/heartbeat_provider_fallback.py`
_Heartbeat provider fallback — cheap cloud lane when primary (Groq) fails._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `execute_openai_compat_heartbeat_prompt` | `(*, prompt, target, max_tokens=…, temperature=…)` | Call an OpenAI-chat/completions-compatible provider for heartbeat. | [src](../../../core/services/heartbeat_provider_fallback.py#L53) |
| function | `try_heartbeat_cheap_fallback` | `(prompt)` | Try cheap lane providers (skip groq + ollamafreeapi) as heartbeat fallback. | [src](../../../core/services/heartbeat_provider_fallback.py#L167) |

