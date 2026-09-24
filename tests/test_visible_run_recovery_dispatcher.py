"""Én forladt opgave genoptages præcis én gang — og kun af API-processen.

Opgave 4. To dispatchere, eller en dispatcher i begge processer, ville enten
starte den samme opgave to gange eller lade den ligge. Testene her holder de
tre ting fast: præcis én start, ingen dispatch i runtime-processen, og at et
krav gives tilbage når starten fejler.
"""
from __future__ import annotations

import pytest

from core.services import in_flight_runs as ifr
from core.services import visible_run_recovery_dispatcher as D


@pytest.fixture(autouse=True)
def _isolerede_poster(monkeypatch):
    poster: dict[str, dict] = {}
    monkeypatch.setattr(ifr, "_load", lambda: {k: dict(v) for k, v in poster.items()})
    monkeypatch.setattr(ifr, "_save", lambda v: (poster.clear(),
                                                 poster.update({k: dict(x) for k, x in v.items()})))
    monkeypatch.setattr(ifr, "owner_still_alive", lambda owner: False)
    monkeypatch.delenv("JARVIS_ENABLE_RUNTIME_SERVICES", raising=False)
    return poster


@pytest.fixture
def spawn(monkeypatch):
    kald: list[dict] = []

    def _start(**kw):
        kald.append(kw)
        return f"visible-{len(kald)}"

    monkeypatch.setattr(
        "core.services.visible_runs_sections.detached_run.start_user_run_detached", _start)
    return kald


def _forladt_opgave(run_id: str = "task-1", *, besked: str = "ret cheap lane") -> None:
    ifr.mark_started(run_id=run_id, session_id="chat-1", user_message=besked)
    ifr.settle_recovering(run_id, reason="shutdown", summary="shutdown")


def test_en_forladt_opgave_genoptages_praecis_EN_gang(spawn):
    _forladt_opgave()
    assert D.recover_due_once()["started"] == 1
    assert D.recover_due_once()["started"] == 0
    assert len(spawn) == 1
    assert spawn[0]["session_id"] == "chat-1"
    assert spawn[0]["message"] == "ret cheap lane"
    assert spawn[0]["recovery_task_id"] == "task-1"
    assert spawn[0]["recovery_generation"] == 1


def test_to_dispatchere_kan_ikke_tage_den_samme_opgave(spawn):
    """Kravet er atomisk: den anden finder ingenting, ikke den samme opgave."""
    _forladt_opgave()
    foerste = D.recover_due_once(owner="100:1")
    anden = D.recover_due_once(owner="200:2")
    assert foerste["started"] == 1 and anden["started"] == 0
    assert len(spawn) == 1


def test_runtime_processen_dispatcher_ikke(monkeypatch):
    monkeypatch.setenv("JARVIS_ENABLE_RUNTIME_SERVICES", "1")
    assert D.start_recovery_dispatcher() is False


def test_api_processen_starter_EN_dispatcher(monkeypatch):
    monkeypatch.setattr(D, "_loop", lambda: None)
    try:
        assert D.start_recovery_dispatcher() is True
        assert D.start_recovery_dispatcher() is True   # idempotent
    finally:
        D.stop_recovery_dispatcher()


def test_en_mislykket_start_giver_kravet_tilbage(monkeypatch):
    _forladt_opgave()

    def _boom(**kw):
        raise RuntimeError("ingen plads til flere kørsler")

    monkeypatch.setattr(
        "core.services.visible_runs_sections.detached_run.start_user_run_detached", _boom)
    svar = D.recover_due_once()
    assert svar["started"] == 0 and svar["released"] == 1
    post = ifr._load()["task-1"]
    assert post["status"] == "recovering", "opgaven skal kunne tages igen"
    assert post["next_attempt_at"], "og først efter en pause"


def test_en_opgave_uden_session_startes_ikke(spawn):
    """En fortsættelse uden samtale ville lande et tilfældigt sted."""
    ifr.mark_started(run_id="task-2", session_id="", user_message="noget")
    ifr.settle_recovering("task-2", reason="shutdown")
    svar = D.recover_due_once()
    assert svar["started"] == 0 and svar["released"] == 1 and not spawn


