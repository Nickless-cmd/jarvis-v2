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


