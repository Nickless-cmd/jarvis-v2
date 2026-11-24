"""Koordinering på tværs af synlige ture, autonome runs, opgaver og agenter.

Testene bruger RIGTIGE rækker i den isolerede db (visible_runs, agent_assignments,
runtime_tasks) — ikke stubbede forbindelser — så de faktisk prøver SQL-grenene.
"""
from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

import pytest

from core.services import work_coordination as wc

VERIFICER = "Verificér om decision_gate.py håndhæver den nyeste ændring"
VERIFICER_ANDEN_ORDLYD = "Undersøg hvorvidt decision_gate stadig håndhæver seneste ændring"
SKRIV_TEST = "Skriv en test for decision_gate.py så ændringen er dækket"


def _iso(minutter_siden: float = 0) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutter_siden)).isoformat()


def _synlig_tur(run_id, *, user="u1", spoerg="", svar="", min_siden=2):
    from core.runtime.db import connect

    with connect() as conn:
        conn.execute(
            "INSERT INTO visible_runs (run_id, lane, provider, model, status, started_at,"
            " finished_at, text_preview, user_id) VALUES (?,?,?,?,?,?,?,?,?)",
            (run_id, "primary", "p", "m", "completed", _iso(min_siden), _iso(min_siden), svar, user),
        )
        conn.execute(
            "INSERT INTO visible_work_units (work_id, run_id, status, lane, provider, model,"
            " finished_at, user_message_preview) VALUES (?,?,?,?,?,?,?,?)",
            (f"w-{run_id}", run_id, "completed", "primary", "p", "m", _iso(min_siden), spoerg),
        )


def _assignment(aid, goal, *, user="u1", status="running"):
    from core.runtime.db import connect

    from core.runtime.db_agent_contract import ensure_agent_contract_tables

    with connect() as conn:
        ensure_agent_contract_tables(conn)
        conn.execute(
            "INSERT INTO agent_assignments (assignment_id, agent_id, owner_user_id,"
            " origin_session_id, goal, status, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (aid, "agent-x", user, "sess", goal, status, _iso(), _iso()),
        )


def _antal_ventende() -> int:
    from core.runtime.db import connect

    with connect() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM runtime_initiatives WHERE status='pending'"
        ).fetchone()[0]


# ── Identitet: fingeraftryk bygger på relationer, ikke emneord ─────────────


def test_forskellig_ordlyd_samme_handling_giver_samme_fingeraftryk(isolated_runtime):
    assert wc.work_fingerprint(VERIFICER) == wc.work_fingerprint(VERIFICER_ANDEN_ORDLYD)


def test_samme_emne_forskellig_handling_giver_forskelligt_fingeraftryk(isolated_runtime):
    assert wc.work_fingerprint(VERIFICER) != wc.work_fingerprint(SKRIV_TEST)


def test_uden_anker_eller_handling_gaettes_der_ikke(isolated_runtime):
    assert wc.work_fingerprint("Noget føles uafklaret") == ""
    assert wc.work_fingerprint("Tjek om det går godt") == ""  # handling uden anker


def test_fingeraftryk_er_scopet_til_bruger(isolated_runtime):
    assert wc.work_fingerprint(VERIFICER, user_id="a") != wc.work_fingerprint(VERIFICER, user_id="b")


# ── Scenarie 1 + race: kun ét arbejde accepteres ───────────────────────────


def test_to_identiske_initiativer_samtidigt_giver_en_claim(isolated_runtime):
    resultater, bar = [], threading.Barrier(8)

    def _koer(i):
        bar.wait()
        resultater.append(wc.claim_work(tekst=VERIFICER, owner=f"w{i}"))

    traade = [threading.Thread(target=_koer, args=(i,)) for i in range(8)]
    [t.start() for t in traade]
    [t.join() for t in traade]
    assert sum(1 for r in resultater if r["claimed"]) == 1
    assert all(r["covering"]["state"] == "in_progress" for r in resultater if not r["claimed"])


