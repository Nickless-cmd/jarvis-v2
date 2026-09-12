"""Turens tanker skal staa hvor de blev taenkt — og overleve streamen.

Bjoern 13/9-2026: «tænker/tænkte i chatview forsvinder stadig efter end stream
i stedet for at persiste som tool results».

Grundsandheden bag testen er maalt paa runtime samme dag: af 265 gemte
assistent-beskeder havde 238 praecis ÉN tanke-blok — ogsaa den tur der havde
100 vaerktoejskald — og de tre seneste rene svar-ture havde NUL. Klienten viste
dem live og tabte dem naar serverens version overtog.
"""
from core.services.visible_turn_accumulator import TurnAccumulator


def _tur() -> TurnAccumulator:
    t = TurnAccumulator()
    t.add_thinking("foerst overvejer jeg planen")
    t.note_tool()
    t.add_tools([{"id": "t1", "name": "bash", "input": {}}], [])
    t.add_thinking("nu ser jeg paa resultatet")
    t.note_text()
    t.add_text("Faerdig.")
    return t


def test_hver_tanke_staar_paa_sin_plads():
    typer = [b["type"] for b in _tur().build_blocks("Faerdig.") if b["type"] != "progress"]
    assert typer == ["thinking", "tool_use", "thinking", "text"]


def test_begge_tanker_beholder_deres_eget_indhold():
    tanker = [b["text"] for b in _tur().build_blocks("Faerdig.") if b["type"] == "thinking"]
    assert tanker == ["foerst overvejer jeg planen", "nu ser jeg paa resultatet"]


def test_sammenhaengende_reasoning_bliver_ÉN_tanke_ikke_én_pr_delta():
    """Deltaerne ankommer tegn for tegn. Uden segment-samling ville en tur med
    tusind deltaer give tusind tanke-blokke."""
    t = TurnAccumulator()
    for d in ("jeg ", "over", "vejer"):
        t.add_thinking(d)
    t.note_text()
    t.add_text("svar")
    tanker = [b for b in t.build_blocks("svar") if b["type"] == "thinking"]
    assert len(tanker) == 1
    assert tanker[0]["text"] == "jeg overvejer"


def test_en_tur_uden_tanker_faar_ingen_tanke_blok():
    t = TurnAccumulator()
    t.note_text()
    t.add_text("svar")
    assert not [b for b in t.build_blocks("svar") if b["type"] == "thinking"]


def test_gamle_enkelt_blok_haenges_IKKE_ovenpaa():
    """`_with_thinking_block` lagde ÉN samlet tanke oeverst. Goer den ogsaa det
    nu, staar den foerste tanke to gange."""
    from core.services.visible_runs_outcomes import _with_thinking_block

    class _Run:
        run_id = "visible-test"

    blokke = [{"type": "thinking", "text": "foerst"}, {"type": "text", "text": "svar"}]
    ud = _with_thinking_block(blokke, _Run(), "hele raesonneringen")
    assert [b["type"] for b in ud] == ["thinking", "text"]
    assert ud[0]["text"] == "foerst"


def test_flere_think_markoerer_end_tanker_giver_ikke_tomme_blokke():
    """Foerste udgave loeste dette med en dedupe magen til den 'text' har.
    Mutations-proeven viste at dedupen ALDRIG blev noedvendig: vagten paa
    antallet af segmenter fanger det allerede, og den kunne fjernes uden at én
    eneste test blev roed. Den er vaek igen — og dette er vagten der gjorde
    arbejdet.
    """
    from core.services.visible_turn_blocks import _build_turn_blocks

    ud = _build_turn_blocks(
        text="svar",
        tool_calls=[],
        tool_results=[],
        interleave=["think", "think", "think", "text"],
        text_segments=["svar"],
        thinking_segments=["en enkelt tanke"],
    )
    tanker = [b for b in ud if b["type"] == "thinking"]
    assert len(tanker) == 1, f"{len(tanker)} tanke-blokke ud af én tanke"


# ── Varighed pr. tanke ──────────────────────────────────────────────────────
# Bjoern 13/9-2026: «nu persister tænkte igen bare uden i xx min/sekunder».
# `visible_thinking_trace` maaler HELE turen under ét og kunne derfor kun
# beskrive den ene samlede blok. Med segmenter skal hver tanke baere sin egen.

def _tur_med_ur(tid: list):
    t = TurnAccumulator(ur=lambda: tid[0])
    t.add_thinking("foerste")
    tid[0] += 3.0
    t.add_thinking(" tanke")
    t.note_tool()
    t.add_tools([{"id": "t1", "name": "bash", "input": {}}], [])
    tid[0] += 100.0          # vaerktoejet koerte laenge — det er IKKE taenketid
    t.add_thinking("anden")
    tid[0] += 9.5
    t.add_thinking(" tanke")
    t.note_text()
    t.add_text("Faerdig.")
    return t


def test_hver_tanke_baerer_sin_egen_varighed():
    blokke = _tur_med_ur([100.0]).build_blocks("Faerdig.")
    assert [b.get("seconds") for b in blokke if b["type"] == "thinking"] == [3.0, 9.5]


def test_vaerktoejets_koeretid_taelles_ikke_som_taenketid():
    """Uret loeb 100 s mens bash arbejdede. Maaltes tanken fra turens start til
    dens slut, ville den anden tanke staa som «Tænkte i 109,5 s»."""
    blokke = _tur_med_ur([0.0]).build_blocks("Faerdig.")
    sek = [b.get("seconds") for b in blokke if b["type"] == "thinking"]
    assert max(sek) < 60, f"en tanke fik vaerktoejets ventetid med: {sek}"


def test_en_tanke_uden_maalt_tid_faar_INGEN_tid():
    """Ét enkelt delta giver start == slut. Nul er ikke en maaling."""
    t = TurnAccumulator(ur=lambda: 5.0)
    t.add_thinking("lynhurtig")
    t.note_text()
    t.add_text("svar")
    tanker = [b for b in t.build_blocks("svar") if b["type"] == "thinking"]
    assert "seconds" not in tanker[0]


def test_tiden_foelger_den_RIGTIGE_tanke_naar_en_er_tom():
    """Tomme segmenter filtreres fra. Filtreres teksterne uden tiderne, skrider
    indekset, og tanke nr. 2 arver nr. 1's varighed."""
    from core.services.visible_turn_blocks import _build_turn_blocks

    ud = _build_turn_blocks(
        text="svar", tool_calls=[], tool_results=[],
        interleave=["think", "think", "text"],
        text_segments=["svar"],
        thinking_segments=["   ", "den aegte tanke"],
        thinking_seconds=[1.0, 7.0],
    )
    tanker = [b for b in ud if b["type"] == "thinking"]
    assert len(tanker) == 1
    assert tanker[0]["seconds"] == 7.0, "tanken arvede det tomme segments tid"


def test_akkumulatoren_melder_selv_nul_som_umaalt():
    """Byggeren har sin EGEN vagt mod nul, saa den her kan ikke ses gennem
    build_blocks — mutations-proeven viste at akkumulatorens vagt kunne fjernes
    uden at én test blev roed. De to lag er hver for sig nok, og begge beholdes
    (byggeren kaldes ogsaa direkte udefra), men saa skal de maales hver for sig.
    """
    t = TurnAccumulator(ur=lambda: 42.0)
    t.add_thinking("lynhurtig")
    assert t.thinking_seconds() == [None]
