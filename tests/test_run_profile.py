"""Hver koersel skal kunne gøre rede for hvilke regler den koerte under.

Fase 9's exit-kriterium: «every run records effective profile schema version
and hash». Foer i dag stod svaret ingen steder — reglerne laa som loese flag
paa `VisibleRun` (`autonomous`, `local_tool_exec`, `trust_all`), og ingen af dem
hedder «profil».
"""
from types import SimpleNamespace

import pytest

from core.runtime.run_profile import profil_for, profil_navn_for


def _run(**kw):
    return SimpleNamespace(**{"autonomous": False, "local_tool_exec": False, **kw})


def test_et_autonomt_run_er_autonomt():
    assert profil_navn_for(_run(autonomous=True)) == "autonomous"


def test_autonom_VINDER_over_kodefladen():
    """«Ingen mennesker til stede» er den stramme egenskab, og den skal vinde.
    Et run der er begge dele er et autonomt run."""
    assert profil_navn_for(_run(autonomous=True, local_tool_exec=True)) == "autonomous"


def test_kodefladen_kendes_paa_local_tool_exec():
    assert profil_navn_for(_run(local_tool_exec=True)) == "jarvis-code"


def test_research_kendes_paa_sit_flag():
    assert profil_navn_for(_run(), research=True) == "research"


def test_research_vinder_IKKE_over_autonom():
    assert profil_navn_for(_run(autonomous=True), research=True) == "autonomous"


def test_en_koersel_kan_ikke_udnaevne_sig_selv_til_ejer(monkeypatch):
    """Rollen kommer fra workspace-konteksten, ikke fra koerslen."""
    monkeypatch.setattr("core.identity.workspace_context.effective_role",
                        lambda: "member")
    assert profil_navn_for(_run(trust_all=True)) == "visible-member"


def test_ejeren_faar_ejer_profilen(monkeypatch):
    monkeypatch.setattr("core.identity.workspace_context.effective_role",
                        lambda: "owner")
    assert profil_navn_for(_run()) == "visible-owner"


def test_et_UBRUGELIGT_run_objekt_falder_til_safe_offline():
    """Tvivl falder nedad, aldrig op."""
    class _Bomb:
        def __getattr__(self, _):
            raise RuntimeError("intet at hente")
    assert profil_navn_for(_Bomb()) == "safe-offline"


def test_profilen_baerer_baade_hash_og_version():
    p = profil_for(_run(autonomous=True))
    assert p.hash and len(p.hash) == 16
    assert p.skema_version >= 1
    assert p.navn == "autonomous"


# ── Raekken ─────────────────────────────────────────────────────────────────

def test_start_raekken_gemmer_profilen(tmp_path, monkeypatch):
    """Uden dette er komponisten et bibliotek ingen kalder — husets hyppigste
    fejl."""
    import sqlite3

    import core.services.visible_runs_outcomes as vro

    db = sqlite3.connect(":memory:")
    db.execute("""CREATE TABLE visible_runs (
        run_id TEXT PRIMARY KEY, lane TEXT, provider TEXT, model TEXT,
        status TEXT, started_at TEXT, finished_at TEXT, text_preview TEXT,
        error TEXT, capability_id TEXT)""")

    class _Conn:
        def __enter__(self): return db
        def __exit__(self, *a): return False
    monkeypatch.setattr(vro, "connect", lambda: _Conn())

    vro.persist_visible_run_start(_run(
        run_id="visible-proeve", lane="primary", provider="ollama",
        model="m", user_message="hej", autonomous=True))

    r = db.execute(
        "SELECT profile_name, profile_hash, profile_schema_version "
        "FROM visible_runs WHERE run_id='visible-proeve'").fetchone()
    assert r is not None, "raekken blev slet ikke skrevet"
    assert r[0] == "autonomous"
    assert len(r[1]) == 16
    assert r[2] >= 1


def test_gamle_raekker_faar_IKKE_en_gaettet_profil():
    """Ingen tilbagefyld. En gaettet profil paa en historisk koersel ville se
    ud som viden og kunne ikke efterproeves."""
    import inspect

    import core.services.visible_runs_outcomes as vro
    kilde = inspect.getsource(vro._sikr_profil_kolonner)
    assert "UPDATE" not in kilde.upper(), "migrationen tilbagefylder"
    assert "DEFAULT ''" in kilde