def test_claim_er_idempotent_ved_gentagelse(isolated_runtime):
    første = wc.claim_work(tekst=VERIFICER, owner="a")
    anden = wc.claim_work(tekst=VERIFICER, owner="a")
    assert første["claimed"] and not anden["claimed"]
    assert anden["covering"]["ref"] == første["task"]["task_id"]


def test_push_initiative_to_identiske_giver_et_initiativ(isolated_runtime):
    from core.services.initiative_queue import push_initiative

    a = push_initiative(focus=VERIFICER, source="inner-voice")
    b = push_initiative(focus=VERIFICER, source="inner-voice")
    assert a and b in ("", a)
    assert _antal_ventende() == 1


# ── Scenarie 2: forskellig ordlyd, samme eksisterende opgave ───────────────


def test_forskelligt_formulerede_initiativer_samme_opgave_koordineres(isolated_runtime):
    from core.services.initiative_queue import push_initiative

    første = push_initiative(focus=VERIFICER, source="inner-voice")
    anden = push_initiative(focus=VERIFICER_ANDEN_ORDLYD, source="inner-voice")
    assert første and anden in ("", første)
    assert _antal_ventende() == 1


def test_eksplicit_relation_til_opgave_koordineres_uanset_tekst(isolated_runtime):
    c = wc.claim_work(tekst=VERIFICER, owner="a")
    tid = c["task"]["task_id"]
    dæk = wc.find_covering_work(f"Hvordan går det med {tid}? Giv status")
    assert dæk and dæk["ref"] == tid and dæk["why"] == "eksplicit-relation"


# ── Scenarie 3: samme emne, forskellige handlinger ─────────────────────────


def test_samme_emne_forskellige_handlinger_bevares_begge(isolated_runtime):
    from core.services.initiative_queue import push_initiative

    a = push_initiative(focus=VERIFICER, source="inner-voice")
    b = push_initiative(focus=SKRIV_TEST, source="inner-voice")
    assert a and b and a != b
    assert _antal_ventende() == 2


def test_claim_laaser_kun_handlingen_ikke_emnet(isolated_runtime):
    assert wc.claim_work(tekst=VERIFICER, owner="a")["claimed"]
    assert wc.claim_work(tekst=SKRIV_TEST, owner="b")["claimed"]


# ── Scenarie 4 + 5: synlig session ↔ autonomt initiativ ────────────────────


def test_synlig_session_paa_opgaven_blokerer_parallelt_initiativ(isolated_runtime):
    from core.services.initiative_queue import push_initiative

    _synlig_tur("visible-1", user="", spoerg="Kan du tjekke om decision_gate.py virker?",
                svar="Jeg undersøger decision_gate nu")
    assert push_initiative(focus=VERIFICER, source="inner-voice") == ""


def test_synlig_session_kan_opdage_autonomt_run_paa_samme_opgave(isolated_runtime):
    wc.claim_work(tekst=VERIFICER, owner="autonomous-abc", origin="autonomous")
    dæk = wc.find_covering_work("Tjek decision_gate.py — håndhæver den ændringen?")
    assert dæk and dæk["kind"] == "task" and dæk["state"] == "in_progress"


# ── Scenarie 6: agent arbejder allerede ────────────────────────────────────


def test_eksisterende_assignment_er_synlig_for_nyt_initiativ(isolated_runtime):
    _assignment("asg-aaaaaaaa11", "Verificér decision_gate.py og rapportér", user="u1")
    dæk = wc.find_covering_work(VERIFICER, user_id="u1")
    assert dæk and dæk["kind"] == "assignment" and dæk["ref"] == "asg-aaaaaaaa11"
    assert dæk["state"] == "delegated"


def test_afsluttet_assignment_dækker_ikke(isolated_runtime):
    _assignment("asg-bbbbbbbb22", "Verificér decision_gate.py", user="u1", status="completed")
    assert wc.find_covering_work(VERIFICER, user_id="u1") is None


# ── Scenarie 7: afsluttet genstartes ikke uden ny evidens ──────────────────


