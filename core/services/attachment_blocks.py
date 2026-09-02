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
