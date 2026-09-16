"""Boot-reconcileren så kun det ene af to lagre.

## Hullet

`list_running_orphans` itererer over `in_flight_runs`. En række der findes i
`visible_runs` men aldrig blev skrevet — eller blev ryddet — i det andet lager
er derfor usynlig for reconcileren **for altid**.

Målt 13/9-2026 på runtime: `autonomous-53cc4ddf…` stod `running` uden
`finished_at` siden 12/9 kl. 20:19, altså ~20 timer, mens reconcileren
rapporterede `count: 0` ved hver eneste opstart. Begge dele var sande. De så
bare på hvert sit lager.

## Hvorfor tærsklen er seks timer og ikke ti minutter

Den eksisterende tærskel hviler på et **ejerskab** (pid + proces-starttid) og
kan derfor være stram. Denne hviler på et **fravær**, og et fravær er et
svagere bevis — det kan skyldes en startvej der ikke skriver begge spor. Så
bærer alderen resten alene.
"""
from __future__ import annotations

import pytest

from core.services import session_boot_reconciler as sbr


@pytest.fixture
def _lager(monkeypatch):
    """Byt både databasen og in_flight-lageret ud."""
    tilstand: dict = {"raekker": [], "kendte": {}, "stemplet": []}

    class _Cursor:
        def __init__(self, raekker): self._r = raekker
        def fetchall(self): return self._r

    class _Conn:
        def execute(self, q, p=()):
            tilstand["sidste_parametre"] = p        # hvilken graense blev brugt?
            return _Cursor(tilstand["raekker"])
        def __enter__(self): return self
        def __exit__(self, *a): return False

    import core.runtime.db as db
    monkeypatch.setattr(db, "connect", lambda: _Conn())
    monkeypatch.setattr(sbr.in_flight_runs, "_load", lambda: tilstand["kendte"])

    import core.services.visible_runs_outcomes as vro
    monkeypatch.setattr(vro, "stamp_visible_run_interrupted",
                        lambda rid, reason="": tilstand["stemplet"].append((rid, reason)))
    return tilstand


def test_raekke_som_INTET_kender_stemples(_lager):
    """Hele pointen: `in_flight_runs` ved intet, altså streamer ingen den."""
    _lager["raekker"] = [("autonomous-zombie",)]
    _lager["kendte"] = {}
    assert sbr._ryd_visible_drift(True) == 1
    assert _lager["stemplet"] == [
        ("autonomous-zombie", "proces doede uden at afslutte koerslen")]


def test_raekke_der_ER_kendt_roeres_IKKE(_lager):
    """Kender det andet lager posten, er der en proces om den — og den
    eksisterende ejerskabs-logik afgoer dens skaebne, ikke den her."""
    _lager["raekker"] = [("visible-lever",)]
    _lager["kendte"] = {"visible-lever": {"run_id": "visible-lever", "status": "running"}}
    assert sbr._ryd_visible_drift(True) == 0
    assert _lager["stemplet"] == []


def test_SKYGGE_taeller_men_skriver_ikke(_lager):
    """Samme kontakt som resten af reconcileren. Skygge er hele husets
    fremgangsmaade for en gate der skaerer."""
    _lager["raekker"] = [("autonomous-zombie",)]
    _lager["kendte"] = {}
    assert sbr._ryd_visible_drift(False) == 1
    assert _lager["stemplet"] == [], "skygge skrev alligevel"


def test_ULAESELIGT_in_flight_stempler_INTET(_lager, monkeypatch):
    """Kan vi ikke laese det andet lager, kan vi ikke VIDE at posten er ukendt.

    Et gaet er ikke et fravaer. Faldt vi tilbage til «ingen kendte», ville en
    forbigaaende laesefejl stemple hver eneste levende koersel som doed.
    """
    _lager["raekker"] = [("visible-lever",)]
    monkeypatch.setattr(sbr.in_flight_runs, "_load",
                        lambda: (_ for _ in ()).throw(OSError("filen laast")))
    assert sbr._ryd_visible_drift(True) == 0
    assert _lager["stemplet"] == []


def test_db_fejl_vaelter_ikke_opstarten(_lager, monkeypatch):
    """En reconciler-fejl maa ALDRIG crashe opstarten — det staar i modulets
    egen governance-note."""
    import core.runtime.db as db
    monkeypatch.setattr(db, "connect",
                        lambda: (_ for _ in ()).throw(RuntimeError("db nede")))
    assert sbr._ryd_visible_drift(True) == 0


