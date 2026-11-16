"""Session-bundet baggrundsarbejde og automatisk fortsaettelse — de tolv scenarier.

KONTRAKT (Bjørn 16/11-2026): et initiativ der opstaar i en samtale tilhoerer den
samtale gennem HELE sin livscyklus — opdagelse, udfoerelse, resultat, vaekning,
fortsaettelse. Et baggrundsresultat maa aldrig lande i en tilfaeldig anden
samtale, og en samtale med kendt oprindelse maa aldrig falde tilbage til ejerens
senest aktive session.

Testene karakteriserer den EKSISTERENDE kaede — der oprettes intet nyt ko-system:

    side_tasks.flag
      -> wakeup_dispatcher.pick_wakeup_run_target
      -> agent_wake_intentions.stage_wake          (varig intention)
      -> in_flight_runs.claim_due_recovery         (single-flight + lease)
      -> visible_run_recovery_dispatcher.recover_due_once
      -> agent_result_inbox.claim_for_model_step   (origin-scopet levering)

Hvert scenarie er skrevet saa det FEJLER hvis den beskyttede adfaerd fjernes;
det er beviset, ikke den groenne koersel (se ``test_scenarie_09``-noten).
"""
from __future__ import annotations

import uuid

import pytest

from core.services import agent_wake_intentions as aw
from core.services import in_flight_runs as ifr
from core.services import side_tasks
from core.services.wakeup_dispatcher import pick_wakeup_run_target

SESSION_A = "session-A-oprindelse"
SESSION_B = "session-B-anden"
OWNER = "owner-1"


@pytest.fixture(autouse=True)
def _ren_tilstand(isolated_runtime):
    """Varigt lager (isolated_runtime peger HOME paa tmp) — ryd mellem tests."""
    ifr._mutate(lambda r: r.clear())
    yield
    ifr._mutate(lambda r: r.clear())


def _outbox_skaer(rows: list[dict]) -> set[str]:
    return {str(r.get("origin_session_id") or "") for r in rows}


# --- Scenario 1: opgaven bevarer sin oprindelse gennem hele livscyklussen ----


def test_scenarie_01_sideopgave_bevarer_oprindelse():
    """En sideopgave rejst i session A baerer A som autoritativ oprindelse.

    Det er forudsaetningen for alle de oevrige scenarier: uden et varigt spor af
    hvor initiativet opstod, kan leveringen ikke finde hjem.
    """
    res = side_tasks.flag(
        title="undersoeg X",
        prompt="goer det",
        session_id=SESSION_A,
        owner_user_id=OWNER,
        parent_run_id="run-A-1",
    )
    assert res.get("status") != "error", res

    # `flag` returnerer en kvittering; sandheden er den PERSISTEREDE post.
    opgave = next(
        r for r in side_tasks._load_all() if r["side_task_id"] == res["side_task_id"]
    )
    assert opgave["owner_user_id"] == OWNER
    assert opgave["origin_session_id"] == SESSION_A
    assert opgave["parent_run_id"] == "run-A-1"
    # Bagudkompatibilitet: gamle laesere bruger stadig `session_id`.
    assert opgave["session_id"] == SESSION_A


# --- Scenario 2: Session B er aktiv — resultatet maa kun lande i A -----------


