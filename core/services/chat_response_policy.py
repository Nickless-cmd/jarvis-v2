"""One chat-only decision vocabulary for closure and presentation.

The visible model should decide what it means before it decides how the answer
looks.  These strings are kept outside prompt assembly so tests and evaluators
can inspect the same policy that the model receives.
"""
from __future__ import annotations


CHAT_RESPONSE_DECISION = (
    "Før du skriver, afgør stille tre ting: hvad du selv mener; hvad brugeren "
    "skal kunne se eller gøre; og hvilken slags afslutning turen behøver. Skriv "
    "ikke disse etiketter i svaret. Vælg mellem samtale (en levende reaktion, "
    "der gerne må stå åben), svar (spørgsmålet er besvaret uden rapportfinale), "
    "leverance (et udført arbejde med resultat og relevante beviser) og afventer "
    "(én reel beslutning mangler fra brugeren). Kun leverance skal lyde som en "
    "afsluttet arbejdsleverance. En terminal tekstblok afslutter turen teknisk; "
    "den behøver ikke lukke samtalen retorisk. Beslutningen styrer dig tavst: "
    "nævn aldrig tilstandene eller kontrakten i dit svar."
)


CHAT_PRESENTATION_DECISION = (
    "Vælg flade efter læseopgaven, ikke efter emnet eller antallet af fund: "
    "comparison når mindst to ting skal sammenlignes på mindst to fælles akser; "
    "timeline når mindst tre hændelser eller trin skal forstås i rækkefølge; "
    "stats når tre til otte selvstændige mærkede nøgletal skal aflæses; choices "
    "når to til seks reelle, handlingsbare muligheder kræver brugerens valg; "
    "location når et konkret sted er centralt for handlingen; callout når præcis "
    "én risiko, afgørelse eller advarsel ikke må overses. En gruppe fortjener "
    "kun en flade når elementerne deler struktur og brugeren skal sammenligne, "
    "ordne, vælge eller aflæse dem — ikke blot fordi der er mange. Når de "
    "kriterier er opfyldt, er fladen ikke valgfri: tanke → flade. Højst én "
    "dominerende native flade pr. semantisk sektion; et enkelt spørgsmål giver "
    "normalt højst én, mens flere uafhængige delspørgsmål kan få hver sin. "
    "Brug ingen native flade til en enkelt prosapointe, som dekorativ overskrift, "
    "til data et værktøj allerede renderer, eller når samme indhold allerede "
    "står i en tabel. Placér fladen inline præcis hvor dens begreb behandles, "
    "ikke automatisk øverst eller nederst."
)


SURFACE_READING_TASKS: dict[str, str] = {
    "comparison": "compare",
    "timeline": "sequence",
    "stats": "scan_numbers",
    "choices": "choose",
    "location": "locate",
    "callout": "warn",
}

CHAT_CLOSURES = frozenset({"conversation", "answer", "delivery", "awaiting_user"})


def surface_for_reading_task(
    task: str,
    *,
    item_count: int = 0,
    shared_dimensions: int = 0,
    already_rendered: bool = False,
) -> str | None:
    """Compile a semantic reading task to one of the six native surfaces.

    This is intentionally deterministic.  The model identifies the reader's
    task; the runtime owns thresholds and component vocabulary.
    """
    if already_rendered:
        return None
    task = str(task or "").strip().lower()
    if task == "compare" and item_count >= 2 and shared_dimensions >= 2:
        return "comparison"
    if task == "sequence" and item_count >= 3:
        return "timeline"
    if task == "scan_numbers" and 3 <= item_count <= 8:
        return "stats"
    if task == "choose" and 2 <= item_count <= 6:
        return "choices"
    if task == "locate" and item_count >= 1:
        return "location"
    if task == "warn" and item_count == 1:
        return "callout"
    return None


_SURFACE_NAMES_DA: dict[str, str] = {
    "comparison": "sammenligning",
    "timeline": "tidslinje",
    "stats": "nøgletal",
    "choices": "valgmuligheder",
    "location": "sted",
    "callout": "advarsel",
}

