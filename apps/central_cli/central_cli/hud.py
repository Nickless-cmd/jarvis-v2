"""Central HUD — J.A.R.V.I.S-style Textual UI, built 1:1 to the mockup.

Layout mirrors ``docs/superpowers/mockups/central-hud-mockup.html`` element for
element: framed HUD · telemetry header (brand · pulsing status · counts · cost ·
connected/latency · clock) · 7-tab nav (active underline, L2 dimmed) · left main
column (pane-header + nerve table + live-feed strip) · right side column (full-
height incident detail with badge/root-cause/related-chips/heal/correlation/
buttons) · command bar (``central>`` + blinking caret + key hints).

Every render/refresh is guarded — a fetch error never crashes the UI. All detail
data is real (joined from realtime + diagnostics + healers via datasource).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from rich.markup import escape as _rescape
from rich.table import Table
from rich.text import Text


def _esc(value: Any) -> str:
    """Escape live/user data before it goes into a Rich-markup string, so a
    value containing '[...]' (asyncio tasks, paths, log lines) can never be
    mis-parsed as a style tag and crash the render."""
    return _rescape(str(value if value is not None else ""))
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.binding import Binding
from textual.widgets import DataTable, Input, RichLog, Static

from central_cli import datasource

# --- palette (mockup :root — exact) --------------------------------------
BG = "#0a0e14"
PANEL = "#0d1420"
LINE = "#16324a"
CYAN = "#00d4ff"
AMBER = "#ffb000"
RED = "#ff4a4a"
GREEN = "#00ff88"
BLUE = "#4488ff"
DIM = "#4a5568"
FG = "#c7d3e0"
FGDIM = "#7b8a9c"
BAR = "#080c12"       # tabs/cmd background
SPARK = "#4a5568"     # dim spark

# state -> (color, glyph label)
_STATE = {
    "aktiv": (GREEN, "● aktiv"),
    "idle": (DIM, "○ idle"),
    "degraded": (AMBER, "◆ degraded"),
    "død": (RED, "✖ død"),
}

# feed decision -> color
_DECISION = {
    "error": RED, "critical": RED, "red": RED, "deny": RED, "block": RED,
    "warn": AMBER, "warning": AMBER, "yellow": AMBER,
    "success": GREEN, "observe": GREEN, "green": GREEN, "allow": GREEN, "ok": GREEN,
}

# tab order: key, label, is_l2
_TABS: list[tuple[str, str, bool]] = [
    ("overview", "Overview", False),
    ("nerves", "Nerves", False),
    ("clusters", "Clusters", False),
    ("incidents", "Incidents", False),
    ("runs", "Runs", False),
    ("approvals", "Approvals", False),
    ("agents", "Agents", False),
    ("mind", "Mind", False),
    ("diagnostics", "Diagnostics", False),
    ("governance", "Governance", True),
]

# anomaly importance -> color
_IMPORTANCE = {
    "high": RED, "critical": RED, "severe": RED,
    "medium": AMBER, "low": DIM, "info": CYAN,
}

# status-word -> (color, label)
_STATUS = {
    "green": (GREEN, "GRØN"),
    "yellow": (AMBER, "GUL"),
    "red": (RED, "RØD"),
}
_CLUSTER_STATUS = {"green": GREEN, "yellow": AMBER, "red": RED, "idle": DIM}
_SEVERITY = {
    "severe": RED, "critical": RED, "error": RED,
    "warn": AMBER, "warning": AMBER, "info": CYAN,
}

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

# agent status -> color
_AGENT_STATUS = {
    "running": GREEN, "active": GREEN, "live": GREEN,
    "idle": DIM, "pending": DIM, "queued": DIM,
    "done": BLUE, "completed": BLUE, "finished": BLUE,
    "error": RED, "failed": RED, "dead": RED,
}


class CentralHud(App):
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
        Binding("f8", "show('mind')", show=False, priority=True),
        Binding("f9", "show('diagnostics')", show=False, priority=True),
        Binding("f10", "show('governance')", show=False, priority=True),
    ]

    def __init__(self, *, client: Any = None, live: bool = True) -> None:
        super().__init__()
        self._client = client
        self._live = live
        self.active_tab = "nerves"
        self._overview: dict = {}
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

    # -- actions -----------------------------------------------------------
    def action_show(self, name: str) -> None:
        self.show_tab(name)

    def action_help(self) -> None:
        return

    # -- navigation (works while the input stays focused) ------------------
    def _table(self) -> DataTable | None:
        if self.active_tab not in _TABLE_TABS:
            return None
        try:
            return self.query_one("#nerve-table", DataTable)
        except Exception:
            return None

    def _refresh_detail_for_current(self) -> None:
        """Render the detail panel for whichever row the cursor is on (used after
        a populate/refresh so the side panel reflects the selection, not incidents)."""
        t = self._table()
        row = 0
        if t is not None:
            try:
                row = int(t.cursor_row or 0)
            except Exception:
                row = 0
        self._render_row_detail(row)

    def _after_cursor_move(self, t: DataTable) -> None:
        """Refresh the detail panel for the newly-selected row (robust — does not
        rely on the RowHighlighted event firing from a programmatic cursor move)."""
        try:
            self._render_row_detail(int(t.cursor_row or 0))
        except Exception:
            pass

    def action_nav_up(self) -> None:
        t = self._table()
        if t is not None:
            t.action_cursor_up()
            self._after_cursor_move(t)

    def action_nav_down(self) -> None:
        t = self._table()
        if t is not None:
            t.action_cursor_down()
            self._after_cursor_move(t)

    def action_nav_pageup(self) -> None:
        t = self._table()
        if t is not None:
            t.action_page_up()
            self._after_cursor_move(t)

    def action_nav_pagedown(self) -> None:
        t = self._table()
        if t is not None:
            t.action_page_down()
            self._after_cursor_move(t)

    def _cycle_tab(self, step: int) -> None:
        keys = [k for k, _, _ in _TABS]
        try:
            i = keys.index(self.active_tab)
        except ValueError:
            i = 0
        self.show_tab(keys[(i + step) % len(keys)])

    def action_next_tab(self) -> None:
        self._cycle_tab(1)

    def action_prev_tab(self) -> None:
        self._cycle_tab(-1)

    def action_cancel(self) -> None:
        """Esc: clear a half-typed command, else cancel a pending confirm."""
        try:
            inp = self.query_one("#hud-cmd-input", Input)
        except Exception:
            inp = None
        if inp is not None and inp.value:
            inp.value = ""
            return
        if self._pending_write is not None:
            self.action_confirm_no()

    # -- command line (always-on terminal prompt) --------------------------
    def on_input_submitted(self, event: Input.Submitted) -> None:  # noqa: ANN001
        val = (event.value or "").strip()
        try:
            self.query_one("#hud-cmd-input", Input).value = ""
        except Exception:
            pass
        # A pending dangerous confirm: y/yes/enter = confirm, n/no = cancel.
        if self._pending_write is not None:
            low = val.lower()
            if val == "" or low in ("y", "yes", "j", "ja"):
                self.action_confirm_yes()
            elif low in ("n", "no", "nej"):
                self.action_confirm_no()
            self._keep_focus()
            return
        if val == "":
            # Empty Enter = drill/select the current row.
            t = self._table()
            if t is not None:
                self._drill_row(int(t.cursor_row or 0))
            self._keep_focus()
            return
        self._run_command(val)
        self._keep_focus()

    def _run_command(self, line: str) -> None:
        """Parse + execute a command via the shared resolve_command layer.
        Read results render FULLY into the detail panel; writes flash in the feed."""
        parts = line.split()
        verb, args = parts[0].lower(), parts[1:]
        try:
            from central_cli.commands import resolve_command
            spec = resolve_command(verb, args)
        except Exception as exc:
            self._flash(f"[{RED}]✖ {verb}: {_esc(str(exc))}[/]")
            return
        try:
            if spec.method == "GET":
                data = self._client.get_json(spec.path, spec.body)
            else:
                data = self._client.post_json(spec.path, spec.body or {})
        except Exception as exc:
            self._flash(f"[{RED}]✖ {_esc(line)}: {_esc(str(exc))}[/]")
            return
        if spec.method == "GET":
            # read: render the full result and DON'T refresh (would clobber it)
            if verb == "feel":
                self._show_feel(data)
            else:
                self._show_command_output(line, data)
        else:
            ok = isinstance(data, dict) and data.get("ok")
            tail = f"[{GREEN}]ok[/]" if ok else f"[{RED}]{_esc(str((data or {}).get('error', data)))[:80]}[/]"
            self._flash(f"[{CYAN}]▸ {_esc(line)}[/] [{DIM}]—[/] {tail}")
            self.refresh_data()

    def _show_feel(self, data: Any) -> None:
        """Render Jarvis' somatic snapshot as his own voice in the detail panel."""
        try:
            panel = self.query_one("#hud-detail", Static)
        except Exception:
            return
        lines = (data or {}).get("lines") or [] if isinstance(data, dict) else []
        self._set_side_paneh(f"[{CYAN}]JARVIS FØLER[/] [{DIM}]— somatisk snapshot[/]")
        if not lines:
            panel.update(Text.from_markup(f"[{FGDIM}]— stille indeni lige nu —[/]"))
        else:
            out = [f"[{GREEN} b]◈ INDRE LIV[/]", ""]
            for ln in lines:
                out.append(f"[{DIM}]·[/] [{FG}]{_esc(ln)}[/]")
                out.append("")
            panel.update(Text.from_markup("\n".join(out)))
        try:
            self.query_one("#hud-panel", Static).display = False
            self.query_one("#hud-side").display = True
        except Exception:
            pass

    def _show_command_output(self, line: str, data: Any) -> None:
        """Render a read command's FULL result into the detail panel (scrollable)."""
        import json
        try:
            panel = self.query_one("#hud-detail", Static)
        except Exception:
            return
        self._set_side_paneh(f"[{CYAN}]KOMMANDO[/] [{DIM}]— {_esc(line)}[/]")
        try:
            pretty = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)
        except Exception:
            pretty = str(data)
        body = "\n".join(_esc(ln) for ln in pretty.splitlines()[:400])
        panel.update(Text.from_markup(f"[{FG}]{body}[/]"))
        # ensure the detail panel is the visible one
        try:
            self.query_one("#hud-panel", Static).display = False
            self.query_one("#hud-side").display = True
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

    def _sync_header(self) -> None:
        try:
            self.query_one("#hud-head", Static).update(self._render_header())
        except Exception:
            pass

    def _sync_tabs(self) -> None:
        try:
            self.query_one("#hud-tabs", Static).update(self._render_tabs())
        except Exception:
            pass

    def _set_paneh(self, text: str) -> None:
        try:
            self.query_one("#main-paneh", Static).update(Text.from_markup(text))
        except Exception:
            pass

    def _set_side_paneh(self, text: str) -> None:
        try:
            self.query_one("#side-paneh", Static).update(Text.from_markup(text))
        except Exception:
            pass

    def _reset_columns(self, table: DataTable, *cols: tuple[str, int]) -> None:
        table.clear(columns=True)
        for label, width in cols:
            table.add_column(label, width=width)

    # -- Nerves ------------------------------------------------------------
    def _populate_nerves(self) -> None:
        try:
            table = self.query_one("#nerve-table", DataTable)
        except Exception:
            return
        self._reset_columns(table, ("cluster", 15), ("nerve", 22), ("state", 15),
                            ("sidste", 8), ("count", 6), ("aktivitet", 18))
        if self._client is None:
            return
        try:
            rows = datasource.nerves(self._client)
        except Exception:
            return
        self._nerve_rows = rows
        self._set_paneh(
            f"[{CYAN}]NERVES[/] [{FGDIM}]— {len(rows)} i alt · filter: [/]"
            f"[{CYAN}]/[/] [{FGDIM}]· sortér: state[/]"
        )
        for r in rows:
            state = str(r.get("state", ""))
            color, glyph = _STATE.get(state, (FG, state))
            if state == "død" and str(r.get("severity", "")) in ("error", "severe", "critical"):
                glyph = "✖ død · error"
            table.add_row(
                Text(str(r.get("cluster", "")), style=FGDIM),
                Text(str(r.get("nerve", "")), style=FG),
                Text(glyph, style=color),
                Text(self._rel_age(r.get("last", "")), style=FGDIM),
                Text(str(r.get("count", 0)), style=FGDIM, justify="right"),
                Text(str(r.get("spark", "")), style=SPARK),
            )

    def _render_feed(self) -> None:
        try:
            log = self.query_one("#hud-feed", RichLog)
        except Exception:
            return
        if self._client is None:
            return
        try:
            rows = datasource.feed(self._client)
        except Exception:
            return
        log.clear()
        for r in rows:
            decision = str(r.get("decision", ""))
            color = _DECISION.get(decision, DIM)
            count = int(r.get("count", 1) or 1)
            badge = f" [{FGDIM}]×{count} · seneste[/]" if count > 1 else ""
            cluster = _esc(r.get("cluster", ""))
            nerve = _esc(r.get("nerve", ""))
            reason = _esc(r.get("reason", ""))
            sep = f" [{DIM}]—[/] {reason}" if reason else ""
            log.write(
                f"[{color}]●[/] [{color}]{cluster}/{nerve}[/] "
                f"[{DIM}]·[/] {_esc(decision)}{badge}{sep}"
            )

    # -- detail panel (side, full height) ----------------------------------
    def _detail_incident(self) -> dict | None:
        if self.active_tab == "incidents" and self._incidents:
            i = max(0, min(self._sel_incident, len(self._incidents) - 1))
            return self._incidents[i]
        top = (self._overview or {}).get("top_incidents") or []
        return top[0] if top else None

    def _render_detail_panel(self) -> None:
        try:
            panel = self.query_one("#hud-detail", Static)
        except Exception:
            return
        inc = self._detail_incident()
        if not inc:
            self._set_side_paneh(f"[{CYAN}]INCIDENT-DETALJE[/] [{DIM}]— —[/]")
            panel.update(Text.from_markup(
                f"[{GREEN} b]◈ ALT ROLIGT[/]\n\n"
                f"[{FGDIM}]Ingen aktive incidents.[/]\n"
                f"[{FGDIM}]Detaljer vises her når noget kræver opmærksomhed.[/]"
            ))
            return
        try:
            d = datasource.incident_detail(self._client, inc)
        except Exception:
            d = dict(inc)

        sev = str(d.get("severity", "") or "—")
        color = _SEVERITY.get(sev, FG)
        cluster = d.get("cluster", "")
        nerve = d.get("nerve", "")
        self._set_side_paneh(
            f"[{CYAN}]INCIDENT-DETALJE[/] [{DIM}]— {_esc(cluster)}/{_esc(nerve)}[/]"
        )

        def _cap(text: Any, n: int) -> str:
            s = str(text or "").replace("\n", " ")
            return s if len(s) <= n else s[: n - 1] + "…"

        # bordered badge (terminal idiom: bg-tinted pill)
        badge_bg = "#1f0d0d" if color == RED else ("#241a05" if color == AMBER else "#06202e")
        lines = [
            f"[{color} b on {badge_bg}] ● {_esc(sev.upper())} · {_esc(cluster)} [/]",
            "",
            f"[{FG} b]{_esc(d.get('title') or nerve)}[/]",
            f"[{FGDIM}]{_esc(_cap(d.get('message', ''), 130))}[/]",
        ]
        rc = d.get("root_cause")
        if rc:
            lines += ["", f"[{FGDIM} b]ROOT CAUSE[/]", f"[{FG}]{_esc(_cap(rc, 130))}[/]"]
        related = d.get("related") or []
        if related:
            chips = "".join(f"[{FGDIM} on #0f1824] {_esc(r)} [/] " for r in related)
            lines += ["", f"[{FGDIM} b]RELATEREDE NERVER[/]", chips]
        heal = d.get("heal_status")
        if heal:
            lines += ["", f"[{FGDIM} b]HEAL-STATUS[/]", f"[{GREEN}]◈ {_esc(_cap(heal, 130))}[/]"]
        corr = d.get("correlation") or {}
        if corr:
            first = str(corr.get("first", ""))[:10]
            last = str(corr.get("last", ""))[:10]
            lines += [
                "",
                f"[{FGDIM} b]CORRELATION[/]",
                f"[{FGDIM}]#{corr.get('sig', '')} · {corr.get('count', 0)} "
                f"forekomster · {first}→{last}[/]",
            ]
        lines += [
            "",
            f"[{CYAN} on #06202e] ↵ fuld diagnostik [/]  [{AMBER} on #241a05] r resolve [/]",
        ]
        panel.update(Text.from_markup("\n".join(lines)))

    # -- Clusters ----------------------------------------------------------
    def _populate_clusters(self) -> None:
        try:
            table = self.query_one("#nerve-table", DataTable)
        except Exception:
            return
        self._reset_columns(table, ("cluster", 18), ("status", 12), ("nerver", 8),
                            ("aktiv", 7), ("idle", 7), ("degraded", 10), ("død", 6))
        if self._client is None:
            return
        try:
            rows = datasource.clusters(self._client)
        except Exception:
            return
        self._cluster_rows = rows
        self._set_paneh(f"[{CYAN}]CLUSTERS[/] [{FGDIM}]— {len(rows)} i alt[/]")
        for r in rows:
            status = str(r.get("status", ""))
            color = _CLUSTER_STATUS.get(status, FG)
            table.add_row(
                Text(str(r.get("cluster", "")), style=FG),
                Text(f"● {status}", style=color),
                Text(str(r.get("nerves", 0)), style=FGDIM),
                Text(str(r.get("aktiv", 0)), style=GREEN),
                Text(str(r.get("idle", 0)), style=DIM),
                Text(str(r.get("degraded", 0)), style=AMBER),
                Text(str(r.get("død", 0)), style=RED),
            )

    # -- Incidents ---------------------------------------------------------
    def _populate_incidents(self) -> None:
        try:
            table = self.query_one("#nerve-table", DataTable)
        except Exception:
            return
        self._reset_columns(table, ("sev", 9), ("cluster/nerve", 26), ("besked", 40))
        if self._client is None:
            return
        try:
            self._incidents = datasource.incidents(self._client)
        except Exception:
            self._incidents = []
        self._set_paneh(f"[{CYAN}]INCIDENTS[/] [{FGDIM}]— {len(self._incidents)} uløste[/]")
        for inc in self._incidents:
            sev = str(inc.get("severity", ""))
            color = _SEVERITY.get(sev, FG)
            cluster = inc.get("cluster", "")
            nerve = inc.get("nerve", "")
            msg = str(inc.get("message", "") or "").replace("\n", " ")
            preview = msg if len(msg) <= 80 else msg[:79] + "…"
            table.add_row(
                Text(f"● {sev}" if sev else "—", style=color),
                Text(f"{cluster}/{nerve}", style=FG),
                Text(preview, style=FGDIM),
            )

    def _drill_incident(self, index: int) -> None:
        self._sel_incident = index
        self._render_detail_panel()

    # -- Anomalies tab -----------------------------------------------------
    def _populate_anomalies(self) -> None:
        try:
            table = self.query_one("#nerve-table", DataTable)
        except Exception:
            return
        self._reset_columns(table, ("vigtighed", 11), ("kategori", 16),
                            ("count", 6), ("signatur", 42))
        if self._client is None:
            return
        try:
            self._anomalies = datasource.anomalies(self._client)
        except Exception:
            self._anomalies = []
        self._set_paneh(f"[{CYAN}]ANOMALIES[/] [{FGDIM}]— {len(self._anomalies)} fanget[/]")
        for a in self._anomalies:
            imp = str(a.get("importance", ""))
            color = _IMPORTANCE.get(imp, FG)
            sig = str(a.get("signature", "")).replace("\n", " ")
            preview = sig if len(sig) <= 42 else sig[:41] + "…"
            table.add_row(
                Text(f"● {imp}" if imp else "—", style=color),
                Text(str(a.get("category", "")), style=FGDIM),
                Text(str(a.get("count", 0)), style=FGDIM, justify="right"),
                Text(preview, style=FG),
            )

    def _render_anomaly_detail(self) -> None:
        try:
            panel = self.query_one("#hud-detail", Static)
        except Exception:
            return
        anoms = self._anomalies or []
        if not anoms:
            self._set_side_paneh(f"[{CYAN}]ANOMALI-DETALJE[/] [{DIM}]— —[/]")
            panel.update(Text.from_markup(f"[{GREEN} b]◈ INGEN ANOMALIER[/]"))
            return
        i = max(0, min(self._sel_anomaly, len(anoms) - 1))
        a = anoms[i]
        imp = str(a.get("importance", "") or "—")
        color = _IMPORTANCE.get(imp, FG)
        cat = a.get("category", "")
        badge_bg = "#1f0d0d" if color == RED else ("#241a05" if color == AMBER else "#06202e")

        def _cap(t: Any, n: int) -> str:
            s = str(t or "").replace("\n", " ")
            return s if len(s) <= n else s[: n - 1] + "…"

        first = str(a.get("first", ""))[:16].replace("T", " ")
        last = str(a.get("last", ""))[:16].replace("T", " ")
        self._set_side_paneh(f"[{CYAN}]ANOMALI-DETALJE[/] [{DIM}]— {_esc(cat)}[/]")
        lines = [
            f"[{color} b on {badge_bg}] ● {_esc(imp.upper())} · {_esc(a.get('source', ''))} [/]",
            "",
            f"[{FG} b]{_esc(cat)}[/]  [{FGDIM}]×{a.get('count', 0)}[/]",
            "",
            f"[{FGDIM} b]SIGNATUR[/]",
            f"[{FG}]{_esc(_cap(a.get('signature', ''), 160))}[/]",
            "",
            f"[{FGDIM} b]SAMPLE[/]",
            f"[{FGDIM}]{_esc(_cap(a.get('sample', ''), 200))}[/]",
        ]
        if a.get("location"):
            lines += ["", f"[{FGDIM} b]LOKATION[/]", f"[{FGDIM}]{_esc(_cap(a.get('location'), 90))}[/]"]
        lines += [
            "",
            f"[{FGDIM} b]VINDUE[/]",
            f"[{FGDIM}]{first}  →  {last}[/]",
        ]
        panel.update(Text.from_markup("\n".join(lines)))

    # -- detail dispatch (every table tab shows full detail of selected row) --
    def _render_row_detail(self, row: int) -> None:
        t = self.active_tab
        if t == "incidents":
            self._sel_incident = row
            self._render_detail_panel()
        elif t == "anomalies":
            self._sel_anomaly = row
            self._render_anomaly_detail()
        elif t == "nerves":
            self._render_nerve_detail(row)
        elif t == "clusters":
            self._render_cluster_detail(row)
        elif t == "governance":
            self._render_gov_detail(row)
        elif t == "agents":
            self._render_agent_detail(row)

    def _render_nerve_detail(self, row: int) -> None:
        try:
            panel = self.query_one("#hud-detail", Static)
        except Exception:
            return
        rows = self._nerve_rows or []
        if not (0 <= row < len(rows)):
            return
        r = rows[row]
        state = str(r.get("state", ""))
        color, glyph = _STATE.get(state, (FG, state))
        cluster = r.get("cluster", "")
        nerve = r.get("nerve", "")
        self._set_side_paneh(f"[{CYAN}]NERVE-DETALJE[/] [{DIM}]— {_esc(cluster)}/{_esc(nerve)}[/]")
        badge_bg = {GREEN: "#06251a", AMBER: "#241a05", RED: "#1f0d0d", DIM: "#0f1824"}.get(color, "#06202e")
        lines = [
            f"[{color} b on {badge_bg}] {_esc(glyph)} [/]",
            "",
            f"[{FG} b]{_esc(nerve)}[/]",
            f"[{FGDIM}]cluster[/]  [{FG}]{_esc(cluster)}[/]",
            "",
            f"[{FGDIM}]sidste fyring[/]  [{FG}]{_esc(self._rel_age(r.get('last', '')))}[/]",
            f"[{FGDIM}]antal (count)[/]  [{FG}]{r.get('count', 0)}[/]",
            "",
            f"[{FGDIM} b]AKTIVITET[/]",
            f"[{SPARK}]{_esc(r.get('spark', '') or '—')}[/]",
        ]
        if r.get("reason"):
            lines += ["", f"[{FGDIM} b]SENESTE[/]", f"[{FGDIM}]{_esc(r.get('reason'))}[/]"]
        lines += ["", f"[{DIM}]↵ vælg · skriv 'toggle {_esc(nerve)} off' for at slå fra[/]"]
        panel.update(Text.from_markup("\n".join(lines)))

    def _render_cluster_detail(self, row: int) -> None:
        try:
            panel = self.query_one("#hud-detail", Static)
        except Exception:
            return
        rows = self._cluster_rows or []
        if not (0 <= row < len(rows)):
            return
        r = rows[row]
        status = str(r.get("status", ""))
        color = _CLUSTER_STATUS.get(status, FG)
        name = r.get("cluster", "")
        self._set_side_paneh(f"[{CYAN}]CLUSTER-DETALJE[/] [{DIM}]— {_esc(name)}[/]")
        badge_bg = {GREEN: "#06251a", AMBER: "#241a05", RED: "#1f0d0d", DIM: "#0f1824"}.get(color, "#06202e")
        lines = [
            f"[{color} b on {badge_bg}] ● {_esc(status.upper())} [/]",
            "",
            f"[{FG} b]{_esc(name)}[/]",
            f"[{FGDIM}]nerver i alt[/]  [{FG} b]{r.get('nerves', 0)}[/]",
            "",
            f"[{GREEN}]● aktiv[/]      [{FG}]{r.get('aktiv', 0)}[/]",
            f"[{DIM}]○ idle[/]       [{FG}]{r.get('idle', 0)}[/]",
            f"[{AMBER}]◆ degraded[/]   [{FG}]{r.get('degraded', 0)}[/]",
            f"[{RED}]✖ død[/]        [{FG}]{r.get('død', 0)}[/]",
            "",
            f"[{CYAN}]↵ filtrér Nerves til denne cluster[/]",
        ]
        panel.update(Text.from_markup("\n".join(lines)))

    def _render_gov_detail(self, row: int) -> None:
        try:
            panel = self.query_one("#hud-detail", Static)
        except Exception:
            return
        flags = self._gov_flags or []
        if not (0 <= row < len(flags)):
            return
        f = flags[row]
        dangerous = bool(f.get("dangerous"))
        value = f.get("value")
        on = bool(value) if isinstance(value, bool) else str(value) not in ("off", "")
        vcolor = GREEN if on else DIM
        label = f.get("label") or f.get("key") or ""
        self._set_side_paneh(f"[{CYAN}]FLAG-DETALJE[/] [{DIM}]— {_esc(f.get('key', ''))}[/]")
        lines = [
            f"[{vcolor} b on #06251a] {_esc(self._fmt_value(value))} [/]"
            if on else f"[{DIM} b on #12161d] {_esc(self._fmt_value(value))} [/]",
            "",
            f"[{FG} b]{_esc(label)}[/]",
            f"[{FGDIM}]nøgle[/]  [{FG}]{_esc(f.get('key', ''))}[/]",
            f"[{FGDIM}]type[/]   [{FG}]{_esc(f.get('kind', 'bool'))}[/]",
        ]
        opts = f.get("options")
        if opts:
            lines.append(f"[{FGDIM}]valg[/]   [{FG}]{_esc(', '.join(map(str, opts)))}[/]")
        if dangerous:
            lines += ["", f"[{AMBER}]⚠ farligt flag — kræver bekræftelse (y) ved ændring[/]"]
        else:
            lines += ["", f"[{DIM}]— ufarligt —[/]"]
        lines += ["", f"[{CYAN} on #06202e] ↵ skift værdi [/]"]
        panel.update(Text.from_markup("\n".join(lines)))

    def on_data_table_row_highlighted(self, event) -> None:  # noqa: ANN001
        try:
            row = int(getattr(event, "cursor_row", 0) or 0)
        except Exception:
            row = 0
        self._render_row_detail(row)

    def on_data_table_row_selected(self, event) -> None:  # noqa: ANN001
        try:
            index = int(getattr(event, "cursor_row", 0) or 0)
        except Exception:
            index = 0
        self._drill_row(index)

    def _drill_row(self, index: int) -> None:
        """Enter/select on a row: governance toggles, others (re)show detail."""
        if self.active_tab == "governance":
            self._toggle_governance_row(index)
        else:
            self._render_row_detail(index)

    # -- Overview ----------------------------------------------------------
    def _render_overview_panel(self) -> None:
        try:
            panel = self.query_one("#hud-panel", Static)
        except Exception:
            return
        ov = self._overview or {}
        status = str(ov.get("status", "unknown")).lower()
        s_color, s_label = _STATUS.get(status, (DIM, status.upper() or "UKENDT"))
        nerves = ov.get("nerves", 0)
        clusters = ov.get("clusters", 0)
        incidents = ov.get("incidents", 0)
        breakers = ov.get("breakers", 0)
        inc_color = RED if incidents else FG
        brk_color = RED if breakers else FG
        lines = [
            f"[{CYAN} b]◈ OVERVIEW[/]",
            "",
            f"[{FGDIM}]status[/]   [{s_color} b]● {s_label}[/]",
            "",
            f"[{FGDIM}]nerver[/] [{FG} b]{nerves}[/]    "
            f"[{FGDIM}]clusters[/] [{FG} b]{clusters}[/]    "
            f"[{FGDIM}]incidents[/] [{inc_color} b]{incidents}[/]    "
            f"[{FGDIM}]breakers[/] [{brk_color} b]{breakers}[/]",
            "",
            f"[{CYAN}]top incidents[/]",
        ]
        top = ov.get("top_incidents") or []
        if not top:
            lines.append(f"[{DIM}]— ingen aktive incidents —[/]")
        for inc in top[:8]:
            sev = str(inc.get("severity", "") or "—")
            color = _SEVERITY.get(sev, FG)
            cluster = inc.get("cluster", "")
            nerve = inc.get("nerve", "")
            msg = str(inc.get("message", "") or "").replace("\n", " ")
            if len(msg) > 90:
                msg = msg[:89] + "…"
            lines.append(f"  [{color}]● {_esc(sev)}[/] [{FGDIM}]{_esc(cluster)}/{_esc(nerve)}[/] — {_esc(msg)}")

        # -- cost sidste 7 dage (self-safe; skjules ved tom data) ----------
        try:
            cd = self._costs_daily or {}
            raw_days = cd.get("days") or []
            per_day: dict[str, float] = {}
            day_order: list[str] = []
            for row in raw_days:
                if not isinstance(row, dict):
                    continue
                day = row.get("day")
                if not isinstance(day, str):
                    continue
                try:
                    c = float(row.get("total_cost") or 0.0)
                except Exception:
                    c = 0.0
                if day not in per_day:
                    per_day[day] = 0.0
                    day_order.append(day)
                per_day[day] += c
            if day_order:
                lines.append("")
                lines.append(f"[{CYAN}]cost sidste 7 dage[/]")
                for day in day_order[:7]:
                    lines.append(
                        f"  [{FGDIM}]{_esc(day)}[/]  [{FG}]${per_day[day]:.2f}[/]"
                    )
        except Exception:
            pass

        panel.update(Text.from_markup("\n".join(lines)))

    # -- Diagnostics -------------------------------------------------------
    def _render_diagnostics_panel(self) -> None:
        try:
            panel = self.query_one("#hud-panel", Static)
        except Exception:
            return
        try:
            diag = datasource.diagnostics(self._client) if self._client else {}
        except Exception:
            diag = {}

        def _count(v: Any) -> int:
            try:
                return len(v)
            except Exception:
                return int(v or 0)

        inc = _count(diag.get("incidents") or [])
        anom = _count(diag.get("anomalies") or [])
        degr = _count(diag.get("degrading") or [])
        root_causes = diag.get("root_causes") or []
        lines = [
            f"[{CYAN} b]◈ DIAGNOSTICS[/]",
            "",
            f"[{FGDIM}]incidents[/] [{(RED if inc else FG)} b]{inc}[/]    "
            f"[{FGDIM}]anomalier[/] [{(AMBER if anom else FG)} b]{anom}[/]    "
            f"[{FGDIM}]degraderer[/] [{(AMBER if degr else FG)} b]{degr}[/]",
            "",
            f"[{CYAN}]rod-årsager[/]",
        ]
        if not root_causes:
            lines.append(f"[{DIM}]— ingen identificerede rod-årsager —[/]")
        for rc in root_causes[:12]:
            if isinstance(rc, dict):
                text = rc.get("signature") or rc.get("cause") or rc.get("message") or str(rc)
                cnt = rc.get("count")
                suffix = f"  [{FGDIM}]×{cnt}[/]" if cnt else ""
            else:
                text, suffix = str(rc), ""
            if len(text) > 84:
                text = text[:83] + "…"
            lines.append(f"  [{AMBER}]▸[/] [{FG}]{_esc(text)}[/]{suffix}")

        # -- seneste hændelser (A7) — rå eventbus-feed --
        try:
            evs = datasource.events(self._client, limit=12) if self._client else []
        except Exception:
            evs = []
        self._events = evs or []
        lines += [
            "",
            f"[{CYAN} b]◈ SENESTE HÆNDELSER[/]  [{FGDIM}]— eventbus ({len(evs)})[/]",
        ]
        if not evs:
            lines.append(f"  [{DIM}]— ingen hændelser —[/]")
        for ev in evs[:12]:
            fam = str(ev.get("family") or "?")
            kind = str(ev.get("kind") or "")
            lines.append(f"  [{DIM}]▸[/] [{FGDIM}]{_esc(fam)}[/] [{FG}]{_esc(kind)}[/]")
        panel.update(Text.from_markup("\n".join(lines)))

    # -- Governance --------------------------------------------------------
    def _populate_governance(self) -> None:
        try:
            table = self.query_one("#nerve-table", DataTable)
        except Exception:
            return
        self._reset_columns(table, ("flag", 30), ("værdi", 10), ("farlig", 12))
        if self._client is None:
            return
        try:
            self._gov_flags = datasource.governance(self._client) or []
        except Exception:
            self._gov_flags = []
        self._set_paneh(f"[{CYAN}]GOVERNANCE[/] [{FGDIM}]— {len(self._gov_flags)} flag · [/]"
                        f"[{CYAN}]t[/] [{FGDIM}]toggler[/]")
        for f in self._gov_flags:
            dangerous = bool(f.get("dangerous"))
            label = str(f.get("label") or f.get("key") or "")
            value = f.get("value")
            on = bool(value) if isinstance(value, bool) else str(value) not in ("off", "")
            val_text = Text(self._fmt_value(value), style=(GREEN if on else DIM))
            danger_cell = (Text("⚠ farlig", style=AMBER) if dangerous
                           else Text("—", style=DIM))
            table.add_row(Text(label, style=FG), val_text, danger_cell)

    # -- Runs (scheduled tasks) --------------------------------------------
    def _populate_runs(self) -> None:
        try:
            table = self.query_one("#nerve-table", DataTable)
        except Exception:
            return
        self._reset_columns(table, ("opgave", 34), ("hvornår", 20), ("status", 12))
        try:
            self._scheduled = datasource.scheduled(self._client) if self._client else []
        except Exception:
            self._scheduled = []
        tasks = self._scheduled or []
        self._set_paneh(
            f"[{CYAN}]PLANLAGT[/] [{FGDIM}]— {len(tasks)} ventende opgaver[/]"
        )
        if not tasks:
            table.add_row(
                Text("— ingen planlagte opgaver —", style=DIM), Text(""), Text("")
            )
            return
        for task in tasks:
            title = (task.get("title") or task.get("name") or task.get("task")
                     or task.get("kind") or "—")
            when = (task.get("next_run") or task.get("scheduled_for")
                    or task.get("when") or "—")
            status = task.get("status") or "—"
            table.add_row(
                Text(_esc(str(title)), style=FG),
                Text(_esc(str(when)), style=FGDIM),
                Text(_esc(str(status)), style=FGDIM),
            )

    # -- Approvals (autonomy proposals) ------------------------------------
    def _populate_approvals(self) -> None:
        try:
            table = self.query_one("#nerve-table", DataTable)
        except Exception:
            return
        self._reset_columns(table, ("forslag", 40), ("art", 18), ("status", 12))
        try:
            self._autonomy = (datasource.autonomy(self._client) if self._client
                              else {"proposals": [], "pending_count": 0})
        except Exception:
            self._autonomy = {"proposals": [], "pending_count": 0}
        proposals = self._autonomy.get("proposals") or []
        pending = self._autonomy.get("pending_count") or 0
        pend_color = AMBER if pending > 0 else FGDIM
        self._set_paneh(
            f"[{CYAN}]AUTONOMI[/] [{FGDIM}]— [/]"
            f"[{pend_color}]{pending} afventer[/]"
        )
        if not proposals:
            table.add_row(
                Text("— ingen afventende forslag —", style=DIM), Text(""), Text("")
            )
            return
        for p in proposals:
            title = (p.get("title") or p.get("summary") or p.get("description")
                     or p.get("kind") or "—")
            kind = p.get("kind") or p.get("type") or "—"
            status = p.get("status") or "pending"
            table.add_row(
                Text(_esc(str(title)), style=FG),
                Text(_esc(str(kind)), style=FGDIM),
                Text(_esc(str(status)), style=FGDIM),
            )

    # -- Agents ------------------------------------------------------------
    def _populate_agents(self) -> None:
        try:
            table = self.query_one("#nerve-table", DataTable)
        except Exception:
            return
        self._reset_columns(table, ("agent", 24), ("rolle", 18),
                            ("status", 14), ("tokens", 10))
        if self._client is None:
            return
        try:
            rows = datasource.agents(self._client)
        except Exception:
            rows = []
        self._agent_rows = rows
        try:
            self._council = datasource.council(self._client)
        except Exception:
            self._council = []
        self._set_paneh(
            f"[{CYAN}]AGENTS[/] [{FGDIM}]— {len(rows)} agenter · "
            f"{len(self._council)} råds-sessioner[/]"
        )
        for r in rows:
            status = str(r.get("status", ""))
            color = _AGENT_STATUS.get(status, FG)
            table.add_row(
                Text(str(r.get("agent_id", "")), style=FG),
                Text(str(r.get("role", "")), style=FGDIM),
                Text(f"● {status}" if status else "—", style=color),
                Text(str(r.get("tokens_burned", 0)), style=FGDIM, justify="right"),
            )

    def _render_agent_detail(self, row: int) -> None:
        try:
            panel = self.query_one("#hud-detail", Static)
        except Exception:
            return
        rows = self._agent_rows or []
        if not (0 <= row < len(rows)):
            self._set_side_paneh(f"[{CYAN}]AGENT-DETALJE[/] [{DIM}]— —[/]")
            panel.update(Text.from_markup(f"[{GREEN} b]◈ INGEN AGENTER[/]"))
            return
        r = rows[row]
        status = str(r.get("status", "") or "—")
        color = _AGENT_STATUS.get(status, FG)
        agent_id = r.get("agent_id", "")
        role = r.get("role", "")
        badge_bg = {GREEN: "#06251a", DIM: "#0f1824", BLUE: "#06202e",
                    RED: "#1f0d0d"}.get(color, "#06202e")
        self._set_side_paneh(f"[{CYAN}]AGENT-DETALJE[/] [{DIM}]— {_esc(agent_id)}[/]")
        lines = [
            f"[{color} b on {badge_bg}] ● {_esc(status.upper())} [/]",
            "",
            f"[{FG} b]{_esc(agent_id)}[/]",
            f"[{FGDIM}]rolle[/]   [{FG}]{_esc(role)}[/]",
            f"[{FGDIM}]tokens[/]  [{FG}]{_esc(r.get('tokens_burned', 0))}[/]",
        ]
        # any remaining fields on the raw agent dict (never fabricated)
        raw = r.get("raw") or {}
        extra = [k for k in raw
                 if k not in ("agent_id", "role", "status", "tokens_burned")]
        if extra:
            lines += ["", f"[{FGDIM} b]FELTER[/]"]
            for k in extra:
                v = str(raw.get(k))
                if len(v) > 60:
                    v = v[:59] + "…"
                lines.append(f"[{FGDIM}]{_esc(k)}[/]  [{FG}]{_esc(v)}[/]")
        panel.update(Text.from_markup("\n".join(lines)))

    # -- Mind & Self -------------------------------------------------------
    def _render_mind_self_panel(self) -> None:
        """Render Jarvis' reduced self as HIS presence in the Central — warm,
        never raw content: living_executive / self_model / world_model."""
        try:
            panel = self.query_one("#hud-panel", Static)
        except Exception:
            return
        try:
            slf = datasource.self_snapshot(self._client) if self._client else {}
        except Exception:
            slf = {}

        def _dot(surface: dict) -> str:
            return (f"[{GREEN}]●[/]" if bool((surface or {}).get("liveness"))
                    else f"[{DIM}]○[/]")

        lines = [
            f"[{CYAN} b]◈ MIND & SELF[/]  [{FGDIM}]— hans selv i Centralen[/]",
        ]
        if not slf:
            lines += ["", f"[{FGDIM}]— selvet er stille lige nu —[/]"]
        else:
            le = slf.get("living_executive") or {}
            le_sum = le.get("summary") or {}
            lines += [
                "",
                f"{_dot(le)} [{GREEN} b]◈ living_executive[/]",
                f"[{FGDIM}]mode[/]         [{FG}]{_esc(le.get('mode', '—'))}[/]",
                f"[{FGDIM}]trace_count[/]  [{FG}]{_esc(le_sum.get('trace_count', 0))}[/]"
                f"   [{FGDIM}]recent[/] [{FG}]{_esc(le_sum.get('recent_count', 0))}[/]",
                f"[{FGDIM}]last_choice[/]  [{FG}]{_esc(le_sum.get('last_choice', '—'))}[/]",
                f"[{FGDIM}]last_action[/]  [{FG}]{_esc(le_sum.get('last_action', '—'))}[/]",
            ]

            sm = slf.get("self_model") or {}
            sm_sum = sm.get("summary") or {}
            sections = sm_sum.get("sections") or []
            if isinstance(sections, list):
                sec_text = ", ".join(str(s) for s in sections)
            else:
                sec_text = str(sections)
            lines += [
                "",
                f"{_dot(sm)} [{GREEN} b]◈ self_model[/]",
                f"[{FGDIM}]layer_count[/]  [{FG}]{_esc(sm_sum.get('layer_count', 0))}[/]",
                f"[{FGDIM}]sections[/]     [{FG}]{_esc(sec_text or '—')}[/]",
            ]

            wm = slf.get("world_model") or {}
            wm_sum = wm.get("summary") or {}
            lines += [
                "",
                f"{_dot(wm)} [{GREEN} b]◈ world_model[/]",
                f"[{FGDIM}]active_count[/]  [{FG}]{_esc(wm_sum.get('active_count', 0))}[/]",
            ]

        # -- memory-pipeline (A5) — always rendered, even if self is empty --
        try:
            mh = datasource.memory_health(self._client) if self._client else {}
        except Exception:
            mh = {}
        self._memory_health = mh or {}
        added = int(mh.get("added_today") or 0)
        journal_mark = (f"[{GREEN}]✓[/]" if mh.get("journal_today")
                        else f"[{AMBER}]mangler[/]")
        lines += [
            "",
            f"[{CYAN} b]◈ HUKOMMELSE[/]  [{FGDIM}]— memory-pipeline[/]",
            f"  [{FGDIM}]tilføjet i dag[/] [{FG} b]{added}[/]  [{FGDIM}]·[/]  "
            f"[{FGDIM}]dagens journal[/] {journal_mark}",
        ]

        # -- indre liv (A8) — reduceret: kun liveness+count pr. sektion --
        try:
            il = datasource.inner_life(self._client) if self._client else {}
        except Exception:
            il = {}
        il = il or {}
        il_live = int(il.get("live_count") or 0)
        il_total = int(il.get("total") or 0)
        lines += [
            "",
            f"[{CYAN} b]◈ INDRE LIV[/]  [{FGDIM}]— {il_live}/{il_total} sektioner aktive[/]",
        ]
        il_sections = il.get("sections") or {}
        if not il_sections:
            lines.append(f"  [{DIM}]— stille —[/]")
        else:
            for name, sec in sorted(il_sections.items()):
                sec = sec or {}
                dot = (f"[{GREEN}]●[/]" if sec.get("liveness") else f"[{DIM}]○[/]")
                cnt = int(sec.get("count") or 0)
                lines.append(f"  {dot} [{FGDIM}]{_esc(name)}[/] [{FG}]{cnt}[/]")

        panel.update(Text.from_markup("\n".join(lines)))

    @staticmethod
    def _rel_age(iso: str) -> str:
        """ISO timestamp → short relative age (2s / 4m / 3t / 2d). '—' on failure."""
        s = str(iso or "").strip()
        if not s or s == "—":
            return "—"
        try:
            ts = datetime.fromisoformat(s.replace("Z", "+00:00"))
            now = datetime.now(ts.tzinfo) if ts.tzinfo else datetime.now()
            secs = max(0, int((now - ts).total_seconds()))
        except Exception:
            return s[:8] if len(s) > 8 else s
        if secs < 60:
            return f"{secs}s"
        if secs < 3600:
            return f"{secs // 60}m"
        if secs < 86400:
            return f"{secs // 3600}t"
        return f"{secs // 86400}d"

    @staticmethod
    def _fmt_value(value: Any) -> str:
        if isinstance(value, bool):
            return "on" if value else "off"
        return str(value)

    def _next_value(self, flag: dict) -> Any:
        kind = str(flag.get("kind") or "")
        value = flag.get("value")
        if kind == "enum":
            options = list(flag.get("options") or [])
            if not options:
                return value
            try:
                idx = options.index(value)
            except ValueError:
                idx = -1
            return options[(idx + 1) % len(options)]
        return not bool(value)

    def _toggle_governance_row(self, index: int) -> None:
        flags = self._gov_flags or []
        if index < 0 or index >= len(flags):
            return
        flag = flags[index]
        key = flag.get("key")
        if key is None:
            return
        self._set_governance(key, self._next_value(flag))

    def _set_governance(self, key: Any, value: Any) -> None:
        payload = {"key": key, "value": value, "confirm": False}
        try:
            resp = self._client.post_json("/central/governance/set", payload)
        except Exception as exc:
            self._flash(f"[{RED}]✖ skrivefejl: {exc}[/]")
            return
        self._handle_write_response("governance", payload, resp)

    # -- Healing -----------------------------------------------------------
    _HEALER_FLAG = {
        "central.daemon_dead": "daemon_restart_live",
        "central.syslog_flood": "syslog_restart_live",
    }

    def _healer_flag_name(self, healer: dict) -> str | None:
        return self._HEALER_FLAG.get(str(healer.get("kind") or ""))

    def _render_healing_panel(self) -> None:
        try:
            panel = self.query_one("#hud-panel", Static)
        except Exception:
            return
        try:
            self._healers = datasource.healers(self._client) if self._client else {}
        except Exception:
            self._healers = {}
        reg = bool(self._healers.get("registry_enabled"))
        reg_color, reg_label = (GREEN, "on") if reg else (DIM, "off")
        healers = self._healers.get("healers") or []
        lines = [
            f"[{CYAN} b]◈ HEALING[/]",
            "",
            f"[{FGDIM}]registry[/]  [{reg_color} b]● {reg_label}[/]",
            "",
            f"[{CYAN}]healere[/]",
        ]
        if not healers:
            lines.append(f"[{DIM}]— ingen healere registreret —[/]")
        for i, h in enumerate(healers):
            kind = str(h.get("kind") or "")
            mode = str(h.get("mode") or "")
            destructive = bool(h.get("destructive"))
            live_on = bool(h.get("live_flag_on"))
            d_mark = f"[{AMBER}]⚠[/]" if destructive else f"[{DIM}]—[/]"
            live_color, live_label = (GREEN, "live") if live_on else (DIM, "shadow")
            settable = self._healer_flag_name(h) is not None
            note = "" if settable else f"  [{DIM}](ikke flag-styret)[/]"
            lines.append(
                f"  [{DIM}]{i}[/] [{FG}]{_esc(kind)}[/]  [{FGDIM}]{_esc(mode)}[/]  "
                f"farlig {d_mark}  [{live_color} b]● {live_label}[/]{note}"
            )
        if self._pending_write is not None:
            lines += ["", self._confirm_line()]
        panel.update(Text.from_markup("\n".join(lines)))

    def _toggle_healer_row(self, index: int) -> None:
        healers = (self._healers.get("healers") or []) if self._healers else []
        if index < 0 or index >= len(healers):
            return
        healer = healers[index]
        flag = self._healer_flag_name(healer)
        if flag is None:
            self._flash(f"[{DIM}]— healer er ikke flag-styret —[/]")
            return
        self._set_healer(flag, not bool(healer.get("live_flag_on")))

    def _set_healer(self, name: Any, enabled: bool) -> None:
        payload = {"name": name, "enabled": enabled, "confirm": False}
        try:
            resp = self._client.post_json("/central/healers/flag", payload)
        except Exception as exc:
            self._flash(f"[{RED}]✖ skrivefejl: {exc}[/]")
            return
        self._handle_write_response("healer", payload, resp)

    # -- shared write / confirm --------------------------------------------
    def _write_path(self, kind: str) -> str:
        return ("/central/governance/set" if kind == "governance"
                else "/central/healers/flag")

    def _write_desc(self, kind: str, payload: dict) -> str:
        if kind == "governance":
            return f"{payload.get('key')}={self._fmt_value(payload.get('value'))}"
        return f"{payload.get('name')}={'on' if payload.get('enabled') else 'off'}"

    def _handle_write_response(self, kind: str, payload: dict, resp: Any) -> None:
        resp = resp if isinstance(resp, dict) else {}
        if resp.get("needs_confirm"):
            self._pending_write = (kind, payload)
            self._flash(f"[{AMBER} b]⚠ bekræft {self._write_desc(kind, payload)}? y/n[/]")
            return
        if resp.get("ok"):
            self._pending_write = None
            self._flash(f"[{GREEN}]✓ sat: {self._write_desc(kind, payload)}[/]")
            self.refresh_data()
            return
        err = resp.get("error") or "ukendt fejl"
        self._flash(f"[{RED}]✖ {err}[/]")

    def _confirm_line(self) -> str:
        if self._pending_write is None:
            return ""
        kind, payload = self._pending_write
        return f"[{AMBER} b]⚠ bekræft {self._write_desc(kind, payload)}? y/n[/]"

    def action_toggle(self) -> None:
        if self.active_tab == "governance":
            try:
                table = self.query_one("#nerve-table", DataTable)
                index = int(table.cursor_row or 0)
            except Exception:
                index = 0
            self._toggle_governance_row(index)

    def action_confirm_yes(self) -> None:
        if self._pending_write is None:
            return
        kind, payload = self._pending_write
        confirmed = dict(payload)
        confirmed["confirm"] = True
        try:
            resp = self._client.post_json(self._write_path(kind), confirmed)
        except Exception as exc:
            self._pending_write = None
            self._flash(f"[{RED}]✖ skrivefejl: {exc}[/]")
            return
        resp = resp if isinstance(resp, dict) else {}
        self._pending_write = None
        if resp.get("ok"):
            self._flash(f"[{GREEN}]✓ sat: {self._write_desc(kind, confirmed)}[/]")
        else:
            self._flash(f"[{RED}]✖ {resp.get('error') or 'afvist'}[/]")
        self.refresh_data()

    def action_confirm_no(self) -> None:
        if self._pending_write is None:
            return
        self._pending_write = None
        self._flash(f"[{DIM}]— afbrudt —[/]")

    def _flash(self, markup: str) -> None:
        try:
            if self.active_tab in _TABLE_TABS:
                self.query_one("#hud-feed", RichLog).write(markup)
            elif self.active_tab == "healing":
                self._render_healing_panel()
        except Exception:
            return

    def _render_placeholder_panel(self, name: str) -> None:
        try:
            panel = self.query_one("#hud-panel", Static)
        except Exception:
            return
        label = {k: lbl for k, lbl, _ in _TABS}.get(name, name)
        panel.update(Text.from_markup(f"[{DIM}]— {label}: venter på wiring —[/]"))


def run_hud(ns) -> int:
    from central_cli.client import CentralClient
    from central_cli.config import resolve_base_url, resolve_token

    client = CentralClient(base_url=resolve_base_url(remote=ns.remote), token=resolve_token())
    CentralHud(client=client, live=True).run()
