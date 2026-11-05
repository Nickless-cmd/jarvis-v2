"""Trin 4+5 i eskaleringstrappen (besluttet 5/11-2026).

Trin 4 = «hold op, men vent på et skift». Trin 5 = «vend tilbage ved
stemningsskift». Testene her skal kunne skelne ``venter`` fra ``dismissed`` —
en grøn test der ikke kan det beviser intet, fordi forskellen mellem at give op
og holde døren åben netop ER tilstanden.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import nudge_broend as nb


@pytest.fixture()
def broend(monkeypatch):
    """Isoleret brønd i hukommelsen — ingen fil, ingen dual-write."""
    lager: list[dict] = []
    monkeypatch.setattr(nb, "_load", lambda: [dict(n) for n in lager])
    monkeypatch.setattr(nb, "_save", lambda x: lager.__setitem__(slice(None), [dict(n) for n in x]))
    monkeypatch.setattr("core.services.outbound_nudges.push_nudge", lambda **kw: None)
    return lager


def _skift(*, kind: str = "mood_shift", alder_timer: float = 0.0) -> dict:
    """Et percept i den form sensory_perception_bridge faktisk returnerer."""
    obs = datetime.now(UTC) - timedelta(hours=alder_timer)
    return {
        "change_type": "sensory-change-atmosphere",
        "salience": "high",
        "summary": "atmosfære-ændring: stemning skiftet fra roligt til mørkt",
        "observed_at": obs.isoformat(),
        "evidence": {"change_kind": kind, "mood_tone_now": "mørkt"},
    }


def test_nudge_der_rammer_loftet_ender_i_venter_og_forsvinder_ikke(broend):
    nid = nb.push(source="opvask", message="opvasken fra i går står stadig", emne="opvask")
    assert nb.mark_sent(nid) is True

    nid2 = nb.push(source="opvask", message="opvasken fra i går står stadig", emne="opvask")
    assert nb.mark_venter(nid2) is True

    n = nb.get(nid2)
    assert n["status"] == nb.STATUS_VENTER
    assert n["status"] != "dismissed"          # den er IKKE opgivet
    assert n["prik"] == 1
    assert n["trin"] == 4
    assert n["venter_siden"]
    # og den er ikke længere i den kø der bliver sagt
    assert nid2 not in [x["nudge_id"] for x in nb.list_pending()]
    # men den findes stadig som hvilende
    assert nid2 in [x["nudge_id"] for x in nb.list_ventende()]


def test_kadence_loftet_er_en_prik_pr_emne_pr_dag(broend):
    nid = nb.push(source="opvask", message="opvasken står stadig", emne="opvask")
    nb.mark_sent(nid)

    assert nb.kadence_tillader("opvask") is False
    assert nb.kadence_tillader("noget-andet") is True

    om_25_timer = datetime.now(UTC) + timedelta(hours=25)
    assert nb.kadence_tillader("opvask", nu=om_25_timer) is True


def test_ventende_nudge_genoptages_ikke_uden_et_registreret_skift(broend):
    nid = nb.push(source="opvask", message="opvasken står stadig", emne="opvask")
    nb.mark_venter(nid)

    assert nb.genoptag_ved_skift(None) == []
    assert nb.genoptag_ved_skift({}) == []
    # et percept uden sanse-change-type er ikke et skift
    assert nb.genoptag_ved_skift({"change_type": "tool-error", "observed_at": datetime.now(UTC).isoformat()}) == []
    # og nudgen står stadig i venter — intet blev flyttet
    assert nb.get(nid)["status"] == nb.STATUS_VENTER


def test_ventende_nudge_genoptages_ved_stemningsskift_som_nyt_tilbud(broend):
    nid = nb.push(source="opvask", message="opvasken står stadig", emne="opvask")
    nb.mark_venter(nid)

    flyttet = nb.genoptag_ved_skift(_skift(kind="mood_shift"))

    assert [n["nudge_id"] for n in flyttet] == [nid]
    n = nb.get(nid)
    assert n["status"] == "pending"
    assert n["trin"] == 5
    assert n["genoptaget_ved"]["change_kind"] == "mood_shift"
    # det er et TILBUD, ikke en gentagelse af den gamle besked
    assert "Skal vi tage den nu" in n["tilbud"]
    assert n["tilbud"] != n["message"]


def test_for_gammelt_skift_genoptager_ikke(broend):
    nid = nb.push(source="opvask", message="opvasken står stadig", emne="opvask")
    nb.mark_venter(nid)

    assert nb.genoptag_ved_skift(_skift(alder_timer=24 * 7)) == []
    assert nb.get(nid)["status"] == nb.STATUS_VENTER


def test_genoptagelse_respekterer_kadence_loftet(broend):
    """Et skift er ikke en fribillet: er emnet nævnt inden for et døgn, venter det."""
    nid = nb.push(source="opvask", message="opvasken står stadig", emne="opvask")
    nb.mark_sent(nid)          # sagt nu
    nid2 = nb.push(source="opvask", message="opvasken står stadig", emne="opvask")
    nb.mark_venter(nid2)

    assert nb.genoptag_ved_skift(_skift()) == []
    assert nb.get(nid2)["status"] == nb.STATUS_VENTER

    om_25_timer = datetime.now(UTC) + timedelta(hours=25)
    flyttet = nb.genoptag_ved_skift(_skift(), nu=om_25_timer)
    assert [n["nudge_id"] for n in flyttet] == [nid2]


def test_oprydning_kaster_ikke_hvilende_nudges_vaek(broend, monkeypatch):
    """En hvilende nudge er en åben dør — oprydning må ikke gøre trin 4 til tavshed."""
    monkeypatch.setattr(nb, "_MAX_NUDGES", 3)
    hvilende = nb.push(source="opvask", message="opvasken står stadig", emne="opvask")
    nb.mark_venter(hvilende)
    for i in range(5):
        nid = nb.push(source=f"k{i}", message=f"noget nyt {i}", emne=f"k{i}")
        nb.mark_sent(nid)

    ids = [n["nudge_id"] for n in broend]
    assert hvilende in ids
    assert nb.get(hvilende)["status"] == nb.STATUS_VENTER


def test_emne_nogle_udledes_naar_kalderen_ikke_giver_en(broend):
    nid = nb.push(source="freetheai_checkin", message="der er nyt indhold klar til dig")
    n = nb.get(nid)
    assert n["emne"].startswith("freetheai_checkin:")
    assert "indhold" in n["emne"]
