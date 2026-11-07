# tests/test_initiativ_godkendelse_trigger.py
"""Godkendelse skal føre til noget (7/11-2026).

## Hvorfor denne fil findes

Målt 7/11-2026: `endorse_long_term_intention` satte `user_approved_at` — og
intet andet. `_initiative_due` læser `next_attempt_at`, og `mark_attempted`
skubber et livsprojekt `_LONG_TERM_REASSESS_DAYS` (14) frem. Så en godkendelse
forkortede ventetiden med nul.

Feltet blev derefter kun læst ét sted: `central_hub`, hvor det bruges til at
SKJULE spørgsmålet for Bjørn. Altså: han godkendte de samme tre livsprojekter
mange gange, og det eneste der skete var at de holdt op med at blive vist —
indtil de dukkede op igen 14 dage senere.

Testen her måler den ene ting der betyder noget: at et godkendt projekt bliver
DUE med det samme, så heartbeat faktisk kan gribe det.
"""

from __future__ import annotations


def test_godkendelse_goer_projektet_due_med_det_samme(isolated_runtime) -> None:
    from core.services import initiative_queue as q

    iid = q.seed_long_term_intention(
        title="Testprojekt for godkendelse", why="fordi den skal kunne maales"
    )

    # Et materialiseret forsøg skubber projektet 14 dage frem — det er den
    # tilstand et livsprojekt reelt staar i naar Bjorn ser det.
    q.mark_attempted(iid, blocked_reason="materialiseret i task")

    ids = [str(i.get("initiative_id") or "") for i in q.get_pending_initiatives()]
    assert iid not in ids, (
        "et netop forsoegt livsprojekt skal IKKE vaere due — ellers beviser "
        "testen intet om godkendelsens virkning"
    )

    q.endorse_long_term_intention(iid, note="go")

    ids = [str(i.get("initiative_id") or "") for i in q.get_pending_initiatives()]
    assert iid in ids, (
        "godkendelsen gjorde ikke projektet due — saa har den ingen arvtager, "
        "og Bjorns tryk betyder kun at spoergsmaalet skjules for ham"
    )


def test_godkendelse_bevarer_projektet(isolated_runtime) -> None:
    """Modsat abandon: status maa ikke aendres. Projektet lever videre."""
    from core.services import initiative_queue as q

    iid = q.seed_long_term_intention(title="Bevares", why="fordi")
    updated = q.endorse_long_term_intention(iid, note="ok")

    assert updated is not None
    assert str(updated.get("status") or "") == "pending"
    assert str(updated.get("user_approved_at") or "") != ""
