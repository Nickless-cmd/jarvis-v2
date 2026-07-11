from __future__ import annotations

from rich.text import Text

from central_cli.engine.state import HudState
from central_cli.frame.detail_screen import DetailScreen
from central_cli.hud_theme import AMBER, CYAN, DIM, FGDIM, RED

INCIDENT_COLUMNS = (("cluster", 14), ("nerve", 18), ("sev", 7), ("besked", 44))

_SEV_COLOR = {"error": RED, "warning": AMBER, "info": DIM}


def build_incident_rows(state: HudState) -> list[dict]:
    """Rækker til CursorStableTable. Hver dict har 'id' (key) + kolonne-labels.
    'besked' vises trunkeret i tabellen (drill for fuld tekst)."""
    data = state.get("diagnostics").data
    incidents = (data or {}).get("incidents", []) if isinstance(data, dict) else []
    rows: list[dict] = []
    for i, inc in enumerate(incidents):
        msg = str(inc.get("message", ""))
        rows.append({
            "id": str(inc.get("id", f"idx{i}")),
            "cluster": str(inc.get("cluster", "")),
            "nerve": str(inc.get("nerve", "")),
            "sev": str(inc.get("severity", "")),
            "besked": msg if len(msg) <= 42 else msg[:41] + "…",
            "_raw": inc,
        })
    return rows


def incident_detail_text(inc: dict) -> Text:
    """Fuld, u-trunkeret detalje som ét Text-objekt (så str() eksponerer indholdet
    og det stadig renderer/scroller). Ingen [:N]-klip."""
    sev = str(inc.get("severity", ""))
    color = _SEV_COLOR.get(sev, FGDIM)
    out = Text()
    out.append_text(Text.from_markup(
        f"[{CYAN}]{inc.get('cluster','')}[/] ▸ [{CYAN}]{inc.get('nerve','')}[/]  "
        f"[{color}]{sev}[/]  [{DIM}]{inc.get('ts','')}[/]"))
    out.append("\n\n")
    out.append_text(Text.from_markup(f"[{FGDIM}]besked[/]\n"))
    out.append(str(inc.get("message", "")))
    rc = inc.get("root_cause") or inc.get("signature")
    if rc:
        out.append("\n\n")
        out.append_text(Text.from_markup(f"[{FGDIM}]root-cause[/]\n"))
        out.append(str(rc))
    corr = inc.get("correlation")
    if isinstance(corr, dict):
        out.append("\n\n")
        out.append_text(Text.from_markup(
            f"[{FGDIM}]korrelation[/] count={corr.get('count','?')} "
            f"first={corr.get('first','?')} last={corr.get('last','?')}"))
    return out


class IncidentDetailScreen(DetailScreen):
    def __init__(self, inc: dict) -> None:
        super().__init__()
        self._inc = inc

    def title_crumb(self) -> str:
        return f"Central ▸ Incidents ▸ {self._inc.get('cluster','')}:{self._inc.get('nerve','')}"

    def body_renderable(self):
        return incident_detail_text(self._inc)
