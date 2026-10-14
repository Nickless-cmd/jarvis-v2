"""De fem korrigerede steps fra autonomi-auditten skal BIDE — ikke bare stå der.

Audit: ``docs/audits/2026-10-14-autonomous-execution-integrity.md`` §11, revideret
samme dag efter gennemgang. Hver test pinner ÉN af de fem, så en regression
navngives af sin egen test i stedet for at gemme sig i en samlet suite.

Steps der pinnes her:

1. Kæde-stemplet i ALLE run-startere (ikke kun genoptagelses-dispatcheren).
6. Genoptagelses-vækningen bærer sin samtale.
7. ``_allerede_besvaret`` kan scopes til runnets samtale.

Steps 3 og 5 bruger ``inbox_db``-fixturen og bor derfor i
``tests/test_inbox_idle_waker.py``, hvor den er defineret.

Steps 2 og 4 blev TRUKKET TILBAGE i revisionen og har derfor ingen test.
"""
from __future__ import annotations


# ── Step 1 — kæde-stemplet i alle startere ──────────────────────────────────


def test_stempl_aktiv_kaede_arver_naar_kaeden_er_i_gang(monkeypatch):
    """Er kæden > 0, arver runnet opgavens id og kæden + 1."""
    from core.services import in_flight_runs as ifr

    monkeypatch.setattr(
        ifr,
        "_load",
        lambda: {
            "r1": {
                "session_id": "s1", "kind": "visible", "recovery_attempt": 2,
                "task_id": "opg-1", "run_id": "r1",
                "started_at": "2026-10-14T10:00:00+00:00",
            }
        },
    )
    kald: dict = {}
    monkeypatch.setattr(ifr, "stempl_genoptagelse", lambda **kw: kald.update(kw))

    assert ifr.stempl_aktiv_kaede(run_id="nyt", session_id="s1",
                                  origin="wakeup") is True
    assert kald["run_id"] == "nyt"
    assert kald["task_id"] == "opg-1", "opgavens id skal følge kæden"
    assert kald["recovery_attempt"] == 3, "kæden skal tælle op, ikke starte forfra"


def test_stempl_aktiv_kaede_roerer_ikke_en_frisk_opgave(monkeypatch):
    """Er kæden 0, er posten en frisk opgave — vi stempler INTET.

    Det er den almindelige brugertur (som nulstiller kæden ved at journalføre
    sig med 0) og enhver opgave i en samtale uden historik.
    """
    from core.services import in_flight_runs as ifr

    monkeypatch.setattr(ifr, "_load", lambda: {})
    kald: list = []
    monkeypatch.setattr(ifr, "stempl_genoptagelse", lambda **kw: kald.append(kw))

    assert ifr.stempl_aktiv_kaede(run_id="nyt", session_id="s1",
                                  origin="wakeup") is False
    assert kald == []


def test_stempl_aktiv_kaede_er_self_safe(monkeypatch):
    """Et fejlende stempel må ikke kaste videre til starteren."""
    from core.services import in_flight_runs as ifr

    def braender(_sid):
        raise RuntimeError("kunne ikke læse journalen")

    monkeypatch.setattr(ifr, "aktiv_kaede", braender)
    assert ifr.stempl_aktiv_kaede(run_id="nyt", session_id="s1",
                                  origin="wakeup") is False


def test_aktiv_kaede_giver_baade_tal_og_opgave(monkeypatch):
    """Tallet og opgavens id skal komme fra SAMME post — den nyeste."""
    from core.services import in_flight_runs as ifr

    monkeypatch.setattr(
        ifr,
        "_load",
        lambda: {
            "gammel": {
                "session_id": "s1", "kind": "visible", "recovery_attempt": 1,
                "task_id": "opg-1", "run_id": "gammel",
                "started_at": "2026-10-14T09:00:00+00:00",
            },
            "ny": {
                "session_id": "s1", "kind": "visible", "recovery_attempt": 2,
                "task_id": "opg-1", "run_id": "ny",
                "started_at": "2026-10-14T10:00:00+00:00",
            },
        },
    )
    assert ifr.aktiv_kaede("s1") == (2, "opg-1")
    assert ifr.aktiv_kaede("") == (0, "")
    assert ifr.aktiv_kaede("ukendt-samtale") == (0, "")


