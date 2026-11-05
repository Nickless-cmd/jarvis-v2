# `core.desktop` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/desktop/__init__.py`
_Jarvis' egen Linux-desktop (Xvfb + window manager) til visning i en fane._

_(no top-level classes or functions)_

## `core/desktop/x_session.py`
_X-session til Jarvis' desktop-fane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_fejl` | `(kode, tekst)` | — | [src](../../../core/desktop/x_session.py#L38) |
| function | `_utilgaengelig` | `(tekst)` | — | [src](../../../core/desktop/x_session.py#L42) |
| function | `_tal` | `(v, lo, hi)` | Klem et tal til [lo, hi]; None hvis det ikke er et endeligt tal. | [src](../../../core/desktop/x_session.py#L46) |
| function | `_taste` | `(navn)` | — | [src](../../../core/desktop/x_session.py#L55) |
| function | `bygg_input` | `(msg)` | Ren funktion: input-dict -> liste af xdotool-argumentlister (eller None). | [src](../../../core/desktop/x_session.py#L69) |
| function | `xvfb_args` | `(display=…, bredde=…, hoejde=…)` | Xvfb-kommandoen. | [src](../../../core/desktop/x_session.py#L118) |
| function | `mangler_pakker` | `()` | Navne på manglende binære pakker (tom liste = klar). | [src](../../../core/desktop/x_session.py#L129) |
| class | `XSession` | `` | — | [src](../../../core/desktop/x_session.py#L142) |
| method | `XSession.__init__` | `(self, display=…, bredde=…, hoejde=…)` | — | [src](../../../core/desktop/x_session.py#L143) |
| method | `XSession._env` | `(self)` | — | [src](../../../core/desktop/x_session.py#L151) |
| method | `XSession._start_proc` | `(self, args)` | — | [src](../../../core/desktop/x_session.py#L167) |
| method | `XSession.start` | `(self)` | — | [src](../../../core/desktop/x_session.py#L174) |
| method | `XSession._server_svarer` | `(self)` | Svarer X-serveren paa displayet? (ikke bare: findes socket-filen) | [src](../../../core/desktop/x_session.py#L206) |
| method | `XSession._ryd_doed_socket` | `(self, sok)` | Fjern resterne af en X-server der ikke svarer, saa vi kan starte en ny. | [src](../../../core/desktop/x_session.py#L217) |
| method | `XSession._fyld_skrivebord` | `(self)` | Saet baggrund, filhaandtering og en terminal paa skrivebordet. | [src](../../../core/desktop/x_session.py#L227) |
| method | `XSession._har_vindue` | `(self, moenster)` | Findes der allerede et vindue med navnet? (saa vi ikke starter dubletter) | [src](../../../core/desktop/x_session.py#L247) |
| method | `XSession.stop` | `(self)` | — | [src](../../../core/desktop/x_session.py#L258) |
| method | `XSession.frame` | `(self)` | Skærmen som JPEG-bytes, eller en struktureret fejl-dict. | [src](../../../core/desktop/x_session.py#L270) |
| method | `XSession.input` | `(self, msg)` | Oversæt og kør input. Aldrig exception; ugyldigt input giver fejl-dict. | [src](../../../core/desktop/x_session.py#L289) |
| function | `shared_session` | `()` | Én delt X-session for hele processen. | [src](../../../core/desktop/x_session.py#L310) |

