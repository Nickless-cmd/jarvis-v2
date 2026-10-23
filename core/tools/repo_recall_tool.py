"""`repo_recall` — søgning i repoets DOKUMENTATION (ikke kildekoden).

Søster-værktøj til `recall`, men et andet stof: `recall` slår op i Jarvis'
egen hukommelse (MEMORY/USER/SOUL/PLAYBOOKS/brain/kronik), `repo_recall`
slår op i dokumentationen i `/media/projects/jarvis-v2` — arkitektur,
specs, runbooks, audits, design-historik.

## Hvorfor det er et selvstændigt værktøj (23/10-2026)

Først var tanken at lægge docs ind i memory-indekset. Det blev forkastet
efter en måling: `recall._source_workspace` kalder `search_memory` uden
`sources`-filter, så ~18.000 doc-chunks ville konkurrere med Jarvis' egne
noter om de 3-5 linjer auto-recall injicerer hver tur. Bjørns arkitektur
er to spor med hver sin pulje — dette er det manuelle spor.

## Hvad det ikke er

Det er ikke kode-søgning. Til kode findes `search` (grep, 0,01 s over
4.033 filer) og `read_file` — de rammer disken direkte og er præcise.
En vektor-søgning efter `def _chunk_markdown` ville give fem funktioner
der «handler om noget lignende»; grep giver den ene.
"""
from __future__ import annotations

from typing import Any

REPO_RECALL_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "repo_recall",
            "description": (
                "Søg i repoets DOKUMENTATION (docs/ og rod-Markdown) — arkitektur, "
                "specs, runbooks, audits, design-historik, planer. Brug den når du "
                "skal finde UD AF HVAD DER ER SKREVET om et emne, eller når du ikke "
                "ved hvad der findes. Det er IKKE kode: til kode brug `search` "
                "(grep, præcis) eller `read_file`. Og det er ikke din hukommelse — "
                "til den brug `recall`."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Hvad du leder efter — emne, system, beslutning",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maks. antal resultater (default 8, maks 25)",
                    },
                    "path": {
                        "type": "string",
                        "description": (
                            "Valgfrit sti-præfiks, fx 'docs/superpowers/specs' eller "
                            "'docs/architecture'. Afgrænser søgningen til den del."
                        ),
                    },
                },
                "required": ["query"],
            },
        },
    },
]


def _exec_repo_recall(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.repo_index import get_stats, search_repo

    query = str(args.get("query") or "").strip()
    if not query:
        return {"status": "error", "error": "query is required"}
    try:
        limit = int(args.get("limit") or 8)
    except (TypeError, ValueError):
        limit = 8
    limit = max(1, min(25, limit))
    path_prefix = str(args.get("path") or "").strip() or None

    try:
        hits = search_repo(query, limit=limit, path_prefix=path_prefix)
    except Exception as exc:  # et søgefejl må ikke dræbe turen
        return {"status": "error", "error": f"repo_recall fejlede: {exc}", "results": []}

    stats = get_stats()
    payload: dict[str, Any] = {
        "status": "ok",
        "query": query,
        "count": len(hits),
        "results": hits,
    }
    # Ærlig tilstand: første kald efter en ny fil kan svare med TF-IDF mens
    # embeddings bygges i baggrunden. Så skal svaret sige det, ikke lade som om.
    if stats.get("status") != "ready":
        payload["index_status"] = stats.get("status")
        payload["note"] = (
            "Indekset er ikke færdigbygget endnu — resultaterne er leksikalske "
            "(TF-IDF). Semantisk søgning aktiveres når baggrundsbygningen er færdig."
        )
    elif not stats.get("has_embeddings"):
        payload["index_status"] = "building"
        payload["note"] = "Embeddings bygges stadig i baggrunden; svaret er leksikalsk."
    return payload
