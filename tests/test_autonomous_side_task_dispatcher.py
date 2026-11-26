from datetime import UTC, datetime, timedelta

import pytest

from core.services import autonomous_side_task_dispatcher as dispatcher
from core.services import side_tasks


@pytest.fixture(autouse=True)
def _budget(monkeypatch):
    monkeypatch.setattr(dispatcher, "_daily_budget_allows", lambda: True)
    monkeypatch.setattr(dispatcher, "_note_daily_start", lambda _task_id: None)


def _state(monkeypatch):
    rows = []
    monkeypatch.setattr(side_tasks, "load_json", lambda _key, _default: list(rows))
    monkeypatch.setattr(
        side_tasks, "save_json", lambda _key, value: rows.__setitem__(slice(None), value),
    )
    return rows


def test_plain_side_task_is_never_claimed(monkeypatch):
    _state(monkeypatch)
    side_tasks.flag(title="Manuel", prompt="Vent på Bjørn")
    assert side_tasks.claim_autonomous(worker_id="worker-1") is None


def test_explicit_inspection_task_can_be_claimed_once(monkeypatch):
    rows = _state(monkeypatch)
    task_id = side_tasks.flag(
        title="Undersøg", prompt="Find årsagen", autonomy_mode="inspect",
    )["side_task_id"]

    claimed = side_tasks.claim_autonomous(worker_id="worker-1")

    assert claimed is not None and claimed["side_task_id"] == task_id
    assert claimed["status"] == "activated"
    assert claimed["autonomy_lease_owner"] == "worker-1"
    assert side_tasks.claim_autonomous(worker_id="worker-2") is None
    assert rows[0]["autonomy_attempts"] == 1


def test_expired_lease_can_be_reclaimed(monkeypatch):
    rows = _state(monkeypatch)
    side_tasks.flag(title="Undersøg", prompt="Find årsagen", autonomy_mode="inspect")
    first = side_tasks.claim_autonomous(worker_id="worker-1", lease_minutes=1)
    rows[0]["autonomy_lease_until"] = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()

    second = side_tasks.claim_autonomous(worker_id="worker-2", lease_minutes=1)

    assert first and second
    assert second["autonomy_lease_owner"] == "worker-2"
    assert rows[0]["autonomy_attempts"] == 2


def test_three_expired_attempts_are_escalated_once(monkeypatch):
    rows = _state(monkeypatch)
    side_tasks.flag(title="Undersøg", prompt="Find årsagen", autonomy_mode="inspect")
    rows[0].update({
        "status": "activated",
        "autonomy_attempts": 3,
        "autonomy_lease_owner": "old-worker",
        "autonomy_lease_until": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
    })
    reported = []
    monkeypatch.setattr(
        "core.services.background_attention.report_background_outcome",
        lambda **kwargs: reported.append(kwargs) or {"inbox": "ok"},
    )

    dispatcher._report_exhausted()
    dispatcher._report_exhausted()

    assert len(reported) == 1
    assert rows[0].get("autonomy_exhausted_reported_at")


def test_dispatcher_starts_one_task_only_when_idle(monkeypatch):
    _state(monkeypatch)
    side_tasks.flag(title="A", prompt="Undersøg A", autonomy_mode="inspect")
    side_tasks.flag(title="B", prompt="Undersøg B", autonomy_mode="inspect")
    monkeypatch.setattr(dispatcher, "_idle_long_enough", lambda: True)
    monkeypatch.setattr(dispatcher, "_something_running", lambda: False)
    monkeypatch.setattr(dispatcher, "_target_session", lambda: "chat-1")
    started = []
    monkeypatch.setattr(
        dispatcher, "_start",
        lambda text, **kwargs: started.append((text, kwargs)) or True,
    )

    result = dispatcher.dispatch_one()

    assert result["started"] == 1
    assert len(started) == 1
    assert started[0][1]["origin"] == "side-task-inspect"
    assert "STOPREGLER" in started[0][0]


