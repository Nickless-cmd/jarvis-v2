"""En FEJLET agent-koersel skal stadig baere sin leverance i `output_summary`.

MAALT 27/10-2026 i den levende DB (`~/.jarvis-v2/state/jarvis.db`):

    status              error_code        antal   tomme output_summary
    completed           -                 9       0
    failed              -                 4       4
    failed              AGENT_INCOMPLETE  2       2

Seks af seks fejlede koersler havde en TOM summary. Aarsagen stod i
`agent_runtime_spawn.py`: succes-stien satte `output_summary=_resume`, fejl-stien
satte kun `failure_reason`. `scout_inbox_delivery` laeser praecis `output_summary`
(med `last_error` som reserve), saa modtageren fik fejlmarkeringen i stedet for
leverancen — Bjoerns klage: «der er ingen steder at se hvad den session leverede».

Vagten parser AST'en i stedet for at grepe efter en streng: en grep ville ogsaa
matche den KOMMENTAR der forklarer fejlen, og saa vaere groen uden at maale noget.
Den kraever at HVERT `update_agent_run(...)`-kald med `status="failed"` baerer
`output_summary` — saa en ny fejlsti ikke kan genindfoere tavsheden.
"""

from __future__ import annotations

import ast
from pathlib import Path

_KILDE = Path(__file__).resolve().parents[1] / "core/services/agent_runtime_spawn.py"


def _kalde(run: ast.AST, navn: str) -> list[ast.Call]:
    return [n for n in ast.walk(run)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id == navn]


def _kw(call: ast.Call, navn: str) -> ast.expr | None:
    for k in call.keywords:
        if k.arg == navn:
            return k.value
    return None


def _er_streng(node: ast.expr | None, vaerdi: str) -> bool:
    return isinstance(node, ast.Constant) and node.value == vaerdi


def test_hver_fejlsti_baerer_en_output_summary() -> None:
    trae = ast.parse(_KILDE.read_text(encoding="utf-8"))
    fejl_kald = [c for c in _kalde(trae, "update_agent_run")
                 if _er_streng(_kw(c, "status"), "failed")]
    # Findes der slet ingen fejlsti, maaler testen ingenting — det skal den sige.
    assert fejl_kald, "fandt ingen update_agent_run(status='failed') — vagten maaler intet"

    uden = [c.lineno for c in fejl_kald if _kw(c, "output_summary") is None]
    assert not uden, (
        "update_agent_run(status='failed') uden output_summary paa linje "
        f"{uden}: en fejlet koersel mister sin leverance, og indbakken viser "
        "fejlmarkeringen i stedet for hvad agenten naaede"
    )
