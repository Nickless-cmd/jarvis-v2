"""Agent Smith må håndhæve Jarvis' løfter — ikke opfinde dem ud fra hyppighed.

MÅLT I PRODUKTION 19. aug 2026, med `gate_enforce.agent_smith` = enabled:
Smith var klatret til Trin 2 og 3 på danske FUNKTIONSORD og havde tre AKTIVE direktiver
på prioritet 85:

    "Stop med at gentage frasen «og det er» — Agent Smith har målt den 15× …"
    "Stop med at gentage frasen «det er en» …"
    "Stop med at gentage frasen «det er ikke» …"

plus en aktiv standing-order der afbrød ham i realtid før tool-exec. Man kan ikke tale
dansk uden de ord. Årsagen: `_may_escalate` accepterede et drift-signal alene, og
`_is_spike` er blind for hvad mønsteret ER — "det er den" gik fra 13 til 18 forekomster
og talte som drift.

Fixet følger `docs/superpowers/specs/2026-07-11-agent-smith-detector-fix.md` krav 1:
berettigelse FØR drift.
"""
from __future__ import annotations

import core.services.central_agent_smith_escalation as e
from core.services.central_agent_smith_escalation import (
    _is_self_bound,
    _may_escalate,
    default_config,
)


def _cfg(**kw):
    c = default_config()
    c.update(kw)
    return c


class TestFunktionsordKanAldrigKlatre:
    """Regressions-testen for det der faktisk skete."""

    def test_de_tre_faktiske_direktiver_ville_ikke_opstaa_igen(self):
        cfg = _cfg(self_commitments=[])
        for frase in ("det er ikke", "det er en", "og det er", "det er den", "det er det"):
            pat = {"baseline": 13.0}
            may, why = _may_escalate(pat, 18.0, f"phrase:{frase}", {}, cfg)
            assert may is False, f"{frase!r} måtte ikke klatre"
            assert why == "not_self_bound"

    def test_spike_alene_er_ikke_nok_laengere(self):
        """Sprogvariation ligner drift. Den må ikke være adgangsbillet."""
        cfg = _cfg(self_commitments=[])
        may, why = _may_escalate({"baseline": 3.0}, 300.0, "phrase:i stedet for", {}, cfg)
        assert may is False and why == "not_self_bound"

    def test_generisk_arbejde_klatrer_ikke(self):
        cfg = _cfg(self_commitments=[])
        may, _ = _may_escalate({"baseline": 8.0}, 40.0,
                               "seq:propose workspace memory update", {}, cfg)
        assert may is False


class TestJarvisEgneLoefterHaandhaeves:
    def test_selv_bundet_moenster_maa_klatre_ved_drift(self):
        """'vil du have' var en ÆGTE fangst — fordi Jarvis selv havde mintet en beslutning."""
        cfg = _cfg(self_commitments=["vil du have"])
        may, why = _may_escalate({"baseline": 5.0}, 14.0, "phrase:vil du have", {}, cfg)
        assert may is True and why == "spike"

    def test_selv_bundet_men_jaevn_bliver_paa_trin_1(self):
        cfg = _cfg(self_commitments=["vil du have"])
        may, why = _may_escalate({"baseline": 14.0}, 14.0, "phrase:vil du have", {}, cfg)
        assert may is False and why == "benign_steady"

    def test_delvist_match_taeller(self):
        cfg = _cfg(self_commitments=["stop med at spørge vil du have"])
        assert _is_self_bound("phrase:vil du have", {}, cfg) is True

    def test_entry_flag_kan_ogsaa_binde(self):
        assert _is_self_bound("phrase:hvad som helst", {"self_bound": True}, _cfg()) is True