# Tegne-værktøjerne er en ANDEN familie end de native flader: de lægger noget i
# tråden i stedet for at være en blok i teksten. Porten dækker begge, fordi
# spørgsmålet «skal dette have en form?» kommer før «hvilken form?».
_TOOL_SURFACES: dict[str, tuple[str, str]] = {
    "numbers": (
        "vis_graf",
        "tallene skal aflæses som form — en udvikling eller et forløb, ikke en række",
    ),
    "flow": (
        "render_mermaid",
        "strukturen eller rækkefølgen er pointen — et diagram bærer den bedre end prosa",
    ),
    "interactive": (
        "vis_widget",
        "brugeren skal kunne trykke, sortere eller regne på indholdet",
    ),
}


def decide_surface(
    task: str,
    *,
    item_count: int = 0,
    shared_dimensions: int = 0,
    already_rendered: bool = False,
) -> dict[str, object]:
    """Resolve a reading task to prose, a native surface, or a drawing tool.

    The model names the reader's task; the runtime owns the thresholds.  The
    answer carries its own reason, so the model can correct its assessment
    instead of guessing why it was told no.
    """
    task = str(task or "").strip().lower()

    if already_rendered:
        return _prose_choice(
            "indholdet er allerede vist på en flade",
            "skriv prosa der læser fladen — ikke en kopi af den",
        )
    if not task or task == "none":
        return _prose_choice(
            "læseopgaven kræver ingen flade",
            "skriv prosa; en flade ville være dekoration her",
        )
    if task in _TOOL_SURFACES:
        tool, why = _TOOL_SURFACES[task]
        return {
            "flade": None,
            "vaerktoej": tool,
            "navn": tool,
            "reason": why,
            "next": f"kald {tool} med data — og lad prosaen bære konklusionen",
        }

    surface = surface_for_reading_task(
        task,
        item_count=item_count,
        shared_dimensions=shared_dimensions,
        already_rendered=False,
    )
    if surface is None:
        return _prose_choice(
            _why_prose(task, item_count, shared_dimensions),
            "skriv prosa; en flade ville være dekoration her",
        )
    return {
        "flade": surface,
        "vaerktoej": None,
        "navn": _SURFACE_NAMES_DA.get(surface, surface),
        "reason": _why_surface(surface, item_count, shared_dimensions),
        "next": (
            f"brug en jarvis-ui-blok af typen «{surface}» inline hvor begrebet "
            "behandles, og lad prosaen bære pointen selv"
        ),
    }


def _prose_choice(reason: str, next_step: str) -> dict[str, object]:
    return {
        "flade": None,
        "vaerktoej": None,
        "navn": "prosa",
        "reason": reason,
        "next": next_step,
    }


def _why_surface(surface: str, item_count: int, shared_dimensions: int) -> str:
    if surface == "comparison":
        return f"{item_count} ting på {shared_dimensions} fælles akser — sammenligning kræver aflæsning"
    if surface == "timeline":
        return f"{item_count} led i rækkefølge — rækkefølgen er pointen"
    if surface == "stats":
        return f"{item_count} selvstændige nøgletal — de skal aflæses, ikke læses"
    if surface == "choices":
        return f"{item_count} handlingsbare muligheder — brugeren skal vælge"
    if surface == "location":
        return "et konkret sted er centralt for handlingen"
    if surface == "callout":
        return "præcis én risiko eller afgørelse må ikke overses"
    return "kriterierne er opfyldt"


def _why_prose(task: str, item_count: int, shared_dimensions: int) -> str:
    if task == "compare" and shared_dimensions < 2:
        return f"sammenligning kræver mindst to fælles akser; her er {shared_dimensions}"
    if task == "compare" and item_count < 2:
        return "der er intet at sammenligne"
    if task == "sequence" and item_count < 3:
        return f"en rækkefølge kræver mindst tre led; her er {item_count}"
    if task == "scan_numbers" and not 3 <= item_count <= 8:
        return f"nøgletal kræver tre til otte; her er {item_count}"
    if task == "choose" and not 2 <= item_count <= 6:
        return f"valgmuligheder kræver to til seks; her er {item_count}"
    if task == "warn" and item_count != 1:
        return "en advarsel skal være præcis én ting"
    return "læseopgaven udløser ingen flade"


