"""`vis_widget` — en interaktiv flade i traaden, i en sandkasse.

Trin 3 af «visuelle svar» (Bjoern 6/10-2026: «tag 1 og 2 og 3»).

**HTML'en rejser som en VEDHAEFTNING, ikke i vaerktoejs-resultatet.** Et
resultat afkortes (`block.resultAfkortet` i desk, og hele
[[project_tool_result_history_bloat]]), saa en widget leveret i et resultat
ville blive skaaret midt over og rendere en halv side. Lige saa vigtigt: HTML
i resultatet ville lande i transkriptet og dermed i hver efterfoelgende prompt
— en widget paa 100 KB ville koste den plads i alle senere ture. Som
vedhaeftning roerer den aldrig historikken.

Leveringen er `graf_tools`/pollinations-moenstret ordret, inklusive
`tool_use_id`-ankeret der bestemmer hvor i traaden fladen lander.

Sikkerheden ligger i TO lag, og ingen af dem er en saniteringsliste:
`widget_dokument.pak` giver dokumentet en CSP der naegter alt netvaerk, og
klienten renderer det i en sandkasse med ugennemsigtig origin. Se modulets
docstring dér for hvorfor husets «aldrig model-HTML»-regel kan vige her.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_WIDGET_REL = "generated/widgets"


def _widget_dir() -> Path:
    from core.runtime.workspace_paths import shared_dir
    return shared_dir() / _WIDGET_REL


def _exec_vis_widget(args: dict[str, Any]) -> dict[str, Any]:
    """Pak, gem og laeg widget'en i traaden. Kaster aldrig."""
    from core.services.widget_dokument import WidgetFejl, pak

    titel = str(args.get("titel") or "").strip()
    try:
        dokument = pak(str(args.get("html") or ""), titel=titel)
    except WidgetFejl as exc:
        # Beskeden siger HVAD der er galt (tom, for stor, helt dokument), saa
        # han kan rette uden at braende en runde paa at gaette.
        return {"status": "error", "error": str(exc)}
    except Exception as exc:  # uventet → sig det, vaelt ikke turen
        logger.warning("vis_widget: kunne ikke pakke dokumentet", exc_info=True)
        return {"status": "error", "error": f"kunne ikke pakke widget'en: {str(exc)[:120]}"}

    raa = dokument.encode("utf-8")
    try:
        mappe = _widget_dir()
        mappe.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
        sti = mappe / f"widget-{stamp}.html"
        sti.write_bytes(raa)
    except Exception as exc:
        logger.warning("vis_widget: kunne ikke skrive filen", exc_info=True)
        return {"status": "error", "error": f"kunne ikke gemme widget'en: {str(exc)[:120]}"}

    attachment_id = ""
    try:
        from core.services.attachment_service import register_generated_media
        attachment_id = register_generated_media(
            local_path=str(sti), mime_type="text/html",
        )
    except Exception:  # filen findes; en manglende registrering taber den ikke
        logger.warning("vis_widget: kunne ikke registrere vedhaeftningen", exc_info=True)
        attachment_id = ""

    if not attachment_id:
        # UDEN et attachment_id kan ingen klient hente dokumentet, og en post
        # paa turen ville love en flade der ikke kan vises. Sig det i stedet.
        return {"status": "error",
                "error": "widget'en blev gemt, men kunne ikke registreres som vedhaeftning "
                         "— den kan derfor ikke vises; proev igen"}

    try:
        from core.services.published_files import note as _note
        _note(
            str(args.get("_runtime_turn_id") or args.get("_runtime_run_id") or ""),
            filename=sti.name,
            mime_type="text/html",
            size_bytes=len(raa),
            attachment_id=attachment_id,
            # Ankeret. Uden det lander fladen bagest, efter prosaen.
            tool_use_id=str(args.get("_runtime_tool_use_id") or ""),
        )
    except Exception:
        logger.warning("vis_widget: kunne ikke laegge posten paa turen", exc_info=True)

    return {
        "status": "ok",
        # Teksten er til HAM: fladen ER vist, saa han skal ikke gengive dens
        # indhold i prosa bagefter.
        "text": (f"Widget'en{' «' + titel + '»' if titel else ''} er vist i traaden "
                 f"({len(raa)} bytes). Skriv kun det den ikke selv siger."),
        "path": str(sti),
        "bytes": len(raa),
        "attachment_id": attachment_id,
    }


WIDGET_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "vis_widget",
            "description": (
                "Show an interactive surface inline in the thread — a table you can sort, a "
                "small calculator, a legend, a layout sketch. Pass an HTML FRAGMENT (no "
                "<html>/<head>): the server wraps it in a document with a strict policy and "
                "the client renders it sandboxed, with no network access. Inline <style> and "
                "<script> work; images and fonts must be data: URIs. Max 256 KB. "
                "The widget can speak back ONCE in a while: call jarvis.sendPrompt('text') from "
                "inside it and that text is sent as a message — PREFIXED with a visible marker "
                "saying it came from the widget, never as Bjørn's own words. At most 5 per widget "
                "and one every 2 seconds, so build it around a click, not a loop. "
                "For a plain chart use vis_graf instead — it is lighter and works everywhere."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "html": {
                        "type": "string",
                        "description": (
                            "HTML fragment. Inline style/script allowed. No network: no "
                            "external src/href, no fetch. Use data: URIs for images."
                        ),
                    },
                    "titel": {
                        "type": "string",
                        "description": "Short title shown as the document title.",
                    },
                },
                "required": ["html"],
            },
        },
    },
]
