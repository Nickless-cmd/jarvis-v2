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

from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.binding import Binding
from textual.widgets import DataTable, RichLog, Static

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
    ("clusters", "Clusters", False),
    ("nerves", "Nerves", False),
    ("incidents", "Incidents", False),
    ("diagnostics", "Diagnostics", False),
    ("healing", "Healing", True),
    ("governance", "Governance", True),
]

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

_TABLE_TABS = {"nerves", "clusters", "incidents", "governance"}
_PANEL_TABS = {"overview", "diagnostics", "healing"}


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

    #hud-cmd {{
        height: 2;
        background: {BAR};
        padding: 0 2;
        border-top: solid {LINE};
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
        Binding("space", "toggle", "Toggle", show=False),
        Binding("t", "toggle", "Toggle", show=False),
        Binding("y", "confirm_yes", "Bekræft", show=False),
        Binding("n", "confirm_no", "Afbryd", show=False),
        Binding("escape", "confirm_no", "Afbryd", show=False),
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
        self._sel_incident: int = 0
        self._pulse_on: bool = True
        self._caret_on: bool = True

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
            yield Static(self._render_cmd(), id="hud-cmd")

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
        # animation timers (pulse status dot + blink caret) — always on
        self.set_interval(0.8, self._tick_pulse)
        self.set_interval(0.53, self._tick_caret)

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

    # -- animation ticks ---------------------------------------------------
    def _tick_pulse(self) -> None:
        self._pulse_on = not self._pulse_on
        self._sync_header()

    def _tick_caret(self) -> None:
        self._caret_on = not self._caret_on
        try:
            self.query_one("#hud-cmd", Static).update(self._render_cmd())
        except Exception:
            pass

    # -- actions -----------------------------------------------------------
    def action_show(self, name: str) -> None:
        self.show_tab(name)

    def action_help(self) -> None:
        return

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
                self._render_detail_panel()
                self._render_feed()
            elif name == "clusters":
                self._populate_clusters()
                self._render_detail_panel()
            elif name == "incidents":
                self._populate_incidents()
                self._render_detail_panel()
            elif name == "governance":
                self._populate_governance()
                self._render_detail_panel()
            elif name == "overview":
                self._render_overview_panel()
            elif name == "diagnostics":
                self._render_diagnostics_panel()
            elif name == "healing":
                self._render_healing_panel()
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
            f"[{DIM}][/][{FGDIM} b]1-7[/] [{DIM}]views ·[/] [{FGDIM} b]↑↓[/] [{DIM}]naviger ·[/] "
            f"[{FGDIM} b]↵[/] [{DIM}]drill ·[/] [{FGDIM} b]/[/] [{DIM}]filter ·[/] "
            f"[{FGDIM} b]:[/] [{DIM}]kommando ·[/] [{FGDIM} b]r[/] [{DIM}]resolve ·[/] "
            f"[{FGDIM} b]?[/] [{DIM}]hjælp[/]"
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
            cluster = r.get("cluster", "")
            nerve = r.get("nerve", "")
            reason = r.get("reason", "")
            sep = f" [{DIM}]—[/] {reason}" if reason else ""
            log.write(
                f"[{color}]●[/] [{color}]{cluster}/{nerve}[/] "
                f"[{DIM}]·[/] {decision}{badge}{sep}"
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
            f"[{CYAN}]INCIDENT-DETALJE[/] [{DIM}]— {cluster}/{nerve}[/]"
        )

        def _cap(text: Any, n: int) -> str:
            s = str(text or "").replace("\n", " ")
            return s if len(s) <= n else s[: n - 1] + "…"

        # bordered badge (terminal idiom: bg-tinted pill)
        badge_bg = "#1f0d0d" if color == RED else ("#241a05" if color == AMBER else "#06202e")
        lines = [
            f"[{color} b on {badge_bg}] ● {sev.upper()} · {cluster} [/]",
            "",
            f"[{FG} b]{d.get('title') or nerve}[/]",
            f"[{FGDIM}]{_cap(d.get('message', ''), 130)}[/]",
        ]
        rc = d.get("root_cause")
        if rc:
            lines += ["", f"[{FGDIM} b]ROOT CAUSE[/]", f"[{FG}]{_cap(rc, 130)}[/]"]
        related = d.get("related") or []
        if related:
            chips = "".join(f"[{FGDIM} on #0f1824] {r} [/] " for r in related)
            lines += ["", f"[{FGDIM} b]RELATEREDE NERVER[/]", chips]
        heal = d.get("heal_status")
        if heal:
            lines += ["", f"[{FGDIM} b]HEAL-STATUS[/]", f"[{GREEN}]◈ {_cap(heal, 130)}[/]"]
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

    def on_data_table_row_highlighted(self, event) -> None:  # noqa: ANN001
        if self.active_tab != "incidents":
            return
        try:
            self._sel_incident = int(getattr(event, "cursor_row", 0) or 0)
        except Exception:
            self._sel_incident = 0
        self._render_detail_panel()

    def on_data_table_row_selected(self, event) -> None:  # noqa: ANN001
        try:
            index = int(getattr(event, "cursor_row", 0) or 0)
        except Exception:
            index = 0
        if self.active_tab == "incidents":
            self._drill_incident(index)
        elif self.active_tab == "governance":
            self._toggle_governance_row(index)

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
            lines.append(f"  [{color}]● {sev}[/] [{FGDIM}]{cluster}/{nerve}[/] — {msg}")
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
            lines.append(f"  [{AMBER}]▸[/] [{FG}]{text}[/]{suffix}")
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
                f"  [{DIM}]{i}[/] [{FG}]{kind}[/]  [{FGDIM}]{mode}[/]  "
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
        panel.update(Text.from_markup(f"[{DIM}]— {label}: kommer i næste build —[/]"))


def run_hud(ns) -> int:
    from central_cli.client import CentralClient
    from central_cli.config import resolve_base_url, resolve_token

    client = CentralClient(base_url=resolve_base_url(remote=ns.remote), token=resolve_token())
    CentralHud(client=client, live=True).run()
