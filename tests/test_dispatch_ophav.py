"""En dispatch skal kunne føres tilbage til den tur der startede den.

## Hvorfor

`claude_dispatch` præger sit eget `task_id` (`uuid4().hex[:12]`) der ikke deler
noget med noget andet lager. Målt 13/9-2026: **elleve** forskellige stores
repræsenterer «et stykke arbejde», og næsten ingen er koblet — så ingen flade
kan vise «denne samtale satte det her i gang».

Forbindelsen fandtes hele tiden i koden. `aktivt_run_id()` blev bygget efter to
hændelser der stod med tomt `run_id` og derfor ikke kunne efterforskes: feltet
fandtes, kalderen sendte det bare ikke. Her var det det samme — kanten blev
kastet væk i det øjeblik dispatchen startede.
"""
from __future__ import annotations

import sqlite3

import pytest

from core.tools.claude_dispatch import audit


@pytest.fixture
def _db(monkeypatch):
    """En rigtig sqlite i hukommelsen — migrationen skal faktisk køre."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE claude_dispatch_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL UNIQUE,
            started_at TEXT NOT NULL, ended_at TEXT,
            spec_json TEXT NOT NULL, status TEXT NOT NULL,
            tokens_used INTEGER NOT NULL DEFAULT 0,
            exit_code INTEGER, diff_summary TEXT, error TEXT)"""
    )

    class _Wrap:
        def __enter__(self): return conn
        def __exit__(self, *a): return False

    monkeypatch.setattr(audit, "connect", lambda: _Wrap())
    return conn


def _spec():
    from core.tools.claude_dispatch.spec import parse_spec
    return parse_spec({"goal": "goer noget", "scope_files": ["core/services/x.py"],
                        "allowed_tools": ["Read"]})


# --------------------------------------------------------- migrationen

def test_migrationen_tilfoejer_kolonnerne(_db):
    audit._sikr_ophav_kolonner(_db)
    kolonner = {r[1] for r in _db.execute("PRAGMA table_info(claude_dispatch_audit)")}
    assert {"origin_run_id", "origin_session_id"} <= kolonner


def test_migrationen_er_IDEMPOTENT(_db):
    """Den koerer ved HVER skrivning. Var den ikke idempotent, ville anden
    dispatch braekke."""
    audit._sikr_ophav_kolonner(_db)
    audit._sikr_ophav_kolonner(_db)
    audit._sikr_ophav_kolonner(_db)
    kolonner = [r[1] for r in _db.execute("PRAGMA table_info(claude_dispatch_audit)")]
    assert kolonner.count("origin_run_id") == 1


def test_INTET_tilbagefyld_paa_gamle_raekker(_db):
    """En historisk dispatch koerte FOER kanten fandtes. Et gaettet ophav ville
    pege paa en forkert koersel — vaerre end et tomt felt."""
    _db.execute(
        "INSERT INTO claude_dispatch_audit (task_id, started_at, spec_json, status) "
        "VALUES ('gammel','2026-01-01','{}','completed')")
    audit._sikr_ophav_kolonner(_db)
    r = _db.execute("SELECT origin_run_id FROM claude_dispatch_audit "
                    "WHERE task_id='gammel'").fetchone()
    assert r["origin_run_id"] == ""


# ------------------------------------------------------------- ophavet

def test_ophavet_GEMMES(_db, monkeypatch):
    monkeypatch.setattr(audit, "_ophav", lambda: ("visible-abc", "sess-1"))
    audit.start_audit_row("t1", _spec())
    r = _db.execute("SELECT origin_run_id, origin_session_id FROM "
                    "claude_dispatch_audit WHERE task_id='t1'").fetchone()
    assert r["origin_run_id"] == "visible-abc"
    assert r["origin_session_id"] == "sess-1"


def test_ukendt_ophav_gemmes_TOMT_ikke_gaettet(_db, monkeypatch):
    monkeypatch.setattr(audit, "_ophav", lambda: ("", ""))
    audit.start_audit_row("t2", _spec())
    r = _db.execute("SELECT origin_run_id FROM claude_dispatch_audit "
                    "WHERE task_id='t2'").fetchone()
    assert r["origin_run_id"] == ""


def test_ophav_der_KASTER_vaelter_ikke_dispatchen(monkeypatch):
    """En dispatch maa ikke kunne braekke fordi bogfoeringen af dens ophav
    fejlede. Arbejdet er vigtigere end sporet til det."""
    monkeypatch.setattr(
        "core.services.session_context_resolve.aktivt_run_id",
        lambda *a: (_ for _ in ()).throw(RuntimeError("nede")))
    assert audit._ophav() == ("", "")