def test_intet_forfaldent_giver_ingen_stoej(spawn):
    assert D.recover_due_once() == {"started": 0, "released": 0, "claimed": ""}
    assert not spawn


def test_sidste_runde_beder_om_en_AFSLUTNING_ikke_mere_arbejde(spawn):
    """Er forsøgene brugt op, må den sidste runde ikke gå med at grave videre."""
    ifr.mark_started(run_id="task-9", session_id="chat-1", user_message="den store opgave")
    ifr.settle_recovering("task-9", reason="provider-round-timeout",
                          summary="den store opgave", recovery_limit=1,
                          final_synthesis_pending=True)
    assert D.recover_due_once()["started"] == 1
    besked = spawn[0]["message"]
    assert "sidste runde" in besked and "Start ikke nyt arbejde" in besked
    assert "den store opgave" in besked, "opgaven skal stadig stå i beskeden"


# ───────── en FAERDIG fortsaettelse maa ikke tages igen (Bjørn 17/9-2026)
#
# Maalt i produktionen: den samme opgave blev genoptaget TRE gange — 21:48:12,
# 21:50:13, 21:52:14 — og hver gang svarede Jarvis faerdigt paa det samme
# spoergsmaal. Afstanden var praecis lejemaalets 120 sekunder, og dét var hele
# forklaringen: `recovery_task_id` blev kun LOGGET af den detachede koersel.
# Kravet stod som «running» i journalen, ingen lukkede det, lejemaalet udloeb,
# og opgaven var forfalden igen. Tre betalte ture paa ét spoergsmaal.

def test_et_udloebet_lejemaal_tager_opgaven_igen(spawn):
    """Mekanismen bag fejlen — den skal blive ved at virke, for det er den der
    redder en opgave hvis processen doer midt i fortsaettelsen."""
    from datetime import datetime, timedelta, UTC
    _forladt_opgave()
    assert D.recover_due_once()["started"] == 1
    senere = datetime.now(UTC) + timedelta(seconds=D.LEASE_SECONDS + 5)
    assert ifr.claim_due_recovery(owner="ny", now=senere) is not None


def test_en_FAERDIG_fortsaettelse_tages_IKKE_igen(spawn):
    """Og her er fejlen: naar fortsaettelsen blev faerdig, skal opgaven vaere
    lukket — ogsaa efter at lejemaalet er udloebet."""
    from datetime import datetime, timedelta, UTC
    _forladt_opgave()
    assert D.recover_due_once()["started"] == 1
    ifr.mark_completed("task-1")            # det den detachede koersel nu goer
    senere = datetime.now(UTC) + timedelta(seconds=D.LEASE_SECONDS + 5)
    assert ifr.claim_due_recovery(owner="ny", now=senere) is None
    assert len(spawn) == 1, "opgaven blev fortsat en gang for meget"


def test_den_detachede_koersel_lukker_opgaven_naar_turen_ER_terminal():
    """Kilde-vagt paa koblingen. `recovery_task_id` blev baaret hele vejen ind
    og saa kun skrevet i loggen — derfor kunne journalen ikke se at opgaven var
    loest, og lejemaalet blev den eneste ting der styrede."""
    import inspect
    from core.services.visible_runs_sections import detached_run
    kilde = inspect.getsource(detached_run)
    assert "mark_completed(recovery_task_id)" in kilde
    # KUN naar turen faktisk blev faerdig: fejlede fortsaettelsen, skal
    # opgaven blive liggende og tages igen — det er hele formaalet.
    assert kilde.index("run_er_terminal(") < kilde.index("mark_completed(recovery_task_id)")


