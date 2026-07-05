"""Central HUD — navigable J.A.R.V.I.S-style Textual UI.

Replaces the bare REPL in ``tui.py``. This build ships the HUD shell
(7-tab nav + dark theme + live header + command bar), the Nerves view
(a DataTable driven by ``datasource.nerves``), and the deduped decision
feed (``datasource.feed``). The other tab bodies are placeholders that
later tasks fill in.

Design invariants:
- A fetch error must never crash the UI (``refresh_data`` is guarded).
- Colors match ``docs/superpowers/mockups/central-hud-mockup.html``.
"""

from __future__ import annotations

from typing import Any

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, RichLog, Static

from central_cli import datasource

# --- theme palette (mockup 1:1) ------------------------------------------
BG = "#0a0e14"
PANEL = "#0d1420"
CYAN = "#00d4ff"
AMBER = "#ffb000"
RED = "#ff4a4a"
GREEN = "#00ff88"
DIM = "#4a5568"
FG = "#c7d3e0"

# state -> (hex color, glyph label)
_STATE = {
    "aktiv": (GREEN, "● aktiv"),
    "idle": (DIM, "○ idle"),
    "degraded": (AMBER, "◆ degraded"),
    "død": (RED, "✖ død"),
}

# feed decision -> color
_DECISION = {
    "error": RED,
    "critical": RED,
    "warn": AMBER,
    "warning": AMBER,
    "success": GREEN,
    "observe": GREEN,
}

# tab order + labels (mockup): key -> label
_TABS: list[tuple[str, str]] = [
    ("overview", "Overview"),
    ("clusters", "Clusters"),
    ("nerves", "Nerves"),
    ("incidents", "Incidents"),
    ("diagnostics", "Diagnostics"),
    ("healing", "Healing"),
    ("governance", "Governance"),
]

# status-word -> (color, label)
_STATUS = {
    "green": (GREEN, "GRØN"),
    "yellow": (AMBER, "GUL"),
    "red": (RED, "RØD"),
}

# cluster status-word -> color (grid uses green/yellow/red/idle)
_CLUSTER_STATUS = {
    "green": GREEN,
    "yellow": AMBER,
    "red": RED,
    "idle": DIM,
}

# incident severity -> color
_SEVERITY = {
    "severe": RED,
    "critical": RED,
    "error": RED,
    "warn": AMBER,
    "warning": AMBER,
    "info": CYAN,
}

# tabs that render into the DataTable vs the panel
_TABLE_TABS = {"nerves", "clusters", "incidents"}
_PANEL_TABS = {"overview", "diagnostics", "healing", "governance"}


