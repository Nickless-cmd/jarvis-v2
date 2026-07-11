from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input

from central_cli.commands import KNOWN_VERBS, resolve_command


def resolve_palette_command(line: str):
    """Slå en kommando-linje op i den eksisterende dispatch. None hvis ukendt.

    Dispatchen har en catch-all der router ethvert verbum til /central/command;
    palette afviser derfor verber der ikke er eksplicit kendte (KNOWN_VERBS),
    så vrøvl-input ikke fejl-fyrer terminal-parseren.
    """
    line = (line or "").strip()
    if not line:
        return None
    parts = line.split()
    if parts[0] not in KNOWN_VERBS:
        return None
    try:
        return resolve_command(parts[0], parts[1:])
    except Exception:
        return None


class CommandPalette(ModalScreen[str | None]):
    """':' åbner denne. Enter → returnér kommando-linjen; Esc → None."""

    BINDINGS = [Binding("escape", "dismiss_none", "annullér")]

    def compose(self) -> ComposeResult:
        with Vertical(id="palette-box"):
            yield Input(placeholder=": kommando (fx status, resolve, nerve <navn>)",
                        id="palette-input")

    def on_mount(self) -> None:
        self.query_one("#palette-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip() or None)

    def action_dismiss_none(self) -> None:
        self.dismiss(None)