def test_taersklen_er_KONSERVATIV():
    """Seks timer, ikke ti minutter. Fravaer er et svagere bevis end ejerskab,
    saa alderen skal baere resten alene — og den laengste koersel maalt i huset
    er minutter (median 77 sekunder)."""
    assert sbr.VISIBLE_DRIFT_AFTER_SECONDS >= 6 * 3600
    assert sbr.VISIBLE_DRIFT_AFTER_SECONDS > sbr.STALE_AFTER_SECONDS


def test_forespoergslen_filtrerer_paa_ALDER_og_paa_running():
    """Kilde-vagt. Uden alders-filteret ville en koersel der lige er startet —
    og hvis in_flight-post endnu ikke er skrevet — blive stemplet doed i et
    kapløb ved opstart."""
    import inspect
    kilde = inspect.getsource(sbr._ryd_visible_drift)
    assert "status = 'running'" in kilde
    assert "started_at < ?" in kilde
    assert "finished_at IS NULL OR finished_at = ''" in kilde


# ------------------------------------------ sweepen skal faktisk KALDES

def test_reconcileren_KALDER_drift_sweepen():
    """En sweep ingen kalder er praecis den fejl den er skrevet for at rette.

    AST, ikke tekstsoegning — kaldet kunne staa i en kommentar.
    """
    import ast
    import pathlib
    træ = ast.parse(pathlib.Path(
        "core/services/session_boot_reconciler.py").read_text())
    fn = next((n for n in ast.walk(træ) if isinstance(n, ast.FunctionDef)
               and n.name == "reconcile_on_boot"), None)
    assert fn is not None, "reconcile_on_boot er flyttet"
    kaldt = {getattr(k.func, "id", "") for k in ast.walk(fn) if isinstance(k, ast.Call)}
    assert "_ryd_visible_drift" in kaldt, \
        "reconcileren rydder ikke driften — zombien bliver staaende"


def test_drift_staar_i_opsummeringen(monkeypatch):
    """Et tal ingen rapporterer er lige saa tavst som ingen sweep."""
    monkeypatch.setattr(sbr, "_ryd_visible_drift", lambda enforced: 7)
    monkeypatch.setattr(sbr.in_flight_runs, "list_running_orphans", lambda *a, **k: [])
    ud = sbr.reconcile_on_boot()
    assert ud.get("visible_drift") == 7


# ──────── en doed koersel blev stemplet i TAVSHED (14/9-2026)
#
# Bjoern, efter at vaerten crashede to gange paa tre minutter:
# «Et run maa aldrig doe».
#
# Genoptagelsen FINDES — `living_executive` planlaegger en self-wakeup paa
# «Resume from interrupted visible run» — men den lytter efter eventet
# `runtime.visible_run_interrupted`. Og det event udsendes ÉT sted:
# `visible_runs.py:3859`, inde i grenen for UDBYDER-fejl.
#
# `stamp_visible_run_interrupted` laver en bar UPDATE og udsender ingenting.
# Den kaldes praecis to steder — begge i boot-reconcileren, altsaa naar en
# koersel doede SAMMEN MED sin proces. Maalt i aften: koerslen der doede kl.
# 20:20 blev stemplet, og NUL self-wakeups fyrede.
#
# En koersel dræbt af et crash laa altsaa doed for evigt, fordi det eneste der
# kunne vaekke den var en udbyder-fejl — ikke en doed.

def test_stemplet_UDSENDER_at_koerslen_blev_afbrudt(monkeypatch):
    """Uden eventet naar genoptagelsen aldrig at hoere om det."""
    import core.services.visible_runs_outcomes as vro
    sendt: list[tuple[str, dict]] = []
    monkeypatch.setattr(vro.event_bus, "publish",
                        lambda navn, nyttelast=None, **k: sendt.append((navn, nyttelast or {})))

    class _Cur:
        rowcount = 1
    class _Conn:
        def execute(self, *a, **k): return _Cur()
        def __enter__(self): return self
        def __exit__(self, *a): return False
    monkeypatch.setattr(vro, "connect", lambda: _Conn())

    assert vro.stamp_visible_run_interrupted("visible-abc", reason="proces doede") is True
    assert sendt, "stemplet var tavst — genoptagelsen hoerer intet"
    navn, p = sendt[0]
    assert navn == "runtime.visible_run_interrupted"
    assert p["run_id"] == "visible-abc"
    # Genoptagelsens prompt bygges af `summary` ELLER `error`
    # (`living_executive:276`). Begge udfyldes med vilje, saa en aendring i
    # hvilken der laeses ikke kan goere prompten til «unknown interruption».
    #
    # Foerste udgave af den her paastand skrev `summary or error` — og saa kunne
    # en mutation toemme `summary` uden at testen opdagede det. En test der
    # accepterer et faldback kan ikke vogte det den vogter over.
    assert "proces doede" in (p.get("summary") or "")
    assert "proces doede" in (p.get("error") or "")


