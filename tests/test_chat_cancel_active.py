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

    assert ud == {"cancelled": True, "run_id": "run-a"}
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

    assert ud == {"cancelled": True, "run_id": "run-b"}
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


def test_to_runs_i_samme_samtale_rammer_den_nyeste(monkeypatch):
    """Semantikken er «det jeg ser» — den nyeste kørsel i samtalen."""
    from apps.api.jarvis_api.routes import chat

    rel.create("run-aeldre", "session-y")
    rel.create("run-nyeste", "session-y")

    ramte: list[str] = []
    monkeypatch.setattr(
        chat, "cancel_visible_run", lambda rid: ramte.append(rid) or True
    )

    ud = chat.chat_cancel_active("session-y")

    assert ud["run_id"] == "run-nyeste"
    assert ramte == ["run-nyeste"]
