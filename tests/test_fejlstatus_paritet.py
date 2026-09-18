"""Server og desk skal vaere enige om hvad en fejl er.

Desk afgoer live om et kald fejlede (`FEJL_STATUS` i streamReducer.ts);
serveren afgoer det naar turen gemmes (`FEJL_STATUSSER`). 18/9-2026 var de
uenige: desk regnede blocked/timeout/cancelled som fejl, serveren ikke. Og
serveren gemte alligevel alt som «done». Resultat: en fejl stod alene i traaden
og blev til en succes ved genindlaesning.

Testen laeser desk-filen direkte, saa en aendring paa den ene side uden den
anden falder her.
"""
from __future__ import annotations

import re
from pathlib import Path

from core.services.visible_followup_events import FEJL_STATUSSER

_DESK = Path(__file__).resolve().parents[1] / "apps/jarvis-desk/src/lib/streamReducer.ts"


def test_server_og_desk_har_samme_fejl_maengde() -> None:
    kilde = _DESK.read_text(encoding="utf-8")
    m = re.search(r"const FEJL_STATUS = new Set\(\[([^\]]*)\]\)", kilde)
    assert m, "FEJL_STATUS blev ikke fundet i streamReducer.ts — er den flyttet?"
    desk = set(re.findall(r"'([^']+)'", m.group(1)))
    assert desk == set(FEJL_STATUSSER)
