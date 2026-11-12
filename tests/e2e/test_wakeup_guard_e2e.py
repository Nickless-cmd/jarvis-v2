"""FULD e2e: vækningskæden gennem den ÆGTE job-kø — den NUVÆRENDE arkitektur.

Omskrevet 12/11-2026. Denne fil beskrev indtil da en kæde der blev erstattet:

    GAMMEL: dispatcher → _active_turn_blocks → skip('user_active')
                                     ELLER start_autonomous_stream_run()
    NY:     dispatcher → wake_gateway.anmod_om_vaekning() → indbakken
                     → inbox_idle_waker → start_autonomous_run()

`autonomous_stream_run` er pensioneret (nul produktionsimports, se dens
docstring), og guarden bor nu i wakeren — `test_wakeup_dispatcher.py` siger det
selv i sin docstring. De ni gamle tests pegede derfor på en funktion der ikke
længere kaldes, og fejlede med `spy.started is False` uanset hvad kæden gjorde.
En test-double der peger på en pensioneret vej måler ingenting.

Hvad der BEVARES her, fordi det ikke dækkes andre steder: koblingen gennem den
ægte job-kø, og at `task_id` + `extra` faktisk følger vækningen HELT ind i
runnet. `test_wake_gateway.py` dækker task_id ind i gatewayen, men ingen test
dækkede springet fra indbakke-post til run — og det er præcis det spring en
migrering kan tabe uden at nogen ser det.

Guarden selv ligger nu hvor den ligger: `test_wakeup_aktiv_samtale_guard.py`
(levende run, karantæne, 10-minutters vinduet, ulæselig log),
`test_inbox_idle_waker.py` (vækkeren) og `test_wakeup_skip_til_indbak.py`
(modenhed — en væknings post oprettes ved BOOKINGEN, ikke ved fyringen).

Alt er ægte: job-køen, registret, handleren, dispatcheren, gatewayen,
indbakken, vækkeren og modenheden. Kun fire ting er isoleret, fordi de ellers
rører verden uden for testen:

  * wakeup-lageret → in-memory, så produktionsdata ikke forurenes
  * job-køen → tmp-fil
  * indbakken → tmp-sqlite
  * selve LLM-kørslen → stubbet, fordi et rigtigt run koster penge og starter
    en agent i produktion

Det sidste er den ærlige grænse: alt FØR LLM-kaldet er e2e; selve kaldet er
stubbet og verificeret på argumentet (hvilken session, hvilken tekst, hvilket
opgave-id).
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

import core.services.jobs_engine as je
import core.services.self_wakeup as sw
from core.runtime import db_inbox


# ── fixtures ────────────────────────────────────────────────────────────────


class _RunSpy:
    """Fanger om/hvordan det autonome run blev startet (den stubbede kant).

    Signaturen SKAL følge produktionens. Målt 16/10-2026: spionen manglede
    `task_id` mens signaturen havde haft den i to dage, kaldet fejlede med
    `unexpected keyword argument`, fejlen blev slugt i kalderens
    `except Exception`, og fire tests så ud som om runnet aldrig startede.
    Test-doublen var forældet — ikke kæden. Derfor bæres alle felterne med.
    """

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(self, message: str, **kw: Any) -> None:
        self.calls.append({"message": message, **kw})

    @property
    def started(self) -> bool:
        return bool(self.calls)


@pytest.fixture
def e2e(monkeypatch, tmp_path):
    """Ægte kæde; kun lager, kø, indbakke og den ydre LLM-kant isoleret."""
    import types

    # 1. Wakeup-lager → in-memory
    store: dict[str, list] = {"records": []}
    monkeypatch.setattr(sw, "load_json", lambda key, default=None: list(store["records"]))
    monkeypatch.setattr(
        sw, "save_json", lambda key, value: store.__setitem__("records", list(value))
    )

    # 2. Job-kø → tmp-fil (så produktionskøen ikke forurenes)
    qpath = Path(tmp_path) / "jobs_queue.json"
    monkeypatch.setattr(je, "_storage_path", lambda: qpath)
    je._LOAD_CACHE_KEY = None
    je._LOAD_CACHE_ITEMS = None

    # 3. Indbakken → tmp-sqlite. Samme mønster som test_inbox_idle_waker.
    sti = Path(tmp_path) / "e2e_inbox.db"

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

    # 4. Registrér de ÆGTE handlers (samme vej som bootstrap gør ved opstart)
    from core.services.governance_bootstrap import ensure_default_job_handlers

    ensure_default_job_handlers()

    # 5. Ydre I/O: nudge, heartbeat, desktop-notifikation → no-op
    monkeypatch.setattr(
        "core.runtime.settings.load_settings",
        lambda: types.SimpleNamespace(nudge_system_enabled=False),
    )
    monkeypatch.setattr(
        "core.services.notification_bridge.send_session_notification", lambda *a, **k: None
    )
    monkeypatch.setattr("core.services.heartbeat_phases.tick_with_phases", lambda *a, **k: None)

    # 6. Den stubbede kant: selve LLM-kørslen — peget på den LEVENDE vej.
    spy = _RunSpy()
    monkeypatch.setattr(
        "core.services.visible_autonomous_run.start_autonomous_run", spy
    )

    # 7. «Kører der noget?» → nej, medmindre testen siger andet. Det er en
    #    cross-process-vagt der ellers læser produktions-DB'en.
    monkeypatch.setattr(
        "core.services.inbox_idle_waker._noget_koerer", lambda: False
    )

    yield types.SimpleNamespace(
        store=store, spy=spy, queue=qpath, inbox_db=sti, monkeypatch=monkeypatch
    )


# ── helpers ─────────────────────────────────────────────────────────────────


def _plant_wakeup(store, *, wid="wake-e2e", session_id="chat-e2e", **over) -> dict[str, Any]:
    """Læg en FORFALDEN wakeup i lageret — samme form som schedule_self_wakeup."""
    past = (datetime.now(UTC) - timedelta(seconds=5)).isoformat()
    rec = {
        "wakeup_id": wid,
        "scheduled_at": past,
        "fire_at": past,          # allerede forfalden → due_wakeups samler den op
        "delay_seconds": 60,
        "prompt": "TJEK: e2e-verifikation",
        "reason": "e2e",
        "extra": None,
        "status": "pending",
        "fired_at": None,
        "consumed_at": None,
        "channel": "app",
        "session_id": session_id,
        "user_id": "1246415163603816499",
        "workspace_name": "bjorn",
        "user_display_name": "Bjørn",
        "role": None,
        "context_channel": "webchat",
    }
    rec.update(over)
    store["records"].append(rec)
    return rec


def _drain_queue() -> list[Any]:
    """Dræn køen præcis som heartbeat_runtime gør — gennem det ægte run_next_job."""
    out = []
    for _ in range(5):
        res = je.run_next_job()
        if res is None:
            break
        out.append(res)
    return out


def _record(store, wid="wake-e2e") -> dict[str, Any]:
    return next(r for r in store["records"] if r.get("wakeup_id") == wid)


def _post_efter_dispatch(wid="wake-e2e") -> dict[str, Any] | None:
    """Find indbakke-posten gatewayen skrev for vækningen.

    Læses direkte fra den isolerede DB uden bruger-filter. `wake_gateway`
    NORMALISERER brugeren (`normaliser_indbakke_bruger`), så posten kan ligge
    under et andet id end vækningens eget — og et gæt på id'et gjorde tre tests
    røde af en grund der intet havde med kæden at gøre.
    """
    from core.services.wake_gateway import _WAKEUP_SAG_PRAEFIKS, vaekning_kilde_id

    # Postens nøgle er `vaek-<sag>`, og en vækning melder sig under sagen
    # "wakeup:<id>" (se `_WAKEUP_SAG_PRAEFIKS`). Målt 12/11-2026: et gæt på
    # formatet ("vaek-" + wakeup_id) gav tre røde tests af en grund der intet
    # havde med kæden at gøre — posten lå der hele tiden under den rigtige nøgle.
    kilde_id = vaekning_kilde_id(f"{_WAKEUP_SAG_PRAEFIKS}{wid}")
    with db_inbox.connect() as conn:
        row = conn.execute(
            "SELECT * FROM inbox_items WHERE kilde_id = ? ORDER BY rowid DESC LIMIT 1",
            (kilde_id,),
        ).fetchone()
    return dict(row) if row is not None else None


# ── tests ───────────────────────────────────────────────────────────────────


def test_e2e_queue_is_really_used(e2e):
    """Bevis at køen faktisk er en del af kæden — ikke bare kaldes forbi."""
    je.enqueue_job(job_type="wakeup_dispatch", payload={"reason": "e2e"}, priority=8)
    assert e2e.queue.exists(), "job-køen skal ligge i det isolerede lager"
    data = json.loads(e2e.queue.read_text())
    assert any(j.get("job_type") == "wakeup_dispatch" for j in data)

    results = _drain_queue()
    assert len(results) == 1
    after = json.loads(e2e.queue.read_text())
    done = [j for j in after if j.get("job_type") == "wakeup_dispatch"]
    assert done and done[-1].get("status") == "ok"


def test_e2e_dispatcher_laegger_i_indbakken_ikke_i_runnet(e2e):
    """Dispatcheren STARTER intet. Den afleverer til indbakken — det er hele
    pointen med gatewayen: kun vækkeren må starte et run, og kun når intet kører.
    """
    _plant_wakeup(e2e.store, session_id="chat-e2e")

    je.enqueue_job(job_type="wakeup_dispatch", payload={"reason": "e2e"}, priority=8)
    results = _drain_queue()

    assert [r.job_type for r in results] == ["wakeup_dispatch"]
    assert results[0].status == "ok"
    assert e2e.spy.started is False, "dispatcheren må ikke starte et run selv"

    post = _post_efter_dispatch()
    assert post is not None, "vækningen skal ligge i indbakken efter dispatch"
    assert post["session_id"] == "chat-e2e"


def test_e2e_task_id_og_extra_naar_runnet_gennem_hele_kaeden(e2e):
    """SPRINGET der kan tabe data: indbakke-post → run.

    `test_wake_gateway.py` beviser at `task_id` når gatewayen, men ingen test
    dækkede at det også kommer videre fra posten og ind i runnet — eller at
    Bjørns `extra` gør. Det er to felter der bærer henholdsvis hvilken
    forpligtelse vækningen fortsætter, og hans egen tilføjelse; tabes de, ved
    runnet ikke hvad det fortsætter i stedet for at gætte.
    """
    from core.services import inbox_idle_waker as waker

    _plant_wakeup(
        e2e.store, session_id="chat-e2e",
        task_id="opg-e2e", extra="husk også X",
    )

    # 1. Gennem den ægte job-kø: vækningen afleveres til indbakken.
    je.enqueue_job(job_type="wakeup_dispatch", payload={"reason": "e2e"}, priority=8)
    _drain_queue()

    post = _post_efter_dispatch()
    assert post is not None, "vækningen skal ligge i indbakken"

    # 2. Vækkeren — den ENESTE der må starte runnet.
    e2e.monkeypatch.setattr(
        "core.services.inbox_idle_waker._session_er_aktiv", lambda _s: False
    )
    udfald = waker.vaek_paa_aabne_poster(bruger_id="1246415163603816499")
    assert udfald.get("vaekket") == 1, f"vækkeren skulle starte præcis ét run: {udfald}"

    assert e2e.spy.started is True, "runnet skal være startet ad den levende vej"
    kald = e2e.spy.calls[0]
    assert kald["task_id"] == "opg-e2e", (
        "opgavens id skal følge vækningen HELT ind i runnet — ellers ved "
        "starteren ikke hvad den fortsætter i stedet for at gætte"
    )
    assert kald["session_id"] == "chat-e2e"
    assert "Tilføjelse: husk også X" in kald["message"], (
        "Bjørns egen tilføjelse skal med ind i direktivet"
    )


def test_e2e_uden_task_id_sender_TOM_streng(e2e):
    """En vækning uden opgave-id sender `""` — ikke `None`, ikke et gæt."""
    from core.services import inbox_idle_waker as waker

    _plant_wakeup(e2e.store, session_id="chat-e2e")   # ingen task_id

    je.enqueue_job(job_type="wakeup_dispatch", payload={"reason": "e2e"}, priority=8)
    _drain_queue()

    e2e.monkeypatch.setattr(
        "core.services.inbox_idle_waker._session_er_aktiv", lambda _s: False
    )
    waker.vaek_paa_aabne_poster(bruger_id="1246415163603816499")

    assert e2e.spy.started is True
    assert e2e.spy.calls[0]["task_id"] == ""


def test_e2e_aktiv_samtale_holder_posten_tilbage(e2e):
    """En aktiv samtale må hverken afbrydes eller få posten brændt af.

    Guarden bor i vækkeren nu (`_session_er_aktiv`), ikke i dispatcheren.
    Kernen er den samme som før: mens Bjørn skriver, starter der intet
    konkurrerende run — og posten bliver liggende, ikke tabt.
    """
    from core.services import inbox_idle_waker as waker

    _plant_wakeup(e2e.store, session_id="chat-e2e")

    je.enqueue_job(job_type="wakeup_dispatch", payload={"reason": "e2e"}, priority=8)
    _drain_queue()
    assert _post_efter_dispatch() is not None

    e2e.monkeypatch.setattr(
        "core.services.inbox_idle_waker._session_er_aktiv", lambda _s: True
    )
    udfald = waker.vaek_paa_aabne_poster(bruger_id="1246415163603816499")

    assert e2e.spy.started is False, "← kernen: intet konkurrerende run"
    assert udfald.get("vaekket", 0) == 0
    post = _post_efter_dispatch()
    assert post is not None, "posten må ikke forsvinde — den skal vente, ikke tabes"


def test_e2e_consumed_before_tick_leaves_trace(e2e):
    """Sidste stille kant, ende til ende gennem den ÆGTE job-kø.

    Sekvensen er den produktionsægte: wakeup'en forfalder og awareness-vejen
    flipper den pending→fired når Jarvis får en tur; han kvitterer den; og
    FØRST DEREFTER kommer dispatcher-tick'en. Dispatcheren filtrerer på
    status=='fired', så den ser intet — men recorden skal bære sporet.

    Denne test overlevede omskrivningen: den måler self_wakeups eget lager og
    awareness-vejen, ikke hvilken starter dispatcheren kalder.
    """
    _plant_wakeup(e2e.store, session_id="chat-e2e")

    # Awareness-vejen (samme kald prompt-contract bruger) flipper pending→fired
    section = sw.self_wakeup_section()
    assert section is not None
    assert _record(e2e.store)["status"] == "fired"

    # ... og han kvitterer FØR dispatcheren når sit næste tick
    assert sw.mark_wakeup_consumed("wake-e2e")["status"] == "ok"

    # Nu kommer tick'en — gennem den ægte kø
    je.enqueue_job(job_type="wakeup_dispatch", payload={"reason": "e2e"}, priority=8)
    _drain_queue()

    rec = _record(e2e.store)
    assert rec["status"] == "consumed"
    assert e2e.spy.started is False
    assert rec.get("dispatched") is None
    assert rec.get("dispatch_skipped") is None       # dispatcheren så den aldrig
    assert rec["consumed_without_dispatch"] is True  # ... men sporet står der
    assert rec["consumed_without_dispatch_reason"] == "consumed_before_dispatch_tick"
