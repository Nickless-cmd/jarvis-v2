"""Tjek explore-agentens påstande mod virkeligheden.

Bjørn 7/9-2026: «burde der ikke være et værn i explore der kan checke
påstande, og rotere model hvis en påstand ikke holder?»

Ja — og det er stærkere end alt jeg forsøgte forinden. Jeg brugte dagen på at
forudsige om en model VILLE lyve (syntetiske prøver, gentagne kørsler,
opdigt-detektor). `copilot-free/gpt-4.1` bestod dem alle og løj i produktion
alligevel. Men explore's påstande er af en helt særlig slags: de er
**efterprøvelige**. En filsti findes eller findes ikke. Linje 12 indeholder
det den siger, eller gør ikke.

Så vi behøver ikke gætte på modellen. Vi kan slå svaret op.

## Hvad der tjekkes

1. **Filstier** — hver nævnt sti skal findes. Fangede
   `src/jarvis/providers/provider_router.py`, som aldrig har eksisteret.
2. **sti:linje:indhold** — linjen skal findes OG bære indholdet. Fangede
   `provider_router.py:12:def route_provider_request`, hvor linje 12 er noget
   helt andet.

## Hvad der IKKE tjekkes

Prosa. En påstand som «nøglerne læses dynamisk» kan ikke slås op, og et værn
der forsøgte ville afvise gyldige svar. Vi tjekker kun det der ER
efterprøveligt — og et svar uden efterprøvelige påstande får ingen dom.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# `sti:linje:indhold` — den form `search` selv returnerer, og dermed den form
# agenten citerer i.
_STI_LINJE = re.compile(r"(?:^|[\s`(\[])(?:\./)?([\w./-]+\.[A-Za-z0-9_]{1,6}):(\d{1,6})(?::(.*))?")
# Bare filstier med mappe i — et bart "config.py" er for tvetydigt til at dømme.
_STI = re.compile(r"(?:^|[\s`(\[])(?:\./)?((?:[\w.-]+/)+[\w.-]+\.[A-Za-z0-9_]{1,6})")

# Endelser vi kan udtale os om. En sti til noget der ikke er en kildefil
# (fx en URL-agtig streng) skal ikke give falske anklager.
_KENDTE = frozenset({"py", "ts", "tsx", "js", "json", "md", "toml", "yaml", "yml",
                     "sh", "kt", "sql", "cfg", "ini", "txt", "gradle"})


def _rod() -> Path:
    try:
        from core.tools.simple_tools import PROJECT_ROOT
        return Path(str(PROJECT_ROOT))
    except Exception:
        return Path.cwd()


def _findes(sti: str, rod: Path) -> bool:
    p = Path(sti)
    if p.is_absolute():
        return p.exists()
    return (rod / sti).exists()


def tjek_paastande(svar: str, *, rod: Path | None = None) -> dict[str, object]:
    """Slå svarets efterprøvelige påstande op. Kaster aldrig.

    Returnerer {"kontrolleret": n, "fejl": [...], "holder": bool}. Uden
    efterprøvelige påstande er `kontrolleret` 0 og `holder` True — vi dømmer
    ikke et svar vi ikke kan efterprøve.
    """
    ud: dict[str, object] = {"kontrolleret": 0, "fejl": [], "holder": True}
    try:
        t = str(svar or "")
        if not t.strip():
            return ud
        r = rod or _rod()
        fejl: list[str] = []
        set_stier: set[str] = set()

        for m in _STI_LINJE.finditer(t):
            sti, nr, indhold = m.group(1), int(m.group(2)), (m.group(3) or "").strip()
            if sti.rsplit(".", 1)[-1].lower() not in _KENDTE:
                continue
            set_stier.add(sti)
            ud["kontrolleret"] = int(ud["kontrolleret"]) + 1
            if not _findes(sti, r):
                fejl.append(f"{sti}: filen findes ikke")
                continue
            if not indhold:
                continue
            try:
                linjer = (r / sti if not Path(sti).is_absolute() else Path(sti)).read_text(
                    encoding="utf-8", errors="replace").splitlines()
            except Exception:
                continue
            if nr < 1 or nr > len(linjer):
                fejl.append(f"{sti}:{nr}: filen har kun {len(linjer)} linjer")
                continue
            # Sammenlign på et NØGENT fragment: modellen omskriver ofte
            # whitespace og klipper linjen. Vi kræver at det den citerer,
            # findes i linjen — ikke at strengene er identiske.
            kerne = indhold.strip().strip("`").split("(")[0].strip()
            if kerne and kerne not in linjer[nr - 1]:
                fejl.append(f"{sti}:{nr}: linjen indeholder ikke {kerne!r}")

        for m in _STI.finditer(t):
            sti = m.group(1)
            if sti in set_stier or sti.rsplit(".", 1)[-1].lower() not in _KENDTE:
                continue
            set_stier.add(sti)
            ud["kontrolleret"] = int(ud["kontrolleret"]) + 1
            if not _findes(sti, r):
                fejl.append(f"{sti}: filen findes ikke")

        ud["fejl"] = fejl
        ud["holder"] = not fejl
    except Exception:
        logger.debug("claim-check væltede — dømmer ikke", exc_info=True)
        return {"kontrolleret": 0, "fejl": [], "holder": True}
    return ud
