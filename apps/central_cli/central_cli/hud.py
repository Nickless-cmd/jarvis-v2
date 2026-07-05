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

    # -- layout ------------------------------------------------------------
    def compose(self) -> ComposeResult:
        yield Static(self._render_header(), id="hud-head")
        yield Static(self._render_tabs(), id="hud-tabs")
        with Horizontal(id="hud-main"):
            yield DataTable(id="nerve-table", zebra_stripes=False)
            yield RichLog(id="hud-feed", markup=True, highlight=False)
        yield Static(self._render_cmd(), id="hud-cmd")

    def on_mount(self) -> None:
        table = self.query_one("#nerve-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("cluster", "nerve", "state", "sidste", "count", "aktivitet")
        self._sync_header()
        self._sync_tabs()
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
        if name != "nerves":
            try:
                feed = self.query_one("#hud-feed", RichLog)
                label = dict(_TABS).get(name, name)
                feed.write(f"[{DIM}]— {label}: kommer i næste build —[/]")
            except Exception:
                pass

    # -- data refresh ------------------------------------------------------
    def refresh_data(self) -> None:
        if self._client is None:
            return
        try:
            self._overview = datasource.overview(self._client)
            self._sync_header()
            self._populate_nerves()
            self._render_feed()
        except Exception:
            # never crash the UI on a fetch error
            return

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

    def _populate_nerves(self) -> None:
        try:
            table = self.query_one("#nerve-table", DataTable)
        except Exception:
            return
        table.clear()
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


def run_hud(ns) -> int:
    from central_cli.client import CentralClient
    from central_cli.config import resolve_base_url, resolve_token

    client = CentralClient(base_url=resolve_base_url(remote=ns.remote), token=resolve_token())
    CentralHud(client=client, live=True).run()
    return 0
