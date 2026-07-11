from __future__ import annotations

from rich.text import Text

from central_cli.engine.state import HudState
from central_cli.hud_theme import AMBER, CYAN, DIM, FGDIM, GREEN, RED

_STATUS_COLOR = {"green": GREEN, "yellow": AMBER, "red": RED}


def render_overview(state: HudState):
    """Renderable til Overview-panelet. Læser KUN fra state (ingen fetch)."""
    e = state.get("realtime")
    data = e.data if isinstance(e.data, dict) else {}
    status = str(data.get("status", "?"))
    color = _STATUS_COLOR.get(status, DIM)

    lines: list = []
    header = Text.from_markup(f"[{color}]● {status.upper()}[/]")
    if e.error:
        header.append_text(Text.from_markup(f"  [{AMBER}]⚠ {e.error} (viser sidste gode)[/]"))
    elif e.loading and e.fetched_at == 0.0:
        header.append_text(Text.from_markup(f"  [{DIM}]henter…[/]"))
    lines.append(header)

    incidents = data.get("incidents") or []
    degrading = data.get("degrading") or []
    breakers = data.get("open_breakers") or []
    counts = Text.from_markup(
        f"[{FGDIM}]incidents[/] [{CYAN}]{len(incidents)}[/]   "
        f"[{FGDIM}]degrading[/] [{AMBER}]{len(degrading)}[/]   "
        f"[{FGDIM}]breakers[/] [{RED}]{len(breakers)}[/]"
    )
    lines.append(counts)

    cost = state.get("costs_daily").data
    if isinstance(cost, dict) and cost.get("today_usd") is not None:
        lines.append(Text.from_markup(f"[{FGDIM}]pris i dag[/] [{CYAN}]${cost['today_usd']}[/]"))

    for inc in incidents[:8]:
        msg = str(inc.get("message", ""))
        lines.append(Text.from_markup(f"  [{DIM}]•[/] {msg}"))  # u-trunkeret; panel scroller

    # Join til én Text (newline-separeret) så str(out) eksponerer indholdet;
    # renderer stadig flerlinjet og scroller i panelet.
    out = Text()
    for i, ln in enumerate(lines):
        if i:
            out.append("\n")
        out.append_text(ln)
    return out
