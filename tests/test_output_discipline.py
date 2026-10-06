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
    """Rendereren fandtes i desk hele foraaret og stod ikke ét sted i prompten.
    Maalt 6/10-2026: **0 af 10.774** assistent-beskeder havde et mermaid-hegn —
    han har aldrig emitteret ét. (Foerste opslag gav 3; de var en
    compact_marker og to tool-resultater, fordi jeg ikke filtrerede paa rolle.)

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