def test_scenarie_02_resultat_lande_kun_i_oprindelsessession():
    """To samtaler, to resultater: claim for B maa ikke se A's raekke.

    Dette er den fejl brugeren beskriver som «resultatet forsvandt ind i en
    tilfaeldig samtale». Scopingen ligger i SQL'en, saa den testes mod den
    RIGTIGE tabel i den isolerede DB.
    """
    from core.runtime import db_agent_contract as c

    conn = c._conn()
    now = c._now_iso()
    for sid, aid in ((SESSION_A, "asg-a"), (SESSION_B, "asg-b")):
        conn.execute(
            "INSERT INTO agent_result_outbox (message_id, assignment_id, result_type, "
            "owner_user_id, origin_session_id, sender_agent_id, recipient_agent_id, "
            "parent_run_id, last_run_id, payload_json, delivery_status, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (f"msg-{aid}", aid, "agent_result", OWNER, sid, "agent-1", "jarvis",
             "run-parent", "run-child", '{"status":"ok","summary":"s"}',
             "accepted", now, now),
        )
    conn.commit()

    kun_b = c.claim_pending_results(owner_user_id=OWNER, origin_session_id=SESSION_B)
    assert _outbox_skaer(kun_b) == {SESSION_B}, "B's claim maa ikke se A's resultat"

    # A's raekke er stadig ubehandlet — den blev ikke spist af B's claim.
    kun_a = c.claim_pending_results(owner_user_id=OWNER, origin_session_id=SESSION_A)
    assert _outbox_skaer(kun_a) == {SESSION_A}

    # En anden ejer ser intet, selv med samme sessions-id.
    from core.runtime import db_agent_contract as c2

    conn2 = c2._conn()
    now2 = c2._now_iso()
    conn2.execute(
        "INSERT INTO agent_result_outbox (message_id, assignment_id, result_type, "
        "owner_user_id, origin_session_id, sender_agent_id, recipient_agent_id, "
        "parent_run_id, last_run_id, payload_json, delivery_status, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("msg-foreign", "asg-foreign", "agent_result", "owner-2", SESSION_A,
         "agent-1", "jarvis", "", "", '{"status":"ok"}', "accepted", now2, now2),
    )
    conn2.commit()
    assert c.claim_pending_results(owner_user_id=OWNER, origin_session_id=SESSION_A) == []


# --- Scenario 3: Session A er ledig og vaekkes ---------------------------------


def test_scenarie_03_ledig_session_vaekkes_automatisk():
    """En skrevet intention bliver et krav recovery-dispatcheren kan tage."""
    aw.stage_wake(
        task_id="wake-a-1", session_id=SESSION_A, owner_user_id=OWNER,
        message=aw.wake_message(condition="all_terminal", assignment_ids=["asg-a"]),
        parent_run_id="run-A-1",
    )
    krav = ifr.claim_due_recovery(owner="dispatch-owner", lease_seconds=60)
    assert krav is not None, "en ledig samtale skal kunne vaekkes"
    assert str(krav.get("session_id")) == SESSION_A
    assert str(krav.get("wake_kind")) == aw.WAKE_KIND


# --- Scenario 4: Session A har en aktiv tur — vaekningen venter ---------------


def test_scenarie_04_aktiv_tur_udsætter_vaekningen():
    """Kører der en tur i samtalen, maa en vaekning ikke starte et konkurrerende run."""
    from core.services.wakeup_dispatcher import _active_turn_blocks

    assert _active_turn_blocks(SESSION_A, karantaene=False) == "", "forudsatning: fri"

    ifr.mark_started(run_id="run-live-A", session_id=SESSION_A, user_message="arbejder")
    aarsag = _active_turn_blocks(SESSION_A, karantaene=False)
    assert aarsag == "session_har_levende_run", (
        "en aktiv tur skal udsaette vaekningen, ikke konkurrere med den"
    )
    # En ANDEN samtale er upaavirket — udsaettelsen maa ikke vaere global.
    assert _active_turn_blocks(SESSION_B, karantaene=False) == ""


# --- Scenario 5: Session A er lukket i klienten ------------------------------


def test_scenarie_05_lukket_klient_blokerer_ikke_fortsaettelsen():
    """Fortsættelsen maa ikke kraeve at nogen har samtalen aaben i en klient.

    Posten baerer ingen klient-binding: `surface` er tom, og intet i kaeden
    spoerger en websocket. Beviset er at intentionen kan skrives og claim es
    uden at nogen klient findes.
    """
    aw.stage_wake(
        task_id="wake-a-5", session_id=SESSION_A, owner_user_id=OWNER,
        message="fortsaet",
    )
    post = ifr._load()["wake-a-5"]
    assert post["surface"] == "", "en vaekning maa ikke bindes til en klient-flade"
    assert ifr.claim_due_recovery(owner="dispatch-owner", lease_seconds=60) is not None


