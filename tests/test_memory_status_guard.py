"""Vagt over MEMORY-statusvagten — den skal SE en falsk statuspåstand.

`scripts/verify_memory_status.py` fanger `## `-overskrifter der formulerer sig
som nutid uden et spor. Baggrunden (målt 16/10-2026): MEMORY.md havde 51
sådanne overskrifter, og 16 af dem var blevet falske — «STADIG ÅBEN» om arbejde
der var færdigt for uger siden, «afventer genstart» om en genstart der for
længst var sket. Filen læses ind i prompten hver tur, så en forkert linje
koster Bjørn et træk: han bad mig bygge noget der allerede var bygget.

Vagten kan ikke afgøre SANDHED — den kan kræve et SPOR. Testen her ser den
sige nej, og ser den holde mund når sporet er der.

Ingen af testene rører produktionens MEMORY.md: hjem og grundlinje er
monkeypatchet til tmp_path.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import verify_memory_status as v

ROD = Path(__file__).resolve().parents[1]


@pytest.fixture
def hjem(tmp_path, monkeypatch):
    """Eget JARVIS_HOME og egen grundlinje — hverken produktion eller repo."""
    ws = tmp_path / "workspaces" / "proevemester"
    ws.mkdir(parents=True)
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    grund = tmp_path / "baseline.json"
    grund.write_text(json.dumps({"i_alt": 0, "pr_fil": {}}), encoding="utf-8")
    monkeypatch.setattr(v, "GRUNDLINJE", grund)
    return ws / "MEMORY.md"


def test_statuspaastand_uden_spor_afvises(hjem, capsys):
    hjem.write_text("# Jarvis Memory\n\n## Stadig åbent\n\nnoget.\n", encoding="utf-8")
    assert v.main([]) == 1, "vagten accepterede en statuspåstand uden spor"
    assert "NYE statuspaastande" in capsys.readouterr().out


def test_dato_er_et_spor(hjem):
    hjem.write_text("## Stadig åbent (målt 16/10-2026)\n", encoding="utf-8")
    assert v.main([]) == 0


def test_lukke_markoer_er_et_spor(hjem):
    hjem.write_text("## Stadig uvidst (LUKKET 8/10-2026)\n", encoding="utf-8")
    assert v.main([]) == 0


def test_kilde_pegning_er_et_spor(hjem):
    hjem.write_text("## Det der stadig staar aabent (kilde: compaction_log)\n", encoding="utf-8")
    assert v.main([]) == 0


def test_overskrift_uden_nutids_ord_ignoreres(hjem):
    hjem.write_text("## Hvorfor halen findes\n", encoding="utf-8")
    assert v.main([]) == 0


def test_kun_niveau2_overskrifter_scannes(hjem):
    hjem.write_text("### Stadig åbent\n\n**Stadig åbent**\n\n## Stadig åbent\n", encoding="utf-8")
    assert [nr for nr, _ in v.fund_i_fil(hjem)] == [5]


# ─── brødtekst-fladen (tilføjet 16/10-2026) ────────────────────────────────


def test_broedtekst_paastand_uden_spor_afvises(hjem, capsys):
    hjem.write_text("# M\n\n**Åbent:** noget der ikke er fulgt op\n", encoding="utf-8")
    assert v.main([]) == 1, "vagten accepterede en brødtekst-påstand uden spor"
    assert "broedtekst" in capsys.readouterr().out


def test_broedtekst_med_dato_er_et_spor(hjem):
    hjem.write_text("# M\n\n**Åbent (16/10-2026):** noget\n", encoding="utf-8")
    assert v.main([]) == 0


def test_broedtekst_kraever_at_linjen_STARTER_med_ordet(hjem):
    """En sætning der tilfældigt nævner ordet er ikke en statuslinje.

    Uden dette krav gav en bred scanning 455 træf på den ægte fil — ubrugelig
    støj. En påstand midt i en sætning er også svær at skelne fra almindelig
    prosa.
    """
    hjem.write_text("# M\n\nDet er stadig uvist om han kommer, men vi venter.\n", encoding="utf-8")
    assert v.main([]) == 0


def test_broedtekst_lang_linje_er_en_analyse_ikke_en_status(hjem):
    hjem.write_text("# M\n\n**Åbent:** " + "x" * 200 + "\n", encoding="utf-8")
    assert v.main([]) == 0


def test_listepunkt_og_fed_strippes_foer_vurdering(hjem):
    hjem.write_text("# M\n\n- **Kræver genstart af api.**\n", encoding="utf-8")
    assert v.main([]) == 1


def test_overskrifter_scannes_ikke_som_broedtekst(hjem):
    """`## `-linjer hører til fund_i_fil — de må ikke tælles to gange."""
    hjem.write_text("# M\n\n## Stadig åbent\n", encoding="utf-8")
    assert v.fund_i_broedtekst(hjem) == []
    assert len(v.fund_i_fil(hjem)) == 1


def test_kodehegn_slaar_ikke_resten_af_filen_fra(hjem):
    """Regression 16/10-2026: et ulige antal ``` tippede tællingen og slog
    16.782 linjer fra (72 % af filen). En linje efter et ulige antal hegn
    SKAL scannes — en blind vagt er dyrere end den støj den fjerner.
    """
    hjem.write_text(
        "# M\n\n```\nkode\n```\n\n```\nhalvt hegn\n\n**Åbent:** efter\n",
        encoding="utf-8",
    )
    assert [nr for nr, _ in v.fund_i_broedtekst(hjem)] == [10]