def test_ophavet_laeses_fra_den_RIGTIGE_kilde():
    """Kilde-vagt: `aktivt_run_id` er den ene offentlige vej ind til run-id'et.
    Et privat opslag paa tvaers af moduler ville braekke naeste gang nogen
    flytter det."""
    import inspect
    kilde = inspect.getsource(audit._ophav)
    assert "aktivt_run_id" in kilde and "aktiv_session_id" in kilde


# -------------------------------------------- fladen skal BAERE det videre

def test_listefladen_BAERER_ophavet():
    """Den eksplicitte kolonneliste i `/api/dispatches` er praecis det sted et
    nyt felt forsvinder tavst. `read_audit_row` bruger `SELECT *` og faar det
    gratis; listen goer ikke."""
    import pathlib
    kilde = pathlib.Path(
        "apps/api/jarvis_api/routes/jarvisx_dispatches.py").read_text()
    assert "origin_run_id, origin_session_id" in kilde, \
        "listens kolonneliste henter ikke ophavet"
    assert '"origin_run_id": _felt(' in kilde, \
        "ophavet naar ikke ud i svaret"


def test_fladen_TAALER_at_kolonnen_mangler():
    """Migrationen er doven. En database der ikke har skrevet en dispatch siden
    feltet kom til, har det ikke — og et KeyError ville vaelte HELE listen paa
    grund af ét felt."""
    from apps.api.jarvis_api.routes.jarvisx_dispatches import _felt

    class _Raekke:
        def __getitem__(self, k):
            raise KeyError(k)

    assert _felt(_Raekke(), "origin_run_id") == ""


def test_fladen_sikrer_kolonnerne_foer_den_laeser():
    """Uden det ville foerste kald mod en umigreret database fejle paa en
    manglende kolonne."""
    import ast
    import pathlib
    træ = ast.parse(pathlib.Path(
        "apps/api/jarvis_api/routes/jarvisx_dispatches.py").read_text())
    fn = next((n for n in ast.walk(træ) if isinstance(n, ast.FunctionDef)
               and n.name == "list_dispatches"), None)
    assert fn is not None
    kaldt = {getattr(k.func, "id", "") for k in ast.walk(fn) if isinstance(k, ast.Call)}
    assert "_sikr_ophav_kolonner" in kaldt


# ------------------------------------------------------- RODEN, ikke ophavet

def test_work_ref_er_KOERSLEN_naar_der_er_en():
    """Er dispatchen foedt af en tur, hoerer arbejdet til den tur."""
    assert audit._work_ref("visible-abc", "d1") == "run:visible-abc"


def test_work_ref_falder_tilbage_paa_dispatchen_selv():
    """Uden ophav er dispatchen sin EGEN rod. Et tomt felt ville goere den
    hjemloes; en reference til en kørsel der ikke findes ville vaere en loegn."""
    assert audit._work_ref("", "d1") == "dispatch:d1"


def test_work_ref_er_tom_naar_INTET_kan_refereres():
    assert audit._work_ref("", "") == ""


def test_roden_GEMMES(_db, monkeypatch):
    monkeypatch.setattr(audit, "_ophav", lambda: ("visible-abc", "s1"))
    audit.start_audit_row("t9", _spec())
    r = _db.execute("SELECT work_ref, origin_run_id FROM claude_dispatch_audit "
                    "WHERE task_id='t9'").fetchone()
    assert r["work_ref"] == "run:visible-abc"
    # De to felter svarer paa hvert sit spoergsmaal og maa ikke smelte sammen.
    assert r["origin_run_id"] == "visible-abc"


def test_roden_kan_OPLOESES_af_den_faelles_vej():
    """En reference hver flade selv skal parse, er ikke en faelles noegle."""
    from core.runtime.work_ref import opløs
    assert opløs(audit._work_ref("visible-abc", "d1")) == ("run", "visible-abc")


def test_fladen_baerer_roden_videre():
    import pathlib
    kilde = pathlib.Path(
        "apps/api/jarvis_api/routes/jarvisx_dispatches.py").read_text()
    assert 'origin_session_id, work_ref' in kilde, "kolonnelisten henter ikke roden"
    assert '"work_ref": _felt(' in kilde, "roden naar ikke ud i svaret"