# ── Én kørsel ad gangen i en samtale (Bjørn 20/9-2026) ──────────────────────
def test_en_forts_starter_IKKE_naar_samtalen_har_et_levende_run(spawn, monkeypatch):
    """«I en session med en bruger må han aldrig køre flere sideløbende runs.»

    Single-flight bor i `start_or_attach_user_run`; dispatcheren gik uden om
    den. Målt 20/9-2026: 456 afbrudte kørsler i køen, 189 af dem i ÉN samtale,
    og fire fortsættelser spawnet på to sekunder efter en genstart.
    """
    from core.services import run_event_log as rel
    monkeypatch.setattr(rel, "active_run_for_session",
                        lambda sid: "visible-koerer-allerede" if sid == "chat-1" else None)
    _forladt_opgave()
    r = D.recover_due_once()
    assert r["started"] == 0 and r["released"] == 1
    assert r["error"] == "session-optaget"
    assert spawn == []                      # der blev IKKE startet noget


def test_kravet_er_ikke_tabt_men_tages_naar_samtalen_er_fri(spawn, monkeypatch):
    """Køen er durabel: en udskudt fortsættelse skal komme igen."""
    from core.services import run_event_log as rel
    optaget = {"ja": True}
    monkeypatch.setattr(rel, "active_run_for_session",
                        lambda sid: "visible-x" if optaget["ja"] else None)
    monkeypatch.setattr(D, "BACKOFF_SECONDS", 0)
    _forladt_opgave()
    assert D.recover_due_once()["started"] == 0
    optaget["ja"] = False                   # turen er slut
    assert D.recover_due_once()["started"] == 1
    assert spawn[0]["session_id"] == "chat-1"


def test_en_anden_samtale_blokerer_ikke(spawn, monkeypatch):
    """Reglen er pr. samtale — ikke en global kø."""
    from core.services import run_event_log as rel
    monkeypatch.setattr(rel, "active_run_for_session",
                        lambda sid: "visible-y" if sid == "en-anden" else None)
    _forladt_opgave()
    assert D.recover_due_once()["started"] == 1


def test_en_ulaeselig_runlog_blokerer_ikke_genoptagelsen(spawn, monkeypatch):
    """Self-safe: kan vi ikke se efter, må arbejdet ikke gå i stå."""
    from core.services import run_event_log as rel

    def _braekker(_sid):
        raise RuntimeError("loggen er væk")
    monkeypatch.setattr(rel, "active_run_for_session", _braekker)
    _forladt_opgave()
    assert D.recover_due_once()["started"] == 1


# ── En udskydelse er ikke et forsoeg (24/9-2026) ────────────────────────────
def test_tre_udskydelser_braender_ikke_hele_genoptagelses_budgettet(spawn, monkeypatch):
    """En samtale der er optaget i 90 sekunder maa ikke koste opgaven ALT.

    Maalt 24/9-2026 paa CT105: 12 poster stod som `recovering` med
    ``recovery_attempt=3``, ``recovery_limit=3`` og
    ``exit_reason="samtalen har et levende run"`` — alle tolv. Ikke EN af dem
    var nogensinde blevet startet. `claim_due_recovery` taeller et forsoeg naar
    kravet TAGES, og dispatcheren tager et krav for overhovedet at kunne se
    hvilken session opgaven hoerer til. Tre udskydelser a 30 sekunder var nok:
    bagefter sprang `claim_due_recovery` posten over for evigt
    (``exhausted = attempt >= limit``), og arbejdet laa der uden at nogen
    hentede det.

    Budgettet er til FORSOEG paa at fortsaette, ikke til opslag.
    """
    from core.services import run_event_log as rel
    optaget = {"ja": True}
    monkeypatch.setattr(rel, "active_run_for_session",
                        lambda sid: "visible-x" if optaget["ja"] else None)
    monkeypatch.setattr(D, "BACKOFF_SECONDS", 0)
    _forladt_opgave()

    for _ in range(5):                      # laengere end `recovery_limit`
        assert D.recover_due_once()["error"] == "session-optaget"

    optaget["ja"] = False
    assert D.recover_due_once()["started"] == 1, (
        "budgettet blev braendt paa udskydelser — opgaven hentes aldrig"
    )


