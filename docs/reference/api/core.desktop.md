# `core.desktop` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/desktop/__init__.py`
_Jarvis' egen Linux-desktop (Xvfb + window manager) til visning i en fane._

_(no top-level classes or functions)_

## `core/desktop/x_session.py`
_X-session til Jarvis' desktop-fane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_fejl` | `(kode, tekst)` | — | [src](../../../core/desktop/x_session.py#L35) |
| function | `_utilgaengelig` | `(tekst)` | — | [src](../../../core/desktop/x_session.py#L39) |
| function | `_tal` | `(v, lo, hi)` | Klem et tal til [lo, hi]; None hvis det ikke er et endeligt tal. | [src](../../../core/desktop/x_session.py#L43) |
| function | `_taste` | `(navn)` | — | [src](../../../core/desktop/x_session.py#L52) |
| function | `bygg_input` | `(msg)` | Ren funktion: input-dict -> liste af xdotool-argumentlister (eller None). | [src](../../../core/desktop/x_session.py#L66) |
| function | `mangler_pakker` | `()` | Navne på manglende binære pakker (tom liste = klar). | [src](../../../core/desktop/x_session.py#L115) |
| class | `XSession` | `` | — | [src](../../../core/desktop/x_session.py#L128) |
| method | `XSession.__init__` | `(self, display=…, bredde=…, hoejde=…)` | — | [src](../../../core/desktop/x_session.py#L129) |
| method | `XSession._env` | `(self)` | — | [src](../../../core/desktop/x_session.py#L137) |
| method | `XSession._start_proc` | `(self, args)` | — | [src](../../../core/desktop/x_session.py#L154) |
| method | `XSession.start` | `(self)` | — | [src](../../../core/desktop/x_session.py#L161) |
| method | `XSession.stop` | `(self)` | — | [src](../../../core/desktop/x_session.py#L189) |
| method | `XSession.frame` | `(self)` | Skærmen som JPEG-bytes, eller en struktureret fejl-dict. | [src](../../../core/desktop/x_session.py#L201) |
| method | `XSession.input` | `(self, msg)` | Oversæt og kør input. Aldrig exception; ugyldigt input giver fejl-dict. | [src](../../../core/desktop/x_session.py#L220) |