def test_en_raekke_der_IKKE_blev_stemplet_udsender_intet(monkeypatch):
    """Idempotens: sweepen koerer igen og igen. Udsendte den hver gang, ville
    én doed koersel vaekke Jarvis ved hver opstart resten af sessionen."""
    import core.services.visible_runs_outcomes as vro
    sendt: list = []
    monkeypatch.setattr(vro.event_bus, "publish", lambda *a, **k: sendt.append(1))

    class _Cur:
        rowcount = 0          # allerede terminal — ingen raekke roert
    class _Conn:
        def execute(self, *a, **k): return _Cur()
        def __enter__(self): return self
        def __exit__(self, *a): return False
    monkeypatch.setattr(vro, "connect", lambda: _Conn())

    assert vro.stamp_visible_run_interrupted("visible-abc", reason="x") is False
    assert sendt == []


def test_en_fejlende_udsendelse_vaelter_ikke_stemplingen(monkeypatch):
    """Stemplingen er det vigtige: en raekke der bliver staaende «running»
    blokerer naeste tur. Eventet er en bonus, ikke en betingelse."""
    import core.services.visible_runs_outcomes as vro
    monkeypatch.setattr(vro.event_bus, "publish",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("bus nede")))

    class _Cur:
        rowcount = 1
    class _Conn:
        def execute(self, *a, **k): return _Cur()
        def __enter__(self): return self
        def __exit__(self, *a): return False
    monkeypatch.setattr(vro, "connect", lambda: _Conn())

    assert vro.stamp_visible_run_interrupted("visible-abc", reason="x") is True


# ── containerens opstart er et staerkere bevis end alder (16/9-2026) ──────
#
# Fire autonome koersler startede 15:28, containeren genstartede 15:37, og
# reconcileren meldte NUL ved hver opstart bagefter: de laa ikke i
# `in_flight_runs`, og seks timer var ikke gaaet.

def test_graensen_er_containerens_opstart_naar_den_er_frisk(monkeypatch):
    from datetime import UTC, datetime, timedelta
    nu = datetime(2026, 9, 16, 14, 0, tzinfo=UTC)
    start = nu - timedelta(minutes=20)
    monkeypatch.setattr(sbr, "_container_start", lambda n=None: start)
    assert sbr._drift_graense(nu) == start          # 20 min slaar 6 timer


def test_graensen_er_alderen_naar_containeren_har_koert_laenge(monkeypatch):
    from datetime import UTC, datetime, timedelta
    nu = datetime(2026, 9, 16, 14, 0, tzinfo=UTC)
    monkeypatch.setattr(sbr, "_container_start", lambda n=None: nu - timedelta(days=3))
    assert sbr._drift_graense(nu) == nu - timedelta(seconds=sbr.VISIBLE_DRIFT_AFTER_SECONDS)


def test_uden_opstartstid_falder_vi_tilbage_paa_alderen(monkeypatch):
    """Kan vi ikke laese /proc/uptime, maa vi ikke stemple paa et gaet."""
    from datetime import UTC, datetime, timedelta
    nu = datetime(2026, 9, 16, 14, 0, tzinfo=UTC)
    monkeypatch.setattr(sbr, "_container_start", lambda n=None: None)
    assert sbr._drift_graense(nu) == nu - timedelta(seconds=sbr.VISIBLE_DRIFT_AFTER_SECONDS)


def test_container_start_laeses_af_proc_uptime(monkeypatch, tmp_path):
    from datetime import UTC, datetime
    fil = tmp_path / "uptime"
    fil.write_text("1200.5 1200.5\n", encoding="utf-8")
    ægte = open
    monkeypatch.setattr("builtins.open",
                        lambda p, *a, **kw: ægte(fil, *a, **kw) if p == "/proc/uptime" else ægte(p, *a, **kw))
    nu = datetime(2026, 9, 16, 14, 0, tzinfo=UTC)
    start = sbr._container_start(nu)
    assert start is not None and abs((nu - start).total_seconds() - 1200.5) < 1


def test_opslaget_bruger_FAKTISK_graensen(_lager, monkeypatch):
    """Mutations-proeve: uden den her kunne kalderen regne sin egen graense ud,
    og alle proever ovenfor ville stadig vaere groenne — fixturen svarer jo det
    samme uanset hvad der spoerges om."""
    from datetime import UTC, datetime
    valgt = datetime(2026, 9, 16, 13, 39, tzinfo=UTC)
    monkeypatch.setattr(sbr, "_drift_graense", lambda *a, **kw: valgt)
    _lager["raekker"] = [("autonomous-zombie",)]
    _lager["kendte"] = {}
    sbr._ryd_visible_drift(True)
    assert _lager["sidste_parametre"] == (valgt.isoformat(),)
