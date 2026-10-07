"""`render_mermaid` — et diagram der også når telefonen.

## Hvorfor værktøjet findes

Desk tegner ` ```mermaid ` selv (`MermaidBlock.tsx`, lazy `import('mermaid')`).
Mobilen har ingen mermaid-renderer: nul referencer i `apps/mobile/src`, og
`mermaid` står ikke i dens `package.json`. Markdown-reglerne i
`MessageBubble.tsx` sender enhver fence til `CodeBlock` — også `mermaid` — så
telefonen viser rå kildekode (målt 7/10-2026, Bjørn: «Det virker kun i desk,
ikk på mobilen»).

Prompten i `output_discipline.py` siger til modellen at en mermaid-blok
*RENDERES som et diagram i jarvis-desk*. Det er sandt i desk og falsk på
mobilen — derfor blev mermaid brugt i god tro, og Bjørn så kildekode.

## Hvorfor serveren rendrer og sender et BILLEDE

Den billige vej havde været at lære mobilen at tegne mermaid. Det kræver en
ny APK, og Bjørn skal bygge den på sin egen maskine. Denne vej kræver intet
build: serveren rendrer SVG'en, raster den til PNG og lægger den på turen som
et genereret billede — præcis den vej `openrouter_image` allerede bruger, og
som begge klienter tegner i dag.

Prisen er ærlig: et diagram bliver et billede, ikke levende markup. Det kan
ikke klikkes, og teksten kan ikke markeres. For et diagram er det en rimelig
handel — og det er den eneste der virker på telefonen uden et build.

## Hvorfor en browser og ikke jsdom

Målt 7/10-2026: mermaid kan IKKE rende i ren node. Den kræver `document`,
`CSSStyleSheet` og — afgørende — en layout-motor til `getBBox()`. jsdom har
ingen layout, så hver shim avler den næste fejl (seks forsøg, sidste viewBox
26 px i stedet for 115). Med Playwrights chromium-binær rendrede det korrekt i
første forsøg. Se `core/services/mermaid_render.py`.

## Hvorfor den ikke ligger i den varme sti

Hvert kald starter en browser: ~1-2 sekunder. Det er for dyrt til at gøre
automatisk for hver mermaid-blok i hvert svar. Værktøjet er derfor noget
modellen VÆLGER, når diagrammet skal kunne ses på telefonen — ikke en
automatisk omskrivning af alle svar.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

#: Bredde i pixels. Et diagram er bredt; 1400 giver skarp tekst på en telefon
#: uden at filen bliver stor.
BREDDE = 1400

#: Loft over HØJDEN. `--width` skalerer proportionalt, så et lodret diagram
#: (`flowchart TD`) bliver 2,7 gange så højt som bredt — målt 7/10-2026:
#: 1400×3797 px for tre knuder. Det er ubrugeligt på en telefon, hvor man så
#: skal scrolle gennem et diagram der kunne være 700 px højt. `--height` lader
#: rsvg-convert begrænse den anden akse, så forholdet bevares.
MAKS_HOEJDE = 1600

#: Et loft over hvad vi vil lægge i tråden. Et diagram over 4 MB er ikke et
#: diagram, det er en fejl.
MAKS_PNG_BYTES = 4_000_000


def _generated_dir() -> Path:
    """Samme mappe som `openrouter_image` skriver i — den er allerede synlig.

    `shared_dir()`, ikke `workspace_dir()`: den sidste kræver en bruger i
    konteksten og rejser `NoUserContextError` i autonome kørsler. Målt
    7/10-2026 ved at læse `openrouter_image_tools._generated_dir` — de
    genererede billeder ligger i `shared/memory/generated/`, og et diagram
    skal ligge samme sted som dem der virker.
    """
    from core.runtime.workspace_paths import shared_dir

    mappe = Path(shared_dir()) / "memory" / "generated"
    mappe.mkdir(parents=True, exist_ok=True)
    return mappe


def _svg_til_png(svg: str) -> bytes:
    """SVG → PNG. Rejser RuntimeError med en brugbar årsag.

    Rasteriseringen sker i **chromium**, ikke i rsvg-convert (maalt
    7/10-2026). Mermaid lægger sine labels i `<foreignObject>` — HTML inde i
    SVG'en — og librsvg tegner den ikke: former, pile og farver kom med, men
    alle kasser stod tomme. Bjørn saa det paa sin telefon.

    Chromium tegner `foreignObject` korrekt, og browseren startes alligevel
    for at rende mermaid, saa rasteriseringen koster kun den ene kommando.
    Skaleringen (bredde styrer, hoejden loefter naar diagrammet er lodret)
    ligger i `mermaid_render.rasteriser`.
    """
    from core.services.mermaid_render import MermaidFejl, rasteriser

    try:
        data = rasteriser(svg, bredde=BREDDE, maks_hoejde=MAKS_HOEJDE)
    except MermaidFejl as exc:
        raise RuntimeError(f"kunne ikke rasterisere diagrammet: {exc}") from exc

    if not data:
        raise RuntimeError("rasteriseringen gav en tom fil")
    if len(data) > MAKS_PNG_BYTES:
        raise RuntimeError(
            f"diagrammet blev {len(data)} bytes (højst {MAKS_PNG_BYTES}) — "
            "forenkl diagrammet"
        )
    return data


def _exec_render_mermaid(args: dict[str, Any]) -> dict[str, Any]:
    """Mermaid-kilde → PNG i tråden, så diagrammet også ses på mobilen."""
    kilde = str(args.get("kilde") or args.get("mermaid") or "").strip()
    if not kilde:
        return {"status": "error", "error": "kilde er påkrævet (mermaid-syntaks)"}

    titel = str(args.get("titel") or "").strip()

    from core.services.mermaid_render import MermaidFejl, render, tilgaengelig

    klar, grund = tilgaengelig()
    if not klar:
        return {"status": "error", "error": f"mermaid-rendereren er ikke klar: {grund}"}

    try:
        svg = render(kilde)
    except MermaidFejl as exc:
        # Kalderens fejl, ikke en hændelse: dårlig mermaid-syntaks er noget
        # modellen kan rette med det samme.
        return {"status": "error", "error": f"mermaid afviste diagrammet: {exc}"}

    try:
        png = _svg_til_png(svg)
    except RuntimeError as exc:
        # Rasteriseringen fejlede (rsvg-convert mangler eller svarede ikke).
        # Fejlen ER svaret til kalderen — den siger hvad der gik galt.
        return {"status": "error", "error": str(exc)}

    navn = f"diagram-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}.png"
    sti = _generated_dir() / navn
    try:
        sti.write_bytes(png)
    except OSError as exc:
        # Disken er fuld eller mappen er ikke skrivbar. Kalderen skal se det,
        # ikke få et svar der lover et diagram der ikke findes.
        return {"status": "error", "error": f"kunne ikke skrive diagrammet: {exc}"}

    attachment_id = ""
    try:
        from core.services.attachment_service import register_generated_image

        attachment_id = register_generated_image(
            local_path=str(sti), mime_type="image/png", source_url="",
        )
    except Exception as exc:
        # Ikke `pass`: uden registreringen ligger billedet på disken men er
        # usynligt i samtalen — og svaret ville love et diagram der ikke kom.
        logger.warning("render_mermaid: kunne ikke registrere %s: %s", sti, exc)

    if not attachment_id:
        return {
            "status": "error",
            "error": "diagrammet blev tegnet, men kunne ikke lægges i tråden "
                     "(ingen aktiv session) — det ligger på disken",
            "path": str(sti),
        }

    # Hæft på turen. Samme «læg og tag»-mønster som `publish_file` og
    # `openrouter_image`: uden dette bærer svaret ikke billedet, og klienten —
    # der renderer efter blokke — viser ingenting.
    try:
        from core.services.published_files import note as _note

        _note(
            str(args.get("_runtime_turn_id") or args.get("_runtime_run_id") or ""),
            filename=navn,
            mime_type="image/png",
            size_bytes=len(png),
            attachment_id=attachment_id,
            tool_use_id=str(args.get("_runtime_tool_use_id") or ""),
        )
    except Exception:
        # Hæftningen er en visning; fejler den, er diagrammet stadig tegnet og
        # registreret. At kaste her ville koste et billede der virker.
        logger.debug("render_mermaid: kunne ikke haefte paa turen", exc_info=True)

    return {
        "status": "ok",
        "attachment_id": attachment_id,
        "path": str(sti),
        "size_bytes": len(png),
        "titel": titel,
        "text": (
            "Diagrammet er tegnet og lagt i tråden som billede — det ses nu på "
            "både desk og mobil. Skriv ikke mermaid-kilden i svaret; den er "
            "allerede vist."
        ),
    }


MERMAID_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "render_mermaid",
            "description": (
                "Tegn et mermaid-diagram og læg det i tråden som billede. "
                "Brug dette i stedet for et ```mermaid-hegn når diagrammet skal "
                "kunne ses på MOBILEN: desk tegner mermaid selv, men telefonen "
                "har ingen mermaid-renderer og viser rå kildekode. Serveren "
                "rendrer her, raster til PNG og lægger billedet på turen — "
                "så virker det på begge klienter uden et nyt app-build. "
                "Koster ~1-2 sekunder (en browser startes), så brug det når "
                "diagrammet faktisk skal ses, ikke for hvert svar."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "kilde": {
                        "type": "string",
                        "description": (
                            "Mermaid-syntaksen, fx 'flowchart TD\\n  A[Start] --> B{Valg}'. "
                            "Uden ```-hegn."
                        ),
                    },
                    "titel": {
                        "type": "string",
                        "description": "Kort titel til logning. Valgfri.",
                    },
                },
                "required": ["kilde"],
            },
        },
    },
]