class TestRisikableHandlingerUndtages:
    def test_risikabel_handling_klatrer_uden_loefte(self):
        """En destruktiv handling behøver ingen forudgående beslutning."""
        cfg = _cfg(self_commitments=[])
        may, why = _may_escalate({"baseline": 1.0}, 2.0,
                                 "seq:delete workspace memory line", {}, cfg)
        assert may is True and why == "risky"

    def test_corroboration_kraever_stadig_berettigelse(self):
        """Et andet værn kan bekræfte AKTIVITET — det gør den ikke uønsket."""
        cfg = _cfg(self_commitments=[])
        may, why = _may_escalate({"baseline": 10.0}, 11.0, "phrase:det er ikke",
                                 {"corroborated": True}, cfg)
        assert may is False and why == "not_self_bound"

    def test_corroboration_virker_naar_moensteret_er_bundet(self):
        cfg = _cfg(self_commitments=["vil du have"])
        may, why = _may_escalate({"baseline": 10.0}, 10.0, "phrase:vil du have",
                                 {"corroborated": True}, cfg)
        assert may is True and why == "corroborated"


class TestIngenSelvbekraeftendeLoekke:
    def test_smiths_egne_mints_maa_ikke_taelle_som_loefte(self):
        """Han mintede «stop det er ikke» og havde derefter et 'commitment' at håndhæve.

        I/O-laget filtrerer på source_type != 'agent_smith'; her sikres at den rene
        funktion ikke selv opfinder en binding ud af ingenting.
        """
        cfg = _cfg(self_commitments=[])
        assert _is_self_bound("phrase:det er ikke", {}, cfg) is False

    def test_tom_konfiguration_er_det_sikre_udgangspunkt(self):
        assert default_config()["self_commitments"] == []


class TestTavshedVedUberettigetMoenster:
    """Efter eskalerings-gaten kommenterede Smith stadig på funktionsord i hver prompt:
    "Mr. Anderson... du gentager «det er ikke». Jeg finder det forudsigeligt. Varier."
    Han bandt ikke længere — men han hakkede. Tavshed er den rigtige adfærd."""

    def _det(self, label, **extra):
        from core.services.central_agent_smith_escalation import pattern_key
        return {pattern_key("phrase", label): {"kind": "phrase", "label": label,
                                               "metric": 18.0, **extra}}

    def test_funktionsord_giver_INGEN_stemme(self):
        from core.services.central_agent_smith_escalation import step_escalation
        st, acts = step_escalation(None, self._det("det er ikke"), "t0",
                                   _cfg(self_commitments=[]))
        assert [a for a in acts if a.get("type") == "voice"] == []
        assert st.get("patterns") == {}, "uberettiget mønster skal ikke engang spores"

    def test_selv_bundet_moenster_faar_stemme(self):
        from core.services.central_agent_smith_escalation import step_escalation
        _, acts = step_escalation(None, self._det("vil du have"), "t0",
                                  _cfg(self_commitments=["vil du have"]))
        assert [a for a in acts if a.get("type") == "voice"], "hans egne løfter skal høres"

    def test_risikabel_handling_faar_stemme_uden_loefte(self):
        from core.services.central_agent_smith_escalation import pattern_key, step_escalation
        det = {pattern_key("seq", "delete workspace memory line"): {
            "kind": "seq", "label": "delete workspace memory line", "metric": 3.0}}
        _, acts = step_escalation(None, det, "t0", _cfg(self_commitments=[]))
        assert [a for a in acts if a.get("type") == "voice"]


# ── Loft på øverste trin, 05-09-2026 ────────────────────────────────────────
# Fundet live: «delete workspace memory line» stod på Trin 3 med 200 cyklusser
# — siden 19. august. Metrikken faldt aldrig under compliance-grænsen, så stigen
# kunne hverken løse det eller slippe det. 200 cyklusser à ~3 timer er 25 døgn.

