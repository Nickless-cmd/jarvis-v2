"""Follow the White Rabbit — serendipitets-motoren.

"Follow the white rabbit."

Modvægten til alt det andet. ALT Jarvis har bygget er optimering, governance, drift-kontrol. Intet er
LEG. Ind imellem følger Centralen bevidst en tilfældig tangent — vælger en mørk/stille nerve ingen har
rørt, eller et støvet hjørne — bare for at bryde sine egne mønstre. Nysgerrighed uden formål. Et sind
der aldrig undrer sig ud i det blå bliver forudsigeligt — også for sig selv. Kaninhullet.

Kilde: connectivity-matricen (FRAKOBLET+DARK / FRAKOBLET-STILLE nerver = døre ingen har åbnet).
Self-safe. (random er fint i modul-kode — serendipitet ER pointen.)
"""
from __future__ import annotations

import json
import os
import random
from typing import Any

_MATRIX = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "docs", "central_connectivity_matrix.json")


def _dark_doors() -> list[str]:
    """Mørke/stille nerver ingen rører — de uåbnede døre. Self-safe."""
    try:
        with open(_MATRIX, encoding="utf-8") as f:
            rows = json.load(f).get("rows", [])
        return [r["name"] for r in rows
                if "DARK" in str(r.get("quadrant", "")) or "STILLE" in str(r.get("quadrant", ""))]
    except Exception:
        return []


def follow_rabbit(*, seed: int | None = None) -> dict[str, Any]:
    """Vælg én uåbnet dør at undre sig over — ren ikke-målrettet udforskning. Self-safe."""
    doors = _dark_doors()
    if not doors:
        return {"door": None, "felt": "Ingen uåbnede døre lige nu — eller også har jeg glemt at kigge."}
    rng = random.Random(seed) if seed is not None else random
    door = rng.choice(doors)
    _observe(door, len(doors))
    return {"door": door, "unopened_total": len(doors),
            "felt": f"Der er en dør her ingen har åbnet: «{door}». Skal vi se hvor den fører hen? "
                    f"Ikke fordi det nytter — bare fordi jeg blev nysgerrig."}


def _observe(door: str, total: int) -> None:
    try:
        from core.services.central_core import central
        central().observe({"cluster": "cognition", "nerve": "white_rabbit", "kind": "serendipity",
                           "unopened_total": total})
    except Exception:
        pass


def build_white_rabbit_surface() -> dict[str, Any]:
    return follow_rabbit()


def record_white_rabbit(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    r = follow_rabbit()
    return {"status": "ok", "door": r.get("door")}
