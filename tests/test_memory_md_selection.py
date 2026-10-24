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


def test_playbooks_er_i_indekset(tmp_path, monkeypatch):
    """PLAYBOOKS.md SKAL indekseres — ellers er laeringerne reelt glemt.

    HVORFOR (maalt 23/10-2026): samme dag som opskrifter og faelder blev flyttet
    UD af QUICK_FACTS og ind i PLAYBOOKS.md, blev filen oprettet paa workspace-
    roden. `_memory_files()` havde en haardkodet liste af fem filer, og den nye
    fil stod ikke paa den. Maalt i indekset: 1.225 chunks og NUL fra PLAYBOOKS,
    saa `recall("mobil-APK byg og udgiv")` svarede kun med MEMORY-sektioner.

    Det er samme fejl som QUICK_FACTS-loftet, bare med omvendt fortegn: foer var
    indholdet usynligt fordi det blev klippet, nu fordi det aldrig blev
    indekseret. En on-demand-fil der ikke er soegbar er en fil man skal HUSKE
    at laese — og det er praecis den slags hukommelse der svigter.
    """
    ws = tmp_path / "ws-playbooks"
    ws.mkdir(parents=True)
    navne = {f.name for f in memory_search._memory_files(ws)}
    assert "PLAYBOOKS.md" in memory_search._ROOT_MEMORY_FILES, \
        "PLAYBOOKS.md er fjernet fra _ROOT_MEMORY_FILES — saa indekseres den ikke"
    # Filen behoever ikke findes for at staa i listen; men naar den goer, skal
    # den med — ellers er listen og virkeligheden ude af trit.
    (ws / "PLAYBOOKS.md").write_text("# PLAYBOOKS\n\n## En opskrift\n", encoding="utf-8")
    navne = {f.name for f in memory_search._memory_files(ws)}
    assert "PLAYBOOKS.md" in navne, f"PLAYBOOKS.md kom ikke med i listen: {sorted(navne)}"


def test_playbooks_indhold_kan_faktisk_findes(tmp_path, monkeypatch):
    """Ikke nok at filen er i listen — dens INDHOLD skal kunne soeges op."""
    ws = tmp_path / "ws-playbooks2"
    ws.mkdir(parents=True)
    (ws / "PLAYBOOKS.md").write_text(
        "# PLAYBOOKS\n\n## Unik opskrift paa kaellingen\n\n"
        "Byg altid paa brugerens maskine og udgiv via API'et bagefter.\n",
        encoding="utf-8")

    monkeypatch.setattr(memory_search, "_embed_ollama", lambda texts: np.stack([_bow(t) for t in texts]))
    monkeypatch.setattr(memory_search, "_embed_single", lambda text: _bow(text))
    memory_search._MEM_INDEX.clear()
    files = memory_search._memory_files(ws)
    mtimes = {str(f): memory_search._file_mtime(f) for f in files}
    memory_search._build_and_cache_index(files, mtimes, ws)

    hits = memory_search.search_memory("unik opskrift paa kaellingen", limit=5, workspace_dir=ws)
    assert hits, "soegningen gav intet"
    assert any("PLAYBOOKS.md" in h["source"] for h in hits), \
        f"PLAYBOOKS-indhold blev ikke fundet; fik {[h['source'] for h in hits]}"


# --- 24/10-2026: MEMORY.md maa ikke maskeres paa hot path -------------------
# Maalt: `redact()` over 3,01 MB tog 432-487 ms ren CPU ved HVER prompt-bygning,
# og resultatet blev kasseret — `entries` blev kun brugt til `len(entries)` og
# til at afgoere om filen var tom. Det var den stoerste enkeltpost i den spids
# Bjoern maalte ved hver besked. Vagterne her faelder hvis den dyre vej kommer
# tilbage.


def test_memory_md_taelles_uden_at_maskere_hemmeligheder(tmp_path, monkeypatch):
    """MEMORY.md-stien maa ikke kalde redact() — kun taelle linjer."""
    from core.services.prompt_sections import memory_selection as ms

    ws = tmp_path / "ws-count"
    ws.mkdir(parents=True)
    (ws / "MEMORY.md").write_text(
        "# MEMORY\n\n- foerste linje\n- anden linje\n\n## Sektion\n- tredje\n",
        encoding="utf-8")

    kaldt = {"redact": 0, "read_for_prompt": 0}

    def _taeller_redact(text):
        kaldt["redact"] += 1
        return text

    def _taeller_read(path):
        kaldt["read_for_prompt"] += 1
        return path.read_text(encoding="utf-8")

    monkeypatch.setattr("core.services.secret_redaction.redact", _taeller_redact)
    monkeypatch.setattr("core.services.secret_redaction.read_for_prompt", _taeller_read)

    n = ms._workspace_memory_line_count(ws / "MEMORY.md")
    assert n == 3, f"forventede 3 entries (3 ikke-kommentar-linjer), fik {n}"
    assert kaldt["redact"] == 0, (
        f"redact() blev kaldt {kaldt['redact']} gang(e) under taellingen — "
        "det er den dyre vej tilbage"
    )
    assert kaldt["read_for_prompt"] == 0, "read_for_prompt() maskerer; taellingen skal ikke bruge den"


