# tests/test_notifikations_kobling.py
from __future__ import annotations

import inspect


def test_afstemning_laegger_en_raekke_for_en_ventende_godkendelse(isolated_runtime, monkeypatch) -> None:
    from core.services import approval_runtime, notification_router
    from core.services import notifikationer as n
    from core.services import notifikations_emittere as e

    monkeypatch.setattr(notification_router, "route_proactive_notification",
                        lambda *a, **kw: {"ok": True})
    monkeypatch.setattr(approval_runtime, "alle_pending_for_owner", lambda uid: [{
        "approval_id": "a-1", "tool_name": "bash_session", "session_id": "s-1"}])

    assert e.afstem_godkendelser("bjorn") == 1
    raekker = n.aabne("bjorn", er_owner=True)
    assert [r["ref"] for r in raekker] == ["a-1"]


def test_afstemning_er_idempotent(isolated_runtime, monkeypatch) -> None:
    """Den koerer ved HVER laesning. Anden gang maa den intet goere."""
    from core.services import approval_runtime, notification_router
    from core.services import notifikationer as n
    from core.services import notifikations_emittere as e

    monkeypatch.setattr(notification_router, "route_proactive_notification",
                        lambda *a, **kw: {"ok": True})
    monkeypatch.setattr(approval_runtime, "alle_pending_for_owner", lambda uid: [{
        "approval_id": "a-1", "tool_name": "bash_session", "session_id": "s-1"}])

    e.afstem_godkendelser("bjorn")
    assert e.afstem_godkendelser("bjorn") == 0
    assert len(n.aabne("bjorn", er_owner=True)) == 1


def test_afstemning_der_fejler_tommer_ikke_feeden(isolated_runtime, monkeypatch) -> None:
    from core.services import approval_runtime
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h

    n.opret(user_id="bjorn", slags="reminder", kilde="egen", titel="Husk mælk")

    def sprang(_uid):
        raise RuntimeError("basen er væk")
    monkeypatch.setattr(approval_runtime, "alle_pending_for_owner", sprang)

    assert len(h.feed("bjorn", er_owner=True)) == 1


def test_feeden_afstemmer_selv(isolated_runtime, monkeypatch) -> None:
    """Uden dette kald ville afstemningen vaere kode ingen kalder."""
    from core.services import approval_runtime, notification_router
    from core.services import notifikationer_hydrering as h

    monkeypatch.setattr(notification_router, "route_proactive_notification",
                        lambda *a, **kw: {"ok": True})
    monkeypatch.setattr(approval_runtime, "alle_pending_for_owner", lambda uid: [{
        "approval_id": "a-1", "tool_name": "bash_session", "session_id": "s-1"}])
    monkeypatch.setattr(approval_runtime, "state",
                        lambda aid: {"status": "pending", "tool_name": "bash_session"})

    poster = h.feed("bjorn", er_owner=True)
    assert len(poster) == 1
    assert poster[0]["kan_afgoere"] is True


