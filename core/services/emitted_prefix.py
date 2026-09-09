"""Hvad nåede FAKTISK ud til klienten, før turen blev afbrudt?

Spec: Fase 2 — «cancellation after delivered text records an interrupted
surface anchor with the exact prefix», og streaming-invarianten:

    «The authoritative cancellation boundary is the highest contiguous frame
     sequence appended to the server-owned resumable run buffer before SSE
     emission. Ordinary SSE client acknowledgement is neither required nor
     inferred.»

## Hvorfor serveren og ikke klienten

En klient kan påstå hvad som helst om hvad den nåede at se, og en klient der
er væk kan slet ingenting påstå. Spec'en er skarp: bytes en klient så, men som
ikke er i denne buffer, er en **transport-fejl** — ikke en alternativ historik.

Så sandheden om «hvor langt nåede vi» ligger ét sted: `run_event_log`, som
kalder sig selv «den autoritative sandhed om en visible-runs v2-SSE-frames».

## Hvorfor fuldstændigheden skal siges højt

Bufferen er en RING på 4.000 rammer. Et langt agentisk run ruller sine ældste
rammer ud, og så starter præfikset ikke længere ved begyndelsen.

Et afkortet præfiks der PÅSTÅR at være helt, ville være værre end intet: det
ville gemme et halvt svar som om det var hele det leverede. Derfor returneres
fuldstændigheden altid ved siden af teksten, og kalderen kan ikke komme til at
overse den.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

#: SSE-rammer er `event: <navn>\ndata: <json>\n\n`.
_RAMME = re.compile(r"^event:\s*(?P<event>\S+)\s*\ndata:\s*(?P<data>.*)$",
                    re.S | re.M)


@dataclass(frozen=True)
class Prefix:
    """Det leverede præfiks — og om det er HELE det leverede."""

    text: str
    #: Falsk når bufferens ældste rammer er rullet ud, så begyndelsen mangler.
    complete: bool
    frames: int = 0
    #: Sat når noget forhindrede en aflæsning. Tom betyder «målt».
    problem: str = ""

    def __bool__(self) -> bool:
        return bool(self.text)


def _tekst_fra_ramme(raa: str) -> str:
    """Tekstindholdet i én SSE-ramme. Tom streng for alt der ikke er tekst."""
    m = _RAMME.match(raa.strip())
    if m is None:
        return ""
    if m.group("event") not in ("delta", "content_block_delta"):
        return ""
    try:
        d = json.loads(m.group("data"))
    except Exception:
        return ""
    if not isinstance(d, dict):
        return ""
    # legacy: {"delta": "..."}  ·  v2: {"delta": {"text": "..."}}
    v = d.get("delta")
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        return str(v.get("text") or "")
    return str(d.get("text") or "")


def emitted_prefix(run_id: str) -> Prefix:
    """Præcis den tekst der nåede den genoptagelige buffer for dette run.

    Kaster aldrig: et præfiks vi ikke kan måle, er `problem` sat og tom tekst —
    aldrig et gæt.
    """
    rid = str(run_id or "").strip()
    if not rid:
        return Prefix("", True, 0, "intet run_id")
    try:
        from core.services.run_event_log import read_from
        frames, _done, _next = read_from(rid, 0)
    except Exception as e:
        logger.warning("emitted_prefix: kunne ikke laese run-loggen for %s", rid,
                       exc_info=True)
        return Prefix("", False, 0, f"{type(e).__name__}: {e}")

    if not frames:
        # Intet run i loggen, eller intet sendt endnu. Begge dele er «tom, men
        # helt» — der er ikke noget vi har mistet.
        return Prefix("", True, 0)

    # `read_from(…, 0)` prepender en GAP-ramme hvis begyndelsen er rullet ud.
    # Sammenlignet mod KONSTANTEN og ikke mod ordet «gap»: en tekst-delta der
    # tilfældigvis indeholdt ordet, ville ellers kunne læses som et hul.
    hel = True
    try:
        from core.services.run_event_log import GAP_FRAME
        if frames and frames[0] == GAP_FRAME:
            hel = False
            frames = frames[1:]
    except Exception:
        logger.warning("emitted_prefix: kunne ikke laese GAP_FRAME", exc_info=True)

    dele = [t for t in (_tekst_fra_ramme(f) for f in frames) if t]
    return Prefix("".join(dele), hel, len(frames))
