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
    assert "hver overskrift i et flerleddet svar bærer en relevant emoji" in tail
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

    assert "regulerer den fælles kerne op eller ned" in tail
    assert "mærkbart legende" in tail
    assert "hver overskrift i et flerleddet svar bærer en relevant emoji" in tail
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
    """Den levende, skimmelige kerne skal med i halen i chat mode."""
    from core.services.visible_chat_pragmatics import build_chat_mode_dynamic_tail
    from core.tools.tool_scoping import reset_tool_scope, set_tool_scope

    token = set_tool_scope("chat")
    try:
        tail = build_chat_mode_dynamic_tail("", message="hvad lavede du i git-loggen?", session_id=None)
    finally:
        reset_tool_scope(token)
    assert "## Chatmode: hvordan jeg taler" in tail
    assert "læsehjælp" in tail
    assert "fast konklusionssektion" in tail
    # 24/10-2026: kontrakten navngav selv afslutningssektionen som eksempel, og
    # så blev den en signatur i hvert svar (Bjørn: «du behøver ikke bruge denne
    # linje i hver besked»). Kontrakten må ikke foreskrive en fast sektion.
    assert "Hvad jeg især lægger mærke til" not in tail
    assert "Vis beviset" in tail
    assert "Grundniveauet i chat er mærkbart engagement" in tail


def test_chatkernen_baerer_de_fem_formgreb_uden_at_tvinge_dem_ind() -> None:
    """Bjørn 25/10-2026: GPT-formen er en styrke, ikke en uvane.

    De fem greb skal være chatkernens fælles repertoire. Samtidig må de ikke
    blive en mekanisk tjekliste, for et kort svar skal fortsat kunne være kort.

    25/10-2026 (målt): 120 svar havde 5 % overskrifter og 5 % lister, mens 90 %
    af prosa-afsnittene var på ≤3 sætninger. Reglen var symmetrisk formuleret
    («værktøjer, ikke en tjekliste»), og symmetri betød at tvivlen altid faldt
    ud til prosaens fordel. Kontrakten er derfor asymmetrisk nu: ved tvivl
    vælger modellen strukturen, men et svar på én pointe skal stadig være kort.
    """
    from core.services.chat_response_policy import CHAT_FORMAT_CORE

    tekst = CHAT_FORMAT_CORE.lower()
    for greb in ("korte afsnit", "overskrifter", "punktopstilling", "fed skrift", "emoji"):
        assert greb in tekst, greb
    # Asymmetrien: standardvalget ved tvivl er struktur, ikke prosa.
    assert "er du i tvivl, så strukturér" in tekst
    assert "et svar på én pointe skal ikke" in tekst
    # Formen skal kunne SPEJLES, ikke kun beskrives — derfor konkrete eksempler.
    assert "lille, én pointe uden struktur" in tekst
    assert "større, tre dele" in tekst
    assert "som et svar til en kollega, ikke som en rapport" in tekst


def test_chatkernen_gider_kan_toer_og_goer() -> None:
    """Engagement skal være baseline; brugerknapperne regulerer intensiteten."""
    from core.services.chat_response_policy import CHAT_ENGAGEMENT_CORE

    tekst = CHAT_ENGAGEMENT_CORE
    for traek in ("GID:", "KAN:", "TØR:", "GØR:"):
        assert traek in tekst
    assert "skruer op og ned" in tekst
    assert "slukker aldrig dette grundniveau" in tekst


def test_injicerede_chatregler_modsiger_ikke_formkernen() -> None:
    """De gamle regler gjorde prosa moralsk rigtig og struktur mistænkelig.

    Saml de to chat-specifikke promptlag, modellen faktisk ser, og hold de
    kendte modsigelser ude. Det er adfærd ved prompt-sømmen, ikke et grep i en
    tilfældig workspace-fil.
    """
    from core.services.chat_conversation_rules import section
    from core.services.prompt_sections.chat_mode import _visible_chat_tone_instruction
    from core.services.visible_chat_pragmatics import CHAT_MODE_HOW_I_TALK
    from core.tools.tool_scoping import tool_scope

    with tool_scope("chat"):
        samlet = "\n".join(filter(None, [
            _visible_chat_tone_instruction(compact=False),
            section(compact=False),
            CHAT_MODE_HOW_I_TALK,
        ]))

    assert "Prosa er standard" not in samlet
    assert "Hver ny tanke får sin egen blok" not in samlet
    assert "typisk to til fire afsnit" not in samlet
    assert "Form følger læseopgaven" in samlet
    assert "Knapperne skruer op og ned" in samlet
    assert "afsluttende autoritet for synlig samtaleadfærd og form" in samlet
    assert "workspace-filer" in samlet and "må ikke ophæve det" in samlet


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


def test_chat_chooses_presence_closure_and_surface_by_reading_task() -> None:
    from core.services.chat_response_policy import SURFACE_READING_TASKS
    from core.services.visible_chat_pragmatics import CHAT_MODE_HOW_I_TALK

    assert {"compare", "sequence", "scan_numbers", "choose", "locate", "warn"} == set(
        SURFACE_READING_TASKS.values()
    )
    assert "hvad du selv mener" in CHAT_MODE_HOW_I_TALK
    assert "samtale (en levende reaktion" in CHAT_MODE_HOW_I_TALK
    assert "Kun leverance" in CHAT_MODE_HOW_I_TALK
    assert "Vælg flade efter læseopgaven" in CHAT_MODE_HOW_I_TALK
    assert "ikke blot fordi der er mange" in CHAT_MODE_HOW_I_TALK
    assert "Placér fladen inline" in CHAT_MODE_HOW_I_TALK
    assert "nævn aldrig tilstandene" in CHAT_MODE_HOW_I_TALK


