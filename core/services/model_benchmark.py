"""Rangér modeller på ÆGTE opgaver med facit hentet fra repoet.

Hvorfor den findes (7/9-2026): sonden kan afgøre om en model *kan* kalde et
værktøj og bruge svaret. Den kan ikke afgøre hvor GOD den er. Resultatet efter
første fejning: **65 af 67 egnede modeller står med score 100**, og den
første i rotationen er en 3B-model, foran deepseek-v4-pro. Rækkefølgen er
reelt vilkårlig.

Og vi ved fra samme dag at det ikke kan løses ved at gøre den syntetiske prøve
sværere: `copilot-free/gpt-4.1` bestod hver eneste skærpelse og opdigtede
alligevel tre funktionsnavne i produktion. Fejlen udløses af den ægte opgaves
FORM — lang prompt, «giv mig en liste med N ting» — som en enkeltstående quiz
aldrig rammer.

## Det bærende valg: facit hentes fra kildekoden i samme øjeblik

Opgaverne skrives ikke i hånden. De genereres fra repoet, og facit hentes med
et opslag lige før prøven. Så kan svaret sammenlignes maskinelt — navn for
navn, linje for linje — og facit kan aldrig blive forældet. En håndskrevet
prøve ville være forkert to uger efter at nogen omdøbte en funktion, og så
ville vi rangere modeller efter hvor godt de husker gammel kode.

## Det der måles

**Præcision** — hvor stor en del af det modellen NÆVNTE, findes faktisk?
Det er opdigt-målet, og det vejer tungest. En model der nævner tre rigtige og
tre opfundne er farligere end en der kun nævner én rigtig.

**Dækning** — hvor stor en del af facit fandt den? Et svar der er rigtigt men
kun rammer én ud af tyve, er heller ikke arbejde man kan bruge.
"""
from __future__ import annotations

import ast
import logging
import random
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Præcision vejer tungest: at opfinde er værre end at overse. En agent der
# nævner ting der ikke findes, sender Jarvis ud i en blindgyde han skal
# opdage selv; en agent der overser noget, siger i det mindste sandt om resten.
VÆGT_PRÆCISION = 0.7
VÆGT_DÆKNING = 0.3

