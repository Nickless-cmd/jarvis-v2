# `core.runtime.04` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/runtime/workspace_paths.py`
_Workspace path resolver — single source of truth for filesystem layout._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `NoUserContextError` | `` | Raised when workspace_dir() is called without a resolvable user_id. | [src](../../../core/runtime/workspace_paths.py#L17) |
| function | `_jarvis_home` | `()` | JARVIS_HOME resolved at call time (so tests can override via env). | [src](../../../core/runtime/workspace_paths.py#L26) |
| function | `shared_dir` | `()` | Jarvis' own state. All users see the same instance. | [src](../../../core/runtime/workspace_paths.py#L31) |
| function | `workspace_dir` | `(user_id=…)` | Per-relation workspace. Defaults to current_user_id() from context. | [src](../../../core/runtime/workspace_paths.py#L40) |
| function | `heartbeat_home` | `()` | Heartbeatets hjem — Jarvis' EGEN rytme, ikke en brugers. | [src](../../../core/runtime/workspace_paths.py#L65) |
| function | `heartbeat_state_path` | `()` | Den fulde sti til heartbeatets tilstand. ÉT svar, ét sted. | [src](../../../core/runtime/workspace_paths.py#L87) |
| function | `heartbeat_policy_path` | `()` | Den fulde sti til heartbeatets policy (HEARTBEAT.md). | [src](../../../core/runtime/workspace_paths.py#L92) |
| function | `workspace_dir_or_owner` | `()` | workspace_dir() with an owner fallback, then shared/ as last resort. | [src](../../../core/runtime/workspace_paths.py#L97) |
| function | `_user_id_to_workspace_name` | `(user_id)` | Resolve user_id → workspace folder name. | [src](../../../core/runtime/workspace_paths.py#L121) |
| function | `rent_mappe_eller_filnavn` | `(navn)` | Et BLOT navn — ingen sti, ingen `..`. Tom streng når det ikke er det. | [src](../../../core/runtime/workspace_paths.py#L157) |
| function | `published_files_dir` | `(user_id=…, *, opret=…)` | Hvor ÉN brugers udgivne filer bor. `~/.jarvis-v2/files/u/<workspace>/`. | [src](../../../core/runtime/workspace_paths.py#L179) |
| function | `published_file_path` | `(filnavn, user_id=…, *, opret_mappe=…)` | Den fulde sti til ÉN brugers fil. Rejser ValueError på en sti. | [src](../../../core/runtime/workspace_paths.py#L226) |

## `core/runtime/ws_auth.py`
_Legitimation paa en WebSocket — uden at skrive tokenet i adgangsloggen._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_foerste_bearer` | `(vaerdi)` | — | [src](../../../core/runtime/ws_auth.py#L41) |
| function | `token_fra_handshake` | `(headers)` | Find tokenet i et WS-handshake. | [src](../../../core/runtime/ws_auth.py#L48) |
| function | `verificer` | `(token)` | Verificér tokenet. Returnerer claims, eller None hvis det ikke holder. | [src](../../../core/runtime/ws_auth.py#L77) |
| function | `kraeves_auth` | `()` | Er auth slaaet til i denne runtime? | [src](../../../core/runtime/ws_auth.py#L94) |
| function | `_private_familier` | `()` | — | [src](../../../core/runtime/ws_auth.py#L129) |
| function | `er_ejer` | `(krav)` | Ejer = rollen «owner» i et verificeret token. Uden token (auth slået fra, | [src](../../../core/runtime/ws_auth.py#L139) |
| function | `til_klient` | `(item, *, ejer)` | Hvad der må sendes til denne klient, eller None. | [src](../../../core/runtime/ws_auth.py#L147) |

