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


def follow_rabbit(*, seed: int | None = None, observe: bool = True) -> dict[str, Any]:
    """Vælg én uåbnet dør at undre sig over — ren ikke-målrettet udforskning. Self-safe.

    (13/11-2026) To rettelser, begge målt:

    1. **Surfacen skrev til Centralen.** `build_white_rabbit_surface()` kaldte denne
       med `observe=True`, så HVERT prompt-build sendte en `serendipity`-hændelse i
       nerve-strømmen. En læsning skal ikke producere data. Nu er `observe=False`
       standardvejen for surface'en; kun cadence-produceren rapporterer.
    2. **Døren var tilfældig ved hvert kald.** Uden seed gav `random.choice` en NY
       dør hver gang — så behovet skiftede ved hvert prompt-build, livscyklussen blev
       nulstillet hver tur, og han kunne hverken tie eller trække sig. Surfacen seeder
       nu på datoen: samme dør hele dagen, en ny i morgen.
    """
    doors = _dark_doors()
    if not doors:
        return {"door": None, "felt": "Ingen uåbnede døre lige nu — eller også har jeg glemt at kigge."}
    rng = random.Random(seed) if seed is not None else random
    door = rng.choice(doors)
    if observe:
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


def _dag_seed() -> int:
    """Én dør pr. dag — seedet på datoen, ikke på kaldet."""
    import hashlib
    from datetime import UTC, datetime
    dag = datetime.now(UTC).date().isoformat()
    return int(hashlib.md5(dag.encode()).hexdigest()[:8], 16)


def build_white_rabbit_surface() -> dict[str, Any]:
    """Ren læsning: samme dør hele dagen, og INGEN hændelse i nerve-strømmen."""
    return follow_rabbit(seed=_dag_seed(), observe=False)


def record_white_rabbit(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence: ÉN dør om dagen — ikke en ny ved hvert kald.

    (13/11-2026) Målt defekt: produceren kaldte `follow_rabbit()` uden seed, mens
    surface'en seedede på datoen. Så «behovet» skiftede hver gang cadence fyrede —
    et terningkast over 422 døre — og karakteren kunne hverken holde fast i en dør
    eller trække sig fra den. Nu bærer begge veje samme dags-seed.

    Han får INGEN konsekvens-lever, og det er et bevidst fravalg: hans formål er
    «nysgerrighed uden formål». At tvinge en tilfældig dør ind i en bindende
    forpligtelse hver dag ville gøre legen til pligt — og fylde beslutnings-listen
    med 422 meningsløse direktiver. En ærlig tilstand er ikke en død gren.
    """
    r = follow_rabbit(seed=_dag_seed(), observe=True)
    return {"status": "ok", "door": r.get("door"), "lever": "ingen (serendipitet, ikke forpligtelse)"}
