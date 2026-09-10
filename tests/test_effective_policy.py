"""Hvad GJALDT der for koerslen — Fase 9.

MAALT 10/9-2026 foer bygningen: `visible_runs` har 13 kolonner og `agent_runs`
19, og ikke ét politik-felt imellem dem. Ingen koersel kunne bagefter sige
hvilke vaerktoejer den saa, om den var autonom, eller om bash var i sandkasse.

Det er ikke bogholderi. Det er den observabilitet der goer dagens hyppigste
fejlklasse synlig: et barn i en bar traad mister tavst sit vaerktoejs-scope og
sin autonomi, og BEGGE tab peger i den farlige retning — tomt scope betyder
«unbound legacy» (ser alt), og tabt autonomi fjerner sandkasse-kravet for bash.
Uden et oejebliksbillede pr. koersel kunne det kun bevises med en
subproces-test.
"""
from __future__ import annotations

from core.services.effective_policy import SKEMA_VERSION, afviger, snapshot


def test_tomt_scope_kaldes_ved_sit_rigtige_navn():
    """Tomt scope er IKKE «ingen adgang». Det er «unbound legacy» og ser ALT.
    En flade der laeser tomheden som en begraensning ville vende betydningen
    paa hovedet, saa den staar skrevet."""
    from core.tools.tool_scoping import _scope_var

    polet = _scope_var.set("")
    try:
        s = snapshot()
        assert s["tool_scope"] == ""
        assert "unbound" in s["tool_scope_betydning"]
    finally:
        _scope_var.reset(polet)

    polet = _scope_var.set("agent")
    try:
        assert snapshot()["tool_scope_betydning"] == "afgraenset"
    finally:
        _scope_var.reset(polet)


def test_anmodet_og_faktisk_sandkasse_er_to_felter():
    """Kriterium 7. Sandkassen har to sandheder: om den er slaaet til, og om
    den faktisk blev KRAEVET for dette kald (`is_autonomous() and taendt`).
    En profil der kun viste den ene ville lyve."""
    s = snapshot()
    assert "sandkasse_taendt" in s and "sandkasse_kraevet" in s
    if s["sandkasse_taendt"] is not None and s["autonom"] is not None:
        assert s["sandkasse_kraevet"] == bool(s["sandkasse_taendt"] and s["autonom"])


def test_samme_politik_giver_samme_hash():
    from core.tools.tool_scoping import _scope_var

    polet = _scope_var.set("agent")
    try:
        a, b = snapshot(), snapshot()
        assert a["policy_hash"] == b["policy_hash"]
    finally:
        _scope_var.reset(polet)


def test_aendret_politik_aendrer_hash_og_kan_forklares():
    from core.tools.tool_scoping import _scope_var

    polet = _scope_var.set("agent")
    try:
        a = snapshot()
    finally:
        _scope_var.reset(polet)
    b = snapshot()                      # tomt scope = unbound legacy

    assert a["policy_hash"] != b["policy_hash"], (
        "en UDVIDELSE af adgangen aendrede ikke hashen — saa kan et tab af "
        "scope ikke ses i data")
    forskelle = afviger(a, b)
    assert any("tool_scope" in f for f in forskelle), forskelle


def test_snapshot_kaster_aldrig(monkeypatch):
    """En manglende maaling bliver `None`, ikke en fejl — og ikke `False`.
    Et ukendt felt maa ikke forveksles med et maalt «nej»."""
    import core.services.effective_policy as ep

    monkeypatch.setattr(ep, "_tool_scope", lambda: (_ for _ in ()).throw(RuntimeError("x")))
    try:
        s = snapshot()
    except Exception as exc:                      # pragma: no cover
        raise AssertionError(f"snapshot kastede: {exc}") from exc
    assert s["skema_version"] == SKEMA_VERSION


def test_koerslen_baerer_politikken_og_fladen_viser_den(isolated_runtime):
    """Skrive- OG laeseside. En kolonne ingen kan laese er den fejl jeg har
    lavet tre gange i dag (`kind`, `runtime_owner`, og naesten denne)."""
    import core.runtime.db_agent_runtime as db
    from core.services.agent_runtime_surfaces import build_agent_detail_surface

    db.create_agent_registry_entry(agent_id="a", role="r", goal="g")
    db.create_agent_run(run_id="r1", agent_id="a", status="completed")

    raekke = db.get_agent_run("r1")
    assert raekke["policy_hash"], "koerslen fik ingen politik-hash"
    assert raekke["policy"]["skema_version"] == SKEMA_VERSION
    assert "tool_scope" in raekke["policy"]

    flade = build_agent_detail_surface("a") or {}
    assert flade["policy_hash"] == raekke["policy_hash"], (
        "politikken staar i DB'en men naar ikke fladen — endnu et lag ingen "
        "kan se")
    assert flade["effective_policy"]["tool_scope_betydning"]
