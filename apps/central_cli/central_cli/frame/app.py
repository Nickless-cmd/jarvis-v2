from __future__ import annotations

import asyncio

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Static

from central_cli.engine.state import HudState
from central_cli.engine.workers import SURFACE_CADENCE, fetch_detail, fetch_surface
from central_cli.frame.palette import CommandPalette, resolve_palette_command
from central_cli.frame.table_view import CursorStableTable
from central_cli.hud_theme import BG, CYAN, FGDIM
from central_cli.views import incidents as v_inc
from central_cli.views import nerves as v_nrv
from central_cli.views.overview import render_overview

_TABS = ["overview", "incidents", "nerves"]


class CockpitApp(App):
    CSS = f"""
    Screen {{ background: {BG}; }}
    #tabs {{ height: 1; background: {BG}; color: {FGDIM}; }}
    #body {{ height: 1fr; }}
    CursorStableTable {{ height: 1fr; }}
    #ovpanel {{ height: 1fr; padding: 1 2; }}
    #footer {{ height: 1; color: {FGDIM}; }}
    """
    BINDINGS = [
        Binding("tab", "next_tab", "fane→", show=False),
        Binding("shift+tab", "prev_tab", "←fane", show=False),
        Binding("enter", "drill", "åbn", show=True, priority=True),
        Binding("colon", "palette", "kommando", show=True),
        Binding("ctrl+q", "quit", "afslut", show=False),
    ]

    def __init__(self, *, client, state: HudState | None = None) -> None:
        super().__init__()
        self._client = client
        self._state = state or HudState()
        self._tab = "overview"

    def compose(self) -> ComposeResult:
        yield Static(self._tab_bar(), id="tabs")
        with VerticalScroll(id="body"):
            yield Static(render_overview(self._state), id="ovpanel")
            yield CursorStableTable(*v_inc.INCIDENT_COLUMNS, id="incidents-table")
            yield CursorStableTable(*v_nrv.NERVE_COLUMNS, id="nerves-table")
        yield Static("", id="footer")

    def _tab_bar(self) -> str:
        cells = []
        for t in _TABS:
            cells.append(f"[{CYAN}]{t}[/]" if t == self._tab else f"[{FGDIM}]{t}[/]")
        return "  ".join(cells)

    def on_mount(self) -> None:
        self._show_tab(self._tab)
        for surface in SURFACE_CADENCE:
            self.run_worker(self._poll(surface), exclusive=False, group=f"poll:{surface}")
        self.set_interval(1.0, self.rerender_active)

    async def _poll(self, surface: str) -> None:
        cadence = SURFACE_CADENCE[surface]
        while True:
            await fetch_surface(self._client, self._state, surface)
            self.rerender_active()
            await asyncio.sleep(cadence)

    async def seed_now(self) -> None:
        for surface in SURFACE_CADENCE:
            await fetch_surface(self._client, self._state, surface)
        self.rerender_active()

    async def switch_tab(self, tab: str) -> None:
        self._tab = tab
        self._show_tab(tab)

    def active_table(self):
        if self._tab == "incidents":
            return self.query_one("#incidents-table", CursorStableTable)
        if self._tab == "nerves":
            return self.query_one("#nerves-table", CursorStableTable)
        return None

    def _show_tab(self, tab: str) -> None:
        self.query_one("#ovpanel", Static).display = tab == "overview"
        self.query_one("#incidents-table", CursorStableTable).display = tab == "incidents"
        self.query_one("#nerves-table", CursorStableTable).display = tab == "nerves"
        self.query_one("#tabs", Static).update(self._tab_bar())
        table = self.active_table()
        if table is not None:
            table.focus()
        self.rerender_active()

    def rerender_active(self) -> None:
        try:
            if self._tab == "overview":
                self.query_one("#ovpanel", Static).update(render_overview(self._state))
            elif self._tab == "incidents":
                self.query_one("#incidents-table", CursorStableTable).update_rows(
                    v_inc.build_incident_rows(self._state), key_field="id")
            elif self._tab == "nerves":
                self.query_one("#nerves-table", CursorStableTable).update_rows(
                    v_nrv.build_nerve_rows(self._state), key_field="nerve")
        except Exception as exc:
            try:
                self.query_one("#footer", Static).update(f"[red]render: {exc}[/red]")
            except Exception:
                pass

    def action_next_tab(self) -> None:
        self._tab = _TABS[(_TABS.index(self._tab) + 1) % len(_TABS)]
        self._show_tab(self._tab)

    def action_prev_tab(self) -> None:
        self._tab = _TABS[(_TABS.index(self._tab) - 1) % len(_TABS)]
        self._show_tab(self._tab)

    def action_drill(self) -> None:
        table = self.active_table()
        if table is None or table.row_count == 0:
            return
        key = table._selected_key()
        if self._tab == "incidents":
            for r in v_inc.build_incident_rows(self._state):
                if r["id"] == key:
                    self.push_screen(v_inc.IncidentDetailScreen(r["_raw"]))
                    return
        elif self._tab == "nerves":
            self.run_worker(
                fetch_detail(self._client, self._state,
                             v_nrv.nerve_detail_surface_key(key), v_nrv.nerve_detail_path(key)),
                exclusive=True, group="nerve-detail")
            screen = v_nrv.NerveDetailScreen(key, self._state)
            self.push_screen(screen)

    def action_palette(self) -> None:
        def _run(line):
            if not line:
                return
            spec = resolve_palette_command(line)
            if spec is None:
                self.query_one("#footer", Static).update(f"[red]ukendt: {line}[/red]")
                return
            self.query_one("#footer", Static).update(f"[dim]{line} → {spec.path}[/dim]")
        self.push_screen(CommandPalette(), _run)
