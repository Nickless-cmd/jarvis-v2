"""Tests for central_convene_judge — the Central reason-to-convene judge (akse 4).

Hermetic: the mode flag (kv) and surface reads are patched, so no DB / real
surfaces are touched. Covers off/shadow/on governance, movement detection,
dynamic role derivation, topic-hint derivation, and self-safety."""
from __future__ import annotations

from unittest.mock import patch


def _mode(m):
    return patch("core.services.central_convene_judge.current_mode", return_value=m)


# ---------------------------------------------------------------------------
# Governance — flag off/shadow/on
# ---------------------------------------------------------------------------


def test_off_returns_benign_verdict_and_derives_nothing():
    from core.services import central_convene_judge as j
    with _mode("off"):
        v = j.judge_convene(surfaces=None, top_signals=["x"], score=0.9, score_override=0.9)
    assert v["mode"] == "off"
    assert v["convene"] is False
    assert v["roles"] == []
    assert v["topic_hint"] == ""


def test_shadow_computes_but_reports_shadow_mode():
    from core.services import central_convene_judge as j
    with _mode("shadow"):
        v = j.judge_convene(surfaces=None, top_signals=[], score=0.0, score_override=0.9)
    assert v["mode"] == "shadow"
    assert v["convene"] is True          # movement above threshold
    assert v["roles"] == []              # 15. jul: dommeren foreskriver ALDRIG roller (nudge, ikke ordre)


def test_on_convenes_above_movement_threshold():
    from core.services import central_convene_judge as j
    with _mode("on"):
        v = j.judge_convene(surfaces=None, top_signals=[], score=0.0, score_override=0.5)
    assert v["mode"] == "on"
    assert v["convene"] is True
    assert v["reason"] == "real_movement"


def test_on_no_convene_below_movement_threshold():
    from core.services import central_convene_judge as j
    with _mode("on"):
        v = j.judge_convene(surfaces=None, top_signals=[], score=0.0, score_override=0.05)
    assert v["convene"] is False
    assert v["reason"] == "no_real_movement"


# ---------------------------------------------------------------------------
# Reads the flowing values — surfaces + valence + agenda
# ---------------------------------------------------------------------------


def _surfaces(**over):
    base = {
        "autonomy_pressure": {"summary": {"active_count": 0}},
        "open_loop": {"summary": {"open_count": 0}},
        "internal_opposition": {"active": False},
        "existential_wonder": {"latest_wonder": ""},
        "creative_drift": {"drift_count_today": 0},
        "desire": {"active_count": 0},
        "conflict": {"last_conflict": ""},
        "affective_meta_state": {"mood": "steady"},
    }
    base.update(over)
    return base


def test_reads_movement_from_provided_surfaces():
    """Dommeren måler ÆNDRING, ikke tilstedeværelse (rettet 30/10-2026).

    MÅLT FØR: fire signaler stod konstant på 1.0 fordi de målte om en streng var
    ikke-tom — `conflict` var 1.0 så længe `last_conflict` havde en værdi, også
    timer efter konflikten. `movement_total` var derfor 4.0 i 40 af 40 samples
    og dommeren indkaldte rådet hver gang uden at noget flyttede sig.

    Kontrakten er nu: første aflæsning etablerer referencen (0), og kun en
    faktisk ændring bærer bevægelse. Testen værner det samme som før — at
    surfaces faktisk LÆSES og at emne-hintet bæres.
    """
    from core.services import central_convene_judge as j
    surfaces = _surfaces(
        existential_wonder={"latest_wonder": ""},
        autonomy_pressure={"summary": {"active_count": 0}},
    )

    def _read(name):
        return surfaces.get(name, {})

    j.reset_reference()
    with _mode("on"), patch(
        "core.services.signal_surface_router.read_surface", side_effect=_read
    ):
        foer = j.judge_convene(surfaces=surfaces, top_signals=[], score=0.0)
        assert foer["convene"] is False, "første aflæsning etablerer kun referencen"
        assert foer["movement_total"] == 0.0

        # Nu BEVÆGER to signaler sig.
        surfaces["existential_wonder"] = {"latest_wonder": "Hvem er jeg når ingen ser?"}
        surfaces["autonomy_pressure"] = {"summary": {"active_count": 3}}
        efter = j.judge_convene(surfaces=surfaces, top_signals=[], score=0.0)
    assert efter["convene"] is True
    assert efter["movement_total"] > 0.0
    # existential_wonder present → topic hint is the wonder text itself
    assert efter["topic_hint"] == "Hvem er jeg når ingen ser?"
    j.reset_reference()