class CentralHud(App):
    """The Central HUD app shell."""

    CSS = f"""
    Screen {{
        background: {BG};
        color: {FG};
    }}
    #hud-head {{
        height: 1;
        background: {PANEL};
        color: {FG};
        padding: 0 1;
    }}
    #hud-tabs {{
        height: 1;
        background: {PANEL};
        color: {DIM};
        padding: 0 1;
    }}
    #hud-main {{
        height: 1fr;
    }}
    #nerve-table {{
        width: 2fr;
        border: solid {CYAN};
        background: {PANEL};
    }}
    #nerve-table > .datatable--header {{
        background: {PANEL};
        color: {CYAN};
        text-style: bold;
    }}
    #nerve-table > .datatable--cursor {{
        background: {CYAN} 20%;
    }}
    #hud-feed {{
        width: 1fr;
        border: solid {CYAN};
        background: {PANEL};
    }}
    #hud-panel {{
        width: 1fr;
        border: solid {CYAN};
        background: {PANEL};
        padding: 1 2;
        overflow-y: auto;
    }}
    #hud-cmd {{
        dock: bottom;
        height: 1;
        background: {PANEL};
        color: {DIM};
        padding: 0 1;
    }}
    """

    BINDINGS = [
        Binding("1", "show('overview')", "Overview", show=False),
        Binding("2", "show('clusters')", "Clusters", show=False),
        Binding("3", "show('nerves')", "Nerves", show=False),
        Binding("4", "show('incidents')", "Incidents", show=False),
        Binding("5", "show('diagnostics')", "Diagnostics", show=False),
        Binding("6", "show('healing')", "Healing", show=False),
        Binding("7", "show('governance')", "Governance", show=False),
        Binding("q", "quit", "Quit", show=False),
        Binding("question_mark", "help", "Hjælp", show=False),
    ]

    def __init__(self, *, client: Any = None, live: bool = True) -> None:
        super().__init__()
        self._client = client
        self._live = live
        self.active_tab = "nerves"
        # cache last-fetched overview for header re-renders
        self._overview: dict = {}
        # cache incidents for drill-down (Incidents tab)
        self._incidents: list = []

    # -- layout ------------------------------------------------------------
    def compose(self) -> ComposeResult:
        yield Static(self._render_header(), id="hud-head")
        yield Static(self._render_tabs(), id="hud-tabs")
        with Horizontal(id="hud-main"):
            yield DataTable(id="nerve-table", zebra_stripes=False)
            yield Static("", id="hud-panel", markup=True)
            yield RichLog(id="hud-feed", markup=True, highlight=False)
        yield Static(self._render_cmd(), id="hud-cmd")

    def on_mount(self) -> None:
        table = self.query_one("#nerve-table", DataTable)
        table.cursor_type = "row"
        self._sync_header()
        self._sync_tabs()
        # nerves is the default tab: table + feed visible, panel hidden
        self._apply_tab_visibility()
        self._populate_nerves()
        self._render_feed()
        if self._live:
            self.set_interval(3.0, self.refresh_data)

    # -- actions (bindings) ------------------------------------------------
    def action_show(self, name: str) -> None:
        self.show_tab(name)

    def action_help(self) -> None:  # placeholder — later task
        return

    # -- navigation --------------------------------------------------------
    def show_tab(self, name: str) -> None:
        self.active_tab = name
        self._sync_tabs()
        self._apply_tab_visibility()
        self._populate_active_tab()

    def _apply_tab_visibility(self) -> None:
        """Toggle which widget owns the content area for the active tab.

        Tabular tabs (nerves/clusters/incidents) show the DataTable + feed;
        panel tabs (overview/diagnostics/…) show the Static panel instead.
        """
        name = self.active_tab
        table_visible = name in _TABLE_TABS
        try:
            self.query_one("#nerve-table", DataTable).display = table_visible
        except Exception:
            pass
        try:
            # feed stays alongside the table for tabular tabs only
            self.query_one("#hud-feed", RichLog).display = table_visible
        except Exception:
            pass
        try:
            self.query_one("#hud-panel", Static).display = not table_visible
        except Exception:
            pass

    def _populate_active_tab(self) -> None:
        """Render real content for whichever tab is active (guarded)."""
        try:
            name = self.active_tab
            if name == "nerves":
                self._populate_nerves()
                self._render_feed()
            elif name == "clusters":
                self._populate_clusters()
            elif name == "incidents":
                self._populate_incidents()
            elif name == "overview":
                self._render_overview_panel()
            elif name == "diagnostics":
                self._render_diagnostics_panel()
            else:
                # healing/governance not yet implemented — keep placeholder
                self._render_placeholder_panel(name)
        except Exception:
            # never crash the UI on a render error
            return

    # -- data refresh ------------------------------------------------------
    def refresh_data(self) -> None:
        if self._client is None:
            return
        try:
            self._overview = datasource.overview(self._client)
            self._sync_header()
        except Exception:
            # never crash the UI on a fetch error
            return
        # refresh whichever tab is active (+ always-visible header/feed)
        self._populate_active_tab()

    # -- rendering helpers -------------------------------------------------
    def _render_header(self) -> str:
        ov = self._overview or {}
        status = str(ov.get("status", "unknown")).lower()
        color, label = _STATUS.get(status, (DIM, status.upper() or "UKENDT"))
        nerves = ov.get("nerves", 0)
        clusters = ov.get("clusters", 0)
        incidents = ov.get("incidents", 0)
        breakers = ov.get("breakers", 0)
        inc_color = RED if incidents else FG
        return (
            f"[{CYAN}]◈ CENTRAL[/] [{DIM}]· J.A.R.V.I.S CLI[/]   "
            f"[{color}]● {label}[/]   "
            f"[{DIM}]nerver[/] [{FG}]{nerves}[/] · "
            f"[{DIM}]clusters[/] [{FG}]{clusters}[/] · "
            f"[{DIM}]incidents[/] [{inc_color}]{incidents}[/] · "
            f"[{DIM}]breakers[/] [{FG}]{breakers}[/]"
        )

    def _render_tabs(self) -> str:
        parts = []
        for idx, (key, label) in enumerate(_TABS, start=1):
            if key == self.active_tab:
                parts.append(f"[{DIM}]{idx}[/][{CYAN} b]{label}[/]")
            else:
                parts.append(f"[{DIM}]{idx}[/][{FG}]{label}[/]")
        return "   ".join(parts)

    def _render_cmd(self) -> str:
        return (
            f"[{CYAN} b]1-7[/] views · [{CYAN} b]↑↓[/] naviger · "
            f"[{CYAN} b]↵[/] drill · [{CYAN} b]/[/] filter · "
            f"[{CYAN} b]:[/] kommando · [{CYAN} b]r[/] resolve · "
            f"[{CYAN} b]?[/] hjælp · [{CYAN} b]q[/] quit"
        )

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

    def _reset_columns(self, table: DataTable, *names: str) -> None:
        """Re-create the table's columns (they differ per tabular tab)."""
        table.clear(columns=True)
        table.add_columns(*names)

    def _populate_nerves(self) -> None:
        try:
            table = self.query_one("#nerve-table", DataTable)
        except Exception:
            return
        self._reset_columns(table, "cluster", "nerve", "state", "sidste",
                             "count", "aktivitet")
        if self._client is None:
            return
        try:
            rows = datasource.nerves(self._client)
        except Exception:
            return
        for r in rows:
            state = str(r.get("state", ""))
            color, glyph = _STATE.get(state, (FG, state))
            state_cell = Text(glyph, style=color)
            table.add_row(
                str(r.get("cluster", "")),
                str(r.get("nerve", "")),
                state_cell,
                str(r.get("last", "") or "—"),
                str(r.get("count", 0)),
                str(r.get("spark", "")),
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
            tag = f" [{DIM}]×{count}[/]" if count > 1 else ""
            cluster = r.get("cluster", "")
            nerve = r.get("nerve", "")
            reason = r.get("reason", "")
            log.write(
                f"[{color}]●[/] [{color}]{cluster}/{nerve}[/] "
                f"[{DIM}]·[/] {decision} — {reason}{tag}"
            )

    # -- Clusters tab ------------------------------------------------------
    def _populate_clusters(self) -> None:
        try:
            table = self.query_one("#nerve-table", DataTable)
        except Exception:
            return
        self._reset_columns(table, "cluster", "status", "nerver", "aktiv",
                            "idle", "degraded", "død")
        if self._client is None:
            return
        try:
            rows = datasource.clusters(self._client)
        except Exception:
            return
        for r in rows:
            status = str(r.get("status", ""))
            color = _CLUSTER_STATUS.get(status, FG)
            status_cell = Text(f"● {status}", style=color)
            table.add_row(
                str(r.get("cluster", "")),
                status_cell,
                str(r.get("nerves", 0)),
                Text(str(r.get("aktiv", 0)), style=GREEN),
                Text(str(r.get("idle", 0)), style=DIM),
                Text(str(r.get("degraded", 0)), style=AMBER),
                Text(str(r.get("død", 0)), style=RED),
            )

    # -- Incidents tab -----------------------------------------------------
    def _populate_incidents(self) -> None:
        try:
            table = self.query_one("#nerve-table", DataTable)
        except Exception:
            return
        self._reset_columns(table, "sev", "cluster/nerve", "besked")
        if self._client is None:
            return
        try:
            self._incidents = datasource.incidents(self._client)
        except Exception:
            self._incidents = []
        for inc in self._incidents:
            sev = str(inc.get("severity", ""))
            color = _SEVERITY.get(sev, FG)
            cluster = inc.get("cluster", "")
            nerve = inc.get("nerve", "")
            msg = str(inc.get("message", "") or "").replace("\n", " ")
            # table cell is a preview; full text lives in the drill-down panel
            preview = msg if len(msg) <= 80 else msg[:79] + "…"
            table.add_row(
                Text(sev or "—", style=color),
                f"{cluster}/{nerve}",
                preview,
            )

    def _drill_incident(self, index: int) -> None:
        """Render the FULL selected incident (no truncation) into the feed."""
        incs = self._incidents or []
        if index < 0 or index >= len(incs):
            return
        inc = incs[index]
        sev = str(inc.get("severity", "") or "—")
        color = _SEVERITY.get(sev, FG)
        cluster = inc.get("cluster", "")
        nerve = inc.get("nerve", "")
        message = str(inc.get("message", "") or "")
        try:
            log = self.query_one("#hud-feed", RichLog)
        except Exception:
            return
        log.clear()
        log.write(f"[{CYAN} b]▸ INCIDENT[/]  [{color}]● {sev}[/]")
        log.write(f"[{DIM}]cluster/nerve[/]  {cluster}/{nerve}")
        log.write("")
        # full message, no truncation
        log.write(f"[{FG}]{message}[/]")

    def on_data_table_row_selected(self, event) -> None:  # noqa: ANN001
        if self.active_tab != "incidents":
            return
        try:
            index = int(getattr(event, "cursor_row", 0) or 0)
        except Exception:
            index = 0
        self._drill_incident(index)

    # -- Overview tab ------------------------------------------------------
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
            f"[{DIM}]status[/]   [{s_color} b]● {s_label}[/]",
            "",
            f"[{DIM}]nerver[/] [{FG} b]{nerves}[/]    "
            f"[{DIM}]clusters[/] [{FG} b]{clusters}[/]    "
            f"[{DIM}]incidents[/] [{inc_color} b]{incidents}[/]    "
            f"[{DIM}]breakers[/] [{brk_color} b]{breakers}[/]",
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
            lines.append(
                f"  [{color}]● {sev}[/] [{DIM}]{cluster}/{nerve}[/] — {msg}"
            )
        panel.update("\n".join(lines))

    # -- Diagnostics tab ---------------------------------------------------
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
            f"[{DIM}]incidents[/] [{(RED if inc else FG)} b]{inc}[/]    "
            f"[{DIM}]anomalier[/] [{(AMBER if anom else FG)} b]{anom}[/]    "
            f"[{DIM}]degraderer[/] [{(AMBER if degr else FG)} b]{degr}[/]",
            "",
            f"[{CYAN}]rod-årsager[/]",
        ]
        if not root_causes:
            lines.append(f"[{DIM}]— ingen identificerede rod-årsager —[/]")
        for rc in root_causes:
            if isinstance(rc, dict):
                text = rc.get("cause") or rc.get("message") or str(rc)
            else:
                text = str(rc)
            lines.append(f"  [{AMBER}]▸[/] [{FG}]{text}[/]")
        panel.update("\n".join(lines))

    # -- placeholder panel (healing/governance not yet built) --------------
    def _render_placeholder_panel(self, name: str) -> None:
        try:
            panel = self.query_one("#hud-panel", Static)
        except Exception:
            return
        label = dict(_TABS).get(name, name)
        panel.update(f"[{DIM}]— {label}: kommer i næste build —[/]")


def run_hud(ns) -> int:
    from central_cli.client import CentralClient
    from central_cli.config import resolve_base_url, resolve_token

    client = CentralClient(base_url=resolve_base_url(remote=ns.remote), token=resolve_token())
    CentralHud(client=client, live=True).run()
    return 0
