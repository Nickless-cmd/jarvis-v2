# `core.runtime.04` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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

