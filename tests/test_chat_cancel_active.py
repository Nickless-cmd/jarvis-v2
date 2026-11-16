"""Stop-knappen skal ramme SAMTALENS run — ikke den globalt seneste.

Målt 16/11-2026: `POST /chat/sessions/{id}/cancel-active` læste
`visible_runs.active_run`, som er ÉN global nøgle uden session-suffiks.
`register_visible_run` overskriver den, så et run i en anden samtale der
registrerede sig sidst gjorde dit eget run usynligt for knappen: stop svarede
`cancelled: false` mens dit run kørte videre.

Det er fail-safe (den dræbte aldrig et fremmed run, fordi den sammenlignede
`session_id`), men fail-wrong: den kunne ikke stoppe det rigtige.

Opslaget findes allerede per session: `live_run_for_session` i
`core.services.run_stream_locator`, brugt af `/sessions/{id}/live`.
"""
from __future__ import annotations

import pytest

from core.services import run_event_log as rel


@pytest.fixture(autouse=True)
def _isolerede_runs(monkeypatch):
    """Run-loggen er proces-global — ryd den, så en nabo i fuld suite ikke lækker ind."""
    rel._RUNS.clear()
    rel._ALIASER.clear()
    rel._ALIASER_OMVENDT.clear()
    from apps.api.jarvis_api.routes import chat

    monkeypatch.setattr(chat, "_kraev_adgang", lambda _sid: None)
    # Stop-settlement skriver til DB; dens egen adfærd har sine tests.
    monkeypatch.setattr(chat, "_settle_user_stop", lambda _rid, _sid="": None)
    yield
    rel._RUNS.clear()


def test_stop_rammer_samtalens_eget_run_ikke_det_globalt_seneste(monkeypatch):
    """Regressionen: B registrerede sig sidst, så den globale slot pegede på B.

    Den gamle kode sammenlignede slottens `session_id` med A og svarede
    `cancelled: false`. A's run kørte videre, usynligt for knappen.
    """
    from apps.api.jarvis_api.routes import chat
    from core.services import visible_runs

    rel.create("run-a", "session-a")
    rel.create("run-b", "session-b")

    # Den globale slot bærer B — præcis den tilstand der brød A.
    monkeypatch.setattr(
        visible_runs,
        "_get_active_visible_run_state",
        lambda: {"session_id": "session-b", "run_id": "run-b"},
    )

    ramte: list[str] = []
    monkeypatch.setattr(
        chat, "cancel_visible_run", lambda rid: ramte.append(rid) or True
    )

    ud = chat.chat_cancel_active("session-a")

    assert ud["cancelled"] is True
    assert ud["run_id"] == "run-a"
    assert ud["run_ids"] == ["run-a"]
    # B må ikke være rørt: den kører i en anden samtale.
    assert ramte == ["run-a"]


def test_den_anden_samtales_run_bliver_ikke_draebt(monkeypatch):
    """Samme tilstand, modsat vinkel: stop i B må ikke ramme A.

    `run-b` oprettes FØRST med vilje, så «globalt seneste» ville pege på A —
    ellers kunne testen bestå ved tilfælde.
    """
    from apps.api.jarvis_api.routes import chat
    from core.services import visible_runs

    rel.create("run-b", "session-b")
    rel.create("run-a", "session-a")
    monkeypatch.setattr(
        visible_runs,
        "_get_active_visible_run_state",
        lambda: {"session_id": "session-a", "run_id": "run-a"},
    )

    ramte: list[str] = []
    monkeypatch.setattr(
        chat, "cancel_visible_run", lambda rid: ramte.append(rid) or True
    )

    ud = chat.chat_cancel_active("session-b")

    assert ud["cancelled"] is True
    assert ud["run_id"] == "run-b"
    assert ud["run_ids"] == ["run-b"]
    assert ramte == ["run-b"]


def test_uden_levende_run_svarer_den_ikke_cancelled(monkeypatch):
    from apps.api.jarvis_api.routes import chat

    monkeypatch.setattr(
        chat,
        "cancel_visible_run",
        lambda _rid: pytest.fail("cancel_visible_run må ikke kaldes uden et levende run"),
    )

    assert chat.chat_cancel_active("session-uden-run") == {"cancelled": False}