def test_dispatch_callbacks_own_running_and_exit_state(monkeypatch):
    rows = _state(monkeypatch)
    task_id = side_tasks.flag(
        title="A", prompt="Undersøg A", autonomy_mode="inspect",
    )["side_task_id"]
    _klar_til_start(monkeypatch)
    monkeypatch.setattr(dispatcher, "_target_session", lambda: "chat-1")

    def fake_start(_text, **kwargs):
        kwargs["started_callback"](visible_run_id="run-1", session_id="chat-1")
        assert rows[0]["status"] == "running"
        assert rows[0]["arbejds_run_id"] == "run-1"
        kwargs["completion_callback"](
            outcome="failed", visible_run_id="run-1", session_id="chat-1",
            error="timeout",
        )
        return True

    monkeypatch.setattr(dispatcher, "_start", fake_start)
    assert dispatcher.dispatch_one()["side_task_id"] == task_id
    assert rows[0]["status"] == "failed"
    assert rows[0]["state_reason"].endswith("timeout")


def test_rejected_start_releases_claim(monkeypatch):
    rows = _state(monkeypatch)
    side_tasks.flag(title="A", prompt="Undersøg A", autonomy_mode="inspect")
    monkeypatch.setattr(dispatcher, "_idle_long_enough", lambda: True)
    monkeypatch.setattr(dispatcher, "_something_running", lambda: False)
    monkeypatch.setattr(dispatcher, "_target_session", lambda: "chat-1")
    monkeypatch.setattr(dispatcher, "_start", lambda text, **kwargs: False)

    result = dispatcher.dispatch_one()

    assert result["started"] == 0
    assert rows[0]["status"] == "queued"
    assert not rows[0].get("autonomy_lease_owner")


def test_runtime_budget_stops_tools_after_ceiling(monkeypatch):
    from core.services import run_autonomy_context as context

    token = context.set_autonomous(True)
    context.set_run_identity("run-budget", "side-task-inspect")
    context.set_autonomous_budget(max_tool_calls=2, max_seconds=60)
    try:
        assert context.consume_autonomous_tool_budget() is True
        assert context.consume_autonomous_tool_budget() is True
        assert context.consume_autonomous_tool_budget() is False
        assert context.autonomous_budget_state()["tool_calls_used"] == 2
    finally:
        context.set_run_identity("", "")
        context.reset_autonomous(token)


# ── Hvor lander et autonomt side-opgave-run? (25/10-2026) ────────────────────
#
# MÅLT 25/10-2026: `dispatch_one` bestemte sessionen med `_target_session()`
# FØR den claimede opgaven. Den kunne derfor per konstruktion ikke svare på
# «hvor hører DETTE arbejde til» — kun «hvad er ejerens app-samtale». Målt i
# drift pegede den på Bjørns aktive samtale, så et autonomt run ville skrive
# sig ind midt i en igangværende snak. De tre andre vække-veje bruger alle
# `pick_wakeup_run_target` med rækkefølgen: opgavens egen samtale → ejerens
# app-samtale → tom ⇒ ingen start. Dispatcheren manglede hele rækkefølgen.

def _klar_til_start(monkeypatch):
    monkeypatch.setattr(dispatcher, "_idle_long_enough", lambda: True)
    monkeypatch.setattr(dispatcher, "_something_running", lambda: False)


