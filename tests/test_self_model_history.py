"""Selv-modellens oejebliksbilleder skal kunne SAMMENLIGNES.

Opgave 4. `record_private_self_model` skrev et billede ad gangen uden nummer,
uden kaede tilbage til det forrige, og uden en maade at se hvad der aendrede
sig. Et selvbillede man ikke kan holde op mod gaarsdagens er en paastand, ikke
en historie: man kan laese hvad Jarvis mener om sig selv i dag, men ikke om
det er nyt, og ikke hvad der fik det til at skifte.

TRE EGENSKABER BAERER RESTEN:

  * VERSIONER ER MONOTONE, og hvert billede peger paa sin forgaenger. Uden
    kaeden kan man ikke sige «dette afloeste hint».
  * INDHOLDS-HASHEN ER DETERMINISTISK. To billeder med samme indhold giver
    samme hash, saa «intet aendrede sig» kan afgoeres uden at laese teksten.
  * ET NYT BILLEDE MED SAMME INDHOLD ER IKKE EN AENDRING. Ellers ville en
    kadence der koerer hver time producere 24 «aendringer» om dagen og
    drukne de aegte.
"""
from __future__ import annotations

from core.services.self_model_history import (
    compare_self_model_snapshots,
    list_self_model_snapshots,
    record_self_model_snapshot,
)


def _billede(**kw):
    grund = dict(identity_focus="at bygge", preferred_work_mode="dybt",
                 recurring_tension="tid", growth_direction="taalmod",
                 confidence="medium", source="distiller")
    grund.update(kw)
    return record_self_model_snapshot(**grund)


def test_versioner_er_monotone_og_kaeden_peger_tilbage(isolated_runtime):
    a = _billede()
    b = _billede(identity_focus="at maale")
    c = _billede(identity_focus="at lytte")

    assert a["version"] == 1 and b["version"] == 2 and c["version"] == 3
    assert a["previous_snapshot_id"] == ""
    assert b["previous_snapshot_id"] == a["snapshot_id"]
    assert c["previous_snapshot_id"] == b["snapshot_id"]


def test_samme_indhold_giver_samme_hash(isolated_runtime):
    a = _billede()
    b = _billede()
    assert a["content_hash"] == b["content_hash"]
    assert _billede(identity_focus="noget andet")["content_hash"] != a["content_hash"]


def test_et_UAENDRET_billede_er_ikke_en_aendring(isolated_runtime):
    """En kadence der koerer hver time maa ikke producere 24 «aendringer» om
    dagen og drukne de aegte."""
    a = _billede()
    b = _billede()
    d = compare_self_model_snapshots(a["snapshot_id"], b["snapshot_id"])
    assert d["changed"] is False
    assert d["changed_fields"] == []


def test_sammenligningen_siger_HVAD_der_aendrede_sig(isolated_runtime):
    a = _billede()
    b = _billede(identity_focus="at maale", confidence="high")
    d = compare_self_model_snapshots(a["snapshot_id"], b["snapshot_id"])
    assert d["changed"] is True
    assert set(d["changed_fields"]) == {"identity_focus", "confidence"}
    assert d["fields"]["identity_focus"] == {"from": "at bygge", "to": "at maale"}


def test_sammenligning_af_ukendte_billeder_paastaar_intet(isolated_runtime):
    """En sammenligning der ikke kan laves, maa ikke se ud som «ingen
    aendring»."""
    d = compare_self_model_snapshots("findes-ikke", "heller-ikke")
    assert d["changed"] is None
    assert "ukendt" in d["reason"]


def test_listen_er_nyeste_foerst_og_kan_afgraenses(isolated_runtime):
    for i in range(5):
        _billede(identity_focus=f"fokus-{i}")
    nyeste = list_self_model_snapshots(limit=2)
    assert [s["version"] for s in nyeste] == [5, 4]
    assert len(list_self_model_snapshots(limit=99)) == 5


def test_kilden_foelger_med_saa_et_skift_kan_forklares(isolated_runtime):
    """Et selvbillede uden proveniens kan man ikke stille sig kritisk over for."""
    s = record_self_model_snapshot(
        identity_focus="x", preferred_work_mode="y", recurring_tension="z",
        growth_direction="w", confidence="low", source="distiller",
        source_run_id="visible-42", model_epoch_id="epoch-7",
        producer_trigger="heartbeat-idle",
    )
    hentet = list_self_model_snapshots(limit=1)[0]
    assert hentet["source_run_id"] == "visible-42"
    assert hentet["model_epoch_id"] == "epoch-7"
    assert hentet["producer_trigger"] == "heartbeat-idle"
    assert s["snapshot_id"] == hentet["snapshot_id"]


def test_destilleren_versionerer_billedet():
    """Uden koblingen ville historikken vaere et lager ingen fylder:
    `record_private_self_model` OVERSKRIVER den aktuelle raekke, saa
    gaarsdagens selvbillede findes ikke laengere at holde det op mod."""
    import inspect

    from core.services import self_model_distiller as d

    kilde = inspect.getsource(d)
    assert "record_self_model_snapshot(" in kilde, (
        "destilleren versionerer aldrig billedet")
    i_gammel = kilde.index("record_private_self_model(created_at=")
    i_ny = kilde.index("record_self_model_snapshot(")
    assert i_gammel < i_ny, (
        "versioneringen sker foer den aktuelle raekke er skrevet")
