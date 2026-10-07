"""`vis_graf` — en graf der faktisk kan SES, i baade desk og mobil.

Trin 2 af «visuelle svar» (Bjoern 6/10-2026: «tag 1 og 2 og 3»).

**Hvorfor en billed-blok og ikke SVG.** Mobilen har `react-native-svg` men
INGEN WebView, saa en SVG-streng kan ikke renderes der uden ny native kode. En
billed-blok renderes derimod allerede af begge klienter — saa en PNG naar
begge flader uden en eneste linje klient-kode.

**Model-markup krydser aldrig en graense.** Jarvis skriver DATA; matplotlib
tegner (`core/services/graf_render.py`). Samme holdning som `MermaidBlock`,
hvis egen kommentar siger at `dangerouslySetInnerHTML` sidder paa «bibliotekets
tilsigtede API, ikke model-HTML».

**Leveringen er pollinations' moenster, ordret.** Den vej er brudt to gange foer
og dokumenteret begge gange, saa den kopieres frem for at genopfindes:

1. `register_generated_image` → `attachment_id`. Uden den er filen skrevet i
   workspace'et og usynlig for enhver klient (maalt 12/9-2026: 392
   assistent-beskeder med billed-blokke havde NUL af typen `image`).
2. `published_files.note(...)` laegger posten paa turen; `visible_runs_outcomes`
   tager den naar svaret persisteres. Uden den er billedet hentbart men ingen
   besked baerer en reference, saa det er usynligt i traaden.
3. **`tool_use_id` er ankeret der bestemmer HVOR i traaden billedet lander.**
   Uden det havner grafen BAGEST, efter prosaen — fejlen openrouter_image fik
   rettet 13/9-2026 og som blev glemt i pollinations indtil 28/9.

Referencen er `attachment_id` (bruger-scopet `/attachments/image/{id}`), ikke en
`/files/`-adresse: den mappe har ingen bruger-afgraensning.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_GRAF_REL = "generated/grafer"


def _graf_dir() -> Path:
    from core.runtime.workspace_paths import shared_dir
    return shared_dir() / _GRAF_REL


def _exec_vis_graf(args: dict[str, Any]) -> dict[str, Any]:
    """Tegn en graf og laeg den i traaden. Kaster aldrig."""
    from core.services.graf_render import GrafFejl, tegn_graf

    spec = {
        "slags": args.get("slags"),
        "titel": args.get("titel"),
        "x_navn": args.get("x_navn"),
        "y_navn": args.get("y_navn"),
        "serier": args.get("serier"),
    }
    try:
        png = tegn_graf(spec)
    except GrafFejl as exc:
        # Beskeden siger HVAD der er galt, saa han kan rette specen uden at
        # gaette. Et generisk «kunne ikke tegne» ville koste en runde.
        return {"status": "error", "error": str(exc)}
    except Exception as exc:  # uventet fejl i tegningen maa ikke vaelte turen
        logger.warning("vis_graf: tegningen fejlede", exc_info=True)
        return {"status": "error", "error": f"kunne ikke tegne grafen: {str(exc)[:120]}"}

    try:
        mappe = _graf_dir()
        mappe.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
        sti = mappe / f"graf-{stamp}.png"
        sti.write_bytes(png)
    except Exception as exc:  # kan ikke skrive → intet at vise, sig det
        logger.warning("vis_graf: kunne ikke skrive filen", exc_info=True)
        return {"status": "error", "error": f"kunne ikke gemme grafen: {str(exc)[:120]}"}

    attachment_id = ""
    try:
        from core.services.attachment_service import register_generated_image
        attachment_id = register_generated_image(
            local_path=str(sti), mime_type="image/png",
        )
    except Exception:  # filen findes; en manglende registrering maa ikke tabe den
        logger.warning("vis_graf: kunne ikke registrere vedhaeftningen", exc_info=True)
        attachment_id = ""

    try:
        from core.services.published_files import note as _note
        _note(
            str(args.get("_runtime_turn_id") or args.get("_runtime_run_id") or ""),
            filename=sti.name,
            mime_type="image/png",
            size_bytes=len(png),
            attachment_id=attachment_id,
            # Ankeret. Uden det lander grafen bagest, efter prosaen.
            tool_use_id=str(args.get("_runtime_tool_use_id") or ""),
        )
    except Exception:  # samme regel: billedet er lavet, posten er en tilfoejelse
        logger.warning("vis_graf: kunne ikke laegge posten paa turen", exc_info=True)

    titel = str(args.get("titel") or "").strip()
    return {
        "status": "ok",
        # Teksten er til HAM, ikke til brugeren: den siger at grafen ER vist, saa
        # han ikke beskriver billedet i prosa bagefter.
        "text": (f"Grafen{' «' + titel + '»' if titel else ''} er tegnet og vist i traaden "
                 f"({len(png)} bytes). Skriv kun konklusionen — billedet staar der."),
        "path": str(sti),
        "bytes": len(png),
        "attachment_id": attachment_id,
    }


GRAF_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "vis_graf",
            "description": (
                "Draw a chart that is RENDERED inline in the thread — in both jarvis-desk "
                "and the phone. Use it when numbers over time or a comparison IS the answer; "
                "a chart beats three sentences of figures. You supply DATA, the server draws it. "
                "Write the conclusion in text too — the image carries the shape, not the point."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "serier": {
                        "type": "array",
                        "description": (
                            "One or more series. Each: {navn, y: [numbers], x: optional "
                            "[numbers or labels]}. x defaults to 1..n. Max 8 series, 500 points."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "navn": {"type": "string", "description": "Series label."},
                                "y": {"type": "array", "items": {"type": "number"}},
                                "x": {"type": "array", "description": "Numbers or text labels."},
                            },
                            "required": ["y"],
                        },
                    },
                    "slags": {
                        "type": "string",
                        "description": "linje (default) | soejle | punkt.",
                    },
                    "titel": {"type": "string", "description": "Chart title."},
                    "x_navn": {"type": "string", "description": "X axis label."},
                    "y_navn": {"type": "string", "description": "Y axis label."},
                },
                "required": ["serier"],
            },
        },
    },
]
