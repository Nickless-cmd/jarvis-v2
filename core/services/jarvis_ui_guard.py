"""Normaliserer og validerer ``jarvis-ui``-blokke FØR de når chatten.

Baggrund (målt 24/10-2026, Bjørn): tre svar i træk fejlede i chatview, og
årsagen var ikke rendereren. To forskellige fejl, begge i MIN tekst:

1. id 220068 (21:43): ``],"}"`` hvor der skulle stå ``]}`` — ugyldig JSON.
   Parserens fejl: ``Expecting ':' delimiter: line 1 column 265``.
2. id 220247 (22:02): JSON'en var gyldig (2 kolonner, 4 rækker, alle
   ``values`` 2 lange), men den stod på SAMME LINJE som fence-markøren:
   ```` ```jarvis-ui {"type":… ````. I CommonMark bliver hele resten af
   linjen en del af info-stringen, så rendereren ser ikke sproget
   ``jarvis-ui`` — og blokken falder tilbage til rå kode.

Fejl nummer to er den farligste, fordi JSON'en er korrekt: enhver validering
der kun kigger på dataene siger «OK», mens brugeren ser rå tekst.

Derfor normaliserer dette modul FORMEN først (JSON på sin egen linje, lukke-
fence på sin egen linje), derefter retter det de entydige JSON-fejl, og
derefter validerer det. Rækkefølgen er ikke tilfældig: en validering der
kører før normaliseringen kan ikke se fejl nummer to.

Reparationerne er bevidst smalle. Kun mønstre der ALDRIG er gyldig JSON
rettes — ``],"}"``, dobbelt komma, trailing komma før ``}``/``]``. Alt andet
lader vi stå: en vagt der gætter forkert og «reparerer» ødelægger et svar der
var i orden, og det er værre end den fejl den skulle fange.

Fail-open overalt: enhver fejl her må aldrig påvirke et svar.
"""

from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)

_FENCE_OPEN = re.compile(r"```jarvis-ui[ \t]*")
#: Et helt fence-område, uanset om JSON'en står på markørens linje.
_FENCE_BLOK = re.compile(r"```jarvis-ui[ \t]*(.*?)```", re.S)

#: Mønstre der aldrig kan være gyldig JSON. Hver reparation er smal og entydig.
_REPARATIONER: tuple[tuple[re.Pattern[str], str], ...] = (
    # `],"}"` → `]}` — den målte fejl fra 220068 (citationstegn efter komma).
    (re.compile(r'\]\s*,\s*"\s*\}'), "]}"),
    # `},"}` → `}}` — samme fejl på objekt-niveau.
    (re.compile(r'\}\s*,\s*"\s*\}'), "}}"),
    # `,]` og `,}` — trailing komma.
    (re.compile(r",\s*\]"), "]"),
    (re.compile(r",\s*\}"), "}"),
    # `,,` — dobbelt komma.
    (re.compile(r",\s*,"), ","),
)


def _normaliser_form(raw: str) -> str:
    """Flyt JSON'en ned på sin egen linje og lukke-fencen på sin egen linje.

    Dette er den reparation der løser den målbare fejl fra 220247: når JSON'en
    står på markørens linje, bliver den en del af info-stringen og blokken
    renderes som rå kode.
    """
    indhold = raw.strip()
    if not indhold:
        return ""
    return f"```jarvis-ui\n{indhold}\n```"


def _reparer_json(tekst: str) -> str:
    """Ret de entydige JSON-fejl. Rører intet der allerede er gyldigt."""
    ud = tekst
    for moenster, erstatning in _REPARATIONER:
        ud = moenster.sub(erstatning, ud)
    return ud


def _validér(tekst: str) -> tuple[bool, str]:
    try:
        data = json.loads(tekst)
    except Exception as fejl:
        return False, str(fejl)
    if not isinstance(data, dict):
        return False, "blokken er ikke et JSON-objekt"
    if not data.get("type"):
        return False, "blokken mangler 'type'"
    # comparison er den eneste type med en strukturel længdekrav.
    if data.get("type") == "comparison":
        kolonner = data.get("columns") or []
        for i, raekke in enumerate(data.get("rows") or []):
            vaerdier = raekke.get("values") or []
            if len(vaerdier) != len(kolonner):
                return False, (
                    f"række {i} har {len(vaerdier)} values, "
                    f"men der er {len(kolonner)} kolonner"
                )
    return True, ""


def normalisér(text: str, *, run_id: str = "") -> str:
    """Normalisér alle ``jarvis-ui``-blokke i teksten. Returnerer ny tekst.

    Kun formen ændres når JSON'en er gyldig (eller kan repareres). Kan den
    ikke repareres, får blokken lov at stå som almindelig kode — en flade der
    ikke kan parses må ikke se ud som en flade.
    """
    if not text or "```jarvis-ui" not in text:
        return text
    try:
        return _normalisér_indre(text, run_id=run_id)
    except Exception:
        logger.debug("jarvis_ui_guard: normalisering fejlede", exc_info=True)
        return text


def _normalisér_indre(text: str, *, run_id: str) -> str:
    aendringer: list[str] = []

    def _erstat(match: re.Match[str]) -> str:
        indhold = match.group(1).strip()
        if not indhold:
            return match.group(0)
        gyldig, fejl = _validér(indhold)
        if not gyldig:
            repareret = _reparer_json(indhold)
            gyldig2, fejl2 = _validér(repareret)
            if gyldig2:
                aendringer.append(f"json repareret: {fejl}")
                indhold = repareret
            else:
                # Kan ikke repareres: lad den stå som almindelig kode, så den
                # ikke ligner en flade der fejlede.
                aendringer.append(f"json ugyldig, degraderet: {fejl2}")
                return f"```text\n{indhold}\n```"
        elif "\n" in match.group(1).strip() or match.group(1).strip() != match.group(1):
            aendringer.append("form normaliseret")
        # Tjek om formen var skæv (JSON på markørens linje).
        raa = match.group(1)
        if raa and not raa.startswith("\n"):
            aendringer.append("form normaliseret (json på markørens linje)")
        return _normaliser_form(indhold)

    ny = _FENCE_BLOK.sub(_erstat, text)
    if aendringer and ny != text:
        _registrér(aendringer, run_id=run_id)
    return ny


def _registrér(aendringer: list[str], *, run_id: str) -> None:
    try:
        from core.runtime.db_central_incidents import record_central_incident

        record_central_incident(
            cluster="runtime",
            nerve="chat_surface_normalised",
            kind="jarvis_ui_repaired",
            severity="info",
            message=(
                f"jarvis-ui normaliseret ({len(aendringer)}): "
                f"{'; '.join(sorted(set(aendringer)))[:300]} "
                f"(run={run_id or 'ukendt'})"
            ),
            dedup=True,
        )
    except Exception:
        logger.debug("jarvis_ui_guard: kunne ikke registrere hændelse", exc_info=True)
