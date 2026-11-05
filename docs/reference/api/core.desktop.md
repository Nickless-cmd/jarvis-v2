# `core.desktop` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/desktop/__init__.py`
_Jarvis' egen Linux-desktop (Xvfb + window manager) til visning i en fane._

_(no top-level classes or functions)_

## `core/desktop/x_session.py`
_X-session til Jarvis' desktop-fane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `WorkspaceUnavailable` | `` | Brugerens workspace kunne ikke opløses. Der er INTET fallback. | [src](../../../core/desktop/x_session.py#L76) |
| function | `_tildel_display` | `(noegle)` | Et display pr. bruger-nøgle; aldrig delt mellem to nøgler. | [src](../../../core/desktop/x_session.py#L80) |
| function | `sandbox_args` | `(workspace, display)` | bwrap-præfiks: kun workspace (rw), read-only systembiblioteker, eget X-socket. | [src](../../../core/desktop/x_session.py#L103) |
| function | `_navn` | `(p)` | Programnavnet bag en proces, også når den er pakket ind i bwrap. | [src](../../../core/desktop/x_session.py#L131) |
| function | `_fejl` | `(kode, tekst)` | — | [src](../../../core/desktop/x_session.py#L139) |
| function | `_utilgaengelig` | `(tekst)` | — | [src](../../../core/desktop/x_session.py#L143) |
| function | `_tal` | `(v, lo, hi)` | Klem et tal til [lo, hi]; None hvis det ikke er et endeligt tal. | [src](../../../core/desktop/x_session.py#L147) |
| function | `_taste` | `(navn)` | — | [src](../../../core/desktop/x_session.py#L156) |
| function | `bygg_input` | `(msg)` | Ren funktion: input-dict -> liste af xdotool-argumentlister (eller None). | [src](../../../core/desktop/x_session.py#L170) |
| function | `xvfb_args` | `(display=…, bredde=…, hoejde=…)` | Xvfb-kommandoen. | [src](../../../core/desktop/x_session.py#L219) |
| function | `mangler_pakker` | `()` | Navne på manglende binære pakker (tom liste = klar). | [src](../../../core/desktop/x_session.py#L230) |
| class | `XSession` | `` | — | [src](../../../core/desktop/x_session.py#L243) |
| method | `XSession.__init__` | `(self, display=…, bredde=…, hoejde=…, *, workspace=…, privilege=…)` | — | [src](../../../core/desktop/x_session.py#L244) |
| method | `XSession._env` | `(self)` | — | [src](../../../core/desktop/x_session.py#L260) |
| method | `XSession._start_proc` | `(self, args)` | — | [src](../../../core/desktop/x_session.py#L276) |
| method | `XSession.start` | `(self)` | — | [src](../../../core/desktop/x_session.py#L300) |
| method | `XSession._server_svarer` | `(self)` | Svarer X-serveren paa displayet? (ikke bare: findes socket-filen) | [src](../../../core/desktop/x_session.py#L336) |
| method | `XSession._ryd_doede` | `(self)` | Reap børn der er døde, saa de ikke bliver zombier. | [src](../../../core/desktop/x_session.py#L347) |
| method | `XSession._wm_oppe` | `(self)` | Lever window manageren? Uden den bliver nye vinduer aldrig mappet. | [src](../../../core/desktop/x_session.py#L357) |
| method | `XSession._vinduer_for` | `(self, pid)` | Vindues-id'er der tilhoerer processen (tom liste hvis ingen). | [src](../../../core/desktop/x_session.py#L369) |
| method | `XSession._vedligehold` | `(self)` | Hold den delte desktop i live: genstart det der er dødt, fyld det der mangler. | [src](../../../core/desktop/x_session.py#L380) |
| method | `XSession._start_vagt` | `(self)` | Én baggrundstraad der holder sessionen i live. | [src](../../../core/desktop/x_session.py#L402) |
| method | `XSession._vagt_loekke` | `(self)` | — | [src](../../../core/desktop/x_session.py#L411) |
| method | `XSession._ryd_doed_socket` | `(self, sok)` | Fjern resterne af en X-server der ikke svarer, saa vi kan starte en ny. | [src](../../../core/desktop/x_session.py#L421) |
| method | `XSession._fyld_skrivebord` | `(self)` | Saet baggrund, filhaandtering og en terminal paa skrivebordet. | [src](../../../core/desktop/x_session.py#L431) |
| method | `XSession._har_klasse` | `(self, klasse)` | Findes der et vindue med den WM-klasse? (robust mod at titlen aendres) | [src](../../../core/desktop/x_session.py#L454) |
| method | `XSession._sikr_terminal` | `(self)` | Sørg for at der findes en synlig terminal. | [src](../../../core/desktop/x_session.py#L465) |
| method | `XSession._har_vindue` | `(self, moenster)` | Findes der allerede et vindue med navnet? (saa vi ikke starter dubletter) | [src](../../../core/desktop/x_session.py#L494) |
| method | `XSession.stop` | `(self)` | — | [src](../../../core/desktop/x_session.py#L505) |
| method | `XSession.frame` | `(self)` | Skærmen som JPEG-bytes, eller en struktureret fejl-dict. | [src](../../../core/desktop/x_session.py#L519) |
| method | `XSession.cursor` | `(self)` | Hvor staar musemarkoeren? Svar: ``{"status":"ok","x":..,"y":..}``. | [src](../../../core/desktop/x_session.py#L538) |
| method | `XSession.zoom` | `(self, x, y, bredde, hoejde, faktor=…)` | Et UDSNIT af skaermen, skaleret op — til at ramme noget smaat. | [src](../../../core/desktop/x_session.py#L574) |
| method | `XSession.wait` | `(self, timeout_ms=…, interval_ms=…)` | Vent til skaermen ÆNDRER sig, eller tiden løber ud. | [src](../../../core/desktop/x_session.py#L609) |
| method | `XSession.input` | `(self, msg)` | Oversæt og kør input. Aldrig exception; ugyldigt input giver fejl-dict. | [src](../../../core/desktop/x_session.py#L641) |
| function | `_workspace_for` | `(user, privilege)` | Opløs workspace gennem den eksisterende adgangsvej (workspace_paths). | [src](../../../core/desktop/x_session.py#L662) |
| function | `session_for` | `(user, privilege)` | Brugerens EGEN X-session, cachet pr. (rettighed, bruger). | [src](../../../core/desktop/x_session.py#L689) |

