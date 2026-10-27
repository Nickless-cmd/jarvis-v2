"""Harness Part 1: tiered output-discipline instruction."""
from core.services.prompt_contract import _output_discipline_instruction


def test_both_tiers_get_synthesis():
    for s in ("weak", "strong"):
        t = _output_discipline_instruction(strength=s)
        assert "enough" in t.lower() and "synthes" in t.lower()


def test_both_tiers_define_commentary_and_final_answer_lanes():
    for strength in ("weak", "strong"):
        text = _output_discipline_instruction(strength=strength)
        assert "Call the first tool BEFORE writing prose" in text
        assert "between tool rounds is commentary" in text
        assert "terminal, tool-free response completes the current turn" in text
        assert "final answer" in text


def test_strong_gets_conciseness_weak_does_not():
    strong = _output_discipline_instruction(strength="strong")
    weak = _output_discipline_instruction(strength="weak")
    assert "25 words" in strong and "100 words" in strong
    assert "25 words" not in weak and "100 words" not in weak


def test_self_safe_on_bad_input():
    assert isinstance(_output_discipline_instruction(strength="bogus"), str)


# ── Visuelle svar: kapabiliteten skal STAA der, og ikke modsiges ─────────────


def test_begge_niveauer_faar_at_vide_at_mermaid_tegnes():
    """Maalt 6/10-2026: **0 af 10.774** assistent-beskeder havde et
    mermaid-hegn — han har aldrig emitteret ét. (Foerste opslag gav 3; de var en
    compact_marker og to tool-resultater, fordi jeg ikke filtrerede paa rolle.)

    Jeg begrundede det med at rendereren «fandtes men var utalt». Det var
    forkert: den var slettet 29/9 (`93be59bb6`, Codex), og jeg laeste den fra et
    gammelt checkout. Linjen var FALSK da den gik live — og Jarvis gjorde den
    sand ved selv at bygge rendereren (`c78754043`).

    Testen findes fordi en kapabilitet kun eksisterer hvis den er NAEVNT —
    linjen her er hele forbindelsen mellem en bygget renderer og en model der
    bruger den."""
    for s in ("weak", "strong"):
        t = _output_discipline_instruction(strength=s)
        assert "```mermaid" in t, f"{s}: mermaid-kapabiliteten mangler"
        assert "RENDERED" in t
        # Mobilen kan ikke tegne den endnu — han skal vide det, ellers svarer
        # han kun i et diagram og telefonen staar med rå kilde.
        assert "mobile" in t.lower()


def test_ordloftet_forbyder_ikke_det_han_lige_fik_lov_til():
    """Kun STRONG har et ordloft, og et diagram er altid over 100 ord. Uden
    undtagelsen slaar de to instruktioner hinanden ihjel."""
    strong = _output_discipline_instruction(strength="strong")
    weak = _output_discipline_instruction(strength="weak")
    assert "100 words" in strong and "does NOT count toward the word cap" in strong
    # Weak har intet loft, saa en undtagelse ville vaere stoej der peger paa en
    # regel der ikke findes.
    assert "100 words" not in weak and "word cap" not in weak


def test_de_tre_visuelle_vaerktoejer_er_alle_NAEVNT_og_pinned():
    """Et vaerktoej prompten beder om SKAL vaere pinned — routeren sender 70-97
    af ~495, og et nyt uden kald-historik kommer ikke i always-core af sig selv.
    Reglen staar i pinned-filens eget `_doc`.

    `suggest_next_task` er med fordi den var det tredje tilfaelde af samme
    moenster: maalt 6/10-2026 kaldt 281 gange af 96.399 vaerktoejskald (0,29 %)
    og naevnt NUL steder i prompten — mens de forslag han faktisk skrev blev
    accepteret 49 af 192 gange (25,5 %)."""
    from core.services.tool_tagger import get_pinned_set, invalidate_cache

    invalidate_cache()
    pinned = get_pinned_set()
    tekst = _output_discipline_instruction(strength="strong")
    for navn in ("vis_graf", "vis_widget", "suggest_next_task"):
        assert navn in tekst, f"{navn} naevnes ikke i prompten"
        assert navn in pinned, (
            f"prompten beder om {navn}, men det er ikke pinned — anvisningen "
            f"kan ikke indfries"
        )


def test_spoergsmaal_gaar_til_pause_and_ask_ikke_komponisten():
    """Maalt 11/10-2026: `pause_and_ask` blev naevnt NUL steder i hele
    prompt_sections/. Reglen fandtes kun for den ENE halvdel — den der peger
    paa komponisten — og en vagt bakkede den op. Saa naar Jarvis havde et
    spoergsmaal, endte det i Bjorns skrivefelt som om det var hans egen besked.
    Bjorn 11/10-2026: «spoergsmaal skal gaa til pause and ask».

    Rangeringen er ogsaa en del af reglen: der findes INTET saerskilt
    anbefalet-felt — raekkefoelgen af options ER rangeringen, saa den
    anbefalede skal staa foerst med «(anbefalet)» i teksten."""
    for s in ("weak", "strong"):
        t = _output_discipline_instruction(strength=s)
        assert "pause_and_ask" in t, f"{s}: spoergsmaal-vejen mangler"
        assert "QUESTION does NOT" in t, f"{s}: forbuddet mod spoergsmaal mangler"
        assert "anbefalet" in t, f"{s}: rangeringen mangler"


def test_pause_and_ask_er_pinned_som_prompten_kraever():
    """Samme regel som de tre visuelle: beder prompten om et vaerktoej, SKAL det
    staa i pinned-filen — ellers kan anvisningen ikke indfries, og Jarvis maa
    hente det midt i turen."""
    from core.services.tool_tagger import get_pinned_set, invalidate_cache

    invalidate_cache()
    tekst = _output_discipline_instruction(strength="weak")
    assert "pause_and_ask" in tekst
    assert "pause_and_ask" in get_pinned_set()


def test_forslaget_loves_at_overleve_en_genstart():
    """Linjen siger det, OG koden gør det (`test_composer_suggest`). Et loefte
    i prompten uden daekning i koden er vaerre end ingen linje."""
    t = _output_discipline_instruction(strength="weak")
    assert "survives an app restart" in t
