"""En manglende `active`-nøgle blev læst som en påstand om at systemet var dødt.

`cognitive_architecture_surface.py:37` gør `result.get("active", False)`.
Målt 25/9-2026 manglede tre af de 71 kognitive flader nøglen — og to af dem
arbejdede:

  * `cognitive_core_experiments` meldte `activity_state: "active"` med **3 af 5**
    undersystemer aktive.
  * `life_phase` returnerede en rigtig fase: «Refleksion — ikke hvad der gik
    godt/skidt, men hvad der forskubbede sig».
  * `learning_curriculum` var reelt tom — men sagde det ved et tilfælde.

Et fravær er ikke en måling. Det blev læst som én.
"""
from __future__ import annotations


def _flader() -> dict:
    from core.services.cognitive_core_experiments import (
        build_cognitive_core_experiments_surface,
    )
    from core.services.heartbeat_runtime import _build_cognitive_surfaces
    f = _build_cognitive_surfaces()
    f["cognitive_core_experiments"] = build_cognitive_core_experiments_surface()
    return f


def test_HVER_kognitiv_flade_siger_om_den_er_aktiv():
    """DEN vagt. Uden den kan en ny flade melde sig død ved at tie."""
    uden = sorted(navn for navn, r in _flader().items()
                  if isinstance(r, dict) and "active" not in r)
    assert not uden, (
        "disse flader siger ikke om de er aktive, og "
        "`cognitive_architecture_surface` laeser derfor False:\n  " + "\n  ".join(uden))


def test_forsoegsfladen_er_aktiv_naar_dens_undersystemer_er_det():
    """Den meldte sig død med 3 af 5 kørende."""
    from core.services.cognitive_core_experiments import (
        build_cognitive_core_experiments_surface,
    )
    u = build_cognitive_core_experiments_surface()
    assert u["active"] == (u["activity_state"] == "active")
    if u["active_count"] > 0:
        assert u["active"] is True


def test_livsfasen_er_altid_aktiv():
    """Den har altid et indhold — en fase, en beskrivelse, et dybde-spørgsmål."""
    from core.services.living_heartbeat_cycle import determine_life_phase
    for time in (3, 9, 14, 21):
        fase = determine_life_phase(hour=time)
        assert fase["active"] is True
        assert fase["phase"] and fase["description"]


def test_et_tomt_pensum_siger_HVORFOR_frem_for_at_tie():
    """«Tom» og «siger ikke noget» må ikke se ens ud. Den ene er en måling.

    Testen stod før som `u["active"] == bool(u["curriculum"])`. Den halvdel
    var rigtig — nøglen SKAL være der — men den koblede livstegnet til
    indholdet, og `cognitive_architecture_surface` læser `active` som «systemet
    lever». En plan uden materiale meldte sig derfor død.

    Nu måles begge dele hver for sig: nøglen findes OG summaryen siger hvorfor
    planen er tom. Målt 25/9-2026 over alle 1007 versioner af
    personlighedsvektoren: `confidence_by_domain` er ikke-tom i 1,
    `recurring_mistakes` i 0 — mens `learned_preferences`, samme skrivevej, er
    fyldt i 728.
    """
    from core.services.self_experiments import generate_learning_curriculum
    u = generate_learning_curriculum()
    assert "active" in u
    assert u["active"] is True
    assert u["summary"], "en tom plan skal stadig sige noget"
    if not u["curriculum"]:
        assert "Ingen plan" in u["summary"]
