"""TTFT og tokens/sekund — målt hos OS, ikke hentet hos udbyderen.

Bjørn 4/10-2026: «kan vi få ttft og tok/s på? kan vi få det fra deepseek apien
eller helst vores egen da andre bruger snakker med ham via ollama cloud.»

## Hvorfor vores egen

Fordi det er det eneste der kan sammenlignes. TTFT er per definition en
vægur-observation — tiden fra vi sendte spørgsmålet til det første stykke
indhold kom tilbage — og den kræver ingen hjælp fra udbyderen. Spurgte vi
DeepSeek, fik vi DeepSeeks tal i DeepSeeks form; spurgte vi Ollama Cloud, fik
vi noget andet eller ingenting, og de to tal ville ikke betyde det samme.

Målt 4/10 i huset: der fandtes INGEN TTFT-måling nogen steder. Det tætteste er
`visible_followup_adapters.got_first_byte` — en vagthund med et 90-sekunders
budget, som ved HVORNÅR det første byte kom, men aldrig har gemt hvor lang tid
det tog. Visningen fandtes dog allerede: `Composer.tsx` har tegnet «TTFT —  ·
— tok/s» hele tiden, fordi `koerselsTal` aldrig satte felterne. Endnu et
tilfælde af at fladen var bygget og produceren manglede.

## Hvad de to tal ER

* **TTFT** = første indholds-token minus start. «Hvor længe sad jeg og kiggede
  på ingenting.» Tænke-tokens tæller MED som indhold — de er det første man
  ser, og en TTFT der ignorerede dem ville sige 14 s om noget der føltes som 2.
* **tok/s** = output-tokens delt med tiden fra FØRSTE token til sidste, ikke
  med hele turen. Tog TTFT'en 10 af 12 sekunder, er skrivehastigheden de to —
  divideres der med 12, straffes modellen for en ventetid den allerede er målt
  på. To tal der måler hver sit er mere brugbare end ét der blander dem.

## Hvorfor den ikke kan vælte en tur

Samme kontrakt som `turn_tail_timing`: modulet holder kun et dict, alt er
fail-safe, og et run der aldrig når sin slutning lækker ikke — der er et loft.
Et måleinstrument der kan ødelægge det det måler er værre end ingen måling.
"""
from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

#: Loft på antallet af runs vi holder styr på ad gangen. Et run der dør uden
#: `afslut` ville ellers blive liggende for evigt — samme fælde `turn_tail_timing`
#: lukkede med sit `_MAKS`.
_MAKS: int = 64

#: run_id -> {"start": float, "foerste": float | None, "tokens": int}
_tempi: dict[str, dict[str, Any]] = {}


def start(run_id: str) -> None:
    """Uret begynder. Kaldes når turen går mod udbyderen."""
    rid = str(run_id or "").strip()
    if not rid:
        return
    if len(_tempi) >= _MAKS:
        # Ældste ud. En fejlet oprydning må ikke blive en hukommelses-lækage,
        # og et tabt måletal er billigere end et run der ikke kan starte.
        try:
            _tempi.pop(next(iter(_tempi)))
        except Exception:  # noqa: BLE001 — tom dict i et kapløb; intet at rydde
            pass
    _tempi[rid] = {"start": time.monotonic(), "foerste": None, "tokens": 0}


def foerste_token(run_id: str) -> None:
    """Det første stykke INDHOLD er på vej ud. Idempotent.

    Idempotent med vilje: kalderen står i en delta-løkke og kan ikke selv vide
    om dette er den første. Skulle den det, ville hver kalder have sin egen
    `if første`, og dén slags kopi driver fra hinanden.
    """
    d = _tempi.get(str(run_id or "").strip())
    if d is not None and d.get("foerste") is None:
        d["foerste"] = time.monotonic()


def afslut(run_id: str, *, output_tokens: int = 0) -> dict[str, float | None]:
    """Luk målingen. `{"ttft_ms": …, "tok_per_sek": …}` — None hvor ukendt.

    `None`, ikke 0: et nul ville tegne «TTFT 0ms» i composeren og se ud som et
    måleresultat. Den manglende værdi er sin egen tilstand, og klienten viser
    allerede en tankestreg for den.
    """
    d = _tempi.pop(str(run_id or "").strip(), None)
    if d is None:
        return {"ttft_ms": None, "tok_per_sek": None}
    nu = time.monotonic()
    foerste = d.get("foerste")
    ttft_ms = round((foerste - d["start"]) * 1000.0, 1) if foerste else None

    tokens = int(output_tokens or d.get("tokens") or 0)
    tok_per_sek: float | None = None
    if foerste is not None and tokens > 0:
        # Skrivetiden, ikke turen: fra første token til nu. Se modulets
        # docstring for hvorfor TTFT ikke må tælle med i nævneren.
        skrivetid = nu - foerste
        if skrivetid > 0.05:
            # Under 50 ms er nævneren ren støj — ét enkelt token der ankom
            # samtidig med at turen sluttede ville give «4000 tok/s».
            tok_per_sek = round(tokens / skrivetid, 1)
    return {"ttft_ms": ttft_ms, "tok_per_sek": tok_per_sek}


def glem(run_id: str) -> None:
    """Smid en måling væk uden at aflæse den — fx når et run annulleres."""
    _tempi.pop(str(run_id or "").strip(), None)


__all__ = ["start", "foerste_token", "afslut", "glem"]