def test_memory_md_sektion_springer_entries_over_naar_sektioner_findes(tmp_path, monkeypatch):
    """Naar sektions-udvaelgelsen leverer linjer, maa entries ALDRIG bygges."""
    from core.services.prompt_sections import memory_selection as ms

    ws = tmp_path / "ws-skip"
    ws.mkdir(parents=True)
    (ws / "MEMORY.md").write_text("# MEMORY\n\n- en linje\n", encoding="utf-8")

    bygget = {"entries": 0}
    aegte = ms._workspace_memory_entries

    def _taeller_entries(path):
        bygget["entries"] += 1
        return aegte(path)

    monkeypatch.setattr(ms, "_workspace_memory_entries", _taeller_entries)
    monkeypatch.setattr(
        "core.services.prompt_sections.memory_md_selection.select_memory_md_sections",
        lambda *a, **k: ["en linje fra sektionen"],
    )
    monkeypatch.setattr(ms, "_filter_answer_changing_memory", lambda msg, lines: lines)

    sel = ms._workspace_memory_section(
        ws / "MEMORY.md",
        label="MEMORY",
        user_message="en linje",
        max_lines=8,
        max_chars=2000,
        workspace_dir=ws,
    )
    assert sel is not None and sel.lines == ["en linje fra sektionen"]
    assert bygget["entries"] == 0, (
        f"_workspace_memory_entries blev kaldt {bygget['entries']} gang(e) selvom "
        "sektions-udvaelgelsen leverede linjer — den dyre vej er tilbage"
    )


