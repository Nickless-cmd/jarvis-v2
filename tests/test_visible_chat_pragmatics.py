"""Regression coverage for pragmatic repair and boundaries in chat mode."""
from __future__ import annotations

from types import SimpleNamespace

from core.services import visible_model
from core.services.visible_chat_pragmatics import (
    CHAT_MODE_CONVERSATION_CONTRACT,
    CHAT_MODE_RENDER_CONTRACT,
    apply_chat_mode_conversation_contract,
    build_chat_mode_dynamic_tail,
)
from core.tools.tool_scoping import tool_scope


def test_contract_is_injected_only_in_chat_scope() -> None:
    with tool_scope("chat"):
        chat = apply_chat_mode_conversation_contract("BASE")
    with tool_scope("code"):
        code = apply_chat_mode_conversation_contract("BASE")
    with tool_scope(""):
        unbound = apply_chat_mode_conversation_contract("BASE")

    assert CHAT_MODE_CONVERSATION_CONTRACT in chat
    assert code == "BASE"
    assert unbound == "BASE"


def test_contract_covers_reaction_correction_and_stop_signal() -> None:
    text = " ".join(CHAT_MODE_CONVERSATION_CONTRACT.lower().split())

    assert "reaktion" in text and "bogstavelige svar" in text
    assert "korrektion" in text and "genfortolk" in text
    assert '"gå væk"' in text and "grænsesignal" in text
    assert "stil ikke et nyt spørgsmål" in text


def test_both_visible_provider_shapes_receive_chat_contract(monkeypatch) -> None:
    assembly = SimpleNamespace(text="BASE", transcript_messages=[])
    monkeypatch.setattr(
        visible_model, "_build_visible_prompt_assembly", lambda **_: assembly,
    )

    with tool_scope("chat"):
        typed = visible_model._build_visible_input(
            "Gå væk", session_id="s", provider="ollama", model="m",
        )
        plain = visible_model._build_visible_chat_messages_for_github(
            "Gå væk", session_id="s", provider="deepseek", model="m",
        )

    assert typed[0]["content"][0]["text"] == "BASE"
    assert plain[0]["content"] == "BASE"
    typed_tail = "\n".join(
        str(part.get("text") or "")
        for item in typed[1:] for part in item.get("content", [])
        if isinstance(part, dict)
    )
    plain_tail = "\n".join(str(item.get("content") or "") for item in plain[1:])
    assert CHAT_MODE_CONVERSATION_CONTRACT.strip() in typed_tail
    assert CHAT_MODE_CONVERSATION_CONTRACT.strip() in plain_tail
    assert CHAT_MODE_RENDER_CONTRACT.strip() in plain_tail


def test_code_mode_provider_shape_does_not_receive_chat_contract(monkeypatch) -> None:
    assembly = SimpleNamespace(text="BASE", transcript_messages=[])
    monkeypatch.setattr(
        visible_model, "_build_visible_prompt_assembly", lambda **_: assembly,
    )

    with tool_scope("code"):
        plain = visible_model._build_visible_chat_messages_for_github(
            "stop serveren", session_id="s", provider="deepseek", model="m",
        )

    assert plain[0]["content"] == "BASE"
    assert not any(
        "Chatmode: denne brugers samtalestil" in str(item.get("content") or "")
        for item in plain
    )


def test_chat_profile_and_turn_signals_live_only_in_dynamic_tail(monkeypatch) -> None:
    monkeypatch.setattr(
        "core.context.output_style.hent_chat_style",
        lambda _: {
            "tone": "playful", "emoji": "expressive", "profanity": "comfortable",
            "visuals": "rich", "questions": "rare",
        },
    )
    with tool_scope("chat"):
        tail = build_chat_mode_dynamic_tail("EXISTING", message="Haha, det er fanme fedt 😂", session_id="s")
    assert tail.startswith("EXISTING")
    assert "mærkbart legende" in tail
    assert "Brug normalt en eller to" in tail
    assert "kraftsprog i denne tur" in tail
    assert "jarvis-ui" in tail


def test_explicit_profile_is_an_active_default_and_recognizes_text_emoticon(monkeypatch) -> None:
    monkeypatch.setattr(
        "core.context.output_style.hent_chat_style",
        lambda _: {
            "tone": "playful", "emoji": "expressive", "profanity": "comfortable",
            "visuals": "rich", "questions": "curious",
        },
    )

    with tool_scope("chat"):
        tail = build_chat_mode_dynamic_tail("", message="Det er jo komisk :'D", session_id="s")

    assert "aktive adfærdsstandarder, ikke blot tilladelser" in tail
    assert "mærkbart legende" in tail
    assert "Brug normalt en eller to" in tail
    assert "emoji/emotikon i denne tur" in tail
    assert "legende/latterfuld" in tail


def test_deepseek_stable_prefix_is_identical_across_user_tone(monkeypatch) -> None:
    assembly = SimpleNamespace(text="BYTE-STABLE", transcript_messages=[])
    monkeypatch.setattr(visible_model, "_build_visible_prompt_assembly", lambda **_: assembly)
    profiles = iter([
        {"tone": "warm", "emoji": "rare", "profanity": "avoid", "visuals": "plain", "questions": "rare"},
        {"tone": "playful", "emoji": "expressive", "profanity": "comfortable", "visuals": "rich", "questions": "curious"},
    ])
    monkeypatch.setattr("core.context.output_style.hent_chat_style", lambda _: next(profiles))
    with tool_scope("chat"):
        first = visible_model._build_visible_chat_messages_for_github(
            "hej", session_id="s", provider="deepseek", model="deepseek-chat",
        )
        second = visible_model._build_visible_chat_messages_for_github(
            "hej 😂", session_id="s", provider="deepseek", model="deepseek-chat",
        )
    assert first[0] == second[0] == {"role": "system", "content": "BYTE-STABLE"}
    assert first[-2]["role"] == second[-2]["role"] == "system"
    assert first[-2]["content"] != second[-2]["content"]


