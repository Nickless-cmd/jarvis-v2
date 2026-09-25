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
