"""Budget og udeladelses-proveniens for kontekst mellem sessioner — Fase 10.

MAALT 10/9-2026 paa 1.410 prompt-maalinger i produktion:

    2026-09-04  total 44.267 tegn   hukommelses-indeks 3.687
    2026-09-10  total 51.126 tegn   hukommelses-indeks 4.790

Indekset voksede 30 % paa seks dage og havde INTET loft. Det er 9 % af
prompten og fordobles paa nogle uger.

Budgettet er sat rundhaandet (8.000) saa det IKKE bider i dag. Vaerdien ligger
et andet sted: naar det en dag bider, SIGER det det. En tavs afkortning ville
vaere den vaerste udgave — han ville tro han saa hele indekset, og det er
praecis den «tavse nul»-klasse der har kostet mest i dette repo.

Klipning er kun forsvarlig fordi de udeladte emner stadig kan naas: baade
`search_memory` og `read_memory_topic` findes som vaerktoejer. Var de ikke
naabare, ville et budget goere hukommelser USYNLIGE, og saa var kuren vaerre
end sygdommen.
"""
from __future__ import annotations

from core.services.prompt_contract import _budgetter_index, _MEMORY_INDEX_BUDGET


def test_under_budget_roeres_ikke():
    idx = "titel a · slug-a\ntitel b · slug-b"
    assert _budgetter_index(idx) == (idx, 0)


def test_over_budget_klippes_og_taelles():
    linjer = [f"titel-{i:04d} · slug-{i:04d} {'x' * 60}" for i in range(400)]
    idx = "\n".join(linjer)
    assert len(idx) > _MEMORY_INDEX_BUDGET

    ud, udeladt = _budgetter_index(idx)
    assert len(ud) <= _MEMORY_INDEX_BUDGET
    assert udeladt > 0
    assert len(ud.splitlines()) + udeladt == len(linjer), (
        "regnskabet gaar ikke op — tallet i prompten ville vaere forkert")


def test_der_klippes_paa_en_LINJEGRAENSE():
    """En halv linje i indekset er en halv slug: uopnaaelig og forvirrende."""
    linjer = [f"titel-{i:04d} · slug-{i:04d} {'y' * 60}" for i in range(400)]
    ud, _ = _budgetter_index("\n".join(linjer))
    for ln in ud.splitlines():
        assert ln in linjer, f"klippet midt i en linje: {ln!r}"


def test_hovedet_er_byte_stabilt_naar_der_kommer_flere_emner():
    """Sektionen deles af warmer-cron og live-run og ligger i det STABILE
    praefiks. Klippes der fra hovedet, ville hvert nyt emne braekke cachen."""
    grund = [f"titel-{i:04d} · slug-{i:04d} {'z' * 60}" for i in range(400)]
    a, _ = _budgetter_index("\n".join(grund))
    b, _ = _budgetter_index("\n".join(grund + ["nyt-emne · slug-nyt"]))
    assert a == b, "et nyt emne aendrede de beholdte linjer — cachen braekker"


def test_sektionen_fortaeller_hvordan_man_naar_det_udeladte(monkeypatch):
    """Uden vejen tilbage er en afkortning bare et tab."""
    import core.services.prompt_contract as pc

    monkeypatch.setattr(pc, "_MEMORY_INDEX_BUDGET", 200)
    monkeypatch.setattr(
        pc, "_compact_curated_index",
        lambda _raa: "\n".join(f"titel-{i} · slug-{i} {'q' * 40}" for i in range(40)))

    class _Sti(dict):
        def __getitem__(self, k):
            import pathlib
            import tempfile
            d = pathlib.Path(tempfile.mkdtemp())
            (d / "t.md").write_text("x")
            return d

    monkeypatch.setattr(
        "core.identity.workspace_bootstrap.workspace_memory_paths",
        lambda name="default": _Sti())
    monkeypatch.setattr("core.memory.memory_topic_store.read_topic_index",
                        lambda name="default": "raa")

    tekst = pc._curated_memory_index_section("default")
    assert "udeladt" in tekst
    assert "search_memory" in tekst, (
        "afkortningen naevner ikke hvordan det udeladte naas — saa er det bare "
        "et tab")
