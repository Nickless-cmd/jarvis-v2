from __future__ import annotations

import json
from typing import Any

from rich.panel import Panel
from rich.table import Table
from rich.console import Group

_STATUS_COLOR = {"green": "green", "yellow": "yellow", "red": "red"}


def render_status(data: dict) -> Panel:
    status = str(data.get("status") or "?")
    breakers = data.get("open_breakers") or []
    incidents = data.get("incidents") or []
    tbl = Table(show_header=True, header_style="bold cyan")
    tbl.add_column("sev"); tbl.add_column("cluster/nerve"); tbl.add_column("besked")
    for i in incidents[:50]:
        tbl.add_row(str(i.get("severity") or ""),
                    f"{i.get('cluster')}/{i.get('nerve')}",
                    str(i.get("message") or "")[:80])
    head = f"[bold]STATUS:[/bold] {status}  |  breakers: {len(breakers)}  |  incidents: {len(incidents)}"
    return Panel(Group(head, tbl), title="◈ CENTRAL", border_style=_STATUS_COLOR.get(status, "cyan"))


def render_generic(data: Any) -> Panel:
    return Panel(json.dumps(data, indent=2, ensure_ascii=False, default=str), title="output", border_style="cyan")
