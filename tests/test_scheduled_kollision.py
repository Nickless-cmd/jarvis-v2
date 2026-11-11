"""En scheduled opgave må ikke starte sit run oveni Bjørns igangværende tur.

MÅLT 30/10-2026 (Bjørn): «dine 2 ture er kollideret og knækket den ende og
leaked ind i den sidste».

BEVISET, fra `chat_messages`:

    id 236638  assistant  chat-00f95aa...  16:43:37  6.447 tegn   ← min tur
    id 236639  assistant  chat-00f95aa...  16:43:43    954 tegn   ← et ANDET run

Begge ligger i SAMME session (code-sessionen «kontektsen kræved en ny
session»), seks sekunder fra hinanden. 236639 er ikke min fortsættelse — det
er scheduled task 152, min egen bookede release-verifikation, der fyrede
16:38:36 og skrev sit runs svar ind i den session Bjørn sad i.

MEKANISMEN. `scheduled_tasks._fire_due_tasks` kalder `pick_wakeup_run_target`
med `record_session=task["session_id"]` — altså den samtale opgaven blev
booket i — og sender derefter `start_autonomous_run` ind i PRÆCIS den session.
Der står ingen aktiv-guard imellem.

Det er ikke en ny fejlklasse: `wakeup_dispatcher.py` fik sin guard 12/9-2026
efter præcis samme måling (wake-d07eaea13d, 26 s efter Bjørn selv skrev), og
den blev udvidet 20/9 og 19/10 med karantæner for hans og min seneste besked.
Scheduled-vejen blev aldrig koblet på. Kommentaren i scheduled_tasks.py siger
endda selv «Samme guard som wakeup_dispatcher bruger (13/6-2026)» — men den
guard, der blev kaldt, var kun KANAL-guarden. Aktiv-guarden manglede.

Testene her kører den ÆGTE `_active_turn_blocks` (kun dens underliggende
lag stubbes), så de fejler hvis scheduled-vejen igen springer den over.
"""

from __future__ import annotations

from datetime import UTC, datetime


def _stub_fyring(monkeypatch, *, app_session: str, levende_run: str = "") -> dict:
    """Kør `_fire_due_tasks()` for ÉN forfalden opgave.

    `levende_run` er det run-id `run_guard.levende_run_i_session` svarer med.
    Er den sat, kører der allerede noget i sessionen — og så må intet nyt run
    startes. Returnerer de kald det autonome run fik (tomt = intet run).
    """
    from core.runtime import db as runtime_db
    from core.services import scheduled_tasks as st

    task = {
        "task_id": "sched-kollision-1",
        "focus": "Verificér releasen",
        "run_at": datetime.now(UTC).isoformat(),
        "status": "pending",
        "scheduled_for_user_id": "",
        "session_id": app_session,
    }
    monkeypatch.setattr(runtime_db, "get_due_scheduled_tasks", lambda *a, **k: [task])
    monkeypatch.setattr(runtime_db, "mark_scheduled_task_fired", lambda *a, **k: None)

    from core.services import routine_trigger_adapters as rta
    monkeypatch.setattr(rta, "routine_cutover_enabled", lambda: False)

    from core.runtime import settings as runtime_settings
    monkeypatch.setattr(
        runtime_settings,
        "load_settings",
        lambda: type("_S", (), {"nudge_system_enabled": True})(),
    )
    from core.services import outbound_nudges
    monkeypatch.setattr(outbound_nudges, "push_nudge", lambda **k: {"nudge_id": "n-1"})

    from core.services import notification_bridge as nb
    monkeypatch.setattr(nb, "delivery_succeeded", lambda r: True)
    monkeypatch.setattr(nb, "send_session_notification", lambda *a, **k: {"status": "ok"})

    from core.services import scheduled_inbox
    monkeypatch.setattr(scheduled_inbox, "registrer_fyret_opgave", lambda **k: {"status": "ok"})

    from core.services import initiative_queue
    monkeypatch.setattr(initiative_queue, "push_initiative", lambda **k: {"status": "ok"})

    from core.services import agent_runtime
    monkeypatch.setattr(agent_runtime, "run_due_agent_schedules", lambda **k: {"triggered_count": 0})

    from core.identity import owner_resolver as orr
    monkeypatch.setattr(orr, "resolve_owner_app_session", lambda: app_session)
    monkeypatch.setattr(orr, "resolve_owner_target_session", lambda: app_session)
    monkeypatch.setattr(
        orr, "session_is_external_channel",
        lambda sid: str(sid or "").startswith(("disc-", "tg-")),
    )

    # KUN det nederste lag stubbes: «kører der et levende run i sessionen?».
    # Selve `_active_turn_blocks` (og dermed karantæne-reglerne) er ÆGTE.
    from core.services import run_guard
    monkeypatch.setattr(
        run_guard, "levende_run_i_session",
        lambda sid: levende_run if str(sid or "") == app_session else "",
    )
    # Karantænerne læser beskeder; i en isoleret test er der ingen at finde.
    from core.services import wakeup_dispatcher as wd
    monkeypatch.setattr(wd, "_bruger_skrev_for_nylig", lambda sid: False)
    monkeypatch.setattr(wd, "_jarvis_skrev_for_nylig", lambda sid: False)

    kald: dict = {}

    # ÉN VÆKKER (11/11-2026): scheduled-vejen starter ikke længere et run selv.
    # Den afleverer til indbakken, og wakeren bærer aktiv-guarden. Spionen skal
    # derfor ramme gatewayen — ellers ser den nul kald, og testen bliver grøn af
    # den forkerte grund (den gamle `_stub_fyring` blev glemt i migrationen).
    from core.services import wake_gateway

    def _anmod(*, kilde=None, sag=None, tekst=None, session_id=None,
               task_id="", origin=None, **k):
        kald["run_session"] = session_id or None
        kald["run_origin"] = origin
        kald["prompt"] = tekst
        kald["kilde"] = kilde
        kald["sag"] = sag
        return {"status": "queued"}

    monkeypatch.setattr(wake_gateway, "anmod_om_vaekning", _anmod)

    st._fire_due_tasks()
    return kald


