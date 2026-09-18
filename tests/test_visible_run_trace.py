"""Sporet gennem en kørsel — og at udskillelsen ikke brækkede noget.

Testene her handler om det en UDSKILLELSE kan ødelægge, ikke om det funktionen
gjorde i forvejen: at imports stadig peger rigtigt, at tilstanden kun findes ét
sted, og at kaldet blev liggende hvor det skal fyre.
"""
from __future__ import annotations

from core.services import visible_run_trace as vrt


class _Run:
    run_id = "visible-abc"
    lane = "visible"
    provider = "deepseek"
    model = "deepseek-v4-flash"


# ───────────────────────────────────────────────── bagudkompatibilitet

def test_alt_er_gen_eksporteret_fra_visible_runs():
    """Målt før flytningen: getteren har tre eksterne kaldere,
    trace-opdateringen seks, runde-publiceringen fire — heraf tests der griber
    direkte i `visible_runs`-navnerummet. En udskillelse der brækker dem, er
    ikke en udskillelse men en flytning med fejl."""
    from core.services import visible_runs as vr
    for navn in ("get_last_visible_execution_trace", "_start_visible_execution_trace",
                 "_update_visible_execution_trace", "_set_last_visible_execution_trace",
                 "_visible_trace_payload", "_publish_agentic_round_start"):
        assert hasattr(vr, navn), f"{navn} kan ikke naas fra visible_runs laengere"


def test_gen_eksporten_peger_paa_SAMME_funktion():
    """Ikke bare et navn der findes — det SAMME objekt. To kopier ville betyde
    to tilstande, og sporet ville blive skrevet ét sted og læst et andet."""
    from core.services import visible_runs as vr
    assert vr._publish_agentic_round_start is vrt._publish_agentic_round_start
    assert vr.get_last_visible_execution_trace is vrt.get_last_visible_execution_trace


def test_tilstanden_findes_KUN_ét_sted():
    """CLAUDE.md: «No dual truth». Første forsøg efterlod
    `_LAST_VISIBLE_EXECUTION_TRACE` begge steder — den slags viser sig som et
    spor der opdateres ét sted og læses et andet."""
    import pathlib
    kilde = pathlib.Path("core/services/visible_runs.py").read_text()
    assert "_LAST_VISIBLE_EXECUTION_TRACE" not in kilde


def test_gen_eksport_blokken_til_de_ANDRE_udskillelser_er_intakt():
    """Første forsøg skar blokken ud paa LINJENUMRE og tog filens sidste
    gen-eksport-blok med. 22 tests gik roede paa
    «has no attribute '_track_runtime_candidates'». Vagten her ville have
    fanget det med det samme."""
    from core.services import visible_runs as vr
    for navn in ("_track_runtime_candidates", "_track_step_failed",
                 "_persist_visible_run_outcome", "resolve_pending_approval"):
        assert hasattr(vr, navn), f"{navn} forsvandt med udskillelsen"


# ───────────────────────────────────────────────────────── selve sporet

def test_et_spor_starter_og_kan_laeses_tilbage(monkeypatch):
    monkeypatch.setattr(vrt.event_bus, "publish", lambda *a, **k: None)
    vrt._start_visible_execution_trace(_Run())
    spor = vrt.get_last_visible_execution_trace() or {}
    assert spor["run_id"] == "visible-abc"
    assert spor["final_status"] == "running"


def test_en_opdatering_FLETTER_frem_for_at_erstatte(monkeypatch):
    """Et spor der blev overskrevet ville tabe alt det tidligere trin skrev."""
    monkeypatch.setattr(vrt.event_bus, "publish", lambda *a, **k: None)
    vrt._start_visible_execution_trace(_Run())
    vrt._update_visible_execution_trace(_Run(), {"invoke_status": "invoked"})
    spor = vrt.get_last_visible_execution_trace() or {}
    assert spor["invoke_status"] == "invoked"
    assert spor["final_status"] == "running", "de oevrige felter forsvandt"