def test_grundlinjen_skrives_kun_med_flaget(hjem):
    hjem.write_text("## Stadig åbent\n", encoding="utf-8")
    assert v.main([]) == 1
    assert v.main(["--skriv-grundlinje"]) == 0
    assert json.loads(Path(v.GRUNDLINJE).read_text(encoding="utf-8"))["i_alt"] == 1
    assert v.main([]) == 0


def test_faerre_end_grundlinjen_er_ikke_en_fejl(hjem, capsys):
    """En oprydning må ikke blokere — kun VÆKST gør."""
    Path(v.GRUNDLINJE).write_text(json.dumps({"i_alt": 5, "pr_fil": {}}), encoding="utf-8")
    hjem.write_text("## Stadig åbent\n", encoding="utf-8")
    assert v.main([]) == 0
    assert "faerre end grundlinjen" in capsys.readouterr().out


def test_ingen_memory_filer_er_ikke_en_fejl(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    assert v.main([]) == 0


# ─── rækkevidden: syv filer, ikke én (udvidet 16/10-2026) ───────────────────


def test_quick_facts_vogtes_ogsaa(hjem, capsys):
    """QUICK_FACTS.md injiceres UBETINGET — uden relevans-filter.

    En forældet linje der koster Bjørn et træk hver tur, ikke kun når han
    spørger om memory. Vagten så før kun MEMORY.md.
    """
    (hjem.parent / "QUICK_FACTS.md").write_text(
        "# QUICK_FACTS\n\n**Afventer genstart** af api.\n", encoding="utf-8"
    )
    assert v.main([]) == 1, "vagten vogter ikke QUICK_FACTS.md"
    assert "QUICK_FACTS.md" in capsys.readouterr().out


def test_raekkevidden_er_de_syv_injicerede_filer():
    """Vagten skal dække præcis de filer prompten læser ind hver tur."""
    assert set(v._BESKYTTEDE) == {
        "MEMORY.md",
        "QUICK_FACTS.md",
        "USER.md",
        "SOUL.md",
        "IDENTITY.md",
        "STANDING_ORDERS.md",
        "VISIBLE_CHAT_RULES.md",
    }


def test_beskyttede_filer_bindes_til_prompt_contract():
    """Listen må ikke drive fra kilden — men må heller ikke importere den.

    Vagten kan ikke importere prompt_contract (så døde den med den). Testen er
    limen: omdøbes eller fjernes en fil i prompten, fejler denne test i stedet
    for at vagten tavst vogter en fil ingen læser.
    """
    kilde = (ROD / "core" / "services" / "prompt_contract.py").read_text(encoding="utf-8")
    mangler = [n for n in v._BESKYTTEDE if n not in kilde]
    assert not mangler, f"vagten vogter filer prompten ikke injicerer: {mangler}"


def test_krypteret_medlemsfil_taelles_ikke(hjem):
    """Et medlems-workspace er krypteret (.enc) — vagten må ikke gætte om den."""
    hjem.write_text("# M\n", encoding="utf-8")
    (hjem.parent / "QUICK_FACTS.md.enc").write_bytes(b"\x00\x01krypteret")
    assert [p.name for p in v._filer()] == ["MEMORY.md"]


# ── QUICK_FACTS må ikke være en hukommelsesbank (målt 23/10-2026) ──────────
#
# Filen var 85.742 tegn med 38 sektioner, hvoraf 26 var opskrifter og fælder.
# Promptens loft på 20.000 klippede 77 % tavst væk — inklusive mobil-APK-
# opskriften. Opskrifterne findes altså, men var usynlige i min egen prompt,
# og jeg gentog kendte fejl med dem foran mig. Reglen nedenfor kræver et VALG
# pr. sektion: opslag (her), fremgangsmåde (PLAYBOOKS.md) eller forløb (MEMORY).


def test_quick_facts_sektion_skal_vaere_erklaeret(hjem, capsys):
    """En ny sektion i QUICK_FACTS kræver at man tager stilling."""
    (hjem.parent / "QUICK_FACTS.md").write_text(
        "# QUICK_FACTS\n\n## Mobil-APK — byg og udgiv\n\nkør gradlew.\n", encoding="utf-8"
    )
    assert v.main([]) == 1, "vagten accepterede en uerklæret sektion i QUICK_FACTS"
    ud = capsys.readouterr().out
    assert "ikke en erklæret opslags-sektion" in ud
    assert "PLAYBOOKS.md" in ud, "fejlbeskeden peger ikke på den rigtige destination"


def test_quick_facts_erklaeret_sektion_er_groen(hjem):
    """Et opslag er kort og står på hvidlisten — det skal passere."""
    (hjem.parent / "QUICK_FACTS.md").write_text(
        "# QUICK_FACTS\n\n## Systemer & URLs\n\n- api: 10.0.0.39\n"
        "## Paths\n\n- repo: /media/projects/jarvis-v2\n",
        encoding="utf-8",
    )
    assert v.main([]) == 0


def test_quick_facts_over_loftet_afvises(hjem, capsys):
    """Alt over promptens loft klippes TAVST — det skal være en fejl, ikke stilhed."""
    loft = v._qf_loft()
    fyld = "x" * (loft + 10)
    (hjem.parent / "QUICK_FACTS.md").write_text(
        f"# QUICK_FACTS\n\n## Systemer\n\n{fyld}\n", encoding="utf-8"
    )
    assert v.main([]) == 1, "vagten accepterede en fil prompten klipper"
    assert "klippes tavst" in capsys.readouterr().out


def test_loftet_laeses_fra_prompt_contract():
    """Loftet må ikke hardcodes — det skal følge promptens faktiske signatur.

    Hardcodede vi 20.000 her, drev de to fra hinanden den dag nogen hævede
    loftet, og så vogtede vagten en grænse ingen læser.
    """
    from core.services.prompt_contract import _quick_facts_section

    faktisk = _quick_facts_section.__kwdefaults__["max_chars"]
    assert v._qf_loft() == faktisk, (
        f"vagtens loft ({v._qf_loft()}) driver fra promptens ({faktisk})"
    )


def test_qf_reglen_rammer_kun_quick_facts(hjem):
    """MEMORY.md må gerne have en «Commit — …»-sektion; QUICK_FACTS må ikke."""
    hjem.write_text("# Jarvis Memory\n\n## Commit — docs-drift\n\ntekst.\n", encoding="utf-8")
    (hjem.parent / "QUICK_FACTS.md").write_text(
        "# QUICK_FACTS\n\n## Systemer\n\n- x\n", encoding="utf-8"
    )
    assert v.main([]) == 0, "reglen lækkede over i MEMORY.md"
