"""Vedhæftninger som blokke på brugerens besked.

Billeder man havde sendt forsvandt ved genindlæsning af en samtale. Årsagen var
to huller, ikke ét:

  1. Mobil-uploads lå KUN i et hukommelses-register i api'ets proces
     (`routes/attachments._registry`) og var væk ved næste genstart.
  2. `channel_attachments` har `session_id`, men INGEN `message_id` — så selv
     med en holdbar post kunne man ikke vide hvilken besked billedet hørte til.
     En hel sessions billeder over hver besked ville være forkert.

Dette modul løser (2) uden en skemaændring: referencerne lægges i brugerbeskedens
egen `content_json`, præcis som assistentens turer allerede bærer deres blokke.
Beskeden og dens billeder bliver dermed ét objekt, og klienten har allerede en
parser for netop det felt.

Blokkene bærer bevidst kun en REFERENCE (attachment_id + filnavn + mime), ikke
selve billedet. Billedet hentes over `/attachments/image/{id}`, som er user-scopet
— lagde vi data i beskeden, ville vi omgå den adgangskontrol.
"""
from __future__ import annotations

from typing import Any

# Kun de typer der giver mening at VISE i tråden. Resten nævnes som fil-blok;
# en zip har intet billede at rendere.
_IMAGE_PREFIX = "image/"


def build_attachment_blocks(metas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Lav content_json-blokke for en brugerbeskeds vedhæftninger.

    *metas* er dicts med mindst `id`/`attachment_id`, `filename`, `mime_type`.
    Ukendte eller tomme poster springes over — en halv reference er værre end
    ingen, fordi klienten så ville tegne et hul der aldrig kan fyldes.
    """
    blocks: list[dict[str, Any]] = []
    for meta in metas or []:
        if not isinstance(meta, dict):
            continue
        aid = str(meta.get("id") or meta.get("attachment_id") or "").strip()
        if not aid:
            continue
        mime = str(meta.get("mime_type") or "").strip()
        name = str(meta.get("filename") or "").strip() or "fil"
        block: dict[str, Any] = {
            "type": "image" if mime.startswith(_IMAGE_PREFIX) else "file",
            "attachment_id": aid,
            "filename": name,
            "mime_type": mime or "application/octet-stream",
        }
        size = meta.get("size_bytes")
        if isinstance(size, int) and size > 0:
            block["size_bytes"] = size
        blocks.append(block)
    return blocks


def user_message_content_json(metas: list[dict[str, Any]]) -> str | None:
    """Serialisér blokkene til det felt `append_chat_message` tager.

    None når der intet er at gemme — så beholder beskeden sin hidtidige form i
    stedet for at få en tom blok-array, som klienten skulle til at skelne fra
    «ingen blokke».
    """
    blocks = build_attachment_blocks(metas)
    if not blocks:
        return None
    import json
    return json.dumps(blocks, ensure_ascii=False)


# ── Modellens egne øjne (6/9-2026) ───────────────────────────────────────
# Blokkene ovenfor er til KLIENTEN: en reference den kan hente billedet på.
# Modellen fik dem aldrig som pixels. Dropper Bjørn et skærmbillede i
# desk-appen, kunne Jarvis kun se det ved selv at kalde `read_attachment` —
# altså ved at vide at der VAR noget at kigge på og bede om det.
#
# Herunder er den anden vej: billederne på den aktuelle tur lægges direkte i
# prompten som rigtige indholdsblokke, når den model der svarer selv kan se.
# Kan den ikke, sker der intet, og vision-vejen står uændret.
#
# Referencen bliver til data FØRST her, i prompt-samlingen, og går aldrig
# gennem den gemte besked. Adgangskontrollen på `/attachments/image/{id}`
# er dermed uberørt — det var hele grunden til at blokkene kun bar en
# reference til at begynde med.

def image_ids_on_message(content_json: str | None) -> list[str]:
    """attachment_id'er for BILLEDER i en besked. Tom liste ved alt andet."""
    if not content_json:
        return []
    import json
    try:
        blokke = json.loads(content_json)
    except Exception:
        return []
    if not isinstance(blokke, list):
        return []
    return [str(b.get("attachment_id"))
            for b in blokke
            if isinstance(b, dict) and b.get("type") == "image" and b.get("attachment_id")]


def image_content_blocks(content_json: str | None, *, limit: int = 4) -> list[dict[str, Any]]:
    """`image_url`-blokke klar til prompten. Tom liste hvis intet kan læses.

    `limit` er et bevidst loft: fire billeder er rigeligt til en tur, og et
    dusin ville fylde konteksten uden at nogen havde bedt om det.
    """
    ud: list[dict[str, Any]] = []
    for aid in image_ids_on_message(content_json)[: max(1, int(limit))]:
        try:
            from core.services.attachment_service import image_data_url
            url = image_data_url(aid)
        except Exception:
            url = None
        if url:
            ud.append({"type": "image_url", "image_url": {"url": url}})
    return ud
