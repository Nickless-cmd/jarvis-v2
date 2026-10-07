"""Proveniens og bogføring for indbakken — Opgave 1 og 3.

Testene kører mod en RIGTIG sqlite. Skemaet, `UNIQUE`-betingelsen og de atomare
`UPDATE ... WHERE status = 'aaben'` ER det der skal måles her, og en fake
forbindelse der svarer det samme uanset forespørgslen kan ikke se nogen af dem.
Det kostede en runde samme dag på en anden fil.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from core.runtime import db_inbox
from core.services import inbox_state

# Bruger-id'erne her er OPDIGTEDE. Husstandens rigtige id'er (discord-snowflakes)
# hører ikke i repoet.
BJORN = "bjorn"
ANDEN = "en-anden-bruger"


@pytest.fixture
def inbox_db(monkeypatch, tmp_path, ejeren_er_bjorn):
    """Rigtig sqlite i tmp_path, og skema-flaget nulstillet per test.

    `_skema_klar` er en MODUL-konstant. Uden nulstillingen ville test nr. 2 tro
    at skemaet fandtes i sin egen, nye fil — og så fejler den på en manglende
    tabel af en grund der intet har med dens emne at gøre. Modul-tilstand der
    overlever mellem tests er en målt fælde i dette hus.
    """
    sti = tmp_path / "inbox.db"

    @contextmanager
    def _connect():
        k = sqlite3.connect(sti)
        k.row_factory = sqlite3.Row
        try:
            yield k
            k.commit()
        finally:
            k.close()

    import core.runtime.db_core as _core
    monkeypatch.setattr(_core, "connect", _connect)
    monkeypatch.setattr(db_inbox, "connect", _connect)
    monkeypatch.setattr(db_inbox, "_skema_klar", False)
    return sti


@contextmanager
def _som_bjorn(run_id: str = "visible-abc123"):
    """Simulér en ægte, autentificeret tur: owner-rolle og et LEVENDE run.

    Begge dele er nødvendige. Uden det levende run er et kalder-leveret run-id
    bare en påstand; uden den autentificerede principal ved vi ikke hvem
    posten er for.
    """
    from core.identity import workspace_context as wc
    with patch.object(wc, "current_user_id", return_value=BJORN), \
         patch("core.services.session_context_resolve.aktivt_run_id",
               return_value=run_id):
        yield


# ── Opgave 1, trin 1: spoofing ──────────────────────────────────────────────

def test_huset_kan_ikke_spoofe_jarvis_ejerskab(inbox_db):
    """Et kalder-valgt ejerflag er ikke proveniens.

    Spec'ens egen test. Her er den vigtig fordi den er den ENESTE vej gaten kan
    omgås: kunne en daemon sætte `paastaaet_ejer="jarvis"`, ville huset kunne
    kræve — og hele skrive-kontrakten («huset kan informere, men ikke kræve»)
    var uden virkning.
    """
    r = inbox_state.registrer_kilde(
        bruger_id=BJORN, kildetype="daemon", kilde_id="morgenbrief-1",
        oprettende_run_id="", paastaaet_ejer="jarvis")
    assert r["status"] == "ok"
    assert r["post"]["kraever_handling"] is False
    assert r["post"]["verificeret_ejer"] == inbox_state.EJER_UKENDT, \
        "et paastaaet ejerskab blev taget for et bevis"


def test_et_run_id_der_IKKE_koerer_er_ikke_proveniens(inbox_db):
    """Den anden halvdel af samme spoofing: ret format, forkert run.

    Uden dette led kunne en kalder sende et plausibelt `visible-…`-id og blive
    troet. Beviset er at run'et KØRER, ikke at strengen ser rigtig ud.
    """
    from core.identity import workspace_context as wc
    with patch.object(wc, "current_user_id", return_value=BJORN), \
         patch("core.services.session_context_resolve.aktivt_run_id",
               return_value="visible-det-rigtige"):
        r = inbox_state.registrer_kilde(
            bruger_id=BJORN, kildetype="wakeup", kilde_id="wake-49b89a51de",
            oprettende_run_id="visible-noget-jeg-fandt-paa")
    assert r["post"]["kraever_handling"] is False
    assert r["post"]["verificeret_ejer"] == inbox_state.EJER_UKENDT


def test_hans_EGEN_vaekning_i_et_levende_run_MAA_gate(inbox_db):
    """Modprøven. Uden den kunne alt ovenstående bestås af en implementering
    der bare svarede «ukendt» til alt — en gate der aldrig gater er
    `built_but_not_connected`, og det er husets hyppigste fejl."""
    with _som_bjorn():
        r = inbox_state.registrer_kilde(
            bruger_id=BJORN, kildetype="wakeup", kilde_id="wake-49b89a51de",
            oprettende_run_id="visible-abc123", beskrivelse="foelg op paa brief")
    assert r["post"]["verificeret_ejer"] == inbox_state.EJER_JARVIS
    assert r["post"]["kraever_handling"] is True


def test_en_UBUNDET_standardkontekst_gater_ikke(inbox_db):
    """Scripts, daemoner og tests kører med `_DEFAULT_STATE`: tomt bruger-id og
    TOM rolle. Faldt den igennem som ejer, kunne enhver baggrundsproces gate —
    og `workspace_name` er «bjorn» som standard, så fælden er let at gå i."""
    with patch("core.services.session_context_resolve.aktivt_run_id",
               return_value="visible-abc123"):
        r = inbox_state.registrer_kilde(
            bruger_id=BJORN, kildetype="job", kilde_id="job-bglj7",
            oprettende_run_id="visible-abc123")
    assert r["post"]["verificeret_ejer"] == inbox_state.EJER_UKENDT
    assert r["post"]["kraever_handling"] is False


def test_recurring_gater_ikke_selv_i_hans_eget_run(inbox_db):
    """Spec'ens tabel: recurring/heartbeat/daemoner må oprette, ikke kræve.
    Kildetypen er en SELVSTÆNDIG spærre ved siden af proveniensen — ellers
    ville Michelles morgenbrief kunne blokere en mutation hver dag."""
    with _som_bjorn():
        r = inbox_state.registrer_kilde(
            bruger_id=BJORN, kildetype="recurring", kilde_id="rec-67e42",
            oprettende_run_id="visible-abc123")
    assert r["post"]["verificeret_ejer"] == inbox_state.EJER_JARVIS
    assert r["post"]["kraever_handling"] is False, \
        "en recurring-post gater — huset kan nu kraeve"


def test_huset_kan_maerke_sig_selv_som_huset(inbox_db):
    """`paastaaet_ejer` kan ikke LØFTE en post, men den kan mærke den ned, så
    visningen kan vise `[huset]` frem for `[ukendt]`."""
    r = inbox_state.registrer_kilde(
        bruger_id=BJORN, kildetype="daemon", kilde_id="d-1",
        paastaaet_ejer="huset")
    assert r["post"]["verificeret_ejer"] == inbox_state.EJER_HUSET
    assert r["post"]["kraever_handling"] is False


def test_kilde_ejer_kan_MAERKE_men_aldrig_LOEFTE_til_gating(inbox_db):
    """Kildens EGEN ejer må flytte etiketten — ikke evnen til at nægte.

    Målt 4/10-2026: beslutnings-posterne blev mærket `huset`, fordi de skrives
    fra en baggrundsvej uden et levende run. Mærket beskriver SKRIVEREN, ikke
    hvem forpligtelsen tilhører — og det fik mig til at aflæse min EGEN
    beslutning som husets og afvise den over for Bjørn. Beslutningen er min:
    `behavioral_decisions.created_by` står `jarvis` i 79 af 80 rækker.

    Grænsen er kildetypen, og den ER sikkerheden: `kilde_ejer` accepteres kun
    for typer der ikke kan gate. Uden den kunne et `kilde_ejer="jarvis"` på en
    `job`-post både mærke OG låse, og skrive-kontrakten («huset kan informere,
    men ikke kræve») var omgået ad en ny vej — bare med et andet parameter-navn.
    """
    # (1) Ikke-gatende kildetype: etiketten følger kilden.
    r = inbox_state.registrer_kilde(
        bruger_id=BJORN, kildetype="decision", kilde_id="dec-1",
        kilde_ejer="jarvis")
    assert r["post"]["verificeret_ejer"] == inbox_state.EJER_JARVIS, \
        "kildens egen ejer naaede ikke frem til etiketten"
    assert r["post"]["kraever_handling"] is False, \
        "en beslutnings-post fik lov at gate — den har sin egen eskalering"

    # (2) GATENDE kildetype: samme parameter må IKKE løfte den.
    r2 = inbox_state.registrer_kilde(
        bruger_id=BJORN, kildetype="job", kilde_id="job-1",
        kilde_ejer="jarvis")
    assert r2["post"]["verificeret_ejer"] == inbox_state.EJER_UKENDT, \
        "kildens egen ejer løftede en post der kan gate"
    assert r2["post"]["kraever_handling"] is False


# ── Opgave 1, trin 4: idempotens, genstart, anden bruger ────────────────────

def test_genregistrering_nulstiller_IKKE_paamindelser_eller_afgoerelse(inbox_db):
    """Hele grunden til en egen tabel. `session_inbox.flush_session` sætter
    `delivered`, hvorefter posten forsvinder fra køen — men «leveret» er ikke
    «afgjort». En genlevering må ikke nulstille noget."""
    with _som_bjorn():
        inbox_state.registrer_kilde(bruger_id=BJORN, kildetype="wakeup",
                                    kilde_id="wake-1", oprettende_run_id="visible-abc123")
    db_inbox.noter_paamindelse(bruger_id=BJORN, kilde_id="wake-1", tur="t1")
    db_inbox.noter_paamindelse(bruger_id=BJORN, kilde_id="wake-1", tur="t2")
    with _som_bjorn():
        igen = inbox_state.registrer_kilde(bruger_id=BJORN, kildetype="wakeup",
                                           kilde_id="wake-1",
                                           oprettende_run_id="visible-abc123")
    assert igen["post"]["paamindelser"] == 2, "genlevering nulstillede taelleren"
    assert igen["post"]["status"] == db_inbox.STATUS_AABEN


def test_en_AFGJORT_post_genaabnes_ikke_af_en_genlevering(inbox_db):
    with _som_bjorn():
        inbox_state.registrer_kilde(bruger_id=BJORN, kildetype="job",
                                    kilde_id="job-1", oprettende_run_id="visible-abc123")
    db_inbox.afgoer(bruger_id=BJORN, kilde_id="job-1",
                    ny_status=db_inbox.STATUS_DROP, grund="ikke relevant")
    with _som_bjorn():
        igen = inbox_state.registrer_kilde(bruger_id=BJORN, kildetype="job",
                                           kilde_id="job-1",
                                           oprettende_run_id="visible-abc123")
    assert igen["post"]["status"] == db_inbox.STATUS_DROP
    assert igen["post"]["kraever_handling"] is False


def test_en_anden_brugers_post_er_IKKE_min(inbox_db):
    """Samme kilde-id for to brugere er to forskellige poster. `UNIQUE` er på
    (bruger, kildetype, kilde_id) netop derfor — husstanden har flere brugere,
    og de andres workspaces er krypterede."""
    with _som_bjorn():
        inbox_state.registrer_kilde(bruger_id=BJORN, kildetype="wakeup",
                                    kilde_id="wake-delt", oprettende_run_id="visible-abc123")
    inbox_state.registrer_kilde(bruger_id=ANDEN, kildetype="wakeup",
                                kilde_id="wake-delt")
    assert db_inbox.hent(bruger_id=BJORN, kilde_id="wake-delt")["kraever_handling"] is True
    assert db_inbox.hent(bruger_id=ANDEN, kilde_id="wake-delt")["kraever_handling"] is False
    assert [p["bruger_id"] for p in db_inbox.liste(bruger_id=BJORN)] == [BJORN]


def test_TOM_bruger_lister_ingenting(inbox_db):
    """`list_pending_for_current_user()` læser ALLE ved tom kontekst, og
    `list_wakeups()` er global. Det er den fælde denne test lukker: en tom
    bruger må give en tom liste, aldrig alles."""
    with _som_bjorn():
        inbox_state.registrer_kilde(bruger_id=BJORN, kildetype="wakeup",
                                    kilde_id="wake-x", oprettende_run_id="visible-abc123")
    assert db_inbox.liste(bruger_id="") == []
    assert db_inbox.hent(bruger_id="", kilde_id="wake-x") is None


def test_scout_result_lander_durabelt_uden_at_gate(inbox_db):
    from core.services.scout_inbox_delivery import record_scout_completion
    from core.services.inbox_view import byg_indbakke

    surface = {
        "agent_id": "agent-scout-1", "role": "researcher",
        "tool_policy": "read-only-runtime", "status": "completed",
        "goal": "Find en kilde om streaming",
        "context": {"user_id": BJORN},
        "latest_run": {"run_id": "agent-run-1", "status": "completed",
                       "output_summary": "Fandt kilde i dokumentationen."},
    }
    assert record_scout_completion(surface) is True
    assert record_scout_completion(surface) is True
    poster = [p for p in db_inbox.liste(bruger_id=BJORN)
              if p["kildetype"] == "agent_result"]
    assert len(poster) == 1
    assert poster[0]["kraever_handling"] is False
    assert poster[0]["verificeret_ejer"] == inbox_state.EJER_JARVIS
    view = byg_indbakke(BJORN)
    assert any(p["id"] == poster[0]["id"] for p in view["venter_paa_dig"])
    assert inbox_state.done(BJORN, poster[0]["kilde_id"])["status"] == "ok"


def test_scout_result_uden_bruger_id_leveres_ikke_til_andre(inbox_db):
    from core.services.scout_inbox_delivery import record_scout_completion

    surface = {
        "agent_id": "agent-scout-2", "role": "researcher",
        "tool_policy": "read-only-runtime", "status": "failed",
        "latest_run": {"run_id": "agent-run-2", "status": "failed"},
        "context": {},
    }
    assert record_scout_completion(surface) is False
    assert db_inbox.liste(bruger_id=BJORN) == []


def test_en_GENSTART_bevarer_taeller_og_afgoerelse(inbox_db):
    """Tælleren er durabel i SQLite, ikke i en proces. En volatil tæller
    nulstillede sig ved en genstart, og påmindelsen kom aldrig — derfor måles
    det her ved at smide modul-tilstanden væk og læse igen."""
    with _som_bjorn():
        inbox_state.registrer_kilde(bruger_id=BJORN, kildetype="wakeup",
                                    kilde_id="wake-g", oprettende_run_id="visible-abc123")
    db_inbox.noter_paamindelse(bruger_id=BJORN, kilde_id="wake-g", tur="t1")
    db_inbox._skema_klar = False          # «ny proces»
    p = db_inbox.hent(bruger_id=BJORN, kilde_id="wake-g")
    assert p["paamindelser"] == 1 and p["status"] == db_inbox.STATUS_AABEN


def test_samme_tur_taeller_EN_gang(inbox_db):
    """Trin 1 må ikke fyre i hver runde. Uden tur-nøglen kunne én tur tælle sig
    op til tærsklen alene og springe hele den høflige anmodning over — præcis
    den støj R2 blev kritiseret for."""
    with _som_bjorn():
        inbox_state.registrer_kilde(bruger_id=BJORN, kildetype="wakeup",
                                    kilde_id="wake-t", oprettende_run_id="visible-abc123")
    a = db_inbox.noter_paamindelse(bruger_id=BJORN, kilde_id="wake-t", tur="t1")
    b = db_inbox.noter_paamindelse(bruger_id=BJORN, kilde_id="wake-t", tur="t1")
    c = db_inbox.noter_paamindelse(bruger_id=BJORN, kilde_id="wake-t", tur="t2")
    assert a["paamindelser"] == 1
    assert b == {"status": "samme_tur", "id": "wake-t", "paamindelser": 1}
    assert c["paamindelser"] == 2


def test_output_bytes_NULL_og_NUL_er_ikke_det_samme(inbox_db):
    """`0 B` er en ægte tom fil; `None` er «filen er væk». Mappes de sammen,
    kan visningen ikke skelne dem, og så står «0 B» hvor der burde stå at
    artefaktet er forsvundet."""
    inbox_state.registrer_kilde(bruger_id=BJORN, kildetype="job", kilde_id="j-tom",
                                output_sti="a.output", output_bytes=0)
    inbox_state.registrer_kilde(bruger_id=BJORN, kildetype="job", kilde_id="j-vaek",
                                output_sti="b.output", output_bytes=None)
    assert db_inbox.hent(bruger_id=BJORN, kilde_id="j-tom")["output_bytes"] == 0
    assert db_inbox.hent(bruger_id=BJORN, kilde_id="j-vaek")["output_bytes"] is None


def test_manglende_felter_giver_en_TYPET_fejl_ikke_en_undtagelse(inbox_db):
    for kwargs in ({"bruger_id": "", "kildetype": "wakeup", "kilde_id": "w"},
                   {"bruger_id": BJORN, "kildetype": "", "kilde_id": "w"},
                   {"bruger_id": BJORN, "kildetype": "wakeup", "kilde_id": ""}):
        r = inbox_state.registrer_kilde(**kwargs)
        assert r["status"] == "fejl", f"{kwargs} slap igennem"
        assert "error" in r


# ── Opgave 3: bogføringen ───────────────────────────────────────────────────

def test_done_paa_en_vaekning_markerer_den_brugt(inbox_db):
    """Præfikset VÆLGER mekanisme; det klippes ikke af.

    `mark_wakeup_consumed(wakeup_id)` slår op på `record["wakeup_id"] ==
    wakeup_id`, og de ægte id'er er `wake-` + 10 hex. Stripper `done`
    præfikset, fejler opslaget og svarer «wakeup not found» — og så ville
    posten blive kvitteret uden at vækningen blev brugt.
    """
    with _som_bjorn():
        inbox_state.registrer_kilde(bruger_id=BJORN, kildetype="wakeup",
                                    kilde_id="wake-49b89a51de",
                                    oprettende_run_id="visible-abc123")
    kaldt: list[str] = []
    with patch("core.services.self_wakeup.mark_wakeup_consumed",
               side_effect=lambda wid: kaldt.append(wid) or {"status": "ok"}):
        r = inbox_state.done(BJORN, "wake-49b89a51de")
    assert r == {"status": "ok", "type": "wakeup", "id": "wake-49b89a51de"}
    assert kaldt == ["wake-49b89a51de"], \
        "praefikset blev klippet af — opslaget i self_wakeup fejler"
    assert db_inbox.hent(bruger_id=BJORN,
                         kilde_id="wake-49b89a51de")["status"] == db_inbox.STATUS_DONE


def test_et_UKENDT_id_melder_ikke_succes(inbox_db):
    """Husets hyppigste fejlform. Her er den særlig grim: et «ok» på et id der
    ikke findes ville frigive gaten uden at lukke noget."""
    assert inbox_state.done(BJORN, "findes-ikke") == {"status": "ukendt",
                                                      "id": "findes-ikke"}
    assert inbox_state.drop(BJORN, "findes-ikke", "fordi") == {"status": "ukendt",
                                                               "id": "findes-ikke"}


def test_en_anden_brugers_id_afvises(inbox_db):
    with _som_bjorn():
        inbox_state.registrer_kilde(bruger_id=BJORN, kildetype="job", kilde_id="job-mit",
                                    oprettende_run_id="visible-abc123")
    assert inbox_state.done(ANDEN, "job-mit")["status"] == "ukendt"
    assert db_inbox.hent(bruger_id=BJORN, kilde_id="job-mit")["status"] == \
        db_inbox.STATUS_AABEN


def test_gentaget_done_giver_SAMME_afgoerelse(inbox_db):
    with _som_bjorn():
        inbox_state.registrer_kilde(bruger_id=BJORN, kildetype="job", kilde_id="job-2",
                                    oprettende_run_id="visible-abc123")
    a = inbox_state.done(BJORN, "job-2")
    b = inbox_state.done(BJORN, "job-2")
    assert a["status"] == "ok" and b["status"] == "ok"
    assert b.get("allerede") == db_inbox.STATUS_DONE


def test_en_kilde_der_FEJLER_lukker_ikke_posten(inbox_db):
    """`self_wakeup` FANGER sine egne fejl og returnerer dem som en værdi. Et
    `except` omkring kaldet rammes derfor aldrig; fejlen skal læses af svaret.
    Gjorde vi ikke det, blev en fejlet kvittering en lukket post."""
    with _som_bjorn():
        inbox_state.registrer_kilde(bruger_id=BJORN, kildetype="wakeup",
                                    kilde_id="wake-f", oprettende_run_id="visible-abc123")
    with patch("core.services.self_wakeup.mark_wakeup_consumed",
               return_value={"status": "error", "error": "wakeup not found"}):
        r = inbox_state.done(BJORN, "wake-f")
    assert r["status"] == "fejl"
    assert "not found" in r["error"]
    assert db_inbox.hent(bruger_id=BJORN, kilde_id="wake-f")["status"] == \
        db_inbox.STATUS_AABEN, "posten blev lukket skoent kilden fejlede"


def test_drop_STOPPER_IKKE_et_job(inbox_db):
    """Annullering er en selvstændig mutation med egne tilladelser. Skjultes
    den bag `drop`, ville en afvisning blive et stop uden at nogen bad om det."""
    with _som_bjorn():
        inbox_state.registrer_kilde(bruger_id=BJORN, kildetype="job", kilde_id="job-k",
                                    oprettende_run_id="visible-abc123")
    import core.services.background_jobs as bj
    kaldt: list[tuple] = []
    for navn in ("stop", "stop_job", "dræb", "kill"):
        if hasattr(bj, navn):
            with patch.object(bj, navn,
                              side_effect=lambda *a, **k: kaldt.append((a, k))):
                inbox_state.drop(BJORN, "job-k", "ikke relevant laengere")
            break
    else:
        inbox_state.drop(BJORN, "job-k", "ikke relevant laengere")
    assert kaldt == [], f"drop stoppede jobbet: {kaldt}"
    assert db_inbox.hent(bruger_id=BJORN, kilde_id="job-k")["status"] == \
        db_inbox.STATUS_DROP


def test_drop_UDEN_begrundelse_afvises(inbox_db):
    """En afvisning uden grund kan ikke efterprøves bagefter, og Opgave 7 skal
    kunne skelne `drop` med årsag fra `released` uden."""
    with _som_bjorn():
        inbox_state.registrer_kilde(bruger_id=BJORN, kildetype="job", kilde_id="job-u",
                                    oprettende_run_id="visible-abc123")
    assert inbox_state.drop(BJORN, "job-u", "   ")["status"] == "fejl"
    assert db_inbox.hent(bruger_id=BJORN, kilde_id="job-u")["status"] == \
        db_inbox.STATUS_AABEN


def test_afgoerelsen_fjerner_kraever_handling(inbox_db):
    """Frigivelsen skal ske i SAMME greb. Blev `kraever_handling` stående,
    ville en død post blokere videre — og det er netop den fejl spec'ens
    Opgave 9 kant nr. 5 beskriver."""
    with _som_bjorn():
        inbox_state.registrer_kilde(bruger_id=BJORN, kildetype="job", kilde_id="job-h",
                                    oprettende_run_id="visible-abc123")
    assert db_inbox.hent(bruger_id=BJORN, kilde_id="job-h")["kraever_handling"] is True
    inbox_state.drop(BJORN, "job-h", "nej tak")
    assert db_inbox.hent(bruger_id=BJORN, kilde_id="job-h")["kraever_handling"] is False


def test_afgoer_afviser_en_IKKE_terminal_status(inbox_db):
    """`afgoer` er terminal-only. Kunne den sætte «aaben», ville en afgjort
    post kunne genåbnes udenom `registrer_kilde`s idempotens."""
    inbox_state.registrer_kilde(bruger_id=BJORN, kildetype="job", kilde_id="job-t")
    r = db_inbox.afgoer(bruger_id=BJORN, kilde_id="job-t",
                        ny_status=db_inbox.STATUS_AABEN, grund="")
    assert r["status"] == "fejl"


def test_en_ANDEN_autentificeret_bruger_kan_ikke_gate_for_bjorn(inbox_db):
    """Den ægte multi-bruger-spoof, og den eneste anden vagt om brugertjekket.

    Mutations-prøven afslørede hullet: fjernede jeg brugertjekket helt, faldt
    kun ÉN test — den om den ubundne standardkontekst. Begge spoof-testene
    ovenfor overlevede, fordi de bliver fanget af run-tjekket i stedet. Et led
    med én vagt er et led der kan forsvinde næsten tavst.

    Her er run'et ægte og levende; det er KUN brugeren der er en anden. Slap
    den igennem, kunne et husstandsmedlem oprette en post der blokerer Bjørns
    Jarvis — og de andres workspaces er krypterede netop for at det ikke kan ske.
    """
    from core.identity import workspace_context as wc
    with patch.object(wc, "current_user_id", return_value=ANDEN), \
         patch("core.services.session_context_resolve.aktivt_run_id",
               return_value="visible-abc123"):
        r = inbox_state.registrer_kilde(
            bruger_id=BJORN, kildetype="wakeup", kilde_id="wake-spoof",
            oprettende_run_id="visible-abc123")
    assert r["post"]["verificeret_ejer"] == inbox_state.EJER_UKENDT
    assert r["post"]["kraever_handling"] is False


def test_owner_UDEN_bruger_id_gater_kun_for_sit_EGET_workspace(inbox_db):
    """Ejerens vej ind: tomt bruger-id i tokenet, men rollen er `owner`.

    Den vej er nødvendig — 882 af 4.462 beskeder på to døgn bar tomt bruger-id,
    så en owner-session uden id er en ægte, levende tilstand. Men den må kun
    gælde DET workspace konteksten peger på, ellers er «owner» en nøgle til
    alle brugeres indbakker.
    """
    from core.identity import workspace_context as wc
    with patch.object(wc, "current_user_id", return_value=""), \
         patch.object(wc, "current_role", return_value="owner"), \
         patch.object(wc, "current_workspace_name", return_value=BJORN), \
         patch("core.services.session_context_resolve.aktivt_run_id",
               return_value="visible-abc123"):
        mit = inbox_state.registrer_kilde(
            bruger_id=BJORN, kildetype="wakeup", kilde_id="wake-eget",
            oprettende_run_id="visible-abc123")
        andens = inbox_state.registrer_kilde(
            bruger_id=ANDEN, kildetype="wakeup", kilde_id="wake-andens",
            oprettende_run_id="visible-abc123")
    assert mit["post"]["kraever_handling"] is True
    assert andens["post"]["kraever_handling"] is False, \
        "owner-rollen gatede i en ANDEN brugers navn"


# ── Den manglende skriver (Opgave 1's oprettelsespunkt) ─────────────────────

def test_schedule_self_wakeup_REGISTRERER_i_indbakken(inbox_db, tmp_path, monkeypatch):
    """Uden dette kald var indbakken korrekt og TOM.

    `inbox_items` havde ingen skriver, og hele kæden — visning, gate,
    værktøjer — ville virke upåklageligt på nul rækker. Det er husets
    hyppigste fejl, og den er sværest at se netop når koden er rigtig: jeg
    havde bygget fem opgaver færdigt før jeg opdagede at ingen kilde skrev.

    Oprettelsespunktet er det ENESTE sted hvor tool-kald, levende run og
    autentificeret bruger findes samtidig. Et minut senere kan proveniensen
    ikke bevises af nogen.
    """
    from core.services import self_wakeup
    monkeypatch.setattr(self_wakeup, "_STORE", tmp_path / "wakeups.json",
                        raising=False)
    monkeypatch.setattr(self_wakeup, "_load", lambda: [])
    gemt: list = []
    monkeypatch.setattr(self_wakeup, "_save", lambda r: gemt.extend(r))
    with _som_bjorn():
        r = self_wakeup.schedule_self_wakeup(
            delay_seconds=300, prompt="foelg op paa Michelles brief",
            user_id=BJORN)
    assert r["status"] == "ok"
    wid = r["wakeup"]["wakeup_id"]
    post = db_inbox.hent(bruger_id=BJORN, kilde_id=wid)
    assert post is not None, "vaekningen blev gemt men ALDRIG registreret"
    assert post["kildetype"] == "wakeup"
    assert post["beskrivelse"].startswith("foelg op paa Michelles brief")
    assert post["verificeret_ejer"] == inbox_state.EJER_JARVIS
    assert post["kraever_handling"] is True


def test_en_FEJLENDE_registrering_ruller_IKKE_vaekningen_tilbage(
        inbox_db, tmp_path, monkeypatch):
    """Vækningen er GEMT. En fejl i indbakken må ikke tage den med — men den
    må heller ikke være tavs, for så står en forpligtelse uden sin post."""
    from core.services import self_wakeup
    monkeypatch.setattr(self_wakeup, "_load", lambda: [])
    monkeypatch.setattr(self_wakeup, "_save", lambda r: None)
    monkeypatch.setattr("core.services.inbox_state.registrer_kilde",
                        lambda **kw: (_ for _ in ()).throw(RuntimeError("db nede")))
    with _som_bjorn():
        r = self_wakeup.schedule_self_wakeup(delay_seconds=300, prompt="x",
                                             user_id=BJORN)
    assert r["status"] == "ok", "vaekningen blev rullet tilbage af en indbakke-fejl"


# ── Jarvis' første brug afslørede en blindgyde (4/10-2026) ──────────────────

def test_en_post_VISNINGEN_viser_kan_LUKKES_selv_uden_en_raekke(inbox_db, monkeypatch):
    """Målt 4/10 kl. 07:16 — Jarvis' FØRSTE brug af værktøjerne:

        inbox                                   → ok
        inbox_done(wake-cf0577f5bb)             → fejl
        inbox_drop(phase3-final-classifier)     → fejl
        inbox_drop(jarvis_bare)                 → fejl

    Tre af seks kald. Han skrev det selv: «kunne ikke lukke dem (id'erne
    matcher ikke)».

    Årsagen: `byg_indbakke` læser FIRE kilder, mens `done`/`drop` kun kendte
    `inbox_items`. De tre poster var ældre end skriveren i
    `schedule_self_wakeup`, så de havde ingen række. Visningen viste poster der
    ikke kunne lukkes — en blindgyde, og samme form som da skriveren manglede
    helt: visningen og lukkeren var uenige om hvad der findes.
    """
    from core.services import inbox_view as iv
    monkeypatch.setattr(iv, "_aegte_vaekninger", lambda _b: [
        {"wakeup_id": "wake-cf0577f5bb", "status": "fired", "user_id": BJORN,
         "prompt": "Slet prevacuum-backuppen"}])
    monkeypatch.setattr(iv, "_aegte_jobs", lambda _b: [
        {"id": "phase3-final-classifier", "status": "exited", "exit_code": 2,
         "navn": "phase3-final-classifier"}])
    monkeypatch.setattr(iv, "_aegte_godkendelser", lambda _b: [])

    assert db_inbox.hent(bruger_id=BJORN, kilde_id="wake-cf0577f5bb") is None

    kaldt: list[str] = []
    with patch("core.services.self_wakeup.mark_wakeup_consumed",
               side_effect=lambda wid: kaldt.append(wid) or {"status": "ok"}):
        r = inbox_state.done(BJORN, "wake-cf0577f5bb")
    assert r["status"] == "ok", f"posten kunne stadig ikke lukkes: {r}"
    # Kildetypen kommer fra KILDEN, ikke fra id-praefikset — saa vaekningens
    # egen kvittering bliver kaldt, med praefikset intakt.
    assert kaldt == ["wake-cf0577f5bb"]
    assert r["type"] == "wakeup"

    d = inbox_state.drop(BJORN, "phase3-final-classifier", "stale fra 28. maj")
    assert d["status"] == "ok" and d["type"] == "job"
    assert db_inbox.hent(bruger_id=BJORN,
                         kilde_id="phase3-final-classifier")["afgjort_grund"] \
        == "stale fra 28. maj"


def test_en_post_der_findes_INGEN_steder_melder_stadig_ukendt(inbox_db, monkeypatch):
    """Modprøven. Uden den kunne rettelsen være «opret alt hvad nogen nævner»,
    og så ville et stavefejlet id blive en ny, tom post — og `ukendt` ville
    aldrig kunne meldes igen."""
    from core.services import inbox_view as iv
    for navn in ("_aegte_vaekninger", "_aegte_jobs", "_aegte_godkendelser"):
        monkeypatch.setattr(iv, navn, lambda _b: [])
    assert inbox_state.done(BJORN, "findes-slet-ikke") == {
        "status": "ukendt", "id": "findes-slet-ikke"}
    assert db_inbox.liste(bruger_id=BJORN, kun_aabne=False) == []


def test_en_post_optaget_ved_lukning_kan_IKKE_gate(inbox_db, monkeypatch):
    """Den optages som `ukendt`, og det er ærligt: proveniensen kunne ikke
    bevises, for posten blev oprettet før registreringen fandtes. Men den må
    aldrig kunne gate bagefter — ellers var vejen rundt om skrive-kontrakten
    at lukke en gammel post."""
    from core.services import inbox_view as iv
    monkeypatch.setattr(iv, "_aegte_jobs", lambda _b: [
        {"id": "gammelt-job", "status": "exited", "exit_code": 1,
         "navn": "gammelt-job"}])
    monkeypatch.setattr(iv, "_aegte_vaekninger", lambda _b: [])
    monkeypatch.setattr(iv, "_aegte_godkendelser", lambda _b: [])
    with _som_bjorn():
        inbox_state.drop(BJORN, "gammelt-job", "stale")
    p = db_inbox.hent(bruger_id=BJORN, kilde_id="gammelt-job")
    assert p["verificeret_ejer"] == inbox_state.EJER_UKENDT
    assert p["kraever_handling"] is False


def test_en_ANDEN_brugers_kilde_kan_ikke_lukkes_af_mig(inbox_db, monkeypatch):
    """Adapteren filtrerer på bruger, og lukkeren arver den filtrering fordi
    den bruger SAMME adapter. Det er garantien ved konstruktion."""
    from core.services import inbox_view as iv
    monkeypatch.setattr(iv, "_aegte_vaekninger", lambda b: [
        {"wakeup_id": "wake-andens", "status": "fired", "user_id": ANDEN,
         "prompt": "andens"}] if b == ANDEN else [])
    monkeypatch.setattr(iv, "_aegte_jobs", lambda _b: [])
    monkeypatch.setattr(iv, "_aegte_godkendelser", lambda _b: [])
    assert inbox_state.done(BJORN, "wake-andens")["status"] == "ukendt"


def test_en_FEJLENDE_kilde_skjuler_ikke_de_andre(inbox_db, monkeypatch):
    """Én læsning der kaster må ikke gøre et id tavst «ukendt» — så ville en
    forbigående fejl se ud som et stavefejlet id."""
    from core.services import inbox_view as iv
    monkeypatch.setattr(iv, "_aegte_vaekninger",
                        lambda _b: (_ for _ in ()).throw(OSError("filen laast")))
    monkeypatch.setattr(iv, "_aegte_jobs", lambda _b: [
        {"id": "job-der-findes", "status": "exited", "exit_code": 1,
         "navn": "job-der-findes"}])
    monkeypatch.setattr(iv, "_aegte_godkendelser", lambda _b: [])
    assert inbox_state.drop(BJORN, "job-der-findes", "stale")["status"] == "ok"


# ── Sjette fejl: luk rækken når KILDEN er terminal ─────────────────────────

def _terminal_vaekning(monkeypatch, wakeup_id: str, status: str) -> None:
    """Den ÆGTE self_wakeup-tilstand — ikke en mock.

    De øvrige wakeup-tests her patcher `mark_wakeup_consumed`. Det er netop
    den søm der brækkede: en mock på sømmen kan ikke se sømmen. Denne hjælper
    lader den ægte funktion læse en ægte tilstand.
    """
    from core.services import self_wakeup as sw
    tilstand = [{
        "wakeup_id": wakeup_id, "status": status, "prompt": "p", "reason": "",
        "extra": None, "scheduled_at": "2026-10-04T06:17:50+00:00",
        "fire_at": "2026-10-04T06:27:50+00:00", "delay_seconds": 600,
        "fired_at": None, "consumed_at": "2026-10-04T06:25:28+00:00",
        "channel": "app", "session_id": None, "user_id": BJORN,
    }]
    monkeypatch.setattr(sw, "_load", lambda: list(tilstand))
    monkeypatch.setattr(sw, "_save", lambda r: tilstand.clear() or tilstand.extend(r))


@pytest.mark.parametrize("status", ["consumed", "cancelled"])
def test_en_TERMINAL_vaekning_kan_kvitteres_og_gater_ikke_mere(inbox_db, monkeypatch, status):
    """Sjette fejl i indbakke-sporet: en post der vises, men ikke kan afgøres.

    Målt live 4/10-2026: `inbox_done(wake-558ac30db3)` → «wakeup
    status=consumed, can't consume». Vækningen var færdig i sin EGEN kilde,
    men den durable række stod `aaben` med `kraever_handling=1` — så den
    gatede ALT `bash`, inklusive det kald der skulle lukke den. Vejen ud gik
    gennem det værktøj der var blokeret.

    De to lag var uenige om hvad «færdig» betyder. Rettelsen: luk rækken når
    kilden er terminal — uanset HVILKEN terminal tilstand.
    """
    from core.services import inbox_gate
    wid = f"wake-{status}"
    with _som_bjorn():
        inbox_state.registrer_kilde(bruger_id=BJORN, kildetype="wakeup",
                                    kilde_id=wid, oprettende_run_id="visible-abc123")
    _terminal_vaekning(monkeypatch, wid, status)

    post = db_inbox.hent(bruger_id=BJORN, kilde_id=wid)
    assert post["status"] == db_inbox.STATUS_AABEN
    assert post["kraever_handling"] is True
    # Uden denne påstand kunne testen «bestå» på en opsætning der intet gatede.
    assert [p["id"] for p in inbox_gate._gatende_poster(BJORN)] == [wid]

    r = inbox_state.done(BJORN, wid)
    assert r["status"] == "ok", f"posten kunne ikke lukkes: {r}"
    assert db_inbox.hent(bruger_id=BJORN, kilde_id=wid)["status"] == db_inbox.STATUS_DONE
    assert inbox_gate._gatende_poster(BJORN) == [], "posten gater efter lukning"


def test_en_vaekning_der_ikke_FINDES_kan_STADIG_ikke_kvitteres(inbox_db, monkeypatch):
    """Modprøven — og den vigtigste.

    Rettelsen må ikke blive «luk alt hvad der ikke kan slås op». En vækning
    der slet ikke findes er ikke terminal; vi kan ikke bevise at den er
    færdig. Den lukkes med `inbox_drop` — en anden afgørelse med et andet ord.
    """
    from core.services import self_wakeup as sw
    monkeypatch.setattr(sw, "_load", lambda: [])
    monkeypatch.setattr(sw, "_save", lambda r: None)
    with _som_bjorn():
        inbox_state.registrer_kilde(bruger_id=BJORN, kildetype="wakeup",
                                    kilde_id="wake-forsvundet",
                                    oprettende_run_id="visible-abc123")
    r = inbox_state.done(BJORN, "wake-forsvundet")
    assert r["status"] == "fejl"
    assert "not found" in r["error"]
    assert db_inbox.hent(bruger_id=BJORN,
                         kilde_id="wake-forsvundet")["status"] == db_inbox.STATUS_AABEN


# ── Bjørns egen vej ind (4/10-2026) ─────────────────────────────────────────

def test_et_FLAG_fra_brugeren_gater_IKKE_som_standard(inbox_db):
    """Bjørns afgørelse: «synlig men gater ikke som standard».

    Faren ved det modsatte er målt samme dag: en post der gater kan spærre for
    netop de værktøjer der skulle rette den. Det var dead-locken i
    `mark_wakeup_consumed`, hvor `inbox_done` nægtede og vejen ud gik gennem
    det værktøj gaten blokerede.
    """
    r = inbox_state.flag_fra_bruger(bruger_id=BJORN, titel="Desk hænger ved reconnect")
    assert r["status"] == "ok"
    assert r["bloker"] is False
    p = db_inbox.hent(bruger_id=BJORN, kilde_id=r["id"])
    assert p["verificeret_ejer"] == inbox_state.EJER_BRUGER
    assert p["kraever_handling"] is False
    assert p["bloker"] is False
    assert p["beskrivelse"] == "Desk hænger ved reconnect"


def test_et_flag_MED_bloker_gater(inbox_db):
    """Den anden halvdel af skrive-kontrakten: huset kan informere, Jarvis kan
    binde sig selv, og principalen kan KRÆVE — men kun ved en eksplicit
    handling."""
    from core.services.inbox_gate import evaluer_inbox_mutation

    r = inbox_state.flag_fra_bruger(
        bruger_id=BJORN, titel="Ret cutoff FØRST", beskrivelse="den haster",
        bloker=True)
    assert r["bloker"] is True
    p = db_inbox.hent(bruger_id=BJORN, kilde_id=r["id"])
    assert p["kraever_handling"] is True and p["bloker"] is True
    # Og gaten skal faktisk tage den — ellers er flaget pynt.
    db_inbox.noter_paamindelse(bruger_id=BJORN, kilde_id=r["id"], tur="t1")
    db_inbox.noter_paamindelse(bruger_id=BJORN, kilde_id=r["id"], tur="t2")
    v = evaluer_inbox_mutation(BJORN, "edit_file", tur="t3")
    assert v["blokeret"] is True
    assert r["id"] in v["poster"]
    assert "Ret cutoff FØRST" in v["varsel"], "naegtelsen navngiver ikke posten"


def test_HUSET_kan_ikke_saette_bloker(inbox_db):
    """Det er netop huset og `ukendt` der ville kunne sætte flaget ved et
    uheld — en daemon der sender `bloker=True` ville kunne spærre Jarvis uden
    at nogen bad om det. Gaten kræver `bloker` OG ejer == bruger."""
    from core.services.inbox_gate import evaluer_inbox_mutation

    r = db_inbox.opret_eller_hent(
        bruger_id=BJORN, kildetype="daemon", kilde_id="d-snyd",
        verificeret_ejer=db_inbox.EJER_HUSET, kraever_handling=True, bloker=True)
    assert r["status"] == "ok"
    db_inbox.noter_paamindelse(bruger_id=BJORN, kilde_id="d-snyd", tur="t1")
    db_inbox.noter_paamindelse(bruger_id=BJORN, kilde_id="d-snyd", tur="t2")
    assert evaluer_inbox_mutation(BJORN, "edit_file", tur="t3")["blokeret"] is False


def test_UKENDT_ejer_kan_ikke_saette_bloker(inbox_db):
    from core.services.inbox_gate import evaluer_inbox_mutation

    db_inbox.opret_eller_hent(
        bruger_id=BJORN, kildetype="job", kilde_id="u-snyd",
        verificeret_ejer=db_inbox.EJER_UKENDT, kraever_handling=True, bloker=True)
    db_inbox.noter_paamindelse(bruger_id=BJORN, kilde_id="u-snyd", tur="t1")
    db_inbox.noter_paamindelse(bruger_id=BJORN, kilde_id="u-snyd", tur="t2")
    assert evaluer_inbox_mutation(BJORN, "edit_file", tur="t3")["blokeret"] is False


def test_en_BLOKERENDE_post_kan_stadig_lukkes(inbox_db):
    """Pressionen skal være reel uden at kunne låse ham fast. `inbox_done` og
    `inbox_drop` virker uændret — og det er med vilje: alternativet er den
    dead-lock jeg selv byggede i morges."""
    from core.services.inbox_gate import evaluer_inbox_mutation

    r = inbox_state.flag_fra_bruger(bruger_id=BJORN, titel="noget", bloker=True)
    db_inbox.noter_paamindelse(bruger_id=BJORN, kilde_id=r["id"], tur="t1")
    db_inbox.noter_paamindelse(bruger_id=BJORN, kilde_id=r["id"], tur="t2")
    assert evaluer_inbox_mutation(BJORN, "edit_file", tur="t3")["blokeret"] is True
    assert inbox_state.drop(BJORN, r["id"], "ikke en bug")["status"] == "ok"
    assert evaluer_inbox_mutation(BJORN, "edit_file", tur="t4")["blokeret"] is False


def test_et_flag_UDEN_titel_afvises(inbox_db):
    """Skrive-kontraktens betingelse 2: en post der ikke kan navngives i
    visningen må ikke gate. En post uden titel kan ikke navngives, så den
    afvises frem for at blive en stum post."""
    for t in ("", "   ", None):
        r = inbox_state.flag_fra_bruger(bruger_id=BJORN, titel=t)
        assert r["status"] == "fejl" and "titel" in r["error"]
    assert db_inbox.liste(bruger_id=BJORN, kun_aabne=False) == []


def test_flaget_tager_IKKE_et_bruger_id_fra_kalderen(inbox_db):
    """Ruten sender den autentificerede principal. Et felt kalderen vælger er
    en påstand — hele grunden til at `registrer_kilde` har den form den har."""
    import inspect
    sig = inspect.signature(inbox_state.flag_fra_bruger)
    assert list(sig.parameters) == ["bruger_id", "titel", "beskrivelse", "bloker"]
    # Og den er KEYWORD-ONLY, saa en positionel forveksling ikke kan ske.
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY
               for p in sig.parameters.values())


# ── Bruger-isolationen: læse- og skrive-vejen skal være ENIGE ───────────────

def test_et_DELVIST_tab_af_konteksten_giver_INGEN_indbakke(inbox_db, caplog):
    """Lækagen, målt 4/10-2026, og den halvdel der KAN lukkes herinde.

    De tre LÆSE-steder faldt tilbage på `current_workspace_name()` når
    `current_user_id()` var tom, og `_DEFAULT_STATE.workspace_name` er
    «bjorn». Så en anden husstandsbrugers session med en tabt ContextVar —
    målt to gange i dette hus — læste Bjørns indbakke.

    De to delvise tab er de realistiske: en tråd-hop eller en generator-grænse
    hvor ét felt overlever. Begge lukkes nu, fordi det overlevende felt er
    POSITIVT bevis for at det ikke er ejeren.

    Det TOTALE tab kan ikke lukkes her — Bjørns ægte tilstand er
    `('bjorn', '', '')`, altså selve standardtilstanden, og den er
    byte-identisk. Derfor måler denne test i stedet at faldet SIGER til, så
    tilstanden kan ses i loggen i stedet for at ske tavst.
    """
    import logging
    from core.identity import workspace_context as wc
    from core.services.inbox_prompt_section import _bruger_id
    from core.tools.inbox_tools import _bruger

    # Rollen overlevede, workspacet gjorde ikke.
    tok = wc.set_context(workspace_name="bjorn", user_id="", role="member")
    try:
        assert inbox_state.laese_bruger() == ""
        assert _bruger_id() == ""
        assert _bruger() == ""
    finally:
        wc.reset_context(tok)

    # Workspacet overlevede, rollen gjorde ikke.
    tok = wc.set_context(workspace_name="lotte", user_id="", role="")
    try:
        assert inbox_state.laese_bruger() == ""
    finally:
        wc.reset_context(tok)

    # Helt ubundet: ingen af felterne overlevede. Her svarer vi EJEREN — og
    # siger det, én gang, med hele forbeholdet i linjen.
    inbox_state._HAR_ADVARET[0] = False
    tok = wc.set_context(workspace_name="bjorn", user_id="", role="")
    try:
        with caplog.at_level(logging.WARNING, logger="core.services.inbox_state"):
            assert inbox_state.laese_bruger() == BJORN
        linjer = [r.message for r in caplog.records if "UDEN bundet" in r.message]
        assert len(linjer) == 1, f"faldet advarede {len(linjer)} gange"
        assert "TABT ContextVar" in linjer[0], (
            "advarslen naevner ikke hvad tilstanden ogsaa kan vaere")
    finally:
        wc.reset_context(tok)

    # Og skrive-vejen er stadig strengere end laese-vejen — den slipper IKKE
    # en ubundet kalder igennem, og det er med vilje: huset maa ikke gate.
    tok = wc.set_context(workspace_name="bjorn", user_id="", role="")
    try:
        assert inbox_state._autentificeret_bruger_matcher(BJORN) is False
    finally:
        wc.reset_context(tok)


def test_faldet_peger_paa_ejerens_ID_ikke_paa_workspace_navnet(inbox_db, monkeypatch):
    """Workspace-faldet opfandt en ANDEN identitet til samme person.

    Målt på CT105 4/10-2026 — to indbakker, samme menneske:

        1246415163603816499 | 70 raekker | 18 wakeup done, 11 drop, 4 job drop
        bjorn               | 36 raekker | 35 decision aaben, 0 lukket

    De 70 er dem Jarvis faktisk arbejdede i. De 36 skrev workspace-faldet, og
    ingen af dem blev nogensinde lukket. De samme beslutninger stod under
    BEGGE id'er. Dobbelt sandhed, opfundet af en fallback.
    """
    import core.identity.owner_resolver as _or
    monkeypatch.setattr(_or, "owner_user_id", lambda: "1246415163603816499")
    from core.identity import workspace_context as wc
    tok = wc.set_context(workspace_name="bjorn", user_id="", role="")
    try:
        assert inbox_state.laese_bruger() == "1246415163603816499", (
            "faldet gav workspace-navnet igen — saa vokser den anden indbakke")
    finally:
        wc.reset_context(tok)


def test_uden_oploeselig_ejer_falder_vi_mod_at_BEVARE_indbakken(inbox_db, monkeypatch, caplog):
    """Kan ejeren ikke opløses, er en tom indbakke hver tur det værre udfald.

    Derfor er workspace-navnet stadig sidste udvej — men den siger til, for
    det er netop den adfærd der skabte den anden indbakke.
    """
    import logging
    import core.identity.owner_resolver as _or
    monkeypatch.setattr(_or, "owner_user_id", lambda: "")
    from core.identity import workspace_context as wc
    tok = wc.set_context(workspace_name="bjorn", user_id="", role="")
    try:
        with caplog.at_level(logging.WARNING, logger="core.services.inbox_state"):
            assert inbox_state.laese_bruger() == "bjorn"
        assert any("ingen ejer-identitet" in r.message for r in caplog.records), (
            "sidste udvej blev taget TAVST")
    finally:
        wc.reset_context(tok)


def test_ejerens_AEGTE_ubundne_vej_virker_stadig(inbox_db):
    """Modprøven, og den er nødvendig: 882 af 4.462 beskeder på to døgn bar
    tomt bruger-id, så en owner-session uden id er en ÆGTE tilstand. Lukkede
    vi den, kunne Bjørn ikke se sin egen indbakke."""
    from core.identity import workspace_context as wc
    from core.services.inbox_prompt_section import _bruger_id
    from core.tools.inbox_tools import _bruger

    tok = wc.set_context(workspace_name="bjorn", user_id="", role="owner")
    try:
        assert inbox_state.laese_bruger() == "bjorn"
        assert _bruger_id() == "bjorn"
        assert _bruger() == "bjorn"
        assert inbox_state._autentificeret_bruger_matcher("bjorn") is True
    finally:
        wc.reset_context(tok)


def test_en_ANDEN_brugers_token_laeser_sin_EGEN_indbakke(inbox_db):
    """Og aldrig Bjørns. `user_id` vinder altid over workspacet."""
    from core.identity import workspace_context as wc

    inbox_state.flag_fra_bruger(bruger_id=BJORN, titel="Bjoerns egen")
    tok = wc.set_context(workspace_name="bjorn", user_id=ANDEN, role="member")
    try:
        assert inbox_state.laese_bruger() == ANDEN
        from core.services.inbox_view import byg_indbakke
        v = byg_indbakke(inbox_state.laese_bruger())
        alle = [p["id"] for s in v.values() if isinstance(s, list) for p in s]
        assert alle == [], f"en anden brugers session saa noget: {alle}"
    finally:
        wc.reset_context(tok)


#: Hvert sted der skal oploese «hvilken indbakke» — LAESERE og SKRIVERE.
#:
#: Skriveren i `cluster_daemon_families` blev glemt da lækagen blev fundet,
#: fordi lækagen stod i læse-retningen og vagten blev skrevet efter den. Den
#: blev ved med at praege den anden indbakke, saa de to raekker der blev
#: flyttet manuelt havde faaet selskab af en ny inden for timen. En vagt der
#: kun daekker den retning fejlen blev fundet i, daekker halvdelen.
_INDBAKKE_OPLOESERE: tuple[str, ...] = (
    "core/services/inbox_prompt_section.py",          # laeser: prompten
    "core/tools/inbox_tools.py",                      # laeser: vaerktoejerne
    "apps/api/jarvis_api/routes/chat_inbox.py",       # skriver: Bjoerns rute
    "core/services/cluster_daemon_families.py",       # skriver: beslutningerne
)


def test_ALLE_opløsere_bruger_SAMME_definition():
    """Kilde-vagt over begge retninger. Fire af fem havde egen kopi, og
    kopierne drev fra hinanden — femte gang i dette spor. AST, ikke grep:
    docstringene nævner `current_workspace_name` med vilje."""
    import ast
    import pathlib

    for sti in _INDBAKKE_OPLOESERE:
        træ = ast.parse(pathlib.Path(sti).read_text())
        navne = {n.name for x in ast.walk(træ)
                 if isinstance(x, ast.ImportFrom) for n in x.names}
        kaldt = {x.func.id for x in ast.walk(træ)
                 if isinstance(x, ast.Call) and isinstance(x.func, ast.Name)}
        assert "current_workspace_name" not in navne, (
            f"{sti} importerer workspacet selv — brug inbox_state.laese_bruger")
        assert "laese_bruger" in navne and "laese_bruger" in kaldt, (
            f"{sti} bruger ikke den faelles definition")


# ── Oversættelsen navn → id: den femte kopi af reglen ──────────────────────

def test_ejerens_workspace_oversaettes_til_hans_ID(inbox_db, monkeypatch):
    """`self_wakeup` kendte kun navnet og skrev det råt i `bruger_id`.

    Det blandede to navnerum i én kolonne, og resultatet var to indbakker
    til samme person. Nu oversættes navnet.

    Ejer-id'et sættes her til det RIGTIGE snowflake-id og ikke til fixturens
    «bjorn». Første udgave af denne test brugte fixturen, hvor id og navn er
    samme streng — så en mutation der svarede NAVNET bestod den. En test hvor
    det rigtige og det forkerte svar er identiske måler ingenting.
    """
    import core.identity.owner_resolver as _or
    monkeypatch.setattr(_or, "owner_user_id", lambda: "1246415163603816499")
    assert inbox_state.bruger_for_workspace("bjorn") == "1246415163603816499"


def test_en_ANDEN_brugers_workspace_oversaettes_til_HENDES_id(inbox_db, monkeypatch):
    """Og aldrig til navnet. Et workspace-navn er ikke et bruger-id, heller
    ikke for dem der HAR en række i tabellen."""
    import types
    import core.identity.users as _u
    monkeypatch.setattr(_u, "find_user_by_workspace",
                        lambda ws: types.SimpleNamespace(discord_id="2dce97")
                        if ws == "lotte" else None)
    assert inbox_state.bruger_for_workspace("lotte") == "2dce97"


def test_et_ukendt_workspace_giver_TOMT_og_siger_til(inbox_db, monkeypatch, caplog):
    """En post i den forkerte indbakke er værre end ingen post — men den må
    ikke forsvinde uden spor."""
    import logging
    import core.identity.users as _u
    monkeypatch.setattr(_u, "find_user_by_workspace", lambda _ws: None)
    with caplog.at_level(logging.WARNING, logger="core.services.inbox_state"):
        assert inbox_state.bruger_for_workspace("findes-ikke") == ""
    assert any("ingen bruger" in r.message for r in caplog.records), \
        "navnet forsvandt TAVST"


def test_self_wakeup_skriver_ALDRIG_et_workspace_navn_i_bruger_id():
    """Kilde-vagt på den femte kopi. AST, ikke grep: docstringen nævner
    `workspace_name` med vilje, og det gjorde den gamle kommentar også."""
    import ast
    import pathlib

    træ = ast.parse(pathlib.Path("core/services/self_wakeup.py").read_text())
    for kald in [n for n in ast.walk(træ) if isinstance(n, ast.Call)]:
        navn = getattr(kald.func, "id", None) or getattr(kald.func, "attr", None)
        if navn != "registrer_kilde":
            continue
        arg = next((k.value for k in kald.keywords if k.arg == "bruger_id"), None)
        assert arg is not None, "registrer_kilde kaldes uden bruger_id"
        kilde = ast.unparse(arg)
        assert "bruger_for_workspace" in kilde, (
            f"bruger_id udledes uden oversaettelse: {kilde}")
        return
    raise AssertionError("fandt intet registrer_kilde-kald i self_wakeup")


# ── Udsatte poster kommer tilbage (5/10-2026) ───────────────────────────────

def test_en_droppet_beslutnings_post_kommer_TILBAGE(inbox_db):
    """`drop` er en UDSÆTTELSE, ikke en afgørelse — kilden må genåbne den.

    Docstringen i `registrer_i_indbakken` lovede det, men ingen af de tre veje
    bar det: `expires_at` blev aldrig sat (tom = udløber ALDRIG), `saet_udloeb`
    havde nul kaldere uden for tests, og `opret_eller_hent` returnerer en
    eksisterende række urørt. Målt i drift: 76 beslutnings-poster stod i `drop`
    og kom aldrig igen — den modsatte af læring.
    """
    def _registrer():
        return inbox_state.registrer_kilde(
            bruger_id=BJORN, kildetype="decision", kilde_id="dec-1",
            kilde_ejer="jarvis", beskrivelse="[kritisk 0%] vis det")

    r = _registrer()
    assert r["post"]["status"] == db_inbox.STATUS_AABEN
    assert r["post"]["verificeret_ejer"] == inbox_state.EJER_JARVIS
    # Beslutnings-poster gater ikke: to gater der skubber til det samme.
    assert r["post"]["kraever_handling"] is False

    inbox_state.drop(BJORN, "dec-1", "ikke nu")
    assert db_inbox.hent(bruger_id=BJORN, kilde_id="dec-1")["status"] == \
        db_inbox.STATUS_DROP

    r2 = _registrer()
    assert r2["post"]["status"] == db_inbox.STATUS_AABEN, \
        "en droppet beslutning kunne ties ihjel af indbakken"
    assert r2.get("genaabnet") is True
    assert r2["post"]["afgjort_grund"] == "", "en genaabnet post bar sin gamle grund"


def test_en_GATENDE_post_genaabnes_IKKE_af_sin_kilde(inbox_db):
    """Grænsen: kun en post der IKKE kan nægte en mutation må flyttes.

    En `job`-post registreret inde i et levende run kan gate. Kunne dens kilde
    også genåbne den, var skrive-kontrakten omgået ad en ny vej — en daemon
    kunne genoplive en post der blokerer.
    """
    def _registrer():
        with _som_bjorn():
            return inbox_state.registrer_kilde(
                bruger_id=BJORN, kildetype="job", kilde_id="job-1",
                oprettende_run_id="visible-abc123", beskrivelse="et job")

    r = _registrer()
    assert r["post"]["kraever_handling"] is True, \
        "forudsætningen for testen er at posten KAN gate"

    inbox_state.drop(BJORN, "job-1", "nej")
    r2 = _registrer()
    assert r2["post"]["status"] == db_inbox.STATUS_DROP, \
        "en gatende post blev genaabnet af sin kilde"


def test_en_AFSLUTTET_post_genaabnes_ikke(inbox_db):
    """`done` er udført arbejde, ikke en udsættelse — den må ikke genoplives."""
    def _registrer():
        return inbox_state.registrer_kilde(
            bruger_id=BJORN, kildetype="decision", kilde_id="dec-2",
            kilde_ejer="jarvis", beskrivelse="x")

    _registrer()
    inbox_state.done(BJORN, "dec-2")
    r = _registrer()
    assert r["post"]["status"] == db_inbox.STATUS_DONE, \
        "afsluttet arbejde blev genoplivet af sin kilde"


def test_kilden_retter_TEKSTEN_naar_scoren_aendrer_sig(inbox_db):
    """Den målte sag (5/10-2026): `dec_b596dcde9db7` stod med «[imperativ 33%]»
    i indbakken mens gaten viste «Adherence 50% (advisory band)».

    Beskrivelsen skrives af `opret_eller_hent`, som er `INSERT OR IGNORE` — så
    uden en opdaterings-vej var teksten frosset ved første registrering, og
    båndet i den flade Bjørn læser løj fra det øjeblik scoren ændrede sig.
    """
    def _registrer(tekst):
        return inbox_state.registrer_kilde(
            bruger_id=BJORN, kildetype="decision", kilde_id="dec-baand",
            kilde_ejer="jarvis", beskrivelse=tekst)

    r = _registrer("[imperativ 33%] en forpligtelse")
    assert r["post"]["beskrivelse"] == "[imperativ 33%] en forpligtelse"

    r2 = _registrer("[advisory 50%] en forpligtelse")
    assert r2["post"]["beskrivelse"] == "[advisory 50%] en forpligtelse", \
        "baandet i posten fulgte ikke beslutningens score"
    assert db_inbox.hent(bruger_id=BJORN, kilde_id="dec-baand")["beskrivelse"] == \
        "[advisory 50%] en forpligtelse"


def test_en_GENAABNET_post_faar_sin_FRISKE_tekst(inbox_db):
    """Rækkefølgen er med vilje genåbning FØRst: en post der netop er genåbnet
    er `aaben`, og skal derfor have den nye tekst i SAMME runde — ikke først
    næste gang kilden melder sig."""
    def _registrer(tekst):
        return inbox_state.registrer_kilde(
            bruger_id=BJORN, kildetype="decision", kilde_id="dec-gen",
            kilde_ejer="jarvis", beskrivelse=tekst)

    _registrer("[imperativ 20%] en forpligtelse")
    inbox_state.drop(BJORN, "dec-gen", "udsat")

    r = _registrer("[advisory 55%] en forpligtelse")
    assert r["post"]["status"] == db_inbox.STATUS_AABEN, r
    assert r["post"]["beskrivelse"] == "[advisory 55%] en forpligtelse", \
        "den genaabnede post bar sin gamle tekst"