def test_ny_opgave_i_samme_samtale_arver_ikke_kaeden(monkeypatch):
    """REGRESSIONSTEST (ChatGPT's indvending, 14/10-2026).

    «En fælles session er ikke dokumentation for en fælles forpligtelse.»

    Opgave A er midt i en kæde i samtalen. En HELT NY opgave B starter i SAMME
    samtale — en `recurring`-påmindelse, en `scheduled`-opgave, en drøm. B må
    ikke arve A's task_id. Gjorde den det, havde vi ikke fjernet
    identitets-problemet, kun vendt det om: to uafhængige opgaver med ÉN
    identitet.

    Målt ved hvert kaldested: `recurring`, `scheduled`, `dream`, `heartbeat`,
    `session_spawn` og `agent-completion` starter alle et FRISKT arbejde. Kun
    `wakeup` (living_executive's genoptagelse) og `inbox` (vækkeren) løfter en
    forpligtelse der allerede findes.
    """
    from core.services import in_flight_runs as ifr

    monkeypatch.setattr(
        ifr,
        "_load",
        lambda: {
            "A": {
                "session_id": "s1", "kind": "visible", "recovery_attempt": 2,
                "task_id": "opg-A", "run_id": "A",
                "started_at": "2026-10-14T10:00:00+00:00",
            }
        },
    )
    kald: list = []
    monkeypatch.setattr(ifr, "stempl_genoptagelse", lambda **kw: kald.append(kw))

    for ny_origin in ("recurring", "scheduled", "dream", "heartbeat",
                      "session_spawn", "agent-completion", "autonomous"):
        assert ifr.stempl_aktiv_kaede(
            run_id=f"B-{ny_origin}", session_id="s1", origin=ny_origin
        ) is False, f"«{ny_origin}» starter en NY opgave og må ikke arve kæden"
    assert kald == [], "ingen ny opgave må få en anden opgaves identitet"


def test_en_fortsaettelse_stempler_stadig(monkeypatch):
    """Gaten må ikke gøre step 1 virkningsløs.

    En vækning der TAGER en forpligtelse op (`wakeup` fra living_executive,
    `inbox` fra vækkeren) skal stadig arve kæden — ellers er loftet lige så
    uopnåeligt som før.
    """
    from core.services import in_flight_runs as ifr

    monkeypatch.setattr(
        ifr,
        "_load",
        lambda: {
            "A": {
                "session_id": "s1", "kind": "visible", "recovery_attempt": 2,
                "task_id": "opg-A", "run_id": "A",
                "started_at": "2026-10-14T10:00:00+00:00",
            }
        },
    )
    for origin in ("wakeup", "inbox", "continuation"):
        kald: dict = {}
        monkeypatch.setattr(ifr, "stempl_genoptagelse", lambda **kw: kald.update(kw))
        assert ifr.stempl_aktiv_kaede(
            run_id="ny", session_id="s1", origin=origin
        ) is True, f"«{origin}» tager en forpligtelse op og skal stemple"
        assert kald["task_id"] == "opg-A"
        assert kald["recovery_attempt"] == 3


# ── Step 6 — vækningen bærer sin samtale ────────────────────────────────────


def test_genoptagelses_vaekning_binder_sin_samtale(monkeypatch):
    """Vækningen bookes UDEN sin samtale → dispatcherens fallback vælger.

    Det er en konkret mekanisme for at arbejdet dukker op i en anden samtale end
    den hvor det blev afbrudt.
    """
    from core.services import living_executive as le

    monkeypatch.setattr(le, "_session_for_run", lambda rid: "chat-abc")
    monkeypatch.setattr(le, "_genoptag_loft_naaet", lambda: None)
    monkeypatch.setattr(le, "_noter_genoptagelse", lambda: None)

    fanget: dict = {}

    def _fake_schedule(**kw):
        fanget.update(kw)
        return {"status": "ok", "wakeup": {"wakeup_id": "w1"}}

    monkeypatch.setattr("core.services.self_wakeup.schedule_self_wakeup", _fake_schedule)

    impulse = {
        "payload": {
            "run_id": "visible-x", "prompt": "p", "delay_seconds": 30,
            "reason": f"living-executive:{le._GENOPTAG_NOEGLE}",
        }
    }
    le._action_schedule_self_wakeup(impulse)

    assert fanget.get("session_id") == "chat-abc"