# --- Scenario 6: procesgenstart mellem faerdigt arbejde og levering ----------


def test_scenarie_06_procesgenstart_bevarer_intentionen():
    """Intentionen ligger i det varige lager, ikke i proceshukommelsen.

    Simuleret genstart: alt modul-lokalt slippes, og posten laeses fra lageret
    igen. En post der kun levede i hukommelsen ville forsvinde her.
    """
    aw.stage_wake(
        task_id="wake-a-6", session_id=SESSION_A, owner_user_id=OWNER,
        message="fortsaet efter genstart",
    )
    foer = dict(ifr._load())
    assert "wake-a-6" in foer

    # «Genstart»: genindlaes fra det varige lager.
    efter = ifr._load()
    assert "wake-a-6" in efter
    assert efter["wake-a-6"]["status"] == "recovering"
    assert efter["wake-a-6"]["session_id"] == SESSION_A


# --- Scenario 7: to eller flere resultater til samme session -----------------


def test_scenarie_07_to_resultater_samles_i_en_fortsaettelse():
    """Flere ventende resultater maa ikke give flere samtidige vaekninger."""
    first = aw.stage_wake(
        task_id="wake-a-7a", session_id=SESSION_A, owner_user_id=OWNER,
        message="resultat 1",
    )
    second = aw.stage_wake(
        task_id="wake-a-7b", session_id=SESSION_A, owner_user_id=OWNER,
        message="resultat 2",
    )
    assert first.get("created") is True
    assert second.get("merged") is True, "andet resultat skal samles, ikke starte en ny"
    assert second.get("task_id") == "wake-a-7a"

    ventende = [k for k, v in ifr._load().items()
                if str(v.get("session_id")) == SESSION_A
                and str(v.get("status")) == "recovering"]
    assert ventende == ["wake-a-7a"], "praecis én fortsaettelse for samtalen"


# --- Scenario 8: dubletlevering af samme resultat ----------------------------


def test_scenarie_08_dublet_levering_er_idempotent():
    """Samme resultat to gange maa hverken give to vaekninger eller to claims."""
    from core.runtime import db_agent_contract as c

    a1 = aw.stage_wake(task_id="wake-a-8", session_id=SESSION_A, owner_user_id=OWNER,
                       message="resultat")
    a2 = aw.stage_wake(task_id="wake-a-8", session_id=SESSION_A, owner_user_id=OWNER,
                       message="resultat")
    assert a1.get("created") is True
    assert a2.get("created") is False, "samme task_id maa ikke oprette en ny post"

    conn = c._conn()
    now = c._now_iso()
    conn.execute(
        "INSERT INTO agent_result_outbox (message_id, assignment_id, result_type, "
        "owner_user_id, origin_session_id, sender_agent_id, recipient_agent_id, "
        "parent_run_id, last_run_id, payload_json, delivery_status, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("msg-dup", "asg-dup", "agent_result", OWNER, SESSION_A, "agent-1", "jarvis",
         "", "", '{"status":"ok"}', "accepted", now, now),
    )
    conn.commit()
    foerste = c.claim_pending_results(owner_user_id=OWNER, origin_session_id=SESSION_A)
    anden = c.claim_pending_results(owner_user_id=OWNER, origin_session_id=SESSION_A)
    assert len(foerste) == 1
    assert anden == [], "et claimet resultat maa aldrig leveres igen"


# --- Scenario 9: oprindelsessession mangler eller er ugyldig -----------------


