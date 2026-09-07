"""Er denne model egnet til agent-arbejde? Svaret bygger på MÅLINGER.

Bjørn 7/9-2026: «hans agenter må aldrig fejle og skal altid levere». Den
konkrete fejl bag ønsket: explore fik en model der kaldte `search`, fik de
rigtige filstier tilbage — og derefter skrev
`src/jarvis/providers/provider_router.py`, en sti der ikke findes, med
opdigtede klassenavne og «confidence: Høj» ovenpå.

`model_probe` fanger præcis det: `follows` måler om en model kan BRUGE et
værktøjsresultat. Nemotron-3-ultra fik 0 der. Men en dom ingen læser ændrer
ingenting — så det her modul er læse-siden.

## To regler der bærer designet

**Ukendt er tilladt.** Har vi ingen måling, blokerer vi ikke. Ellers ville en
tom karakter-tabel lamme hele agent-arbejdet indtil første fejning er kørt —
og en fejemaskine der slukker for systemet mens den arbejder, er værre end
den fejl den skulle løse. Kun **kendt-dårlig** udelukkes.

**Kun værktøjs-roller.** Filosof og etiker skal ikke kalde værktøjer; at
kræve `follows` af dem ville udelukke gode modeller fra arbejde de er fine
til. De er også de tre travleste roller (75 af 112 kørsler i døgnet).
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Roller hvis arbejde falder fra hinanden uden brugbare værktøjskald.
VÆRKTØJS_ROLLER = frozenset({
    "researcher", "explorer", "critic", "planner", "executor", "watcher",
    "devils_advocate",
})

# Under dette regnes en målt model ikke for egnet. Spejler
# model_catalogue_sweep.MIN_SCORE_AGENT.
MIN_SCORE = 60


def _registret() -> list[dict[str, Any]]:
    try:
        from core.runtime.provider_router import load_provider_router_registry
        return list((load_provider_router_registry() or {}).get("models") or [])
    except Exception:
        return []


def dom(provider: str, model: str, *, poster: list[dict] | None = None) -> str:
    """'egnet' | 'uegnet' | 'ukendt'. Kaster aldrig.

    Værnet ligger HER og ikke kun i `_registret`: løftet «kaster aldrig» skal
    holde uanset hvad kilden gør, ellers kan en defekt registerlæsning stoppe
    en agent i at blive født. Tvivl → "ukendt" → tilladt.
    """
    try:
        return _dom(provider, model, poster)
    except Exception:
        logger.debug("fitness: kunne ikke bedømme %s/%s", provider, model, exc_info=True)
        return "ukendt"


def _dom(provider: str, model: str, poster: list[dict] | None) -> str:
    p, m = str(provider or "").strip(), str(model or "").strip()
    if not p or not m:
        return "ukendt"
    for post in (poster if poster is not None else _registret()):
        if str(post.get("provider") or "") != p or str(post.get("model") or "") != m:
            continue
        if "probe_score" not in post:
            return "ukendt"          # registreret, men aldrig prøvet
        if not post.get("enabled", True):
            return "uegnet"
        detalje = post.get("probe_detail") or {}
        if not detalje.get("follows"):
            # DEN afgørende prøve: kalder værktøj, men bruger ikke svaret.
            return "uegnet"
        return "egnet" if int(post.get("probe_score") or 0) >= MIN_SCORE else "uegnet"
    return "ukendt"


def er_blokeret(provider: str, model: str, *, rolle: str = "") -> bool:
    """True kun når vi har MÅLT at modellen ikke duer til værktøjs-arbejde."""
    if rolle and rolle not in VÆRKTØJS_ROLLER:
        return False
    return dom(provider, model) == "uegnet"


def bedste_egnede(*, undtagen: frozenset[str] = frozenset()) -> tuple[str, str]:
    """Den højest scorende målte model der bestod `follows`. ('','') hvis ingen.

    Bruges som sidste udvej når ruteren bliver ved med at pege på en model vi
    har målt som uegnet — så en agent hellere kører på noget vi VED virker end
    på noget vi ved ikke gør.
    """
    bedst: tuple[int, str, str] = (-1, "", "")
    try:
        poster = _registret()
    except Exception:
        return "", ""
    for post in poster:
        p, m = str(post.get("provider") or ""), str(post.get("model") or "")
        if not p or not m or p in undtagen or not post.get("enabled", True):
            continue
        if not (post.get("probe_detail") or {}).get("follows"):
            continue
        s = int(post.get("probe_score") or 0)
        if s >= MIN_SCORE and s > bedst[0]:
            bedst = (s, p, m)
    return bedst[1], bedst[2]


def egnede_modeller(*, undtagen: frozenset[tuple[str, str]] = frozenset(),
                    maks: int = 4) -> list[tuple[str, str]]:
    """Målte, egnede modeller — bedste først. Til rotation.

    Bjørn 7/9-2026: «i stedet for at låse sig på kun én model, rotere». Vi kan
    ikke forudsige hvilken model der lyver i denne kørsel — det er målt at
    samme model gør begge dele på samme opgave. Men vi kan efterprøve svaret og
    prøve en anden når det ikke holder.
    """
    ud: list[tuple[int, str, str]] = []
    try:
        poster = _registret()
    except Exception:
        return []
    for post in poster:
        p, m = str(post.get("provider") or ""), str(post.get("model") or "")
        if not p or not m or (p, m) in undtagen or not post.get("enabled", True):
            continue
        if not (post.get("probe_detail") or {}).get("follows"):
            continue
        s = int(post.get("probe_score") or 0)
        if s >= MIN_SCORE:
            # RÆKKEFØLGEN kommer fra benchmarken når den findes, ikke fra
            # sonden. Efter første fejning stod 65 af 67 egnede modeller med
            # probe_score 100, og den første i rotationen var en 3B-model
            # foran deepseek-v4-pro. Sonden siger KAN den; benchmarken siger
            # hvor godt. Umålte lægger sig efter de målte, ikke forrest.
            k = post.get("kvalitets_score")
            ud.append((int(k) if k is not None else -1, s, p, m))
    ud.sort(key=lambda x: (-x[0], -x[1]))
    # Én model pr. UDBYDER: to modeller hos samme udbyder deler ofte adfærd,
    # og pointen med rotation er at komme et andet sted hen.
    set_udbydere: set[str] = set()
    valgt: list[tuple[str, str]] = []
    for _, _, p, m in ud:
        if p in set_udbydere:
            continue
        set_udbydere.add(p)
        valgt.append((p, m))
        if len(valgt) >= maks:
            break
    return valgt