def test_ukendt_samtale_sender_ingen_binding(monkeypatch):
    """Kan samtalen ikke afgøres, sendes `None` — ikke en gættet session."""
    from core.services import living_executive as le

    monkeypatch.setattr(le, "_session_for_run", lambda rid: "")
    monkeypatch.setattr(le, "_genoptag_loft_naaet", lambda: None)
    monkeypatch.setattr(le, "_noter_genoptagelse", lambda: None)

    fanget: dict = {}

    def _fake_schedule(**kw):
        fanget.update(kw)
        return {"status": "ok", "wakeup": {"wakeup_id": "w1"}}

    monkeypatch.setattr("core.services.self_wakeup.schedule_self_wakeup", _fake_schedule)

    impulse = {
        "payload": {
            "run_id": "visible-x", "prompt": "p", "delay_seconds": 30,
            "reason": f"living-executive:{le._GENOPTAG_NOEGLE}",
        }
    }
    le._action_schedule_self_wakeup(impulse)

    assert fanget.get("session_id") is None


# ── Step 7 — `_allerede_besvaret` kan scopes ────────────────────────────────


def test_session_for_run_er_aerlig_naar_den_ikke_ved_det():
    """Et tomt svar er et rigtigt svar: så kan vi ikke scope, og den brede
    adfærd bevares frem for at gætte en samtale."""
    from core.services import living_executive as le

    assert le._session_for_run("") == ""


def test_allerede_besvaret_scoper_paa_samtalen(monkeypatch):
    """SQL'en skal bære et session-filter når samtalen er kendt."""
    from core.services import living_executive as le

    fanget: list = []

    class _FakeConn:
        def execute(self, sql, params):
            fanget.append((sql, params))

            class _R:
                def fetchone(self):
                    return ("2026-10-14T10:00:00+00:00",) if len(params) == 1 else (0,)

            return _R()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(le, "_session_for_run", lambda rid: "chat-abc")
    monkeypatch.setattr("core.runtime.db.connect", lambda: _FakeConn())

    le._allerede_besvaret("visible-x")

    sqls = " ".join(s for s, _ in fanget)
    assert "tool_router_decisions" in sqls, "samtale-scopet mangler"
    assert any("session_id = ?" in s for s, _ in fanget)
    assert any("chat-abc" in str(p) for _, p in fanget)


def test_allerede_besvaret_genoptager_naar_samtalen_er_ukendt(monkeypatch):
    """REGRESSIONSTEST (ChatGPT's P1, 14/10-2026).

    Uden samtale faldt funktionen tilbage til en GLOBAL søgning: en afsluttet
    kørsel i en helt ANDEN samtale blev læst som «brugeren er gået videre», og
    en legitim genoptagelse blev droppet TAVST. Det er ikke fail-safe, det er
    fail-silent-drop. Tvivlen skal falde ud til at genoptage — samme regel som
    når basen ikke kan læses.
    """
    from core.services import living_executive as le

    kald: list = []

    class _FakeConn:
        def execute(self, sql, params):
            kald.append((sql, params))

            class _R:
                def fetchone(self):
                    return ("2026-10-14T10:00:00+00:00",)

            return _R()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(le, "_session_for_run", lambda rid: "")
    monkeypatch.setattr("core.runtime.db.connect", lambda: _FakeConn())

    assert le._allerede_besvaret("visible-x") is False
    assert len(kald) == 1, "kun opslaget af finished_at — ingen global søgning"


# ── Opgavens id føres eksplicit gennem vækningen (14/10-2026) ───────────────
#
# `source_id → task_id → claim → run_id → outcome`. Origin er ikke
# opgaveidentitet: en `wakeup` eller en inbox-post KAN være en fortsættelse,
# men kan også være helt nyt arbejde. Bærer kalderen id'et, behøver vi ikke
# gætte — og origin-gaten degraderes fra «det eneste signal» til en fallback.


