"""Adfaerdstests for de kapsel-felter der fik en maalt skriver 10/11-2026.

Vagten i ``test_capsule_felter_har_skriver.py`` beviser at hvert VIST felt har
en ikke-konstant skriver. Den beviser ikke at skriveren virker, og den beviser
slet ikke at tidsfeltet ikke stadig kopieres. Derfor denne fil: hver test
kalder den faktiske funktion og maaler resultatet.

Fire defekter blev rettet samme dag, alle med samme form — et felt der blev
VIST som nutidstilstand uden at vaere maalt:

1. ``hours_since_last_session`` blev KOPIERET fra den forrige kapsel, saa den
   stod permanent paa 0.0. Hele wake-up-blokken sagde «Quick return (0 min
   since last session)» uanset hvor lang pausen var.
2. ``goals.active_goals`` blev vist, men ``list_active_goals()`` blev aldrig
   kaldt fra capsule-vejen.
3. ``somatic.*`` blev vist, men ``sensory_archive.list_recent()`` blev aldrig
   kaldt fra capsule-vejen.
4. ``goals.recent_completions`` blev altid sendt som en TOM liste — en
   konstant der lignede en maaling — og er derfor fjernet fra visningen.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

import core.services.continuity as c

# ``visible_runs`` skal importeres FOER ``visible_runs_memory``: sidstnaevnte
# importerer ``visible_runs`` paa modul-niveau, og den anden vej rundt rammer
# en delvist initialiseret modul (ImportError paa _maybe_trigger_continuation).
import core.services.visible_runs  # noqa: F401
import core.services.visible_runs_memory as vrm


@pytest.fixture
def capsule_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(c, "CAPSULE_DIR", tmp_path)
    monkeypatch.setattr(c, "CAPSULE_CURRENT", tmp_path / "session_capsule.json")
    monkeypatch.setattr(c, "CAPSULE_PREV", tmp_path / "session_capsule.prev.json")
    monkeypatch.setattr(c, "CAPSULE_OLDER", tmp_path / "session_capsule.older.json")
    return tmp_path


def _kapsel_med_pause(tidspunkt: object) -> dict:
    kapsel = dict(c._EMPTY_CAPSULE)
    kapsel["wake_provenance"] = {
        "previous_session_id": "chat-gammel",
        "previous_session_ended_at": tidspunkt,
        "hours_since_last_session": 0.0,  # den gamle, kopierede vaerdi
    }
    return kapsel


# ── 1. tidsfeltet: beregnes, kopieres ikke ────────────────────────────


def test_hours_since_beregnes_af_forrige_tidspunkt(capsule_dir):
    """Den gamle vaerdi var 0.0 — den nye skal vaere den FAKTISKE pause."""
    tre_timer_siden = datetime.now(UTC) - timedelta(hours=3)
    c.write_capsule(_kapsel_med_pause(tre_timer_siden.isoformat()))

    ny = c.capture_state(session_id="chat-ny")

    timer = ny["wake_provenance"]["hours_since_last_session"]
    assert timer is not None
    assert 2.9 < timer < 3.1, f"forventede ~3 timer, fik {timer}"


def test_hours_since_er_none_naar_tidspunktet_ikke_kan_parses(capsule_dir):
    """«Ikke maalt» er aerligt; et paastaaet nul er ikke.

    Foer faldt et uparsebart tidspunkt tilbage paa 0.0 — hvilket ville give
    «Quick return» om et vilkaarligt langt ophold.
    """
    c.write_capsule(_kapsel_med_pause("ikke-en-dato"))

    ny = c.capture_state(session_id="chat-ny")

    assert ny["wake_provenance"]["hours_since_last_session"] is None


def test_blokken_paastaar_ikke_nul_naar_pausen_ikke_er_maalt(capsule_dir):
    """Den viste header maa ikke sige «0 min» om en umaalt pause."""
    kapsel = dict(c._EMPTY_CAPSULE)
    kapsel["wake_provenance"] = {
        "previous_session_id": None,
        "previous_session_ended_at": None,
        "hours_since_last_session": None,
    }

    blok = c.build_wake_up_block(kapsel)

    assert blok is not None
    assert "0 min since last session" not in blok
    assert "pause ikke maalt" in blok


# ── 2. goals: tre udfald ──────────────────────────────────────────────


def test_goals_fra_aktive_maal_giver_de_faktiske_titler(monkeypatch):
    import core.services.long_horizon_goals as lhg

    monkeypatch.setattr(
        lhg,
        "list_active_goals",
        lambda limit=5: [{"title": "Ryd worktrees", "goal_id": "g1"}],
    )

    assert vrm._goals_fra_aktive_maal() == {
        "active_goals": [{"title": "Ryd worktrees", "id": "g1"}],
        "recent_completions": [],
    }


def test_goals_rydder_naar_der_er_maalt_og_tomt(monkeypatch):
    """Maalt tomt skal RYDDE feltet — ikke arve den forrige kapsels maal."""
    import core.services.long_horizon_goals as lhg

    monkeypatch.setattr(lhg, "list_active_goals", lambda limit=5: [])

    assert vrm._goals_fra_aktive_maal() == {
        "active_goals": [],
        "recent_completions": [],
    }


def test_goals_arver_naar_maalingen_fejler(monkeypatch):
    """En fejlet maaling er ikke et bevis for at der ingen maal er."""
    import core.services.long_horizon_goals as lhg

    def boom(**kwargs):
        raise RuntimeError("db nede")

    monkeypatch.setattr(lhg, "list_active_goals", boom)

    assert vrm._goals_fra_aktive_maal() is None


# ── 3. somatic: tre udfald ────────────────────────────────────────────


def test_somatic_læser_det_faktisk_sansede(monkeypatch):
    import core.services.sensory_archive as sa

    monkeypatch.setattr(
        sa,
        "list_recent",
        lambda **kwargs: [{"content": "gult aftenlys over skrivebordet", "modality": "visual"}],
    )

    resultat = vrm._somatic_fra_sansearkivet()

    assert resultat is not None
    assert resultat["last_visual"] == "gult aftenlys over skrivebordet"


def test_somatic_rydder_naar_arkivet_er_maalt_tomt(monkeypatch):
    import core.services.sensory_archive as sa

    monkeypatch.setattr(sa, "list_recent", lambda **kwargs: [])

    assert vrm._somatic_fra_sansearkivet() == {
        "last_visual": None,
        "last_audio": None,
        "atmosphere": None,
    }


def test_somatic_arver_naar_maalingen_fejler(monkeypatch):
    import core.services.sensory_archive as sa

    def boom(**kwargs):
        raise RuntimeError("arkiv nede")

    monkeypatch.setattr(sa, "list_recent", boom)

    assert vrm._somatic_fra_sansearkivet() is None


# ── 4. de felter der blev fjernet fra visningen ───────────────────────


def test_blokken_viser_ikke_de_umaalte_felter(capsule_dir):
    """open_thread, relation og recent_completions maa ikke vises som nutid.

    De havde ingen skriver (open_thread, relation) eller blev altid sendt som
    en tom liste (recent_completions). Et felt uden maaling hoerer ikke i
    visningen — det var praecis den fejlform hele dagen handlede om.
    """
    kapsel = dict(c._EMPTY_CAPSULE)
    kapsel["attention"] = dict(c._EMPTY_CAPSULE["attention"])
    kapsel["attention"]["open_thread"] = "en traad der aldrig blev maalt"
    kapsel["relation"] = dict(c._EMPTY_CAPSULE["relation"])
    kapsel["goals"] = {"active_goals": [], "recent_completions": ["noget gammelt"]}

    blok = c.build_wake_up_block(kapsel)

    assert blok is not None
    assert "Open thread" not in blok
    assert "Relationship" not in blok
    assert "Recent completions" not in blok
