"""Matrix-karaktererne som en MÅLING — ikke en navneliste (13/11-2026).

Bjørn: «alle matrix karaktererne og deres funktioner tilføjes systemstatus i
arbejdsfladen i desk». `/mc/cadence-producers` viser hele registret (~119), så
karaktererne drukner. Denne flade filtrerer dem ud — og viser det der gør den
til en måling: hvad hver af dem SENEST faktisk gjorde.

## Hvor listen har hjemme

Der findes ingen karakter-liste, og der skal ikke komme en. «En Matrix-karakter»
er defineret ved hvor den registreres: alt der meldes ind gennem
`internal_cadence_matrix.register_matrix_producers`. Navnene UDLEDES ved at køre
den registrering mod en opsamler — registret røres ikke. En ny karakter dukker
op her af sig selv, og en afmeldt forsvinder (vi krydser med det levende
register). Den ene hårdkodede liste i TSX'en, som `cadence_producers`-docstringen
advarer imod («den viste 9 % af sandheden»), findes derfor ikke.

NB: modulet registrerer FLERE end de 17 inline-karakterer fra bestillingen
(også construct, oracle, architect, merovingian, relational, trainman …). De er
med: udfaldssproget bruges af bl.a. `relational`, som ikke er blandt de 17.

## Hvor udfaldet læses fra

Cadence-journalen (`cadence_decisions`) gemmer kun tikkets status (`ran`,
`cooling_down` …) — ikke hvad producenten svarede. Svaret (`outcome`, ofte under
`landing`) levede kun i hukommelsen i runtime-processen, som API-processen ikke
kan se. `noter_udfald` gemmer det derfor holdbart når producenten har kørt;
`internal_cadence` kalder den. Et udfald vi ikke har set vises som «ukendt»,
aldrig som et gæt.
"""
from __future__ import annotations

import ast
import importlib.util
import logging
from typing import Any, Callable, Iterable

logger = logging.getLogger(__name__)

_KEY_PREFIX = "cadence_udfald:"

#: Sproget karaktererne fik 13/11-2026: tekst + tone. Ukendte værdier vises
#: RÅT (tone «ukendt») frem for at blive pænt forklaret forkert.
UDFALDSSPROG: dict[str, tuple[str, str]] = {
    "by_design": ("grænse i designet", "neutral"),
    "denied": ("afvist", "warn"),
    "sammenlignet_uden_fald": ("sammenlignet, intet fald", "ok"),
    "fald_registreret": ("fald registreret", "warn"),
    "intet_grundlag": ("intet grundlag", "neutral"),
    "utilgaengelig": ("utilgængelig", "bad"),
    "sammenlignet_uden_skift": ("sammenlignet, intet skift", "ok"),
    "skift_registreret": ("skift registreret", "warn"),
}


def matrix_navne(register_fn: Callable[[Callable[..., None]], None] | None = None) -> list[str]:
    """Navnene på det Matrix-modulet registrerer — uden at røre registret."""
    if register_fn is None:
        from core.services.internal_cadence_matrix import register_matrix_producers
        register_fn = register_matrix_producers
    fundet: list[str] = []
    register_fn(lambda spec: fundet.append(spec.name))
    return fundet


def udled_udfald(result: Any) -> str | None:
    """Udfaldet i et producer-svar: `landing.outcome`, dernæst `outcome`.

    None hvis svaret ikke har et — vi opfinder ikke et udfald ud af `status`.
    """
    if not isinstance(result, dict):
        return None
    landing = result.get("landing")
    if isinstance(landing, dict) and landing.get("outcome"):
        return str(landing["outcome"])
    if result.get("outcome"):
        return str(result["outcome"])
    return None


def beskriv_udfald(outcome: str | None) -> dict[str, str] | None:
    if not outcome:
        return None
    tekst, tone = UDFALDSSPROG.get(outcome, (outcome, "ukendt"))
    return {"outcome": outcome, "tekst": tekst, "tone": tone}


