"""Indbakken skal kunne VÆKKE — ikke kun gate.

Bjørn 10/10-2026: «skal inbox kunne vække dig, på den hvis du ikk er i et
aktivt run?» Svaret var nej: `inbox_gate` blokerer kun mutationer INDE i et
run, og intet starter et run fordi en post findes. En `kraever_handling=1`-post
uden dispatcher ventede til næste heartbeat eller hans næste besked.

Det er hullet: en forpligtelse der kræver handling bør ikke kunne stå og vente
på at nogen tilfældigvis kører.

Vækkeren er bevidst KONSERVATIV:
  * kun poster der faktisk gater (`kraever_handling` + verificeret ejer)
  * kun når INTET run er i gang
  * kun én vækning pr. post — ellers bliver den en kæde der skriver i hans chat
  * self-safe: enhver fejl → ingen vækning, aldrig en væltet poller
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

import pytest

from core.runtime import db_inbox


@pytest.fixture
def inbox_db(monkeypatch, tmp_path):
    sti = tmp_path / "idle.db"

    @contextmanager
    def _connect():
        k = sqlite3.connect(sti)
        k.row_factory = sqlite3.Row
        try:
            yield k
            k.commit()
        finally:
            k.close()

    monkeypatch.setattr(db_inbox, "connect", _connect)
    monkeypatch.setattr(db_inbox, "_skema_klar", False)
    return sti


def _post(bruger="bjorn", id="wake-1", **kw) -> dict:
    r = db_inbox.opret_eller_hent(
        # Disse tests maaler den GENERELLE gatende indbakke-vej. En wakeup har
        # sin egen kildeautoritative modenhed og testes i
        # test_wakeup_skip_til_indbak.py; brugte vi den som standard her,
        # gjorde fixturen fremtidige wakeups kunstigt modne.
        bruger_id=bruger, kildetype=kw.pop("kildetype", "job"), kilde_id=id,
        oprettende_run_id="visible-abc",
        verificeret_ejer=kw.pop("ejer", db_inbox.EJER_JARVIS),
        kraever_handling=kw.pop("kraever_handling", True),
        beskrivelse=kw.pop("beskrivelse", "foelg op"), **kw)
    assert r["status"] == "ok", r
    return r["post"]


@pytest.fixture(autouse=True)
def _samtale(monkeypatch):
    """Giv hver post en MÅL-samtale — 14/10-2026.

    Vækkeren kræver nu en samtale at vække i: den må ikke længere starte et run
    i `auto-autonomous` (en session ingen læser). Uden denne fixture ville hver
    test nedenfor skulle stille en session op for at komme til sit egentlige
    emne. Den test der måler NETOP dét krav overskriver den selv.
    """
    from core.services import inbox_idle_waker as w

    monkeypatch.setattr(w, "_maal_session", lambda post: "chat-1")
    monkeypatch.setattr(w, "_session_er_aktiv", lambda session_id: False)


# ── hvem må vække ───────────────────────────────────────────────────────────

def test_kun_gatende_poster_vaekker(inbox_db):
    """En informerende post (huset/ukendt) må ikke starte et run."""
    from core.services.inbox_idle_waker import kandidater

    _post(id="husets", ejer=db_inbox.EJER_HUSET, kraever_handling=False)
    _post(id="ukendt", ejer=db_inbox.EJER_UKENDT, kraever_handling=False)
    _post(id="min", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)

    ids = [p["kilde_id"] for p in kandidater("bjorn")]
    assert ids == ["min"]


def test_afgjorte_poster_vaekker_ikke(inbox_db):
    from core.services.inbox_idle_waker import kandidater

    _post(id="aaben", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    _post(id="lukket", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    db_inbox.afgoer(bruger_id="bjorn", kilde_id="lukket",
                    ny_status=db_inbox.STATUS_DONE, grund="test")

    ids = [p["kilde_id"] for p in kandidater("bjorn")]
    assert ids == ["aaben"]


def test_anden_brugers_poster_vaekker_ikke_mig(inbox_db):
    """Husstanden har flere brugere — en post for en anden må ikke starte mit run."""
    from core.services.inbox_idle_waker import kandidater

    _post(bruger="mikkel", id="hans", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    assert kandidater("bjorn") == []


# ── hvornår den må fyre ─────────────────────────────────────────────────────

def test_aktivt_run_blokerer_vaekning(inbox_db, monkeypatch):
    """Kører der noget, må vækkeren ikke starte et konkurrerende run."""
    from core.services import inbox_idle_waker as w

    _post(id="min", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    monkeypatch.setattr(w, "_noget_koerer", lambda: True)
    startet = []
    monkeypatch.setattr(w, "_start_run", lambda tekst, **kw: startet.append(tekst))

    r = w.vaek_paa_aabne_poster(bruger_id="bjorn")
    assert r["vaekket"] == 0
    assert startet == []


def test_ingen_aktivt_run_vaekker(inbox_db, monkeypatch):
    from core.services import inbox_idle_waker as w

    _post(id="min", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    monkeypatch.setattr(w, "_noget_koerer", lambda: False)
    startet = []
    monkeypatch.setattr(w, "_start_run", lambda tekst, **kw: startet.append(tekst))

    r = w.vaek_paa_aabne_poster(bruger_id="bjorn")
    assert r["vaekket"] == 1
    assert len(startet) == 1
    assert "min" in startet[0]


def test_samme_post_vaekker_kun_en_gang(inbox_db, monkeypatch):
    """Uden dette ville hver poll-runde starte et nyt run — en kæde i hans chat."""
    from core.services import inbox_idle_waker as w

    _post(id="min", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    monkeypatch.setattr(w, "_noget_koerer", lambda: False)
    startet = []
    monkeypatch.setattr(w, "_start_run", lambda tekst, **kw: startet.append(tekst))

    assert w.vaek_paa_aabne_poster(bruger_id="bjorn")["vaekket"] == 1
    assert w.vaek_paa_aabne_poster(bruger_id="bjorn")["vaekket"] == 0
    assert len(startet) == 1


def test_loft_pr_runde(inbox_db, monkeypatch):
    """Ti aabne poster maa ikke blive ti runs i samme runde."""
    from core.services import inbox_idle_waker as w

    for i in range(10):
        _post(id=f"p{i}", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    monkeypatch.setattr(w, "_noget_koerer", lambda: False)
    startet = []
    monkeypatch.setattr(w, "_start_run", lambda tekst, **kw: startet.append(tekst))

    r = w.vaek_paa_aabne_poster(bruger_id="bjorn")
    assert r["vaekket"] == w.MAKS_PR_RUNDE
    assert len(startet) == w.MAKS_PR_RUNDE


# ── gaten må ikke blinde vækkeren ───────────────────────────────────────────

def test_gatens_spor_blinder_ikke_vaekkeren(inbox_db, monkeypatch):
    """MÅLT I DRIFT 10/10-2026: gaten og vækkeren delte ét felt.

    `inbox_gate` skriver sit RUN-ID i `sidste_paamindelse_tur` når den minder om
    en post den netop nægtede en mutation for. Vækkeren læste det SAMME felt som
    «har jeg allerede vækket?» og krævede det tomt. Konsekvensen var skarp:
    enhver post der havde fået bare én gate-påmindelse kunne ALDRIG vække — og
    det er præcis de poster vækkeren findes for.

    Målt: med gatens spor sat → `kandidater=0` og `{'vaekket': 0,
    'aarsag': 'ingen_kandidater'}`. Samme post, spor nulstillet → `vaekket: 1`.
    Kun sporet skilte.
    """
    from core.services import inbox_idle_waker as w

    _post(id="min", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    # Gaten minder om posten, som den gør ved en nægtet mutation:
    db_inbox.noter_paamindelse(bruger_id="bjorn", kilde_id="min", tur="visible-abc")

    monkeypatch.setattr(w, "_noget_koerer", lambda: False)
    startet = []
    monkeypatch.setattr(w, "_start_run", lambda tekst, **kw: startet.append(tekst))

    r = w.vaek_paa_aabne_poster(bruger_id="bjorn")
    assert r["vaekket"] == 1, "gatens spor blinded the waker"
    assert len(startet) == 1


def test_vaekningens_spor_er_sit_eget(inbox_db, monkeypatch):
    """Vækkeren skriver sit eget spor — ikke påmindelses-feltet gaten ejer."""
    from core.services import inbox_idle_waker as w

    _post(id="min", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    monkeypatch.setattr(w, "_noget_koerer", lambda: False)
    monkeypatch.setattr(w, "_start_run", lambda tekst, **kw: tekst)

    assert w.vaek_paa_aabne_poster(bruger_id="bjorn")["vaekket"] == 1
    post = db_inbox.hent(bruger_id="bjorn", kilde_id="min")
    assert post["sidste_vaekning_tur"] == w._VAEKKET_AF
    # Påmindelses-sporet er URØRT — det tilhører gaten.
    assert post["sidste_paamindelse_tur"] == ""


def test_nulstil_vaekning_roerer_ikke_paamindelser(inbox_db):
    """Rollback af vækningens spor må ikke slette gaten's historik."""
    _post(id="min", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    db_inbox.noter_paamindelse(bruger_id="bjorn", kilde_id="min", tur="visible-abc")
    db_inbox.noter_vaekning(bruger_id="bjorn", kilde_id="min", tur="inbox-idle-waker")

    db_inbox.nulstil_vaekning(bruger_id="bjorn", kilde_id="min")

    post = db_inbox.hent(bruger_id="bjorn", kilde_id="min")
    assert post["sidste_vaekning_tur"] == ""
    assert post["sidste_paamindelse_tur"] == "visible-abc"
    assert post["paamindelser"] == 1


def test_ci_alarm_vaekker_uden_at_vaere_gatende(inbox_db, monkeypatch):
    """Maalt 15/10-2026: CI-vagten skrev sin alarm med `daemon`, som hverken
    gater eller dispatcher. Bjørn sad i en aaben session og fik intet signal da
    desk-release 0.6.237 fejlede. En CI-alarm er sin EGEN klasse: ikke-gatende
    (den maa ikke naegte en mutation), men dispatchbar og moden i det oejeblik
    den skrives."""
    from core.services import inbox_idle_waker as w

    _post(id="ci-status-watch", kildetype="ci_alarm",
          ejer=db_inbox.EJER_JARVIS, kraever_handling=False)
    monkeypatch.setattr(w, "_noget_koerer", lambda: False)
    startet = []
    monkeypatch.setattr(w, "_start_run", lambda tekst, **kw: startet.append(tekst))

    r = w.vaek_paa_aabne_poster(bruger_id="bjorn")
    assert r["vaekket"] == 1, "en CI-alarm skal kunne vaekke en ledig session"
    assert len(startet) == 1


def test_daemon_post_vaekker_stadig_ikke(inbox_db, monkeypatch):
    """`ci_alarm` er en snaever klasse. En almindelig daemon-post er fortsat
    informerende og maa IKKE starte et run — ellers bliver hver vagt en silo."""
    from core.services import inbox_idle_waker as w

    _post(id="en-vagt", kildetype="daemon",
          ejer=db_inbox.EJER_JARVIS, kraever_handling=False)
    monkeypatch.setattr(w, "_noget_koerer", lambda: False)
    startet = []
    monkeypatch.setattr(w, "_start_run", lambda tekst, **kw: startet.append(tekst))

    assert w.vaek_paa_aabne_poster(bruger_id="bjorn")["vaekket"] == 0
    assert startet == []


# ── self-safe ───────────────────────────────────────────────────────────────

def test_fejl_i_laesningen_vaelter_ikke_polleren(inbox_db, monkeypatch):
    from core.services import inbox_idle_waker as w

    def braender(**kw):
        raise RuntimeError("db nede")

    monkeypatch.setattr(w, "kandidater", braender)
    r = w.vaek_paa_aabne_poster(bruger_id="bjorn")
    assert r["status"] == "ok"
    assert r["vaekket"] == 0


def test_fejl_i_run_start_efterlader_ikke_post_som_vaekket(inbox_db, monkeypatch):
    """Kaster run-start, maa posten IKKE markeres — saa proeves den igen."""
    from core.services import inbox_idle_waker as w

    _post(id="min", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    monkeypatch.setattr(w, "_noget_koerer", lambda: False)

    def braender(tekst, **kw):
        raise RuntimeError("kunne ikke starte")

    monkeypatch.setattr(w, "_start_run", braender)
    r = w.vaek_paa_aabne_poster(bruger_id="bjorn")
    assert r["vaekket"] == 0
    # anden runde proever igen — posten er ikke brændt af
    startet = []
    monkeypatch.setattr(w, "_start_run", lambda tekst, **kw: startet.append(tekst))
    assert w.vaek_paa_aabne_poster(bruger_id="bjorn")["vaekket"] == 1


# ── samtalen runnet hører til (14/10-2026) ──────────────────────────────────
#
# Bjørn: «men idle vækningen, bør ikk starte autonome sessioner. de bør vække
# den session de høre til...» Målt: `_dispatch_tekst` gav `session=None` for
# ALLE gatende poster, og `normalize_origin("inbox")` kollapser ukendte navne
# til «autonomous». Resultatet var et run i `auto-autonomous-{dato}` — en
# session ingen læser — hver gang en post ventede.


def test_en_post_uden_samtale_vaekker_IKKE(inbox_db, monkeypatch):
    """Ingen samtale ⇒ ingen vækning. Posten venter; vi laver ikke en silo."""
    from core.services import inbox_idle_waker as w

    _post(id="min", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    monkeypatch.setattr(w, "_maal_session", lambda post: "")
    monkeypatch.setattr(w, "_noget_koerer", lambda: False)
    startet = []
    monkeypatch.setattr(w, "_start_run", lambda tekst, **kw: startet.append(tekst))

    r = w.vaek_paa_aabne_poster(bruger_id="bjorn")
    assert r["vaekket"] == 0, "et run uden samtale er præcis den silo vi fjerner"
    assert startet == []
    # Og posten er IKKE brændt af — næste runde må prøve igen.
    post = db_inbox.hent(bruger_id="bjorn", kilde_id="min")
    assert post["sidste_vaekning_tur"] == ""


def test_runnet_faar_postens_samtale_ikke_en_auto_session(inbox_db, monkeypatch):
    """Den målte fejl: sessionen skal være postens — ikke `auto-…`."""
    from core.services import inbox_idle_waker as w

    _post(id="min", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    monkeypatch.setattr(w, "_noget_koerer", lambda: False)
    kaldt: list[dict] = []
    monkeypatch.setattr(w, "_start_run",
                        lambda tekst, **kw: kaldt.append({"tekst": tekst, **kw}))

    assert w.vaek_paa_aabne_poster(bruger_id="bjorn")["vaekket"] == 1
    assert kaldt[0]["session_id"] == "chat-1"
    assert kaldt[0]["user_id"] == "bjorn"
    assert not kaldt[0]["session_id"].startswith("auto-"), (
        "et autonomt run i auto-* er præcis den silo Bjørn pegede på"
    )


def test_postens_egen_aktive_session_blokerer_foer_vaekkespor(
    inbox_db, monkeypatch,
):
    """Preflight kan have tjekket en anden ejersession end postens mål."""
    from core.services import inbox_idle_waker as w

    _post(id="min", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    monkeypatch.setattr(w, "_noget_koerer", lambda: False)
    monkeypatch.setattr(w, "_session_er_aktiv", lambda sid: sid == "chat-1")
    startet = []
    monkeypatch.setattr(w, "_start_run", lambda tekst, **kw: startet.append(tekst))

    assert w.vaek_paa_aabne_poster(bruger_id="bjorn")["vaekket"] == 0
    assert startet == []
    assert db_inbox.hent(bruger_id="bjorn", kilde_id="min")["sidste_vaekning_tur"] == ""


def test_maal_session_er_dispatcherens_egen_definition():
    """To definitioner af «hvor skal dette lande» driver fra hinanden.

    Kilden læses fra FILEN — ikke med `inspect.getsource`: autouse-fixturen
    monkeypatcher `_maal_session`, og `getsource` ville så læse lambda'en i
    stedet for funktionen. Det målte jeg ved at fejle på det først.
    """
    import pathlib

    kilde = pathlib.Path(
        "core/services/inbox_idle_waker.py").read_text(encoding="utf-8")
    start = kilde.index("def _maal_session")
    slut = kilde.index("def _start_run")
    krop = kilde[start:slut]
    assert "pick_wakeup_run_target" in krop, (
        "vækkeren skal bruge dispatcherens session-valg, ikke sin egen kopi"
    )
    assert "session_is_external_channel" in krop, (
        "app-vækninger må ikke re-engagere en ekstern kanal (Discord/Telegram)"
    )


def test_start_run_kraever_en_session():
    """Signaturen må ikke kunne kaldes uden en samtale.

    Indtil 14/10-2026 var `session_id` valgfri med default `None` — og `None`
    betød `auto-autonomous`. Kravet skal ligge i signaturen, ikke i en
    kommentar.
    """
    import inspect

    from core.services import inbox_idle_waker as w

    param = inspect.signature(w._start_run).parameters["session_id"]
    assert param.default is inspect.Parameter.empty, (
        "en valgfri session_id er hvordan siloen opstod"
    )


# ── de fem steps fra autonomi-auditten: ærlig vækning + re-tjek (14/10-2026) ──
#
# Audit: docs/audits/2026-10-14-autonomous-execution-integrity.md §11.
# Testene bor HER fordi de bruger `inbox_db`-fixturen, som er defineret i denne
# fil — en fixture i en anden testfil kan ikke importeres ind.


def test_afvist_start_lader_ikke_posten_staa_vaekket(inbox_db, monkeypatch):
    """Run-guarden afviste TAVST (returvaerdi False) → posten maa ikke staa vaekket."""
    from core.services import inbox_idle_waker as w

    _post(id="min", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    monkeypatch.setattr(w, "_noget_koerer", lambda: False)
    monkeypatch.setattr(w, "_start_run", lambda tekst, **kw: False)

    assert w.vaek_paa_aabne_poster(bruger_id="bjorn")["vaekket"] == 0

    startet = []
    monkeypatch.setattr(w, "_start_run", lambda tekst, **kw: startet.append(tekst))
    assert w.vaek_paa_aabne_poster(bruger_id="bjorn")["vaekket"] == 1


def test_ukendt_returvaerdi_bevarer_gammel_adfaerd(inbox_db, monkeypatch):
    """`None` = startet. Tvivlen skal falde ud til at have startet."""
    from core.services import inbox_idle_waker as w

    _post(id="min", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    monkeypatch.setattr(w, "_noget_koerer", lambda: False)
    monkeypatch.setattr(w, "_start_run", lambda tekst, **kw: None)

    assert w.vaek_paa_aabne_poster(bruger_id="bjorn")["vaekket"] == 1


def test_re_tjek_mellem_iterationer_stopper_anden_start(inbox_db, monkeypatch):
    """MAKS_PR_RUNDE = 2 var et loft uden en vagt undervejs."""
    from core.services import inbox_idle_waker as w

    for i in range(3):
        _post(id=f"p{i}", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)

    kald = {"n": 0}

    def _koerer():
        kald["n"] += 1
        return kald["n"] > 1

    monkeypatch.setattr(w, "_noget_koerer", _koerer)
    startet = []
    monkeypatch.setattr(w, "_start_run", lambda tekst, **kw: startet.append(tekst))

    assert w.vaek_paa_aabne_poster(bruger_id="bjorn")["vaekket"] == 1
    assert len(startet) == 1


# ── arbejdsrummet skal med (11/11-2026) ──────────────────────────────────────

def test_vaekning_binder_arbejdsrummet_foer_runnet_starter(monkeypatch):
    """Da `wakeup_dispatcher` blev flyttet ind i vækkeren, fulgte dens
    `set_context(...)`-kald IKKE med — og `start_autonomous_run` arver blot
    ContextVars fra den tråd der kalder.

    Uden binding kører en vækning booket i Michelles arbejdsrum i Bjørns, og
    runnet ser den forkerte hukommelse. Fejlen er TAVS: runnet starter og
    svarer som om intet er galt. Denne vagt måler hvad runnet faktisk ser.
    """
    from contextlib import contextmanager
    from pathlib import Path

    from core.identity.workspace_context import (
        current_user_id,
        current_workspace_name,
    )
    from core.services import inbox_idle_waker as w

    setninger: list[tuple[str, str]] = []

    @contextmanager
    def _reservation(session_id):
        class _R:
            acquired = True
            reason = ""
        yield _R()

    def _fake_start(tekst, **kw):
        # Det er HER beviset ligger: hvad ser runnet, i det øjeblik det starter?
        setninger.append((current_workspace_name(), current_user_id()))
        return True

    monkeypatch.setattr(
        "core.services.background_start_reservation.reserve_background_start",
        _reservation,
    )
    monkeypatch.setattr(
        "core.services.visible_autonomous_run.start_autonomous_run", _fake_start
    )
    monkeypatch.setattr(
        "core.runtime.workspace_paths.workspace_dir",
        lambda uid: Path("/tmp/ws") / "michelle",
    )

    w._start_run("gør noget", session_id="chat-1", user_id="4242")

    assert setninger == [("michelle", "4242")], (
        f"runnet startede uden det rigtige arbejdsrum: {setninger}"
    )


def test_konteksten_rulles_tilbage_efter_runnet(monkeypatch):
    """Bindingen må ikke lække ud i den poller der kaldte vækkeren — ellers
    kører resten af indbakke-runderne i den forkerte brugers arbejdsrum."""
    from contextlib import contextmanager
    from pathlib import Path

    from core.identity.workspace_context import current_workspace_name
    from core.services import inbox_idle_waker as w

    @contextmanager
    def _reservation(session_id):
        class _R:
            acquired = True
            reason = ""
        yield _R()

    monkeypatch.setattr(
        "core.services.background_start_reservation.reserve_background_start",
        _reservation,
    )
    monkeypatch.setattr(
        "core.services.visible_autonomous_run.start_autonomous_run",
        lambda tekst, **kw: True,
    )
    monkeypatch.setattr(
        "core.runtime.workspace_paths.workspace_dir",
        lambda uid: Path("/tmp/ws") / "michelle",
    )

    foer = current_workspace_name()
    w._start_run("gør noget", session_id="chat-1", user_id="4242")
    assert current_workspace_name() == foer, "arbejdsrummet lækkede ud af kaldet"


# ── Afregning efter run (12/11-2026) ────────────────────────────────────────
#
# Bjørn: «du skal enten kvittere når en vækning er overstået … eller systemet
# skal gøre det automatisk efter en vækning er fuldført.»
#
# Denne test maaler TILSLUTNINGEN, ikke bare at funktionen findes. En
# afregning der aldrig bliver kaldt er praecis det teater Bjørn advarer om:
# koden ser rigtig ud, og posten staar fast alligevel.

class _Reservation:
    acquired = True
    reason = ""


@contextmanager
def _reservation(*_a, **_kw):
    yield _Reservation()


def test_runnet_faar_en_completion_callback_der_lukker_posten(
        inbox_db, monkeypatch):
    """Hele kaeden: post → run → callback → posten er `done`.

    Uden tilslutningen ville posten staa `aaben` med et vaekkespor, og
    `kandidater()` springer den over — den kunne hverken rejses igen eller
    lukkes af nogen anden.
    """
    from core.services import inbox_idle_waker as w
    import core.services.background_start_reservation as bsr
    import core.services.visible_autonomous_run as var

    _post(id="job-afregn", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    monkeypatch.setattr(w, "_noget_koerer", lambda: False)
    monkeypatch.setattr(bsr, "reserve_background_start", _reservation)

    fanget: dict = {}

    def _fake_start(tekst, **kw):
        fanget.update(kw)
        # Efterlign starteren: runnet er terminalt, og callbacken kaldes.
        kw["completion_callback"](
            outcome="completed", visible_run_id="autonomous-afregn",
            session_id=kw.get("session_id", ""), error="",
        )
        return True

    monkeypatch.setattr(var, "start_autonomous_run", _fake_start)

    r = w.vaek_paa_aabne_poster(bruger_id="bjorn")
    assert r["vaekket"] == 1, r
    assert callable(fanget.get("completion_callback")), \
        "runnet fik ingen completion_callback — afregningen er ikke tilsluttet"
    # Adressen blev baaret med hele vejen: det er NETOP denne post der blev
    # lukket, ikke en tilfaeldig anden.

    post = db_inbox.hent(bruger_id="bjorn", kilde_id="job-afregn")
    assert post["status"] == db_inbox.STATUS_DONE, post["status"]


def test_et_FEJLET_run_lukker_posten_som_fejlet(inbox_db, monkeypatch):
    """Samme tilslutning, det andet udfald: en fejl maa ikke efterlade posten
    aaben med et vaekkespor, for saa er den laast for evigt."""
    from core.services import inbox_idle_waker as w
    import core.services.background_start_reservation as bsr
    import core.services.visible_autonomous_run as var

    _post(id="job-fejl", ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    monkeypatch.setattr(w, "_noget_koerer", lambda: False)
    monkeypatch.setattr(bsr, "reserve_background_start", _reservation)

    def _fake_start(tekst, **kw):
        kw["completion_callback"](
            outcome="failed", visible_run_id="autonomous-fejl",
            session_id=kw.get("session_id", ""), error="modellen svarede ikke",
        )
        return True

    monkeypatch.setattr(var, "start_autonomous_run", _fake_start)

    assert w.vaek_paa_aabne_poster(bruger_id="bjorn")["vaekket"] == 1
    post = db_inbox.hent(bruger_id="bjorn", kilde_id="job-fejl")
    assert post["status"] == db_inbox.STATUS_FEJLET, post["status"]


# ── Tre grene ved en AKTIV samtale (Bjørn 12/11-2026) ──────────────────────
#
# «inbox skal vurdere om der gået X min uden du eller jeg ikk har skrevet hvis
# det er et ældre wakeup, men hvis det er et wakeup du mangler sår bør inbox
# starte den med det samme eller hvis du er aktiv lægge den markeret i inbox og
# forlange du læserne.»
#
# Målt i drift før fixet: wake-b1f4f73cf9 fyrede 17:55:43 og var stadig
# ubesvaret, fordi samtalen var aktiv 61 sekunder senere. Guarden havde ret i
# at vente — fejlen var at der ikke fandtes en anden udgang.


def _vaekning(id="vaek-wakeup:wake-1", **kw):
    """En post af typen `vaekning`: må starte et run, men gater ikke af sig selv.

    Netop derfor var hun usynlig: hun var hverken kørt (samtalen var aktiv)
    eller krævet (kraever_handling=0).
    """
    return _post(id=id, kildetype="vaekning", kraever_handling=False, **kw)


def test_en_GAMMEL_post_paa_en_aktiv_samtale_bliver_KRAEVET_laest(
        inbox_db, monkeypatch):
    """Den ældre vækning må ikke forsvinde — hun skal KRÆVES, ikke bare vente."""
    from core.services import inbox_idle_waker as w

    _vaekning()
    monkeypatch.setattr(w, "_noget_koerer", lambda: False)
    monkeypatch.setattr(w, "_session_er_aktiv", lambda sid: True)
    monkeypatch.setattr(w, "_alder_minutter", lambda p, **kw: 30.0)
    startet: list[str] = []
    monkeypatch.setattr(w, "_start_run", lambda t, **kw: startet.append(t) or True)

    r = w.vaek_paa_aabne_poster(bruger_id="bjorn")

    assert r["vaekket"] == 0, "en aktiv samtale maa ikke afbrydes"
    assert startet == []
    post = db_inbox.hent(bruger_id="bjorn", kilde_id="vaek-wakeup:wake-1")
    assert post["kraever_handling"] is True, (
        "posten ventede 30 min paa en aktiv samtale og blev hverken koert "
        "eller kraevet — praecis den tilstand der gjorde hende usynlig")
    assert post["status"] == "aaben", "hun skal stadig kunne afgoeres"


def test_en_FRISK_post_paa_en_aktiv_samtale_bliver_IKKE_kraevet(
        inbox_db, monkeypatch):
    """En samtale der er aktiv NU bliver ofte fri om faa minutter — vent."""
    from core.services import inbox_idle_waker as w

    _vaekning()
    monkeypatch.setattr(w, "_noget_koerer", lambda: False)
    monkeypatch.setattr(w, "_session_er_aktiv", lambda sid: True)
    monkeypatch.setattr(w, "_alder_minutter", lambda p, **kw: 1.0)

    r = w.vaek_paa_aabne_poster(bruger_id="bjorn")

    assert r["vaekket"] == 0
    post = db_inbox.hent(bruger_id="bjorn", kilde_id="vaek-wakeup:wake-1")
    assert post["kraever_handling"] is False, (
        "en post paa eet minut skal have sin chance, ikke kraeves med det samme")


def test_en_kraevet_post_GATER_en_mutation(inbox_db, monkeypatch):
    """Beviset der betyder noget: kraevet betyder KRÆVET, ikke blot markeret.

    Uden denne er `kraev_laesning` en label der ser rigtig ud og gør ingenting.
    """
    from core.services import inbox_gate

    _vaekning()
    foer = inbox_gate.evaluer_inbox_mutation(
        "bjorn", "write_file", {"path": "/tmp/x"}, tur="run-1")
    assert foer["blokeret"] is False, "en ikke-gatende post maa ikke blokere"

    db_inbox.kraev_laesning(bruger_id="bjorn", kilde_id="vaek-wakeup:wake-1")

    # Gaten blokerer foerst naar paamindelses-taersklen er naaet; dens foerste
    # svar er en advarsel. Vi koerer den til taersklen og kraever blokaden.
    svar = {}
    for i in range(5):
        svar = inbox_gate.evaluer_inbox_mutation(
            "bjorn", "write_file", {"path": "/tmp/x"}, tur=f"run-{i}")
        if svar["blokeret"]:
            break
    assert svar["blokeret"] is True, (
        "posten blev kraevet, men gaten naegtede stadig ikke — saa er kravet "
        "et teater-flag")
    assert "vaek-wakeup:wake-1" in svar["poster"]


def test_alderen_taelles_fra_fire_at_for_en_vaekning(monkeypatch):
    """En vækning faar sin raekke ved BOOKINGEN — `created_at` kan vaere timer
    ældre end det øjeblik hun fyrer. Maalte vi paa den, ville hver planlagt
    vækning være «gammel» i samme sekund hun fyrer."""
    from datetime import UTC, datetime, timedelta

    from core.services import inbox_idle_waker as w

    nu = datetime(2026, 11, 12, 18, 0, tzinfo=UTC)
    monkeypatch.setattr(w, "_wakeup_records", lambda: {
        "wake-1": {"fire_at": (nu - timedelta(minutes=2)).isoformat()},
    })
    post = {
        "kildetype": "wakeup", "kilde_id": "wake-1",
        "created_at": (nu - timedelta(hours=3)).isoformat(),
    }
    assert w._alder_minutter(post, nu=nu) == pytest.approx(2.0, abs=0.01)

    # En post UDEN en laesbar tid er ikke gatende paa et gæt.
    assert w._alder_minutter({"created_at": ""}, nu=nu) is None
    assert w._alder_minutter({"created_at": "i går"}, nu=nu) is None


# ── `dispatched` er først sandt når runnet er startet ──────────────────────
def _fang_events(monkeypatch) -> list[tuple[str, dict]]:
    from core.eventbus.bus import event_bus

    set_: list[tuple[str, dict]] = []
    monkeypatch.setattr(event_bus, "publish",
                        lambda kind, payload=None, **kw: set_.append((kind, payload or {})))
    return set_


@pytest.mark.parametrize("kilde_id, kildetype, startet, forventet", [
    ("vaek-wakeup:wake-abc", "vaekning", True, [("self_wakeup.dispatched", "wake-abc")]),
    ("vaek-wakeup:wake-abc", "vaekning", None, [("self_wakeup.dispatched", "wake-abc")]),
    # starteren afviste TAVST → intet run → intet dispatched
    ("vaek-wakeup:wake-abc", "vaekning", False, []),
    # en post der ikke er en wakeup-vækning
    ("min", "job", True, []),
    ("vaek-rutine:rec-1", "vaekning", True, []),
])
def test_dispatched_udgives_kun_naar_en_wakeup_faktisk_har_faaet_sit_run(
        inbox_db, monkeypatch, kilde_id, kildetype, startet, forventet):
    from core.services import inbox_idle_waker as w

    _post(id=kilde_id, kildetype=kildetype, ejer=db_inbox.EJER_JARVIS, kraever_handling=True)
    monkeypatch.setattr(w, "_noget_koerer", lambda: False)
    monkeypatch.setattr(w, "_start_run", lambda tekst, **kw: startet)
    publiceret = _fang_events(monkeypatch)

    r = w.vaek_paa_aabne_poster(bruger_id="bjorn")

    assert r == {"status": "ok", "vaekket": 0 if startet is False else 1}
    ud = [(k, p.get("wakeup_id")) for k, p in publiceret if k.startswith("self_wakeup.")]
    assert ud == forventet
