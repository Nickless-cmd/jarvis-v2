"""Fase 9: fladen skal kunne FORKLARE hvilke regler en koersel koerte under.

Spec'en skriver «Mission Control explains ...». MC findes ikke laengere — den
blev revet ud — og fladerne er i dag `central_cli` og desk, som begge henter
`/central/*`. Kriteriet er oversat dertil, ikke droppet.
"""
import pytest

from core.services.central_profiles import (
    FORKLAREDE_FELTER, build_profiles_surface,
)


@pytest.fixture
def flade():
    return build_profiles_surface()


def test_alle_syv_profiler_forklares(flade):
    from core.runtime.profiles import kendte
    assert {p["navn"] for p in flade["profiler"]} == set(kendte())


@pytest.mark.parametrize("felt", [
    "tool_scope", "approval_mode", "retry", "compaction",
    "memory", "private_layers", "subagents",
])
def test_hvert_felt_spec_en_naevner_er_med(felt, flade):
    """Spec'en opregner dem: tools, approval, retry, compaction, memory,
    private layers, subagent policy."""
    assert felt in FORKLAREDE_FELTER
    for p in flade["profiler"]:
        assert felt in p, f"{p['navn']} forklarer ikke {felt}"


def test_modellen_hoerer_til_KOERSLEN_ikke_profilen(flade):
    """Samme profil kan koere paa flere modeller. Stod model paa profilen,
    ville forklaringen vaere forkert for halvdelen af koerslerne."""
    for p in flade["profiler"]:
        assert "model" not in p
    for k in flade["seneste_kørsler"]:
        assert "model" in k


def test_hver_profil_baerer_sin_hash(flade):
    for p in flade["profiler"]:
        assert len(p["hash"]) == 16


def test_koersler_uden_nulevende_profil_udpeges(monkeypatch):
    """Staar der en hash paa en koersel som ingen nulevende profil har, er
    profilen aendret siden. Det er ikke en fejl — det er praecis det man vil
    vide naar man undersoeger noget fra i forgaars."""
    import core.services.central_profiles as cp
    monkeypatch.setattr(cp, "_seneste_kørsler", lambda graense=20: [
        {"run_id": "r1", "lane": "primary", "model": "m", "status": "completed",
         "started_at": "2026-09-11T10:00:00", "profil": "autonomous",
         "hash": "enhashderikkefind", "skema_version": 1},
    ])
    s = cp.build_profiles_surface()
    assert s["hashes_uden_nulevende_profil"] == ["enhashderikkefind"]


def test_en_database_uden_migrationen_er_ikke_en_fejl(monkeypatch):
    """Kolonnerne kommer via doven migration. En base der ikke har naaet den
    skal give en tom liste, ikke et kast."""
    import core.services.central_profiles as cp
    def _boom():
        raise RuntimeError("ingen kolonne")
    monkeypatch.setattr("core.runtime.db.connect", _boom)
    assert cp._seneste_kørsler() == []
    assert cp.build_profiles_surface()["profiler"]


def test_ruten_er_ejer_gated():
    """En profil beskriver hvilke rettigheder koersler har. Det er ikke noget
    et husstandsmedlem skal kunne kortlaegge."""
    import inspect

    from apps.api.jarvis_api.routes import central_profiles as rute
    kilde = inspect.getsource(rute.get_profiles)
    assert "_require_owner()" in kilde


def test_ruten_er_registreret_i_appen():
    """Ellers er overfladen bygget og utilgaengelig — husets hyppigste fejl."""
    import pathlib
    kilde = pathlib.Path("apps/api/jarvis_api/app.py").read_text()
    assert "central_profiles" in kilde
    assert "_central_profiles.router" in kilde
