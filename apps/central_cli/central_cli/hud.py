"""Central HUD — J.A.R.V.I.S-style Textual UI, built 1:1 to the mockup.

Layout mirrors ``docs/superpowers/mockups/central-hud-mockup.html`` element for
element: framed HUD · telemetry header (brand · pulsing status · counts · cost ·
connected/latency · clock) · 7-tab nav (active underline, L2 dimmed) · left main
column (pane-header + nerve table + live-feed strip) · right side column (full-
height incident detail with badge/root-cause/related-chips/heal/correlation/
buttons) · command bar (``central>`` + blinking caret + key hints).

Every render/refresh is guarded — a fetch error never crashes the UI. All detail
data is real (joined from realtime + diagnostics + healers via datasource).

This is the thin app-shell. The read-side (table population + detail/panel
rendering) lives in :class:`central_cli.hud_populate._PopulateMixin`; the
action-side (key handlers, command line, writes) in
:class:`central_cli.hud_actions._ActionMixin`; the palette/status-maps/``_esc``
in :mod:`central_cli.hud_theme`. All three are re-exported here so existing
imports (``from central_cli.hud import CentralHud, _TABS, BG, _STATE, _esc``)
keep working unchanged.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from rich.table import Table
from rich.text import Text

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.binding import Binding
from textual.widgets import DataTable, Input, RichLog, Static

from central_cli import datasource

# -- re-export palette / status-maps / _esc (backward-compat) --------------
from central_cli.hud_theme import (  # noqa: F401
    _esc,
    BG, PANEL, LINE, CYAN, AMBER, RED, GREEN, BLUE, DIM, FG, FGDIM, BAR, SPARK,
    _STATE, _DECISION, _IMPORTANCE, _STATUS, _CLUSTER_STATUS, _SEVERITY,
    _AFFECT, _AGENT_STATUS, _RUN_STATUS,
)
from central_cli.hud_populate import _PopulateMixin
from central_cli.hud_actions import _ActionMixin

# tab order: key, label, is_l2
_TABS: list[tuple[str, str, bool]] = [
    ("overview", "Overview", False),
    ("nerves", "Nerves", False),
    ("clusters", "Clusters", False),
    ("incidents", "Incidents", False),
    ("runs", "Runs", False),
    ("approvals", "Approvals", False),
    ("agents", "Agents", False),
    ("connections", "Connections", True),
    ("users", "Users", True),
    ("excess", "Excess", True),
    ("decentral", "Decentral", True),
    ("mind", "Mind", False),
    ("diagnostics", "Diagnostics", False),
    ("governance", "Governance", True),
]

# Table-backed tabs (left main column + nerve-table + side detail). "anomalies"
# is no longer a top-level tab of its own, but its view stays fully reachable
# (its populate/detail logic is unchanged) and folds into the incidents tab as a
# sub-view — so no anomaly functionality is lost.
_TABLE_TABS = {"nerves", "clusters", "incidents", "anomalies", "governance",
               "agents", "runs", "approvals"}
# Panel-backed tabs (single full-width panel). "runs"/"approvals" are now wired
# as real table-tabs (scheduled/autonomy), so they no longer live here.
# "mind" renders Jarvis' self as a panel. "healing" stays reachable as a panel
# sub-view (its render/toggle logic intact).
_PANEL_TABS = {
    "overview", "diagnostics", "healing", "mind",
}


class CentralHud(_PopulateMixin, _ActionMixin, App):
    """The Central HUD app shell (mockup-faithful)."""

    CSS = f"""
    Screen {{ background: #05070b; color: {FG}; }}

    #hud-frame {{
        border: round {CYAN};
        background: {BG};
        height: 1fr;
        margin: 1 2 0 2;
        padding: 0;
    }}

    #hud-head {{
        height: 2;
        background: {BG};
        padding: 0 1;
        border-bottom: solid {LINE};
    }}
    #hud-tabs {{
        height: 2;
        background: {BAR};
        padding: 0 1;
        border-bottom: solid {LINE};
    }}

    #hud-body {{ height: 1fr; }}

    #hud-main {{
        width: 3fr;
        border-right: solid {LINE};
    }}
    #main-paneh {{
        height: 2;
        color: {CYAN};
        background: {BG};
        padding: 0 1;
        border-bottom: solid {LINE};
    }}
    #nerve-table {{
        height: 1fr;
        background: {BG};
        scrollbar-size-vertical: 1;
    }}
    #nerve-table > .datatable--header {{
        background: {BG};
        color: {FGDIM};
        text-style: none;
    }}
    #nerve-table > .datatable--cursor {{
        background: {CYAN} 15%;
    }}
    #feed-paneh {{
        height: 2;
        color: {FGDIM};
        background: {BG};
        padding: 0 1;
        border-top: solid {LINE};
    }}
    #hud-feed {{
        height: 8;
        background: {BG};
        padding: 0 1;
    }}

    #hud-side {{
        width: 48;
        background: {BG};
    }}
    #side-paneh {{
        height: 2;
        color: {CYAN};
        background: {BG};
        padding: 0 1;
        border-bottom: solid {LINE};
    }}
    #hud-detail {{
        height: 1fr;
        background: {BG};
        padding: 1 2;
        overflow-y: auto;
    }}

    #hud-panel {{
        width: 1fr;
        background: {BG};
        padding: 1 2;
        overflow-y: auto;
    }}

    #hud-cmdbar {{
        height: 2;
        background: {BAR};
        border-top: solid {LINE};
        padding: 0 2;
    }}
    #hud-prompt {{
        width: 9;
        height: 1;
        color: {CYAN};
        background: {BAR};
    }}
    #hud-cmd-input {{
        width: 1fr;
        height: 1;
        border: none;
        background: {BAR};
        color: {FG};
        padding: 0;
    }}
    """

    BINDINGS = [
        # Navigation works while the command input stays focused (priority).
        Binding("up", "nav_up", "Op", show=False, priority=True),
        Binding("down", "nav_down", "Ned", show=False, priority=True),
        Binding("pageup", "nav_pageup", show=False, priority=True),
        Binding("pagedown", "nav_pagedown", show=False, priority=True),
        Binding("tab", "next_tab", "Næste fane", show=False, priority=True),
        Binding("shift+tab", "prev_tab", "Forrige fane", show=False, priority=True),
        Binding("escape", "cancel", "Ryd/annullér", show=False, priority=True),
        Binding("ctrl+q", "quit", "Quit", show=False, priority=True),
        # Direct tab jumps via function keys (digits are free for typing).
        # F1-F10 map 1:1 to the ten tabs in _TABS order.
        Binding("f1", "show('overview')", show=False, priority=True),
        Binding("f2", "show('nerves')", show=False, priority=True),
        Binding("f3", "show('clusters')", show=False, priority=True),
        Binding("f4", "show('incidents')", show=False, priority=True),
        Binding("f5", "show('runs')", show=False, priority=True),
        Binding("f6", "show('approvals')", show=False, priority=True),
        Binding("f7", "show('agents')", show=False, priority=True),
        # 6. jul: F-taster matcher nav-numrene (14 faner nu; F1-F12 = de første 12, resten via Tab).
        Binding("f8", "show('connections')", show=False, priority=True),
        Binding("f9", "show('users')", show=False, priority=True),
        Binding("f10", "show('excess')", show=False, priority=True),
        Binding("f11", "show('decentral')", show=False, priority=True),
        Binding("f12", "show('mind')", show=False, priority=True),
    ]

    def __init__(self, *, client: Any = None, live: bool = True) -> None:
        super().__init__()
        self._client = client
        self._live = live
        self.active_tab = "nerves"
        self._overview: dict = {}
        self._affect: dict = {}
        self._tone: dict = {}
        self._incidents: list = []
        self._gov_flags: list = []
        self._healers: dict = {}
        self._pending_write: tuple[str, dict] | None = None
        self._latency_ms: int | None = None
        self._connected: bool = False
        self._cost: float | None = None
        self._costs_daily: dict = {}
        self._sel_incident: int = 0
        self._sel_anomaly: int = 0
        self._anomalies: list = []
        self._nerve_rows: list = []
        self._cluster_rows: list = []
        self._agent_rows: list = []
        self._run_rows: list = []
        self._scheduled: list = []
        self._autonomy: dict = {}
        self._memory_health: dict = {}
        self._events: list = []
        self._council: list = []
        self._pulse_on: bool = True
        self._caret_on: bool = True
        self._cmd_mode: bool = False

    # -- layout ------------------------------------------------------------
    def compose(self) -> ComposeResult:
        with Vertical(id="hud-frame"):
            yield Static(self._render_header(), id="hud-head")
            yield Static(self._render_tabs(), id="hud-tabs")
            with Horizontal(id="hud-body"):
                with Vertical(id="hud-main"):
                    yield Static("", id="main-paneh")
                    yield DataTable(id="nerve-table", zebra_stripes=False)
                    yield Static(
                        Text.from_markup(f"[{FGDIM}]live feed[/] [{DIM}]— deduperet[/]"),
                        id="feed-paneh",
                    )
                    yield RichLog(id="hud-feed", markup=True, highlight=False)
                with Vertical(id="hud-side"):
                    yield Static("", id="side-paneh")
                    yield Static("", id="hud-detail", markup=True)
                yield Static("", id="hud-panel", markup=True)
            with Horizontal(id="hud-cmdbar"):
                yield Static(Text.from_markup(f"[{CYAN} b]central>[/]"), id="hud-prompt")
                yield Input(
                    id="hud-cmd-input",
                    placeholder="skriv kommando · ↑↓ vælg · ↵ drill/kør · ⇥ skift fane · Esc ryd",
                )

    def on_mount(self) -> None:
        table = self.query_one("#nerve-table", DataTable)
        table.cursor_type = "row"
        self._prime()
        self._sync_header()
        self._sync_tabs()
        self._apply_tab_visibility()
        self._populate_active_tab()
        self._render_feed()
        if self._live:
            self.set_interval(3.0, self.refresh_data)
        # pulse the status dot; keep the command input focused (terminal feel)
        self.set_interval(0.8, self._tick_pulse)
        try:
            self.query_one("#hud-cmd-input", Input).focus()
        except Exception:
            pass

    def _prime(self) -> None:
        if self._client is None:
            return
        try:
            start = datetime.now()
            self._overview = datasource.overview(self._client)
            self._latency_ms = int((datetime.now() - start).total_seconds() * 1000)
            self._connected = True
        except Exception:
            self._connected = False
        try:
            self._cost = datasource.cost_today(self._client)
        except Exception:
            self._cost = None
        try:
            self._costs_daily = datasource.costs_daily(self._client)
        except Exception:
            self._costs_daily = {}
        try:
            self._affect = datasource.affect(self._client)
        except Exception:
            self._affect = {}
        try:
            self._tone = datasource.tone(self._client)
        except Exception:
            self._tone = {}

    # -- animation ticks ---------------------------------------------------
    def _tick_pulse(self) -> None:
        self._pulse_on = not self._pulse_on
        self._sync_header()

    def _keep_focus(self) -> None:
        try:
            inp = self.query_one("#hud-cmd-input", Input)
            if self.focused is not inp:
                inp.focus()
        except Exception:
            pass

    def show_tab(self, name: str) -> None:
        self.active_tab = name
        self._sync_tabs()
        self._apply_tab_visibility()
        self._populate_active_tab()

    def _apply_tab_visibility(self) -> None:
        table_visible = self.active_tab in _TABLE_TABS
        for wid, vis in (
            ("#hud-main", table_visible),
            ("#hud-side", table_visible),
            ("#hud-panel", not table_visible),
        ):
            try:
                self.query_one(wid).display = vis
            except Exception:
                pass

    def _populate_active_tab(self) -> None:
        try:
            name = self.active_tab
            if name == "nerves":
                self._populate_nerves()
                self._refresh_detail_for_current()
                self._render_feed()
            elif name == "clusters":
                self._populate_clusters()
                self._refresh_detail_for_current()
            elif name == "incidents":
                self._populate_incidents()
                self._refresh_detail_for_current()
            elif name == "anomalies":
                self._populate_anomalies()
                self._refresh_detail_for_current()
            elif name == "governance":
                self._populate_governance()
                self._refresh_detail_for_current()
            elif name == "agents":
                self._populate_agents()
                self._refresh_detail_for_current()
            elif name == "connections":
                self._populate_connections()
            elif name == "users":
                self._populate_users()
            elif name == "excess":
                self._populate_excess()
            elif name == "decentral":
                self._populate_decentral()
            elif name == "overview":
                self._render_overview_panel()
            elif name == "diagnostics":
                self._render_diagnostics_panel()
            elif name == "healing":
                self._render_healing_panel()
            elif name == "mind":
                self._render_mind_self_panel()
            elif name == "runs":
                self._populate_runs()
                self._refresh_detail_for_current()
            elif name == "approvals":
                self._populate_approvals()
            else:
                self._render_placeholder_panel(name)
        except Exception:
            return

    # -- refresh -----------------------------------------------------------
    def refresh_data(self) -> None:
        if self._client is None:
            return
        try:
            start = datetime.now()
            self._overview = datasource.overview(self._client)
            self._latency_ms = int((datetime.now() - start).total_seconds() * 1000)
            self._connected = True
        except Exception:
            self._connected = False
            self._sync_header()
            return
        try:
            self._cost = datasource.cost_today(self._client)
        except Exception:
            pass
        try:
            self._costs_daily = datasource.costs_daily(self._client)
        except Exception:
            pass
        try:
            self._affect = datasource.affect(self._client)
        except Exception:
            pass
        try:
            self._tone = datasource.tone(self._client)
        except Exception:
            pass
        self._sync_header()
        self._populate_active_tab()

    # -- header ------------------------------------------------------------
    def _render_header(self) -> Table:
        ov = self._overview or {}
        status = str(ov.get("status", "unknown")).lower()
        s_color, s_label = _STATUS.get(status, (DIM, status.upper() or "UKENDT"))
        nerves = ov.get("nerves", 0)
        clusters = ov.get("clusters", 0)
        incidents = ov.get("incidents", 0)
        breakers = ov.get("breakers", 0)
        inc_color = RED if incidents else FG
        dot = "●" if self._pulse_on else "◍"
        cost = f"[{FGDIM}]cost i dag[/] [{FG} b]${self._cost:.2f}[/]" if self._cost is not None else ""
        conn_color, conn_label = (GREEN, "CONNECTED") if self._connected else (RED, "OFFLINE")
        lat = f" [{FGDIM}]· {self._latency_ms}ms[/]" if self._latency_ms is not None else ""
        clock = datetime.now().strftime("%H:%M:%S")

        left = (
            f"[{CYAN} b]◈ CENTRAL[/] [{FGDIM}]· J.A.R.V.I.S CLI v1.0[/]  "
            f"[{s_color}]{dot}[/] [{s_color} b]{s_label}[/]  "
            f"[{FGDIM}]nerver[/] [{FG} b]{nerves}[/] [{DIM}]·[/] "
            f"[{FGDIM}]clusters[/] [{FG} b]{clusters}[/] [{DIM}]·[/] "
            f"[{FGDIM}]incidents[/] [{inc_color} b]{incidents}[/] [{DIM}]·[/] "
            f"[{FGDIM}]breakers[/] [{FG} b]{breakers}[/]"
        )
        cost_sp = f"{cost}  " if cost else ""
        right = (
            f"{cost_sp}[{conn_color}]●[/] [{FGDIM}]{conn_label}{lat}[/]  "
            f"[{FGDIM}]{clock}[/]"
        )
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="right")
        grid.add_row(Text.from_markup(left), Text.from_markup(right))
        return grid

    def _render_tabs(self) -> Text:
        parts = []
        for idx, (key, label, l2) in enumerate(_TABS, start=1):
            if key == self.active_tab:
                parts.append(f"[{DIM}]{idx}[/] [{CYAN} b u]{label}[/]")
            elif l2:
                parts.append(f"[{DIM}]{idx}[/] [#3a4658]{label}[/]")
            else:
                parts.append(f"[{DIM}]{idx}[/] [{FGDIM}]{label}[/]")
        return Text.from_markup("    ".join(parts))

    def _render_cmd(self) -> Text:
        caret = "█" if self._caret_on else " "
        keys = (
            f"[{FGDIM} b]F1-F10[/] [{DIM}]views ·[/] [{FGDIM} b]↑↓[/] [{DIM}]naviger ·[/] "
            f"[{FGDIM} b]↵[/] [{DIM}]drill ·[/] [{FGDIM} b]t[/] [{DIM}]toggle ·[/] "
            f"[{FGDIM} b]:[/] [{DIM}]kommando ·[/] [{FGDIM} b]?[/] [{DIM}]hjælp ·[/] "
            f"[{FGDIM} b]q[/] [{DIM}]quit[/]"
        )
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="right")
        grid.add_row(
            Text.from_markup(f"[{CYAN}]central>[/][{CYAN}]{caret}[/]"),
            Text.from_markup(keys),
        )
        return grid


def run_hud(ns) -> int:
    import os
    from central_cli.client import CentralClient
    from central_cli.config import resolve_base_url, resolve_token

    client = CentralClient(base_url=resolve_base_url(remote=ns.remote), token=resolve_token())
    use_v2 = getattr(ns, "v2", False) or os.environ.get("CENTRAL_COCKPIT_V2") == "1"
    if use_v2:
        from central_cli.frame.app import CockpitApp
        CockpitApp(client=client).run()
        return 0
    CentralHud(client=client, live=True).run()
    return 0
