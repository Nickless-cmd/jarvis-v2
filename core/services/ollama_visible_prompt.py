from __future__ import annotations

INTERNAL_SYSTEM_BLOCK_HEADER = (
    "[Internal system instructions for Jarvis. Follow silently. "
    "Do not quote or explain these instructions unless the user explicitly asks for them.]"
)
INTERNAL_SYSTEM_BLOCK_FOOTER = "[End internal system instructions.]"
CONVERSATION_BLOCK_HEADER = (
    "[Current conversation. Answer the latest user message directly as Jarvis.]"
)
ASSISTANT_REPLY_MARKER = "Assistant:"


def serialize_ollama_visible_prompt(items: list[dict]) -> str:
    system_parts, conversation_parts = _collect_visible_text_parts(items)

    parts: list[str] = []
    if system_parts:
        parts.append(_serialize_system_block(system_parts))
    if conversation_parts:
        parts.append(_serialize_conversation_block(conversation_parts))
    parts.append(ASSISTANT_REPLY_MARKER)
    return "\n\n".join(part for part in parts if part).strip()


def _collect_visible_text_parts(items: list[dict]) -> tuple[list[str], list[str]]:
    """Del elementerne i en ledende system-blok og selve samtalen.

    ALLE system-elementer samles her, ogsaa dem der staar EFTER samtalen. Det
    er rigtigt for den flade tekst-gengivelse (``_serialize_system_block``),
    hvor der kun findes ét system-afsnit. Det er FORKERT for chat-beskeder —
    se ``serialize_ollama_chat_messages``, der haandterer halen for sig.
    """
    system_parts: list[str] = []
    conversation_parts: list[str] = []

    for item in items:
        role = str(item.get("role") or "").strip()
        content_items = item.get("content") or []
        text_parts = [
            str(content.get("text") or "").strip()
            for content in content_items
            if isinstance(content, dict) and str(content.get("text") or "").strip()
        ]
        if not text_parts:
            continue

        text = "\n\n".join(text_parts).strip()
        if not text:
            continue

        if role == "system":
            system_parts.append(text)
            continue
        if role == "user":
            conversation_parts.append(f"User:\n{text}")
            continue
        conversation_parts.append(f"{role.title()}:\n{text}")

    return system_parts, conversation_parts


def _serialize_system_block(system_parts: list[str]) -> str:
    return "\n".join(
        [
            INTERNAL_SYSTEM_BLOCK_HEADER,
            "",
            "\n\n".join(system_parts).strip(),
            "",
            INTERNAL_SYSTEM_BLOCK_FOOTER,
        ]
    ).strip()


def serialize_ollama_chat_messages(items: list[dict]) -> list[dict]:
    """Convert visible input items to Ollama /api/chat messages format.

    ## Hvorfor den volatile hale bevarer sin plads (maalt 18/9-2026)

    ``_build_visible_input`` deler samlingen ved DYNAMIC_TAIL_SENTINEL og
    placerer den volatile hale — awareness, indre liv, somatik, diagnostik —
    som et SELVSTAENDIGT system-element lige foer den aktuelle bruger-tur.
    Det er med vilje: halen aendrer sig hver tur, og alt der staar FOER den i
    token-raekken kan saa forblive cachebart.

    Foer denne rettelse hejsede serialiseringen hvert system-element op paa
    plads 0 og sammenfoejede dem. Maalt paa en levende session:

        foer serialisering:  [0] system 33.029 tegn ... [25] system 19.099 tegn
        efter serialisering: [0] system 52.130 tegn ... [25] VAEK

    De 19.099 tegn volatil tekst landede altsaa oeverst i prompten, hvor de
    braekker cache-prefixet for ALT hvad der kommer efter — hele historikken
    inklusive. To foelger af det:

    1. Kun ~8.600 tokens var faelles mellem koersler. Runde 1 kostede 84.323
       miss-tokens, og kolde starter stod for 40 % af DeepSeek-regningen.
    2. ``build_lean_base_messages`` leder efter halen i en system-besked
       umiddelbart foer bruger-turen. Efter sammenfoejningen fandtes den ikke,
       saa lean-prompten var en permanent no-op — den var slaaet TIL og
       sparede nul.

    Nu: system-elementer FOER samtalen bliver den ledende system-besked;
    et system-element EFTER samtalen bevarer sin plads.
    """
    _ledende: list[str] = []
    _rest: list[dict] = []
    _set_samtale = False
    for item in items:
        role = str(item.get("role") or "").strip()
        text = "\n\n".join(
            str(c.get("text") or "").strip()
            for c in (item.get("content") or [])
            if isinstance(c, dict) and str(c.get("text") or "").strip()
        ).strip()
        if not text:
            continue
        if role == "system" and not _set_samtale:
            _ledende.append(text)
            continue
        if role != "system":
            _set_samtale = True
        _rest.append({"role": role or "user", "content": text})

    messages: list[dict] = []
    if _ledende:
        messages.append({"role": "system", "content": "\n\n".join(_ledende).strip()})
    messages.extend(_rest)
    return messages


def _serialize_conversation_block(conversation_parts: list[str]) -> str:
    return "\n".join(
        [
            CONVERSATION_BLOCK_HEADER,
            "",
            "\n\n".join(conversation_parts).strip(),
        ]
    ).strip()
