# `core.runtime.03` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/runtime/provider_router.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `load_provider_router_registry` | `()` | — | [src](../../../core/runtime/provider_router.py#L18) |
| function | `configure_provider_router_entry` | `(*, provider, model, auth_mode, auth_profile, base_url, api_key, lane, set_visible)` | — | [src](../../../core/runtime/provider_router.py#L30) |
| function | `provider_router_summary` | `()` | — | [src](../../../core/runtime/provider_router.py#L125) |
| function | `main_agent_target` | `()` | — | [src](../../../core/runtime/provider_router.py#L162) |
| function | `main_agent_selection` | `()` | — | [src](../../../core/runtime/provider_router.py#L183) |
| function | `select_main_agent_target` | `(*, provider, model, auth_profile=…)` | — | [src](../../../core/runtime/provider_router.py#L200) |
| function | `resolve_provider_router_target` | `(*, lane)` | — | [src](../../../core/runtime/provider_router.py#L254) |
| function | `provider_router_lane_targets` | `()` | — | [src](../../../core/runtime/provider_router.py#L320) |
| function | `list_provider_router_targets` | `(*, lane)` | — | [src](../../../core/runtime/provider_router.py#L325) |
| function | `_provider_surface` | `(item)` | — | [src](../../../core/runtime/provider_router.py#L360) |
| function | `_model_surface` | `(item)` | — | [src](../../../core/runtime/provider_router.py#L378) |
| function | `_latest_model_for_lane` | `(*, registry, lane)` | — | [src](../../../core/runtime/provider_router.py#L388) |
| function | `_configured_main_agent_targets` | `(*, registry)` | — | [src](../../../core/runtime/provider_router.py#L405) |
| function | `_configured_target_match` | `(*, registry, provider, model)` | — | [src](../../../core/runtime/provider_router.py#L447) |
| function | `_readiness_hint` | `(*, provider, auth_mode, auth_profile)` | — | [src](../../../core/runtime/provider_router.py#L459) |
| function | `_provider_entry` | `(*, registry, provider)` | — | [src](../../../core/runtime/provider_router.py#L472) |
| function | `_provider_auth_mode` | `(*, provider, registry)` | — | [src](../../../core/runtime/provider_router.py#L483) |
| function | `_provider_base_url` | `(*, provider, registry)` | — | [src](../../../core/runtime/provider_router.py#L490) |
| function | `_credentials_ready` | `(*, provider, auth_profile)` | — | [src](../../../core/runtime/provider_router.py#L497) |
| function | `_upsert_provider` | `(items, entry)` | — | [src](../../../core/runtime/provider_router.py#L514) |
| function | `_upsert_model` | `(items, entry)` | — | [src](../../../core/runtime/provider_router.py#L523) |
| function | `_default_registry` | `()` | — | [src](../../../core/runtime/provider_router.py#L536) |
| function | `_normalize_simple_id` | `(value, *, label)` | — | [src](../../../core/runtime/provider_router.py#L543) |
| function | `_normalize_auth_mode` | `(value)` | — | [src](../../../core/runtime/provider_router.py#L550) |
| function | `_ollama_model_exists` | `(*, registry, model)` | Return True if *model* is available in the live Ollama instance. | [src](../../../core/runtime/provider_router.py#L557) |
| function | `_normalize_profile` | `(value)` | — | [src](../../../core/runtime/provider_router.py#L572) |
| function | `_normalize_lane` | `(value)` | — | [src](../../../core/runtime/provider_router.py#L579) |
| function | `_now` | `()` | — | [src](../../../core/runtime/provider_router.py#L586) |

## `core/runtime/refresh_tokens.py`
_Refresh-token-rotation (spec §22.6)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_hash` | `(token)` | — | [src](../../../core/runtime/refresh_tokens.py#L26) |
| function | `_now` | `()` | — | [src](../../../core/runtime/refresh_tokens.py#L30) |
| function | `_kv` | `()` | — | [src](../../../core/runtime/refresh_tokens.py#L34) |
| function | `_index_add` | `(user_id, h)` | — | [src](../../../core/runtime/refresh_tokens.py#L39) |
| function | `issue_refresh_token` | `(user_id)` | Udsted en ny refresh-token til brugeren. Returnerer den RÅ token (vises kun | [src](../../../core/runtime/refresh_tokens.py#L51) |
| function | `verify_refresh_token` | `(token)` | Returnér user_id hvis refresh-token er gyldig (aktiv + ikke udløbet), ellers None. | [src](../../../core/runtime/refresh_tokens.py#L67) |
| function | `_deactivate` | `(h)` | — | [src](../../../core/runtime/refresh_tokens.py#L81) |
| function | `rotate_refresh_token` | `(token, *, app_id=…)` | Veksl en refresh-token til et nyt access+refresh-par. Den gamle refresh-token | [src](../../../core/runtime/refresh_tokens.py#L92) |
| function | `revoke_all` | `(user_id)` | Invalidér ALLE brugerens refresh-tokens (§22.6 + !revoke-override). Returnerer | [src](../../../core/runtime/refresh_tokens.py#L115) |

## `core/runtime/run_profile.py`
_Hvilken profil koerer en given koersel under — Fase 9._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `profil_navn_for` | `(run, *, research=…)` | Profilnavnet for en koersel. Falder altid ud i noget kendt. | [src](../../../core/runtime/run_profile.py#L30) |
| function | `_synlig_profil` | `(run)` | Ejeren eller et husstandsmedlem? | [src](../../../core/runtime/run_profile.py#L45) |
| function | `profil_for` | `(run, *, research=…, overstyring=…)` | Den effektive profil for en koersel — klar til at gemmes paa raekken. | [src](../../../core/runtime/run_profile.py#L83) |

## `core/runtime/runtime_json_io.py`
_Safe read/merge/write helpers for runtime.json._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `read_runtime_raw` | `()` | Return current runtime.json as a plain dict. Empty dict if file missing. | [src](../../../core/runtime/runtime_json_io.py#L30) |
| function | `_prune_old_backups` | `()` | — | [src](../../../core/runtime/runtime_json_io.py#L40) |
| function | `_write_backup` | `(payload)` | — | [src](../../../core/runtime/runtime_json_io.py#L56) |
| function | `write_runtime_merged` | `(updates)` | Merge `updates` into runtime.json, writing atomically. | [src](../../../core/runtime/runtime_json_io.py#L68) |

## `core/runtime/secrets.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `MailConfig` | `` | — | [src](../../../core/runtime/secrets.py#L18) |
| function | `_backup_file` | `()` | — | [src](../../../core/runtime/secrets.py#L27) |
| function | `_missing_key_message` | `(key)` | — | [src](../../../core/runtime/secrets.py#L31) |
| function | `ensure_runtime_file_perms` | `()` | Garantér at runtime.json kun er læsbar af ejeren (0600). | [src](../../../core/runtime/secrets.py#L41) |
| function | `_parse_int` | `(value, key)` | — | [src](../../../core/runtime/secrets.py#L59) |
| function | `read_runtime_key` | `(key, env_override=…, *, as_int=…)` | Read a top-level key from ~/.jarvis-v2/config/runtime.json. | [src](../../../core/runtime/secrets.py#L68) |
| function | `mail_config` | `()` | — | [src](../../../core/runtime/secrets.py#L103) |

## `core/runtime/session_handle.py`
_`SessionHandle` — én ejer, én lease, én sekvens._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SessionFormatError` | `` | Sessionens format kan ikke åbnes. Bærer hvilken slags. | [src](../../../core/runtime/session_handle.py#L63) |
| method | `SessionFormatError.__init__` | `(self, verdict, besked)` | — | [src](../../../core/runtime/session_handle.py#L66) |
| class | `NotWritable` | `` | Der blev forsøgt en skrivning gennem et skrivebeskyttet håndtag. | [src](../../../core/runtime/session_handle.py#L71) |
| class | `SessionHeader` | `` | Uforanderlig. Skrives ÉN gang ved oprettelsen og ændres aldrig. | [src](../../../core/runtime/session_handle.py#L76) |
| method | `SessionHeader.as_json` | `(self)` | — | [src](../../../core/runtime/session_handle.py#L87) |
| function | `_ensure_header_column` | `(conn)` | — | [src](../../../core/runtime/session_handle.py#L93) |
| function | `write_header` | `(session_id, *, generation=…)` | Skriv headeren én gang. Et andet forsøg er en fejl, ikke en opdatering. | [src](../../../core/runtime/session_handle.py#L100) |
| function | `read_header` | `(session_id)` | — | [src](../../../core/runtime/session_handle.py#L119) |
| function | `classify_format` | `(session_id)` | Fire udfald der kan skelnes. En session uden header er `current`: | [src](../../../core/runtime/session_handle.py#L142) |
| class | `SessionHandle` | `` | Ejerskabet gjort til noget man holder. Brug som context manager. | [src](../../../core/runtime/session_handle.py#L159) |
| method | `SessionHandle.__init__` | `(self, session_id, *, owner, token, header, format_verdict)` | — | [src](../../../core/runtime/session_handle.py#L162) |
| method | `SessionHandle.writable` | `(self)` | — | [src](../../../core/runtime/session_handle.py#L174) |
| method | `SessionHandle.token` | `(self)` | — | [src](../../../core/runtime/session_handle.py#L178) |
| method | `SessionHandle.seq` | `(self)` | — | [src](../../../core/runtime/session_handle.py#L181) |
| method | `SessionHandle.append` | `(self, event)` | Læg i kø. Intet rører databasen før `flush()` eller `close()`. | [src](../../../core/runtime/session_handle.py#L186) |
| method | `SessionHandle.flush` | `(self)` | Skriv køen som ÉN batch. Returnerer antal skrevne hændelser. | [src](../../../core/runtime/session_handle.py#L202) |
| method | `SessionHandle._projicer` | `(self)` | Kør projektionerne EFTER commit — kun for en kanonisk session. | [src](../../../core/runtime/session_handle.py#L222) |
| method | `SessionHandle.close` | `(self)` | Flush og GIV LEASE'N FRA DIG. Uden det venter næste proces på | [src](../../../core/runtime/session_handle.py#L251) |
| method | `SessionHandle.__enter__` | `(self)` | — | [src](../../../core/runtime/session_handle.py#L270) |
| method | `SessionHandle.__exit__` | `(self, *exc)` | — | [src](../../../core/runtime/session_handle.py#L273) |
| function | `_bedoem` | `(session_id)` | — | [src](../../../core/runtime/session_handle.py#L277) |
| function | `open_readonly` | `(session_id)` | Kig uden at tage noget. Skriver intet — heller ikke en lease-række. | [src](../../../core/runtime/session_handle.py#L289) |
| function | `open_for_write` | `(session_id, *, owner, ttl_s=…)` | Tag skriveretten. Returnerer et skrivebeskyttet håndtag hvis en anden | [src](../../../core/runtime/session_handle.py#L296) |

## `core/runtime/settings.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RuntimeSettings` | `` | — | [src](../../../core/runtime/settings.py#L11) |
| method | `RuntimeSettings.to_dict` | `(self)` | — | [src](../../../core/runtime/settings.py#L549) |
| function | `load_settings` | `()` | — | [src](../../../core/runtime/settings.py#L655) |
| function | `update_visible_execution_settings` | `(*, visible_model_provider=…, visible_model_name=…, visible_auth_profile=…)` | — | [src](../../../core/runtime/settings.py#L1107) |

## `core/runtime/state_store.py`
_Tiny JSON-file state store for module-globals that must survive restart._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_path` | `(name)` | — | [src](../../../core/runtime/state_store.py#L27) |
| function | `load_json` | `(name, default)` | Read ``state/<name>.json``; return ``default`` if missing/corrupt. | [src](../../../core/runtime/state_store.py#L31) |
| function | `save_json` | `(name, data)` | Atomically persist ``data`` to ``state/<name>.json``. | [src](../../../core/runtime/state_store.py#L48) |
| function | `save_json_strict` | `(name, data)` | Atomically persist JSON and propagate failures to authoritative callers. | [src](../../../core/runtime/state_store.py#L59) |

## `core/runtime/token_renewal.py`
_Fornyelse af bearer-tokens — så en klient ikke låses ude af tiden alene._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/runtime/token_renewal.py#L80) |
| function | `_afkod_uden_udloeb` | `(raw)` | Verificér signatur + udsteder, men LAD udløb passere. | [src](../../../core/runtime/token_renewal.py#L84) |
| function | `_gemt_bruger` | `(user_id)` | Slå brugeren op i BEGGE kartoteker. | [src](../../../core/runtime/token_renewal.py#L106) |
| function | `_klem_rolle` | `(token_rolle, gemt)` | Laveste af (token-rolle, gemt rolle). Ukendt bruger → token-rollen. | [src](../../../core/runtime/token_renewal.py#L130) |
| function | `_husk_jti` | `(user_id, jti)` | Skriv jti'en i brugerens liste, så den kan sortlistes senere. | [src](../../../core/runtime/token_renewal.py#L145) |
| function | `udloebs_alder_dage` | `(raw_token)` | Hvor mange dage er tokenet udløbet? Kun til LOGNING. | [src](../../../core/runtime/token_renewal.py#L163) |
| function | `renew` | `(raw_token, *, now=…)` | Veksl et bearer-token til et friskt et. | [src](../../../core/runtime/token_renewal.py#L189) |
| function | `revoke_user_tokens` | `(user_id)` | Sortlist alle fornyede tokens for én bruger. Returnerer antallet. | [src](../../../core/runtime/token_renewal.py#L260) |

## `core/runtime/work_ref.py`
_Én præfikset reference til et stykke arbejde — og ét sted at opløse den._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `UgyldigReference` | `` | Referencen kan ikke opløses. Rejses hellere end at gætte en art. | [src](../../../core/runtime/work_ref.py#L62) |
| function | `lav` | `(art, id_)` | Byg en reference. Afviser ukendte arter og tomme id'er. | [src](../../../core/runtime/work_ref.py#L66) |
| function | `opløs` | `(reference)` | `art:id` → `(art, id)`. Afviser alt den ikke kan opløse. | [src](../../../core/runtime/work_ref.py#L88) |
| function | `er_gyldig` | `(reference)` | Kan referencen opløses? Til steder der skal filtrere, ikke fejle. | [src](../../../core/runtime/work_ref.py#L109) |
| function | `lager_for` | `(reference)` | Hvilket lager peger referencen ind i? Til fejlbeskeder og flader. | [src](../../../core/runtime/work_ref.py#L118) |
| function | `fra_run` | `(run_id)` | Genvej for den hyppigste rod: en synlig eller autonom kørsel. | [src](../../../core/runtime/work_ref.py#L124) |
| function | `fra_task` | `(task_id)` | — | [src](../../../core/runtime/work_ref.py#L129) |

## `core/runtime/workspace_paths.py`
_Workspace path resolver — single source of truth for filesystem layout._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `NoUserContextError` | `` | Raised when workspace_dir() is called without a resolvable user_id. | [src](../../../core/runtime/workspace_paths.py#L17) |
| function | `_jarvis_home` | `()` | JARVIS_HOME resolved at call time (so tests can override via env). | [src](../../../core/runtime/workspace_paths.py#L26) |
| function | `shared_dir` | `()` | Jarvis' own state. All users see the same instance. | [src](../../../core/runtime/workspace_paths.py#L31) |
| function | `workspace_dir` | `(user_id=…)` | Per-relation workspace. Defaults to current_user_id() from context. | [src](../../../core/runtime/workspace_paths.py#L40) |
| function | `workspace_dir_or_owner` | `()` | workspace_dir() with an owner fallback, then shared/ as last resort. | [src](../../../core/runtime/workspace_paths.py#L65) |
| function | `_user_id_to_workspace_name` | `(user_id)` | Resolve user_id → workspace folder name. | [src](../../../core/runtime/workspace_paths.py#L89) |

## `core/runtime/ws_auth.py`
_Legitimation paa en WebSocket — uden at skrive tokenet i adgangsloggen._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_foerste_bearer` | `(vaerdi)` | — | [src](../../../core/runtime/ws_auth.py#L38) |
| function | `token_fra_handshake` | `(headers)` | Find tokenet i et WS-handshake. | [src](../../../core/runtime/ws_auth.py#L45) |
| function | `verificer` | `(token)` | Verificér tokenet. Returnerer claims, eller None hvis det ikke holder. | [src](../../../core/runtime/ws_auth.py#L74) |
| function | `kraeves_auth` | `()` | Er auth slaaet til i denne runtime? | [src](../../../core/runtime/ws_auth.py#L91) |

