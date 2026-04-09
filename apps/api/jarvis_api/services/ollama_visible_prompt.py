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
    """Convert visible input items to Ollama /api/chat messages format."""
    system_parts, conversation_parts = _collect_visible_text_parts(items)
    messages: list[dict] = []
    if system_parts:
        messages.append({
            "role": "system",
            "content": "\n\n".join(system_parts).strip(),
        })
    for part in conversation_parts:
        if part.startswith("User:\n"):
            messages.append({"role": "user", "content": part[6:].strip()})
        elif part.startswith("Assistant:\n"):
            messages.append({"role": "assistant", "content": part[11:].strip()})
        else:
            messages.append({"role": "user", "content": part.strip()})
    return messages


def _serialize_conversation_block(conversation_parts: list[str]) -> str:
    return "\n".join(
        [
            CONVERSATION_BLOCK_HEADER,
            "",
            "\n\n".join(conversation_parts).strip(),
        ]
    ).strip()
