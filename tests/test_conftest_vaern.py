"""Værnene i conftest skal kunne SES virke — og ses slippe en markeret test igennem.

`_guard_prod_db_path` og `_guard_prod_state_dir` har eksisteret siden 17/9-2026
uden en eneste test. De er autouse-fixtures: fjernes de, bliver hele suiten ved
med at være grøn, mens testfikstur siver ud i den ægte `~/.jarvis-v2`. Det er
præcis den tavshed de blev skrevet for at fjerne.

Målt 25/9-2026: med `_guard_prod_shared_dir` slået fra skrev fire testfiler i
den rigtige `~/.jarvis-v2/shared/runtime/dreaming_session.json` — og de 56
tests bestod i begge tilfælde. Forureningen er usynlig i testresultatet, så den
skal måles direkte.
"""
from __future__ import annotations

import pathlib

import pytest


def _aegte_hjem() -> pathlib.Path:
    return pathlib.Path.home() / ".jarvis-v2"


# ── shared/ og workspaces/ (_guard_prod_shared_dir) ─────────────────────────


def test_shared_dir_peger_IKKE_paa_den_aegte_mappe():
    """23 moduler skriver i `shared/runtime/`. Ingen af dem må ramme driften."""
    from core.runtime.workspace_paths import shared_dir

    assert shared_dir().resolve() != (_aegte_hjem() / "shared").resolve()


def test_en_skrivning_lander_uden_for_driften(tmp_path):
    """Ikke bare stien — den faktiske fil."""
    from core.runtime.workspace_paths import shared_dir

    maal = shared_dir() / "runtime" / "vaern_proeve.json"
    maal.parent.mkdir(parents=True, exist_ok=True)
    maal.write_text("{}", encoding="utf-8")
    try:
        assert not str(maal.resolve()).startswith(str(_aegte_hjem().resolve()))
    finally:
        maal.unlink(missing_ok=True)


@pytest.mark.real_home
def test_real_home_slipper_igennem():
    """Symmetrien: et værn der ikke kan slås fra bliver slået ud i stedet.

    `real_home` findes for benchmarks og lignende der MÅ måle mod maskinens
    egne data — se `test_memory_benchmarks.py::test_source_diversity`.
    """
    from core.runtime.workspace_paths import shared_dir

    assert shared_dir().resolve() == (_aegte_hjem() / "shared").resolve()


# ── state/ (_guard_prod_state_dir) ──────────────────────────────────────────


def test_state_store_peger_IKKE_paa_den_aegte_mappe():
    """Værnet fra 17/9 havde heller ingen test. Nu har det."""
    from core.runtime import state_store

    assert state_store._STATE_DIR.resolve() != (_aegte_hjem() / "state").resolve()


@pytest.mark.real_state
def test_real_state_slipper_igennem():
    from core.runtime import state_store

    assert state_store._STATE_DIR.resolve() == (_aegte_hjem() / "state").resolve()


# ── de to værn må ikke forveksles ───────────────────────────────────────────


def test_de_to_vaern_er_uafhaengige():
    """`JARVIS_HOME`-værnet rører kun `shared/` og `workspaces/`.

    `core.runtime.config.JARVIS_HOME` beregnes ved import fra `Path.home()` og
    læser IKKE env'en, så `config/`, `state/` og `logs/` er urørt af det. Det
    er derfor de to værn kan sættes og slås fra hver for sig.
    """
    from core.runtime.config import JARVIS_HOME
    from core.runtime.workspace_paths import shared_dir

    assert JARVIS_HOME.resolve() == _aegte_hjem().resolve()
    assert shared_dir().resolve() != (_aegte_hjem() / "shared").resolve()


# ── bash_session-daemonen ───────────────────────────────────────────────────


def test_pid_filen_peger_ikke_paa_den_aegte_daemon():
    """`_PID_PATH` er porten ind til den ægte shell-daemon.

    `bash_session._STATE_DIR` beregnes ved import som
    `Path.home()/".jarvis-v2"/"state"` og læser ALDRIG `JARVIS_HOME`, så
    hverken `shared/`-værnet eller `state/`-værnet rammer den. Uden dette
    tredje værn kunne en test starte en shell-daemon på maskinen
    (`_ensure_daemon_running` spawner når der ingen er) og bagefter forhindre
    den i at lukke ned igen (enhver forespørgsel nulstiller uret bag
    selv-nedlukningen efter en time).
    """
    from core.tools import bash_session

    assert bash_session._PID_PATH.resolve() != (
        _aegte_hjem() / "state" / "bash_session.pid").resolve()
    assert not bash_session._PID_PATH.exists()
    assert bash_session._read_daemon_pid() is None


@pytest.mark.real_bash_daemon
def test_real_bash_daemon_slipper_igennem():
    from core.tools import bash_session

    assert bash_session._PID_PATH.resolve() == (
        _aegte_hjem() / "state" / "bash_session.pid").resolve()


# ── produktionsdatabasen (_afvis_skrivning_til_prod_db) ─────────────────────


def _prod_sti() -> pathlib.Path:
    from core.runtime.config import STATE_DIR

    return pathlib.Path(STATE_DIR) / "jarvis.db"


def test_skrivning_til_prod_db_afvises_ved_porten():
    """En modul-bundet `connect` må ikke kunne snige sig forbi DB_PATH-værnet.

    Målt 4/11-2026: `db_cadence_journal.py` bandt `connect` på modul-niveau.
    `_guard_prod_db_path` patcher kun den modul-instans der ligger i
    `sys.modules`; en funktionskopi fra en ældre instans rammer ikke den patch.
    121 rækker landede i den levende base mens suiten var grøn.
    """
    import sqlite3

    with pytest.raises(AssertionError, match="ÆGTE produktionsdatabase"):
        sqlite3.connect(str(_prod_sti()))


def test_skrivning_via_uri_uden_ro_afvises_ogsaa():
    """`file:`-URI er en anden indgang til samme fil — den skal også lukkes."""
    import sqlite3

    with pytest.raises(AssertionError, match="ÆGTE produktionsdatabase"):
        sqlite3.connect(f"file:{_prod_sti()}", uri=True)


def test_laesning_af_prod_db_slipper_igennem():
    """`_prod_db_shield_path` kopierer prods skema read-only — det skal virke.

    Et værn der også blokerede læsning ville tvinge shielden til at gætte
    skemaet, og så er den ikke længere skema-tro mod drift.
    """
    import sqlite3

    prod = _prod_sti()
    if not prod.is_file():
        pytest.skip("ingen produktionsdatabase på denne maskine")
    conn = sqlite3.connect(f"file:{prod}?mode=ro", uri=True)
    try:
        assert conn.execute("SELECT count(*) FROM sqlite_master").fetchone()[0] > 0
    finally:
        conn.close()


@pytest.mark.real_db
def test_real_db_slipper_igennem():
    """Symmetrien: markøren findes for tests der bevidst må røre den ægte base."""
    import sqlite3

    prod = _prod_sti()
    if not prod.is_file():
        pytest.skip("ingen produktionsdatabase på denne maskine")
    conn = sqlite3.connect(str(prod))
    conn.close()