def test_presence_and_surface_decisions_never_reach_code_mode() -> None:
    from core.tools.tool_scoping import tool_scope

    with tool_scope("chat"):
        chat = build_chat_mode_dynamic_tail("", message="sammenlign dem", session_id="s")
    with tool_scope("code"):
        code = build_chat_mode_dynamic_tail("", message="sammenlign dem", session_id="s")

    assert "Vælg flade efter læseopgaven" in chat
    assert "Kun leverance" in chat
    assert "Vælg flade efter læseopgaven" not in code
    assert "Kun leverance" not in code


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
    assert "tanke → flade" in tekst.lower()
    for flade in ("timeline", "comparison", "stats", "callout", "choices", "location"):
        assert flade in tekst, flade
    # Skemaerne skal stadig stå der — en forkert values-længde dropper rækken tavst.
    assert "præcis samme antal som" in tekst
    # Den gamle tilladelses-formulering må ikke snige sig ind igen.
    assert "kan du skrive" not in tekst
    assert "når én kompakt visuel flade er tydeligere end prosa" not in tekst.lower()


def test_tekstdisciplin_staar_i_kontrakten_og_i_halen() -> None:
    """Fælden: niveau 3 sagde hvordan afsnit bygges, men intet om hvor langt et svar
    må være — så «vær grundig» vandt over «vær læsbar». Målt 24/10-2026: Bjørn pegede
    på tekstdisciplin som det sidste der manglede, efter at fladerne var på plads.
    """
    from core.services.visible_chat_pragmatics import (
        CHAT_MODE_HOW_I_TALK,
        build_chat_mode_dynamic_tail,
    )
    from core.tools.tool_scoping import reset_tool_scope, set_tool_scope

    assert "Tekstdisciplin" in CHAT_MODE_HOW_I_TALK
    # lean-vagtens forudsætning: kontrakten skal være ÉN blok uden tomme linjer internt.
    assert "\n\n" not in CHAT_MODE_HOW_I_TALK

    token = set_tool_scope("chat")
    try:
        tail = build_chat_mode_dynamic_tail("", message="hvad lavede du i git-loggen?", session_id=None)
    finally:
        reset_tool_scope(token)
    assert "Tekstdisciplin" in tail

    token = set_tool_scope("code")
    try:
        tail_code = build_chat_mode_dynamic_tail("", message="ret koden", session_id=None)
    finally:
        reset_tool_scope(token)
    assert "Tekstdisciplin" not in tail_code


def test_max_profil_er_et_gulv_ikke_et_loft(monkeypatch) -> None:
    """Bjørn 25/10-2026: «hvis jeg ikk beder dig om det så gør du det ikk».

    Målt på 150 svar med ALLE fem knapper på max (playful/expressive/
    comfortable/rich/curious): overskrifter 9 %, emoji i overskriften 1 %,
    lister 11 %. Profilen var altså ikke problemet — den var allerede skruet
    i bund. Teksterne var skrevet som LOFT («højst en eller to», «gerne når
    profilen bærer den», «undlad når …»), så der var intet at skrue OP til.

    En maks-profil skal derfor læses som et GULV: standarden er at formen ER
    der, og undtagelsen skal begrundes — ikke omvendt.
    """
    monkeypatch.setattr(
        "core.context.output_style.hent_chat_style",
        lambda _: {
            "tone": "playful", "emoji": "expressive", "profanity": "comfortable",
            "visuals": "rich", "questions": "curious",
        },
    )
    with tool_scope("chat"):
        tail = build_chat_mode_dynamic_tail("", message="vis mig det", session_id="s")

    # Emoji: fast del af formen, ikke en undtagelse — og knyttet til overskriften.
    assert "FAST del af formen" in tail
    assert "hver overskrift i et flerleddet svar bærer en relevant emoji" in tail
    assert "Det er standarden" in tail

    # Visuelt: hierarki er et krav ved tre eller flere dele, flader er standardvalget.
    assert "SKAL have hierarki" in tail
    assert "det er standardvalget" in tail

    # Det gamle loft må ikke snige sig ind igen.
    assert "en eller to" not in tail
    assert "gerne med en relevant emoji når" not in tail


def test_kernen_kan_ikke_ophaeve_profilens_gulv() -> None:
    """Niveau 3 må ikke længere sige at grebene «ikke er obligatoriske».

    Målt 25/10-2026: niveau 3 sagde «de gør ikke grebene enten forbudte eller
    obligatoriske», mens niveau 5 sagde «SKAL have hierarki». To niveauer pegede
    hver sin vej, og i tvivl faldt jeg tilbage til prosa — 9 % overskrifter og
    1 % emoji i overskriften med alle fem knapper på maks. Kernen skal skrue OP,
    aldrig ned, og et loft må ikke kunne læses som et valg.
    """
    from core.services.chat_response_policy import CHAT_FORMAT_CORE

    tekst = CHAT_FORMAT_CORE.lower()
    assert "skruer op for denne kerne" in tekst
    assert "aldrig sjældnere end kernen kræver" in tekst
    assert "et loft er ikke et valg" in tekst
    # Den gamle dobbelthed må ikke snige sig ind igen.
    assert "forbudte eller obligatoriske" not in tekst
    assert "regulerer hyppighed og styrke" not in tekst
