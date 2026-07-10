# `core.identity` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/identity/__init__.py`

_(no top-level classes or functions)_

## `core/identity/candidate_workflow.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `approve_runtime_contract_candidate` | `(candidate_id, *, status_reason_override=…)` | — | [src](../../../core/identity/candidate_workflow.py#L42) |
| function | `reject_runtime_contract_candidate` | `(candidate_id)` | — | [src](../../../core/identity/candidate_workflow.py#L86) |
| function | `apply_runtime_contract_candidate` | `(candidate_id, *, status_reason_override=…)` | — | [src](../../../core/identity/candidate_workflow.py#L110) |
| function | `_should_auto_apply` | `(candidate, kind)` | Memory-cluster (2026-06-22): rut promotion-beslutningen gennem den GRADEREDE | [src](../../../core/identity/candidate_workflow.py#L210) |
| function | `auto_apply_safe_user_md_candidates` | `()` | — | [src](../../../core/identity/candidate_workflow.py#L229) |
| function | `auto_apply_safe_memory_md_candidates` | `()` | — | [src](../../../core/identity/candidate_workflow.py#L269) |
| function | `apply_approved_runtime_contract_candidates` | `(*, target_files=…, limit=…)` | — | [src](../../../core/identity/candidate_workflow.py#L309) |
| function | `_require_candidate` | `(candidate_id)` | — | [src](../../../core/identity/candidate_workflow.py#L355) |
| function | `_require_status` | `(candidate, *, allowed)` | — | [src](../../../core/identity/candidate_workflow.py#L364) |
| function | `_latest_equivalent_applied_candidate` | `(candidate)` | — | [src](../../../core/identity/candidate_workflow.py#L370) |
| function | `_candidate_eligible_for_auto_apply` | `(candidate)` | — | [src](../../../core/identity/candidate_workflow.py#L389) |
| function | `_memory_candidate_eligible_for_auto_apply` | `(candidate)` | — | [src](../../../core/identity/candidate_workflow.py#L435) |
| function | `_candidate_dimension_key` | `(candidate)` | — | [src](../../../core/identity/candidate_workflow.py#L516) |
| function | `_candidate_write_material` | `(candidate)` | — | [src](../../../core/identity/candidate_workflow.py#L524) |
| function | `_user_line_from_key` | `(candidate)` | — | [src](../../../core/identity/candidate_workflow.py#L547) |
| function | `_memory_line_from_key` | `(candidate)` | — | [src](../../../core/identity/candidate_workflow.py#L558) |
| function | `_canonical_self_line_from_key` | `(candidate)` | — | [src](../../../core/identity/candidate_workflow.py#L566) |
| function | `_chronicle_write_material` | `(candidate)` | — | [src](../../../core/identity/candidate_workflow.py#L570) |
| function | `_default_approval_status_reason` | `(candidate, *, superseded)` | — | [src](../../../core/identity/candidate_workflow.py#L592) |
| function | `_default_apply_status_reason` | `(candidate, *, write_status)` | — | [src](../../../core/identity/candidate_workflow.py#L617) |
| function | `_fuzzy_line_match` | `(line, existing_text, threshold=…)` | Check if *line* is already present in *existing_text* (fuzzy). | [src](../../../core/identity/candidate_workflow.py#L636) |
| function | `_append_curated_topic_line` | `(content_line)` | Route en MEMORY.md-promovering til curated-memory-TOPIC'en i stedet for at | [src](../../../core/identity/candidate_workflow.py#L674) |
| function | `_append_workspace_contract_line` | `(*, target_file, section_heading, content_line)` | — | [src](../../../core/identity/candidate_workflow.py#L710) |
| function | `_append_workspace_contract_line_raw` | `(*, target_file, section_heading, content_line)` | — | [src](../../../core/identity/candidate_workflow.py#L729) |
| function | `_append_workspace_contract_block` | `(*, target_file, section_heading, content_block)` | — | [src](../../../core/identity/candidate_workflow.py#L784) |
| function | `_insert_under_heading` | `(text, heading, content_line)` | — | [src](../../../core/identity/candidate_workflow.py#L824) |
| function | `_insert_block_under_heading` | `(text, heading, content_block)` | — | [src](../../../core/identity/candidate_workflow.py#L847) |
| function | `_apply_chronicle_runtime_contract_candidate` | `(candidate, *, status_reason_override=…)` | — | [src](../../../core/identity/candidate_workflow.py#L870) |
| function | `_chronicle_entry_shape` | `(candidate)` | — | [src](../../../core/identity/candidate_workflow.py#L965) |
| function | `_single_line` | `(value)` | — | [src](../../../core/identity/candidate_workflow.py#L973) |
| function | `_now_iso` | `()` | — | [src](../../../core/identity/candidate_workflow.py#L977) |
| function | `_check_repeat_writer_trap` | `(target_file, content_line)` | Check if the same content has been written too many times. Alarm if stuck. | [src](../../../core/identity/candidate_workflow.py#L995) |

## `core/identity/email_verify.py`
_Email-verifikation (spec 2026-06-15 §5). Token-store i runtime_state_kv,_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RateLimited` | `` | — | [src](../../../core/identity/email_verify.py#L16) |
| function | `_now` | `()` | — | [src](../../../core/identity/email_verify.py#L20) |
| function | `_today` | `()` | — | [src](../../../core/identity/email_verify.py#L24) |
| function | `_load` | `()` | — | [src](../../../core/identity/email_verify.py#L28) |
| function | `_save` | `(items)` | — | [src](../../../core/identity/email_verify.py#L33) |
| function | `create_token` | `(*, user_id, email, ttl_hours=…)` | — | [src](../../../core/identity/email_verify.py#L37) |
| function | `consume_token` | `(token)` | Returnér user_id hvis token er gyldigt + ikke udløbet; fjern det (engangs). | [src](../../../core/identity/email_verify.py#L52) |
| function | `_send_mail` | `(args)` | — | [src](../../../core/identity/email_verify.py#L74) |
| function | `send_verification_email` | `(*, user_id, email, base_url)` | — | [src](../../../core/identity/email_verify.py#L79) |

## `core/identity/owner_resolver.py`
_Owner-identity resolution for autonomous dispatch._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `get_owner_discord_id` | `()` | Return the owner's Discord user ID, or empty string if unknown. | [src](../../../core/identity/owner_resolver.py#L34) |
| function | `is_owner_session` | `(session)` | Decide whether a session record belongs to the owner. | [src](../../../core/identity/owner_resolver.py#L63) |
| function | `resolve_owner_target_session` | `()` | Find the session that an autonomous Bjørn-event should target. | [src](../../../core/identity/owner_resolver.py#L104) |
| function | `session_is_external_channel` | `(session_id)` | True hvis sessionen er en EKSTERN kanal (Discord/Telegram) ud fra titlen. | [src](../../../core/identity/owner_resolver.py#L166) |
| function | `resolve_owner_app_session` | `()` | Som resolve_owner_target_session, men returnerer KUN en app/webchat- | [src](../../../core/identity/owner_resolver.py#L186) |

## `core/identity/passwords.py`
_Password-hashing (spec 2026-06-15 §5.2) — bcrypt, cost-factor 12._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `hash_password` | `(plaintext)` | bcrypt-hash (cost 12). Returnerer en utf-8-streng ($2b$…). | [src](../../../core/identity/passwords.py#L12) |
| function | `verify_password` | `(plaintext, hashed)` | True hvis password matcher hash. Fejl-tolerant (ugyldigt hash → False). | [src](../../../core/identity/passwords.py#L18) |

## `core/identity/project_context.py`
_Project context — current "where am I working" as set by JarvisX._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `current_project_root` | `()` | Return the current project root path, or empty string if none. | [src](../../../core/identity/project_context.py#L23) |
| function | `set_project_root` | `(path)` | Set the project root for the current context. | [src](../../../core/identity/project_context.py#L28) |
| function | `reset_project_root` | `(token)` | — | [src](../../../core/identity/project_context.py#L38) |

## `core/identity/runtime_candidates.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_extract_proposal_types` | `(items, target_file)` | — | [src](../../../core/identity/runtime_candidates.py#L56) |
| function | `_observe_candidate_workflows` | `(counts)` | Egress-fri puls til Centralen (§24.4) — cluster=identity. KUN antal foreslåede | [src](../../../core/identity/runtime_candidates.py#L98) |
| function | `build_runtime_candidate_workflows` | `()` | — | [src](../../../core/identity/runtime_candidates.py#L125) |
| function | `total_pending_runtime_candidates` | `(workflows)` | — | [src](../../../core/identity/runtime_candidates.py#L248) |
| function | `build_runtime_candidate_write_history` | `()` | — | [src](../../../core/identity/runtime_candidates.py#L255) |
| function | `_workflow_state` | `(*, workflow_id, label, target_file, proposed_count, approved_count, rejected_count, applied_count, superseded_count, items, proposal_types=…, is_canonical_self=…)` | — | [src](../../../core/identity/runtime_candidates.py#L282) |
| function | `_with_apply_readiness` | `(item)` | — | [src](../../../core/identity/runtime_candidates.py#L342) |
| function | `candidate_apply_readiness` | `(item)` | — | [src](../../../core/identity/runtime_candidates.py#L350) |
| function | `_workflow_apply_readiness_summary` | `(items)` | — | [src](../../../core/identity/runtime_candidates.py#L440) |

## `core/identity/runtime_contract.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_runtime_contract_state` | `(name=…)` | — | [src](../../../core/identity/runtime_contract.py#L82) |
| function | `_observe_runtime_contract` | `(*, canonical_present, canonical_expected, pending_write_count, capabilities_available, capabilities_gated, bootstrap_status)` | Egress-fri puls til Centralen (§24.4) — cluster=identity. KUN present/expected/ | [src](../../../core/identity/runtime_contract.py#L241) |
| function | `_bootstrap_status` | `(workspace_dir)` | — | [src](../../../core/identity/runtime_contract.py#L275) |
| function | `_file_state` | `(path, *, name, role, loaded_by_default, activation, writer)` | — | [src](../../../core/identity/runtime_contract.py#L307) |
| function | `_canonical_activation` | `(filename)` | — | [src](../../../core/identity/runtime_contract.py#L330) |
| function | `_canonical_writer` | `(filename)` | — | [src](../../../core/identity/runtime_contract.py#L338) |
| function | `_file_summary` | `(name, role, present, loaded_by_default)` | — | [src](../../../core/identity/runtime_contract.py#L344) |
| function | `_capability_contract_state` | `(capability_truth)` | — | [src](../../../core/identity/runtime_contract.py#L354) |

## `core/identity/user_attribution_migrations.py`
_User attribution migrations — add user_id/workspace_name columns._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_table_has_column` | `(conn, table, column)` | — | [src](../../../core/identity/user_attribution_migrations.py#L62) |
| function | `_table_exists` | `(conn, table)` | — | [src](../../../core/identity/user_attribution_migrations.py#L78) |
| function | `run_user_attribution_migrations` | `()` | Add user_id / attributable_user_id columns to all listed tables. | [src](../../../core/identity/user_attribution_migrations.py#L89) |
| function | `list_user_attribution_schema` | `()` | Return current status of all attribution columns for admin/debug. | [src](../../../core/identity/user_attribution_migrations.py#L133) |

## `core/identity/user_db.py`
_Højniveau-bruger-adapter (spec 2026-06-15) ovenpå users-tabellen._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/identity/user_db.py#L23) |
| function | `_norm_email` | `(email)` | — | [src](../../../core/identity/user_db.py#L27) |
| function | `_email_hash` | `(email)` | Deterministisk opslags-hash. Pepper fra runtime (eller fast fallback). | [src](../../../core/identity/user_db.py#L31) |
| function | `_enc` | `(user_id, value)` | — | [src](../../../core/identity/user_db.py#L41) |
| function | `_dec` | `(user_id, blob)` | — | [src](../../../core/identity/user_db.py#L47) |
| function | `_row_to_public` | `(row)` | — | [src](../../../core/identity/user_db.py#L56) |
| function | `create_user` | `(*, email, name, password, role=…, workspace=…)` | — | [src](../../../core/identity/user_db.py#L80) |
| function | `get_user` | `(user_id)` | — | [src](../../../core/identity/user_db.py#L99) |
| function | `find_user_by_email` | `(email)` | — | [src](../../../core/identity/user_db.py#L104) |
| function | `verify_login` | `(email, password)` | — | [src](../../../core/identity/user_db.py#L109) |
| function | `set_google_email` | `(user_id, google_email, role=…)` | Knyt en Google-email til en konto (migration/linking). STORE-AGNOSTISK: | [src](../../../core/identity/user_db.py#L118) |
| function | `has_google_link` | `(user_id)` | Har brugeren en Google-konto linket? (vedvarende UI-indikator). | [src](../../../core/identity/user_db.py#L133) |
| function | `find_user_by_google_email` | `(google_email)` | Slå en konto op via sin linkede Google-email. Returnerer {user_id, role}. | [src](../../../core/identity/user_db.py#L138) |
| function | `set_email_verified` | `(user_id, verified=…)` | — | [src](../../../core/identity/user_db.py#L152) |
| function | `mute_user` | `(user_id)` | — | [src](../../../core/identity/user_db.py#L157) |
| function | `unmute_user` | `(user_id)` | — | [src](../../../core/identity/user_db.py#L161) |
| function | `set_quota_tier` | `(user_id, tier)` | — | [src](../../../core/identity/user_db.py#L165) |
| function | `set_language` | `(user_id, language)` | Sæt brugerens sprog-præference (da/en/auto). Self-scope via account-route. | [src](../../../core/identity/user_db.py#L171) |
| function | `set_consent` | `(user_id, *, data_processing=…, marketing=…, blind_access=…)` | — | [src](../../../core/identity/user_db.py#L178) |
| function | `list_users` | `(*, include_deleted=…)` | — | [src](../../../core/identity/user_db.py#L190) |
| function | `_effective_tier` | `(user)` | Eksplicit tier vinder. Uden eksplicit tier kvalificerer kun owner-rollen | [src](../../../core/identity/user_db.py#L203) |
| function | `create_api_key` | `(user_id, *, ttl_days=…)` | Mint en langlivet API-nøgle (JWT m. jti) hvis brugerens tier kvalificerer. | [src](../../../core/identity/user_db.py#L213) |
| function | `revoke_api_key` | `(user_id)` | Revokér brugerens API-nøgle: bloklist dens jti + ryd den lagrede nøgle. | [src](../../../core/identity/user_db.py#L231) |
| function | `is_api_key_revoked` | `(jti)` | — | [src](../../../core/identity/user_db.py#L249) |
| function | `_provision_workspace` | `(user)` | Opret + (§16) krypter brugerens workspace ved oprettelse: mappe + baseline- | [src](../../../core/identity/user_db.py#L257) |
| function | `register_user` | `(*, email, name, password, base_url, role=…)` | Selvregistrering (officiel vej): opret bruger (email_verified=0) + | [src](../../../core/identity/user_db.py#L272) |
| function | `verify_email_token` | `(token)` | Forbrug et verifikations-token → markér brugeren email_verified. | [src](../../../core/identity/user_db.py#L287) |
| function | `add_user` | `(*, email, name, password, role=…, workspace=…, tier=…)` | Owner/Jarvis' manuelle oprettelse: opretter en FÆRDIG-verificeret bruger | [src](../../../core/identity/user_db.py#L296) |
| function | `_audit` | `(*, user_id, action, actor)` | — | [src](../../../core/identity/user_db.py#L315) |
| function | `read_audit_log` | `()` | — | [src](../../../core/identity/user_db.py#L324) |
| function | `delete_user` | `(user_id, *, mode=…, actor=…)` | mode='soft' → deleted_at-timestamp (fortryd-venlig, grace-period). | [src](../../../core/identity/user_db.py#L330) |

## `core/identity/users.py`
_User Registry — per-user workspace mapping for multi-user Jarvis._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_users_file` | `()` | Resolve users.json path at call time so tests can isolate via HOME. | [src](../../../core/identity/users.py#L38) |
| class | `User` | `` | — | [src](../../../core/identity/users.py#L46) |
| method | `User.as_dict` | `(self)` | — | [src](../../../core/identity/users.py#L59) |
| function | `_now_iso` | `()` | — | [src](../../../core/identity/users.py#L63) |
| function | `_ensure_file` | `()` | — | [src](../../../core/identity/users.py#L67) |
| function | `load_users` | `()` | Load all registered users from users.json. Empty list if file missing. | [src](../../../core/identity/users.py#L77) |
| function | `_save_users` | `(users)` | — | [src](../../../core/identity/users.py#L113) |
| function | `find_user_by_discord_id` | `(discord_id)` | Lookup by discord_id. Returns None if unknown. | [src](../../../core/identity/users.py#L123) |
| function | `find_user_by_name` | `(name)` | — | [src](../../../core/identity/users.py#L134) |
| function | `find_user_by_workspace` | `(workspace)` | — | [src](../../../core/identity/users.py#L144) |
| function | `add_user` | `(*, discord_id, name, role=…, workspace=…)` | Add a new user. Returns the User or None on validation failure. | [src](../../../core/identity/users.py#L154) |
| function | `remove_user` | `(*, discord_id)` | Remove user from registry. Does NOT delete workspace files (manual decision). | [src](../../../core/identity/users.py#L196) |
| function | `_update_user_field` | `(discord_id, field, value)` | Opdatér ét felt på en bruger (immutabel replace) og persistér. False hvis ukendt. | [src](../../../core/identity/users.py#L210) |
| function | `set_app_id` | `(*, discord_id, app_id)` | Bind en jarvis-desk-app (UUID4) til en bruger — kryptografisk session-binding. | [src](../../../core/identity/users.py#L231) |
| function | `set_totp_seed` | `(*, discord_id, seed)` | Sæt/rotér en brugers TOTP-override-seed. SECRET (§6.0): kun owner-session | [src](../../../core/identity/users.py#L236) |
| function | `get_totp_seed` | `(*, discord_id)` | Hent en brugers TOTP-seed ("" hvis ikke sat / ukendt bruger). | [src](../../../core/identity/users.py#L242) |
| function | `get_owner` | `()` | Return the single owner user (there should be exactly one). | [src](../../../core/identity/users.py#L248) |
| function | `is_known_discord_id` | `(discord_id)` | — | [src](../../../core/identity/users.py#L256) |
| function | `list_member_workspaces` | `()` | Return all registered workspace names (for UI / admin). | [src](../../../core/identity/users.py#L260) |

## `core/identity/visible_identity.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `load_visible_identity_prompt` | `(name=…)` | — | [src](../../../core/identity/visible_identity.py#L17) |
| function | `load_visible_identity_summary` | `(name=…)` | — | [src](../../../core/identity/visible_identity.py#L39) |
| function | `_observe_visible_identity` | `(summary)` | Egress-fri puls til Centralen (§24.4) — cluster=identity. KUN aktiv-flag + antal | [src](../../../core/identity/visible_identity.py#L73) |
| function | `_identity_lines` | `(path)` | — | [src](../../../core/identity/visible_identity.py#L95) |
| function | `_bounded_line` | `(text)` | — | [src](../../../core/identity/visible_identity.py#L110) |
| function | `_fingerprint` | `(text)` | — | [src](../../../core/identity/visible_identity.py#L117) |

## `core/identity/workspace_bootstrap.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `WorkspaceBootstrapResult` | `` | — | [src](../../../core/identity/workspace_bootstrap.py#L37) |
| method | `WorkspaceBootstrapResult.summary` | `(self)` | — | [src](../../../core/identity/workspace_bootstrap.py#L42) |
| function | `_resolve_workspace_name` | `(name)` | Resolve 'default' to current contextvar workspace if one is bound. | [src](../../../core/identity/workspace_bootstrap.py#L50) |
| function | `ensure_default_workspace` | `(name=…)` | — | [src](../../../core/identity/workspace_bootstrap.py#L66) |
| function | `ensure_layered_memory_dirs` | `(name=…)` | — | [src](../../../core/identity/workspace_bootstrap.py#L71) |
| function | `workspace_memory_paths` | `(name=…)` | — | [src](../../../core/identity/workspace_bootstrap.py#L88) |
| function | `append_daily_memory_note` | `(note, *, name=…, source=…)` | Append a short note to today's daily memory file. | [src](../../../core/identity/workspace_bootstrap.py#L104) |
| function | `read_daily_memory_lines` | `(*, name=…, limit=…)` | Read the most recent daily memory notes (today only). | [src](../../../core/identity/workspace_bootstrap.py#L163) |
| function | `read_recent_daily_memory_lines` | `(*, name=…, days=…, limit=…)` | Read bounded daily memory notes across a recent lookback window. | [src](../../../core/identity/workspace_bootstrap.py#L204) |
| function | `_load_known_sizes` | `(workspace_dir)` | Load last-known-good file sizes from .file_sizes.json in the workspace. | [src](../../../core/identity/workspace_bootstrap.py#L253) |
| function | `_save_known_sizes` | `(workspace_dir, sizes)` | Persist current file sizes as last-known-good baseline. | [src](../../../core/identity/workspace_bootstrap.py#L266) |
| function | `_check_workspace_file_health` | `(workspace_dir, filename, known_sizes)` | Check a workspace file for suspicious shrinkage or stub-level size. | [src](../../../core/identity/workspace_bootstrap.py#L301) |
| function | `bootstrap_workspace` | `(name=…)` | — | [src](../../../core/identity/workspace_bootstrap.py#L359) |
| function | `bootstrap_user_workspace` | `(workspace_name, *, display_name=…)` | Bootstrap a per-user workspace. Unlike bootstrap_workspace(), | [src](../../../core/identity/workspace_bootstrap.py#L439) |

## `core/identity/workspace_context.py`
_Workspace Context — thread-local/async-safe current-user binding._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `_ContextState` | `` | — | [src](../../../core/identity/workspace_context.py#L36) |
| function | `current_workspace_name` | `()` | Return current workspace name. Default 'default' if unset. | [src](../../../core/identity/workspace_context.py#L60) |
| function | `current_user_id` | `()` | Return current user_id (discord_id). Empty string if none set. | [src](../../../core/identity/workspace_context.py#L65) |
| function | `current_user_display_name` | `()` | — | [src](../../../core/identity/workspace_context.py#L70) |
| function | `current_context_snapshot` | `()` | — | [src](../../../core/identity/workspace_context.py#L74) |
| function | `set_context` | `(*, workspace_name, user_id=…, user_display_name=…, role=…, channel=…, session_id=…)` | Set workspace context explicitly. Returns Token for reset. | [src](../../../core/identity/workspace_context.py#L83) |
| function | `current_session_id` | `()` | Aktuel session-id ("" hvis ikke sat). | [src](../../../core/identity/workspace_context.py#L108) |
| function | `set_session_id` | `(session_id)` | Opdatér KUN session_id på den nuværende kontekst (bevar role/user/workspace). | [src](../../../core/identity/workspace_context.py#L113) |
| function | `effective_role` | `()` | Rollen efter TOTP-override-elevering (§6.0). | [src](../../../core/identity/workspace_context.py#L132) |
| function | `is_override_active` | `()` | True hvis sessionen er TOTP-override-elevet (IKKE en native owner-session). | [src](../../../core/identity/workspace_context.py#L154) |
| function | `privacy_scoped_user_id` | `()` | user_id til PRIVATLIVS-scopede data-læsninger (session-søgning, chat-historik). | [src](../../../core/identity/workspace_context.py#L173) |
| function | `reset_context` | `(token)` | — | [src](../../../core/identity/workspace_context.py#L185) |
| function | `user_context` | `(*, discord_id=…, workspace_override=…, user_display_name_override=…)` | Set workspace context for the duration of a block. | [src](../../../core/identity/workspace_context.py#L190) |
| function | `bind_context_if_unset` | `(*, workspace_name=…, user_id=…, user_display_name=…)` | Bind context only if still on default — useful for late-binding | [src](../../../core/identity/workspace_context.py#L237) |
| function | `current_role` | `()` | Return current bearer-token role ("owner"|"member"|"guest"|""). | [src](../../../core/identity/workspace_context.py#L256) |
| function | `current_channel` | `()` | Return the transport channel the current request came in on. | [src](../../../core/identity/workspace_context.py#L263) |

