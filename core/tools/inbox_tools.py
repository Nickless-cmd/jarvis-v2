"""De tre indbakke-værktøjer: `inbox`, `inbox_done`, `inbox_drop`.

Opgave 5 i `docs/superpowers/specs/2026-10-03-indbakke-som-kontrolflade-design.md`.

## Hvorfor en egen fil, og ikke i `simple_tools_definitions.py`

Et værktøjsnavn bor **fem** steder: skema, eksekutor, dispatch, desk og mobil.
Målt 2/10-2026 ramte jeg tre af de fem i første forsøg. Og en AST-sletning af et
skema i den store definitions-fil ramte den INDRE dict og efterlod
`{'type': 'function'}` — gyldig Python, så `compileall` tav, og først
`test_browser_tools` fangede det.

Huset har allerede et mønster der undgår begge: servicemodulet ejer sit eget
`*_TOOL_DEFINITIONS` og sine `_exec_*`, og `simple_tools.py` importerer dem.
`self_wakeup` gør det, og så gør indbakken det også. Det holder
definitions-filen fra at vokse og samler de tre navne ét sted hvor de kan læses
sammen.

Filerne over 2.000 linjer (`simple_tools_definitions.py` 3.675,
`simple_tools_native.py` 3.240) røres derfor slet ikke. `simple_tools.py`
(2.264) får en import, tre dispatch-linjer og tre eksport-navne — under
Boy Scout-reglens tærskel på 20 linjer, og ingen logik-ændring.

## Færre værktøjer, ikke flere

Han har otte listnings/bogførings-værktøjer i dag. Indbakken skal **reducere**
det han kalder, ikke lægge et niende ovenpå: `inbox` erstatter i praksis
`list_self_wakeups`, `list_agents` og `bash_session_list` som *det han kalder*.

De gamle `list_*` fjernes IKKE her. De er billige, de virker
(`list_self_wakeups`: 59 kald, 0 fejl), og at fjerne et værktøj rører de samme
fem steder. En oprydning hører i sit eget spor.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

INBOX_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "inbox",
            "description": (
                "Din indbakke: alt der venter paa dig, samlet. Otte sektioner "
                "— hvad der vakte dig denne tur, hvad der VENTER PAA DIG (kun "
                "den kan blokere mutationer), hvad der er i gang, dine "
                "sideopgaver, dine egne beslutninger, hvad der er paa vej, "
                "hvad der er planlagt, og hvad der venter paa Bjoern. "
                "Én linje per post med id, status, alder og en henvisning — "
                "aldrig filindhold, og intet raat payload. Erstatter i "
                "praksis list_self_wakeups, list_agents og bash_session_list "
                "som det du kalder."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inbox_done",
            "description": (
                "Kvittér en ALLEREDE UDFOERT opgave i indbakken. For en fyret "
                "vaekning kalder den mark_wakeup_consumed; for et job eller en "
                "agent kontrollerer den terminalt udfald foerst. Den markerer "
                "IKKE en endnu ikke fyret vaekning som brugt. Dette er den ene "
                "af to maader en blokerende post frigives — et blik paa `inbox` "
                "frigiver ikke."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "string",
                           "description": "Postens id, praecis som `inbox` viste "
                                          "det (f.eks. wake-49b89a51de)."},
                },
                "required": ["id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inbox_drop",
            "description": (
                "Afvis en aaben indbakke-post med begrundelse. Den stopper IKKE "
                "et koerende job eller en agent — annullering er en selvstaendig "
                "handling med egne tilladelser. Begrundelsen er obligatorisk: en "
                "afvisning uden grund kan ikke efterproeves bagefter."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Postens id."},
                    "reason": {"type": "string",
                               "description": "Hvorfor den ikke skal goeres."},
                },
                "required": ["id", "reason"],
            },
        },
    },
]


def _bruger() -> str:
    """Den autentificerede bruger. Tom streng når ingen er bundet.

    Værktøjerne tager IKKE et bruger-id som parameter. Kunne modellen vælge
    bruger, var hele bruger-afgrænsningen et flag kalderen styrer — præcis den
    fejlform `registrer_kilde` er bygget imod.
    """
    # ÉN definition, i `inbox_state.laese_bruger`. Min foerste udgave her
    # faldt tilbage paa workspacet UDEN at kraeve owner-rollen, og standarden
    # er «bjorn» — saa en tabt ContextVar i en anden brugers session gav
    # adgang til Bjoerns indbakke.
    try:
        from core.services.inbox_state import laese_bruger
        return laese_bruger()
    except Exception as exc:  # noqa: BLE001
        logger.warning("inbox_tools: kunne ikke laese bruger-konteksten: %s", exc)
        return ""


#: Sektionerne i visningen — ÉN liste, delt af teksten og af skemaets
#: beskrivelse. To lister drev fra hinanden: skemaet sagde «Seks sektioner»
#: længe efter der var otte, og nævnte «hvad der gentager sig» — en sektion der
#: ikke findes i visningen (`Kilder.gentagende` er `lambda _b: []` og har
#: aldrig haft en kilde). Beskrivelsen er det modellen læser FØR den kalder, så
#: et forkert tal der er ikke kosmetik.
_SEKTIONER: tuple[tuple[str, str], ...] = (
    ("VAKTE DENNE TUR", "vakte"),
    ("VENTER PAA DIG", "venter_paa_dig"),
    ("I GANG", "i_gang"),
    ("SIDEOPGAVER", "sideopgaver"),
    # Beslutnings-posterne fik deres egen sektion 5/10-2026. De gater ikke,
    # så de hører ikke under «VENTER PÅ DIG» — men de bliver i VISNINGEN,
    # fordi sektionen er det eneste sted alle beslutnings-id'er står
    # (gaten navngiver kun de 12 værste). Se `inbox_view._UDEN_LOFT`.
    ("BESLUTNINGER", "beslutninger"),
    ("PAA VEJ", "paa_vej"),
    ("PLANLAGTE", "planlagte"),
    ("VENTER PAA BJOERN", "venter_paa_bjorn"),
)


def _tekst(v: dict[str, Any]) -> str:
    """Visningen som ÉN tekst. Tomme sektioner udelades helt.

    En overskrift med nul linjer er støj: den fylder i prompten og siger
    ingenting. Og rækkefølgen er fast — «VENTER PÅ DIG» øverst efter «VAKTE»,
    fordi det er den eneste sektion der kan blokere.
    """
    ud: list[str] = []
    for titel, noegle in _SEKTIONER:
        poster = list(v.get(noegle) or [])
        if not poster:
            continue
        ud.append(f"{titel} ({len(poster)})" if len(poster) > 1 else titel)
        ud += [f"  {p.get('linje') or p.get('id')}" for p in poster]
        if v.get(f"{noegle}_skjult"):
            ud.append(f"  +{v[f'{noegle}_skjult']} mere")
    tal = int(v.get("backlog_tal") or 0)
    if tal:
        ud.append(f"\nBacklog: {tal} kandidat-forslag → GET /central/candidates")
    return "\n".join(ud) if ud else "Indbakken er tom."


def _exec_inbox(arguments: dict[str, Any] | None = None, **_kw) -> dict[str, Any]:
    """Hele visningen. Læser; skriver intet."""
    bruger = _bruger()
    if not bruger:
        # Typet fejl, ikke en undtagelse, og ALDRIG en liste over alle brugere.
        return {"status": "error", "error": "ingen autentificeret bruger"}
    from core.services.inbox_view import byg_indbakke
    v = byg_indbakke(bruger)
    if v.get("status") != "ok":
        return {"status": "error", "error": str(v.get("error") or "ukendt fejl")}
    # INTET payload (rettet 5/10-2026). Her stod `"indbakke": v` — hele den rå
    # struktur oveni teksten. Målt mod rigtige data samme dag: 4.441 tegn tekst
    # og 28.014 tegn rå struktur oveni, altså 6,3x, hvoraf 9.601 tegn var
    # posternes FULDE beskrivelser (`inbox_view._post` afkorter linjen, ikke
    # den gemte tekst). Værktøjets eget løfte er «én linje per post, aldrig
    # filindhold», og nøglen havde NUL læsere: desk og mobil henter deres tal
    # fra `opmaerksomhed`-endpointet, og `inbox_prompt_section` kalder
    # `byg_indbakke` direkte. Skal en fremtidig flade have strukturen, kalder
    # den `byg_indbakke` — den vej findes allerede.
    return {"status": "ok", "tekst": _tekst(v),
            "antal_venter_paa_dig": len(v.get("venter_paa_dig") or [])}


def _exec_inbox_done(arguments: dict[str, Any] | None = None, **_kw) -> dict[str, Any]:
    a = arguments or {}
    post_id = str(a.get("id") or "").strip()
    if not post_id:
        return {"status": "error", "error": "id kraeves"}
    bruger = _bruger()
    if not bruger:
        return {"status": "error", "error": "ingen autentificeret bruger"}
    from core.services.inbox_state import done
    r = done(bruger, post_id)
    # `ukendt` er IKKE en succes. Et «ok» paa et id der ikke findes ville
    # frigive gaten uden at lukke noget — husets hyppigste fejlform.
    if r.get("status") == "ukendt":
        return {"status": "error", "error": f"ingen aaben post med id {post_id}",
                "id": post_id}
    if r.get("status") == "fejl":
        return {"status": "error", "error": str(r.get("error") or ""), "id": post_id}
    return {"status": "ok", "id": post_id, "type": str(r.get("type") or "")}


def _exec_inbox_drop(arguments: dict[str, Any] | None = None, **_kw) -> dict[str, Any]:
    a = arguments or {}
    post_id = str(a.get("id") or "").strip()
    grund = str(a.get("reason") or "").strip()
    if not post_id:
        return {"status": "error", "error": "id kraeves"}
    if not grund:
        return {"status": "error", "error": "reason kraeves — en afvisning uden "
                                            "grund kan ikke efterproeves"}
    bruger = _bruger()
    if not bruger:
        return {"status": "error", "error": "ingen autentificeret bruger"}
    from core.services.inbox_state import drop
    r = drop(bruger, post_id, grund)
    if r.get("status") == "ukendt":
        return {"status": "error", "error": f"ingen aaben post med id {post_id}",
                "id": post_id}
    if r.get("status") == "fejl":
        return {"status": "error", "error": str(r.get("error") or ""), "id": post_id}
    return {"status": "ok", "id": post_id, "type": str(r.get("type") or "")}


__all__ = [
    "INBOX_TOOL_DEFINITIONS", "_exec_inbox", "_exec_inbox_done", "_exec_inbox_drop",
]