def test_eksplicit_task_id_stempler_uanset_origin(monkeypatch):
    """Et eksplicit id VINDER over origin-navnet."""
    from core.services import in_flight_runs as ifr

    monkeypatch.setattr(ifr, "_load", lambda: {})
    kald: dict = {}
    monkeypatch.setattr(ifr, "stempl_genoptagelse", lambda **kw: kald.update(kw))

    # `recurring` er ikke en fortsættelses-origin — men med et eksplicit id
    # ved vi bedre end navnet.
    assert ifr.stempl_aktiv_kaede(run_id="nyt", session_id="s1",
                                  origin="recurring", task_id="opg-Z") is True
    assert kald["task_id"] == "opg-Z"
    assert kald["recovery_attempt"] == 1, (
        "mindst ét forsøg er brugt — runnet ER en fortsættelse"
    )


def test_eksplicit_id_arver_kaede_tallet(monkeypatch):
    """Id'et erstatter identiteten — ikke tælleren. Er kæden kendt, tælles op."""
    from core.services import in_flight_runs as ifr

    monkeypatch.setattr(
        ifr,
        "_load",
        lambda: {
            "A": {
                "session_id": "s1", "kind": "visible", "recovery_attempt": 2,
                "task_id": "opg-A", "run_id": "A",
                "started_at": "2026-10-14T10:00:00+00:00",
            }
        },
    )
    kald: dict = {}
    monkeypatch.setattr(ifr, "stempl_genoptagelse", lambda **kw: kald.update(kw))

    assert ifr.stempl_aktiv_kaede(run_id="nyt", session_id="s1",
                                  origin="recurring", task_id="opg-A") is True
    assert kald["recovery_attempt"] == 3


def test_eksplicit_id_arver_IKKE_en_anden_opgaves_taeller(monkeypatch):
    """REGRESSIONSTEST (ChatGPT's anden indvending, 14/10-2026).

    «Forsøgstælleren skal findes ud fra `task_id`, når det er angivet — ikke
    fra sessionens seneste kæde.»

    Opgave A staar paa forsoeg 2 i samtalen. Opgave B vaekkes i SAMME samtale
    med sit EGET eksplicitte id. B skal have sit eget budget: ét forsoeg brugt
    — ikke A's 3. Ellers er identiteten rigtig og budgettet laant, og loftet
    paa tre kan stadig omgaas ved at skifte opgave inden for samme samtale.
    """
    from core.services import in_flight_runs as ifr

    monkeypatch.setattr(
        ifr,
        "_load",
        lambda: {
            "A": {
                "session_id": "s1", "kind": "visible", "recovery_attempt": 2,
                "task_id": "opg-A", "run_id": "A",
                "started_at": "2026-10-14T10:00:00+00:00",
            }
        },
    )
    kald: dict = {}
    monkeypatch.setattr(ifr, "stempl_genoptagelse", lambda **kw: kald.update(kw))

    assert ifr.stempl_aktiv_kaede(run_id="B", session_id="s1",
                                  origin="wakeup", task_id="opg-B") is True
    assert kald["task_id"] == "opg-B", "B's eget id — ikke A's"
    assert kald["recovery_attempt"] == 1, (
        "B maa ikke arve A's forsoegstal: en anden opgave er et andet budget"
    )


def test_eksplicit_id_arver_sit_eget_tal_naar_opgaven_er_set_foer(monkeypatch):
    """Samme opgave, tidligere led: tallet skal FORTSÆTTE, ikke nulstilles.

    Modstykket til testen ovenfor. Uden den kunne rettelsen blive «tæl altid
    fra 1», og saa kunne loftet aldrig naas for den opgave der faktisk
    genoptages.
    """
    from core.services import in_flight_runs as ifr

    monkeypatch.setattr(
        ifr,
        "_load",
        lambda: {
            "A": {
                "session_id": "s1", "kind": "visible", "recovery_attempt": 2,
                "task_id": "opg-A", "run_id": "A",
                "started_at": "2026-10-14T10:00:00+00:00",
            },
            "B": {
                "session_id": "s1", "kind": "visible", "recovery_attempt": 1,
                "task_id": "opg-B", "run_id": "B",
                "started_at": "2026-10-14T11:00:00+00:00",
            },
        },
    )
    kald: dict = {}
    monkeypatch.setattr(ifr, "stempl_genoptagelse", lambda **kw: kald.update(kw))

    assert ifr.stempl_aktiv_kaede(run_id="C", session_id="s1",
                                  origin="wakeup", task_id="opg-B") is True
    assert kald["task_id"] == "opg-B"
    assert kald["recovery_attempt"] == 2, "B's eget led nummer to"


