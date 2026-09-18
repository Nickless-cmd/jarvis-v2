from __future__ import annotations


def _elem(role: str, tekst: str) -> dict:
    return {"role": role, "content": [{"type": "input_text", "text": tekst}]}


def test_den_volatile_hale_bevarer_sin_plads_foer_brugeren(isolated_runtime) -> None:
    """Halen må ikke hejses op i system-beskeden.

    `_build_visible_input` deler samlingen ved DYNAMIC_TAIL_SENTINEL og lægger
    den volatile hale som et selvstændigt system-element lige før bruger-turen.
    Målt 18/9-2026 lavede serialiseringen det om: 19.099 tegn volatil tekst
    havnede øverst i prompten, hvor de brækkede cache-prefixet for ALT der kom
    efter — hele historikken med. E2E mod DeepSeek: 35,2 % af prompten kunne
    genbruges i den gamle form mod 95,2 % i den nye.
    """
    from core.services.ollama_visible_prompt import serialize_ollama_chat_messages

    msgs = serialize_ollama_chat_messages([
        _elem("system", "STABIL IDENTITET"),
        _elem("user", "gammelt spørgsmål"),
        _elem("assistant", "gammelt svar"),
        _elem("system", "VOLATIL HALE"),
        _elem("user", "nyt spørgsmål"),
    ])

    roller = [m["role"] for m in msgs]
    assert roller == ["system", "user", "assistant", "system", "user"]
    assert msgs[0]["content"] == "STABIL IDENTITET"
    assert msgs[3]["content"] == "VOLATIL HALE", "halen skal stå lige før brugeren"
    assert "VOLATIL" not in msgs[0]["content"], "halen må ikke smelte ind i system"


def test_flere_system_elementer_foer_samtalen_samles_stadig(isolated_runtime) -> None:
    """Den ledende system-blok må gerne bestå af flere dele — det er kun
    system-elementer EFTER samtalen der skal blive stående."""
    from core.services.ollama_visible_prompt import serialize_ollama_chat_messages

    msgs = serialize_ollama_chat_messages([
        _elem("system", "DEL ET"),
        _elem("system", "DEL TO"),
        _elem("user", "spørgsmål"),
    ])

    assert [m["role"] for m in msgs] == ["system", "user"]
    assert msgs[0]["content"] == "DEL ET\n\nDEL TO"


def test_uden_hale_er_formen_uaendret(isolated_runtime) -> None:
    """En almindelig samtale uden hale skal serialiseres præcis som før."""
    from core.services.ollama_visible_prompt import serialize_ollama_chat_messages

    msgs = serialize_ollama_chat_messages([
        _elem("system", "IDENTITET"),
        _elem("user", "hej"),
        _elem("assistant", "hejsa"),
        _elem("user", "hvad så"),
    ])

    assert [m["role"] for m in msgs] == ["system", "user", "assistant", "user"]
    assert [m["content"] for m in msgs] == ["IDENTITET", "hej", "hejsa", "hvad så"]