def noter_udfald(name: str, result: Any, *, at: str) -> bool:
    """Gem seneste udfald holdbart (deles af API- og runtime-processen).

    Skriver kun når svaret HAR et udfald, så de ~100 øvrige producenter ikke
    koster en skrivning pr. kørsel. Self-safe.
    """
    outcome = udled_udfald(result)
    if not outcome:
        return False
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(f"{_KEY_PREFIX}{name}", {"outcome": outcome, "at": at})
        return True
    except Exception:
        logger.debug("kunne ikke gemme udfald for %s", name, exc_info=True)
        return False


def _laes_udfald(name: str) -> dict[str, Any] | None:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(f"{_KEY_PREFIX}{name}", None)
        return v if isinstance(v, dict) else None
    except Exception:
        # En statusflade maa ikke vaelte fordi én karakter mangler et udfald.
        # Den viser «ukendt» i stedet — men fejlen skal kunne ses i loggen.
        logger.debug("kunne ikke laese udfald for %s", name, exc_info=True)
        return None


def funktion_af(name: str) -> str:
    """Første linje af `central_<name>.py`s docstring. Læses som tekst (ast) —
    ingen import, så en tung modul ikke trækkes ind af en statusflade."""
    try:
        spec = importlib.util.find_spec(f"core.services.central_{name}")
        if spec is None or not spec.origin:
            return ""
        with open(spec.origin, encoding="utf-8") as fh:
            doc = ast.get_docstring(ast.parse(fh.read())) or ""
        return doc.strip().splitlines()[0].strip() if doc.strip() else ""
    except Exception:
        # En manglende eller ulaeselig modulfil giver tom funktionstekst, ikke en
        # krasch i en statusflade. Navnet paa karakteren vises stadig.
        logger.debug("kunne ikke laese funktion for %s", name, exc_info=True)
        return ""


def byg_raekker(
    specs: Iterable[Any],
    navne: Iterable[str],
    *,
    tempo: float,
    effektiv_cooldown: Callable[[str, float, float], float],
    sidste_koersel: Callable[[str], str],
    udfald_af: Callable[[str], dict[str, Any] | None],
    funktion: Callable[[str], str],
) -> list[dict[str, Any]]:
    """Ren sammenstilling: registrets specs filtreret til karaktererne."""
    ud = set(navne)
    raekker: list[dict[str, Any]] = []
    for sp in sorted(specs, key=lambda s: (s.priority, s.name)):
        if sp.name not in ud:
            continue
        gemt = udfald_af(sp.name) or {}
        raekker.append({
            "name": sp.name,
            "funktion": funktion(sp.name),
            "priority": sp.priority,
            "cooldown_minutes": sp.cooldown_minutes,
            "effektiv_cooldown_minutes": round(
                float(effektiv_cooldown(sp.name, float(sp.cooldown_minutes), tempo)), 1),
            "last_run_at": sidste_koersel(sp.name) or None,
            "udfald": beskriv_udfald(gemt.get("outcome")),
            "udfald_at": gemt.get("at") or None,
        })
    return raekker


def build_matrix_karakterer_surface() -> dict[str, object]:
    """Flade til Desk → Systemstatus. Self-safe: tom liste ved fejl."""
    try:
        from core.services import internal_cadence as ic
        from core.services.cadence_claims import last_success_at
        from core.services.central_cadence_conductor import (
            current_tick_tempo, effective_cooldown,
        )
        ic._ensure_producers_registered()
        tempo = current_tick_tempo()
        raekker = byg_raekker(
            list(ic._producers.values()), matrix_navne(),
            tempo=tempo, effektiv_cooldown=effective_cooldown,
            sidste_koersel=last_success_at, udfald_af=_laes_udfald,
            funktion=funktion_af,
        )
    except Exception:
        logger.warning("matrix-karakterer kunne ikke bygges", exc_info=True)
        return {"active": False, "tempo": 1.0, "antal": 0, "karakterer": []}
    return {"active": True, "tempo": tempo, "antal": len(raekker), "karakterer": raekker}