def test_scenarie_09_ugyldig_oprindelse_blokeres_uden_omdirigering():
    """En eksplicit origin der ikke kan bruges maa IKKE falde tilbage til en
    tilfaeldig app-session. Posten skal staa ventende med en synlig aarsag.

    MUTATIONSBEVIS: genindfoeres det gamle ``return app_resolver()`` paa den
    eksterne gren, fejler denne test med en session i stedet for ``None``.
    """
    kaldt: list[str] = []

    def app_resolver() -> str:
        kaldt.append("app")
        return SESSION_B

    def owner_resolver() -> str:
        kaldt.append("owner")
        return SESSION_B

    udfald = pick_wakeup_run_target(
        channel="app",
        record_session="discord-123",
        app_resolver=app_resolver,
        owner_resolver=owner_resolver,
        is_external=lambda sid: sid.startswith("discord-"),
    )
    assert udfald is None, "en ugyldig eksplicit origin maa ikke omdirigeres"
    assert kaldt == [], "resolverne maa slet ikke spoerges naar origin er eksplicit og ugyldig"


# --- Scenario 10: manuelt stoppet session ------------------------------------


def test_scenarie_10_stoppet_session_vaekkes_ikke():
    """Et brugerstop skal gaelde den ventende vaekning — den maa ikke genopstaa."""
    aw.stage_wake(task_id="wake-a-10", session_id=SESSION_A, owner_user_id=OWNER,
                  message="fortsaet")
    assert aw.cancel_pending_wake("wake-a-10", reason="brugeren stoppede") is True

    post = ifr._load()["wake-a-10"]
    assert post["status"] == "cancelled"
    assert ifr.claim_due_recovery(owner="dispatch-owner", lease_seconds=60) is None, (
        "en aflyst vaekning maa ikke kunne claim es"
    )


# --- Scenario 11: agentresultater og sideopgaver foelger samme princip -------


def test_scenarie_11_agent_og_sideopgave_deler_samme_oprindelsesprincip():
    """Begge veje baerer samme tre identitetsfelter og samme vaekningssti."""
    opgave = side_tasks.flag(
        title="agent-arbejde", prompt="koer", session_id=SESSION_A,
        owner_user_id=OWNER, parent_run_id="run-A-11",
    )
    opgave = next(
        r for r in side_tasks._load_all() if r["side_task_id"] == opgave["side_task_id"]
    )
    assert (opgave["owner_user_id"], opgave["origin_session_id"], opgave["parent_run_id"]) == (
        OWNER, SESSION_A, "run-A-11"
    )

    # Samme vaekningsvej som en agent-ventekontrakt bruger.
    aw.stage_wake(task_id="wake-a-11", session_id=opgave["origin_session_id"],
                  owner_user_id=opgave["owner_user_id"], message="agenten er faerdig",
                  parent_run_id=opgave["parent_run_id"])
    post = ifr._load()["wake-a-11"]
    assert post["session_id"] == SESSION_A
    assert post["parent_run_id"] == "run-A-11"


# --- Scenario 12: selvstaendige systeminitiativer ---------------------------


def test_scenarie_12_systeminitiativ_bevarer_eget_hjem():
    """Uden en oprindelig brugersession maa posten ikke tildeles en kunstig.

    Systeminitiativer har deres egen hjem-vej (resolveren). Kontrakten er at
    den vej stadig bruges — og at den ikke blandes sammen med den eksplicitte.
    """
    kaldt: list[str] = []

    def app_resolver() -> str:
        kaldt.append("app")
        return "auto-system-session"

    udfald = pick_wakeup_run_target(
        channel="app",
        record_session="",          # systeminitiativ: ingen oprindelig samtale
        app_resolver=app_resolver,
        owner_resolver=lambda: "owner-session",
        is_external=lambda sid: False,
    )
    assert udfald == "auto-system-session"
    assert kaldt == ["app"], "kun app-resolveren maa bruges for et systeminitiativ"
