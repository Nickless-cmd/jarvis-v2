"""Delta-sporet: hvor i kaeden bliver streamen klumpet? (3/10-2026)

Bjoern: «kan du maale om det er modelen der er for hurtigt … streaming burde
glide». Codex maalte 36 bidder over 27s med et hul paa 9,4s, mens desk brugte
90-150 % CPU — og kunne IKKE skille modellen fra serveren fra desk.

Sporet har derfor to maalepunkter i samme tur, og testene her pinner det der
afgoer om maalingen kan bruges:

1. Slukket koster INTET — ellers aendrer maalingen det den maaler.
2. Fordelingen skjuler ikke det store hul (median, p95, max — ikke gennemsnit).
3. Begge punkter er faktisk koblet, hver sit sted i kaeden.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from core.services import delta_trace as dt


@pytest.fixture
def taendt(monkeypatch):
    monkeypatch.setattr(dt, "taendt", lambda: True)
    dt._spor.clear()
    yield
    dt._spor.clear()


@pytest.fixture
def ur(monkeypatch):
    """Et styret ur, saa hullerne er praecise og ikke afhaenger af maskinen."""
    nu = {"t": 100.0}
    monkeypatch.setattr(dt.time, "monotonic", lambda: nu["t"])
    return nu


# ── Slukket skal koste ingenting ──────────────────────────────────────────

def test_slukket_sporer_INTET():
    """Et spor der koster noget naar det er slukket, aendrer det det maaler."""
    dt._spor.clear()
    dt.noter("ind", "run-1", 10)
    assert dt._spor == {}
    assert dt.afslut("run-1") == {}


def test_sentinelen_afgoer_og_tvivl_er_SLUKKET(monkeypatch):
    monkeypatch.setattr(dt.os.path, "exists",
                        lambda _p: (_ for _ in ()).throw(OSError("i stykker")))
    assert dt.taendt() is False


# ── Fordelingen maa ikke udglatte ─────────────────────────────────────────

def test_det_store_hul_overlever_opsummeringen(taendt, ur):
    """Kernen. Codex' 9,4-sekunders ophold ville forsvinde i et gennemsnit:
    35 hurtige bidder plus ét langt ophold giver et gennemsnit der ser fint ud.
    Derfor median, p95 og MAX — og hvor maxet laa."""
    for i in range(20):
        dt.noter("ind", "run-1", 50)
        ur["t"] += 0.010 if i != 9 else 9.4
    ud = dt.afslut("run-1")
    assert ud["ind"]["n"] == 20
    assert ud["ind"]["tegn"] == 1000
    assert ud["ind"]["median_ms"] == 10
    assert ud["ind"]["max_ms"] == 9400, "det store hul er forsvundet"
    assert ud["ind"]["max_ved"] == 10, "vi kan ikke finde hullet igen"


def test_p95_ligger_over_medianen_naar_halen_er_lang(taendt, ur):
    for i in range(100):
        dt.noter("ind", "run-1", 1)
        ur["t"] += 0.010 if i < 94 else 2.0
    ud = dt.afslut("run-1")["ind"]
    assert ud["median_ms"] == 10
    assert ud["p95_ms"] >= 2000, "halen naaede ikke p95"


def test_de_to_punkter_holdes_ADSKILT(taendt, ur):
    """Hele pointen: kan de ikke sammenlignes hver for sig, kan man ikke sige
    hvor klumpen opstod."""
    dt.noter("ind", "run-1", 10); ur["t"] += 0.1
    dt.noter("ind", "run-1", 10); ur["t"] += 0.1
    dt.noter("ud", "run-1", 20); ur["t"] += 3.0
    dt.noter("ud", "run-1", 20)
    ud = dt.afslut("run-1")
    assert ud["ind"]["max_ms"] == 100
    assert ud["ud"]["max_ms"] == 3000
    assert ud["ind"]["tegn"] == 20 and ud["ud"]["tegn"] == 40


def test_to_runs_blandes_ikke(taendt, ur):
    dt.noter("ind", "run-a", 1); ur["t"] += 0.05
    dt.noter("ind", "run-a", 1)
    dt.noter("ind", "run-b", 1); ur["t"] += 5.0
    dt.noter("ind", "run-b", 1)
    a = dt.afslut("run-a")
    assert a["ind"]["max_ms"] == 50
    b = dt.afslut("run-b")
    assert b["ind"]["max_ms"] == 5000


# ── Kanterne ──────────────────────────────────────────────────────────────

def test_EN_delta_giver_ingen_fordeling(taendt, ur):
    """Ét punkt har ingen huller. En «median paa nul huller» ville vaere et
    tal man kunne tro paa."""
    dt.noter("ind", "run-1", 5)
    assert dt.afslut("run-1") == {}


def test_afslut_rydder_sporet(taendt, ur):
    dt.noter("ind", "run-1", 1); ur["t"] += 0.1
    dt.noter("ind", "run-1", 1)
    dt.afslut("run-1")
    assert dt.afslut("run-1") == {}, "sporet blev ikke ryddet"
    assert not any(k[1] == "run-1" for k in dt._spor)


def test_tomt_run_id_sporer_ikke(taendt):
    dt.noter("ind", "", 5)
    assert dt._spor == {}


def test_loftet_forhindrer_at_et_run_aeder_hukommelse(taendt, ur):
    for _ in range(dt._MAKS + 50):
        dt.noter("ind", "run-1", 1)
        ur["t"] += 0.001
    assert len(dt._spor[("ind", "run-1")]) == dt._MAKS


def test_et_run_der_doer_uden_terminal_laekker_ikke_for_evigt(taendt):
    """Uden loftet ville hvert afbrudt run blive staaende i hukommelsen."""
    for i in range(dt._MAKS_RUNS + 5):
        dt.noter("ind", f"run-{i}", 1)
    assert len(dt._spor) <= dt._MAKS_RUNS + 1


def test_sporet_kaster_ALDRIG(taendt, monkeypatch):
    monkeypatch.setattr(dt.time, "monotonic",
                        lambda: (_ for _ in ()).throw(RuntimeError("i stykker")))
    dt.noter("ind", "run-1", 5)   # maa ikke kaste
    monkeypatch.setattr(dt, "_fordeling",
                        lambda _h: (_ for _ in ()).throw(RuntimeError("i stykker")))
    assert dt.afslut("run-1") == {}


# ── Koblingen: begge punkter, hver sit sted ──────────────────────────────

def test_BEGGE_maalepunkter_er_koblet():
    """Et spor med kun ét punkt kan ikke svare paa spoergsmaalet — og det var
    praecis derfor Codex ikke kunne afslutte maalingen."""
    ind = pathlib.Path("core/services/visible_model_adapters.py").read_text()
    ast.parse(ind)
    assert "_dt_noter(delta)" in ind, "punkt «ind» er ikke koblet paa foerste pas"
    assert '_dt.noter("ind"' in ind

    # Og paa de AGENTISKE RUNDER, hvor det meste af teksten kommer fra.
    # Maalt 3/10: to rigtige ture gav NUL «ind»-linjer mod to «ud», fordi
    # sporet kun sad paa foerste pas. Runderne yielder `FollowupDelta` fra en
    # anden fil — instrumenteringen sad paa den vej der producerer MINDST.
    fu = pathlib.Path("core/services/visible_followup_adapters.py").read_text()
    ast.parse(fu)
    assert fu.count("_dt_ind(session_id") >= 2, (
        "de agentiske runder er ikke daekket — og de leverer stoerstedelen "
        "af teksten i en synlig tur")

    ud = pathlib.Path("apps/api/jarvis_api/routes/chat_stream_v2.py").read_text()
    ast.parse(ud)
    assert "_dt_ud(session_id, f)" in ud, "punkt «ud» er ikke koblet"
    assert "_dt.noter('ud'" in ud
    assert "afslut(session_id" in ud, "opsummeringen kaldes aldrig"


def test_udgangen_taeller_kun_TEKST_rammer():
    """Ping og terminale rammer er ikke indhold. Talte de med, ville
    fordelingen se jaevnere ud end den er — netop den udglatning maalingen
    findes for at undgaa."""
    ud = pathlib.Path("apps/api/jarvis_api/routes/chat_stream_v2.py").read_text()
    assert "'text_delta' not in ramme" in ud


def test_noeglen_maa_IKKE_komme_fra_en_contextvar():
    """Den fejl der gjorde den foerste maaling ubrugelig.

    Maalt 3/10-2026, foerste koersel efter udrulning: NUL «ind»-linjer mod én
    «ud». Indgangen noeglede paa `aktivt_run_id()`, som henter fra en
    ContextVar (`run_autonomy_context`) — og gatens globale fallback er,
    ifoelge dens egen kommentar, «tom i jarvis-api, hvor de synlige ture
    koerer». Adapteren koerer i en arbejdstraad, hvor ContextVar'en ikke
    foelger med. Noeglen var tom, og `noter` droppede hver eneste maaling.

    Husets `contextvar_async_generator_gap` og `tool_scope_ctxvar_lost`
    beskriver to tidligere udgaver af samme fejlform. Vagten her er grunden
    til at den ikke skal findes en fjerde gang ved at laese en tom journal.
    """
    ind = pathlib.Path("core/services/visible_model_adapters.py").read_text()
    traeet = ast.parse(ind)

    # AST, ikke strengsoegning: ordet `aktivt_run_id` staar med vilje i
    # docstringen ovenfor som forklaring paa fejlen, og en grep ville faelde
    # sin egen begrundelse. Samme fejl som en taelling af «urgent=True» der
    # ramte dens egne kommentarer, maalt samme dag.
    brugt: list[str] = []
    for n in ast.walk(traeet):
        if isinstance(n, ast.Name):
            brugt.append(n.id)
        elif isinstance(n, ast.Attribute):
            brugt.append(n.attr)
        elif isinstance(n, ast.ImportFrom):
            brugt.extend(a.name for a in n.names)
    assert "aktivt_run_id" not in brugt, (
        "indgangen noegler paa et kontekst-opslag igen — det er tomt i "
        "adapterens arbejdstraad, og saa maaler sporet ingenting")
    assert '_dt.noter("ind", str(session_id' in ind, (
        "noeglen skal vaere adapterens egen session_id-PARAMETER")


def test_followup_sporet_noegler_ogsaa_paa_SESSIONEN():
    """Samme fejl maa ikke kunne snige sig ind ad bagdoeren."""
    fu = pathlib.Path("core/services/visible_followup_adapters.py").read_text()
    brugt: list[str] = []
    for n in ast.walk(ast.parse(fu)):
        if isinstance(n, ast.Name):
            brugt.append(n.id)
        elif isinstance(n, ast.Attribute):
            brugt.append(n.attr)
    assert "aktivt_run_id" not in brugt
    assert '_dt.noter("ind", str(session_id' in fu


def test_sentinel_tjekket_kommer_FOER_arbejdet():
    """Et slukket spor maa ikke koste noget per token."""
    for fil, mark in (
        ("core/services/visible_model_adapters.py", '_dt.noter("ind"'),
        ("apps/api/jarvis_api/routes/chat_stream_v2.py", "_dt.noter('ud'"),
    ):
        kilde = pathlib.Path(fil).read_text()
        assert kilde.index("_dt.taendt()") < kilde.index(mark), fil


# ── Tre-vejs-opdelingen: nettet, os selv, eller planlaeggeren ─────────────
#
# Delta-sporets to punkter viste at klumpen allerede findes naar vi modtager.
# Men det kunne betyde to vidt forskellige ting, og de kraever hver sin
# rettelse: udbyderen sender i stoed, ELLER vores egen traad bliver sultet og
# behandler en ophobet buffer paa én gang. Et tidsstempel per event kan ikke
# skelne dem — der er intet mellem en raa linje og en delta. Tre tal kan.


def test_blokeret_tid_peger_paa_NETTET(taendt, ur):
    """Laa vi og ventede paa readline, kom data langsomt udefra."""
    for _ in range(5):
        dt.noter_laesning("s1", blokeret_s=2.0, behandlet_s=0.001)
        ur["t"] += 2.0
    ud = dt.afslut_laesning("s1")
    assert ud["n"] == 5
    assert ud["blokeret_s"] == 10.0
    assert ud["uforklaret_s"] < 0.1, "tiden er gjort rede for"


def test_uforklaret_tid_peger_paa_PLANLAEGGEREN(taendt, ur):
    """Hverken ventet paa nettet eller brugt CPU — saa var traaden sat af.
    Det er den sultede traad, og den ville LIGNE et stoed udefra."""
    for _ in range(4):
        dt.noter_laesning("s1", blokeret_s=0.001, behandlet_s=0.001)
        ur["t"] += 5.0          # fem sekunders UR-tid per laesning
    ud = dt.afslut_laesning("s1")
    assert ud["blokeret_s"] < 0.1 and ud["behandlet_s"] < 0.1
    assert ud["uforklaret_s"] >= 14.0, "den sultede traad er ikke synlig"


def test_behandlet_tid_peger_paa_OS_SELV(taendt, ur):
    for _ in range(3):
        dt.noter_laesning("s1", blokeret_s=0.0, behandlet_s=3.0)
        ur["t"] += 3.0
    ud = dt.afslut_laesning("s1")
    assert ud["behandlet_s"] == 9.0
    assert ud["uforklaret_s"] < 0.1


def test_det_stoerste_enkelt_ophold_bevares(taendt, ur):
    """Et gennemsnit ville skjule det ene lange ophold — samme grund som
    `max` i delta-fordelingen."""
    for i in range(10):
        dt.noter_laesning("s1", blokeret_s=0.01 if i != 4 else 30.0, behandlet_s=0.0)
        ur["t"] += 0.01 if i != 4 else 30.0
    assert dt.afslut_laesning("s1")["maks_blok_ms"] == 30000


def test_EN_laesning_giver_ingen_opsummering(taendt, ur):
    dt.noter_laesning("s1", blokeret_s=1.0, behandlet_s=0.0)
    assert dt.afslut_laesning("s1") == {}


def test_laesesporet_er_no_op_naar_slukket():
    dt._laes.clear()
    dt.noter_laesning("s1", blokeret_s=1.0, behandlet_s=1.0)
    assert dt._laes == {}
    assert dt.afslut_laesning("s1") == {}


def test_laesesporet_kaster_aldrig(taendt, monkeypatch):
    monkeypatch.setattr(dt.time, "monotonic",
                        lambda: (_ for _ in ()).throw(RuntimeError("i stykker")))
    dt.noter_laesning("s1", blokeret_s=1.0, behandlet_s=0.0)
    assert dt.afslut_laesning("s1") == {}


def test_maale_loekken_er_KOBLET_og_gratis_naar_slukket():
    """Tre ting paa én gang: at maalingen findes, at den kan SKELNE de tre
    slags tid, og at den aldrig koster funktionalitet."""
    sse = pathlib.Path("core/services/visible_model_sse.py").read_text()
    ast.parse(sse)
    assert "def _raa_linjer(" in sse, "linje-kilden er ikke skilt fra parsningen"
    assert "_raa_linjer(response, maale_noegle)" in sse, "parsningen bruger den ikke"
    assert sse.count("# A11 pkt. 1: decode UDEN at rejse.") == 1, (
        "parsningen findes to steder — to sandheder kan drive fra hinanden")
    assert "response.readline()" in sse
    assert "noter_laesning(" in sse, "laese-sporet er ikke koblet"
    # Ikke bare at `thread_time` NAEVNES — den staar to steder, saa en
    # mutation af selve beregningen slap igennem en ren navne-soegning.
    assert "_t.thread_time() - cpu_sidst" in sse, (
        "uden traadens CPU-tid kan vores egen tid ikke skilles fra "
        "planlaeggerens — og saa maaler opdelingen ingenting")
    assert "behandlet_s=behandlet" in sse, "CPU-tiden naar ikke sporet"


def test_en_response_UDEN_readline_falder_tilbage_uden_maaling():
    """Den fejl der faldt syv tests. En fake-response er iterérbar uden at
    have `readline`; en eksplicit laese-loekke gav da NUL events. En maaling
    maa aldrig koste funktionalitet."""
    from core.services.visible_model_sse import _raa_linjer
    linjer = [b"data: {\"a\": 1}\n", b"\n"]
    assert list(_raa_linjer(iter(linjer), "en-noegle")) == linjer
    assert list(_raa_linjer(iter(linjer), "")) == linjer

    sse = pathlib.Path("core/services/visible_model_sse.py").read_text()
    assert 'callable(getattr(response, "readline", None))' in sse, (
        "fallbacken mangler — en iterator uden readline ville give nul events")


def test_sentinel_tjekket_kommer_FOER_maalingen():
    """Et slukket spor maa ikke koste noget per linje."""
    sse = pathlib.Path("core/services/visible_model_sse.py").read_text()
    assert sse.index("_dt_sse.taendt()") < sse.index("while True:")

    fu = pathlib.Path("core/services/visible_followup_adapters.py").read_text()
    assert "maale_noegle=str(session_id" in fu, "noeglen sendes ikke med"

    ud = pathlib.Path("apps/api/jarvis_api/routes/chat_stream_v2.py").read_text()
    assert "afslut_laesning(session_id" in ud, "opsummeringen skrives aldrig"