def test_en_udskydelse_spiser_ikke_den_sidste_slutrunde(spawn, monkeypatch):
    """`final_synthesis_pending` maa ikke forsvinde paa et krav der ikke startede.

    Kravet saetter ``recovery_mode="final_synthesis"`` og rydder flaget i SAMME
    mutation. Gives kravet tilbage uden at noget blev startet, er retten til en
    afsluttende sammenfatning vaek — og saa svarer han aldrig paa det han
    naaede.
    """
    from core.services import run_event_log as rel
    optaget = {"ja": True}
    monkeypatch.setattr(rel, "active_run_for_session",
                        lambda sid: "visible-x" if optaget["ja"] else None)
    monkeypatch.setattr(D, "BACKOFF_SECONDS", 0)
    ifr.mark_started(run_id="task-fs", session_id="chat-1", user_message="ret cheap lane")
    ifr.settle_recovering("task-fs", reason="tom", summary="tom",
                          final_synthesis_pending=True)

    assert D.recover_due_once()["error"] == "session-optaget"
    assert ifr.get_record("task-fs").get("final_synthesis_pending") is True

    optaget["ja"] = False
    assert D.recover_due_once()["started"] == 1
    assert spawn[0]["message"].startswith("Din sidste runde")


def test_en_start_der_FEJLER_taeller_stadig_som_et_forsoeg(monkeypatch):
    """Rullede vi ogsaa den tilbage, ville en permanent brudt start proeve evigt.

    Skellet er hele pointen: et opslag er ikke et forsoeg, men et forsoeg der
    gik galt er et forsoeg.
    """
    def _braekker(**kw):
        raise RuntimeError("provider nede")
    monkeypatch.setattr(
        "core.services.visible_runs_sections.detached_run.start_user_run_detached",
        _braekker)
    monkeypatch.setattr(D, "BACKOFF_SECONDS", 0)
    _forladt_opgave()

    for _ in range(3):
        assert D.recover_due_once()["started"] == 0
    # Budgettet er brugt — fjerde gang findes posten ikke laengere som forfalden.
    assert D.recover_due_once() == {"started": 0, "released": 0, "claimed": ""}
    assert int(ifr.get_record("task-1")["recovery_attempt"]) == 3


def test_udskydelserne_venter_laengere_og_laengere_men_ikke_uendeligt():
    """En optaget samtale maa ikke blive til et bank paa doeren hvert 30. sekund."""
    assert D._udskydelses_backoff(0) == D.BACKOFF_SECONDS
    assert D._udskydelses_backoff(1) == 2 * D.BACKOFF_SECONDS
    assert D._udskydelses_backoff(3) == 8 * D.BACKOFF_SECONDS      # 240s, under loftet
    assert D._udskydelses_backoff(50) == D.MAX_UDSKYDELSE_SECONDS


def test_udskydelser_nulstilles_naar_et_nyt_segment_doer(spawn, monkeypatch):
    """Ventetiden arves ikke: en ny afregning starter en ny serie."""
    from core.services import run_event_log as rel
    monkeypatch.setattr(rel, "active_run_for_session", lambda sid: "visible-x")
    monkeypatch.setattr(D, "BACKOFF_SECONDS", 0)
    _forladt_opgave()
    for _ in range(3):
        D.recover_due_once()
    assert int(ifr.get_record("task-1")["recovery_deferrals"]) == 3

    ifr.settle_recovering("task-1", reason="shutdown igen", summary="shutdown igen")
    assert int(ifr.get_record("task-1")["recovery_deferrals"]) == 0