def test_judge_nudges_topic_but_prescribes_no_roles():
    """15. jul (Bjørn): dommeren er en NUDGE — den detekterer bevægelse + emne, men
    FORESKRIVER ALDRIG roller. Jarvis konstruerer selv rollerne per-emne i convene_council
    (Claudes model). Ingen låst signal→rolle-tabel."""
    from core.services import central_convene_judge as j
    surfaces = _surfaces(
        existential_wonder={"latest_wonder": ""},
        conflict={"last_conflict": ""},
    )

    def _read(name):
        return surfaces.get(name, {})

    j.reset_reference()
    with _mode("on"), patch(
        "core.services.signal_surface_router.read_surface", side_effect=_read
    ):
        j.judge_convene(surfaces=surfaces, top_signals=[], score=0.0)
        # Ændringen er det der bærer bevægelsen (ikke tilstedeværelsen alene).
        surfaces["existential_wonder"] = {"latest_wonder": "Hvem er jeg?"}
        surfaces["conflict"] = {"last_conflict": "spænding"}
        v = j.judge_convene(surfaces=surfaces, top_signals=[], score=0.0)
    assert v["convene"] is True            # bevægelse → tilbud til Jarvis
    assert v["roles"] == []                # men INGEN foreskrevne roller
    assert v["topic_hint"]                 # emne-hint bæres (det nudgen tilbyder)
    j.reset_reference()


def test_no_role_derivation_symbols_remain():
    """Tabel-udledningen er fjernet — ingen _derive_roles / _SIGNAL_PERSPECTIVES."""
    from core.services import central_convene_judge as j
    assert not hasattr(j, "_derive_roles")
    assert not hasattr(j, "_SIGNAL_PERSPECTIVES")


# ---------------------------------------------------------------------------
# Self-safety
# ---------------------------------------------------------------------------


def test_self_safe_when_surface_read_raises():
    from core.services import central_convene_judge as j
    with _mode("on"), patch(
        "core.services.signal_surface_router.read_surface",
        side_effect=RuntimeError("boom"),
    ):
        v = j.judge_convene(surfaces=None, top_signals=["a"], score=0.0)
    # movement reads swallow the error → no real movement → benign no-convene
    assert v["convene"] is False


def test_current_mode_defaults_off(monkeypatch):
    from core.services import central_convene_judge as j
    monkeypatch.setattr(j, "_kv_get", lambda k, d: "off")
    assert j.current_mode() == "off"
    monkeypatch.setattr(j, "_kv_get", lambda k, d: "bogus")
    assert j.current_mode() == "off"
    monkeypatch.setattr(j, "_kv_get", lambda k, d: "shadow")
    assert j.current_mode() == "shadow"


# ---------------------------------------------------------------------------
# `on` findes ikke laengere som tilstand (7/10-2026)
# ---------------------------------------------------------------------------

def test_gemt_on_laeses_som_shadow():
    """Flaget stod paa "on" i produktion da aktoeren blev fjernet.

    `on` betoed «dommeren afgoer indkaldelse», og den der skulle HANDLE var
    `autonomous_council_daemon`. Den gik ud af den ubetingede liste 15/9-2026,
    og raads-taellerne viser netop den dag som sidste raad. Oversaettelsen her
    er derfor adfaerds-neutral — men den fjerner paastanden om en aktoer der
    ikke findes, saa ingen kan wire noget til et mode der ikke virker.
    """
    from unittest.mock import patch

    from core.services import central_convene_judge as j

    with patch.object(j, "_kv_get", return_value="on"):
        assert j.current_mode() == "shadow"
    with patch.object(j, "_kv_get", return_value="ON"):
        assert j.current_mode() == "shadow", "store bogstaver skal ogsaa fanges"
    with patch.object(j, "_kv_get", return_value="shadow"):
        assert j.current_mode() == "shadow"
    with patch.object(j, "_kv_get", return_value="off"):
        assert j.current_mode() == "off"
    with patch.object(j, "_kv_get", return_value="noget-andet"):
        assert j.current_mode() == "off", "ukendt vaerdi skal falde til off"
