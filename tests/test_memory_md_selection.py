"""Task 2 (memory repair 2026-09-04): MEMORY.md is selected by SECTION, not "last 4 lines"."""
from __future__ import annotations

import os
import time
from pathlib import Path

import numpy as np
import pytest

from core.services import memory_search
from core.services.prompt_sections import memory_md_selection as mms
from core.services.prompt_sections.memory_md_selection import select_memory_md_sections

MEMORY_MD = """# MEMORY

## Hardware
- ChiefOne er min fysiske vært, Gigabyte B650, Ubuntu 24.04.
- GPU 1070 i containeren, ollama embeddings.

## pfSense nøgle
- pfsense api-nøglen blev flyttet fra kode til .env via env_override.
- pfsense nøgle besluttet: python-dotenv i requirements.

## Wait-state ads
- Idlen bedste-case €100/md, Sponsoric overvej.
- Wait-state ads dækker ikke API-regningen.
"""


def _bow(text: str) -> np.ndarray:
    """Deterministic bag-of-words hashing embedder (768-dim) for tests."""
    v = np.zeros(768, dtype=np.float32)
    for w in text.lower().replace("-", " ").split():
        w = w.strip(".,:;()[]«»\"'")
        if len(w) < 3:
            continue
        v[hash(w) % 768] += 1.0
    n = np.linalg.norm(v)
    return v / n if n else v


@pytest.fixture
def ws(tmp_path, monkeypatch) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "MEMORY.md").write_text(MEMORY_MD, encoding="utf-8")
    monkeypatch.setattr(memory_search, "_embed_ollama", lambda texts: np.stack([_bow(t) for t in texts]))
    monkeypatch.setattr(memory_search, "_embed_single", lambda text: _bow(text))
    memory_search._MEM_INDEX.clear()
    files = memory_search._memory_files(ws)
    mtimes = {str(f): memory_search._file_mtime(f) for f in files}
    memory_search._build_and_cache_index(files, mtimes, ws)  # synchronous, deterministic
    return ws


def test_selects_matching_section_with_heading(ws):
    lines = select_memory_md_sections(
        "hvor ligger pfsense api nøglen og hvad besluttede vi?", workspace_dir=ws,
    )
    assert lines, "expected at least one section"
    assert lines[0].startswith("§ pfSense nøgle:")
    assert "env_override" in lines[0]


def test_sections_are_deduped_by_heading_and_capped(ws):
    lines = select_memory_md_sections(
        "pfsense nøgle env_override python-dotenv", workspace_dir=ws, max_sections=3, max_chars=120,
    )
    headings = [ln.split(":")[0] for ln in lines]
    assert len(headings) == len(set(headings))
    assert sum(len(ln) for ln in lines) <= 120 or len(lines) == 1


def test_short_message_yields_nothing(ws):
    assert select_memory_md_sections("hej", workspace_dir=ws) == []


def test_search_memory_source_filter(ws):
    (ws / "USER.md").write_text("## Preferences\n- pfsense pfsense pfsense nøgle sprog dansk\n", encoding="utf-8")
    files = memory_search._memory_files(ws)
    mtimes = {str(f): memory_search._file_mtime(f) for f in files}
    memory_search._MEM_INDEX.clear()
    memory_search._build_and_cache_index(files, mtimes, ws)
    hits = memory_search.search_memory("pfsense nøgle", limit=5, sources=["MEMORY.md"], workspace_dir=ws)
    assert hits
    assert all(h["source"] == "MEMORY.md" for h in hits)


def test_selector_promotes_exact_match_over_semantic_noise(monkeypatch, tmp_path):
    def fake_search_memory(*args, **kwargs):
        return [
            {
                "section": "visible_output_text guard",
                "text": "Hukommelsen blev amputeret af tomme svar i agentiske runder.",
                "score": 0.95,
            },
            {
                "section": "Hardware",
                "text": "GPU-maskine LXC 107 kører Ollama med GTX 1070 passthrough.",
                "score": 0.40,
            },
        ]

    monkeypatch.setattr(memory_search, "search_memory", fake_search_memory)

    lines = select_memory_md_sections(
        "hvilken GPU har jeg og hvad bruges den til?",
        workspace_dir=tmp_path,
        max_sections=1,
    )

    assert lines == ["§ Hardware: GPU-maskine LXC 107 kører Ollama med GTX 1070 passthrough."]