def test_runnet_lander_i_baggrundssiloen_ikke_i_opgavens_samtale(monkeypatch):
    """26/11-2026: opgavens EGEN samtale er ikke laengere en gyldig adresse.

    Foer vandt `chat-hvor-opgaven-hoerer-til` over ejerens aktive samtale.
    Bjorn strammede reglen: chat mode maa kun vaekkes af rutiner og wakeups,
    saa en side-opgave hoerer til i baggrunden uanset hvilken samtale den blev
    flagget i (527 af 677 baerer selv en `chat-*`-adresse, maalt 26/11-2026).
    """
    _state(monkeypatch)
    side_tasks.flag(
        title="Undersøg", prompt="Find årsagen", autonomy_mode="inspect",
        session_id="chat-hvor-opgaven-hoerer-til",
    )
    _klar_til_start(monkeypatch)
    monkeypatch.setattr(dispatcher, "_target_session", lambda: "chat-bjoerns-aktive")
    started = []
    monkeypatch.setattr(
        dispatcher, "_start",
        lambda text, **kwargs: started.append(kwargs) or True,
    )

    result = dispatcher.dispatch_one()

    assert result["started"] == 1, "opgaven skal KOERE, bare ikke i samtalen"
    assert not started[0]["session_id"].startswith("chat-"), (
        "side-opgaven landede i en samtale — praecis det Bjorn forbod"
    )
    assert started[0]["session_id"].startswith("auto-side-task-")


def test_uden_egen_samtale_gaar_den_til_baggrundssiloen(monkeypatch):
    """Ingen egen adresse ⇒ baggrunden, ikke ejerens aktive samtale."""
    _state(monkeypatch)
    side_tasks.flag(title="Undersøg", prompt="Find årsagen", autonomy_mode="inspect")
    _klar_til_start(monkeypatch)
    monkeypatch.setattr(dispatcher, "_target_session", lambda: "chat-senest-aktiv")
    started = []
    monkeypatch.setattr(
        dispatcher, "_start",
        lambda text, **kwargs: started.append(kwargs) or True,
    )

    result = dispatcher.dispatch_one()

    assert result["started"] == 1
    assert not started[0]["session_id"].startswith("chat-")
    assert started[0]["session_id"].startswith("auto-side-task-")


def test_ingen_samtale_starter_i_baggrundssiloen(monkeypatch):
    """Tom adresse ⇒ baggrundssilo. FOER: «ingen start, bliv i koeen».

    Den gamle kontrakt var `no-session` + frigivet claim. Den betoed at en
    opgave uden en samtale aldrig blev koert — og efter 26/11 ville det ramme
    78 % af alle side-opgaver. En side-opgave har altid et sted at koere.
    """
    rows = _state(monkeypatch)
    side_tasks.flag(title="Undersøg", prompt="Find årsagen", autonomy_mode="inspect")
    _klar_til_start(monkeypatch)
    monkeypatch.setattr(dispatcher, "_target_session", lambda: "")
    started = []
    monkeypatch.setattr(
        dispatcher, "_start",
        lambda text, **kwargs: started.append(kwargs) or True,
    )

    result = dispatcher.dispatch_one()

    assert result["started"] == 1
    assert started[0]["session_id"].startswith("auto-side-task-")
    assert rows[0]["status"] == "running"


def test_en_ekstern_kanal_bruges_ikke_som_adresse(monkeypatch):
    """Discord/Telegram maa hverken vaere adresse eller laanes som fallback.

    Bevaret fra 28/10-2026: `pick_wakeup_run_target` afviser eksterne kanaler.
    Opgaven lander derfor i baggrunden — den venter ikke og den gaar ikke til
    en kanal Bjorn ikke sidder i.
    """
    _state(monkeypatch)
    side_tasks.flag(
        title="Undersøg", prompt="Find årsagen", autonomy_mode="inspect",
        session_id="disc-origin",
    )
    _klar_til_start(monkeypatch)
    monkeypatch.setattr(dispatcher, "_target_session", lambda: "chat-tilfaeldig")
    monkeypatch.setattr(
        "core.identity.owner_resolver.session_is_external_channel",
        lambda sid: str(sid).startswith("disc-"),
    )
    started = []
    monkeypatch.setattr(
        dispatcher, "_start",
        lambda text, **kwargs: started.append(kwargs) or True,
    )

    result = dispatcher.dispatch_one()

    assert result["started"] == 1
    assert not started[0]["session_id"].startswith("disc-")
    assert not started[0]["session_id"].startswith("chat-")
    assert started[0]["session_id"].startswith("auto-side-task-")
