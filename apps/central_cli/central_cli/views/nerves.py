from __future__ import annotations

from rich.text import Text

from central_cli.engine.state import HudState
from central_cli.frame.detail_screen import DetailScreen
from central_cli.hud_theme import CYAN, DIM, FGDIM, GREEN

NERVE_COLUMNS = (("cluster", 16), ("nerve", 24), ("state", 14))


def build_nerve_rows(state: HudState) -> list[dict]:
    data = state.get("timeseries").data
    series = (data or {}).get("series", {}) if isinstance(data, dict) else {}
    rows: list[dict] = []
    seen: set[str] = set()
    for key in sorted(series):
        cluster, _, nerve = key.partition(":")
        if not nerve:
            cluster, nerve = "", key
        if nerve in seen:               # row-key skal være unik i DataTable
            continue
        seen.add(nerve)
        val = series[key] if isinstance(series[key], dict) else {}
        total = sum(int(p.get("count", 0) or 0) for p in val.values() if isinstance(p, dict))
        rows.append({
            "nerve": nerve,             # key_field
            "cluster": cluster,
            "state": "aktiv" if total > 0 else "idle",
            "_raw": val,
        })
    return rows


def nerve_detail_surface_key(nerve: str) -> str:
    return f"nerve_detail:{nerve}"


def nerve_detail_path(nerve: str) -> str:
    return f"/central/nerve/{nerve}"


def nerve_detail_text(nerve: str, detail: dict | None) -> Text:
    out = Text()
    out.append_text(Text.from_markup(f"[{CYAN}]{nerve}[/]  [{DIM}]seneste beslutninger[/]\n\n"))
    if not isinstance(detail, dict):
        out.append_text(Text.from_markup(f"[{DIM}]henter…[/]"))
        return out
    recent = detail.get("recent") or []
    if not recent:
        out.append_text(Text.from_markup(f"[{DIM}]ingen observationer[/]"))
    for obs in recent[:30]:
        # Label styling via markup; raw values as plain appends so brackets in
        # decision/reason can never be parsed as markup and crash from_markup.
        out.append(str(obs.get("decision", "?")), style=GREEN)
        out.append("  ")
        out.append(str(obs.get("reason", "")), style=FGDIM)
        out.append("\n")
        payload = obs.get("payload")
        if payload:
            out.append("    ")
            out.append(str(payload), style="dim")
            out.append("\n")
    return out


class NerveDetailScreen(DetailScreen):
    """Drill-detalje for én nerve. Læser sin egen surface (nerve_detail:<navn>)
    fra HudState; appen starter en on-demand worker når skærmen pushes."""

    def __init__(self, nerve: str, state: HudState) -> None:
        super().__init__()
        self._nerve = nerve
        self._state = state

    def on_mount(self) -> None:
        self.set_interval(0.5, self.refresh_body)   # screen-scoped → ryddes automatisk ved pop

    def title_crumb(self) -> str:
        return f"Central ▸ Nerves ▸ {self._nerve}"

    def body_renderable(self):
        entry = self._state.get(nerve_detail_surface_key(self._nerve))
        return nerve_detail_text(self._nerve, entry.data if isinstance(entry.data, dict) else None)
