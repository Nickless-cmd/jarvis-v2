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
def inbox_db(monkeypatch, tmp_path):
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