def test_vaekningen_gemmer_opgavens_id(monkeypatch):
    """`schedule_self_wakeup` skal kunne BÆRE forpligtelsen videre."""
    from core.services import self_wakeup as sw

    gemt: list = []
    monkeypatch.setattr(sw, "_load", lambda: [])
    monkeypatch.setattr(sw, "_save", lambda recs: gemt.extend(recs))

    r = sw.schedule_self_wakeup(delay_seconds=60, prompt="p", task_id="opg-Z")
    assert r.get("status") == "ok"
    assert gemt and gemt[0].get("task_id") == "opg-Z"

    gemt.clear()
    sw.schedule_self_wakeup(delay_seconds=60, prompt="p")
    assert gemt and gemt[0].get("task_id") is None, "nyt arbejde bærer intet id"


def test_genoptagelsen_baerer_opgavens_id(monkeypatch):
    """Vækningen skal bære FORPLIGTELSEN — ikke kun dens samtale."""
    from core.services import in_flight_runs as ifr
    from core.services import living_executive as le

    monkeypatch.setattr(le, "_session_for_run", lambda rid: "chat-abc")
    monkeypatch.setattr(le, "_genoptag_loft_naaet", lambda: None)
    monkeypatch.setattr(le, "_noter_genoptagelse", lambda: None)
    monkeypatch.setattr(
        ifr, "get_record",
        lambda rid: {"task_id": "opg-A", "session_id": "chat-abc"},
    )

    fanget: dict = {}

    def _fake_schedule(**kw):
        fanget.update(kw)
        return {"status": "ok", "wakeup": {"wakeup_id": "w1"}}

    monkeypatch.setattr("core.services.self_wakeup.schedule_self_wakeup", _fake_schedule)

    le._action_schedule_self_wakeup({"payload": {
        "run_id": "visible-x", "prompt": "p", "delay_seconds": 30,
        "reason": f"living-executive:{le._GENOPTAG_NOEGLE}",
    }})

    assert fanget.get("task_id") == "opg-A"
    assert fanget.get("session_id") == "chat-abc"


def test_en_paamindelse_baerer_ikke_et_opgave_id(monkeypatch):
    """En påmindelse er NYT arbejde — den må ikke arve en forpligtelse."""
    from core.services import living_executive as le

    monkeypatch.setattr(le, "_session_for_run", lambda rid: "chat-abc")

    fanget: dict = {}

    def _fake_schedule(**kw):
        fanget.update(kw)
        return {"status": "ok", "wakeup": {"wakeup_id": "w1"}}

    monkeypatch.setattr("core.services.self_wakeup.schedule_self_wakeup", _fake_schedule)

    le._action_schedule_self_wakeup({"payload": {
        "run_id": "visible-x", "prompt": "p", "delay_seconds": 30,
        "reason": "living-executive:reminder",
    }})

    assert fanget.get("task_id") == ""


def test_hele_kaeden_baerer_task_id():
    """KONTRAKTEN: et brud i ét led gør de tre andre virkningsløse.

    Vækningen → dispatcheren → starteren → stemplet. Alle fire skal kunne
    bære opgavens id, ellers er `source_id → task_id → run_id` en påstand
    uden et sted at bo.
    """
    import inspect

    from core.services import (
        autonomous_stream_run,
        in_flight_runs,
        self_wakeup,
        visible_autonomous_run,
    )

    for funktion in (
        in_flight_runs.stempl_aktiv_kaede,
        self_wakeup.schedule_self_wakeup,
        autonomous_stream_run.start_autonomous_stream_run,
        visible_autonomous_run.start_autonomous_run,
    ):
        assert "task_id" in inspect.signature(funktion).parameters, (
            f"{funktion.__module__}.{funktion.__name__} mangler task_id"
        )