def test_afsluttet_opgave_genstartes_ikke_uden_ny_evidens(isolated_runtime):
    from core.services import runtime_tasks

    c = wc.claim_work(tekst=VERIFICER, owner="a")
    runtime_tasks.update_task(c["task"]["task_id"], status="succeeded")
    igen = wc.claim_work(tekst=VERIFICER_ANDEN_ORDLYD, owner="b")
    assert not igen["claimed"] and igen["covering"]["state"] == "done"
    assert igen["covering"]["why"] == "allerede-udfoert"


def test_ny_evidens_genaabner_afsluttet_arbejde(isolated_runtime):
    from core.services import runtime_tasks

    c = wc.claim_work(tekst=VERIFICER, owner="a")
    runtime_tasks.update_task(c["task"]["task_id"], status="succeeded")
    igen = wc.claim_work(tekst=VERIFICER, owner="b", new_evidence=True)
    assert igen["claimed"]


# ── Scenarie 8: fejl/efterladt kan overtages ───────────────────────────────


def test_fejlet_opgave_blokerer_ikke_nyt_forsoeg(isolated_runtime):
    from core.services import runtime_tasks

    c = wc.claim_work(tekst=VERIFICER, owner="a")
    runtime_tasks.update_task(c["task"]["task_id"], status="failed")
    assert wc.claim_work(tekst=VERIFICER, owner="b")["claimed"]


def test_efterladt_opgave_overtages_efter_udloebet_lease(isolated_runtime):
    """Crash recovery: workeren dør midt i; leasen udløber; reaperen requeuer; en anden vinder."""
    from core.runtime.db import connect
    from core.services import runtime_tasks

    c = wc.claim_work(tekst=VERIFICER, owner="doer")
    tid = c["task"]["task_id"]
    assert runtime_tasks.claim_task(tid, owner="doer") is not None
    with connect() as conn:
        conn.execute("UPDATE runtime_tasks SET lease_expires_at=? WHERE task_id=?",
                     (_iso(60), tid))
        conn.commit()
    assert runtime_tasks.reap_expired_leases() == [tid]
    overtaget = runtime_tasks.claim_task(tid, owner="ny-worker")
    assert overtaget is not None and overtaget["owner"] == "ny-worker"
    # og to samtidige overtagelser giver stadig kun én vinder
    assert runtime_tasks.claim_task(tid, owner="tredje") is None