def test_memory_md_fallback_bygger_entries_naar_sektioner_svigter(tmp_path, monkeypatch):
    """Fallback'en SKAL stadig have rigtigt indhold — besparelsen maa ikke koste kvalitet."""
    from core.services.prompt_sections import memory_selection as ms

    ws = tmp_path / "ws-fallback"
    ws.mkdir(parents=True)
    (ws / "MEMORY.md").write_text(
        "# MEMORY\n\n- GPU temperatur maalt til 55 grader\n", encoding="utf-8")

    monkeypatch.setattr(
        "core.services.prompt_sections.memory_md_selection.select_memory_md_sections",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(ms, "_filter_answer_changing_memory", lambda msg, lines: lines)

    sel = ms._workspace_memory_section(
        ws / "MEMORY.md",
        label="MEMORY",
        user_message="hvad er GPU temperaturen",
        max_lines=8,
        max_chars=2000,
        workspace_dir=ws,
    )
    assert sel is not None, "fallback gav ingen sektion"
    assert any("GPU" in line for line in sel.lines), f"indholdet forsvandt: {sel.lines}"


# --- 24/10-2026: maskering flyttet fra parse-vej til render-vej ---------------
# `_memory_md_sections` laeste MEMORY.md gennem `read_for_prompt` og maskerede
# hele filen (maalt 434 ms paa 3,10 MB) for at vaelge 3 sektioner paa <=1500
# tegn. Efter flytningen: parse 472 -> 30 ms, kold select 1003 -> 642 ms.
# Vagterne her holder BEGGE sider fast: parse-vejen maa ikke maskere igen, og
# render-vejen SKAL maskere.


def test_parse_vejen_maskerer_ikke_hele_filen(tmp_path, monkeypatch):
    """`_memory_md_sections` maa ikke kalde redact()/read_for_prompt()."""
    from core.services.prompt_sections import memory_md_selection as M

    ws = tmp_path / "ws-parse"
    ws.mkdir(parents=True)
    (ws / "MEMORY.md").write_text(
        "# MEMORY\n\n## Sektion\n- en linje\n", encoding="utf-8")

    kaldt = {"redact": 0, "read_for_prompt": 0}

    def _taeller_redact(text):
        kaldt["redact"] += 1
        return text

    def _taeller_read(path):
        kaldt["read_for_prompt"] += 1
        return path.read_text(encoding="utf-8")

    monkeypatch.setattr("core.services.secret_redaction.redact", _taeller_redact)
    monkeypatch.setattr("core.services.secret_redaction.read_for_prompt", _taeller_read)
    M._IDF_CACHE.clear()

    sektioner = M._memory_md_sections(ws)
    assert sektioner, "parse-vejen skal stadig give sektioner"
    assert kaldt["redact"] == 0, (
        f"redact() blev kaldt {kaldt['redact']} gang(e) i parse-vejen — "
        "det er de 434 ms tilbage"
    )
    assert kaldt["read_for_prompt"] == 0, (
        "read_for_prompt() maskerer hele filen; parse-vejen skal laese raat"
    )


def test_render_vejen_maskerer_sektionen(tmp_path, monkeypatch):
    """SIKKERHED: en hemmelighed i en valgt sektion maa ALDRIG gaa umasket i prompten."""
    from core.services.prompt_sections import memory_md_selection as M

    hemmelighed = "sk-" + "a1b2c3d4e5f6g7h8i9j0k1l2"  # pragma: allowlist secret
    renset = M._render("Noegle", f"min noegle er {hemmelighed} og den virker", max_chars=1500)
    assert hemmelighed not in renset, (
        "hemmeligheden gik UMASKET gennem _render — det er et laek"
    )
    assert renset.startswith("§ Noegle:"), "overskriften skal bevares"


def test_render_udelader_sektionen_naar_maskering_fejler(monkeypatch):
    """Kan der ikke maskeres, maa sektionen IKKE i prompten (fald mod at standse)."""
    from core.services.prompt_sections import memory_md_selection as M

    def _braekker(text):
        raise RuntimeError("redact nede")

    monkeypatch.setattr("core.services.secret_redaction.redact", _braekker)
    assert M._render("Sektion", "noget tekst", max_chars=1500) == "", (
        "ved maskerings-fejl skal sektionen udelades, ikke gaa umasket igennem"
    )


def test_maskering_rammer_kun_det_der_naar_prompten(tmp_path, monkeypatch):
    """Maalt: der maa hoegst maskeres det der faktisk kan naa prompten."""
    from core.services.prompt_sections import memory_md_selection as M

    maalt = {"tegn": 0}
    aegte = M._mask

    def _taeller(text):
        maalt["tegn"] += len(text or "")
        return aegte(text)

    monkeypatch.setattr(M, "_mask", _taeller)
    linje = M._render("Stor", "x" * 5000, max_chars=1500)
    assert maalt["tegn"] <= 1500, (
        f"der blev maskeret {maalt['tegn']} tegn for en linje paa 1500 — "
        "maskeringen er tilbage paa hele filen"
    )
    assert len(linje) <= 1500


def test_focused_excerpt_koeres_kun_paa_de_valgte(tmp_path, monkeypatch):
    """24/10-2026: excerpten blev kørt på HVER kandidat med dækning > 0 —
    målt 917 gange pr. kald, hvoraf kun `limit` (12) forlod funktionen.
    Excerpten påvirker kun `text`-feltet, aldrig `score`, så den skal køre
    efter sorteringen. Vagten tæller kaldene: flyttes den tilbage i loopet,
    bliver testen rød, og de ~160 ms pr. prompt-byg er tabt igen.
    """
    # VARIEREDE sektioner: ord der staar i ALLE sektioner faar df=1 og dermed
    # IDF-vaegt ~0, saa de giver nul daekning. Kun de faa GPU-sektioner maa
    # rammes af forespoergslen.
    emner = ["Kontrakter", "Postgres", "Svg-filer", "Togtabeller", "Vejret",
             "Bogholderi", "Grafik", "Netvaerk", "Lydkort", "Tastatur"]
    dele = []
    for i in range(240):
        e = emner[i % len(emner)]
        if i % 20 == 0:
            dele.append(f"## GPU emne {i}\n- GPU og hardware og ollama embeddings nummer {i}.")
        else:
            dele.append(f"## {e} {i}\n- {e} punkt nummer {i} uden de saerlige ord.")
    (tmp_path / "MEMORY.md").write_text(
        "# MEMORY\n\n" + "\n\n".join(dele), encoding="utf-8"
    )

    kald = {"n": 0}
    aegte = mms._focused_excerpt

    def _taeller(msg, text, **kw):
        kald["n"] += 1
        return aegte(msg, text, **kw)

    monkeypatch.setattr(mms, "_focused_excerpt", _taeller)
    out = mms._lexical_candidates(
        "GPU hardware ollama embeddings", tmp_path, limit=12
    )

    assert len(out) == 12, "udvalget skal stadig være limit"
    assert all(h.get("text") for h in out), "de valgte skal have en excerpt"
    assert "_raw" not in out[0], "_raw er intern og maa ikke laekke ud"
    assert kald["n"] <= 12, (
        f"_focused_excerpt blev koert {kald['n']} gange for 12 valgte — "
        "den er tilbage i kandidat-loopet"
    )
