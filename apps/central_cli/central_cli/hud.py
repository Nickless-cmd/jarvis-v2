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
_TABLE_TABS = {"nerves", "clusters", "incidents", "governance"}
_PANEL_TABS = {"overview", "diagnostics", "healing"}


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
        # cache last-fetched overview for header re-renders
        self._overview: dict = {}
        # cache incidents for drill-down (Incidents tab)
        self._incidents: list = []
        # cache governance flags (rows) + healers payload for writes
        self._gov_flags: list = []
        self._healers: dict = {}
        # pending confirm-guarded write: (kind, payload) or None
        self._pending_write: tuple[str, dict] | None = None

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
            elif name == "governance":
                self._populate_governance()
            elif name == "healing":
                self._render_healing_panel()
            else:
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
        try:
            index = int(getattr(event, "cursor_row", 0) or 0)
        except Exception:
            index = 0
        if self.active_tab == "incidents":
            self._drill_incident(index)
        elif self.active_tab == "governance":
            self._toggle_governance_row(index)

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

    # -- Governance tab ----------------------------------------------------
    def _populate_governance(self) -> None:
        try:
            table = self.query_one("#nerve-table", DataTable)
        except Exception:
            return
        self._reset_columns(table, "flag", "værdi", "farlig")
        if self._client is None:
            return
        try:
            self._gov_flags = datasource.governance(self._client) or []
        except Exception:
            self._gov_flags = []
        for f in self._gov_flags:
            dangerous = bool(f.get("dangerous"))
            label = str(f.get("label") or f.get("key") or "")
            value = f.get("value")
            val_text = Text(self._fmt_value(value),
                            style=AMBER if dangerous else FG)
            danger_cell = (Text("⚠", style=AMBER) if dangerous
                           else Text("—", style=DIM))
            table.add_row(label, val_text, danger_cell)

    @staticmethod
    def _fmt_value(value: Any) -> str:
        if isinstance(value, bool):
            return "on" if value else "off"
        return str(value)

    def _next_value(self, flag: dict) -> Any:
        """Compute the toggled value: bool → flip, enum → cycle options."""
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
        # bool (or unknown) → flip truthiness
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
        """Write a governance flag with confirm-guard on dangerous ones."""
        payload = {"key": key, "value": value, "confirm": False}
        try:
            resp = self._client.post_json("/central/governance/set", payload)
        except Exception as exc:
            self._flash(f"[{RED}]✖ skrivefejl: {exc}[/]")
            return
        self._handle_write_response("governance", payload, resp)

    # -- Healing tab -------------------------------------------------------
    # map a healer kind → its settable live-flag name (None = not settable)
    _HEALER_FLAG = {
        "central.daemon_dead": "daemon_restart_live",
        "central.syslog_flood": "syslog_restart_live",
    }

    def _healer_flag_name(self, healer: dict) -> str | None:
        kind = str(healer.get("kind") or "")
        return self._HEALER_FLAG.get(kind)

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
            f"[{DIM}]registry[/]  [{reg_color} b]● {reg_label}[/]",
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
                f"  [{DIM}]{i}[/] [{FG}]{kind}[/]  [{DIM}]{mode}[/]  "
                f"farlig {d_mark}  [{live_color} b]● {live_label}[/]{note}"
            )
        if self._pending_write is not None:
            lines += ["", self._confirm_line()]
        panel.update("\n".join(lines))

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
        """Write a healer flag with confirm-guard on dangerous ones."""
        payload = {"name": name, "enabled": enabled, "confirm": False}
        try:
            resp = self._client.post_json("/central/healers/flag", payload)
        except Exception as exc:
            self._flash(f"[{RED}]✖ skrivefejl: {exc}[/]")
            return
        self._handle_write_response("healer", payload, resp)

    # -- shared write / confirm flow ---------------------------------------
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
        if self.active_tab not in ("governance", "healing"):
            return
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
            err = resp.get("error") or "afvist"
            self._flash(f"[{RED}]✖ {err}[/]")
        self.refresh_data()

    def action_confirm_no(self) -> None:
        if self._pending_write is None:
            return
        self._pending_write = None
        self._flash(f"[{DIM}]— afbrudt —[/]")

    def _flash(self, markup: str) -> None:
        """Write a short status/confirm line into the feed or panel (guarded)."""
        try:
            if self.active_tab in _TABLE_TABS:
                log = self.query_one("#hud-feed", RichLog)
                log.write(markup)
            else:
                # panel tabs (healing): re-render so the confirm line shows
                if self.active_tab == "healing":
                    self._render_healing_panel()
        except Exception:
            return

    # -- placeholder panel (unused tabs) -----------------------------------
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