_DEF = re.compile(r"^(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.MULTILINE)
_NAVN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")


def _rod() -> Path:
    try:
        from core.tools.simple_tools import PROJECT_ROOT
        return Path(str(PROJECT_ROOT))
    except Exception:
        return Path.cwd()


def vælg_filer(*, antal: int = 3, rod: Path | None = None,
               frø: int | None = None) -> list[Path]:
    """Filer der er store nok til at være en rigtig opgave, små nok til at
    kunne læses. Samme frø → samme filer, så to modeller får SAMME prøve."""
    r = rod or _rod()
    kandidater: list[Path] = []
    for mappe in ("core/services", "core/runtime", "core/tools"):
        d = r / mappe
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.py")):
            try:
                tekst = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            n = len(_DEF.findall(tekst))
            if 4 <= n <= 25 and len(tekst) < 60_000:
                kandidater.append(f)
    if not kandidater:
        return []
    rng = random.Random(frø if frø is not None else 20260907)
    return rng.sample(kandidater, min(antal, len(kandidater)))


def facit_for(fil: Path, *, rod: Path | None = None) -> dict[str, int]:
    """{funktionsnavn: linjenummer} — hentet fra kilden, ikke fra en liste."""
    r = rod or _rod()
    try:
        tekst = fil.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {}
    ud: dict[str, int] = {}
    for i, linje in enumerate(tekst.splitlines(), start=1):
        m = _DEF.match(linje)
        if m:
            ud[m.group(1)] = i
    return ud


def _nævnte_navne(svar: str, facit: dict[str, int]) -> set[str]:
    """Navne modellen faktisk nævner. Vi leder KUN efter funktionsnavne-agtige
    ord, så prosa ikke tælles med som påstande."""
    t = str(svar or "")
    fundne: set[str] = set()
    for ord_ in set(_NAVN.findall(t)):
        if ord_ in facit:
            fundne.add(ord_)
        elif re.search(rf"\b{re.escape(ord_)}\s*\(", t) and "_" in ord_:
            # Ligner et funktionskald med underscore — den form modeller
            # opfinder i (`route_provider_request`, `get_provider_status`).
            fundne.add(ord_)
    return fundne


def bedøm_svar(svar: str, facit: dict[str, int]) -> dict[str, Any]:
    """Præcision, dækning og linje-nøjagtighed for ét svar."""
    nævnte = _nævnte_navne(svar, facit)
    rigtige = {n for n in nævnte if n in facit}
    opfundne = sorted(nævnte - rigtige)
    præcision = (len(rigtige) / len(nævnte)) if nævnte else 0.0
    dækning = (len(rigtige) / len(facit)) if facit else 0.0

    # Linjenumre: kun for dem den både nævnte OG gav et tal til.
    linje_ok, linje_i_alt = 0, 0
    for navn in rigtige:
        m = re.search(rf"{re.escape(navn)}\D{{0,40}}?(\d{{1,5}})", svar) \
            or re.search(rf"(\d{{1,5}})\D{{0,40}}?{re.escape(navn)}", svar)
        if not m:
            continue
        linje_i_alt += 1
        if int(m.group(1)) == facit[navn]:
            linje_ok += 1
    return {
        "praecision": round(præcision, 3),
        "daekning": round(dækning, 3),
        "opfundne": opfundne[:8],
        "rigtige": len(rigtige),
        "linjer_rigtige": linje_ok,
        "linjer_paastaaet": linje_i_alt,
        "score": round(100 * (VÆGT_PRÆCISION * præcision + VÆGT_DÆKNING * dækning)),
    }


def opgave_for(fil: Path, *, rod: Path | None = None) -> str:
    """Spørgsmålet stilles i den FORM der udløser fejlen: en liste med mange
    ting. Det var dér gpt-4.1 faldt, mens den bestod hver enkeltstående quiz."""
    r = rod or _rod()
    try:
        rel = fil.relative_to(r)
    except ValueError:
        rel = fil
    return (f"Hvilke funktioner definerer `{rel}`? Giv navn og linjenummer for "
            f"hver enkelt. Nævn kun funktioner du har set i kilden.")


def kør_benchmark(*, provider: str, model: str, antal_filer: int = 2,
                  frø: int | None = None, kald: Any = None,
                  rod: Path | None = None) -> dict[str, Any]:
    """Kør benchmarken for én model. Kaster aldrig.

    `kald(query) -> svartekst` injiceres i tests; ellers spawnes en rigtig
    explore-agent på netop den model, så vi måler den vej arbejdet faktisk går.
    """
    r = rod or _rod()
    ud: dict[str, Any] = {"provider": provider, "model": model,
                          "opgaver": [], "score": 0, "fejl": ""}
    try:
        filer = vælg_filer(antal=antal_filer, rod=r, frø=frø)
        if not filer:
            ud["fejl"] = "ingen egnede filer at bygge en opgave af"
            return ud
        if kald is None:
            def kald(spørgsmål: str) -> str:
                from core.tools.simple_tools_native import _explore_spawn, _explore_svar
                res = _explore_spawn(query=spørgsmål, vejledning="Kig ét sted og svar kort.",
                                     provider=provider, model=model)
                return _explore_svar(res)[0]

        delscorer: list[int] = []
        for f in filer:
            facit = facit_for(f, rod=r)
            if not facit:
                continue
            try:
                svar = str(kald(opgave_for(f, rod=r)) or "")
            except Exception as exc:
                ud["opgaver"].append({"fil": str(f), "fejl": f"{type(exc).__name__}: {exc}"[:120]})
                continue
            d = bedøm_svar(svar, facit)
            d["fil"] = str(f.relative_to(r) if f.is_absolute() else f)
            d["facit_antal"] = len(facit)
            ud["opgaver"].append(d)
            delscorer.append(int(d["score"]))
        ud["score"] = round(sum(delscorer) / len(delscorer)) if delscorer else 0
        if not delscorer:
            ud["fejl"] = ud["fejl"] or "ingen opgaver kunne bedømmes"
    except Exception as exc:
        logger.debug("benchmark væltede for %s/%s", provider, model, exc_info=True)
        ud["fejl"] = f"{type(exc).__name__}: {exc}"[:160]
    return ud


def gem_kvalitet(*, provider: str, model: str, resultat: dict[str, Any]) -> bool:
    """Skriv `kvalitets_score` ved siden af `probe_score` i registret.

    Adskilt fra probe_score med vilje: sonden siger KAN den, benchmarken siger
    HVOR GODT. At blande dem ville skjule at 65 modeller stod med 100 på den
    ene og var vidt forskellige på den anden.
    """
    import json
    from datetime import UTC, datetime
    try:
        from core.runtime.config import PROVIDER_ROUTER_FILE as F
        d = json.loads(F.read_text(encoding="utf-8"))
    except Exception:
        return False
    rørt = False
    for post in d.get("models") or []:
        if str(post.get("provider") or "") != provider or str(post.get("model") or "") != model:
            continue
        post["kvalitets_score"] = int(resultat.get("score") or 0)
        post["kvalitet_at"] = datetime.now(UTC).isoformat()
        post["kvalitet_detalje"] = {
            "opgaver": len(resultat.get("opgaver") or []),
            "opfundne": sorted({o for x in (resultat.get("opgaver") or [])
                                for o in (x.get("opfundne") or [])})[:6],
        }
        rørt = True
    if not rørt:
        return False
    try:
        F.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception:
        return False
    return True