def test_scheduled_taber_ikke_opgaven_naar_samtalen_er_optaget(isolated_runtime, monkeypatch):
    """Den gamle kontrakt kastede opgaven væk når samtalen var optaget.

    Guarden stod i `scheduled_tasks.py` og betød «er samtalen optaget, dispatcher
    vi INTET» — posten lå så i indbakken, men runnet blev aldrig startet for den.
    Nu afleveres posten og wakeren udskyder den til samtalen er ledig. Det der
    måles her er derfor at opgaven IKKE forsvinder.
    """
    kald = _stub_fyring(
        monkeypatch, app_session="chat-optaget-1", levende_run="run-abc123",
    )
    assert kald.get("run_session") == "chat-optaget-1", (
        "scheduled-vejen afleverede ikke opgaven til den bundne samtale — en "
        f"optaget samtale må udskyde, ikke tabe: {kald}"
    )
    assert kald.get("run_origin") == "scheduled"
    assert kald.get("kilde") == "scheduled"


def test_scheduled_run_startes_naar_sessionen_er_ledig(isolated_runtime, monkeypatch):
    """Modstykket: uden et levende run skal opgaven dispatch'es som før.

    Uden denne ville «start aldrig» også gøre testen ovenfor grøn — og det
    ville være den samme tavse virkningsløshed som fejlen selv.
    """
    kald = _stub_fyring(monkeypatch, app_session="chat-ledig-1", levende_run="")
    assert kald.get("run_session") == "chat-ledig-1"
    assert kald.get("run_origin") == "scheduled"


def test_aktiv_guarden_har_praecis_en_implementering_og_ligger_paa_vaekningsvejen():
    """Guarden er FLYTTET, ikke fjernet (11/11-2026).

    Den lå før i `scheduled_tasks.py` med kontrakten «er samtalen optaget,
    dispatcher vi INTET» — og konsekvensen var et TABT run. Wakeren bærer den
    nu, så posten venter i stedet for at forsvinde. Det der stadig skal værnes
    om er at der findes ÉN implementering: to kopier ville drive fra hinanden,
    og så ville den ene stille holde op med at virke — præcis hvad der skete her.
    """
    import pathlib

    waker = pathlib.Path("core/services/inbox_idle_waker.py").read_text(encoding="utf-8")
    assert "_active_turn_blocks" in waker, (
        "wakeren tjekker ikke den fælles aktiv-guard — så kan et scheduled run "
        "igen lande oveni Bjørns igangværende tur"
    )

    for navn in ("scheduled_tasks.py", "recurring_tasks.py"):
        kilde = pathlib.Path(f"core/services/{navn}").read_text(encoding="utf-8")
        # Kun kode-linjer: en omtale i en kommentar er ikke et kald.
        kode = "\n".join(
            linje for linje in kilde.splitlines()
            if not linje.lstrip().startswith("#")
        )
        assert "def _active_turn_blocks" not in kode, (
            f"{navn} har lavet sin EGEN kopi af aktiv-guarden — brug "
            "wakeup_dispatcher._active_turn_blocks, så de to ikke driver fra hinanden"
        )
        assert "start_autonomous_run(" not in kode, (
            f"{navn} starter stadig et run direkte — kilden skal signalere til "
            "indbakken, så wakeren kan bære guarden"
        )
