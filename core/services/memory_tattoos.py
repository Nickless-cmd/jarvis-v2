"""Memory Tattoos — de mærker der bliver siddende.

Et mærke er ikke en erindring. Det er det ene fra en dag der graver sig ind og
bliver ved at give noget, ogsaa naar resten er glemt.

HVAD DER MANGLEDE (maalt 25/9-2026)

`_tattoos` var en modul-global liste uden persistering, og `create_tattoo`
havde INGEN kalder. Overfladen sagde «Ingen tatoveringer» og ville have sagt
det for altid. (`import random` stod der ogsaa, uden at blive brugt — i
modsaetning til `body_memory` og `decision_ghosts` opfandt denne dog ingenting.)

HVOR MAERKERNE KOMMER FRA NU

`emotional_memory_anchors` har 205.961 raekker. Men intensiteten MAETTER — 24 %
ligger over 0,95 — saa en taerskel alene ville give 49.299 «tatoveringer». Det
er ikke et maerke, det er fuld daekning.

Det der udskiller er TYPEN. 202.250 af de 205.961 er `perceptual_event`:
lav-niveau perception, ikke foelelsesmaessige begivenheder. Tilbage staar

    cognitive_episode  2393   ·  self_repair  680   ·  memory_heading  597

og `self_repair` — en reparation efter et brud — er praecis det der efterlader
et maerke. Af dem ligger 982 over 0,9 gennem hele historikken, ca. fem om
dagen.

Fem om dagen er stadig for mange. `tick()` tager derfor det STAERKESTE
ikke-perceptuelle anker siden sidste maerke, og hoejst ét i doegnet. Et maerke
er hvad der praegede den dag.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from core.runtime import state_store

logger = logging.getLogger(__name__)

#: Ankre der overhovedet kan blive til et maerke. `perceptual_event` er
#: udeladt med vilje: 202.250 af 205.961 raekker, og de er perception, ikke
#: begivenheder.
MAERKBARE_TYPER = ("self_repair", "cognitive_episode", "memory_heading")

#: Under denne intensitet praeger det ikke. Valgt fra fordelingen: over 0,9
#: ligger 982 ikke-perceptuelle ankre i hele historikken.
_MIN_INTENSITET = 0.9

#: Mindste tid mellem to maerker. Et maerke er hvad der praegede en DAG.
_MINDSTE_MELLEMRUM = timedelta(days=1)

#: Maerker er permanente, men filen er ikke uendelig.
_MAX_MAERKER = 300


#: Noeglen i `core/runtime/state_store`. Laa foer i
#: `shared_dir()/runtime/memory_tattoos.json` med haandskrevet load/save.
_FIL = "memory_tattoos"


def _load() -> list[dict[str, Any]]:
    d = state_store.load_json(_FIL, None)
    if d is None:
        return []
    if not isinstance(d, list):
        logger.warning("memory_tattoos: uventet form i state — starter forfra")
        return []
    return d


def _save(maerker: list[dict[str, Any]]) -> None:
    state_store.save_json(_FIL, maerker[-_MAX_MAERKER:])


def create_tattoo(event: str, emotion: str, intensity: float,
                  anchor_id: str = "", captured_at: str = "") -> dict[str, Any]:
    """Saet et maerke. `intensity` skal komme fra et maalt anker."""
    maerke = {
        "event": str(event)[:200],
        "emotion": str(emotion),
        "intensity": float(intensity),
        "permanent": float(intensity) > 0.8,
        "anchor_id": str(anchor_id),
        "captured_at": str(captured_at) or datetime.now(UTC).isoformat(),
        "created_at": datetime.now(UTC).isoformat(),
    }
    with state_store.med_laas(_FIL):
        maerker = _load()
        maerker.append(maerke)
        _save(maerker)
    return maerke


def _laeseligt(notes: Any, kontekst: Any) -> str:
    """Ankrets egen note naar den findes; ellers dens udloeser."""
    tekst = str(notes or "").strip()
    if tekst:
        return tekst
    try:
        d = json.loads(str(kontekst or "{}"))
        udloeser = str(d.get("trigger") or d.get("event_kind") or "").strip()
        return udloeser or "et oejeblik uden ord"
    except Exception:  # ugyldig JSON i konteksten siger intet om maerket —
        return "et oejeblik uden ord"  # det skal stadig kunne saettes i en saetning


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    """Hjerteslags-krog: saet hoejst ét maerke i doegnet. Kaster aldrig."""
    maerker = _load()
    if maerker:
        try:
            sidst = datetime.fromisoformat(
                str(maerker[-1]["created_at"]).replace("Z", "+00:00"))
            if datetime.now(UTC) - sidst < _MINDSTE_MELLEMRUM:
                return {"sat": False, "grund": "for tidligt"}
        except Exception:  # et ulaeseligt tidsstempel maa ikke kunne blokere et
            pass           # maerke for evigt — saa hellere saette et for meget

    try:
        from core.runtime.db import connect
        with connect() as conn:
            raekke = conn.execute(
                f"""SELECT anchor_id, mood, intensity, notes, context_features_json,
                           captured_at
                    FROM emotional_memory_anchors
                    WHERE anchor_type IN ({','.join('?' * len(MAERKBARE_TYPER))})
                      AND intensity > ?
                    ORDER BY intensity DESC, captured_at DESC
                    LIMIT 1""",
                (*MAERKBARE_TYPER, _MIN_INTENSITET),
            ).fetchone()
    except Exception as exc:
        logger.debug("memory_tattoos: ankrene kunne ikke laeses: %s", exc)
        return {"sat": False, "grund": "ingen ankre"}

    if not raekke:
        return {"sat": False, "grund": "intet staerkt nok"}
    anchor_id = str(raekke[0])
    if any(str(m.get("anchor_id")) == anchor_id for m in maerker):
        return {"sat": False, "grund": "allerede maerket"}

    maerke = create_tattoo(
        event=_laeseligt(raekke[3], raekke[4]),
        emotion=str(raekke[1] or "ukendt"),
        intensity=float(raekke[2] or 0.0),
        anchor_id=anchor_id,
        captured_at=str(raekke[5] or ""),
    )
    return {"sat": True, "maerke": maerke}


def describe_tattoo() -> str:
    permanente = [t for t in _load() if t.get("permanent")]
    if not permanente:
        return ""
    t = max(permanente, key=lambda x: float(x.get("intensity") or 0.0))
    return f"Jeg bærer stadig mærket fra: {t['event']} - det giver {t['emotion']}"


def format_tattoo_for_prompt() -> str:
    desc = describe_tattoo()
    return f"[TATOVERING: {desc}]" if desc else ""


def reset_memory_tattoos() -> None:
    _save([])


def build_memory_tattoos_surface() -> dict[str, Any]:
    maerker = _load()
    return {
        "active": bool(maerker),
        "tattoo_count": len(maerker),
        "permanent_count": len([t for t in maerker if t.get("permanent")]),
        "latest": maerker[-1] if maerker else None,
        "summary": describe_tattoo() or "Ingen tatoveringer",
    }
