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


def test_partial_surfaces_baseline_every_successfully_read_signal(isolated_runtime):
    """Fallback-læste signaler skal indgå i dommerens egen reference.

    Fjerner man ``ok_signals.add(name)`` fra den vellykkede fallback-gren,
    indeholder referencen kun det ene injicerede surface, og ændringer i de
    øvrige seks kan aldrig bidrage til ``movement_total``.
    """
    from core.runtime import db_core
    from core.services import central_convene_judge as j

    fallback_surfaces = _surfaces()

    def _read(name):
        return fallback_surfaces.get(name, {})

    j.reset_reference()
    with _mode("on"), patch(
        "core.services.signal_surface_router.read_surface", side_effect=_read
    ):
        first = j.judge_convene(
            surfaces={"existential_wonder": {"latest_wonder": "x"}},
            top_signals=["existential_wonder"],
            score=0.0,
        )

        reference = db_core.get_runtime_state_value(j._PREV_LEVELS_KEY, None)
        assert reference == {
            "autonomy_pressure": 0.0,
            "open_loop": 0.0,
            "internal_opposition": 0.0,
            "existential_wonder": 1.0,
            "creative_drift": 0.0,
            "desire": 0.0,
            "conflict": 0.0,
        }
        assert first["movement_total"] == 0.0

        fallback_surfaces["autonomy_pressure"] = {
            "summary": {"active_count": 3}
        }
        second = j.judge_convene(
            surfaces={"existential_wonder": {"latest_wonder": "x"}},
            top_signals=["existential_wonder"],
            score=0.0,
        )

    assert second["movement_total"] > 0.0


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


# ---------------------------------------------------------------------------
# Alders-vægtning af de binære signaler (14/11-2026)
# ---------------------------------------------------------------------------


def _iso(minutter_siden: float) -> str:
    from datetime import UTC, datetime, timedelta

    return (datetime.now(UTC) - timedelta(minutes=minutter_siden)).isoformat()


def test_frisk_undren_vejer_tungere_end_en_gammel():
    """MÅLT 14/11-2026: `conflict` og `existential_wonder` stod på 1.0 i alle
    500 samples over seks døgn — reglen var `1.0 if <streng> else 0.0`, så en
    konflikt fra kl. 05:56 talte lige så meget kl. 14.

    Uden denne test kan alders-vægtningen fjernes igen uden at nogen ser det,
    og dommeren er tilbage til at måle tilstedeværelse i stedet for bevægelse.
    """
    from core.services import central_convene_judge as j

    frisk = j._movement_from_signal(
        "conflict", {"last_conflict": "spænding", "generated_at": _iso(5)}
    )
    gammel = j._movement_from_signal(
        "conflict", {"last_conflict": "spænding", "generated_at": _iso(60 * 8)}
    )
    assert frisk > 0.9, f"en konflikt fra 5 min siden skal veje næsten fuldt, fik {frisk}"
    assert gammel == 0.0, f"en konflikt fra 8 timer skal være faldet til nul, fik {gammel}"
    assert frisk > gammel

    wonder_frisk = j._movement_from_signal(
        "existential_wonder", {"latest_wonder": "Hvem er jeg?", "last_generated_at": _iso(5)}
    )
    wonder_gammel = j._movement_from_signal(
        "existential_wonder",
        {"latest_wonder": "Hvem er jeg?", "last_generated_at": _iso(60 * 8)},
    )
    assert wonder_frisk > 0.9
    assert wonder_gammel == 0.0


def test_manglende_tidsstempel_falder_tilbage_paa_binaer():
    """Bagudkompatibilitet: en surface UDEN tidsstempel må ikke blive nul.

    Et signal der forsvinder fordi kilden ikke leverer en tid ville se ud som et
    fald på 1.0 — det største mulige — og udløse en indkaldelse netop når kilden
    er ufuldstændig. Derfor falder vi tilbage til den gamle regel.
    """
    from core.services import central_convene_judge as j

    assert j._movement_from_signal("conflict", {"last_conflict": "noget"}) == 1.0
    assert j._movement_from_signal("existential_wonder", {"latest_wonder": "noget"}) == 1.0


def test_tomt_indhold_er_nul_uanset_tidsstempel():
    """En frisk tid uden indhold er ikke et signal."""
    from core.services import central_convene_judge as j

    assert j._movement_from_signal("conflict", {"last_conflict": "", "generated_at": _iso(1)}) == 0.0
    assert (
        j._movement_from_signal(
            "existential_wonder", {"latest_wonder": "", "last_generated_at": _iso(1)}
        )
        == 0.0
    )


def test_en_ny_post_loefter_movement_total_over_taersklen():
    """Den ægte ende-til-ende: en frisk post SKAL kunne udløse dommeren.

    Før rettelsen var niveauet konstant 1.0, så deltaet var 0 i alle samples og
    dommeren kunne aldrig sige ja. Her måles det mod den rigtige tærskel.
    """
    from core.services import central_convene_judge as j

    def _surfaces(**over):
        base = {
            "autonomy_pressure": {"summary": {"active_count": 0}},
            "open_loop": {"summary": {"open_count": 0}},
            "internal_opposition": {"active": False},
            "existential_wonder": {"latest_wonder": "", "last_generated_at": ""},
            "creative_drift": {"drift_count_today": 0},
            "desire": {"active_count": 0},
            "conflict": {"last_conflict": "", "generated_at": ""},
            "affective_meta_state": {"mood": "steady"},
        }
        base.update(over)
        return base

    surfaces = _surfaces()

    def _read(name):
        return surfaces.get(name, {})

    from unittest.mock import patch

    j.reset_reference()
    with _mode("on"), patch(
        "core.services.signal_surface_router.read_surface", side_effect=_read
    ):
        foer = j.judge_convene(surfaces=surfaces, top_signals=[], score=0.0)
        assert foer["convene"] is False

        # En konflikt opstår NU.
        surfaces["conflict"] = {"last_conflict": "spænding 1.0", "generated_at": _iso(0)}
        efter = j.judge_convene(surfaces=surfaces, top_signals=[], score=0.0)

    assert efter["movement_total"] >= j._MOVEMENT_THRESHOLD, (
        f"en ny konflikt skal kunne løfte bevægelsen over tærsklen "
        f"{j._MOVEMENT_THRESHOLD}, fik {efter['movement_total']}"
    )
    assert efter["convene"] is True
