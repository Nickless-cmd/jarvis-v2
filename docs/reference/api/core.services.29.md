# `core.services.29` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/tool_router.py`
_Per-turn tool selection._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ToolSelection` | `` | — | [src](../../../core/services/tool_router.py#L42) |
| function | `_clarity_signal` | `(msg)` | Hvor sandsynligt er det at turen har brug for et vaerktoej? | [src](../../../core/services/tool_router.py#L64) |
| function | `_score` | `(user_message, *, top_sim, load_more_rate_7d)` | — | [src](../../../core/services/tool_router.py#L113) |
| function | `_all_tool_names` | `()` | — | [src](../../../core/services/tool_router.py#L120) |
| function | `_always_core_set` | `(limit)` | Top-N tools by 7-day call count ∪ pinned set, with fallback. | [src](../../../core/services/tool_router.py#L128) |
| function | `kald_pr_bruger` | `(dage=…)` | Hvilke vaerktoejer kalder hver bruger — grundlaget kernen mangler. | [src](../../../core/services/tool_router.py#L166) |
| function | `_load_more_rate_7d` | `()` | — | [src](../../../core/services/tool_router.py#L199) |
| function | `_confidence_buckets` | `(values, n_buckets=…)` | — | [src](../../../core/services/tool_router.py#L217) |
| function | `_count_missed_tools` | `(rows)` | — | [src](../../../core/services/tool_router.py#L225) |
| function | `build_tool_router_surface` | `()` | Mission Control surface for tool router state. | [src](../../../core/services/tool_router.py#L241) |
| function | `select_tools` | `(*, user_message, session_id, lane, run_id=…)` | Select a subset of tools for this turn. Always returns a ToolSelection. | [src](../../../core/services/tool_router.py#L345) |
| function | `_sprog_bro_taendt` | `()` | Live-kontakt for sprog-broen. Self-safe: kan config ikke laeses, er den TIL. | [src](../../../core/services/tool_router.py#L385) |
| function | `_embedding_query` | `(user_message)` | Forespoergslen der embeddes — dansk broet til engelsk. | [src](../../../core/services/tool_router.py#L394) |
| function | `_select_inner` | `(*, user_message, session_id, lane, run_id, settings, started_at)` | — | [src](../../../core/services/tool_router.py#L425) |
| function | `_persist` | `(sel, user_message, session_id, lane, run_id)` | — | [src](../../../core/services/tool_router.py#L493) |

## `core/services/tool_router_runtime.py`
_Nightly daemon: refresh always-core ranking, recompute embeddings,_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_adjust_threshold` | `(*, current, load_more_rate_7d)` | — | [src](../../../core/services/tool_router_runtime.py#L19) |
| function | `_read_load_more_rate` | `()` | — | [src](../../../core/services/tool_router_runtime.py#L29) |
| function | `run_once` | `()` | Single daemon iteration. Safe to call manually for testing. | [src](../../../core/services/tool_router_runtime.py#L34) |
| function | `_loop` | `()` | — | [src](../../../core/services/tool_router_runtime.py#L64) |
| function | `start_tool_router_runtime` | `()` | — | [src](../../../core/services/tool_router_runtime.py#L73) |
| function | `stop_tool_router_runtime` | `()` | — | [src](../../../core/services/tool_router_runtime.py#L85) |
| function | `build_tool_router_runtime_surface` | `()` | Mission Control-surface: koerer router-daemonen, og hvad sagde dens sidste kørsel? | [src](../../../core/services/tool_router_runtime.py#L89) |

## `core/services/tool_tagger.py`
_Tool tag taxonomy._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_json` | `(p)` | — | [src](../../../core/services/tool_tagger.py#L39) |
| function | `_ensure_loaded` | `()` | — | [src](../../../core/services/tool_tagger.py#L49) |
| function | `get_tags` | `(tool_name)` | Return tags for `tool_name`. Overrides win over auto. Empty if unknown. | [src](../../../core/services/tool_tagger.py#L65) |
| function | `get_pinned_set` | `()` | — | [src](../../../core/services/tool_tagger.py#L75) |
| function | `invalidate_cache` | `()` | — | [src](../../../core/services/tool_tagger.py#L80) |
| function | `bootstrap_tags` | `(*, dry_run=…)` | Use cheap-lane LLM to generate domain tags for every registered tool. | [src](../../../core/services/tool_tagger.py#L85) |
| function | `build_tool_tagger_surface` | `()` | Mission Control-surface: hvor mange vaerktoejer er tagget, overstyret og pinnet? | [src](../../../core/services/tool_tagger.py#L149) |

## `core/services/tool_usage_store.py`
_Tools-cluster Phase 2 — persistent forbrugs-statistik (DB-backed, cross-proces)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure` | `(conn)` | — | [src](../../../core/services/tool_usage_store.py#L29) |
| function | `record_use` | `(tool, *, kind=…, ok=…)` | UPSERT-increment forbrugs-tæller for ét tool-kald. Best-effort, hot-path-sikker. | [src](../../../core/services/tool_usage_store.py#L41) |
| function | `usage_stats` | `()` | {tool: {count, errors, kind, last_used}} for alle tools der ER blevet kaldt. | [src](../../../core/services/tool_usage_store.py#L67) |
| function | `_bucket_for` | `(count)` | — | [src](../../../core/services/tool_usage_store.py#L85) |
| function | `usage_buckets` | `(registered=…)` | Klassificér tools i most/often/sometimes/rare/never. Hvis `registered` gives, indgår | [src](../../../core/services/tool_usage_store.py#L92) |
| function | `tool_order` | `(registered)` | Ordn registrerede tools efter forbrug: mest-brugte FØRST, aldrig-brugte SIDST. | [src](../../../core/services/tool_usage_store.py#L106) |
| function | `dead_tools` | `(registered)` | Registrerede tools der ALDRIG er kaldt (count 0). Vises sidst / kandidater til at | [src](../../../core/services/tool_usage_store.py#L116) |
| function | `observe_stats` | `(registered=…)` | Periodisk (cadence): central.observe forbrugs-summary + flag antal døde tools. | [src](../../../core/services/tool_usage_store.py#L123) |
| function | `build_tool_usage_store_surface` | `()` | Mission Control-surface: hvad er der faktisk talt i `tool_usage`? | [src](../../../core/services/tool_usage_store.py#L147) |

## `core/services/tool_world_change.py`
_Ændrede dette værktøjskald verden? (loop-fix 2026-09-05)_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_shell_command` | `(arguments)` | — | [src](../../../core/services/tool_world_change.py#L37) |
| function | `_mutation_tool_names` | `()` | Navne fra verification_gate — ét sted at vedligeholde listen. | [src](../../../core/services/tool_world_change.py#L45) |
| function | `call_changed_the_world` | `(*, tool_name, arguments=…, status=…)` | True når kaldet reelt ændrede state (og lykkedes). | [src](../../../core/services/tool_world_change.py#L54) |
| function | `round_changed_the_world` | `(results)` | Ændrede mindst ét kald i denne agentiske runde verden? | [src](../../../core/services/tool_world_change.py#L83) |

## `core/services/totp_verifier.py`
_TOTP-verifikation (RFC 6238) til owner-override — ren stdlib, ingen dependency._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_b32_decode` | `(seed)` | Dekodér base32-seed; tilføj padding + uppercase. Tom/ugyldig → b''. | [src](../../../core/services/totp_verifier.py#L31) |
| function | `_hotp` | `(key, counter)` | RFC 4226 HOTP — HMAC-SHA1 + dynamic truncation → _DIGITS cifre. | [src](../../../core/services/totp_verifier.py#L43) |
| function | `generate_code` | `(seed, *, timestamp=…)` | 6-cifret TOTP for `seed` på `timestamp` (default: nu). | [src](../../../core/services/totp_verifier.py#L52) |
| function | `verify` | `(code, *, seed, now=…, valid_window=…)` | True hvis `code` matcher TOTP for `seed` inden for ±valid_window vinduer. | [src](../../../core/services/totp_verifier.py#L62) |
| function | `generate_seed` | `()` | Ny tilfældig 16-byte base32-nøgle (uden padding) til QR-setup. | [src](../../../core/services/totp_verifier.py#L88) |
| function | `provisioning_uri` | `(seed, *, account, issuer=…)` | Byg en otpauth://-URI som authenticator-apps (Google Authenticator, Authy, | [src](../../../core/services/totp_verifier.py#L94) |
| function | `revoke` | `(_old_seed=…)` | Returnér en ny seed. Caller (owner-session) persisterer den + smider den gamle. | [src](../../../core/services/totp_verifier.py#L106) |
| function | `record_attempt` | `(session_id, *, now=…)` | Registrér et override-forsøg. True hvis tilladt, False hvis rate-limited. | [src](../../../core/services/totp_verifier.py#L120) |

## `core/services/truth_gate_v2.py`
_Evidens-baseret TruthGate v2 (Fase 2). Detekterer handlings-påstande og verificerer_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ActionClaim` | `` | — | [src](../../../core/services/truth_gate_v2.py#L35) |
| function | `_er_mellemmenneskeligt` | `(text, m)` | Peger paastanden paa en person eller paa noget der er SAGT? | [src](../../../core/services/truth_gate_v2.py#L74) |
| function | `detect_action_claims` | `(text)` | Deterministisk: find handlings-påstande. commit_hash tæller kun i commit/git/log- | [src](../../../core/services/truth_gate_v2.py#L85) |
| function | `_er_hash_vi_selv_har_vist` | `(hash_i_tekst)` | Er det den commit-hash env-blokken selv skrev ind i hans prompt? | [src](../../../core/services/truth_gate_v2.py#L128) |
| function | `_run_result_text` | `(followup_exchanges)` | — | [src](../../../core/services/truth_gate_v2.py#L165) |
| function | `verify_claim` | `(claim, executed_tool_names, followup_exchanges)` | In-run evidens: kørte et tool i kategorien? + (for citeret output/hash) matcher | [src](../../../core/services/truth_gate_v2.py#L173) |
| function | `classify_severity` | `(claims)` | — | [src](../../../core/services/truth_gate_v2.py#L218) |
| function | `_footnote_for` | `(claim)` | Byg én fodnote-linje for et uverificeret claim i den konsistente stil. | [src](../../../core/services/truth_gate_v2.py#L222) |
| function | `_annotate` | `(text, claims)` | Bevar teksten + append fodnote(r) i bunden (én pr. claim, adskilt fra | [src](../../../core/services/truth_gate_v2.py#L232) |
| function | `_annotate_soft` | `(text, claims=…)` | Bagudkompatibel: bløde påstande → fodnote. (claims valgfri; uden dem | [src](../../../core/services/truth_gate_v2.py#L241) |
| function | `_llm_judge` | `(text)` | Spørg billig lane om teksten påstår en handling der kræver tool-evidens. | [src](../../../core/services/truth_gate_v2.py#L256) |
| function | `_maybe_llm_claim` | `(text)` | LLM-dommer KUN hvis teksten har et handlings-hint men intet deterministisk match. | [src](../../../core/services/truth_gate_v2.py#L279) |
| function | `truth_gate_v2` | `(ctx)` | ctx: {text, executed_tool_names, followup_exchanges, run_id, session_id}. | [src](../../../core/services/truth_gate_v2.py#L293) |

## `core/services/turens_vaerktoejer.py`
_Ét værktøjssæt for HELE turen — begge trin ser det samme._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_navn` | `(d)` | — | [src](../../../core/services/turens_vaerktoejer.py#L41) |
| function | `vaerktoejer_for_turen` | `(alle, *, user_message, session_id)` | Værktøjerne for DENNE tur — samme sæt i begge trin. | [src](../../../core/services/turens_vaerktoejer.py#L45) |

## `core/services/turn_changelog.py`
_End-of-turn changelog — auto-summarize what this turn changed._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_tool_calls_during` | `(run_id, started_at)` | — | [src](../../../core/services/turn_changelog.py#L27) |
| function | `_git_changed_files` | `(repo)` | — | [src](../../../core/services/turn_changelog.py#L50) |
| function | `build_turn_changelog` | `(*, run_id=…, started_at=…, repo_root=…)` | — | [src](../../../core/services/turn_changelog.py#L67) |
| function | `previous_turn_changelog_section` | `(session_id)` | Look at the most recent visible run for this session and surface the | [src](../../../core/services/turn_changelog.py#L80) |
| function | `format_changelog` | `(changelog)` | Render a compact human-readable summary, or None if empty. | [src](../../../core/services/turn_changelog.py#L129) |

## `core/services/turn_tail_timing.py`
_Hvor bliver sekunderne af EFTER svaret er skrevet færdigt?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `start` | `(run_id)` | — | [src](../../../core/services/turn_tail_timing.py#L42) |
| function | `mark` | `(run_id, navn)` | Notér at ét led er færdigt. Gratis hvis `start` aldrig blev kaldt. | [src](../../../core/services/turn_tail_timing.py#L57) |
| function | `slut` | `(run_id)` | Afslut målingen. Returnerer halens længde i sekunder (0 hvis ukendt). | [src](../../../core/services/turn_tail_timing.py#L67) |
| function | `_nulstil_for_tests` | `()` | — | [src](../../../core/services/turn_tail_timing.py#L87) |

## `core/services/turn_trace.py`
_core/services/turn_trace.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_sentinel` | `()` | — | [src](../../../core/services/turn_trace.py#L29) |
| function | `active` | `()` | — | [src](../../../core/services/turn_trace.py#L36) |
| function | `start` | `(label=…)` | Nulstil tidslinjen ved request-in. No-op uden sentinel. | [src](../../../core/services/turn_trace.py#L40) |
| function | `mark` | `(kind, label=…, dur_ms=…)` | Tilføj ét event + print en LIVE-linje til stderr (så ruten kan følges i | [src](../../../core/services/turn_trace.py#L58) |
| function | `dump` | `(reason=…)` | Skriv hele tidslinjen til latest.json + kompakt stderr-resumé, og sluk. | [src](../../../core/services/turn_trace.py#L79) |

## `core/services/ui_panel_store.py`
_Pending UI-panel-kald (spec §8.2, Fase 6 #3, opdateret 2026-06-16 med scope)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `request_panel` | `(panel, *, detail=…, scope=…, session_id=…, action=…)` | Tilføj en pending panel-forespørgsel. | [src](../../../core/services/ui_panel_store.py#L32) |
| function | `list_pending` | `(*, session_id=…)` | Returnér alle pending requests (status='pending'), valgfrit filtreret på session. | [src](../../../core/services/ui_panel_store.py#L73) |
| function | `ack_panel` | `(request_id)` | Markér en request som 'opened' (desk-appen har åbnet panelet). | [src](../../../core/services/ui_panel_store.py#L83) |
| function | `get_request_status` | `(request_id)` | Nuværende status ('pending'/'opened') for en request, eller None hvis ukendt. | [src](../../../core/services/ui_panel_store.py#L94) |
| function | `_load` | `()` | — | [src](../../../core/services/ui_panel_store.py#L103) |
| function | `_save` | `(state)` | — | [src](../../../core/services/ui_panel_store.py#L114) |

## `core/services/unconscious_modulation.py`
_Unconscious modulation — sub-symbolic sampling-parameter shift._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_modulation_enabled` | `()` | Kill-switch check. True = modulate; False = pass base through. | [src](../../../core/services/unconscious_modulation.py#L32) |
| function | `compute_unconscious_modulation` | `(*, base_temperature, base_top_p, workspace_id=…)` | Return (modulated_temperature, modulated_top_p). | [src](../../../core/services/unconscious_modulation.py#L40) |

## `core/services/unconscious_temperature_field.py`
_Unconscious temperature field — backwards-compat wrapper for Lag 10._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_unconscious_temperature_hint` | `()` | Backwards-compat: returns heartbeat-formatted hint string or None. | [src](../../../core/services/unconscious_temperature_field.py#L15) |
| function | `build_unconscious_temperature_field_surface` | `(*, force_refresh=…)` | Backwards-compat: surface dict for Mission Control consumers. | [src](../../../core/services/unconscious_temperature_field.py#L30) |

## `core/services/unfinished_intent.py`
_Unfinished-intent detector for visible-run output._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `UnfinishedIntent` | `` | Resultat af detector: hvilken pattern matched. | [src](../../../core/services/unfinished_intent.py#L30) |
| function | `_tail` | `(text, n=…)` | Returner sidste ~n tegn af teksten. | [src](../../../core/services/unfinished_intent.py#L126) |
| function | `_er_negeret` | `(tail, m)` | True hvis pausenøgleordet er indledt af en negation («uden at …»). | [src](../../../core/services/unfinished_intent.py#L152) |
| function | `_sætning_omkring` | `(tail, m)` | Returner (sætning, startindeks) for sætningen matchet står i. | [src](../../../core/services/unfinished_intent.py#L203) |
| function | `_er_sætningsblokeret` | `(tail, m)` | True hvis sætningen omkring matchet er negeret eller spørgende. | [src](../../../core/services/unfinished_intent.py#L215) |
| function | `detect_unfinished_intent` | `(text)` | Returner UnfinishedIntent hvis teksten antyder Jarvis stoppede midt | [src](../../../core/services/unfinished_intent.py#L253) |
| function | `is_in_cooldown` | `(session_id)` | True hvis session_id har triggered en continuation indenfor cooldown-vinduet. | [src](../../../core/services/unfinished_intent.py#L371) |
| function | `mark_triggered` | `(session_id)` | Marker at en continuation netop er triggered for session_id. | [src](../../../core/services/unfinished_intent.py#L380) |
| function | `reset_cooldown_for_tests` | `()` | Test-helper: tøm cooldown-state mellem test cases. | [src](../../../core/services/unfinished_intent.py#L388) |

## `core/services/untrusted_fencing.py`
_Indhegning af utroet indhold — porteret fra jarvis-code._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_neutralisér` | `(tekst)` | Afvaebn hegn-markoerer INDE i nyttelasten. | [src](../../../core/services/untrusted_fencing.py#L46) |
| function | `fence` | `(kilde, indhold)` | Pak indhold ind som utroet data. Self-safe. | [src](../../../core/services/untrusted_fencing.py#L63) |
| function | `kilde_for_tool` | `(navn)` | Hvilken slags kilde er dette vaerktoejs resultat? Ren. | [src](../../../core/services/untrusted_fencing.py#L71) |
| function | `should_fence` | `(navn)` | Skal dette vaerktoejs resultat hegnes ind? Ren. | [src](../../../core/services/untrusted_fencing.py#L88) |
| function | `_hegn_blok` | `(kilde, blok)` | Hegn teksten i én indholdsblok. Ikke-tekst-blokke roeres ikke. | [src](../../../core/services/untrusted_fencing.py#L101) |
| function | `fence_tool_result` | `(navn, resultat)` | Hegn den laesbare krop af et vaerktoejs-resultat. Self-safe. | [src](../../../core/services/untrusted_fencing.py#L112) |

## `core/services/upload_sandbox.py`
_Uploadede filer og arkiver — pakket ud ét sted, og aldrig eksekverbart._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ExtractResult` | `` | — | [src](../../../core/services/upload_sandbox.py#L47) |
| method | `ExtractResult.as_dict` | `(self)` | — | [src](../../../core/services/upload_sandbox.py#L55) |
| function | `looks_like_archive` | `(path)` | Er filen et arkiv? Afgøres på INDHOLD, ikke på navn. | [src](../../../core/services/upload_sandbox.py#L61) |
| function | `harden_upload` | `(path)` | Gør en uploadet fil ulæselig for andre og umulig at eksekvere. | [src](../../../core/services/upload_sandbox.py#L76) |
| function | `sandbox_root_for` | `(attachment_id)` | Mappen et bestemt arkiv pakkes ud i. Én pr. vedhæftning. | [src](../../../core/services/upload_sandbox.py#L89) |
| function | `_is_inside` | `(root, candidate)` | Ligger `candidate` under `root` — også efter symlink-opløsning? | [src](../../../core/services/upload_sandbox.py#L95) |
| function | `_reject_name` | `(name)` | Tom streng hvis navnet er i orden, ellers grunden til at det ikke er. | [src](../../../core/services/upload_sandbox.py#L109) |
| function | `_write_entry` | `(dest, data_iter, remaining)` | Skriv én post og returnér antal skrevne bytes. Rejser ValueError ved loft. | [src](../../../core/services/upload_sandbox.py#L122) |
| function | `_chunks` | `(fileobj, size=…)` | — | [src](../../../core/services/upload_sandbox.py#L136) |
| function | `safe_extract` | `(archive_path, attachment_id)` | Pak et arkiv ud i sin egen sandkasse — post for post. | [src](../../../core/services/upload_sandbox.py#L144) |
| function | `scan_tree` | `(root)` | Kør ClamAV på en udpakket sandkasse. (ren, begrundelse). | [src](../../../core/services/upload_sandbox.py#L234) |

## `core/services/user_activity.py`
_Bruger-aktivitets-nerve — ét sted der svarer "hvornår var X sidst aktiv, og hvordan"._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_q1` | `(conn, sql, params)` | — | [src](../../../core/services/user_activity.py#L17) |
| function | `build_user_activity_surface` | `(*, active_within_s=…)` | Pr. registreret bruger: sidst aktiv (flettet fra alle kilder), via hvad, aktiv nu, | [src](../../../core/services/user_activity.py#L25) |

## `core/services/user_contradiction_tracker.py`
_User Contradiction Tracker — detects when the user contradicts themselves._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_tokens` | `(text)` | — | [src](../../../core/services/user_contradiction_tracker.py#L46) |
| function | `_has_negation` | `(text)` | — | [src](../../../core/services/user_contradiction_tracker.py#L50) |
| function | `_fetch_recent_user_messages` | `(*, hours=…, limit=…)` | Fetch recent user (role='user') chat messages. | [src](../../../core/services/user_contradiction_tracker.py#L54) |
| function | `_fetch_existing_statements` | `(*, limit=…)` | Fetch stored user statements for comparison. | [src](../../../core/services/user_contradiction_tracker.py#L76) |
| function | `_ensure_user_contradiction_tables` | `(conn)` | Idempotent table creation — delegates to db_user_contradiction's helper. | [src](../../../core/services/user_contradiction_tracker.py#L95) |
| function | `extract_statements` | `(text)` | Split a message into individual claim-like sentences. | [src](../../../core/services/user_contradiction_tracker.py#L105) |
| function | `_classify_topic` | `(text)` | Simple keyword-based topic classification. | [src](../../../core/services/user_contradiction_tracker.py#L138) |
| function | `_detect_contradictions_between` | `(new_statement, new_topic, existing, *, max_findings=…)` | Compare a new statement against existing stored statements. | [src](../../../core/services/user_contradiction_tracker.py#L170) |
| function | `scan_for_contradictions` | `(*, hours=…)` | Main entry point — scan recent user messages for contradictions. | [src](../../../core/services/user_contradiction_tracker.py#L231) |
| function | `build_user_contradiction_surface` | `(*, limit=…)` | Build signal surface for user contradictions. | [src](../../../core/services/user_contradiction_tracker.py#L355) |
| function | `record_user_statement` | `(text, topic=…, session_id=…, source=…, user_id=…)` | Record a user statement. Thin wrapper around DB upsert. | [src](../../../core/services/user_contradiction_tracker.py#L430) |
| function | `check_contradiction` | `(text, topic=…, user_id=…)` | Check a statement against existing stored statements for contradictions. | [src](../../../core/services/user_contradiction_tracker.py#L467) |
| function | `detect_and_store_contradiction` | `(text, topic=…, session_id=…, source=…, user_id=…)` | Record a statement AND detect/store contradictions in one call. | [src](../../../core/services/user_contradiction_tracker.py#L489) |
| function | `get_user_contradictions` | `(*, limit=…, status=…, user_id=…)` | Get stored contradictions. Thin wrapper around DB query. | [src](../../../core/services/user_contradiction_tracker.py#L576) |

## `core/services/user_emotional_resonance.py`
_User Emotional Resonance — detect and respond to the user's mood._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `detect_user_mood` | `(*, user_message, run_id=…)` | Detect user mood from message and persist. | [src](../../../core/services/user_emotional_resonance.py#L73) |
| function | `get_current_user_mood` | `()` | Get the latest detected user mood. | [src](../../../core/services/user_emotional_resonance.py#L139) |
| function | `build_user_emotional_resonance_surface` | `()` | MC surface for user emotional resonance. | [src](../../../core/services/user_emotional_resonance.py#L147) |

## `core/services/user_hensyn.py`
_Bruger-hensyn — handlingsrelevante hensyn med VARIG og SITUATIONEL levetid._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Hensyn` | `` | Ét handlingsrelevant hensyn med levetid, grænse og effekt-tælling. | [src](../../../core/services/user_hensyn.py#L161) |
| method | `Hensyn.to_dict` | `(self)` | — | [src](../../../core/services/user_hensyn.py#L185) |
| method | `Hensyn.from_dict` | `(cls, data)` | — | [src](../../../core/services/user_hensyn.py#L189) |
| function | `_load` | `()` | Læs de gemte hensyn. Tom liste hvis intet er gemt — aldrig en fejl. | [src](../../../core/services/user_hensyn.py#L199) |
| function | `_save` | `(items)` | — | [src](../../../core/services/user_hensyn.py#L212) |
| function | `_normaliser` | `(tekst)` | — | [src](../../../core/services/user_hensyn.py#L224) |
| function | `_nøgle` | `(regel)` | Sammenligningsnøgle for to formuleringer af samme hensyn. | [src](../../../core/services/user_hensyn.py#L228) |
| function | `kandidat_kategori` | `(linje)` | Kategori for en kandidatlinje — ``None`` når linjen ikke er en kandidat. | [src](../../../core/services/user_hensyn.py#L235) |
| function | `kandidater` | `(linjer)` | (kategori, linje) for de linjer der kan bære et hensyn. Rækkefølgen bevares. | [src](../../../core/services/user_hensyn.py#L255) |
| function | `_formuler` | `(linje, kategori, llm)` | Formulér (regel, grænse) for én kandidat — ``None`` når den forkastes. | [src](../../../core/services/user_hensyn.py#L286) |
| function | `_nu` | `()` | — | [src](../../../core/services/user_hensyn.py#L337) |
| function | `_alder_dage` | `(hensyn, nu)` | — | [src](../../../core/services/user_hensyn.py#L341) |
| function | `vaegt` | `(hensyn, nu=…)` | Hensynets aktuelle vægt 0-1. Varige er altid 1.0. | [src](../../../core/services/user_hensyn.py#L351) |
| function | `forfrem` | `(hensyn, nu=…)` | Situationel → varig når den er set nok gange eller kilden er eksplicit varig. | [src](../../../core/services/user_hensyn.py#L360) |
| function | `opdater` | `(hensyn, nu=…)` | Anvend levetidsreglerne: forfrem, falm, og erklær støj. | [src](../../../core/services/user_hensyn.py#L372) |
| function | `aktive` | `(hensyns, nu=…)` | De hensyn der må bruge plads i prompten, stærkeste først. | [src](../../../core/services/user_hensyn.py#L395) |
| function | `marker_injiceret` | `(hensyns, ids)` | Tæl at disse hensyn blev injiceret i en tur. Kaldes af læsesiden. | [src](../../../core/services/user_hensyn.py#L407) |
| function | `marker_ramte` | `(hensyns, hensyn_id)` | Registrér at hensynet faktisk påvirkede et svar. Nulstiller støj-tællingen. | [src](../../../core/services/user_hensyn.py#L416) |
| function | `tjek_brud` | `(hensyn, svar)` | Deterministisk brud-detektor for de kategorier hvor det er entydigt. | [src](../../../core/services/user_hensyn.py#L426) |
| function | `registrer_svar` | `(hensyns, svar)` | Kør brud-detektoren på et færdigt svar. Returnerer den opdaterede liste. | [src](../../../core/services/user_hensyn.py#L450) |
| function | `_linje_hash` | `(linje)` | — | [src](../../../core/services/user_hensyn.py#L464) |
| function | `_behandlede` | `()` | Kildelinjer der allerede er vurderet — så et modelkald ikke gentages. | [src](../../../core/services/user_hensyn.py#L470) |
| function | `_gem_behandlede` | `(hashes)` | — | [src](../../../core/services/user_hensyn.py#L487) |
| function | `udled` | `(linjer, *, kilde, llm=…, eksisterende=…)` | Udled hensyn fra profil-linjer. Eksisterende hensyn genkendes og tælles. | [src](../../../core/services/user_hensyn.py#L498) |
| function | `_profil_linjer` | `(workspace_dir)` | (sektion, linje) fra de dele af USER.md der kan bære hensyn. | [src](../../../core/services/user_hensyn.py#L561) |
| function | `tick_user_hensyn` | `(*, workspace_dir=…, llm=…, skip_cadence=…)` | Baggrunds-udledning: læs profilen, udled hensyn, anvend levetiderne. | [src](../../../core/services/user_hensyn.py#L579) |
| function | `byg_hensyn_sektion` | `(*, max_chars=…, nu=…, taeller_injektion=…)` | Prompt-sektionen — "" når intet hensyn er aktivt. | [src](../../../core/services/user_hensyn.py#L654) |

## `core/services/user_md_update_proposal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_user_md_update_proposals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L20) |
| function | `refresh_runtime_user_md_update_proposal_statuses` | `()` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L42) |
| function | `build_runtime_user_md_update_proposal_surface` | `(*, limit=…)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L73) |
| function | `_extract_user_md_update_proposals` | `()` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L101) |
| function | `_persist_user_md_update_proposals` | `(*, proposals, session_id, run_id)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L159) |
| function | `_with_runtime_view` | `(item, proposal)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L232) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L242) |
| function | `_build_proposal_type` | `(*, item)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L252) |
| function | `_build_user_dimension` | `(*, item, proposal_type)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L265) |
| function | `_build_proposed_update` | `(*, proposal_type)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L278) |
| function | `_build_proposal_reason` | `(*, proposal_type, proposal_confidence, signal_summary)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L288) |
| function | `_build_proposal_confidence` | `(*, signal_confidence, proposal_type)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L300) |
| function | `_build_source_anchor` | `(*, item)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L308) |
| function | `_build_status_reason` | `(*, proposal_type, signal_status)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L318) |
| function | `_title_suffix` | `(user_dimension)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L329) |
| function | `_dimension_from_canonical_key` | `(canonical_key)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L334) |
| function | `_source_anchor_from_support_summary` | `(summary)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L339) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L344) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L353) |
| function | `_parse_dt` | `(raw)` | — | [src](../../../core/services/user_md_update_proposal_tracking.py#L363) |

## `core/services/user_model_daemon.py`
_User model daemon — Theory of Mind: a living model of the user's state and patterns._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_persist_user_model` | `()` | — | [src](../../../core/services/user_model_daemon.py#L44) |
| function | `tick_user_model_daemon` | `(recent_messages, *, skip_event_gate=…)` | Analyze recent interaction and update user model. | [src](../../../core/services/user_model_daemon.py#L52) |
| function | `get_user_model_summary` | `()` | — | [src](../../../core/services/user_model_daemon.py#L130) |
| function | `build_user_model_surface` | `()` | — | [src](../../../core/services/user_model_daemon.py#L134) |
| function | `build_user_model_prompt_line` | `(*, max_chars=…)` | Én linje til den SYNLIGE prompt — "" når dæmonen intet har målt endnu. | [src](../../../core/services/user_model_daemon.py#L142) |
| function | `_analyze_messages` | `(messages)` | — | [src](../../../core/services/user_model_daemon.py#L167) |
| function | `_detect_communication_style` | `(messages)` | — | [src](../../../core/services/user_model_daemon.py#L184) |
| function | `_generate_model_summary` | `(messages, model)` | — | [src](../../../core/services/user_model_daemon.py#L195) |
| function | `_store_model` | `(summary, now)` | — | [src](../../../core/services/user_model_daemon.py#L223) |

## `core/services/user_scope.py`
_Per-bruger data-scope (SECURITY #154, streng GDPR)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `scope_uid` | `()` | Den bruger-id en privat DB-operation skal scopes til. "" hvis intet kan | [src](../../../core/services/user_scope.py#L15) |

## `core/services/user_temperature_engine.py`
_User temperature field engine — Lag 10 two-stream pipeline._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_afgraens_workspace` | `(workspace)` | Hvilken workspace må læses? Tom → intet (fail-closed). | [src](../../../core/services/user_temperature_engine.py#L70) |
| function | `_coerce_float` | `(v)` | — | [src](../../../core/services/user_temperature_engine.py#L75) |
| function | `_now` | `()` | — | [src](../../../core/services/user_temperature_engine.py#L82) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/user_temperature_engine.py#L86) |
| function | `_punct_density` | `(message)` | — | [src](../../../core/services/user_temperature_engine.py#L93) |
| function | `_caps_density` | `(message)` | — | [src](../../../core/services/user_temperature_engine.py#L100) |
| function | `_burst_density` | `(message_at, *, workspace=…)` | User msgs in last 5 min, normalized: 0 → 0.0, 5+ → 1.0. | [src](../../../core/services/user_temperature_engine.py#L108) |
| function | `_delay_since_last_jarvis` | `(message_at, *, workspace=…)` | Seconds since the prior assistant message. None if no prior or > 60min. | [src](../../../core/services/user_temperature_engine.py#L132) |
| function | `_parse_hour` | `(message_at)` | — | [src](../../../core/services/user_temperature_engine.py#L166) |
| function | `_compute_raw_signals` | `(*, message, message_at, baseline, workspace=…)` | Map a single message + baseline to 6 normalized signals. | [src](../../../core/services/user_temperature_engine.py#L174) |
| function | `map_signals_to_field` | `(signals)` | Pure function: 6 raw signals → valens/arousal/texture/confidence. | [src](../../../core/services/user_temperature_engine.py#L222) |
| function | `_texture_from_circumplex` | `(valens, arousal)` | Pure function: (valens, arousal) → texture key. | [src](../../../core/services/user_temperature_engine.py#L245) |
| function | `_validate_llm_output` | `(raw)` | — | [src](../../../core/services/user_temperature_engine.py#L269) |
| function | `combine_streams` | `(*, struct, llm)` | Deterministic merge of structural + LLM streams. | [src](../../../core/services/user_temperature_engine.py#L294) |
| function | `_is_significant_shift` | `(prior, new)` | Did valens/arousal shift > threshold or texture change? | [src](../../../core/services/user_temperature_engine.py#L362) |
| function | `_compute_baseline` | `(*, days=…, workspace=…)` | Compute rolling baseline from last N days of user messages. | [src](../../../core/services/user_temperature_engine.py#L376) |
| function | `get_active_field` | `(*, workspace_id=…)` | Read active field, honoring kill-switch. | [src](../../../core/services/user_temperature_engine.py#L445) |
| function | `format_temperature_field_for_heartbeat` | `(*, workspace_id=…)` | Render the field as a heartbeat awareness-section block. | [src](../../../core/services/user_temperature_engine.py#L470) |
| function | `get_response_style_modifiers` | `(*, workspace_id=…)` | Return response-style hints based on active temperature field. | [src](../../../core/services/user_temperature_engine.py#L510) |
| function | `get_active_field_surface` | `(*, workspace_id=…, force_refresh=…)` | Return MC-friendly surface dict. force_refresh ignored in Phase 1. | [src](../../../core/services/user_temperature_engine.py#L563) |
| function | `run_structural_stream` | `(*, workspace_id, message, message_at)` | Per-message structural pipeline. Updates struct_* + recomputes field_*. | [src](../../../core/services/user_temperature_engine.py#L594) |
| function | `_get_or_build_baseline` | `(*, prior, settings, workspace=…)` | Return cached baseline if fresh, else rebuild. | [src](../../../core/services/user_temperature_engine.py#L667) |
| function | `_has_pending_trigger` | `(*, workspace_id)` | Read trigger flag without consuming. | [src](../../../core/services/user_temperature_engine.py#L723) |
| function | `run_llm_stream` | `(*, workspace_id=…, force=…)` | Run LLM-based pipeline (4h cadence or on trigger). | [src](../../../core/services/user_temperature_engine.py#L729) |

## `core/services/user_temperature_runtime.py`
_Daemon for the user-temperature LLM stream (Lag 10)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get_workspace_lock` | `(workspace_id)` | — | [src](../../../core/services/user_temperature_runtime.py#L26) |
| function | `_run_one_cycle` | `(workspace_id, *, force=…)` | Acquire workspace lock, run LLM stream. Never raises. | [src](../../../core/services/user_temperature_runtime.py#L35) |
| function | `_list_active_workspaces` | `()` | — | [src](../../../core/services/user_temperature_runtime.py#L52) |
| function | `_resolve_periodic_interval_seconds` | `()` | — | [src](../../../core/services/user_temperature_runtime.py#L56) |
| function | `_loop` | `()` | Two rhythms in one loop: | [src](../../../core/services/user_temperature_runtime.py#L65) |
| function | `start_user_temperature_runtime` | `()` | Start the daemon. Idempotent. | [src](../../../core/services/user_temperature_runtime.py#L88) |
| function | `stop_user_temperature_runtime` | `()` | — | [src](../../../core/services/user_temperature_runtime.py#L101) |

## `core/services/user_theory_of_mind.py`
_User Theory of Mind — model what the user thinks and feels._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_user_mental_model` | `(user_id=…)` | Build a theory-of-mind model of the user. | [src](../../../core/services/user_theory_of_mind.py#L22) |
| function | `_build_secondary_user_model` | `(user_id)` | Return stored ToM snapshot for a secondary user. | [src](../../../core/services/user_theory_of_mind.py#L33) |
| function | `_build_primary_user_model` | `()` | Build live DB-backed theory-of-mind for the primary user. | [src](../../../core/services/user_theory_of_mind.py#L45) |
| function | `format_user_model_for_prompt` | `(model)` | Compact user model for prompt injection. | [src](../../../core/services/user_theory_of_mind.py#L102) |
| function | `build_user_theory_of_mind_surface` | `()` | — | [src](../../../core/services/user_theory_of_mind.py#L124) |
| function | `_emit_user_theory_of_mind_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/user_theory_of_mind.py#L140) |

## `core/services/user_understanding_signal_tracking.py`
_User-understanding signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_user_understanding_signals_for_visible_turn` | `(*, session_id, run_id, user_message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L33) |
| function | `refresh_runtime_user_understanding_signal_statuses` | `()` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L75) |
| function | `build_runtime_user_understanding_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L79) |
| function | `_extract_user_understanding_candidates` | `(*, user_message, session_id)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L83) |
| function | `_preference_signal` | `(messages)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L117) |
| function | `_workstyle_signal` | `(messages)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L173) |
| function | `_reminder_worthiness_signal` | `(messages)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L204) |
| function | `_cadence_preference_signal` | `(messages)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L233) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L264) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L273) |
| function | `_user_understanding_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L282) |
| function | `_recent_user_messages` | `(*, session_id, current_message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L294) |
| function | `_is_explicit_danish_preference` | `(message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L318) |
| function | `_is_explicit_concise_preference` | `(message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L326) |
| function | `_is_scoped_workstyle_signal` | `(message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L334) |
| function | `_is_carry_forward_preference` | `(message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L350) |
| function | `_is_reporting_cadence_preference` | `(message)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L357) |
| function | `_dimension_from_canonical_key` | `(canonical_key)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L373) |
| function | `_source_anchor` | `(text)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L380) |
| function | `_source_anchor_from_support_summary` | `(summary)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L385) |
| function | `_quote` | `(text, *, limit=…)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L392) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L401) |
| function | `_contains_any` | `(text, needles)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L413) |
| function | `_rank_confidence` | `(confidence)` | — | [src](../../../core/services/user_understanding_signal_tracking.py#L417) |

## `core/services/valence_trajectory.py`
_Valence Trajectory — long-term flourishing/withering signal._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_persisted_samples` | `()` | — | [src](../../../core/services/valence_trajectory.py#L35) |
| function | `_persist_samples` | `()` | — | [src](../../../core/services/valence_trajectory.py#L52) |
| function | `_clamp` | `(x, lo=…, hi=…)` | — | [src](../../../core/services/valence_trajectory.py#L68) |
| function | `_sample_current_valence` | `()` | Compute a single instantaneous valence score in [-1, 1] from runtime signals. | [src](../../../core/services/valence_trajectory.py#L72) |
| function | `tick` | `(_seconds=…)` | Sample current valence and append to rolling window. | [src](../../../core/services/valence_trajectory.py#L127) |
| function | `_trajectory_from_window` | `()` | Compute trajectory statistics from current window. | [src](../../../core/services/valence_trajectory.py#L138) |
| function | `_infer_dominant_driver` | `(current_score)` | Heuristic: which single signal is pushing hardest right now? | [src](../../../core/services/valence_trajectory.py#L180) |
| function | `get_trajectory` | `()` | Return cached trajectory, recomputing only periodically. | [src](../../../core/services/valence_trajectory.py#L208) |
| function | `current_instant` | `()` | Freshest instantaneous valence — the latest window sample (reactive, present-moment), | [src](../../../core/services/valence_trajectory.py#L218) |
| function | `build_valence_trajectory_surface` | `()` | Mission Control surface for valence trajectory. | [src](../../../core/services/valence_trajectory.py#L231) |
| function | `_summary_line` | `(traj)` | — | [src](../../../core/services/valence_trajectory.py#L246) |
| function | `build_valence_trajectory_prompt_section` | `()` | Return a single prompt line when trajectory is notable. | [src](../../../core/services/valence_trajectory.py#L262) |
| function | `reset_valence_trajectory` | `()` | Reset state (for testing). | [src](../../../core/services/valence_trajectory.py#L274) |
| function | `_publish_valence_trajectory_transition` | `(payload=…)` | Publish a state-transition event. Called from real transition points | [src](../../../core/services/valence_trajectory.py#L285) |

## `core/services/value_formation.py`
_Value Formation — emergent ethics from experience._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_value_from_experience` | `(*, action, outcome, reflection)` | — | [src](../../../core/services/value_formation.py#L12) |
| function | `detect_value_from_outcome` | `(*, action_type, outcome_status, user_mood)` | Detect potential value-forming experiences. | [src](../../../core/services/value_formation.py#L32) |
| function | `get_crystallized_values` | `(conviction_threshold=…)` | Return values with conviction above threshold — these have become commitments. | [src](../../../core/services/value_formation.py#L54) |
| function | `build_formed_values_surface` | `()` | — | [src](../../../core/services/value_formation.py#L60) |

## `core/services/verification_gate.py`
_Verification gate — advisory check on destructive/mutation actions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `sqlite_kald_er_laesning` | `(sql)` | Er hele `sqlite3`-kaldets SQL en ren læsning? | [src](../../../core/services/verification_gate.py#L117) |
| function | `_uden_anfoersel` | `(tekst)` | Erstat hvert anførselstegns-span med `Q`. | [src](../../../core/services/verification_gate.py#L148) |
| function | `_opdel_segmenter` | `(c)` | Opdel på shell-separatorer UDEN FOR anførselstegn. | [src](../../../core/services/verification_gate.py#L181) |
| function | `_ssh_remote_kommando` | `(seg)` | Udtræk fjernkommandoen fra et ssh-kald — eller `None` hvis kaldet ikke | [src](../../../core/services/verification_gate.py#L254) |
| function | `_ssh_er_laesning` | `(seg, dybde)` | Er ssh-kaldet en ren læsning? Kun hvis fjernkommandoen selv er det. | [src](../../../core/services/verification_gate.py#L312) |
| function | `_python_er_laesning` | `(args, hel_segment)` | Er dette python-kald beviseligt en læsning? | [src](../../../core/services/verification_gate.py#L348) |
| function | `_curl_er_laesning` | `(args)` | Kun en ren GET uden data-, upload- eller output-flag er en læsning. | [src](../../../core/services/verification_gate.py#L365) |
| function | `shell_command_is_mutating` | `(command, *, _dybde=…)` | True hvis et shell-kald reelt ændrer state; False for read-only. | [src](../../../core/services/verification_gate.py#L383) |
| function | `_suggested_verify` | `(tool)` | — | [src](../../../core/services/verification_gate.py#L545) |
| function | `_recent_events` | `(minutes=…)` | — | [src](../../../core/services/verification_gate.py#L553) |
| function | `_scan` | `(events)` | Classify events into mutations / strict-verifies / light-verifies. | [src](../../../core/services/verification_gate.py#L567) |
| function | `evaluate_verification_gate` | `(*, minutes=…)` | Return verification-gate signals for the recent window. | [src](../../../core/services/verification_gate.py#L631) |
| function | `_observe_verification_decision` | `(*, passed, failed, unverified)` | Egress-frit Central-observe af verifikations-gatens beslutning (§7.2). | [src](../../../core/services/verification_gate.py#L683) |
| function | `verification_gate_section` | `(*, record=…)` | Format gate signals as a prompt-awareness section, or None. | [src](../../../core/services/verification_gate.py#L709) |
| function | `_exec_verification_status` | `(args)` | — | [src](../../../core/services/verification_gate.py#L791) |

## `core/services/verification_gate_telemetry.py`
_R2 verification gate telemetry — track whether warnings get heeded._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/verification_gate_telemetry.py#L52) |
| function | `_save` | `(data)` | — | [src](../../../core/services/verification_gate_telemetry.py#L64) |
| function | `record_surface` | `(*, failed_verify_count, unverified_count, mutation_count, verify_count)` | Called by verification_gate_section when it returns a non-None section. | [src](../../../core/services/verification_gate_telemetry.py#L97) |
| function | `record_verify_event` | `(*, tool, status, at=…, verify_kind=…)` | Called by the telemetry listener for tool.completed events. If a recent | [src](../../../core/services/verification_gate_telemetry.py#L134) |
| function | `sweep_expired_surfaces` | `()` | Mark surfaces as 'ignored' once they're past the reaction window with | [src](../../../core/services/verification_gate_telemetry.py#L180) |
| function | `get_telemetry_summary` | `(*, hours=…)` | Aggregate counts + heed rates over the lookback window. | [src](../../../core/services/verification_gate_telemetry.py#L211) |
| function | `telemetry_section` | `()` | Render telemetry as a prompt-awareness section. Only shows when there's | [src](../../../core/services/verification_gate_telemetry.py#L266) |
| function | `_poll_db_for_verify_events` | `()` | Poll the events table for new tool.completed verify_* events. | [src](../../../core/services/verification_gate_telemetry.py#L304) |
| function | `subscribe` | `()` | Start the DB-polling telemetry listener. Idempotent per process. | [src](../../../core/services/verification_gate_telemetry.py#L384) |

## `core/services/versioneret_json_svar.py`
_Et færdigt HTTP-svar pr. version — serialiseret og komprimeret ÉN gang._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_vil_have_gzip` | `(accept_encoding)` | — | [src](../../../core/services/versioneret_json_svar.py#L35) |
| function | `versioneret_json_svar` | `(*, noegle, version, etag, accept_encoding, indhold)` | Byg (eller genbrug) svaret for `version`. `indhold` kaldes kun ved ny version. | [src](../../../core/services/versioneret_json_svar.py#L44) |

## `core/services/veto_gate.py`
_Adaptive veto gate — pre-execution hook that pauses tool calls when pushback is firm._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_negated` | `(user_message, consent_start_idx)` | True if a negation word appears within ~30 chars of the consent token. | [src](../../../core/services/veto_gate.py#L105) |
| function | `_check_token_signal_gate` | `(user_message, tool_name)` | Check if user message contains explicit consent that overrides veto. | [src](../../../core/services/veto_gate.py#L131) |
| function | `_maybe_record_override_from_token_signal` | `(tool_name)` | If the token-signal gate detected an override pattern, check if there | [src](../../../core/services/veto_gate.py#L167) |
| function | `_ensure_veto_events_table` | `()` | Ensure the veto_events table exists. | [src](../../../core/services/veto_gate.py#L232) |
| function | `log_veto_event` | `(tool_name, user_message, feeling, intensity, evidence_summary, veto_result, resolution=…)` | Log a veto decision to the veto_events table. | [src](../../../core/services/veto_gate.py#L242) |
| function | `resolve_veto_event` | `(event_id, resolution)` | Mark a veto event as resolved (overridden, honored, false_positive). | [src](../../../core/services/veto_gate.py#L283) |
| function | `veto_event_stats` | `(tool_name=…, limit=…)` | Read recent veto events for observability. | [src](../../../core/services/veto_gate.py#L327) |
| function | `_ensure_veto_adaptive_counters_table` | `()` | Create the table if missing + migrate legacy KV entries once per process. | [src](../../../core/services/veto_gate.py#L471) |
| function | `_adjust_counter` | `(tool_name, feeling, kind, delta)` | Read-modify-write a counter ("overrides" or "honored") in veto_adaptive_counters. | [src](../../../core/services/veto_gate.py#L526) |
| function | `_get_counter` | `(tool_name, feeling, kind)` | Read a counter without modification. | [src](../../../core/services/veto_gate.py#L563) |
| function | `_get_override_count` | `(tool_name, feeling)` | — | [src](../../../core/services/veto_gate.py#L580) |
| function | `_increment_override_count` | `(tool_name, feeling)` | — | [src](../../../core/services/veto_gate.py#L584) |
| function | `_get_honored_count` | `(tool_name, feeling)` | — | [src](../../../core/services/veto_gate.py#L588) |
| function | `_increment_honored_count` | `(tool_name, feeling)` | — | [src](../../../core/services/veto_gate.py#L592) |
| function | `_base_threshold` | `(tool_name, feeling)` | Look up per-(tool, feeling) base from _BASE_THRESHOLDS. | [src](../../../core/services/veto_gate.py#L596) |
| function | `_override_lift` | `(overrides)` | Aftagende stigning pr. override: ceiling * n/(n+half). | [src](../../../core/services/veto_gate.py#L605) |
| function | `_adaptive_threshold` | `(tool_name, feeling, intensity)` | Compute the effective veto threshold for this (tool, feeling) pair. | [src](../../../core/services/veto_gate.py#L617) |
| function | `check_veto` | `(tool_name, user_message=…, session_id=…, record_event=…, user_present=…)` | Check if a tool call should be vetoed. | [src](../../../core/services/veto_gate.py#L710) |
| function | `_extract_feeling` | `(section)` | Extract the feeling name from the pushback section. | [src](../../../core/services/veto_gate.py#L897) |
| function | `_extract_intensity` | `(section)` | Extract the intensity value from the pushback section. | [src](../../../core/services/veto_gate.py#L907) |
| function | `_summarize_evidence` | `(section)` | Extract a brief evidence summary from the pushback section. | [src](../../../core/services/veto_gate.py#L920) |
| function | `_extract_action` | `(section)` | Extract the action tier from the pushback section text. | [src](../../../core/services/veto_gate.py#L933) |
| function | `_has_evidence` | `(section)` | Check if the pushback section contains evidence markers. | [src](../../../core/services/veto_gate.py#L943) |
| function | `_format_veto_reason` | `(section, tool_name, event_id=…)` | Format a human-readable veto reason. | [src](../../../core/services/veto_gate.py#L948) |
| function | `build_veto_gate_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/veto_gate.py#L978) |
| function | `record_override` | `(tool_name, feeling)` | Record that the user overrode a veto for this (tool, feeling) pair. | [src](../../../core/services/veto_gate.py#L1041) |
| function | `record_jarvis_override` | `(tool_name, feeling)` | Registrér at JARVIS — ikke brugeren — overstyrede en gate for dette (tool, feeling). | [src](../../../core/services/veto_gate.py#L1073) |
| function | `_emit_veto_gate_event` | `(kind, payload=…)` | Emit a scoped event — defensive, never blocks caller. | [src](../../../core/services/veto_gate.py#L1103) |

## `core/services/visible_autonomous_run.py`
_Autonome (heartbeat-startede) synlige runs: starter og observation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_trust_for_session` | `(session_id)` | Samtalens tilladelses-niveau — fail-closed til `ask`. | [src](../../../core/services/visible_autonomous_run.py#L22) |
| function | `_observe_autonomous_run` | `(*, run, session_id, outcome, frames=…, error=…)` | #10 (Phase A): gør autonome runs (dream/idle/proaktiv) synlige som ENHED i Den | [src](../../../core/services/visible_autonomous_run.py#L37) |
| function | `start_autonomous_run` | `(message, session_id=…, follow=…, origin=…, task_id=…, max_tool_calls=…, max_seconds=…, tool_scope=…, force_user_id=…, started_callback=…, completion_callback=…)` | Trigger an autonomous (heartbeat-initiated) visible run in a background thread. | [src](../../../core/services/visible_autonomous_run.py#L95) |

## `core/services/visible_chat_pragmatics.py`
_Pragmatic conversation boundaries for the visible chat-only lane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_chat_style_contract` | `(message, session_id)` | Build a short, per-user/current-turn style contract for the cache tail. | [src](../../../core/services/visible_chat_pragmatics.py#L65) |
| function | `build_chat_mode_dynamic_tail` | `(tail, *, message, session_id)` | Append the active mode's large contract after the cache boundary. | [src](../../../core/services/visible_chat_pragmatics.py#L136) |
| function | `apply_chat_mode_conversation_contract` | `(instruction)` | Append the hierarchy only when the effective runtime scope is ``chat``. | [src](../../../core/services/visible_chat_pragmatics.py#L173) |

## `core/services/visible_chat_quality.py`
_Observe chat-response quality without rewriting the user's text._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_hierarchy_signals` | `(prose, paragraphs)` | Mål om et langt svar har hierarki — ikke om det er pænt. | [src](../../../core/services/visible_chat_quality.py#L31) |
| function | `_emoji_heading_signals` | `(prose)` | Mål om overskrifterne bærer emoji — den form Bjørn bad om 25/10-2026. | [src](../../../core/services/visible_chat_quality.py#L45) |
| function | `analyse_chat_response` | `(text, *, wall_chars=…)` | Return measurable quality signals for a final chat response. | [src](../../../core/services/visible_chat_quality.py#L67) |
| function | `observe_chat_response` | `(text, **context)` | Emit one metadata-only observation when, and only when, scope is chat. | [src](../../../core/services/visible_chat_quality.py#L117) |

## `core/services/visible_first_pass_output.py`
_Én synlig grænse for første modelsvar._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `FirstPassOutputFilter` | `` | Filtrér capability-markup, DSML og synlige runtime-markører — i den rækkefølge. | [src](../../../core/services/visible_first_pass_output.py#L50) |
| method | `FirstPassOutputFilter.__init__` | `(self, kilder=…)` | — | [src](../../../core/services/visible_first_pass_output.py#L53) |
| method | `FirstPassOutputFilter._dsml` | `(self, text)` | — | [src](../../../core/services/visible_first_pass_output.py#L70) |
| method | `FirstPassOutputFilter._halv` | `(self, text)` | Fjern den halve DSL-form: navnet og de rå tags — men BEHOLD indholdet. | [src](../../../core/services/visible_first_pass_output.py#L82) |
| method | `FirstPassOutputFilter.feed` | `(self, text)` | — | [src](../../../core/services/visible_first_pass_output.py#L117) |
| method | `FirstPassOutputFilter.fundet` | `(self)` | Citation-markører fundet i strømmen. | [src](../../../core/services/visible_first_pass_output.py#L131) |
| method | `FirstPassOutputFilter.flush` | `(self)` | — | [src](../../../core/services/visible_first_pass_output.py#L140) |

## `core/services/visible_first_pass_pump.py`
_Worker-thread pump for the first visible model stream._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `pump_first_pass` | `(run, *, controller, tool_scope, loop, queue, sentinel, stream_fn=…)` | — | [src](../../../core/services/visible_first_pass_pump.py#L10) |

## `core/services/visible_first_pass_results.py`
_Publish first-pass tool outcomes before post-tool prompt assembly._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `surface_tool_result` | `(sr, status=…)` | Close one measured call immediately before its terminal UI fact. | [src](../../../core/services/visible_first_pass_results.py#L18) |
| function | `_ejer_kan_svare` | `(run)` | Er der et menneske i den anden ende af DENNE kørsel? | [src](../../../core/services/visible_first_pass_results.py#L42) |
| function | `publish_first_pass_results` | `(results, *, run, step_counter, out)` | Resolve approvals and publish terminal UI facts; do not persist transcript. | [src](../../../core/services/visible_first_pass_results.py#L72) |