def test_getteren_giver_en_KOPI(monkeypatch):
    """Ellers kunne en kalder ændre husets spor ved et uheld."""
    monkeypatch.setattr(vrt.event_bus, "publish", lambda *a, **k: None)
    vrt._start_visible_execution_trace(_Run())
    a = vrt.get_last_visible_execution_trace() or {}
    a["final_status"] = "roert udefra"
    b = vrt.get_last_visible_execution_trace() or {}
    assert b["final_status"] == "running"


def test_hver_opdatering_UDSENDES(monkeypatch):
    """Sporet er til for at kunne ses. Et spor ingen faar besked om, er en
    variabel."""
    sendt: list[str] = []
    monkeypatch.setattr(vrt.event_bus, "publish", lambda navn, *a, **k: sendt.append(navn))
    vrt._start_visible_execution_trace(_Run())
    assert sendt == ["runtime.visible_run_execution_trace"]


# ──────────────────────────────────────── kaldet blev hvor det skal fyre

def test_runde_publiceringen_kaldes_stadig_fra_loekken():
    """Kun DEFINITIONEN flyttede. Fyrede kaldet et andet sted, ville
    runde-kæderne i den kausale graf miste deres forælder — og
    `test_process_lifecycle` kraever desuden at nedluknings-vagten staar foer
    det."""
    import ast
    import pathlib
    træ = ast.parse(pathlib.Path("core/services/visible_runs.py").read_text())
    # BAADE `FunctionDef` og `AsyncFunctionDef`: `_stream_visible_run` er en
    # generator-funktion, og en vagt der kun kender den ene form finder ingenting
    # og ser ud som om kaldet er væk.
    fn = next((n for n in ast.walk(træ)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               and n.name == "_stream_visible_run"), None)
    assert fn is not None, "_stream_visible_run er flyttet"
    kaldt = {getattr(k.func, "id", "") for k in ast.walk(fn) if isinstance(k, ast.Call)}
    assert "_publish_agentic_round_start" in kaldt


# ─────────────────────────────────────── runde-etiketten (14/9-2026)
#
# «Rettede fejl i login» — hvad runden UDRETTEDE. Den mekaniske linje i
# klienterne siger hvad der SKETE; de to står sammen, etiketten først.
#
# CC bærer sin som `pendingToolUseSummary` og leverer den NÆSTE tur. Vi kan
# levere i samme runde, fordi streamen allerede bærer top-level runde-events —
# men kun hvis kaldet ikke får runden til at vente. Derfor en tråd.

def test_runden_venter_ALDRIG_paa_etiketten(monkeypatch):
    """Det er hele betingelsen for at levere i samme runde i stedet for næste.
    Blokerede den, ville vi have byttet en langsommere tur for en pænere linje.
    """
    import threading
    laas = threading.Event()
    monkeypatch.setattr(vrt, "_etiket", lambda *a, **k: (laas.wait(5), "sent")[1])
    monkeypatch.setattr(vrt.event_bus, "publish", lambda *a, **k: None)
    t = vrt.udsend_runde_etiket(run_id="visible-a", round_num=1,
                                vaerktoejer=[{"name": "bash", "input": {}}])
    assert t is not None and t.is_alive(), "kaldet blev kørt synkront"
    laas.set()
    t.join(timeout=5)


def test_etiketten_UDSENDES_med_sine_tool_ids(monkeypatch):
    """`preceding_tool_use_ids` i CC. Uden dem hæfter etiketten sig på en PLADS
    i strømmen i stedet for på sit batch."""
    sendt: list[tuple[str, dict]] = []
    monkeypatch.setattr(vrt, "_etiket", lambda *a, **k: "Rettede fejl i login")
    monkeypatch.setattr(vrt.event_bus, "publish",
                        lambda navn, nyttelast=None, **k: sendt.append((navn, nyttelast or {})))
    t = vrt.udsend_runde_etiket(run_id="visible-a", round_num=2,
                                vaerktoejer=[{"name": "bash", "input": {}, "id": "t1"}],
                                hensigt="ret den fejl")
    t.join(timeout=5)
    assert sendt, "intet event"
    navn, p = sendt[0]
    assert navn == "runtime.tool_round_label"
    assert p["etiket"] == "Rettede fejl i login"
    assert p["tool_use_ids"] == ["t1"]
    assert p["run_id"] == "visible-a" and p["round"] == 2


