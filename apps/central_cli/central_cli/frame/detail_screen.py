from __future__ import annotations

from rich.console import RenderableType
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

from central_cli.hud_theme import CYAN, DIM


class DetailScreen(Screen):
    """Base for drill-down. Fuld bredde, scrollbar body, brødkrumme, Esc popper.
    Subklasser overrider `title_crumb()` og `body_renderable()`."""

    BINDINGS = [Binding("escape", "app.pop_screen", "tilbage", show=True)]

    def title_crumb(self) -> str:
        return "Central ▸ detalje"

    def body_renderable(self) -> RenderableType:
        return "(tom)"

    def compose(self) -> ComposeResult:
        yield Static(
            f"[{CYAN}]{self.title_crumb()}[/]  [{DIM}]— esc: tilbage[/]",
            id="crumb",
        )
        with VerticalScroll(id="detail-body"):
            yield Static(self.body_renderable(), id="detail-content")

    def refresh_body(self) -> None:
        try:
            self.query_one("#detail-content", Static).update(self.body_renderable())
            self.query_one("#crumb", Static).update(
                f"[{CYAN}]{self.title_crumb()}[/]  [{DIM}]— esc: tilbage[/]"
            )
        except Exception:  # skærmen kan være poppet imens
            pass