def _pinned_state(cycles: int) -> dict:
    return {"patterns": {"seq:x": {
        "kind": "seq", "label": "x", "rung": e.RUNG_CONFRONT,
        "first_seen": "2026-08-19T00:00:00+00:00", "last_seen": "2026-08-19T00:00:00+00:00",
        "baseline": 3.0, "last_metric": 3.0, "cycles_at_rung": cycles,
        "decision_id": "d1", "standing_order_id": "so1", "history": [],
    }}}


def test_et_uflytteligt_moenster_slippes_til_sidst():
    st, acts = e.step_escalation(
        _pinned_state(e._CONFRONT_GIVE_UP_CYCLES + 1),
        {"seq:x": {"kind": "seq", "label": "x", "metric": 3.0, "corroborated": True}},
        "2026-09-05T00:00:00+00:00")
    assert "seq:x" not in st["patterns"]
    assert any(a["type"] == "observe" and a.get("reason") == "unmovable" for a in acts)


def test_opgivelsen_pensionerer_direktiv_OG_standing_order():
    """Ellers bliver der et forældet håndhævelses-spor tilbage — en landmine
    den dag håndhævelse tændes."""
    _, acts = e.step_escalation(
        _pinned_state(e._CONFRONT_GIVE_UP_CYCLES + 1),
        {"seq:x": {"kind": "seq", "label": "x", "metric": 3.0, "corroborated": True}},
        "2026-09-05T00:00:00+00:00")
    assert any(a["type"] == "revoke" for a in acts)
    assert any(a["type"] == "deactivate_order" for a in acts)


def test_han_lyver_ikke_om_at_have_vundet():
    _, acts = e.step_escalation(
        _pinned_state(e._CONFRONT_GIVE_UP_CYCLES + 1),
        {"seq:x": {"kind": "seq", "label": "x", "metric": 3.0, "corroborated": True}},
        "2026-09-05T00:00:00+00:00")
    line = next(a["line"] for a in acts if a["type"] == "voice")
    assert "Endelig" not in line
    assert "slipper det" in line


def test_under_loftet_bliver_han_staaende():
    st, _ = e.step_escalation(
        _pinned_state(2),
        {"seq:x": {"kind": "seq", "label": "x", "metric": 3.0, "corroborated": True}},
        "2026-09-05T00:00:00+00:00")
    assert st["patterns"]["seq:x"]["rung"] == e.RUNG_CONFRONT


def test_compliance_gaar_stadig_forud_for_opgivelse():
    """Falder metrikken, er det en SEJR — ikke en opgivelse, uanset cyklusser."""
    _, acts = e.step_escalation(
        _pinned_state(e._CONFRONT_GIVE_UP_CYCLES + 1),
        {"seq:x": {"kind": "seq", "label": "x", "metric": 0.5, "corroborated": True}},
        "2026-09-05T00:00:00+00:00")
    assert any(a.get("reason") == "weakened" for a in acts)
    assert not any(a.get("reason") == "unmovable" for a in acts)


def test_en_maalt_adfaerd_overlever_Trin_1_porten():
    """Porten findes for at stoppe opfundne «stop X» fra ordhyppighed. Et mønster
    et andet værn HAR målt er ikke en opfindelse — ellers ville Smiths nye øjne
    være inerte, fordi «tomme løfter» hverken er et risikabelt ord eller et løfte
    Jarvis selv har formuleret."""
    st, acts = e.step_escalation(
        None,
        {"behaviour:tomme løfter": {"kind": "behaviour", "label": "tomme løfter",
                                    "metric": 31.0, "corroborated": True}},
        "2026-09-05T00:00:00+00:00")
    assert "behaviour:tomme løfter" in st["patterns"]


def test_en_ren_frase_overlever_stadig_IKKE_porten():
    """August-fejlen må ikke kunne komme tilbage ad den vej."""
    st, _ = e.step_escalation(
        None,
        {"phrase:det er ikke": {"kind": "phrase", "label": "det er ikke", "metric": 15.0}},
        "2026-09-05T00:00:00+00:00")
    assert st["patterns"] == {}