def test_en_fejlet_koersel_giver_en_raekke(isolated_runtime, monkeypatch) -> None:
    """KALDER finalize_in_flight rigtigt. En kilde-vagt der greber efter en
    streng maaler naesten ingenting — den ville vaere groen ogsaa hvis kaldet
    stod i en gren der aldrig naas.

    K3 (2026-09-22): denne test bevisede FOER kun at raekken blev SKABT — den
    stoppede lige foer den ville have opdaget at raekken forsvinder igen ved
    foerste hydrering. `_hydrer_run` accepterede kun `("failed",
    "interrupted")` for `run_failed`, men `status_for_run()` laeser den RAA
    DB-status, som kan vaere `failed_terminal` (se
    core/services/visible_runs.py:6081, `settlement_shadow.py:109`
    normaliserer netop den til `failed`). Udvidet til ogsaa at laese feeden
    igen bagefter, med en rigtig `visible_runs`-raekke saa
    `status_for_run("r-1")` faktisk finder `failed_terminal` i stedet for at
    falde igennem paa "raekken findes ikke"."""
    from core.runtime.db import connect
    from core.services import notification_router
    from core.services import notifikationer as n
    from core.services import notifikationer_hydrering as h
    from core.services.visible_runs_sections.run_finalization import finalize_in_flight

    monkeypatch.setattr(notification_router, "route_proactive_notification",
                        lambda *a, **kw: {"delivered": True, "channel": "push",
                                          "target": "bjorn", "fallback_used": False})
    with connect() as conn:
        # Noeglen hedder `session_id`; `id` er et autoincrement-heltal, og der
        # findes INGEN user_id-kolonne (maalt 21/9-2026).
        conn.execute(
            "INSERT INTO chat_sessions (session_id, title, created_at, updated_at)"
            " VALUES (?,?,?,?)", ("s-1", "Kæledyret", "nu", "nu"))
        # Den RIGTIGE DB-projektion et run efterlader — uden den falder
        # `status_for_run("r-1")` tilbage paa "" (raekken findes ikke), og
        # hydreringen ville lukke raekken uanset hvilke statusser den
        # accepterer.
        conn.execute(
            "INSERT INTO visible_runs (run_id, lane, provider, model, status,"
            " finished_at) VALUES (?,?,?,?,?,?)",
            ("r-1", "visible", "test-provider", "test-model", "failed_terminal", "nu"))
        conn.commit()
    monkeypatch.setattr(
        "core.identity.workspace_context.current_user_id", lambda: "bjorn")

    finalize_in_flight(run_id="r-1", session_id="s-1", status="failed_terminal",
                       error="noget braekkede")

    raekker = n.aabne("bjorn", er_owner=True)
    assert [r["slags"] for r in raekker] == ["run_failed"]
    assert "Kæledyret" in raekker[0]["titel"]

    # Den del testen FOER stoppede lige foer: laes feeden igen. Uden K3-
    # rettelsen lukkes raekken her, og poster bliver [].
    poster = h.feed("bjorn", er_owner=True)
    assert [p["slags"] for p in poster] == ["run_failed"], (
        "raekken forsvandt ved hydrering — failed_terminal blev ikke "
        "genkendt som en fejlet koersel"
    )


def test_en_faerdig_koersel_giver_den_anden_slags(isolated_runtime, monkeypatch) -> None:
    from core.runtime.db import connect
    from core.services import notification_router
    from core.services import notifikationer as n
    from core.services.visible_runs_sections.run_finalization import finalize_in_flight

    monkeypatch.setattr(notification_router, "route_proactive_notification",
                        lambda *a, **kw: {"delivered": False, "channel": "none",
                                          "target": "", "fallback_used": False})
    with connect() as conn:
        # Noeglen hedder `session_id`; `id` er et autoincrement-heltal, og der
        # findes INGEN user_id-kolonne (maalt 21/9-2026).
        conn.execute(
            "INSERT INTO chat_sessions (session_id, title, created_at, updated_at)"
            " VALUES (?,?,?,?)", ("s-1", "Kæledyret", "nu", "nu"))
        conn.commit()
    monkeypatch.setattr(
        "core.identity.workspace_context.current_user_id", lambda: "bjorn")

    finalize_in_flight(run_id="r-2", session_id="s-1", status="completed")
    assert [r["slags"] for r in n.aabne("bjorn", er_owner=True)] == ["run_done"]


def test_release_vagten_kalder_emitteren() -> None:
    """Denne ENE er en kilde-vagt med vilje: at koere vagten rigtigt kraever et
    kald ud af huset til GitHub. Den maaler kun at ledningen findes — selve
    adfaerden er daekket af emitter-testene."""
    import apps.api.jarvis_api.routes.app_release as m
    assert "notifikations_emittere" in inspect.getsource(m)