def test_en_TOM_etiket_udsendes_ikke(monkeypatch):
    """En tom overskrift ville få klienten til at rydde plads til ingenting."""
    sendt: list = []
    monkeypatch.setattr(vrt, "_etiket", lambda *a, **k: "")
    monkeypatch.setattr(vrt.event_bus, "publish", lambda *a, **k: sendt.append(1))
    t = vrt.udsend_runde_etiket(run_id="a", round_num=1,
                                vaerktoejer=[{"name": "bash", "input": {}}])
    t.join(timeout=5)
    assert sendt == []


def test_INGEN_vaerktoejer_starter_slet_ingen_traad(monkeypatch):
    """En runde uden værktøjer har intet at opsummere. En tråd pr. tekst-runde
    ville være ren spild."""
    monkeypatch.setattr(vrt, "_etiket", lambda *a, **k: "x")
    assert vrt.udsend_runde_etiket(run_id="a", round_num=1, vaerktoejer=[]) is None


def test_en_FEJL_i_etiketten_vaelter_ikke_noget(monkeypatch):
    """En etiket er en overskrift. En tur må aldrig vælte fordi overskriften
    ikke kunne skrives — CC's egen kilde logger og lader kaldet passere.

    Målt med en mutation: første udgave af testen ventede blot på `join()` og
    kaldte det bevis. Det er det ikke — en exception i en tråd når ALDRIG ud
    gennem `join()`, så testen bestod også da fejlen blev kastet videre. Den
    lytter nu på `threading.excepthook`, som er det eneste sted en ubehandlet
    tråd-exception viser sig.
    """
    import threading
    fanget: list[object] = []
    monkeypatch.setattr(threading, "excepthook", lambda a: fanget.append(a))
    monkeypatch.setattr(vrt, "_etiket",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    t = vrt.udsend_runde_etiket(run_id="a", round_num=1,
                                vaerktoejer=[{"name": "bash", "input": {}}])
    t.join(timeout=5)
    assert fanget == [], "fejlen slap ubehandlet ud af traaden"


def test_traaden_er_DAEMON(monkeypatch):
    """Ellers kunne en langsom etiket holde processen i live ved nedlukning —
    og huset har lige brugt en dag på kørsler der ikke ville dø."""
    monkeypatch.setattr(vrt, "_etiket", lambda *a, **k: "x")
    monkeypatch.setattr(vrt.event_bus, "publish", lambda *a, **k: None)
    t = vrt.udsend_runde_etiket(run_id="a", round_num=1,
                                vaerktoejer=[{"name": "bash", "input": {}}])
    assert t.daemon is True
    t.join(timeout=5)


def test_loekken_KALDER_runde_etiketten():
    """En generator ingen kalder er husets hyppigste fejl — og præcis den jeg
    selv efterlod i `90a5bc56c`, med en note om at den ventede på en
    udskillelse. AST, ikke tekstsøgning: kaldet nævnes også i en kommentar lige
    over kaldestedet."""
    import ast
    import pathlib
    træ = ast.parse(pathlib.Path("core/services/visible_runs.py").read_text())
    fn = next((n for n in ast.walk(træ)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               and n.name == "_stream_visible_run"), None)
    assert fn is not None
    kaldt = {getattr(k.func, "id", "") for k in ast.walk(fn) if isinstance(k, ast.Call)}
    assert "_publish_runde_etiket" in kaldt, "runden skriver ingen etiket"


# ─────────────────── etiketten skal kunne NÅ skærmen (14/9-2026)
#
# Den regnes i en tråd, og en generator kan kun `yield` fra sit eget flow. Det
# er derfor Claude Code leverer sin NÆSTE tur — ikke et tilfælde ved deres
# løkke, men en følge af at streame. Vores løkke har flere runder pr. tur, så
# vi kan tømme køen ved næste RUNDES start: én runde senere, ikke én tur.

def test_en_faerdig_etiket_kan_haentes_af_loekken(monkeypatch):
    monkeypatch.setattr(vrt, "_etiket", lambda *a, **k: "Rettede fejl i login")
    monkeypatch.setattr(vrt.event_bus, "publish", lambda *a, **k: None)
    vrt.ryd_ventende("visible-k")
    t = vrt.udsend_runde_etiket(run_id="visible-k", round_num=1,
                                vaerktoejer=[{"name": "bash", "input": {}, "id": "t1"}])
    t.join(timeout=5)
    ventende = vrt.haent_ventende("visible-k")
    assert len(ventende) == 1
    assert ventende[0]["etiket"] == "Rettede fejl i login"
    assert ventende[0]["tool_use_ids"] == ["t1"]


def test_koeen_TOEMMES_naar_den_er_hentet(monkeypatch):
    """Ellers ville samme etiket blive sendt igen ved hver runde-start."""
    monkeypatch.setattr(vrt, "_etiket", lambda *a, **k: "x")
    monkeypatch.setattr(vrt.event_bus, "publish", lambda *a, **k: None)
    vrt.ryd_ventende("visible-k2")
    vrt.udsend_runde_etiket(run_id="visible-k2", round_num=1,
                            vaerktoejer=[{"name": "bash", "input": {}}]).join(timeout=5)
    assert len(vrt.haent_ventende("visible-k2")) == 1
    assert vrt.haent_ventende("visible-k2") == []


def test_koeen_holder_koerslerne_ADSKILT(monkeypatch):
    """To samtidige kørsler må ikke få hinandens overskrifter."""
    monkeypatch.setattr(vrt, "_etiket", lambda v, h: h)
    monkeypatch.setattr(vrt.event_bus, "publish", lambda *a, **k: None)
    for r in ("visible-a1", "visible-b1"):
        vrt.ryd_ventende(r)
        vrt.udsend_runde_etiket(run_id=r, round_num=1, hensigt=r,
                                vaerktoejer=[{"name": "bash", "input": {}}]).join(timeout=5)
    assert vrt.haent_ventende("visible-a1")[0]["etiket"] == "visible-a1"
    assert vrt.haent_ventende("visible-b1")[0]["etiket"] == "visible-b1"


def test_en_ukendt_koersel_giver_en_TOM_liste():
    assert vrt.haent_ventende("findes-ikke") == []


def test_koeen_har_et_LOFT(monkeypatch):
    """En kørsel der aldrig tømmer sin kø — fordi den døde midt i — må ikke
    kunne vokse ubegrænset. Huset har haft 2,81 mio. kanter på den måde."""
    monkeypatch.setattr(vrt, "_etiket", lambda *a, **k: "x")
    monkeypatch.setattr(vrt.event_bus, "publish", lambda *a, **k: None)
    vrt.ryd_ventende("visible-loft")
    for i in range(vrt.MAKS_VENTENDE + 5):
        vrt.udsend_runde_etiket(run_id="visible-loft", round_num=i,
                                vaerktoejer=[{"name": "bash", "input": {}}]).join(timeout=5)
    assert len(vrt.haent_ventende("visible-loft")) <= vrt.MAKS_VENTENDE


def test_loekken_TOEMMER_koeen_og_sender_den():
    """Kilde-vagt. En kø ingen tømmer er en etiket ingen ser — og huset har
    haft præcis den fejl: «events i en kø ingen tømmer»."""
    import ast
    import pathlib
    kilde = pathlib.Path("core/services/visible_runs.py").read_text()
    træ = ast.parse(kilde)
    fn = next((n for n in ast.walk(træ)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               and n.name == "_stream_visible_run"), None)
    assert fn is not None
    kaldt = {getattr(k.func, "id", "") for k in ast.walk(fn) if isinstance(k, ast.Call)}
    # 19/9-2026: begge hoeste gaar gennem `_hoest_etiketter`, der baade
    # returnerer etiketterne til streamen og GEMMER dem i turen.
    assert "_hoest_etiketter" in kaldt, "koeen toemmes aldrig"
    assert '_sse("tool_round_label"' in kilde, "etiketten sendes ikke paa streamen"


# ──────── den sidste rundes etiket blev aldrig leveret (14/9-2026)
#
# Køen fyldtes ved rundens SLUTNING og tømtes kun ved NÆSTE rundes start. To
# følger, og begge er stille:
#
#   - den sidste tool-rundes etiket bliver aldrig hentet — der er ingen næste
#   - en etiket der ikke er klar inden for løkkens omløb venter en hel runde
#
# Det er «events i en kø ingen tømmer» — den fejl huset har haft før, og som
# jeg selv skrev en test-kommentar om da jeg byggede køen.

def test_en_etiket_der_stadig_regnes_VENTES_der_paa(monkeypatch):
    """Ved turens slutning er der ikke mere at lave — saa en kort venten paa en
    etiket der er 0,3 s fra at vaere faerdig, er bedre end at tabe den."""
    import threading
    start = threading.Event()
    monkeypatch.setattr(vrt, "_etiket", lambda *a, **k: (start.wait(2), "Sen etiket")[1])
    monkeypatch.setattr(vrt.event_bus, "publish", lambda *a, **k: None)
    vrt.ryd_ventende("visible-sen")
    vrt.udsend_runde_etiket(run_id="visible-sen", round_num=1,
                            vaerktoejer=[{"name": "bash", "input": {}, "id": "t1"}])
    # Intet klart endnu
    assert vrt.haent_ventende("visible-sen") == []
    start.set()
    ud = vrt.haent_ventende_med_frist("visible-sen", 2.0)
    assert len(ud) == 1 and ud[0]["etiket"] == "Sen etiket"


def test_fristen_er_et_LOFT_og_ikke_en_ventetid(monkeypatch):
    """En etiket der haenger, maa ikke forsinke turens afslutning i det
    uendelige. Fristen loeber ud, og turen lukker."""
    import threading
    import time
    monkeypatch.setattr(vrt, "_etiket", lambda *a, **k: (time.sleep(5), "x")[1])
    monkeypatch.setattr(vrt.event_bus, "publish", lambda *a, **k: None)
    vrt.ryd_ventende("visible-haeng")
    vrt.udsend_runde_etiket(run_id="visible-haeng", round_num=1,
                            vaerktoejer=[{"name": "bash", "input": {}, "id": "t1"}])
    t0 = time.time()
    ud = vrt.haent_ventende_med_frist("visible-haeng", 0.4)
    brugt = time.time() - t0
    assert ud == []
    assert brugt < 1.5, f"ventede {brugt:.1f}s paa en frist paa 0,4"


def test_uden_noget_i_gang_ventes_der_SLET_ikke(monkeypatch):
    """Den almindelige tilstand er at der intet er. Den maa ikke koste tid."""
    import time
    vrt.ryd_ventende("visible-tom")
    t0 = time.time()
    assert vrt.haent_ventende_med_frist("visible-tom", 2.0) == []
    assert time.time() - t0 < 0.3


def test_traadene_ryddes_med_koeen(monkeypatch):
    """Ellers vokser bogholderiet over traade for hver eneste koersel."""
    monkeypatch.setattr(vrt, "_etiket", lambda *a, **k: "x")
    monkeypatch.setattr(vrt.event_bus, "publish", lambda *a, **k: None)
    vrt.udsend_runde_etiket(run_id="visible-ryd", round_num=1,
                            vaerktoejer=[{"name": "bash", "input": {}}]).join(timeout=5)
    vrt.ryd_ventende("visible-ryd")
    assert "visible-ryd" not in vrt._TRAADE


def test_loekken_toemmer_koeen_FOER_turen_lukker():
    """Kilde-vagt paa det led der manglede. Uden det gaar den sidste
    tool-rundes etiket tabt — og det er ofte den mest interessante runde."""
    import ast
    import pathlib
    kilde = pathlib.Path("core/services/visible_runs.py").read_text()
    træ = ast.parse(kilde)
    fn = next((n for n in ast.walk(træ)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               and n.name == "_stream_visible_run"), None)
    assert fn is not None
    kaldt = {getattr(k.func, "id", "") for k in ast.walk(fn) if isinstance(k, ast.Call)}
    # Den sidste hoest er `_hoest_etiketter` MED en frist (tredje argument).
    med_frist = [k for k in ast.walk(fn) if isinstance(k, ast.Call)
                 and getattr(k.func, "id", "") == "_hoest_etiketter" and len(k.args) == 3]
    assert med_frist, "den sidste etiket hentes aldrig"