def test_selector_falls_back_to_lexical_memory_scan(monkeypatch, tmp_path):
    (tmp_path / "MEMORY.md").write_text(
        "# MEMORY\n\n"
        "## Runtime støj\n"
        "- Tomme svar i agentiske runder.\n\n"
        "## Hardware\n"
        "- GPU-maskine LXC 107 kører Ollama med GTX 1070 passthrough.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        memory_search,
        "search_memory",
        lambda *args, **kwargs: [
            {
                "section": "Runtime støj",
                "text": "Tomme svar i agentiske runder.",
                "score": 0.90,
            }
        ],
    )

    lines = select_memory_md_sections(
        "hvilken GPU har jeg og hvad bruges den til?",
        workspace_dir=tmp_path,
        max_sections=1,
    )

    assert lines == ["§ Hardware: GPU-maskine LXC 107 kører Ollama med GTX 1070 passthrough."]


def test_alle_curated_filer_indekseres_uanset_navn_og_mtime(tmp_path):
    """Varig viden har ingen kvote (18/10-2026): ALLE curated-filer skal med.

    Maalt i drift foer fixet: 115 filer i `memory/curated`, men kun 32
    indekseret — 83 varige vidensfiler var ikke soegbare. Testen her laaser at
    hele mappen kommer med, ogsaa naar der er flere end den gamle kvote paa 30,
    og at sorteringen stadig er mtime-baseret: navnesortering droppede tavst
    curated-memory.md fordi "c" sorterer foer "sansernes-arkiv-…".
    """
    ws = tmp_path / "ws2"
    (ws / "memory" / "curated").mkdir(parents=True)
    d = ws / "memory" / "curated"
    # 31 files named so that "curated-memory.md" sorts FIRST alphabetically …
    old = d / "curated-memory.md"
    old.write_text("# Curated\n- newest content\n", encoding="utf-8")
    now = time.time()
    for i in range(31):
        f = d / f"sansernes-arkiv-{i:02d}.md"
        f.write_text(f"# {i}\n- x\n", encoding="utf-8")
        os.utime(f, (now - 10_000 + i, now - 10_000 + i))  # all OLDER than curated-memory.md
    os.utime(old, (now, now))
    files = memory_search._memory_files(ws)
    names = {f.name for f in files}
    assert "curated-memory.md" in names, "newest file must survive"
    # Ingen kvote paa varig viden: alle 32 skal med — ikke 30.
    assert len([f for f in files if f.parent == d]) == 32


def test_kvoten_gaelder_daily_men_ikke_curated(tmp_path):
    """Den nye kontrakt (18/10-2026): varig viden ubegraenset, rullende log loftet.

    Dette er selve skellet. Gaar det tabt — fx ved at nogen saetter en kvote
    tilbage paa curated — falder varige noter tavst ud af soegningen igen.
    """
    ws = tmp_path / "ws-skel"
    for sub in ("curated", "daily"):
        (ws / "memory" / sub).mkdir(parents=True)
    now = time.time()
    for sub in ("curated", "daily"):
        for i in range(45):
            f = ws / "memory" / sub / f"f-{i:02d}.md"
            f.write_text(f"# {i}\n- x\n", encoding="utf-8")
            os.utime(f, (now - i, now - i))
    files = memory_search._memory_files(ws)
    cur = [f for f in files if f.parent.name == "curated"]
    dai = [f for f in files if f.parent.name == "daily"]
    assert len(cur) == 45, f"alle curated-filer skal med, fik {len(cur)}"
    assert len(dai) == 30, f"daily skal have loft paa 30, fik {len(dai)}"