def test_initiativ_claim_er_atomisk_og_lease_udloeber(isolated_runtime):
    from core.runtime.db import connect
    from core.services.initiative_queue import claim_initiative, push_initiative

    iid = push_initiative(focus=VERIFICER, source="inner-voice")
    sejre, bar = [], threading.Barrier(6)

    def _koer(i):
        bar.wait()
        sejre.append(claim_initiative(iid, holder=f"w{i}"))

    ts = [threading.Thread(target=_koer, args=(i,)) for i in range(6)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sum(sejre) == 1
    # holderen dør → leasen udløber → en anden kan overtage
    with connect() as conn:
        conn.execute("UPDATE runtime_initiatives SET next_attempt_at=? WHERE initiative_id=?",
                     (_iso(1), iid))
        conn.commit()
    assert claim_initiative(iid, holder="overtager")


# ── Scenarie 9 + 11: ingen undertrykkelse af uafhængige initiativer ────────


def test_bruger_offline_baggrundsinitiativ_fortsaetter(isolated_runtime):
    from core.services.initiative_queue import push_initiative

    assert push_initiative(focus=VERIFICER, source="inner-voice")


def test_aktivitetsspaerring_blokerer_ikke_uafhaengigt_initiativ(isolated_runtime):
    from core.services.initiative_queue import push_initiative

    _synlig_tur("visible-2", user="", spoerg="Hjælp mig med en opskrift på boller",
                svar="Her er en opskrift", min_siden=1)
    assert push_initiative(focus=VERIFICER, source="inner-voice")


def test_uanalyserbart_initiativ_rammes_stadig_af_noedbremsen(isolated_runtime):
    from core.services.initiative_queue import push_initiative

    _synlig_tur("visible-3", user="", min_siden=1)
    assert push_initiative(focus="Giv det lidt mere opmærksomhed i dag", source="inner-voice") == ""


# ── Scenarie 10: brugerisolation ───────────────────────────────────────────


def test_to_brugere_samme_emne_holdes_adskilt(isolated_runtime):
    a = wc.claim_work(tekst=VERIFICER, owner="a", user_id="alice")
    b = wc.claim_work(tekst=VERIFICER, owner="b", user_id="bob")
    assert a["claimed"] and b["claimed"]


def test_anden_brugers_synlige_tur_og_agent_dækker_ikke(isolated_runtime):
    _synlig_tur("visible-alice", user="alice", spoerg="tjek decision_gate.py", svar="ok")
    _assignment("asg-cccccccc33", "Verificér decision_gate.py", user="alice")
    assert wc.find_covering_work(VERIFICER, user_id="bob") is None
    assert wc.find_covering_work(VERIFICER, user_id="alice") is not None


def test_svar_afslorer_aldrig_indhold(isolated_runtime):
    _synlig_tur("visible-s", user="alice", spoerg="HEMMELIGT tjek decision_gate.py", svar="x")
    dæk = wc.find_covering_work(VERIFICER, user_id="alice")
    assert "HEMMELIGT" not in repr(dæk)


# ── Hensigt: refleksion med konkret handling er ikke en tilstand ───────────


def test_refleksion_med_konkret_handling_afvises_ikke_som_tilstand(isolated_runtime):
    from core.services.initiative_queue import _er_ikke_et_initiativ

    assert _er_ikke_et_initiativ("Jeg bliver her lidt uden at presse en plan ud af det") == \
        "tilstandsbeskrivelse"
    assert _er_ikke_et_initiativ("Jeg vil tjekke om decision_gate.py håndhæver ændringen") == ""


# ── Ingen tavse afvisninger ────────────────────────────────────────────────


def test_koordination_efterlader_begrundet_event(isolated_runtime, monkeypatch):
    from core.eventbus import bus

    set_ = []
    monkeypatch.setattr(bus.event_bus, "publish", lambda kind, payload=None, **k: set_.append((kind, payload)))
    wc.claim_work(tekst=VERIFICER, owner="a")
    wc.claim_work(tekst=VERIFICER, owner="b")
    beslutninger = [p for k, p in set_ if k == "coordination.decision"]
    assert [p["decision"] for p in beslutninger] == ["accepted", "coordinated"]
    assert beslutninger[1]["reason"] and beslutninger[1]["covering"]["ref"]


# ── Ejer-isolation i _eksplicit_relation ─────────────────────────────────────
# Målt 24/11-2026: task-grenen læste kun (task_id, status) og sprang ejer-
# tjekket over, mens assignment-grenen lige nedenfor brugte _bruger_matcher.
# Konsekvens: bruger A kunne afgøre om bruger B's task fandtes og var aktiv —
# ved at se om hans eget initiativ blev afvist som «dækket».


def test_fremmed_task_maa_ikke_daekke_mit_initiativ(isolated_runtime):
    """B's private task må ikke «dække» A's initiativ, men B's eget skal."""
    from core.services import runtime_tasks

    t = runtime_tasks.create_task(
        kind="work", goal="B's private arbejde", origin="test", owner="u2",
    )
    tid = str(t["task_id"])
    tekst = f"Tjek {tid} for status"

    # Kontrol: samme bruger SKAL dækkes. Fejler den, rammer testen ikke grenen
    # og kan derfor ikke bevise noget om lækagen.
    egen = wc.find_covering_work(tekst, user_id="u2")
    assert egen is not None, "kontrollen fejlede: egen task dækkede ikke — grenen rammes ikke"
    assert egen["ref"] == tid

    # Lækagen: u1 må ikke få dækning af u2's task.
    fremmed = wc.find_covering_work(tekst, user_id="u1")
    assert fremmed is None, f"LÆKAGE: u1 fik dækning af u2's task: {fremmed}"
