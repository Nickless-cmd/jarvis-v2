"""Reconcileren skal LÆSE bindingen — ikke requeue et run der netop lykkedes.

11/11-2026. `routine_dispatch` afregnede sit claim i en proces-lokal closure.
Den kan ikke bæres gennem indbakken, og uden den requeuede
`reconcile_expired_runs` et udløbet claim BLINDT — også når det visible run
faktisk var lykkedes. Rutinen kørte så en gang til.

Bindingen (`routine_runs.visible_run_id`) gør afregningen til en tilstand.
Disse tests håndhæver de fire grene:

* `running`   → leasen fornyes, runnet requeues IKKE
* `completed` → `complete_run_success` (resultat + terminal hændelse)
* `failed`    → `transition_run(to_status='failed')`
* ukendt      → gammel adfærd: requeue
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.runtime import db_routines


@pytest.fixture
def rutine_run(isolated_runtime, monkeypatch):
    """Én kørende rutine-række med udløbet lease og en binding.

    Rækken bygges med husets EGNE funktioner (`create_routine` → `create_run`
    → `claim_run`) i stedet for rå INSERT: skemaet ændrer sig, og et fixture
    der duplikerer det ville gå i stå uden at nogen opdagede hvorfor.
    """
    import core.runtime.db_core as db_core
    import core.services.keyring_store as keyring_store

    monkeypatch.setattr(keyring_store, "get_user_key", lambda _owner: b"x" * 32)

    def _opret(*, visible_run_id: str, status: str = "running") -> str:
        db_routines.create_routine(
            owner_user_id="bjorn", access_scope="user_private", name="test",
            instruction=b"goer noget", capability_scope="chat",
            trigger_kind="manual", trigger_config={},
            permission_policy={}, delivery_policy={}, inbox_policy={},
            retention_policy={}, failure_policy={}, routine_id="r1",
        )
        run = db_routines.create_run(
            routine_id="r1", idempotency_key="idem", trigger_source="manual",
        )
        run_id = str(run["run_id"])
        db_routines.claim_run(run_id, holder="holder", lease_seconds=900)
        with db_core.connect() as conn:
            # Leasen skal vaere UDLOEBET for at reconcileren ser raekken.
            conn.execute(
                "UPDATE routine_runs SET lease_expires_at=? WHERE run_id=?",
                ("2026-11-11T00:00:00+00:00", run_id),
            )
            if visible_run_id:
                conn.execute(
                    "UPDATE routine_runs SET visible_run_id=?,session_id='chat-1' "
                    "WHERE run_id=?",
                    (visible_run_id, run_id),
                )
                conn.execute(
                    "INSERT INTO visible_runs (run_id,lane,provider,model,status,"
                    "started_at,finished_at) VALUES (?,?,?,?,?,?,?)",
                    (visible_run_id, "primary", "test", "test", status,
                     "2026-11-11T00:00:00+00:00", ""),
                )
        return run_id

    return _opret


def _status(run_id: str) -> str:
    import core.runtime.db_core as db_core

    with db_core.connect() as conn:
        return str(
            conn.execute(
                "SELECT status FROM routine_runs WHERE run_id=?", (run_id,)
            ).fetchone()["status"]
        )


def test_koerende_visible_run_fornyer_leasen_i_stedet_for_at_requeue(rutine_run):
    """Et langt run må ikke dobbelt-køres fordi leasen løb ud undervejs."""
    run_id = rutine_run(visible_run_id="vis-1", status="running")
    nu = datetime.now(UTC)

    udfald = db_routines.reconcile_expired_runs(now=nu)

    assert _status(run_id) == "running", "et levende run blev requeued"
    assert udfald[0]["diagnostic_code"] == "lease_renewed", udfald


def test_lykkedes_visible_run_afregnes_som_succes(rutine_run):
    """Kernen i rettelsen: et gennemført run må ikke køre igen."""
    run_id = rutine_run(visible_run_id="vis-2", status="completed")

    udfald = db_routines.reconcile_expired_runs(now=datetime.now(UTC))

    assert _status(run_id) == "succeeded", "et lykkedes run blev requeued"
    assert udfald[0]["status"] == "succeeded", udfald


def test_lykkedes_run_faar_sin_terminale_haendelse(rutine_run):
    """En rå UPDATE ville efterlade et run der SER afsluttet ud men er hult."""
    import core.runtime.db_core as db_core

    run_id = rutine_run(visible_run_id="vis-3", status="completed")
    db_routines.reconcile_expired_runs(now=datetime.now(UTC))

    with db_core.connect() as conn:
        terminal = conn.execute(
            "SELECT kind FROM routine_run_events WHERE run_id=? AND terminal=1",
            (run_id,),
        ).fetchall()
    assert [r["kind"] for r in terminal] == ["succeeded"], terminal


def test_fejlet_visible_run_afregnes_som_fejl(rutine_run):
    run_id = rutine_run(visible_run_id="vis-4", status="failed")

    udfald = db_routines.reconcile_expired_runs(now=datetime.now(UTC))

    assert _status(run_id) == "failed", "et fejlet run blev requeued"
    assert udfald[0]["diagnostic_code"] == "session_failed", udfald


def test_uden_binding_requeues_som_foer(rutine_run):
    """Ukendt udfald må ikke opfindes — den gamle adfærd er den ærlige."""
    run_id = rutine_run(visible_run_id="", status="running")

    udfald = db_routines.reconcile_expired_runs(now=datetime.now(UTC))

    assert _status(run_id) == "queued", "en ubundet række blev afgjort på et gæt"
    assert udfald[0]["diagnostic_code"] == "lease_expired", udfald