# ── IDF-vaegtet daekning + cachet sektions-parse (5/10-2026) ────────────────
#
# `_lexical_coverage` vaegter 0,65 af rangeringen — mere end selve soegningen —
# og taellede BINAER ord-tilstedevaerelse. Maalt paa Bjoerns 928 sektioner:
# «ligger» i 130 af dem (idf 1,97), «pfsense» i 11 (idf 4,44), lige vaegt.
# Konsekvensen var bunker: 9 sektioner lige paa 0,667, 148 paa 0,333.


@pytest.fixture(autouse=True)
def _ryd_idf_cache():
    """Modul-cachen maa ikke laekke mellem tests."""
    mms._IDF_CACHE.clear()
    yield
    mms._IDF_CACHE.clear()


#: Bunken opstaar fordi flere sektioner rammer FORSKELLIGE par af
#: forespoergslens ord og derfor faar samme uvaegtede andel. Det var moensteret
#: i hans fil: ni sektioner lige paa 0,667 for «hvor ligger pfsense-nøglen».
#:   · 24 fyld rammer kun «ligger» (meget almindeligt)
#:   · 5 rammer «ligger» + «nøglen»  → 2 af 3
#:   · 1 rammer «pfsense» + «nøglen» → 2 af 3, men med de SJAELDNE ord
_KORPUS = (
    [(f"Fyld {i}", "det ligger et sted her") for i in range(24)]
    + [(f"Nøglen i fyld {i}", "nøglen ligger et sted") for i in range(5)]
    + [("pfsense-nøgle → .env", "pfsense_api_key og nøglen flyttet hertil")]
)
_RIGTIG = len(_KORPUS) - 1


def test_et_sjaeldent_ord_vejer_mere_end_et_almindeligt():
    """Hele fejlen: «ligger» (130 af 928) taellede som «pfsense» (11 af 928)."""
    v = mms._idf_vaegte(_KORPUS)
    assert v["pfsense"] > v["ligger"], "det sjaeldne ord skal veje mest"


def test_vaegtene_bryder_bunken():
    """Uvaegtet staar alle 30 lige, fordi de alle rammer «ligger»."""
    q = "hvor ligger pfsense-nøglen"
    uvaegtet = [mms._lexical_coverage(q, h, t) for h, t in _KORPUS]
    assert uvaegtet.count(max(uvaegtet)) > 1, "forudsaetningen: uvaegtet er der en bunke"

    v = mms._idf_vaegte(_KORPUS)
    vaegtet = [mms._lexical_coverage(q, h, t, vaegte=v) for h, t in _KORPUS]
    assert vaegtet.count(max(vaegtet)) == 1, "vaegtet skal der staa ÉN paa toppen"
    assert vaegtet.index(max(vaegtet)) == _RIGTIG, "og det skal vaere pfsense-sektionen"


def test_uden_vaegte_er_adfaerden_UAENDRET():
    """`_focused_excerpt` scorer enkelte saetninger og har intet korpus."""
    q = "hvor ligger pfsense-nøglen"
    assert mms._lexical_coverage(q, "", "pfsense ligger her") == \
           mms._lexical_coverage(q, "", "pfsense ligger her", vaegte=None)
    assert mms._lexical_coverage(q, "", "pfsense ligger her", vaegte={}) == \
           mms._lexical_coverage(q, "", "pfsense ligger her")


def test_for_lille_korpus_giver_INGEN_vaegte():
    """Under 20 sektioner er en df-taelling stoej."""
    assert mms._idf_vaegte(_KORPUS[:5]) == {}
    assert mms._idf_vaegte([]) == {}


def test_et_ukendt_ord_aendrer_ikke_RAEKKEFOELGEN():
    """En slaafejl faar hoejeste vaegt og kan aldrig rammes — den skalerer alle
    kandidater ens ned. Niveauet falder, rangeringen ikke."""
    v = mms._idf_vaegte(_KORPUS)
    uden = [mms._lexical_coverage("ligger pfsense", h, t, vaegte=v) for h, t in _KORPUS]
    med = [mms._lexical_coverage("ligger pfsense zzqqxx", h, t, vaegte=v) for h, t in _KORPUS]
    assert max(med) < max(uden), "det ukendte ord skal traekke niveauet ned"
    assert uden.index(max(uden)) == med.index(max(med)), "men ikke aendre hvem der vinder"


