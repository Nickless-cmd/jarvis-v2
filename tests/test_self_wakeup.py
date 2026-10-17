"""Unit tests for self_wakeup."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import core.services.self_wakeup as sw


def test_schedule_validates_prompt(monkeypatch):
    monkeypatch.setattr(sw, "_load", lambda: [])
    monkeypatch.setattr(sw, "_save", lambda r: None)
    result = sw.schedule_self_wakeup(delay_seconds=120, prompt="")
    assert result["status"] == "error"


def test_schedule_clamps_delay(monkeypatch):
    state: list = []
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))
    # Below min
    result = sw.schedule_self_wakeup(delay_seconds=10, prompt="x")
    assert result["wakeup"]["delay_seconds"] == 60
    # Above max
    state.clear()
    result = sw.schedule_self_wakeup(delay_seconds=999999, prompt="x")
    assert result["wakeup"]["delay_seconds"] == 86400


def test_schedule_persists(monkeypatch):
    state: list = []
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))
    result = sw.schedule_self_wakeup(delay_seconds=120, prompt="resume X", reason="test")
    assert result["status"] == "ok"
    assert result["wakeup"]["status"] == "pending"
    assert "resume X" in result["wakeup"]["prompt"]
    assert len(state) == 1


def test_tool_schedule_binds_current_session_and_user(monkeypatch):
    """Regression: a wakeup must return to the visible session that created it."""
    from core.identity.workspace_context import reset_context, set_context

    state: list = []
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))
    token = set_context(
        workspace_name="bjorn",
        user_id="owner-123",
        user_display_name="Bjoern",
        role="owner",
        channel="jarvisx-electron",
        session_id="chat-origin",
    )
    try:
        result = sw._exec_schedule_self_wakeup({
            "delay_seconds": 120,
            "prompt": "resume X",
            "reason": "test",
        })
    finally:
        reset_context(token)

    wakeup = result["wakeup"]
    assert wakeup["session_id"] == "chat-origin"
    assert wakeup["user_id"] == "owner-123"
    assert wakeup["workspace_name"] == "bjorn"
    assert wakeup["user_display_name"] == "Bjoern"
    assert wakeup["role"] == "owner"
    assert wakeup["context_channel"] == "jarvisx-electron"


def test_tool_schedule_baerer_peak_varsel_naar_den_lander_i_vinduet(monkeypatch):
    """Peak-værnet skal sidde på BOOKING-VEJEN, ikke kun i hjælperen (7/10-2026).

    Hjælperen alene beviser intet: en funktion der virker og aldrig bliver kaldt
    er husets dyreste fejlform. Denne test går gennem exec-funktionen og beviser
    at svaret fra et rigtigt booking-forsøg bærer varslet.
    """
    from core.identity.workspace_context import reset_context, set_context

    monkeypatch.setattr(sw, "_load", lambda: [])
    monkeypatch.setattr(sw, "_save", lambda r: None)
    # Onsdag 06:00 UTC = 08:00 dansk — inde i dagvinduet (06-10 UTC).
    peak_tid = "2026-10-07T06:00:00+00:00"
    monkeypatch.setattr(
        sw, "schedule_self_wakeup",
        lambda **kw: {"status": "ok",
                      "wakeup": {"wakeup_id": "w1", "fire_at": peak_tid}},
    )
    token = set_context(
        workspace_name="bjorn",
        user_id="owner-123",
        user_display_name="Bjoern",
        role="owner",
        channel="jarvisx-electron",
        session_id="chat-origin",
    )
    try:
        result = sw._exec_schedule_self_wakeup({"delay_seconds": 120, "prompt": "x"})
    finally:
        reset_context(token)

    assert result["status"] == "ok"
    assert "peak_varsel" in result, "bookingen landede i vinduet — det skal stå i svaret"
    assert "MYLDRETIDEN" in result["peak_varsel"]


def test_tool_schedule_er_tav_naar_den_lander_i_off_peak(monkeypatch):
    """Modprøven: uden for vinduet skal svaret være som før — intet nyt felt."""
    from core.identity.workspace_context import reset_context, set_context

    monkeypatch.setattr(sw, "_load", lambda: [])
    monkeypatch.setattr(sw, "_save", lambda r: None)
    # Onsdag 14:00 UTC = 16:00 dansk — mellem de to vinduer.
    fri_tid = "2026-10-07T14:00:00+00:00"
    monkeypatch.setattr(
        sw, "schedule_self_wakeup",
        lambda **kw: {"status": "ok",
                      "wakeup": {"wakeup_id": "w2", "fire_at": fri_tid}},
    )
    token = set_context(
        workspace_name="bjorn",
        user_id="owner-123",
        user_display_name="Bjoern",
        role="owner",
        channel="jarvisx-electron",
        session_id="chat-origin",
    )
    try:
        result = sw._exec_schedule_self_wakeup({"delay_seconds": 120, "prompt": "x"})
    finally:
        reset_context(token)

    assert result["status"] == "ok"
    assert "peak_varsel" not in result


def test_max_pending_limit(monkeypatch):
    state = [{"wakeup_id": f"w{i}", "status": "pending"} for i in range(20)]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: None)
    result = sw.schedule_self_wakeup(delay_seconds=120, prompt="x")
    assert result["status"] == "error"
    assert "max 20" in result["error"]


def test_due_wakeups_marks_fired(monkeypatch):
    past = (datetime.now(UTC) - timedelta(seconds=10)).isoformat()
    future = (datetime.now(UTC) + timedelta(seconds=300)).isoformat()
    state = [
        {"wakeup_id": "w1", "status": "pending", "fire_at": past, "prompt": "p1", "reason": "r1"},
        {"wakeup_id": "w2", "status": "pending", "fire_at": future, "prompt": "p2", "reason": ""},
    ]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))
    due = sw.due_wakeups()
    ids = [r["wakeup_id"] for r in due]
    assert "w1" in ids
    assert "w2" not in ids
    # w1 should now be marked fired in state
    w1 = next(r for r in state if r["wakeup_id"] == "w1")
    assert w1["status"] == "fired"


def test_mark_consumed(monkeypatch):
    state = [{"wakeup_id": "w1", "status": "fired", "prompt": "p", "reason": ""}]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))
    result = sw.mark_wakeup_consumed("w1")
    assert result["status"] == "ok"
    assert state[0]["status"] == "consumed"


def test_cancel_pending(monkeypatch):
    state = [{"wakeup_id": "w1", "status": "pending"}]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))
    result = sw.cancel_wakeup("w1")
    assert result["status"] == "ok"
    assert state[0]["status"] == "cancelled"


def test_cancel_fired_fails(monkeypatch):
    state = [{"wakeup_id": "w1", "status": "fired"}]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: None)
    result = sw.cancel_wakeup("w1")
    assert result["status"] == "error"


def test_section_returns_none_when_no_fired(monkeypatch):
    monkeypatch.setattr(sw, "due_wakeups", lambda **kw: [])
    assert sw.self_wakeup_section() is None


def test_cleanup_removes_old_consumed(monkeypatch):
    now = datetime.now(UTC)
    old = (now - timedelta(hours=200)).isoformat()  # > 7 dage
    fresh = (now - timedelta(hours=24)).isoformat()  # < 7 dage
    state = [
        {"wakeup_id": "w1", "status": "consumed", "consumed_at": old, "prompt": "old"},
        {"wakeup_id": "w2", "status": "consumed", "consumed_at": fresh, "prompt": "fresh"},
        {"wakeup_id": "w3", "status": "pending", "fire_at": (now + timedelta(hours=1)).isoformat(), "prompt": "future"},
    ]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))
    result = sw.cleanup_old_wakeups()
    assert result["removed"] == 1  # kun w1 (gammel consumed)
    assert result["remaining"] == 2
    ids = [r["wakeup_id"] for r in state]
    assert "w1" not in ids
    assert "w2" in ids
    assert "w3" in ids


def test_cleanup_removes_old_cancelled(monkeypatch):
    now = datetime.now(UTC)
    state = [
        {"wakeup_id": "w1", "status": "cancelled", "scheduled_at": (now - timedelta(hours=200)).isoformat(), "prompt": "old"},
        {"wakeup_id": "w2", "status": "cancelled", "scheduled_at": (now - timedelta(hours=24)).isoformat(), "prompt": "fresh"},
    ]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))
    result = sw.cleanup_old_wakeups()
    assert result["removed"] == 1  # kun w1
    assert result["remaining"] == 1
    assert state[0]["wakeup_id"] == "w2"


def test_cleanup_removes_stale_fired(monkeypatch):
    now = datetime.now(UTC)
    state = [
        {"wakeup_id": "w1", "status": "fired", "fired_at": (now - timedelta(hours=48)).isoformat(), "prompt": "stale", "consumed_at": None},
        {"wakeup_id": "w2", "status": "fired", "fired_at": (now - timedelta(hours=2)).isoformat(), "prompt": "recent", "consumed_at": None},
    ]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))
    result = sw.cleanup_old_wakeups()
    assert result["removed"] == 1  # kun w1 (stale > 24h)
    assert result["remaining"] == 1
    assert state[0]["wakeup_id"] == "w2"


def test_cleanup_noop_when_nothing_old(monkeypatch):
    now = datetime.now(UTC)
    state = [
        {"wakeup_id": "w1", "status": "consumed", "consumed_at": (now - timedelta(hours=2)).isoformat(), "prompt": "recent"},
        {"wakeup_id": "w2", "status": "fired", "fired_at": (now - timedelta(hours=2)).isoformat(), "prompt": "recent", "consumed_at": None},
        {"wakeup_id": "w3", "status": "pending", "fire_at": (now + timedelta(hours=1)).isoformat(), "prompt": "future"},
    ]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))
    result = sw.cleanup_old_wakeups()
    assert result["removed"] == 0
    assert result["remaining"] == 3


def test_section_lists_fired_wakeups(monkeypatch):
    monkeypatch.setattr(sw, "due_wakeups", lambda **kw: [
        {"wakeup_id": "w1", "status": "fired",
         "prompt": "Tjek om brugeren er klar", "reason": "follow-up"},
    ])
    section = sw.self_wakeup_section()
    assert section is not None
    assert "Tjek om brugeren er klar" in section
    assert "follow-up" in section


# ── Vækningen hører til ÉN samtale (målt 16/10-2026) ─────────────────────


@contextmanager
def _i_samtale(sid: str):
    """Sæt den aktuelle samtale for blokken — og ryd op bagefter."""
    from core.identity import workspace_context as ws

    tok = ws.set_session_id(sid)
    try:
        yield
    finally:
        ws._current_state.reset(tok)


def _sektion(monkeypatch, records: list[dict]) -> str | None:
    monkeypatch.setattr(sw, "due_wakeups", lambda **kw: records)
    return sw.self_wakeup_section()


def test_sektionen_skjuler_vaekninger_fra_en_ANDEN_samtale(monkeypatch):
    """Målt 16/10-2026: `wake-0352149b73` pegede på `chat-f6b595cd…`, men
    dukkede op i awareness i en ANDEN samtale — og svaret landede dér. Bjørn:
    «du kom ikk tilbage?», mens arbejdet var gjort et andet sted.

    En vækning der peger på en fremmed samtale må ikke vises her: dens svar
    hører hjemme der nogen venter, og awareness her ville flytte det væk.
    """
    rec = [{"wakeup_id": "w1", "status": "fired", "prompt": "tjek CI",
            "session_id": "chat-ANDEN"}]
    with _i_samtale("chat-MIN"):
        assert _sektion(monkeypatch, rec) is None


def test_sektionen_viser_vaekningen_i_sit_eget_hjem(monkeypatch):
    """Samme vækning, men i den samtale den peger på — der SKAL den vises."""
    rec = [{"wakeup_id": "w1", "status": "fired", "prompt": "tjek CI",
            "session_id": "chat-MIN"}]
    with _i_samtale("chat-MIN"):
        sektion = _sektion(monkeypatch, rec)
    assert sektion is not None
    assert "tjek CI" in sektion


def test_hjemloes_vaekning_vises_i_enhver_samtale(monkeypatch):
    """Uden `session_id` har vækningen intet sted at vente. At skjule den
    ville gøre den usynlig for ALLE — værre end den støj filtreringen undgår.
    """
    rec = [{"wakeup_id": "w1", "status": "fired", "prompt": "hjemloes"}]
    with _i_samtale("chat-MIN"):
        sektion = _sektion(monkeypatch, rec)
    assert sektion is not None
    assert "hjemloes" in sektion


def test_ukendt_samtale_viser_ALT(monkeypatch):
    """Kan vi ikke afgøre hjemmet (`""`, fx et heartbeat-tick), må et gæt ikke
    skjule noget. Filtreringen falder tilbage til den gamle adfærd."""
    rec = [{"wakeup_id": "w1", "status": "fired", "prompt": "x",
            "session_id": "chat-ANDEN"}]
    with _i_samtale(""):
        assert _sektion(monkeypatch, rec) is not None


# ── Sjette fejl: kilden kan være terminal på en måde lukkeren ikke genkendte ──

def _komplet(wakeup_id: str, status: str) -> dict:
    """En record med de felter `schedule_self_wakeup` selv skriver.

    Uden dem måler testen sin egen mangel på felter i stedet for sit emne.
    """
    return {
        "wakeup_id": wakeup_id, "status": status, "prompt": "p", "reason": "",
        "extra": None, "scheduled_at": "2026-10-04T06:17:50+00:00",
        "fire_at": "2026-10-04T06:27:50+00:00", "delay_seconds": 600,
        "fired_at": None, "consumed_at": "2026-10-04T06:25:28+00:00",
        "channel": "app", "session_id": None, "user_id": "bjorn",
        "workspace_name": None, "user_display_name": None, "role": None,
        "context_channel": None,
    }


def test_mark_consumed_paa_en_ALLEREDE_consumed_er_idempotent(monkeypatch):
    """At kvittere en allerede kvitteret vækning er en NO-OP, ikke en fejl.

    Målt live 4/10-2026: `inbox_done(wake-558ac30db3)` svarede «wakeup
    status=consumed, can't consume» — og den durable række stod stadig
    `aaben` med `kraever_handling=1`, så den gatede permanent. Posten kunne
    ikke lukkes med det værktøj der findes til at lukke den.

    `_luk_kilden` i inbox_state accepterer ALLEREDE svaret «already» som
    succes. Det er kilden her der aldrig svarede det.
    """
    state = [_komplet("w1", "consumed")]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))
    result = sw.mark_wakeup_consumed("w1")
    assert result["status"] == "already", f"en kvitteret vaekning blev en fejl: {result}"
    assert state[0]["status"] == "consumed", "en no-op aendrede tilstanden"


def test_mark_consumed_paa_en_CANCELLED_er_idempotent(monkeypatch):
    """Samme form, anden terminal tilstand.

    `cancel_wakeup` lukker vækningen, ikke dens durable række — målt
    4/10-2026 på `wake-99ac19041a`, hvor posten stod åben efter annulleringen.
    """
    state = [_komplet("w1", "cancelled")]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: None)
    result = sw.mark_wakeup_consumed("w1")
    assert result["status"] == "already", f"en annulleret vaekning blev en fejl: {result}"


def test_mark_consumed_paa_en_UKENDT_tilstand_er_STADIG_en_fejl(monkeypatch):
    """Modprøven. Rettelsen må ikke gøre kvitteringen blind.

    En tilstand vi ikke kender er ikke det samme som en terminal tilstand —
    og en post man ikke kan afgøre er værre end ingen post.
    """
    state = [_komplet("w1", "noget-nyt")]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: None)
    assert sw.mark_wakeup_consumed("w1")["status"] == "error"


# ── Kaede-loftet (5/10-2026) ────────────────────────────────────────────────
#
# Bjoern: «Hvorfor for jeg 3 til 5 beskeder på et svar??» Hver kvitteret
# vaekning bookede en ny. `_MAX_PENDING` kunne ikke se det: en kaede forbruger
# hvert led foer den booker det naeste, saa de ventende er altid 0 eller 1.
# Maalt i `self_wakeups.json`: 140 poster, 116 consumed, NUL ventende.

def _poster(n: int, *, sid: str = "chat-A", status: str = "consumed",
            timer_siden: float = 1.0) -> list[dict]:
    stamp = (datetime.now(UTC) - timedelta(hours=timer_siden)).isoformat()
    return [{"wakeup_id": f"wake-{i}", "session_id": sid, "status": status,
             "scheduled_at": stamp} for i in range(n)]


def test_kaede_loftet_AFVISER_ved_graensen(monkeypatch):
    """Den test hooken kraever: vagten skal ses afvise."""
    monkeypatch.setattr(sw, "_load", lambda: _poster(sw._MAX_PR_SAMTALE_PR_DOEGN))
    monkeypatch.setattr(sw, "_save", lambda r: None)
    res = sw.schedule_self_wakeup(delay_seconds=900, prompt="tjek igen",
                                  session_id="chat-A")
    assert res["status"] == "error"
    assert "chain" in res["error"]
    assert res["bookinger_seneste_doegn"] == sw._MAX_PR_SAMTALE_PR_DOEGN


def test_loftet_taeller_FORBRUGTE_med(monkeypatch):
    """Det er hele pointen — og praecis det `_MAX_PENDING` ikke kunne.

    Nul ventende, tyve forbrugte: den gamle vagt ville slippe det igennem.
    """
    poster = _poster(sw._MAX_PR_SAMTALE_PR_DOEGN, status="consumed")
    assert not [p for p in poster if p["status"] == "pending"]
    monkeypatch.setattr(sw, "_load", lambda: poster)
    monkeypatch.setattr(sw, "_save", lambda r: None)
    res = sw.schedule_self_wakeup(delay_seconds=900, prompt="x", session_id="chat-A")
    assert res["status"] == "error", "forbrugte led ER kaeden"


def test_loftet_er_pr_samtale(monkeypatch):
    """En anden samtale maa ikke blokeres af denne samtales kaede."""
    monkeypatch.setattr(sw, "_load", lambda: _poster(sw._MAX_PR_SAMTALE_PR_DOEGN, sid="chat-A"))
    monkeypatch.setattr(sw, "_save", lambda r: None)
    res = sw.schedule_self_wakeup(delay_seconds=900, prompt="x", session_id="chat-B")
    assert res["status"] == "ok"


def test_poster_aeldre_end_et_doegn_taeller_ikke(monkeypatch):
    """Vinduet ruller. 25 timer gamle led er ikke en aktiv kaede."""
    monkeypatch.setattr(
        sw, "_load",
        lambda: _poster(sw._MAX_PR_SAMTALE_PR_DOEGN * 2, timer_siden=25.0))
    monkeypatch.setattr(sw, "_save", lambda r: None)
    res = sw.schedule_self_wakeup(delay_seconds=900, prompt="x", session_id="chat-A")
    assert res["status"] == "ok"


def test_uden_samtale_blokerer_loftet_ikke(monkeypatch):
    """En vaekning uden session kan ikke tilskrives en kaede — og maa ikke
    rammes af en anden samtales."""
    monkeypatch.setattr(sw, "_load", lambda: _poster(sw._MAX_PR_SAMTALE_PR_DOEGN))
    monkeypatch.setattr(sw, "_save", lambda r: None)
    res = sw.schedule_self_wakeup(delay_seconds=900, prompt="x", session_id=None)
    assert res["status"] == "ok"


def test_svaret_baerer_taellingen_saa_han_ser_den(monkeypatch):
    """Tallet skal staa i SVARET, ikke kun i afvisningen — beslutningen om et
    led mere tages naar han booker, ikke naar loftet rammer."""
    state = _poster(3)
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: None)
    res = sw.schedule_self_wakeup(delay_seconds=900, prompt="x", session_id="chat-A")
    assert res["status"] == "ok"
    assert res["bookinger_seneste_doegn"] == 4, "de tre plus denne"
    assert res["loft_pr_samtale_pr_doegn"] == sw._MAX_PR_SAMTALE_PR_DOEGN


def test_taelleren_ignorerer_uparselige_tidsstempler(monkeypatch):
    """En raekke med skraldet tidsstempel maa hverken taelle med eller kaste."""
    poster = _poster(2) + [{"wakeup_id": "x", "session_id": "chat-A",
                            "status": "consumed", "scheduled_at": "ikke-en-dato"}]
    assert sw.bookinger_seneste_doegn(poster, "chat-A") == 2


def test_vinduet_kan_ankres_saa_vagten_kan_afspilles():
    """Uden et anker svarer en afspilning mod historikken ALTID «nul afvist».

    Posterne nedenfor er 40 dage gamle. Maalt fra nu er de uden for vinduet;
    maalt fra deres egen tid er de en kaede paa tre.
    """
    da = datetime.now(UTC) - timedelta(days=40)
    poster = [{"wakeup_id": f"w{i}", "session_id": "chat-A", "status": "consumed",
               "scheduled_at": (da + timedelta(hours=i)).isoformat()} for i in range(3)]
    assert sw.bookinger_seneste_doegn(poster, "chat-A") == 0
    assert sw.bookinger_seneste_doegn(poster, "chat-A", nu=da + timedelta(hours=3)) == 3


# ── Laasen om lageret (17/10-2026) ─────────────────────────────────────────
#
# Maalt forud for fixet: `wake-cf45dfee74` fandtes 11 gange i `events` —
# scheduled, registreret i indbakken, gatede et vaerktoej — og NUL gange i
# `self_wakeups.json`. Syv skrivesteder gjorde alle `_load()` -> mutér ->
# `_save()`, og hver `_save()` skriver HELE filen. `jarvis-api` og
# `jarvis-runtime` deler den, saa den ene skrev sin gamle liste tilbage over
# den andens. Dispatcheren gjorde vinduet ekstra bredt: den holdt et snapshot
# gennem hele loekken, der starter autonome runs, og gemte til sidst.


def _laase_observatoer(monkeypatch):
    """Registrer om `_load` blev kaldt INDE i laasen."""
    tilstand: dict = {"inde": False, "kald": [], "records": []}

    @contextmanager
    def _fake_laas(_navn):
        tilstand["inde"] = True
        try:
            yield
        finally:
            tilstand["inde"] = False

    monkeypatch.setattr(sw, "med_laas", _fake_laas)
    monkeypatch.setattr(sw, "er_ulaesbar", lambda _navn: False)

    def _load():
        tilstand["kald"].append(tilstand["inde"])
        return list(tilstand["records"])

    monkeypatch.setattr(sw, "_load", _load)
    monkeypatch.setattr(sw, "_save", lambda r: None)
    return tilstand


def test_alle_skrivestier_laeser_inde_i_laasen(monkeypatch):
    """Laasen skal ligge om LAESNINGEN — ikke kun om skrivningen.

    Blev der laest udenfor, ville to processer laese samme liste, og den sidste
    gemning vinde. Det er praecis det tab der blev maalt.
    """
    obs = _laase_observatoer(monkeypatch)
    forfaldne = [{"wakeup_id": "w1", "status": "pending",
                  "fire_at": "2020-01-01T00:00:00+00:00"}]
    tilfaelde = [
        ("schedule", lambda: sw.schedule_self_wakeup(delay_seconds=60, prompt="x"), []),
        ("due", lambda: sw.due_wakeups(), forfaldne),
        ("consumed", lambda: sw.mark_wakeup_consumed("w1"),
         [{"wakeup_id": "w1", "status": "fired"}]),
        ("cancel", lambda: sw.cancel_wakeup("w1"),
         [{"wakeup_id": "w1", "status": "pending"}]),
        ("extra", lambda: sw.add_wakeup_extra("w1", "til"),
         [{"wakeup_id": "w1", "status": "pending"}]),
        ("cleanup", lambda: sw.cleanup_old_wakeups(), []),
        ("marker", lambda: sw.marker_dispatch("w1", dispatched=True),
         [{"wakeup_id": "w1", "status": "fired"}]),
    ]
    for navn, kald, records in tilfaelde:
        obs["records"] = records
        obs["kald"].clear()
        kald()
        assert obs["kald"], f"{navn}: _load blev slet ikke kaldt"
        # Den SIDSTE laesning er den der foeder skrivningen, og den skal ligge
        # inde i laasen. `due_wakeups` maa gerne kigge laasefrit FOERST: det er
        # saadan den undgaar at tage en skrive-laas paa hver prompt-bygning.
        assert obs["kald"][-1] is True, (
            f"{navn}: skrive-laesningen laa UDEN FOR laasen — {obs['kald']}"
        )


def test_to_samtidige_skrivere_taber_ikke_hinanden(monkeypatch, tmp_path):
    """Det oprindelige tab, reproduceret: to skrivere, samme fil.

    Uden laasen laeser begge traade den samme liste, og den sidste gemning
    vinder — den andens post er vaek. Fjernes `med_laas` fra
    `schedule_self_wakeup`, fejler denne test.
    """
    import threading
    import time

    import core.runtime.state_store as ss

    monkeypatch.setattr(ss, "_STATE_DIR", tmp_path)
    ægte_load = sw._load

    def _langsom_load():
        data = ægte_load()
        time.sleep(0.05)  # vinduet hvor den anden traad naar at laese det samme
        return data

    monkeypatch.setattr(sw, "_load", _langsom_load)

    def _book(sid):
        sw.schedule_self_wakeup(delay_seconds=3600, prompt="x", session_id=sid)

    traade = [threading.Thread(target=_book, args=(sid,)) for sid in ("a", "b")]
    for t in traade:
        t.start()
    for t in traade:
        t.join()

    gemt = ss.load_json("self_wakeups", [])
    hjem = sorted(str(r.get("session_id")) for r in gemt)
    assert hjem == ["a", "b"], f"en booking forsvandt i kaploebet: {hjem}"


def test_marker_dispatch_overskriver_ikke_en_post_der_kom_til_imellem(monkeypatch, tmp_path):
    """Det BREDE tab: dispatcheren gemte hele sit snapshot tilbage til sidst."""
    import core.runtime.state_store as ss

    monkeypatch.setattr(ss, "_STATE_DIR", tmp_path)
    ss.save_json("self_wakeups", [{"wakeup_id": "w1", "status": "fired", "prompt": "p"}])
    # Den anden proces booker en post mens dispatcheren arbejder.
    ss.save_json("self_wakeups", ss.load_json("self_wakeups", []) + [
        {"wakeup_id": "w2", "status": "pending", "prompt": "ny"},
    ])

    sw.marker_dispatch("w1", dispatched=True)

    poster = ss.load_json("self_wakeups", [])
    ids = [r.get("wakeup_id") for r in poster]
    assert ids == ["w1", "w2"], f"den anden proces' post blev overskrevet: {ids}"
    assert poster[0]["dispatched"] is True


def test_marker_dispatch_roerer_ikke_en_allerede_lukket_vaekning(monkeypatch, tmp_path):
    """Et dispatch-flag paa en kvitteret vaekning ville modsige
    `consumed_without_dispatch`, som netop findes for at kunne sige
    «naaede aldrig frem»."""
    import core.runtime.state_store as ss

    monkeypatch.setattr(ss, "_STATE_DIR", tmp_path)
    ss.save_json("self_wakeups", [
        {"wakeup_id": "w1", "status": "consumed",
         "consumed_at": "2026-10-17T00:00:00+00:00"},
    ])

    svar = sw.marker_dispatch("w1", dispatched=True)

    assert svar["status"] == "no-op"
    post = ss.load_json("self_wakeups", [])[0]
    assert "dispatched" not in post


def test_korrupt_lager_bliver_ikke_overskrevet_med_en_tom_liste(monkeypatch, tmp_path):
    """`load_json` svarer `[]` for baade «filen mangler» og «filen er korrupt».

    Skrev en skrive-sti den tomme liste tilbage, var posterne vaek — og der stod
    intet i svaret, for der var ingen fejl at se.
    """
    import core.runtime.state_store as ss

    monkeypatch.setattr(ss, "_STATE_DIR", tmp_path)
    raa = "{ ikke json"
    (tmp_path / "self_wakeups.json").write_text(raa, encoding="utf-8")

    svar = sw.schedule_self_wakeup(delay_seconds=60, prompt="x")

    assert svar["status"] == "error"
    assert "kan ikke laeses" in svar["error"]
    assert (tmp_path / "self_wakeups.json").read_text(encoding="utf-8") == raa


def test_er_ulaesbar_skelner_manglende_fra_korrupt(monkeypatch, tmp_path):
    import core.runtime.state_store as ss

    monkeypatch.setattr(ss, "_STATE_DIR", tmp_path)
    assert ss.er_ulaesbar("self_wakeups") is False          # findes ikke
    (tmp_path / "self_wakeups.json").write_text("[]", encoding="utf-8")
    assert ss.er_ulaesbar("self_wakeups") is False          # tom, men gyldig
    (tmp_path / "self_wakeups.json").write_text("{", encoding="utf-8")
    assert ss.er_ulaesbar("self_wakeups") is True           # korrupt
