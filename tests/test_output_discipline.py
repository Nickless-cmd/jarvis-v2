"""Harness Part 1: tiered output-discipline instruction."""
from core.services.prompt_contract import _output_discipline_instruction


def test_both_tiers_get_synthesis():
    for s in ("weak", "strong"):
        t = _output_discipline_instruction(strength=s)
        assert "enough" in t.lower() and "synthes" in t.lower()


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

    `suggest_next_message` er med fordi den var det tredje tilfaelde af samme
    moenster: maalt 6/10-2026 kaldt 281 gange af 96.399 vaerktoejskald (0,29 %)
    og naevnt NUL steder i prompten — mens de forslag han faktisk skrev blev
    accepteret 49 af 192 gange (25,5 %)."""
    from core.services.tool_tagger import get_pinned_set, invalidate_cache

    invalidate_cache()
    pinned = get_pinned_set()
    tekst = _output_discipline_instruction(strength="strong")
    for navn in ("vis_graf", "vis_widget", "suggest_next_message"):
        assert navn in tekst, f"{navn} naevnes ikke i prompten"
        assert navn in pinned, (
            f"prompten beder om {navn}, men det er ikke pinned — anvisningen "
            f"kan ikke indfries"
        )


def test_forslaget_loves_at_overleve_en_genstart():
    """Linjen siger det, OG koden gør det (`test_composer_suggest`). Et loefte
    i prompten uden daekning i koden er vaerre end ingen linje."""
    t = _output_discipline_instruction(strength="weak")
    assert "survives an app restart" in t