def test_sektionerne_parses_kun_EN_gang_pr_filversion(tmp_path, monkeypatch):
    """Den gamle kode laeste og parsede 980 KB ved HVERT kald — det var
    halvdelen af de 283 ms. Maalt efter: 134 ms."""
    (tmp_path / "MEMORY.md").write_text(
        "# T\n" + "".join(f"\n## Sektion {i}\n\nkrop {i} med ord\n" for i in range(30)),
        encoding="utf-8")
    kald = {"n": 0}
    rigtig = mms._memory_md_sections

    def _taeller(ws):
        kald["n"] += 1
        return rigtig(ws)
    monkeypatch.setattr(mms, "_memory_md_sections", _taeller)

    for _ in range(4):
        mms._sektioner_og_vaegte(tmp_path)
    assert kald["n"] == 1, f"parsede {kald['n']} gange i stedet for én"


def test_en_aendret_fil_invaliderer_cachen(tmp_path):
    import os
    import time
    sti = tmp_path / "MEMORY.md"
    sti.write_text("# T\n" + "".join(f"\n## A{i}\n\nkrop {i}\n" for i in range(30)), encoding="utf-8")
    foer, _ = mms._sektioner_og_vaegte(tmp_path)
    time.sleep(0.01)
    sti.write_text("# T\n" + "".join(f"\n## B{i}\n\nny krop {i}\n" for i in range(30)), encoding="utf-8")
    os.utime(sti, (time.time() + 1, time.time() + 1))
    efter, _ = mms._sektioner_og_vaegte(tmp_path)
    assert [h for h, _ in foer] != [h for h, _ in efter], "cachen leverede den gamle fil"


def test_terms_er_cachet(tmp_path):
    """`_terms` skal ramme cachen — den SAMME forespoergsel blev tokeniseret
    13.830 gange pr. assembly (maalt 12/10-2026: 934 ms ren CPU, 71% spild).

    Uden `lru_cache` paa `_terms` fejler denne: hvert kald ville vaere et miss.
    """
    mms._terms.cache_clear()
    for _ in range(50):
        mms._terms("hvor ligger pfsense api-noeglen")
    info = mms._terms.cache_info()
    assert info.misses == 1, f"forventede 1 miss, fik {info.misses}"
    assert info.hits == 49, f"forventede 49 hits, fik {info.hits}"


def test_terms_resultat_kan_ikke_muteres(tmp_path):
    """Cachet resultat skal vaere immutabelt — et delt muterbart saet ville
    lade én kalder korrumpere naeste kalders tokenisering."""
    mms._terms.cache_clear()
    t = mms._terms("pfsense noegle env_override")
    assert isinstance(t, frozenset)
    with pytest.raises(AttributeError):
        t.add("snik")  # type: ignore[attr-defined]


# ── Kvote-skel + pin-mekanisme (18/10-2026) ────────────────────────────────
#
# Maalt 18/10-2026: kvoten var 30 og gjaldt BAADE `memory/curated` (115 filer)
# og `memory/daily` (179 filer). Kun 32 curated-filer var indekseret — 83
# varige vidensfiler var tavst usoegbare, uden fejl og uden advarsel.
# Fixet: varig viden har INGEN kvote; den rullende log har et loft
# (`_DAILY_FILE_LIMIT`). Pin er et TILLAEG ovenpaa kvoten, saa en daglig fil
# kan garanteres indekseret uanset hvor mange nyere der er kommet til.