def test_en_opgave_der_er_for_gammel_genoptages_ikke_men_afregnes(spawn, monkeypatch):
    """Et spoergsmaal fra i forgaars fortsaettes ikke — det afsluttes synligt.

    Aldersgraensen fandtes kun i `interrupted_for_session`; claim-stien havde
    ingen. Det gjorde ikke noget saa laenge udskydelser braendte budgettet paa
    halvandet minut, for saa stoppede opgaven af sig selv. Naar den fejl er
    rettet, er aldersgraensen det eneste der er tilbage — og uden den ville
    rettelsen goere det VAERRE: en fortsaettelse af et 71 timer gammelt
    spoergsmaal midt i en samtale der for laengst er gaaet videre.

    Maalt 24/9-2026 paa CT105: de aeldste fire af de tolv fastlaaste var
    62-71 timer gamle.
    """
    from datetime import UTC, datetime, timedelta
    _forladt_opgave()
    gammel = (datetime.now(UTC) - timedelta(
        hours=ifr.GENOPTAGELSES_VINDUE_TIMER + 1)).isoformat()
    poster = ifr._load()
    n = ifr._record_key(poster, "task-1")
    poster[n]["settled_at"] = gammel
    poster[n]["interrupted_at"] = gammel
    ifr._save(poster)

    assert D.recover_due_once()["started"] == 0
    assert spawn == []
    efter = ifr.get_record("task-1")
    # Den maa ikke bare springes over: saa ville den ligge som `recovering`
    # for evigt og LIGNE noget der stadig kunne hentes.
    assert efter["status"] == "failed_terminal"
    assert efter["exit_reason"] == "genoptagelses-vinduet udloeb"
    assert efter["notice_pending"] is True


def test_en_opgivet_opgave_forsvinder_ikke_tavst_fra_klienten(spawn, monkeypatch):
    """Loeb en opgave toer, skal han FAA det at vide — praecis en gang.

    `recovery_snapshot` saa kun paa `recovering`/`running`. En opgave der blev
    opgivet forsvandt derfor bare fra klienten: indikatoren slukkede, og der
    stod ingenting om at spoergsmaalet var droppet. Det er samme fejlklasse som
    den vi retter her — arbejde der stille holder op med at findes.
    """
    from datetime import UTC, datetime, timedelta
    _forladt_opgave()
    gammel = (datetime.now(UTC) - timedelta(
        hours=ifr.GENOPTAGELSES_VINDUE_TIMER + 1)).isoformat()
    poster = ifr._load()
    n = ifr._record_key(poster, "task-1")
    poster[n]["settled_at"] = gammel
    poster[n]["interrupted_at"] = gammel
    ifr._save(poster)
    D.recover_due_once()

    snap = ifr.recovery_snapshot("chat-1")
    assert snap is not None, "den opgivne opgave blev aldrig fortalt"
    assert snap["state"] == "failed_terminal"
    assert snap["notice"]

    # ... og kun EN gang. Ellers ville den staa som «afbrudt» i et doegn og
    # ligne noget der stadig skete.
    assert ifr.recovery_snapshot("chat-1") is None


# ── Varslets tekst skal vaere sand (24/9-2026) ──────────────────────────────
def test_et_opgivet_run_faar_ikke_at_vide_at_checkpointet_kan_genoptages():
    """Standardteksten lover «Checkpointet er bevaret» — det passer ikke her.

    Begge de nye grunde faldt tilbage paa `recovery_notice`s standardtekst, og
    den siger at automatisk recovery er opbrugt MEN at checkpointet er bevaret.
    For et run hvis genoptagelses-vindue er udloebet — eller som er opgivet
    efter aftale — er der ikke noget at vente paa. Saa skal beskeden sige hvad
    han kan goere i stedet: skrive den igen.
    """
    from core.services.visible_terminal_policy import recovery_notice

    udloebet = recovery_notice("genoptagelses-vinduet udloeb", continuing=False)
    assert "Skriv den igen" in udloebet["message"]
    assert "bevaret" not in udloebet["message"]
    assert udloebet["continuing"] is False

    opgivet = recovery_notice("opgivet efter aftale — budgettet var braendt", continuing=False)
    assert "opgivet efter aftale" in opgivet["message"].lower()
    assert "Skriv den igen" in opgivet["message"]
    assert opgivet["continuing"] is False

    # De levende grunde skal stadig love fortsaettelse — ellers har jeg
    # slukket varslet for alt det der FAKTISK fortsaetter.
    lever = recovery_notice("pending-tool-intent", continuing=True)
    assert "fortsaetter automatisk" in lever["message"]
    assert lever["continuing"] is True
