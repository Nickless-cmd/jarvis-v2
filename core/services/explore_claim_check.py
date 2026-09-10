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
_STI_LINJE = re.compile(r"(?:^|[\s`(\[])(/?[\w./-]+\.[A-Za-z0-9_]{1,6}):(\d{1,6})(?::(.*))?")
# Bare filstier med mappe i — et bart "config.py" er for tvetydigt til at dømme.
# `/?` foran: ABSOLUTTE stier blev slet ikke matchet, saa en workstation-rapport
# — der naturligt skriver `/home/bs/projekt/src/main.ts` — gav NUL kontrollerede
# paastande. Vaernet ville have vaeret koblet paa og alligevel blindt.
# URL'er rammes ikke: `https:` fejler paa kolon, og `//host` fejler paa den
# anden skraastreg.
_STI = re.compile(r"(?:^|[\s`(\[])(/?(?:[\w.-]+/)+[\w.-]+\.[A-Za-z0-9_]{1,6})")

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


def tjek_paastande(svar: str, *, rod: Path | None = None,
                   findes_fn=None, linje_fn=None) -> dict[str, object]:
    """Slå svarets efterprøvelige påstande op. Kaster aldrig.

    Returnerer {"kontrolleret": n, "fejl": [...], "holder": bool}. Uden
    efterprøvelige påstande er `kontrolleret` 0 og `holder` True — vi dømmer
    ikke et svar vi ikke kan efterprøve.

    `findes_fn(sti) -> bool | None` slår stier op ET ANDET STED end containerens
    filsystem. Den findes fordi en workstation-explore undersøger BJØRNS
    maskine: `_rod()` peger på containerens repo, så et opslag her ville flage
    HVER eneste sti som opdigtet. Derfor var værnet slået helt fra for
    workstation — og det var rigtigt, men det efterlod den sti hvor en
    fabrikeret rapport koster mest, helt uden værn.

    `None` fra `findes_fn` betyder «kunne ikke afgøres» og tæller hverken som
    fund eller fejl. Et værn der gætter er værre end intet: det ville anklage
    ægte filer for ikke at findes.

    `linje_fn(sti, nr, fragment) -> bool | None` efterprøver et CITAT et andet
    sted. Jarvis foreslog den: `operator_grep` giver fil, linjenummer og tekst
    i ét kald. Målt 10/9-2026 koster et grep 0,08 s — det SAMME som
    eksistens-tjekket, og med mere i svaret. Uden den ville et citat over broen
    kun kunne bekræftes for at filen findes, ikke for at linjen siger det der
    påstås.
    """
    ud: dict[str, object] = {"kontrolleret": 0, "fejl": [], "holder": True}
    try:
        t = str(svar or "")
        if not t.strip():
            return ud
        r = rod or _rod()
        fejl: list[str] = []
        set_stier: set[str] = set()

        def _slaa_op(sti: str) -> bool | None:
            if findes_fn is None:
                return _findes(sti, r)
            try:
                return findes_fn(sti)
            except Exception:
                return None

        for m in _STI_LINJE.finditer(t):
            sti, nr, indhold = m.group(1), int(m.group(2)), (m.group(3) or "").strip()
            if sti.rsplit(".", 1)[-1].lower() not in _KENDTE:
                continue
            set_stier.add(sti)
            _findes_den = _slaa_op(sti)
            if _findes_den is None:
                continue                      # uafgjort — hverken fund eller fejl
            ud["kontrolleret"] = int(ud["kontrolleret"]) + 1
            if not _findes_den:
                fejl.append(f"{sti}: filen findes ikke")
                continue
            if not indhold:
                continue
            if findes_fn is not None:
                # Over broen: ét grep giver baade linjenummer og tekst.
                if linje_fn is None:
                    continue
                kerne = indhold.strip().strip("`").split("(")[0].strip()
                if not kerne:
                    continue
                try:
                    passer = linje_fn(sti, nr, kerne)
                except Exception:
                    passer = None
                if passer is False:
                    fejl.append(f"{sti}:{nr}: linjen indeholder ikke {kerne!r}")
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
            _findes_den = _slaa_op(sti)
            if _findes_den is None:
                continue
            ud["kontrolleret"] = int(ud["kontrolleret"]) + 1
            if not _findes_den:
                fejl.append(f"{sti}: filen findes ikke")

        ud["fejl"] = fejl
        ud["holder"] = not fejl
    except Exception:
        logger.debug("claim-check væltede — dømmer ikke", exc_info=True)
        return {"kontrolleret": 0, "fejl": [], "holder": True}
    return ud
