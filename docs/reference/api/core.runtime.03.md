# `core.runtime.03` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/runtime/state_store.py`
_Tiny JSON-file state store for module-globals that must survive restart._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_path` | `(name)` | — | [src](../../../core/runtime/state_store.py#L26) |
| function | `load_json` | `(name, default)` | Read ``state/<name>.json``; return ``default`` if missing/corrupt. | [src](../../../core/runtime/state_store.py#L30) |
| function | `save_json` | `(name, data)` | Atomically persist ``data`` to ``state/<name>.json``. | [src](../../../core/runtime/state_store.py#L47) |

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