def test_pinnet_fil_overlever_et_fyldt_mtime_vindue(tmp_path):
    """Kernen i pin: 40 NYERE filer maa ikke skubbe den pinnede ud af daily."""
    ws = tmp_path / "ws-pin"
    d = ws / "memory" / "daily"
    d.mkdir(parents=True)
    now = time.time()
    pinned = d / "pin-varig-viden.md"
    pinned.write_text("# Varig\n- regel der skal blive\n", encoding="utf-8")
    os.utime(pinned, (now - 100_000, now - 100_000))  # AELDST af alle
    for i in range(40):
        f = d / f"ny-{i:02d}.md"
        f.write_text(f"# {i}\n- x\n", encoding="utf-8")
        os.utime(f, (now - i, now - i))  # alle NYERE end den pinnede

    names = {f.name for f in memory_search._memory_files(ws)}
    assert "pin-varig-viden.md" in names, "pinnet fil skal overleve uanset mtime"
    # ... og den fortraenger ikke nogen: kvoten giver stadig praecis 30.
    assert len([f for f in memory_search._memory_files(ws) if f.parent == d]) == 31


def test_pin_er_et_tillaeg_ikke_en_omfordeling(tmp_path):
    """Uden pin: 30. Med pin: 31. Pin maa ikke stjaele en plads fra vinduet."""
    ws = tmp_path / "ws-pin2"
    d = ws / "memory" / "daily"
    d.mkdir(parents=True)
    now = time.time()
    for i in range(35):
        f = d / f"f-{i:02d}.md"
        f.write_text(f"# {i}\n- x\n", encoding="utf-8")
        os.utime(f, (now - i, now - i))
    uden = [f for f in memory_search._memory_files(ws) if f.parent == d]
    assert len(uden) == 30

    pinned = d / "pin-ekstra.md"
    pinned.write_text("# Pin\n- y\n", encoding="utf-8")
    os.utime(pinned, (now - 999, now - 999))
    med = [f for f in memory_search._memory_files(ws) if f.parent == d]
    assert len(med) == 31
    assert {f.name for f in uden} <= {f.name for f in med}, "ingen fil maa forsvinde"


def test_pin_gaelder_ogsaa_memory_daily(tmp_path):
    """Kvoten er delt mellem de to mapper — pin skal virke i begge."""
    ws = tmp_path / "ws-pin3"
    for sub in ("curated", "daily"):
        (ws / "memory" / sub).mkdir(parents=True)
    now = time.time()
    p = ws / "memory" / "daily" / "pin-daglig.md"
    p.write_text("# Daglig\n- vigtig\n", encoding="utf-8")
    os.utime(p, (now - 100_000, now - 100_000))
    for i in range(35):
        f = ws / "memory" / "daily" / f"d-{i:02d}.md"
        f.write_text(f"# {i}\n- x\n", encoding="utf-8")
        os.utime(f, (now - i, now - i))
    names = {f.name for f in memory_search._memory_files(ws)}
    assert "pin-daglig.md" in names


def test_pinnet_fil_bliver_faktisk_soegbar(tmp_path, monkeypatch):
    """Ikke nok at filen er i listen — den skal ogsaa kunne findes."""
    ws = tmp_path / "ws-pin4"
    d = ws / "memory" / "curated"
    d.mkdir(parents=True)
    now = time.time()
    pinned = d / "pin-unik-regel.md"
    pinned.write_text(
        "# Unik\n\n## Klammetricket\n\npgrep matcher sin egen kommandolinje og draeber sit eget kald.\n",
        encoding="utf-8")
    os.utime(pinned, (now - 100_000, now - 100_000))
    for i in range(40):
        f = d / f"stoej-{i:02d}.md"
        f.write_text(f"# Stoej {i}\n\n- irrelevant fyld nummer {i}\n", encoding="utf-8")
        os.utime(f, (now - i, now - i))

    monkeypatch.setattr(memory_search, "_embed_ollama", lambda texts: np.stack([_bow(t) for t in texts]))
    monkeypatch.setattr(memory_search, "_embed_single", lambda text: _bow(text))
    memory_search._MEM_INDEX.clear()
    files = memory_search._memory_files(ws)
    mtimes = {str(f): memory_search._file_mtime(f) for f in files}
    memory_search._build_and_cache_index(files, mtimes, ws)

    hits = memory_search.search_memory("pgrep draeber sit eget kald", limit=5, workspace_dir=ws)
    assert hits, "soegningen gav intet"
    assert any("pin-unik-regel.md" in h["source"] for h in hits), \
        f"pinnet fil blev ikke fundet; fik {[h['source'] for h in hits]}"
