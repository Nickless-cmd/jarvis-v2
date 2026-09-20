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
