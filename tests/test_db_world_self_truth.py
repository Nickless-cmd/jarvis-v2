"""Invarianterne bag verdens- og selv-modellens sandhed.

`tests/runtime/test_db_world_self_truth.py` daekker migreringens detaljer.
Denne fil haevder de EGENSKABER de tre rettelser handler om, i den form de skal
holde uanset hvordan de er implementeret:

  * bevis taelles i distinkte koersler, ikke i kald
  * en post uden proveniens taeller ikke
  * «faerdig» er en observation, ikke en tilstand
"""
from __future__ import annotations

import pytest

from core.runtime.db_world_self_truth import (
    select_conversation_topics,
    upsert_conversation_topic,
)


def _emne(noegle, *, run_id, session_id, titel="T", nr=0):
    return upsert_conversation_topic(
        topic_id=f"topic-{nr}", canonical_key=noegle, title=titel,
        summary="s", source_kind="visible_run", session_id=session_id,
        run_id=run_id, created_at="2026-09-10T00:00:00",
        updated_at="2026-09-10T00:00:00",
    )


@pytest.mark.parametrize("gentagelser", [2, 5])
def test_samme_koersel_leveret_flere_gange_taeller_ÉN(isolated_runtime, gentagelser):
    """Et emne der ser stoettet ud af fem kilder, men er ét run leveret fem
    gange, er en opfundet styrke."""
    for i in range(gentagelser):
        _emne("topic:gentaget", run_id="run-1", session_id="s-a", nr=i)
    t = select_conversation_topics(limit=5)[0]
    assert t["support_count"] == 1
    assert t["session_count"] == 1


def test_samme_session_i_to_omgange_taeller_ÉN(isolated_runtime):
    """A -> B -> A. En taeller der sammenligner med den SIDSTE session ville
    tælle A to gange; distinkte raekker kan ikke tage fejl af det."""
    _emne("topic:frem-og-tilbage", run_id="r1", session_id="A", nr=1)
    _emne("topic:frem-og-tilbage", run_id="r2", session_id="B", nr=2)
    _emne("topic:frem-og-tilbage", run_id="r3", session_id="A", nr=3)
    t = select_conversation_topics(limit=5)[0]
    assert t["support_count"] == 3
    assert t["session_count"] == 2


def test_uden_proveniens_er_der_intet_bevis(isolated_runtime):
    """Der er intet at pege tilbage paa, saa der taelles ikke. Emnet
    opdateres stadig — vi kasserer ikke indholdet, vi naegter bare at kalde
    det bevis."""
    _emne("topic:uden-spor", run_id="", session_id="", titel="Foerst", nr=1)
    _emne("topic:uden-spor", run_id="", session_id="", titel="Sidst", nr=2)
    t = select_conversation_topics(limit=5)[0]
    assert t["support_count"] == 0
    assert t["session_count"] == 0
    assert t["title"] == "Sidst"


def test_faerdig_migrering_tages_op_igen_naar_noget_bliver_berettiget(isolated_runtime):
    """Markoeren gaar kun FREMAD. Uden en gen-scanning ville en raekke der
    bliver berettiget UNDER den aldrig blive set — migreringen troede den var
    faerdig fordi den var det engang."""
    from core.runtime.db_runtime_executive_signals import (
        list_runtime_world_model_signals,
        update_runtime_world_model_signal_status,
        upsert_runtime_world_model_signal,
    )
    from core.runtime.db_world_self_truth import quarantine_legacy_world_topics

    for i in (1, 2):
        upsert_runtime_world_model_signal(
            signal_id=f"legacy-{i}", signal_type="conversational_context",
            canonical_key=f"legacy:{i}", status="active", title=f"L{i}",
            summary="x", rationale="x", source_kind="visible_run",
            confidence="medium", evidence_summary="x", support_summary="x",
            support_count=1, session_count=1,
            created_at="2026-09-10T00:00:00", updated_at="2026-09-10T00:00:00",
        )
    assert quarantine_legacy_world_topics(batch_size=50)["completed"] == 1

    # En raekke bliver aktiv igen UNDER markoeren.
    update_runtime_world_model_signal_status(
        "legacy-1", status="active", updated_at="2026-09-10T01:00:00")

    igen = quarantine_legacy_world_topics(batch_size=50)
    assert igen["quarantined"] == 1, "migreringen saa aldrig den genaabnede raekke"
    tilstande = {r["signal_id"]: r["status"]
                 for r in list_runtime_world_model_signals(limit=10)}
    assert tilstande["legacy-1"] == "legacy_quarantined"
