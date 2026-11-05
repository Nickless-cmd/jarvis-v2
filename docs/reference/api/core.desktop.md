# `core.desktop` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/desktop/__init__.py`
_Jarvis' egen Linux-desktop (Xvfb + window manager) til visning i en fane._

_(no top-level classes or functions)_

## `core/desktop/x_session.py`
_X-session til Jarvis' desktop-fane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_fejl` | `(kode, tekst)` | — | [src](../../../core/desktop/x_session.py#L46) |
| function | `_utilgaengelig` | `(tekst)` | — | [src](../../../core/desktop/x_session.py#L50) |
| function | `_tal` | `(v, lo, hi)` | Klem et tal til [lo, hi]; None hvis det ikke er et endeligt tal. | [src](../../../core/desktop/x_session.py#L54) |
| function | `_taste` | `(navn)` | — | [src](../../../core/desktop/x_session.py#L63) |
| function | `bygg_input` | `(msg)` | Ren funktion: input-dict -> liste af xdotool-argumentlister (eller None). | [src](../../../core/desktop/x_session.py#L77) |
| function | `xvfb_args` | `(display=…, bredde=…, hoejde=…)` | Xvfb-kommandoen. | [src](../../../core/desktop/x_session.py#L126) |
| function | `mangler_pakker` | `()` | Navne på manglende binære pakker (tom liste = klar). | [src](../../../core/desktop/x_session.py#L137) |
| class | `XSession` | `` | — | [src](../../../core/desktop/x_session.py#L150) |
| method | `XSession.__init__` | `(self, display=…, bredde=…, hoejde=…)` | — | [src](../../../core/desktop/x_session.py#L151) |
| method | `XSession._env` | `(self)` | — | [src](../../../core/desktop/x_session.py#L162) |
| method | `XSession._start_proc` | `(self, args)` | — | [src](../../../core/desktop/x_session.py#L178) |
| method | `XSession.start` | `(self)` | — | [src](../../../core/desktop/x_session.py#L190) |
| method | `XSession._server_svarer` | `(self)` | Svarer X-serveren paa displayet? (ikke bare: findes socket-filen) | [src](../../../core/desktop/x_session.py#L226) |
| method | `XSession._ryd_doede` | `(self)` | Reap børn der er døde, saa de ikke bliver zombier. | [src](../../../core/desktop/x_session.py#L237) |
| method | `XSession._wm_oppe` | `(self)` | Lever window manageren? Uden den bliver nye vinduer aldrig mappet. | [src](../../../core/desktop/x_session.py#L247) |
| method | `XSession._vinduer_for` | `(self, pid)` | Vindues-id'er der tilhoerer processen (tom liste hvis ingen). | [src](../../../core/desktop/x_session.py#L259) |
| method | `XSession._vedligehold` | `(self)` | Hold den delte desktop i live: genstart det der er dødt, fyld det der mangler. | [src](../../../core/desktop/x_session.py#L270) |
| method | `XSession._start_vagt` | `(self)` | Én baggrundstraad der holder sessionen i live. | [src](../../../core/desktop/x_session.py#L292) |
| method | `XSession._vagt_loekke` | `(self)` | — | [src](../../../core/desktop/x_session.py#L301) |
| method | `XSession._ryd_doed_socket` | `(self, sok)` | Fjern resterne af en X-server der ikke svarer, saa vi kan starte en ny. | [src](../../../core/desktop/x_session.py#L311) |
| method | `XSession._fyld_skrivebord` | `(self)` | Saet baggrund, filhaandtering og en terminal paa skrivebordet. | [src](../../../core/desktop/x_session.py#L321) |
| method | `XSession._har_klasse` | `(self, klasse)` | Findes der et vindue med den WM-klasse? (robust mod at titlen aendres) | [src](../../../core/desktop/x_session.py#L344) |
| method | `XSession._sikr_terminal` | `(self)` | Sørg for at der findes en synlig terminal. | [src](../../../core/desktop/x_session.py#L355) |
| method | `XSession._har_vindue` | `(self, moenster)` | Findes der allerede et vindue med navnet? (saa vi ikke starter dubletter) | [src](../../../core/desktop/x_session.py#L384) |
| method | `XSession.stop` | `(self)` | — | [src](../../../core/desktop/x_session.py#L395) |
| method | `XSession.frame` | `(self)` | Skærmen som JPEG-bytes, eller en struktureret fejl-dict. | [src](../../../core/desktop/x_session.py#L409) |
| method | `XSession.input` | `(self, msg)` | Oversæt og kør input. Aldrig exception; ugyldigt input giver fejl-dict. | [src](../../../core/desktop/x_session.py#L428) |
| function | `shared_session` | `()` | Én delt X-session for hele processen. | [src](../../../core/desktop/x_session.py#L449) |