def test_et_afsluttet_run_kan_ikke_stoppes(monkeypatch):
    """Et færdigt run er ikke et stop-mål — knappen skal ikke rapportere succes."""
    from apps.api.jarvis_api.routes import chat

    rel.create("run-faerdig", "session-x")
    rel.mark_done("run-faerdig")

    monkeypatch.setattr(
        chat,
        "cancel_visible_run",
        lambda _rid: pytest.fail("et terminalt run må ikke kaldes for cancel"),
    )

    assert chat.chat_cancel_active("session-x") == {"cancelled": False}


def test_to_runs_i_samme_samtale_stopper_begge(monkeypatch):
    """En stop-knap i samtalen stopper SAMTALENS arbejde — ikke kun det nyeste.

    16/11-2026: `live_run_for_session` returnerer `candidates[-1]`, så et
    samtidigt run i samme session (fx en vækning mens brugeren selv sender)
    blev efterladt kørende. Brugeren trykkede stop og så arbejdet fortsætte.
    Det er ikke «det jeg ser» — det er halvt arbejde tilbage.
    """
    from apps.api.jarvis_api.routes import chat

    rel.create("run-aeldre", "session-y")
    rel.create("run-nyeste", "session-y")

    ramte: list[str] = []
    monkeypatch.setattr(
        chat, "cancel_visible_run", lambda rid: ramte.append(rid) or True
    )

    ud = chat.chat_cancel_active("session-y")

    assert sorted(ramte) == ["run-aeldre", "run-nyeste"]
    assert ud["cancelled"] is True
    # Bagudkompatibilitet: `run_id` er stadig den nyeste, som før.
    assert ud["run_id"] == "run-nyeste"


def test_stop_alle_rammer_ikke_en_anden_samtale(monkeypatch):
    """«Alle» betyder alle i DENNE samtale — ikke alle i processen."""
    from apps.api.jarvis_api.routes import chat

    rel.create("run-y1", "session-y")
    rel.create("run-y2", "session-y")
    rel.create("run-fremmed", "session-z")

    ramte: list[str] = []
    monkeypatch.setattr(
        chat, "cancel_visible_run", lambda rid: ramte.append(rid) or True
    )

    chat.chat_cancel_active("session-y")

    assert sorted(ramte) == ["run-y1", "run-y2"]
    assert "run-fremmed" not in ramte


def test_run_ejet_af_den_anden_proces_kan_stoppes(monkeypatch):
    """Den ægte cross-process-vej — målt 16/11-2026, ikke antaget.

    `run_event_log` er in-memory PR. PROCES. Et run startet af jarvis-runtime
    (en vækning) findes derfor IKKE i API-processens log; det findes kun i
    `in_flight_runs` (state/in_flight_runs.json under flock) og i
    `visible_runs.control.<run_id>` i runtime-state.

    Testen registrerer runnet ad PRÆCIS den vej runtime bruger — `mark_started`
    plus control-state — og kræver at endpointet finder og annullerer det.
    Uden `active_locations`-grenen i endpointet ville opslaget svare «intet run».
    """
    from apps.api.jarvis_api.routes import chat
    from core.services import in_flight_runs as ifr
    from core.services.visible_runs import (
        _get_visible_run_control,
        _set_visible_run_control,
    )

    sid, rid = "session-runtime-ejet", "run-runtime-ejet"
    ifr.mark_started(run_id=rid, session_id=sid, user_message="vækning", kind="visible")
    _set_visible_run_control(rid, {"run_id": rid, "session_id": sid, "cancelled": False})
    try:
        ud = chat.chat_cancel_active(sid)

        assert ud["cancelled"] is True, "stop skal ramme et run ejet af den anden proces"
        assert rid in ud["run_ids"]
        # Flaget er det runtime læser — det er selve annulleringen, ikke et svar.
        assert _get_visible_run_control(rid).get("cancelled") is True
    finally:
        ifr.mark_completed(rid)
        _set_visible_run_control(rid, {})


def test_run_uden_control_state_afvises_ikke_som_succes(monkeypatch):
    """Et run der ikke kan annulleres må ikke rapporteres som stoppet.

    Målt 16/11-2026: `cancel_visible_run` kræver en controller ELLER en
    control-state-post. Mangler begge, findes intet at annullere — og svaret
    skal være `cancelled: false`, ikke en tavs succes.
    """
    from apps.api.jarvis_api.routes import chat
    from core.services import in_flight_runs as ifr

    sid, rid = "session-uden-kontrol", "run-uden-kontrol"
    ifr.mark_started(run_id=rid, session_id=sid, user_message="x", kind="visible")
    try:
        ud = chat.chat_cancel_active(sid)
        assert ud["cancelled"] is False
        assert ud["run_ids"] == []
    finally:
        ifr.mark_completed(rid)