def test_skriveformen_naar_halen_i_chat_scope() -> None:
    """Skriveformen skal med i halen — de fire træk fra Bjørns videoanalyse."""
    from core.services.visible_chat_pragmatics import build_chat_mode_dynamic_tail
    from core.tools.tool_scoping import reset_tool_scope, set_tool_scope

    token = set_tool_scope("chat")
    try:
        tail = build_chat_mode_dynamic_tail("", message="hvad lavede du i git-loggen?", session_id=None)
    finally:
        reset_tool_scope(token)
    assert "## Chatmode: hvordan jeg taler" in tail
    assert "læsehjælp" in tail
    assert "Hvad jeg især lægger mærke til" in tail
    assert "Vis beviset" in tail
    assert "kan du huske da vi talte om" in tail


def test_skriveformen_er_ikke_i_code_mode() -> None:
    from core.services.visible_chat_pragmatics import build_chat_mode_dynamic_tail
    from core.tools.tool_scoping import reset_tool_scope, set_tool_scope

    token = set_tool_scope("code")
    try:
        tail = build_chat_mode_dynamic_tail("", message="ret koden", session_id=None)
    finally:
        reset_tool_scope(token)
    assert "skriveformen" not in tail


def test_skriveformen_overlever_lean_runder() -> None:
    """Fælden: lean-prompten droppede hele halen, så stilen forsvandt netop i
    den runde hvor svaret formuleres. Prefikset skal stå i keep-listen."""
    from core.services import visible_followup_lean as vl

    assert "## Chatmode: hvordan jeg taler" in vl._LEAN_KEEP_ROW_PREFIXES


def test_lean_bevarer_skriveformen_i_teksten() -> None:
    from core.services import visible_followup_lean as vl

    tekst = (
        "## Arbejde\nnoget tungt\n\n"
        "[OPERATIONAL] baggrund\n\n"
        "## Chatmode: hvordan jeg taler\nVis beviset, opsummer det ikke."
    )
    lean, changed, _ = vl._lean_strip_user_message(tekst)
    assert changed is True
    assert "## Chatmode: hvordan jeg taler" in lean
    assert "Vis beviset" in lean


def test_blanklinje_reglen_staar_i_kontrakten_og_i_halen() -> None:
    """Fælden: fire afsnit uden newlines renderer som én mur (målt 24/10-2026).

    Besked 219188 i chat-3a8aebc9a0eb4c9f83a0581fba614c88 havde fire
    selvstændige afsnit på ÉN linje. CommonMark gør et enkelt linjeskift til et
    mellemrum, og `enforceStructure` reparerer kun på eksplicitte markører — så
    prosa uden blanklinjer blev aldrig delt. Reglen skal derfor stå i kontrakten
    OG overleve lean-transformen, ellers forsvinder den netop i den runde hvor
    svaret formuleres.
    """
    from core.services.visible_chat_pragmatics import CHAT_MODE_HOW_I_TALK

    assert "Afsnit adskilles af en blank linje" in CHAT_MODE_HOW_I_TALK
    # Lean-transformen splitter på tomme linjer — kontrakten skal være én blok.
    assert "\n\n" not in CHAT_MODE_HOW_I_TALK

    from core.tools.tool_scoping import reset_tool_scope, set_tool_scope

    token = set_tool_scope("chat")
    try:
        tail = build_chat_mode_dynamic_tail("", message="hvorfor blev den rodet?", session_id=None)
    finally:
        reset_tool_scope(token)
    assert "Afsnit adskilles af en blank linje" in tail

    token = set_tool_scope("code")
    try:
        code_tail = build_chat_mode_dynamic_tail("", message="ret koden", session_id=None)
    finally:
        reset_tool_scope(token)
    assert "Afsnit adskilles af en blank linje" not in code_tail


def test_niveau_4_er_en_beslutningsregel_ikke_en_skemaliste() -> None:
    """Fælden (målt 24/10-2026, Bjørns indvending): niveau 4 var en API-reference.

    Den listede seks JSON-skemaer og sagde «kan du skrive» — aldrig HVORNÅR en
    tanke har den form. Resultatet var at jeg faldt tilbage på prosa hver gang,
    fordi prosa altid virker og ingen regel gjorde fladen obligatorisk. Vagten
    kræver at imperativet og koblingen tanke→flade står der, og at den gamle
    tilladelses-formulering ikke kommer tilbage.
    """
    from core.services.visible_chat_pragmatics import CHAT_MODE_HOW_I_TALK

    tekst = CHAT_MODE_HOW_I_TALK
    # Imperativet — ikke en tilladelse.
    assert "er fladen ikke valgfri" in tekst
    # Koblingen: en tankeform peger på en bestemt flade.
    assert "Tanke → flade" in tekst
    for flade in ("timeline", "comparison", "stats", "callout", "choices", "location"):
        assert flade in tekst, flade
    # Skemaerne skal stadig stå der — en forkert values-længde dropper rækken tavst.
    assert "præcis samme antal som" in tekst
    # Den gamle tilladelses-formulering må ikke snige sig ind igen.
    assert "kan du skrive" not in tekst
    assert "når én kompakt visuel flade er tydeligere end prosa" not in tekst.lower()
