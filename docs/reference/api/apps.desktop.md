# `apps.desktop` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `apps/desktop/orb.py`
_Jarvis desktop orb widget — frameless, always-on-top, live voice state._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `read_phase` | `()` | Læs voice-fasen fra PHASE_FILE; returnér 'idle' hvis filen mangler eller er ugyldig. | [src](../../../apps/desktop/orb.py#L19) |
| class | `DragHandle` | `` | Thin strip at top that lets user drag the frameless window. | [src](../../../apps/desktop/orb.py#L28) |
| method | `DragHandle.__init__` | `(self, window)` | — | [src](../../../apps/desktop/orb.py#L31) |
| method | `DragHandle.mousePressEvent` | `(self, event)` | Gem musens offset ift. vinduets top-venstre hjørne ved venstreklik (start på træk). | [src](../../../apps/desktop/orb.py#L45) |
| method | `DragHandle.mouseMoveEvent` | `(self, event)` | Flyt vinduet så det følger musen under et venstre-knap-træk. | [src](../../../apps/desktop/orb.py#L50) |
| method | `DragHandle.mouseReleaseEvent` | `(self, event)` | Nulstil træk-tilstanden når museknappen slippes. | [src](../../../apps/desktop/orb.py#L55) |
| function | `poll_phase` | `()` | Læs den aktuelle fase; hvis den er ændret, opdatér orb'en via JavaScript set(phase). | [src](../../../apps/desktop/orb.py#L87) |
| function | `on_load_finished` | `(ok)` | Ved vellykket sideindlæsning: stop demo-cyklus, sæt 'idle' og start 800ms fase-polling-timer. | [src](../../../apps/desktop/orb.py#L96) |

